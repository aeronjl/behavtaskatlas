from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import urllib.request
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from behavtaskatlas.models import CanonicalTrial

BRODY_CLICKS_PROTOCOL_ID = "protocol.rat-auditory-clicks-nose-poke"
BRODY_CLICKS_DATASET_ID = "dataset.brody-lab-poisson-clicks-2009-2024"
DEFAULT_CLICKS_DERIVED_DIR = Path("derived/auditory_clicks")
DEFAULT_CLICKS_SESSION_ID = "B075-parsed"
CLICKS_PSYCHOMETRIC_X_AXIS_LABEL = "Signed click-count difference (right minus left clicks)"
HUMAN_CLICKS_PROTOCOL_ID = "protocol.human-auditory-clicks-button"
HUMAN_CLICKS_DATASET_ID = "dataset.london-human-poisson-clicks-dbs-mendeley"
DEFAULT_HUMAN_CLICKS_RAW_MAT = Path("data/raw/human_clicks_mendeley/poisson_clicks_rawdata.mat")
DEFAULT_HUMAN_CLICKS_DERIVED_DIR = Path("derived/human_auditory_clicks")
DEFAULT_HUMAN_CLICKS_SESSION_ID = "london-dbs-poisson-clicks-mendeley"
MENDELEY_HUMAN_CLICKS_DATASET_URL = "https://data.mendeley.com/datasets/3j86m7mjx2/1"
MENDELEY_HUMAN_CLICKS_FILE_ID = "dce6ed60-2585-45aa-957c-a731ff6b9790"
MENDELEY_HUMAN_CLICKS_DOWNLOAD_URL = (
    "https://data.mendeley.com/public-files/datasets/3j86m7mjx2/files/"
    f"{MENDELEY_HUMAN_CLICKS_FILE_ID}/file_downloaded"
)
MENDELEY_HUMAN_CLICKS_SHA256 = (
    "1040c8fe110e8eec206fb589f30dbff681429de4bb64162a116fdec17904d49a"
)
HUMAN_CLICKS_PSYCHOMETRIC_X_AXIS_LABEL = (
    "Signed click-count difference at response (right minus left clicks)"
)
EVIDENCE_KERNEL_SUMMARY_FIELDS = [
    "bin_index",
    "bin_start",
    "bin_end",
    "n_trials",
    "n_right_choice",
    "n_left_choice",
    "mean_signed_evidence",
    "mean_signed_evidence_right_choice",
    "mean_signed_evidence_left_choice",
    "choice_difference",
    "point_biserial_r",
    "normalized_weight",
]
CLICKS_BATCH_SUMMARY_FIELDS = [
    "mat_file",
    "session_id",
    "parsed_field",
    "subject_id",
    "task_type",
    "status",
    "error",
    "n_trials",
    "harmonization_summary_rows",
    "psychometric_summary_rows",
    "psychometric_prior_contexts",
    "evidence_kernel_rows",
    "evidence_kernel_analyzed_trials",
    "evidence_kernel_excluded_trials",
    "source_file_sha256",
    "output_dir",
]
AGGREGATE_PSYCHOMETRIC_BIAS_FIELDS = [
    "session_id",
    "subject_id",
    "task_type",
    "prior_context",
    "n_trials",
    "n_response_trials",
    "n_click_difference_levels",
    "empirical_bias_click_difference",
    "empirical_threshold_click_difference",
    "left_lapse_empirical",
    "right_lapse_empirical",
    "fit_status",
    "fit_bias_click_difference",
    "fit_scale_click_difference",
    "fit_threshold_click_difference",
    "fit_left_lapse",
    "fit_right_lapse",
]
AGGREGATE_KERNEL_SUMMARY_FIELDS = [
    "bin_index",
    "bin_start",
    "bin_end",
    "n_rats",
    "total_trials",
    "mean_choice_difference",
    "median_choice_difference",
    "min_choice_difference",
    "max_choice_difference",
    "mean_point_biserial_r",
    "mean_normalized_weight",
]


def download_human_clicks_mendeley_mat(
    path: Path = DEFAULT_HUMAN_CLICKS_RAW_MAT,
    *,
    url: str = MENDELEY_HUMAN_CLICKS_DOWNLOAD_URL,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "behavtaskatlas/0.1"})
    with urllib.request.urlopen(request) as response:
        content = response.read()
    path.write_bytes(content)
    return {
        "source_url": url,
        "dataset_url": MENDELEY_HUMAN_CLICKS_DATASET_URL,
        "output_path": str(path),
        "n_bytes": len(content),
        "sha256": file_sha256(path),
    }


