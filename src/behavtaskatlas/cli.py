from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from behavtaskatlas.clicks import (
    CLICKS_PSYCHOMETRIC_X_AXIS_LABEL,
    DEFAULT_CLICKS_DERIVED_DIR,
    DEFAULT_CLICKS_SESSION_ID,
    aggregate_brody_clicks_batch,
    analyze_brody_clicks,
    analyze_brody_clicks_evidence_kernel,
    brody_clicks_provenance_payload,
    load_brody_clicks_mat,
    write_aggregate_kernel_summary_csv,
    write_aggregate_kernel_svg,
    write_aggregate_psychometric_bias_csv,
    write_clicks_aggregate_report_html,
    write_clicks_batch_summary_csv,
    write_evidence_kernel_summary_csv,
    write_evidence_kernel_svg,
)
from behavtaskatlas.ibl import (
    DEFAULT_DERIVED_DIR,
    DEFAULT_IBL_EID,
    analyze_ibl_visual_decision,
    harmonize_ibl_visual_trials,
    load_canonical_trials_csv,
    load_ibl_trials_from_openalyx,
    provenance_payload,
    summarize_canonical_trials,
    write_analysis_json,
    write_canonical_trials_csv,
    write_ibl_visual_report_html,
    write_provenance_json,
    write_psychometric_svg,
    write_summary_csv,
)
from behavtaskatlas.models import SCHEMA_MODELS, CanonicalTrial
from behavtaskatlas.rdm import (
    DEFAULT_RDM_DERIVED_DIR,
    DEFAULT_RDM_RAW_CSV,
    DEFAULT_RDM_SESSION_ID,
    RDM_PSYCHOMETRIC_X_AXIS_LABEL,
    analyze_roitman_rdm,
    download_roitman_rdm_csv,
    load_roitman_rdm_csv,
    rdm_provenance_payload,
    write_rdm_chronometric_csv,
    write_rdm_chronometric_svg,
    write_rdm_report_html,
)
from behavtaskatlas.static_site import (
    build_catalog_payload,
    build_static_index_payload,
    write_static_catalog_html,
    write_static_catalog_json,
    write_static_index_html,
    write_static_manifest_json,
    write_static_protocol_pages,
)
from behavtaskatlas.validation import validate_repository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="behavtaskatlas")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate repository records")
    validate_parser.add_argument("root", nargs="?", default=".", help="Repository root")

    schema_parser = subparsers.add_parser(
        "export-schemas", help="Export JSON schemas from the Python models"
    )
    schema_parser.add_argument("output_dir", nargs="?", default="schemas")

    ibl_parser = subparsers.add_parser(
        "ibl-harmonize", help="Harmonize one IBL visual decision session"
    )
    ibl_parser.add_argument("--eid", default=DEFAULT_IBL_EID, help="IBL session UUID/eid")
    ibl_parser.add_argument(
        "--out-dir",
        default="derived/ibl_visual_decision",
        help="Directory for generated artifacts",
    )
    ibl_parser.add_argument("--cache-dir", default=None, help="Optional ONE cache directory")
    ibl_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")
    ibl_parser.add_argument(
        "--revision",
        default=None,
        help="Optional IBL dataset revision to load, e.g. 2025-03-03",
    )

    analyze_parser = subparsers.add_parser(
        "ibl-analyze", help="Analyze a harmonized IBL visual decision session"
    )
    analyze_parser.add_argument("--eid", default=DEFAULT_IBL_EID, help="IBL session UUID/eid")
    analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_DERIVED_DIR),
        help="Directory containing generated IBL artifacts",
    )
    analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    ibl_report_parser = subparsers.add_parser(
        "ibl-report",
        help="Render a static HTML report from an analyzed IBL visual decision session",
    )
    ibl_report_parser.add_argument("--eid", default=DEFAULT_IBL_EID, help="IBL session UUID/eid")
    ibl_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_DERIVED_DIR),
        help="Directory containing generated IBL artifacts",
    )
    ibl_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    ibl_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    ibl_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    ibl_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    clicks_parser = subparsers.add_parser(
        "clicks-harmonize",
        help="Harmonize one local Brody Lab Poisson Clicks `.mat` file",
    )
    clicks_parser.add_argument("--mat-file", required=True, help="Path to a local `.mat` file")
    clicks_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory for generated artifacts",
    )
    clicks_parser.add_argument(
        "--parsed-field",
        default="parsed",
        choices=["parsed", "parsed_frozen"],
        help="ratdata field to harmonize",
    )
    clicks_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    clicks_analyze_parser = subparsers.add_parser(
        "clicks-analyze",
        help="Analyze a harmonized Brody Lab Poisson Clicks session",
    )
    clicks_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_CLICKS_SESSION_ID,
        help="Harmonized session directory name",
    )
    clicks_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory containing generated auditory-clicks artifacts",
    )
    clicks_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )
    clicks_analyze_parser.add_argument(
        "--kernel-bins",
        type=int,
        default=10,
        help="Number of normalized time bins for the evidence-kernel analysis",
    )

    clicks_batch_parser = subparsers.add_parser(
        "clicks-batch",
        help="Harmonize and analyze multiple local Brody Lab Poisson Clicks `.mat` files",
    )
    clicks_batch_sources = clicks_batch_parser.add_mutually_exclusive_group(required=True)
    clicks_batch_sources.add_argument(
        "--mat-dir",
        default=None,
        help="Directory containing extracted `.mat` files",
    )
    clicks_batch_sources.add_argument(
        "--mat-file",
        action="append",
        default=None,
        dest="mat_files",
        help="Path to a local `.mat` file; may be passed more than once",
    )
    clicks_batch_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory for generated artifacts and batch_summary.csv",
    )
    clicks_batch_parser.add_argument(
        "--parsed-field",
        default="parsed",
        choices=["parsed", "parsed_frozen"],
        help="ratdata field to harmonize",
    )
    clicks_batch_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")
    clicks_batch_parser.add_argument(
        "--kernel-bins",
        type=int,
        default=10,
        help="Number of normalized time bins for the evidence-kernel analysis",
    )
    clicks_batch_parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional maximum number of `.mat` files after filename sorting",
    )
    clicks_batch_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first file that fails",
    )

    clicks_aggregate_parser = subparsers.add_parser(
        "clicks-aggregate",
        help="Aggregate existing Brody Lab clicks batch outputs",
    )
    clicks_aggregate_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory containing generated auditory-clicks batch artifacts",
    )
    clicks_aggregate_parser.add_argument(
        "--batch-summary",
        default=None,
        help="Optional explicit path to a clicks batch_summary.csv",
    )

    clicks_report_parser = subparsers.add_parser(
        "clicks-report",
        help="Render a static HTML report from existing clicks aggregate outputs",
    )
    clicks_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory containing generated auditory-clicks aggregate artifacts",
    )
    clicks_report_parser.add_argument(
        "--aggregate-result",
        default=None,
        help="Optional explicit path to aggregate_result.json",
    )
    clicks_report_parser.add_argument(
        "--aggregate-kernel-svg",
        default=None,
        help="Optional explicit path to aggregate_kernel.svg",
    )
    clicks_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    rdm_download_parser = subparsers.add_parser(
        "rdm-download",
        help="Download the processed Roitman-Shadlen random-dot motion CSV",
    )
    rdm_download_parser.add_argument(
        "--out-file",
        default=str(DEFAULT_RDM_RAW_CSV),
        help="Local output path under ignored raw-data storage",
    )

    rdm_parser = subparsers.add_parser(
        "rdm-harmonize",
        help="Harmonize the processed Roitman-Shadlen random-dot motion CSV",
    )
    rdm_parser.add_argument(
        "--csv-file",
        default=str(DEFAULT_RDM_RAW_CSV),
        help="Path to the processed Roitman-Shadlen CSV",
    )
    rdm_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_RDM_DERIVED_DIR),
        help="Directory for generated random-dot motion artifacts",
    )
    rdm_parser.add_argument(
        "--session-id",
        default=DEFAULT_RDM_SESSION_ID,
        help="Session directory name for the processed dataset",
    )
    rdm_parser.add_argument("--monkey", type=int, default=None, help="Optional monkey id")
    rdm_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    rdm_analyze_parser = subparsers.add_parser(
        "rdm-analyze",
        help="Analyze a harmonized Roitman-Shadlen random-dot motion dataset",
    )
    rdm_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_RDM_SESSION_ID,
        help="Harmonized session directory name",
    )
    rdm_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_RDM_DERIVED_DIR),
        help="Directory containing generated random-dot motion artifacts",
    )
    rdm_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    rdm_report_parser = subparsers.add_parser(
        "rdm-report",
        help="Render a static HTML report from analyzed random-dot motion artifacts",
    )
    rdm_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_RDM_SESSION_ID,
        help="Analyzed session directory name",
    )
    rdm_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_RDM_DERIVED_DIR),
        help="Directory containing generated random-dot motion artifacts",
    )
    rdm_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    rdm_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    rdm_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    rdm_report_parser.add_argument(
        "--chronometric-svg",
        default=None,
        help="Optional explicit path to chronometric.svg",
    )
    rdm_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    site_index_parser = subparsers.add_parser(
        "site-index",
        help="Render a static index linking generated vertical-slice reports",
    )
    site_index_parser.add_argument(
        "--derived-dir",
        default="derived",
        help="Derived artifact root containing generated slice reports",
    )
    site_index_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional index HTML output path",
    )
    site_index_parser.add_argument(
        "--manifest-file",
        default=None,
        help="Optional machine-readable manifest JSON output path",
    )
    site_index_parser.add_argument(
        "--catalog-file",
        default=None,
        help="Optional catalog HTML output path",
    )
    site_index_parser.add_argument(
        "--catalog-json-file",
        default=None,
        help="Optional machine-readable catalog JSON output path",
    )

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(Path(args.root))
    if args.command == "export-schemas":
        return _export_schemas(Path(args.output_dir))
    if args.command == "ibl-harmonize":
        return _ibl_harmonize(
            eid=args.eid,
            out_dir=Path(args.out_dir),
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            limit=args.limit,
            revision=args.revision,
        )
    if args.command == "ibl-analyze":
        return _ibl_analyze(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "ibl-report":
        return _ibl_report(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "clicks-harmonize":
        return _clicks_harmonize(
            mat_file=Path(args.mat_file),
            out_dir=Path(args.out_dir),
            parsed_field=args.parsed_field,
            limit=args.limit,
        )
    if args.command == "clicks-analyze":
        return _clicks_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
            kernel_bins=args.kernel_bins,
        )
    if args.command == "clicks-batch":
        return _clicks_batch(
            mat_files=[Path(path) for path in args.mat_files] if args.mat_files else None,
            mat_dir=Path(args.mat_dir) if args.mat_dir else None,
            out_dir=Path(args.out_dir),
            parsed_field=args.parsed_field,
            limit=args.limit,
            kernel_bins=args.kernel_bins,
            max_files=args.max_files,
            fail_fast=args.fail_fast,
        )
    if args.command == "clicks-aggregate":
        return _clicks_aggregate(
            derived_dir=Path(args.derived_dir),
            batch_summary=Path(args.batch_summary) if args.batch_summary else None,
        )
    if args.command == "clicks-report":
        return _clicks_report(
            derived_dir=Path(args.derived_dir),
            aggregate_result=Path(args.aggregate_result) if args.aggregate_result else None,
            aggregate_kernel_svg=Path(args.aggregate_kernel_svg)
            if args.aggregate_kernel_svg
            else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "rdm-download":
        return _rdm_download(out_file=Path(args.out_file))
    if args.command == "rdm-harmonize":
        return _rdm_harmonize(
            csv_file=Path(args.csv_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            monkey=args.monkey,
            limit=args.limit,
        )
    if args.command == "rdm-analyze":
        return _rdm_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "rdm-report":
        return _rdm_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            chronometric_svg=Path(args.chronometric_svg) if args.chronometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "site-index":
        return _site_index(
            derived_dir=Path(args.derived_dir),
            out_file=Path(args.out_file) if args.out_file else None,
            manifest_file=Path(args.manifest_file) if args.manifest_file else None,
            catalog_file=Path(args.catalog_file) if args.catalog_file else None,
            catalog_json_file=Path(args.catalog_json_file)
            if args.catalog_json_file
            else None,
        )
    parser.error(f"Unknown command {args.command!r}")
    return 2


def _validate(root: Path) -> int:
    report = validate_repository(root.resolve())
    if report.ok:
        print(f"Validated {len(report.records)} records.")
        return 0

    for issue in report.issues:
        print(f"{issue.path}: {issue.message}", file=sys.stderr)
    return 1


def _export_schemas(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    for schema_name, model in SCHEMA_MODELS.items():
        path = output_dir / f"{schema_name}.schema.json"
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(path)
    return 0


def _ibl_harmonize(
    *,
    eid: str,
    out_dir: Path,
    cache_dir: Path | None,
    limit: int | None,
    revision: str | None,
) -> int:
    try:
        source_trials, details = load_ibl_trials_from_openalyx(
            eid,
            cache_dir=cache_dir,
            revision=revision,
        )
        trials = harmonize_ibl_visual_trials(
            source_trials,
            session_id=eid,
            subject_id=details.get("subject"),
            limit=limit,
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / eid
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"

    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        provenance_payload(
            eid=eid,
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _ibl_analyze(
    *,
    eid: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / eid
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra ibl behavtaskatlas ibl-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_ibl_visual_decision(trials)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(plot_path, result["summary_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    return 0


def _ibl_report(
    *,
    eid: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / eid
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or session_dir / "psychometric.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"IBL analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas ibl-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = None
    if psychometric_svg_path.exists():
        psychometric_svg_text = psychometric_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", session_dir / "psychometric_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("canonical trials CSV", session_dir / "trials.csv"),
            ("harmonization summary CSV", session_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_ibl_visual_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote IBL visual decision report to {report_path}")
    if psychometric_svg_text is None:
        print(
            "Psychometric SVG not found, wrote report without inline plot: "
            f"{psychometric_svg_path}"
        )
    return 0


def _clicks_harmonize(
    *,
    mat_file: Path,
    out_dir: Path,
    parsed_field: str,
    limit: int | None,
) -> int:
    if not mat_file.exists():
        print(f"MATLAB file not found: {mat_file}", file=sys.stderr)
        return 2
    try:
        trials, details = load_brody_clicks_mat(
            mat_file,
            parsed_field=parsed_field,
            limit=limit,
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    outputs = _write_clicks_harmonization_outputs(
        trials=trials,
        details=details,
        mat_file=mat_file,
        out_dir=out_dir,
        parsed_field=parsed_field,
    )

    print(f"Wrote {len(trials)} trials to {outputs['trials_path']}")
    print(f"Wrote {len(outputs['summary_rows'])} summary rows to {outputs['summary_path']}")
    print(f"Wrote provenance to {outputs['provenance_path']}")
    return 0


def _clicks_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
    kernel_bins: int,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra clicks behavtaskatlas clicks-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    try:
        outputs = _write_clicks_analysis_outputs(
            trials=trials,
            session_dir=session_dir,
            kernel_bins=kernel_bins,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {outputs['psychometric_summary_path']}")
    print(f"Wrote analysis result to {outputs['analysis_result_path']}")
    print(f"Wrote psychometric plot to {outputs['psychometric_plot_path']}")
    print(f"Wrote evidence-kernel summary to {outputs['evidence_kernel_summary_path']}")
    print(f"Wrote evidence-kernel result to {outputs['evidence_kernel_result_path']}")
    print(f"Wrote evidence-kernel plot to {outputs['evidence_kernel_plot_path']}")
    return 0


def _clicks_batch(
    *,
    mat_files: list[Path] | None,
    mat_dir: Path | None,
    out_dir: Path,
    parsed_field: str,
    limit: int | None,
    kernel_bins: int,
    max_files: int | None,
    fail_fast: bool,
) -> int:
    try:
        paths = _clicks_batch_mat_files(mat_files=mat_files, mat_dir=mat_dir, max_files=max_files)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not paths:
        print("No `.mat` files found for clicks batch.", file=sys.stderr)
        return 2

    rows = []
    n_failed = 0
    for mat_file in paths:
        row = _clicks_batch_row_template(mat_file=mat_file, parsed_field=parsed_field)
        try:
            trials, details = load_brody_clicks_mat(
                mat_file,
                parsed_field=parsed_field,
                limit=limit,
            )
            harmonization_outputs = _write_clicks_harmonization_outputs(
                trials=trials,
                details=details,
                mat_file=mat_file,
                out_dir=out_dir,
                parsed_field=parsed_field,
            )
            analysis_outputs = _write_clicks_analysis_outputs(
                trials=trials,
                session_dir=harmonization_outputs["session_dir"],
                kernel_bins=kernel_bins,
            )
            psychometric_contexts = sorted(
                {
                    row["prior_context"]
                    for row in analysis_outputs["psychometric_result"]["summary_rows"]
                    if row["prior_context"]
                }
            )
            row.update(
                {
                    "session_id": harmonization_outputs["session_id"],
                    "subject_id": details.get("subject_id"),
                    "task_type": details.get("task_type"),
                    "status": "ok",
                    "n_trials": len(trials),
                    "harmonization_summary_rows": len(harmonization_outputs["summary_rows"]),
                    "psychometric_summary_rows": len(
                        analysis_outputs["psychometric_result"]["summary_rows"]
                    ),
                    "psychometric_prior_contexts": ";".join(psychometric_contexts),
                    "evidence_kernel_rows": len(
                        analysis_outputs["evidence_kernel_result"]["summary_rows"]
                    ),
                    "evidence_kernel_analyzed_trials": analysis_outputs[
                        "evidence_kernel_result"
                    ]["n_analyzed_trials"],
                    "evidence_kernel_excluded_trials": analysis_outputs[
                        "evidence_kernel_result"
                    ]["n_excluded_trials"],
                    "source_file_sha256": details.get("source_file_sha256"),
                    "output_dir": str(harmonization_outputs["session_dir"]),
                }
            )
            print(f"OK {mat_file}: {len(trials)} trials")
        except Exception as exc:
            n_failed += 1
            row.update({"status": "error", "error": str(exc)})
            print(f"ERROR {mat_file}: {exc}", file=sys.stderr)
            rows.append(row)
            if fail_fast:
                break
            continue
        rows.append(row)

    summary_path = out_dir / "batch_summary.csv"
    write_clicks_batch_summary_csv(summary_path, rows)
    print(f"Wrote batch summary to {summary_path}")
    print(f"Processed {len(rows)} files: {len(rows) - n_failed} ok, {n_failed} failed")
    return 1 if n_failed else 0


def _clicks_aggregate(*, derived_dir: Path, batch_summary: Path | None) -> int:
    batch_summary_path = batch_summary or derived_dir / "batch_summary.csv"
    if not batch_summary_path.exists():
        print(
            f"Clicks batch summary not found: {batch_summary_path}. "
            "Run `uv run behavtaskatlas clicks-batch` first.",
            file=sys.stderr,
        )
        return 2

    try:
        result = aggregate_brody_clicks_batch(batch_summary_path)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output_dir = derived_dir
    psychometric_path = output_dir / "aggregate_psychometric_bias.csv"
    kernel_summary_path = output_dir / "aggregate_kernel_summary.csv"
    result_path = output_dir / "aggregate_result.json"
    kernel_plot_path = output_dir / "aggregate_kernel.svg"

    write_aggregate_psychometric_bias_csv(
        psychometric_path,
        result["psychometric_bias_rows"],
    )
    write_aggregate_kernel_summary_csv(kernel_summary_path, result["kernel_summary_rows"])
    write_analysis_json(result_path, result)
    write_aggregate_kernel_svg(kernel_plot_path, result["kernel_summary_rows"])

    print(f"Aggregated {result['n_ok']} ok batch rows from {batch_summary_path}")
    print(f"Wrote aggregate psychometric bias table to {psychometric_path}")
    print(f"Wrote aggregate kernel summary to {kernel_summary_path}")
    print(f"Wrote aggregate result to {result_path}")
    print(f"Wrote aggregate kernel plot to {kernel_plot_path}")
    if result["n_artifact_errors"]:
        print(f"Encountered {result['n_artifact_errors']} aggregate artifact errors")
        return 1
    return 0


def _clicks_report(
    *,
    derived_dir: Path,
    aggregate_result: Path | None,
    aggregate_kernel_svg: Path | None,
    out_file: Path | None,
) -> int:
    result_path = aggregate_result or derived_dir / "aggregate_result.json"
    kernel_svg_path = aggregate_kernel_svg or derived_dir / "aggregate_kernel.svg"
    report_path = out_file or derived_dir / "report.html"
    if not result_path.exists():
        print(
            f"Clicks aggregate result not found: {result_path}. "
            "Run `uv run behavtaskatlas clicks-aggregate` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not isinstance(loaded, dict):
        print(f"Expected JSON object in {result_path}", file=sys.stderr)
        return 2

    kernel_svg_text = None
    if kernel_svg_path.exists():
        kernel_svg_text = kernel_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        "aggregate result JSON": _relative_artifact_link(result_path, report_dir),
        "aggregate psychometric bias CSV": _relative_artifact_link(
            derived_dir / "aggregate_psychometric_bias.csv",
            report_dir,
        ),
        "aggregate kernel summary CSV": _relative_artifact_link(
            derived_dir / "aggregate_kernel_summary.csv",
            report_dir,
        ),
        "aggregate kernel SVG": _relative_artifact_link(kernel_svg_path, report_dir),
        "batch summary CSV": _relative_artifact_link(
            derived_dir / "batch_summary.csv",
            report_dir,
        ),
    }
    write_clicks_aggregate_report_html(
        report_path,
        loaded,
        aggregate_kernel_svg_text=kernel_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote clicks aggregate report to {report_path}")
    if kernel_svg_text is None:
        print(
            "Aggregate kernel SVG not found, wrote report without inline plot: "
            f"{kernel_svg_path}"
        )
    return 0


def _rdm_download(*, out_file: Path) -> int:
    try:
        details = download_roitman_rdm_csv(out_file)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded {details['n_bytes']} bytes to {out_file}")
    print(f"SHA256 {details['sha256']}")
    return 0


def _rdm_harmonize(
    *,
    csv_file: Path,
    out_dir: Path,
    session_id: str,
    monkey: int | None,
    limit: int | None,
) -> int:
    if not csv_file.exists():
        print(
            f"RDM CSV not found: {csv_file}. Run `uv run behavtaskatlas rdm-download` first.",
            file=sys.stderr,
        )
        return 2
    try:
        trials, details = load_roitman_rdm_csv(
            csv_file,
            session_id=session_id,
            monkey=monkey,
            limit=limit,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        rdm_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _rdm_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas rdm-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_roitman_rdm(trials)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"
    chronometric_path = session_dir / "chronometric_summary.csv"
    chronometric_plot_path = session_dir / "chronometric.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        plot_path,
        result["summary_rows"],
        x_axis_label=RDM_PSYCHOMETRIC_X_AXIS_LABEL,
    )
    write_rdm_chronometric_csv(chronometric_path, result["chronometric_rows"])
    write_rdm_chronometric_svg(chronometric_plot_path, result["chronometric_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    print(f"Wrote chronometric summary to {chronometric_path}")
    print(f"Wrote chronometric plot to {chronometric_plot_path}")
    return 0


def _rdm_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    chronometric_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or session_dir / "psychometric.svg"
    chronometric_svg_path = chronometric_svg or session_dir / "chronometric.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"RDM analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas rdm-analyze` first.",
            file=sys.stderr,
        )
        return 2
    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = (
        psychometric_svg_path.read_text(encoding="utf-8")
        if psychometric_svg_path.exists()
        else None
    )
    chronometric_svg_text = (
        chronometric_svg_path.read_text(encoding="utf-8")
        if chronometric_svg_path.exists()
        else None
    )
    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", session_dir / "psychometric_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("chronometric summary CSV", session_dir / "chronometric_summary.csv"),
            ("chronometric SVG", chronometric_svg_path),
            ("canonical trials CSV", session_dir / "trials.csv"),
        ]
        if path.exists()
    }
    write_rdm_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        chronometric_svg_text=chronometric_svg_text,
        artifact_links=artifact_links,
    )
    print(f"Wrote random-dot motion report to {report_path}")
    return 0


def _site_index(
    *,
    derived_dir: Path,
    out_file: Path | None,
    manifest_file: Path | None,
    catalog_file: Path | None,
    catalog_json_file: Path | None,
) -> int:
    index_path = out_file or derived_dir / "index.html"
    manifest_path = manifest_file or index_path.with_name("manifest.json")
    catalog_path = catalog_file or index_path.with_name("catalog.html")
    catalog_json_path = catalog_json_file or index_path.with_name("catalog.json")
    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=index_path,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
    )
    write_static_index_html(index_path, payload)
    write_static_manifest_json(manifest_path, payload)
    catalog_payload = build_catalog_payload(
        root=Path("."),
        derived_dir=derived_dir,
        catalog_path=catalog_path,
        catalog_json_path=catalog_json_path,
        report_index_path=index_path,
    )
    write_static_catalog_html(catalog_path, catalog_payload)
    write_static_catalog_json(catalog_json_path, catalog_payload)
    protocol_pages = write_static_protocol_pages(catalog_path, catalog_payload)
    available = sum(1 for item in payload["slices"] if item.get("report_status") == "available")
    print(f"Wrote static index to {index_path}")
    print(f"Wrote report manifest to {manifest_path}")
    print(f"Wrote catalog to {catalog_path}")
    print(f"Wrote catalog JSON to {catalog_json_path}")
    print(f"Wrote {len(protocol_pages)} protocol detail pages")
    print(f"Indexed {len(payload['slices'])} vertical slices; {available} report available")
    return 0


def _write_clicks_harmonization_outputs(
    *,
    trials: list[CanonicalTrial],
    details: dict[str, Any],
    mat_file: Path,
    out_dir: Path,
    parsed_field: str,
) -> dict[str, Any]:
    session_id = f"{mat_file.stem}-{parsed_field}"
    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"

    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        brody_clicks_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )
    return {
        "session_id": session_id,
        "session_dir": session_dir,
        "trials_path": trials_path,
        "summary_path": summary_path,
        "provenance_path": provenance_path,
        "summary_rows": summary,
    }


def _write_clicks_analysis_outputs(
    *,
    trials: list[CanonicalTrial],
    session_dir: Path,
    kernel_bins: int,
) -> dict[str, Any]:
    result = analyze_brody_clicks(trials)
    kernel_result = analyze_brody_clicks_evidence_kernel(trials, n_bins=kernel_bins)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"
    kernel_summary_path = session_dir / "evidence_kernel_summary.csv"
    kernel_result_path = session_dir / "evidence_kernel_result.json"
    kernel_plot_path = session_dir / "evidence_kernel.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        plot_path,
        result["summary_rows"],
        x_axis_label=CLICKS_PSYCHOMETRIC_X_AXIS_LABEL,
    )
    write_evidence_kernel_summary_csv(kernel_summary_path, kernel_result["summary_rows"])
    write_analysis_json(kernel_result_path, kernel_result)
    write_evidence_kernel_svg(kernel_plot_path, kernel_result["summary_rows"])
    return {
        "psychometric_summary_path": summary_path,
        "analysis_result_path": result_path,
        "psychometric_plot_path": plot_path,
        "evidence_kernel_summary_path": kernel_summary_path,
        "evidence_kernel_result_path": kernel_result_path,
        "evidence_kernel_plot_path": kernel_plot_path,
        "psychometric_result": result,
        "evidence_kernel_result": kernel_result,
    }


def _clicks_batch_mat_files(
    *,
    mat_files: list[Path] | None,
    mat_dir: Path | None,
    max_files: int | None,
) -> list[Path]:
    if max_files is not None and max_files <= 0:
        raise ValueError("max_files must be positive")
    if mat_files is not None:
        paths = mat_files
    elif mat_dir is not None:
        if not mat_dir.exists():
            raise ValueError(f"MATLAB file directory not found: {mat_dir}")
        if not mat_dir.is_dir():
            raise ValueError(f"MATLAB file path is not a directory: {mat_dir}")
        paths = sorted(path for path in mat_dir.iterdir() if path.suffix.lower() == ".mat")
    else:
        paths = []
    sorted_paths = sorted(paths, key=lambda path: path.name)
    return sorted_paths[:max_files] if max_files is not None else sorted_paths


def _clicks_batch_row_template(*, mat_file: Path, parsed_field: str) -> dict:
    return {
        "mat_file": str(mat_file),
        "session_id": f"{mat_file.stem}-{parsed_field}",
        "parsed_field": parsed_field,
        "subject_id": mat_file.stem,
        "task_type": None,
        "status": None,
        "error": None,
        "n_trials": None,
        "harmonization_summary_rows": None,
        "psychometric_summary_rows": None,
        "psychometric_prior_contexts": None,
        "evidence_kernel_rows": None,
        "evidence_kernel_analyzed_trials": None,
        "evidence_kernel_excluded_trials": None,
        "source_file_sha256": None,
        "output_dir": None,
    }
    return 0


def _relative_artifact_link(path: Path, base_dir: Path) -> str:
    return os.path.relpath(path, base_dir).replace(os.sep, "/")


def _read_json_object_file(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return loaded


if __name__ == "__main__":
    raise SystemExit(main())
