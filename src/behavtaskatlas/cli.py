from __future__ import annotations

import argparse
import json
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
    write_provenance_json,
    write_psychometric_svg,
    write_summary_csv,
)
from behavtaskatlas.models import SCHEMA_MODELS, CanonicalTrial
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


if __name__ == "__main__":
    raise SystemExit(main())