def harmonize_brody_clicks_trial(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
    subject_id: str | None = None,
    dataset_id: str = BRODY_CLICKS_DATASET_ID,
    protocol_id: str = BRODY_CLICKS_PROTOCOL_ID,
) -> CanonicalTrial:
    missing = sorted(field for field in ["nL", "nR", "gr", "hh", "sd"] if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Brody clicks trial fields: {joined}")

    n_left = int(source["nL"])
    n_right = int(source["nR"])
    click_difference = n_right - n_left
    stimulus_duration = _optional_float(source.get("sd"))
    left_times = _float_list(source.get("left_click_times", []))
    right_times = _float_list(source.get("right_click_times", []))

    return CanonicalTrial(
        protocol_id=protocol_id,
        dataset_id=dataset_id,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="auditory",
        stimulus_value=float(click_difference),
        stimulus_units="right minus left clicks",
        stimulus_side=_evidence_side(click_difference),
        evidence_strength=abs(float(click_difference)),
        evidence_units="absolute click count difference",
        choice=_go_right_label(source["gr"]),
        correct=_optional_hit(source.get("hh")),
        response_time=None,
        response_time_origin=None,
        feedback=_feedback_label(source.get("hh")),
        prior_context=_optional_gamma(source.get("ga")),
        task_variables={
            "left_click_count": n_left,
            "right_click_count": n_right,
            "click_count_difference": click_difference,
            "stimulus_duration": stimulus_duration,
            "left_click_times": left_times,
            "right_click_times": right_times,
            "gamma": _optional_float(source.get("ga")),
            "reward_gamma": _optional_float(source.get("rg")),
            "task_type": source.get("task_type"),
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_human_clicks_trial(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
) -> CanonicalTrial:
    required = ["dur", "rt", "cdiff", "cans", "choice", "corr", "dbs", "pt", "session"]
    missing = sorted(field for field in required if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required human clicks trial fields: {joined}")

    response_time = _required_float(source["rt"], field="rt")
    scheduled_duration = _required_float(source["dur"], field="dur")
    source_cdiff = _required_int(source["cdiff"], field="cdiff")
    click_difference = -source_cdiff
    left_times_all = _float_list(source.get("left_click_times", []))
    right_times_all = _float_list(source.get("right_click_times", []))
    left_times = [time for time in left_times_all if time <= response_time]
    right_times = [time for time in right_times_all if time <= response_time]
    patient_id = _required_int(source["pt"], field="pt")
    source_session = _required_int(source["session"], field="session")

    return CanonicalTrial(
        protocol_id=HUMAN_CLICKS_PROTOCOL_ID,
        dataset_id=HUMAN_CLICKS_DATASET_ID,
        subject_id=f"patient-{patient_id:02d}",
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="auditory",
        stimulus_value=float(click_difference),
        stimulus_units="right minus left clicks at response",
        stimulus_side=_evidence_side(click_difference),
        evidence_strength=abs(float(click_difference)),
        evidence_units="absolute click count difference at response",
        choice=_human_left_is_one_choice_label(source["choice"]),
        correct=_optional_hit(source.get("corr")),
        response_time=response_time,
        response_time_origin="response time in seconds relative to trial start",
        feedback="none",
        prior_context=_dbs_context(source["dbs"]),
        block_id=f"patient-{patient_id:02d}-session-{source_session:02d}",
        task_variables={
            "patient": patient_id,
            "source_session": source_session,
            "dbs": _required_int(source["dbs"], field="dbs"),
            "dbs_label": _dbs_label(source["dbs"]),
            "left_click_count": len(left_times),
            "right_click_count": len(right_times),
            "click_count_difference": click_difference,
            "source_cdiff_left_minus_right": source_cdiff,
            "correct_answer": _human_left_is_one_choice_label(source["cans"]),
            "correct_answer_code": _required_int(source["cans"], field="cans"),
            "choice_code": _required_int(source["choice"], field="choice"),
            "stimulus_duration": response_time,
            "scheduled_stimulus_duration": scheduled_duration,
            "left_click_times": left_times,
            "right_click_times": right_times,
            "all_left_click_times": left_times_all,
            "all_right_click_times": right_times_all,
            "alpha": _optional_float(source.get("alpha")),
            "beta": _optional_float(source.get("beta")),
            "gamma": _optional_float(source.get("gamma")),
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_brody_clicks_trials(
    parsed: dict[str, Any],
    *,
    session_id: str,
    subject_id: str | None = None,
    task_type: str | None = None,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    n_trials = _parsed_length(parsed)
    if limit is not None:
        n_trials = min(n_trials, limit)
    return [
        harmonize_brody_clicks_trial(
            _parsed_trial_source(parsed, index, task_type=task_type),
            session_id=session_id,
            subject_id=subject_id,
            trial_index=index,
        )
        for index in range(n_trials)
    ]


def harmonize_human_clicks_trials(
    rows: list[dict[str, Any]],
    *,
    base_session_id: str = DEFAULT_HUMAN_CLICKS_SESSION_ID,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    if limit is not None:
        rows = rows[:limit]
    return [
        harmonize_human_clicks_trial(
            row,
            session_id=_human_clicks_session_id(row, base_session_id=base_session_id),
            trial_index=index,
        )
        for index, row in enumerate(rows)
    ]


def load_brody_clicks_mat(
    mat_file: Path,
    *,
    parsed_field: str = "parsed",
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    try:
        import scipy.io
    except ImportError as exc:
        raise RuntimeError(
            "Brody clicks ingestion requires scipy. Install it with `uv sync --extra clicks`."
        ) from exc

    try:
        loaded = scipy.io.loadmat(mat_file, squeeze_me=True, simplify_cells=True)
    except NotImplementedError as exc:
        raise RuntimeError(
            "This MATLAB file appears to require v7.3/HDF5 support. "
            "Add an h5py-backed loader before ingesting this file."
        ) from exc

    ratdata = loaded.get("ratdata")
    if not isinstance(ratdata, dict):
        raise ValueError("Expected MATLAB variable `ratdata` to load as a mapping")
    parsed = ratdata.get(parsed_field)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected ratdata.{parsed_field} to load as a mapping")

    subject_id = mat_file.stem
    trials = harmonize_brody_clicks_trials(
        parsed,
        session_id=f"{subject_id}-{parsed_field}",
        subject_id=subject_id,
        task_type=ratdata.get("task_type"),
        limit=limit,
    )
    details = {
        "source_file": str(mat_file),
        "source_file_name": mat_file.name,
        "source_file_sha256": file_sha256(mat_file),
        "parsed_field": parsed_field,
        "subject_id": subject_id,
        "task_type": ratdata.get("task_type"),
        "n_trials": len(trials),
    }
    return trials, details


def load_human_clicks_mendeley_mat(
    mat_file: Path,
    *,
    session_id: str = DEFAULT_HUMAN_CLICKS_SESSION_ID,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    try:
        import scipy.io
    except ImportError as exc:
        raise RuntimeError(
            "Human clicks ingestion requires scipy. Install it with `uv sync --extra clicks`."
        ) from exc

    loaded = scipy.io.loadmat(mat_file, squeeze_me=True, simplify_cells=True)
    data = loaded.get("data")
    if not isinstance(data, dict):
        raise ValueError("Expected MATLAB variable `data` to load as a mapping")

    rows, session_parameters = _human_clicks_rows(data)
    trials = harmonize_human_clicks_trials(rows, base_session_id=session_id, limit=limit)
    details = {
        "source_file": str(mat_file),
        "source_file_name": mat_file.name,
        "source_file_sha256": file_sha256(mat_file),
        "source_url": MENDELEY_HUMAN_CLICKS_DATASET_URL,
        "source_file_download_url": MENDELEY_HUMAN_CLICKS_DOWNLOAD_URL,
        "source_file_id": MENDELEY_HUMAN_CLICKS_FILE_ID,
        "mendeley_doi": "10.17632/3j86m7mjx2.1",
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "patient_sessions": sorted({trial.block_id for trial in trials if trial.block_id}),
        "dbs_contexts": sorted(
            {trial.prior_context for trial in trials if trial.prior_context}
        ),
        "session_parameters": session_parameters,
    }
    return trials, details


def analyze_brody_clicks(trials: list[CanonicalTrial]) -> dict[str, Any]:
    from behavtaskatlas.ibl import analyze_canonical_psychometric

    return analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.auditory-clicks.descriptive-psychometric",
        protocol_id=BRODY_CLICKS_PROTOCOL_ID,
        dataset_id=BRODY_CLICKS_DATASET_ID,
        report_title="Auditory Clicks Aggregate Report",
        stimulus_label="Signed click-count difference",
        stimulus_units="right minus left clicks",
        stimulus_metric_name="click_difference",
        caveats=[
            (
                "Empirical bias and threshold use linear interpolation over empirical "
                "p(right). Fitted values use a four-parameter logistic model over signed "
                "click-count difference."
            ),
            (
                "No-response trials are included in total trial counts but excluded from "
                "the p(right) denominator."
            ),
            (
                "This baseline analysis ignores within-trial click timing; click-time "
                "weighting should be a later slice-specific analysis."
            ),
        ],
    )


def analyze_human_clicks(trials: list[CanonicalTrial]) -> dict[str, Any]:
    from behavtaskatlas.ibl import analyze_canonical_psychometric

    return analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.human-auditory-clicks.descriptive-psychometric",
        protocol_id=HUMAN_CLICKS_PROTOCOL_ID,
        dataset_id=HUMAN_CLICKS_DATASET_ID,
        report_title="Human Auditory Clicks DBS Report",
        stimulus_label="Signed click-count difference",
        stimulus_units="right minus left clicks at response",
        stimulus_metric_name="click_difference",
        caveats=[
            (
                "The Mendeley dataset contains Parkinson's disease patient trials "
                "with DBS off/on labels, not a broad healthy-volunteer reference sample."
            ),
            (
                "The source `cdiff` field is left-minus-right clicks at response. "
                "The atlas canonical axis flips this to right-minus-left for "
                "cross-clicks consistency."
            ),
            (
                "Click-time kernels use click events up to the response time. The "
                "source also includes the pre-scheduled trial duration and clicks "
                "after response in task_variables for auditability."
            ),
        ],
    )


def analyze_brody_clicks_evidence_kernel(
    trials: list[CanonicalTrial],
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    return _analyze_clicks_evidence_kernel(
        trials,
        n_bins=n_bins,
        analysis_id="analysis.auditory-clicks.evidence-kernel",
        protocol_id=BRODY_CLICKS_PROTOCOL_ID,
        dataset_id=BRODY_CLICKS_DATASET_ID,
    )


def analyze_human_clicks_evidence_kernel(
    trials: list[CanonicalTrial],
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    return _analyze_clicks_evidence_kernel(
        trials,
        n_bins=n_bins,
        analysis_id="analysis.human-auditory-clicks.evidence-kernel",
        protocol_id=HUMAN_CLICKS_PROTOCOL_ID,
        dataset_id=HUMAN_CLICKS_DATASET_ID,
    )


def _analyze_clicks_evidence_kernel(
    trials: list[CanonicalTrial],
    *,
    n_bins: int,
    analysis_id: str,
    protocol_id: str,
    dataset_id: str,
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    examples = [_trial_bin_evidence(trial, n_bins=n_bins) for trial in trials]
    included = [example for example in examples if example is not None]
    rows = _evidence_kernel_rows(included, n_bins=n_bins)
    return {
        "analysis_id": analysis_id,
        "analysis_type": "choice_triggered_evidence_kernel",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": protocol_id,
        "dataset_id": dataset_id,
        "n_trials": len(trials),
        "n_analyzed_trials": len(included),
        "n_excluded_trials": len(trials) - len(included),
        "n_bins": n_bins,
        "time_axis": "normalized_stimulus_time",
        "feature": "right minus left click count per normalized time bin",
        "summary_rows": rows,
        "caveats": [
            (
                "This is a descriptive choice-triggered evidence kernel, not a full "
                "accumulation-model fit."
            ),
            (
                "Click times are normalized by each trial's stimulus duration, so bins "
                "compare relative rather than absolute stimulus time."
            ),
            "Only left and right response trials with click times and stimulus duration are used.",
        ],
    }


def write_evidence_kernel_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVIDENCE_KERNEL_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_clicks_batch_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLICKS_BATCH_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_brody_clicks_batch(batch_summary_path: Path) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    batch_rows = _read_csv_dicts(batch_summary_path)
    psychometric_rows: list[dict[str, Any]] = []
    kernel_rows_by_bin: dict[int, list[dict[str, Any]]] = {}
    rat_results: list[dict[str, Any]] = []
    task_types = set()
    gamma_contexts = set()

    for batch_row in batch_rows:
        if batch_row.get("task_type"):
            task_types.add(batch_row["task_type"])
        if batch_row.get("psychometric_prior_contexts"):
            gamma_contexts.update(
                context
                for context in batch_row["psychometric_prior_contexts"].split(";")
                if context
            )

        rat_result = _batch_rat_result_template(batch_row, batch_summary_path=batch_summary_path)
        if batch_row.get("status") != "ok":
            rat_result["status"] = "batch_error"
            rat_result["error"] = batch_row.get("error")
            rat_results.append(rat_result)
            continue

        output_dir = Path(rat_result["output_dir"])
        analysis_path = output_dir / "analysis_result.json"
        kernel_path = output_dir / "evidence_kernel_result.json"
        rat_result["analysis_result_path"] = str(analysis_path)
        rat_result["evidence_kernel_result_path"] = str(kernel_path)

        try:
            analysis_result = _read_json_dict(analysis_path)
            kernel_result = _read_json_dict(kernel_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            rat_result["status"] = "artifact_error"
            rat_result["error"] = str(exc)
            rat_results.append(rat_result)
            continue

        prior_results = analysis_result.get("prior_results", [])
        kernel_summary_rows = kernel_result.get("summary_rows", [])
        rat_result.update(
            {
                "status": "ok",
                "error": None,
                "n_psychometric_prior_contexts": len(prior_results),
                "n_kernel_rows": len(kernel_summary_rows),
                "n_kernel_analyzed_trials": kernel_result.get("n_analyzed_trials"),
                "n_kernel_excluded_trials": kernel_result.get("n_excluded_trials"),
            }
        )
        rat_results.append(rat_result)

        for prior_result in prior_results:
            context = prior_result.get("prior_context")
            if context:
                gamma_contexts.add(context)
            psychometric_rows.append(
                _aggregate_psychometric_row(
                    batch_row=batch_row,
                    prior_result=prior_result,
                )
            )

        for kernel_row in kernel_summary_rows:
            bin_index = _optional_int(kernel_row.get("bin_index"))
            if bin_index is None:
                continue
            kernel_rows_by_bin.setdefault(bin_index, []).append(kernel_row)

    kernel_summary = _aggregate_kernel_rows(kernel_rows_by_bin)
    n_batch_ok = sum(1 for row in batch_rows if row.get("status") == "ok")
    n_batch_failed = len(batch_rows) - n_batch_ok
    n_artifact_errors = sum(1 for row in rat_results if row.get("status") == "artifact_error")

    return {
        "analysis_id": "analysis.auditory-clicks.batch-aggregate",
        "analysis_type": "batch_aggregate",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": BRODY_CLICKS_PROTOCOL_ID,
        "dataset_id": BRODY_CLICKS_DATASET_ID,
        "batch_summary_path": str(batch_summary_path),
        "n_batch_rows": len(batch_rows),
        "n_ok": n_batch_ok,
        "n_failed": n_batch_failed,
        "n_artifact_errors": n_artifact_errors,
        "n_trials_total": sum(
            _optional_int(row.get("n_trials")) or 0
            for row in batch_rows
            if row.get("status") == "ok"
        ),
        "task_types": sorted(task_types),
        "gamma_contexts": sorted(gamma_contexts),
        "rat_results": rat_results,
        "psychometric_bias_rows": psychometric_rows,
        "kernel_summary_rows": kernel_summary,
        "caveats": [
            (
                "This aggregate reads previously generated local batch artifacts; it does "
                "not reprocess raw `.mat` files."
            ),
            (
                "Per-rat psychometric rows preserve each rat's gamma schedule rather than "
                "forcing a shared set of prior contexts."
            ),
            (
                "Kernel rows average descriptive choice-triggered evidence summaries across rats; "
                "they are not a hierarchical or multivariate click-weighting model."
            ),
        ],
    }


def concatenate_brody_clicks_trials(
    batch_summary_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    """Concatenate per-rat canonical trials CSVs into a slice-level
    trials.csv for downstream cross-rat extraction (e.g. extract-finding
    --by-subject). Reads each ok batch row's output_dir/trials.csv and
    writes them in-order to `out_path`.

    Returns a small summary dict (n_rows, n_subjects, missing_paths)
    suitable for embedding in aggregate provenance.
    """
    batch_rows = _read_csv_dicts(batch_summary_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames: list[str] | None = None
    n_rows = 0
    subjects: list[str] = []
    missing: list[str] = []

    with out_path.open("w", encoding="utf-8", newline="") as fout:
        writer: csv.DictWriter[str] | None = None
        for batch_row in batch_rows:
            if batch_row.get("status") != "ok":
                continue
            output_dir = _batch_output_dir(batch_row, batch_summary_path=batch_summary_path)
            trials_path = output_dir / "trials.csv"
            if not trials_path.exists():
                missing.append(str(trials_path))
                continue
            with trials_path.open(newline="", encoding="utf-8") as fin:
                reader = csv.DictReader(fin)
                if writer is None:
                    fieldnames = list(reader.fieldnames or [])
                    writer = csv.DictWriter(fout, fieldnames=fieldnames)
                    writer.writeheader()
                elif list(reader.fieldnames or []) != fieldnames:
                    raise ValueError(
                        f"trials.csv schema mismatch in {trials_path}: "
                        f"got {reader.fieldnames!r}, expected {fieldnames!r}"
                    )
                for row in reader:
                    writer.writerow(row)
                    n_rows += 1
            subject = (batch_row.get("subject_id") or "").strip()
            if subject and subject not in subjects:
                subjects.append(subject)

    return {
        "out_path": str(out_path),
        "n_rows": n_rows,
        "n_subjects": len(subjects),
        "subjects": subjects,
        "missing_paths": missing,
    }


def brody_clicks_aggregate_provenance_payload(
    *,
    result: dict[str, Any],
    batch_summary_path: Path,
    output_files: dict[str, str],
    trials_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": BRODY_CLICKS_PROTOCOL_ID,
        "dataset_id": BRODY_CLICKS_DATASET_ID,
        "source": {
            "batch_summary_path": str(batch_summary_path),
            "n_batch_rows": result.get("n_batch_rows"),
            "n_ok": result.get("n_ok"),
            "n_failed": result.get("n_failed"),
            "n_artifact_errors": result.get("n_artifact_errors"),
        },
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "batch_summary": str(batch_summary_path),
            "rat_artifacts": [
                {
                    "session_id": row.get("session_id"),
                    "subject_id": row.get("subject_id"),
                    "status": row.get("status"),
                    "output_dir": row.get("output_dir"),
                    "analysis_result_path": row.get("analysis_result_path"),
                    "evidence_kernel_result_path": row.get("evidence_kernel_result_path"),
                }
                for row in result.get("rat_results", [])
            ],
        },
        "outputs": output_files,
        "trials_summary": trials_summary,
        "caveats": [
            (
                "This is aggregate provenance over already generated per-rat artifacts; "
                "raw `.mat` provenance remains in each rat session directory."
            ),
            (
                "A clean aggregate provenance file requires rerunning the per-rat batch "
                "and aggregate commands from the same clean commit."
            ),
        ],
    }


def write_aggregate_psychometric_bias_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AGGREGATE_PSYCHOMETRIC_BIAS_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_aggregate_kernel_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AGGREGATE_KERNEL_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_aggregate_kernel_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(aggregate_kernel_svg(rows), encoding="utf-8")


def write_clicks_aggregate_report_html(
    path: Path,
    result: dict[str, Any],
    *,
    aggregate_kernel_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        clicks_aggregate_report_html(
            result,
            aggregate_kernel_svg_text=aggregate_kernel_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def write_evidence_kernel_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(evidence_kernel_svg(rows), encoding="utf-8")


def aggregate_kernel_svg(rows: list[dict[str, Any]]) -> str:
    width = 760
    height = 430
    left = 78
    right = 34
    top = 44
    bottom = 72
    plot_width = width - left - right
    plot_height = height - top - bottom
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="120">'
            '<text x="20" y="60">No aggregate evidence-kernel data available</text></svg>\n'
        )

    y_values = []
    for row in rows:
        for key in [
            "mean_choice_difference",
            "min_choice_difference",
            "max_choice_difference",
        ]:
            value = _optional_float(row.get(key))
            if value is not None:
                y_values.append(value)
    if not y_values:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="120">'
            '<text x="20" y="60">No aggregate evidence-kernel data available</text></svg>\n'
        )
    y_limit = max(max(abs(value) for value in y_values), 1.0)

    def x_scale(index: int) -> float:
        return left + (index + 0.5) * plot_width / len(rows)

    def y_scale(value: float) -> float:
        return top + (0.5 - value / (2.0 * y_limit)) * plot_height

    zero_y = y_scale(0.0)
    points = []
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="24" font-family="sans-serif" font-size="16" '
        'font-weight="700">Mean choice-triggered evidence across rats</text>',
        f'<line x1="{left}" y1="{zero_y:.1f}" x2="{left + plot_width}" '
        f'y2="{zero_y:.1f}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" '
        'stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 22}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14">Normalized stimulus time</text>',
        f'<text x="18" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 18 '
        f'{top + plot_height / 2})">Right-choice minus left-choice evidence</text>',
    ]

    for y_value in [-y_limit, -y_limit / 2.0, 0.0, y_limit / 2.0, y_limit]:
        y = y_scale(y_value)
        elements.append(
            f'<line x1="{left - 4}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" '
            'stroke="#ddd"/>'
        )
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{y_value:.2g}</text>'
        )

    for row in rows:
        index = int(row["bin_index"])
        mean_value = _optional_float(row.get("mean_choice_difference"))
        if mean_value is None:
            continue
        x = x_scale(index)
        y = y_scale(mean_value)
        points.append((x, y))
        min_value = _optional_float(row.get("min_choice_difference"))
        max_value = _optional_float(row.get("max_choice_difference"))
        if min_value is not None and max_value is not None:
            y_min = y_scale(min_value)
            y_max = y_scale(max_value)
            elements.append(
                f'<line x1="{x:.1f}" y1="{y_max:.1f}" x2="{x:.1f}" y2="{y_min:.1f}" '
                'stroke="#7a7a7a" stroke-width="1.3"/>'
            )
            elements.append(
                f'<line x1="{x - 5:.1f}" y1="{y_max:.1f}" x2="{x + 5:.1f}" '
                f'y2="{y_max:.1f}" stroke="#7a7a7a" stroke-width="1.3"/>'
            )
            elements.append(
                f'<line x1="{x - 5:.1f}" y1="{y_min:.1f}" x2="{x + 5:.1f}" '
                f'y2="{y_min:.1f}" stroke="#7a7a7a" stroke-width="1.3"/>'
            )
        elements.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#1f77b4"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{height - 48}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11">{float(row["bin_start"]):.1f}</text>'
        )

    if len(points) > 1:
        path = " ".join(
            f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}"
            for index, (x, y) in enumerate(points)
        )
        elements.append(f'<path d="{path}" fill="none" stroke="#1f77b4" stroke-width="2"/>')

    elements.append(
        f'<text x="{left + plot_width}" y="{height - 48}" text-anchor="middle" '
        'font-family="sans-serif" font-size="11">1.0</text>'
    )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def clicks_aggregate_report_html(
    result: dict[str, Any],
    *,
    aggregate_kernel_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    artifact_links = artifact_links or {}
    psychometric_rows = result.get("psychometric_bias_rows", [])
    kernel_rows = result.get("kernel_summary_rows", [])
    rat_results = result.get("rat_results", [])
    gamma_contexts = result.get("gamma_contexts", [])
    task_types = result.get("task_types", [])

    title = "Auditory Clicks Aggregate Report"
    metrics = [
        ("Rats ok", result.get("n_ok")),
        ("Batch failures", result.get("n_failed")),
        ("Artifact errors", result.get("n_artifact_errors")),
        ("Parsed trials", _format_integer(result.get("n_trials_total"))),
        ("Psychometric rows", _format_integer(len(psychometric_rows))),
        ("Kernel bins", _format_integer(len(kernel_rows))),
    ]
    kernel_svg = aggregate_kernel_svg_text or (
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="120">'
        '<text x="20" y="60">Aggregate kernel plot not available</text></svg>'
    )

    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title>",
        "<style>",
        _aggregate_report_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        f"<p class=\"eyebrow\">{escape(str(result.get('analysis_id', 'analysis')))}</p>",
        f"<h1>{escape(title)}</h1>",
        "<p class=\"lede\">Batch-level view of the Brody Lab Poisson clicks slice, "
        "generated from local aggregate artifacts rather than raw MATLAB files.</p>",
        "</header>",
        '<section class="metrics" aria-label="Aggregate metrics">',
    ]
    for label, value in metrics:
        html.extend(
            [
                '<div class="metric">',
                f"<span>{escape(label)}</span>",
                f"<strong>{escape(_format_cell(value))}</strong>",
                "</div>",
            ]
        )
    html.extend(
        [
            "</section>",
            '<section class="grid-two">',
            "<div>",
            "<h2>Coverage</h2>",
            _definition_list(
                [
                    ("Protocol", result.get("protocol_id")),
                    ("Dataset", result.get("dataset_id")),
                    ("Task types", ", ".join(str(item) for item in task_types)),
                    ("Gamma contexts", ", ".join(str(item) for item in gamma_contexts)),
                ]
            ),
            "</div>",
            "<div>",
            "<h2>Provenance</h2>",
            _definition_list(
                [
                    ("Generated", result.get("generated_at")),
                    ("Commit", result.get("behavtaskatlas_commit")),
                    ("Git dirty", result.get("behavtaskatlas_git_dirty")),
                    ("Batch summary", result.get("batch_summary_path")),
                ]
            ),
            "</div>",
            "</section>",
            '<section class="figure-section">',
            "<h2>Evidence Kernel</h2>",
            '<div class="figure-wrap">',
            kernel_svg,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Per-Rat Coverage</h2>",
            _html_table(
                rat_results,
                [
                    ("subject_id", "Rat"),
                    ("task_type", "Task"),
                    ("n_trials", "Trials"),
                    ("n_psychometric_prior_contexts", "Prior contexts"),
                    ("n_kernel_rows", "Kernel rows"),
                    ("n_kernel_excluded_trials", "Kernel exclusions"),
                    ("status", "Status"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Psychometric Bias By Rat And Gamma</h2>",
            _html_table(
                psychometric_rows,
                [
                    ("subject_id", "Rat"),
                    ("prior_context", "Gamma"),
                    ("n_trials", "Trials"),
                    ("n_click_difference_levels", "Levels"),
                    ("empirical_bias_click_difference", "Empirical bias"),
                    ("fit_bias_click_difference", "Fit bias"),
                    ("fit_threshold_click_difference", "Fit threshold"),
                    ("fit_status", "Fit status"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Aggregate Kernel Summary</h2>",
            _html_table(
                kernel_rows,
                [
                    ("bin_index", "Bin"),
                    ("bin_start", "Start"),
                    ("bin_end", "End"),
                    ("n_rats", "Rats"),
                    ("total_trials", "Trials"),
                    ("mean_choice_difference", "Mean choice difference"),
                    ("min_choice_difference", "Min"),
                    ("max_choice_difference", "Max"),
                    ("mean_point_biserial_r", "Mean r"),
                ],
            ),
            "</section>",
        ]
    )
    if artifact_links:
        html.extend(
            [
                "<section>",
                "<h2>Generated Files</h2>",
                '<ul class="artifact-list">',
            ]
        )
        for label, href in artifact_links.items():
            html.append(f'<li><a href="{escape(href, quote=True)}">{escape(label)}</a></li>')
        html.extend(["</ul>", "</section>"])

    caveats = result.get("caveats", [])
    if caveats:
        html.extend(["<section>", "<h2>Caveats</h2>", "<ul>"])
        html.extend(f"<li>{escape(str(caveat))}</li>" for caveat in caveats)
        html.extend(["</ul>", "</section>"])

    html.extend(["</main>", "</body>", "</html>"])
    return "\n".join(html) + "\n"


def write_clicks_session_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    kernel_result: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    evidence_kernel_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        clicks_session_report_html(
            analysis_result,
            kernel_result=kernel_result,
            provenance=provenance,
            psychometric_svg_text=psychometric_svg_text,
            evidence_kernel_svg_text=evidence_kernel_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def clicks_session_report_html(
    analysis_result: dict[str, Any],
    *,
    kernel_result: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    evidence_kernel_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    kernel_result = kernel_result or {}
    provenance = provenance or {}
    artifact_links = artifact_links or {}
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    title = str(analysis_result.get("report_title") or "Auditory Clicks Report")
    prior_results = analysis_result.get("prior_results", [])
    summary_rows = analysis_result.get("summary_rows", [])
    kernel_rows = kernel_result.get("summary_rows", [])
    subjects = source.get("subjects") if isinstance(source.get("subjects"), list) else []
    patient_sessions = (
        source.get("patient_sessions") if isinstance(source.get("patient_sessions"), list) else []
    )

    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title>",
        "<style>",
        _aggregate_report_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        f"<p class=\"eyebrow\">{escape(str(analysis_result.get('analysis_id', 'analysis')))}</p>",
        f"<h1>{escape(title)}</h1>",
        f"<p class=\"lede\">{escape(_clicks_session_report_lede(analysis_result))}</p>",
        "</header>",
        '<section class="metrics" aria-label="Session metrics">',
        _metric_html("Trials", analysis_result.get("n_trials")),
        _metric_html("Response trials", analysis_result.get("n_response_trials")),
        _metric_html("Subjects", len(subjects)),
        _metric_html("Patient sessions", len(patient_sessions)),
        _metric_html("Psychometric rows", len(summary_rows)),
        _metric_html("Kernel bins", len(kernel_rows)),
        "</section>",
        '<section class="grid-two">',
        "<div>",
        "<h2>Source</h2>",
        _definition_list(
            [
                ("Dataset", analysis_result.get("dataset_id")),
                ("Protocol", analysis_result.get("protocol_id")),
                ("Source DOI", source.get("mendeley_doi")),
                ("Source file", source.get("source_file_name")),
                ("Subjects", ", ".join(str(item) for item in subjects)),
                ("DBS contexts", ", ".join(str(item) for item in source.get("dbs_contexts", []))),
            ]
        ),
        "</div>",
        "<div>",
        "<h2>Provenance</h2>",
        _definition_list(
            [
                ("Generated", analysis_result.get("generated_at")),
                ("Commit", analysis_result.get("behavtaskatlas_commit")),
                ("Git dirty", analysis_result.get("behavtaskatlas_git_dirty")),
                ("File SHA256", source.get("source_file_sha256")),
                ("Response time", analysis_result.get("response_time_origin")),
            ]
        ),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Psychometric Summary</h2>",
        '<div class="figure-wrap">',
        psychometric_svg_text or _missing_svg("Psychometric plot not available"),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Evidence Kernel</h2>",
        '<div class="figure-wrap">',
        evidence_kernel_svg_text or _missing_svg("Evidence-kernel plot not available"),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Psychometric Fit</h2>",
        _html_table(
            _clicks_prior_report_rows(prior_results),
            [
                ("prior_context", "Context"),
                ("n_trials", "Trials"),
                ("n_response_trials", "Responses"),
                ("n_click_difference_levels", "Levels"),
                ("empirical_bias_click_difference", "Empirical bias"),
                ("empirical_threshold_click_difference", "Empirical threshold"),
                ("fit_bias_click_difference", "Fit bias"),
                ("fit_threshold_click_difference", "Fit threshold"),
                ("fit_status", "Fit status"),
            ],
        ),
        "</section>",
        "<section>",
        "<h2>Kernel Rows</h2>",
        _html_table(
            kernel_rows,
            [
                ("bin_index", "Bin"),
                ("bin_start", "Start"),
                ("bin_end", "End"),
                ("n_trials", "Trials"),
                ("choice_difference", "Choice difference"),
                ("point_biserial_r", "Point-biserial r"),
                ("normalized_weight", "Normalized weight"),
            ],
        ),
        "</section>",
    ]
    if artifact_links:
        html.extend(["<section>", "<h2>Generated Files</h2>", '<ul class="artifact-list">'])
        for label, href in artifact_links.items():
            html.append(f'<li><a href="{escape(href, quote=True)}">{escape(label)}</a></li>')
        html.extend(["</ul>", "</section>"])

    caveats = [*analysis_result.get("caveats", []), *kernel_result.get("caveats", [])]
    if caveats:
        html.extend(["<section>", "<h2>Caveats</h2>", "<ul>"])
        html.extend(f"<li>{escape(str(caveat))}</li>" for caveat in caveats)
        html.extend(["</ul>", "</section>"])

    html.extend(["</main>", "</body>", "</html>"])
    return "\n".join(html) + "\n"


def evidence_kernel_svg(rows: list[dict[str, Any]]) -> str:
    width = 720
    height = 420
    left = 72
    right = 28
    top = 34
    bottom = 68
    plot_width = width - left - right
    plot_height = height - top - bottom
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No evidence-kernel data available</text></svg>\n'
        )

    values = [
        float(row["choice_difference"])
        for row in rows
        if row["choice_difference"] is not None
    ]
    if not values:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No evidence-kernel data available</text></svg>\n'
        )
    y_limit = max(max(abs(value) for value in values), 1.0)

    def x_scale(index: int) -> float:
        return left + (index + 0.5) * plot_width / len(rows)

    def y_scale(value: float) -> float:
        return top + (0.5 - value / (2.0 * y_limit)) * plot_height

    zero_y = y_scale(0.0)
    bar_width = max(4.0, plot_width / len(rows) * 0.68)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{zero_y:.1f}" x2="{left + plot_width}" '
        f'y2="{zero_y:.1f}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" '
        'stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 20}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14">Normalized stimulus time</text>',
        f'<text x="18" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 18 '
        f'{top + plot_height / 2})">Right-choice minus left-choice evidence</text>',
    ]

    for y_value in [-y_limit, -y_limit / 2.0, 0.0, y_limit / 2.0, y_limit]:
        y = y_scale(y_value)
        elements.append(
            f'<line x1="{left - 4}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" '
            'stroke="#ddd"/>'
        )
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{y_value:.2g}</text>'
        )

    for row in rows:
        index = int(row["bin_index"])
        value = float(row["choice_difference"] or 0.0)
        x = x_scale(index)
        y = y_scale(value)
        top_y = min(y, zero_y)
        height_px = abs(zero_y - y)
        color = "#1f77b4" if value >= 0 else "#d62728"
        elements.append(
            f'<rect x="{x - bar_width / 2:.1f}" y="{top_y:.1f}" width="{bar_width:.1f}" '
            f'height="{height_px:.1f}" fill="{color}" fill-opacity="0.78"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{height - 46}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11">{float(row["bin_start"]):.1f}</text>'
        )

    elements.append(
        f'<text x="{left + plot_width}" y="{height - 46}" text-anchor="middle" '
        'font-family="sans-serif" font-size="11">1.0</text>'
    )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def brody_clicks_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": BRODY_CLICKS_PROTOCOL_ID,
        "dataset_id": BRODY_CLICKS_DATASET_ID,
        "source": {
            "zenodo_url": "https://zenodo.org/records/13352119",
            "doi": "10.5281/zenodo.13352119",
            **details,
        },
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "n_trials": len(trials),
        "source_fields": ["nL", "nR", "sd", "gr", "hh", "ga", "rg", "bt.left", "bt.right"],
        "outputs": output_files,
        "caveats": [
            "The full Zenodo archive is large and should remain in ignored local raw-data storage.",
            (
                "The archive uses ZIP64/Deflate64 compression; macOS unzip and "
                "Python zipfile may not extract it."
            ),
            "The parsed release excludes violations, frozen trials, and trials longer than 1 s.",
            "Day/session breaks are not identified in the parsed release.",
        ],
    }


def human_clicks_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": HUMAN_CLICKS_PROTOCOL_ID,
        "dataset_id": HUMAN_CLICKS_DATASET_ID,
        "source": {
            "mendeley_dataset_url": MENDELEY_HUMAN_CLICKS_DATASET_URL,
            "mendeley_file_download_url": MENDELEY_HUMAN_CLICKS_DOWNLOAD_URL,
            "mendeley_file_id": MENDELEY_HUMAN_CLICKS_FILE_ID,
            "expected_sha256": MENDELEY_HUMAN_CLICKS_SHA256,
            **details,
        },
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "n_trials": len(trials),
        "source_fields": [
            "dur",
            "rt",
            "cdiff",
            "cans",
            "choice",
            "corr",
            "dbs",
            "sesstime",
            "trialpar.ctl",
            "trialpar.ctr",
            "alpha",
            "beta",
            "gamma",
            "session",
            "pt",
        ],
        "outputs": output_files,
        "caveats": [
            (
                "The dataset is a Parkinson's disease patient DBS off/on dataset, "
                "so it should not be treated as a generic healthy-human benchmark."
            ),
            (
                "The source `cdiff` field is left-minus-right clicks at response; "
                "canonical trials use right-minus-left for consistency with the "
                "rat clicks slice."
            ),
        ],
    }


def _aggregate_report_css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #17212b;
  --muted: #5f6c76;
  --line: #d8dee4;
  --panel: #f6f8fa;
  --accent: #1464a5;
  --ok: #237a57;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: #ffffff;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  line-height: 1.45;
}
main {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 32px 0 48px;
}
header {
  padding-bottom: 22px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 3.4rem);
  line-height: 1.03;
}
h2 {
  margin: 0 0 14px;
  font-size: 1.15rem;
}
.lede {
  max-width: 760px;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 1.05rem;
}
section {
  margin-top: 28px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.metric {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: var(--panel);
}
.metric span {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}
.metric strong {
  display: block;
  margin-top: 4px;
  font-size: 1.45rem;
}
.grid-two {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}
dl {
  display: grid;
  grid-template-columns: minmax(120px, 0.34fr) 1fr;
  gap: 8px 14px;
  margin: 0;
}
dt {
  color: var(--muted);
  font-weight: 700;
}
dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
}
.figure-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
}
.figure-wrap svg {
  display: block;
  max-width: 100%;
  height: auto;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}
table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th,
td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--panel);
  color: #2f3b45;
  font-size: 0.76rem;
  text-transform: uppercase;
}
tbody tr:last-child td {
  border-bottom: 0;
}
.artifact-list {
  columns: 2;
  padding-left: 18px;
}
a {
  color: var(--accent);
}
@media (max-width: 720px) {
  main {
    width: min(100vw - 20px, 1180px);
    padding-top: 20px;
  }
  dl {
    grid-template-columns: 1fr;
  }
  .artifact-list {
    columns: 1;
  }
}
""".strip()


def _definition_list(rows: list[tuple[str, Any]]) -> str:
    parts = ["<dl>"]
    for label, value in rows:
        parts.append(f"<dt>{escape(label)}</dt>")
        parts.append(f"<dd>{escape(_format_cell(value))}</dd>")
    parts.append("</dl>")
    return "\n".join(parts)


def _metric_html(label: str, value: Any) -> str:
    return "\n".join(
        [
            '<div class="metric">',
            f"<span>{escape(label)}</span>",
            f"<strong>{escape(_format_cell(value))}</strong>",
            "</div>",
        ]
    )


def _html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="empty">No rows available.</p>'
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for _, label in columns:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        parts.append("<tr>")
        for key, _ in columns:
            parts.append(f"<td>{escape(_format_cell(row.get(key)))}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _clicks_session_report_lede(analysis_result: dict[str, Any]) -> str:
    if analysis_result.get("protocol_id") == HUMAN_CLICKS_PROTOCOL_ID:
        return (
            "Human Poisson-clicks slice generated from the Mendeley DBS off/on "
            "MATLAB file, with psychometrics split by DBS context and a "
            "response-window click-time evidence kernel."
        )
    return (
        "Auditory-clicks slice generated from canonical trial artifacts, with "
        "descriptive psychometrics and a click-time evidence kernel."
    )


def _clicks_prior_report_rows(prior_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for prior_result in prior_results:
        fit = prior_result.get("fit")
        if not isinstance(fit, dict):
            fit = {}
        rows.append(
            {
                "prior_context": prior_result.get("prior_context") or "all trials",
                "n_trials": prior_result.get("n_trials"),
                "n_response_trials": prior_result.get("n_response_trials"),
                "n_click_difference_levels": prior_result.get("n_click_difference_levels"),
                "empirical_bias_click_difference": prior_result.get(
                    "empirical_bias_click_difference"
                ),
                "empirical_threshold_click_difference": prior_result.get(
                    "empirical_threshold_click_difference"
                ),
                "fit_bias_click_difference": fit.get("bias_click_difference"),
                "fit_threshold_click_difference": fit.get("threshold_click_difference"),
                "fit_status": fit.get("status"),
            }
        )
    return rows


def _missing_svg(message: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        f'<text x="20" y="60">{escape(message)}</text></svg>'
    )


def _format_integer(value: Any) -> str:
    numeric = _optional_int(value)
    if numeric is None:
        return ""
    return f"{numeric:,}"


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    numeric = _optional_float(value)
    if numeric is not None:
        if numeric.is_integer():
            return f"{int(numeric):,}"
        return f"{numeric:.4g}"
    return str(value)


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json_dict(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return loaded


def _human_clicks_rows(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    required = [
        "dur",
        "rt",
        "cdiff",
        "cans",
        "choice",
        "corr",
        "dbs",
        "sesstime",
        "trialpar",
        "session",
        "pt",
    ]
    missing = sorted(field for field in required if field not in data)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required human clicks MATLAB fields: {joined}")

    n_trials = len(data["cdiff"])
    for field in required:
        actual = len(data[field])
        if actual != n_trials:
            raise ValueError(f"Field {field!r} has length {actual}, expected {n_trials}")

    session_parameters = _human_clicks_session_parameters(data, n_trials=n_trials)
    parameters_by_session = {
        (row["patient"], row["source_session"]): row for row in session_parameters
    }
    rows = []
    for index in range(n_trials):
        patient = _required_int(_index_value(data["pt"], index), field="pt")
        source_session = _required_int(_index_value(data["session"], index), field="session")
        trialpar = _index_value(data["trialpar"], index)
        if not isinstance(trialpar, dict):
            raise ValueError(f"Expected trialpar[{index}] to load as a mapping")
        row = {
            "dur": _index_value(data["dur"], index),
            "rt": _index_value(data["rt"], index),
            "cdiff": _index_value(data["cdiff"], index),
            "cans": _index_value(data["cans"], index),
            "choice": _index_value(data["choice"], index),
            "corr": _index_value(data["corr"], index),
            "dbs": _index_value(data["dbs"], index),
            "sesstime": _index_value(data["sesstime"], index),
            "session": source_session,
            "pt": patient,
            "left_click_times": _float_list(trialpar.get("ctl", [])),
            "right_click_times": _float_list(trialpar.get("ctr", [])),
        }
        parameters = parameters_by_session.get((patient, source_session), {})
        for field in ["alpha", "beta", "gamma"]:
            if field in parameters:
                row[field] = parameters[field]
        rows.append(row)
    return rows, session_parameters


def _human_clicks_session_parameters(
    data: dict[str, Any],
    *,
    n_trials: int,
) -> list[dict[str, Any]]:
    combos: list[tuple[int, int]] = []
    for index in range(n_trials):
        combo = (
            _required_int(_index_value(data["pt"], index), field="pt"),
            _required_int(_index_value(data["session"], index), field="session"),
        )
        if combo not in combos:
            combos.append(combo)

    rows = []
    for index, (patient, source_session) in enumerate(combos):
        row: dict[str, Any] = {
            "patient": patient,
            "source_session": source_session,
            "session_id": f"patient-{patient:02d}-session-{source_session:02d}",
        }
        for field in ["alpha", "beta", "gamma"]:
            values = data.get(field)
            if values is not None and len(values) == len(combos):
                row[field] = _optional_float(_index_value(values, index))
        rows.append(row)
    return rows


def _human_clicks_session_id(row: dict[str, Any], *, base_session_id: str) -> str:
    patient = _required_int(row["pt"], field="pt")
    source_session = _required_int(row["session"], field="session")
    return f"{base_session_id}-patient-{patient:02d}-session-{source_session:02d}"


def _batch_rat_result_template(
    batch_row: dict[str, Any],
    *,
    batch_summary_path: Path,
) -> dict[str, Any]:
    output_dir = _batch_output_dir(batch_row, batch_summary_path=batch_summary_path)
    return {
        "mat_file": batch_row.get("mat_file"),
        "session_id": batch_row.get("session_id"),
        "subject_id": batch_row.get("subject_id"),
        "task_type": batch_row.get("task_type"),
        "batch_status": batch_row.get("status"),
        "n_trials": _optional_int(batch_row.get("n_trials")),
        "output_dir": str(output_dir),
        "status": None,
        "error": None,
    }


def _batch_output_dir(batch_row: dict[str, Any], *, batch_summary_path: Path) -> Path:
    candidates = []
    if batch_row.get("output_dir"):
        output_dir = Path(batch_row["output_dir"])
        candidates.append(output_dir)
        if not output_dir.is_absolute():
            candidates.append(batch_summary_path.parent / output_dir)
    if batch_row.get("session_id"):
        candidates.append(batch_summary_path.parent / batch_row["session_id"])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else batch_summary_path.parent


def _aggregate_psychometric_row(
    *,
    batch_row: dict[str, Any],
    prior_result: dict[str, Any],
) -> dict[str, Any]:
    fit = prior_result.get("fit")
    if not isinstance(fit, dict):
        fit = {}
    return {
        "session_id": batch_row.get("session_id"),
        "subject_id": batch_row.get("subject_id"),
        "task_type": batch_row.get("task_type"),
        "prior_context": prior_result.get("prior_context"),
        "n_trials": prior_result.get("n_trials"),
        "n_response_trials": prior_result.get("n_response_trials"),
        "n_click_difference_levels": prior_result.get("n_click_difference_levels"),
        "empirical_bias_click_difference": prior_result.get(
            "empirical_bias_click_difference"
        ),
        "empirical_threshold_click_difference": prior_result.get(
            "empirical_threshold_click_difference"
        ),
        "left_lapse_empirical": prior_result.get("left_lapse_empirical"),
        "right_lapse_empirical": prior_result.get("right_lapse_empirical"),
        "fit_status": fit.get("status"),
        "fit_bias_click_difference": fit.get("bias_click_difference"),
        "fit_scale_click_difference": fit.get("scale_click_difference"),
        "fit_threshold_click_difference": fit.get("threshold_click_difference"),
        "fit_left_lapse": fit.get("left_lapse"),
        "fit_right_lapse": fit.get("right_lapse"),
    }


def _aggregate_kernel_rows(
    kernel_rows_by_bin: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for bin_index, bin_rows in sorted(kernel_rows_by_bin.items()):
        choice_differences = _finite_float_values(bin_rows, "choice_difference")
        point_biserial_values = _finite_float_values(bin_rows, "point_biserial_r")
        normalized_weights = _finite_float_values(bin_rows, "normalized_weight")
        rows.append(
            {
                "bin_index": bin_index,
                "bin_start": _mean_float(_finite_float_values(bin_rows, "bin_start")),
                "bin_end": _mean_float(_finite_float_values(bin_rows, "bin_end")),
                "n_rats": len(bin_rows),
                "total_trials": sum(_optional_int(row.get("n_trials")) or 0 for row in bin_rows),
                "mean_choice_difference": _mean_float(choice_differences),
                "median_choice_difference": _median_float(choice_differences),
                "min_choice_difference": min(choice_differences)
                if choice_differences
                else None,
                "max_choice_difference": max(choice_differences)
                if choice_differences
                else None,
                "mean_point_biserial_r": _mean_float(point_biserial_values),
                "mean_normalized_weight": _mean_float(normalized_weights),
            }
        )
    return rows


def _finite_float_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values = []
    for row in rows:
        value = _optional_float(row.get(key))
        if value is not None:
            values.append(value)
    return values


def _mean_float(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _median_float(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.median(values)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _trial_bin_evidence(
    trial: CanonicalTrial,
    *,
    n_bins: int,
) -> tuple[list[int], int] | None:
    if trial.choice not in {"left", "right"}:
        return None
    task_variables = trial.task_variables
    stimulus_duration = _optional_float(task_variables.get("stimulus_duration"))
    if stimulus_duration is None or stimulus_duration <= 0:
        return None

    bins = [0 for _ in range(n_bins)]
    for time_value in _float_list(task_variables.get("right_click_times", [])):
        bin_index = _time_bin_index(time_value, stimulus_duration, n_bins)
        if bin_index is not None:
            bins[bin_index] += 1
    for time_value in _float_list(task_variables.get("left_click_times", [])):
        bin_index = _time_bin_index(time_value, stimulus_duration, n_bins)
        if bin_index is not None:
            bins[bin_index] -= 1

    choice_code = 1 if trial.choice == "right" else 0
    return bins, choice_code


def _evidence_kernel_rows(
    examples: list[tuple[list[int], int]],
    *,
    n_bins: int,
) -> list[dict[str, Any]]:
    rows = []
    raw_weights = []
    for bin_index in range(n_bins):
        values = [bins[bin_index] for bins, _ in examples]
        right_values = [bins[bin_index] for bins, choice in examples if choice == 1]
        left_values = [bins[bin_index] for bins, choice in examples if choice == 0]
        right_mean = _mean(right_values)
        left_mean = _mean(left_values)
        choice_difference = (
            right_mean - left_mean if right_mean is not None and left_mean is not None else None
        )
        raw_weights.append(choice_difference or 0.0)
        rows.append(
            {
                "bin_index": bin_index,
                "bin_start": bin_index / n_bins,
                "bin_end": (bin_index + 1) / n_bins,
                "n_trials": len(values),
                "n_right_choice": len(right_values),
                "n_left_choice": len(left_values),
                "mean_signed_evidence": _mean(values),
                "mean_signed_evidence_right_choice": right_mean,
                "mean_signed_evidence_left_choice": left_mean,
                "choice_difference": choice_difference,
                "point_biserial_r": _point_biserial_r(values, [choice for _, choice in examples]),
                "normalized_weight": None,
            }
        )

    denominator = sum(abs(value) for value in raw_weights)
    for row, raw_weight in zip(rows, raw_weights, strict=True):
        row["normalized_weight"] = raw_weight / denominator if denominator else None
    return rows


def _time_bin_index(time_value: float, stimulus_duration: float, n_bins: int) -> int | None:
    if not math.isfinite(time_value) or time_value < 0.0 or time_value > stimulus_duration:
        return None
    normalized = time_value / stimulus_duration
    return min(int(normalized * n_bins), n_bins - 1)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _point_biserial_r(values: list[int], choices: list[int]) -> float | None:
    if len(values) != len(choices) or len(values) < 2:
        return None
    mean_x = sum(values) / len(values)
    mean_y = sum(choices) / len(choices)
    variance_x = sum((value - mean_x) ** 2 for value in values)
    variance_y = sum((choice - mean_y) ** 2 for choice in choices)
    if variance_x == 0.0 or variance_y == 0.0:
        return None
    covariance = sum(
        (value - mean_x) * (choice - mean_y)
        for value, choice in zip(values, choices, strict=True)
    )
    return covariance / math.sqrt(variance_x * variance_y)


def _parsed_trial_source(
    parsed: dict[str, Any],
    index: int,
    *,
    task_type: str | None,
) -> dict[str, Any]:
    source = {
        "nL": _index_value(parsed["nL"], index),
        "nR": _index_value(parsed["nR"], index),
        "sd": _index_value(parsed["sd"], index),
        "gr": _index_value(parsed["gr"], index),
        "hh": _index_value(parsed["hh"], index),
        "task_type": task_type,
    }
    for optional_field in ["ga", "rg"]:
        if optional_field in parsed:
            source[optional_field] = _index_value(parsed[optional_field], index)
    if "bt" in parsed:
        bup_times = _index_value(parsed["bt"], index)
        source["left_click_times"] = _extract_click_times(bup_times, "left")
        source["right_click_times"] = _extract_click_times(bup_times, "right")
    return source


def _parsed_length(parsed: dict[str, Any]) -> int:
    required = ["nL", "nR", "sd", "gr", "hh"]
    missing = sorted(field for field in required if field not in parsed)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Brody clicks parsed fields: {joined}")
    n_trials = len(parsed["nL"])
    for field in required:
        if len(parsed[field]) != n_trials:
            actual = len(parsed[field])
            raise ValueError(f"Field {field!r} has length {actual}, expected {n_trials}")
    return n_trials


def _extract_click_times(bup_times: Any, side: str) -> list[float]:
    if isinstance(bup_times, dict):
        return _float_list(bup_times.get(side, []))
    value = getattr(bup_times, side, [])
    return _float_list(value)


def _go_right_label(value: Any) -> str:
    if _as_float(value) == 1.0:
        return "right"
    if _as_float(value) == 0.0:
        return "left"
    return "unknown"


def _optional_hit(value: Any) -> bool | None:
    numeric = _as_float(value)
    if numeric == 1.0:
        return True
    if numeric == 0.0:
        return False
    return None


def _feedback_label(value: Any) -> str:
    hit = _optional_hit(value)
    if hit is True:
        return "reward"
    if hit is False:
        return "error"
    return "unknown"


def _evidence_side(click_difference: int) -> str:
    if click_difference > 0:
        return "right"
    if click_difference < 0:
        return "left"
    return "none"


def _human_left_is_one_choice_label(value: Any) -> str:
    numeric = _as_float(value)
    if numeric == 1.0:
        return "left"
    if numeric == 0.0:
        return "right"
    return "unknown"


def _dbs_label(value: Any) -> str:
    numeric = _as_float(value)
    if numeric == 1.0:
        return "on"
    if numeric == 0.0:
        return "off"
    return "unknown"


def _dbs_context(value: Any) -> str:
    return f"dbs={_dbs_label(value)}"


def _optional_gamma(value: Any) -> str | None:
    numeric = _optional_float(value)
    if numeric is None:
        return None
    return f"gamma={numeric:.3g}"


def _index_value(values: Any, index: int) -> Any:
    value = values[index]
    if hasattr(value, "item"):
        return value.item()
    return value


def _float_list(values: Any) -> list[float]:
    if values is None:
        return []
    try:
        iterator = iter(values)
    except TypeError:
        return [float(values)]
    return [float(value) for value in iterator]


def _optional_float(value: Any) -> float | None:
    numeric = _as_float(value)
    if numeric is None or math.isnan(numeric):
        return None
    return numeric


def _required_float(value: Any, *, field: str) -> float:
    numeric = _optional_float(value)
    if numeric is None:
        raise ValueError(f"Field {field} must be numeric, got {value!r}")
    return numeric


def _optional_int(value: Any) -> int | None:
    numeric = _optional_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _required_int(value: Any, *, field: str) -> int:
    numeric = _required_float(value, field=field)
    return int(numeric)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe_value(item) for item in value]
    numeric = _as_float(value)
    if numeric is not None and math.isfinite(numeric):
        return numeric
    if value is None:
        return None
    if isinstance(value, str | int | bool):
        return value
    return str(value)
