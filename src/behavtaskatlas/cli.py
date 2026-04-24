from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from behavtaskatlas.clicks import (
    CLICKS_PSYCHOMETRIC_X_AXIS_LABEL,
    DEFAULT_CLICKS_DERIVED_DIR,
    DEFAULT_CLICKS_SESSION_ID,
    analyze_brody_clicks,
    analyze_brody_clicks_evidence_kernel,
    brody_clicks_provenance_payload,
    load_brody_clicks_mat,
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
from behavtaskatlas.models import SCHEMA_MODELS
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

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
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
    result = analyze_brody_clicks(trials)
    try:
        kernel_result = analyze_brody_clicks_evidence_kernel(trials, n_bins=kernel_bins)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

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

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    print(f"Wrote evidence-kernel summary to {kernel_summary_path}")
    print(f"Wrote evidence-kernel result to {kernel_result_path}")
    print(f"Wrote evidence-kernel plot to {kernel_plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
