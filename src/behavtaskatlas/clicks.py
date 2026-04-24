from __future__ import annotations

import csv
import hashlib
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from behavtaskatlas.models import CanonicalTrial

BRODY_CLICKS_PROTOCOL_ID = "protocol.poisson-clicks-evidence-accumulation"
BRODY_CLICKS_DATASET_ID = "dataset.brody-lab-poisson-clicks-2009-2024"
DEFAULT_CLICKS_DERIVED_DIR = Path("derived/auditory_clicks")
DEFAULT_CLICKS_SESSION_ID = "B075-parsed"
CLICKS_PSYCHOMETRIC_X_AXIS_LABEL = "Signed click-count difference (right minus left clicks)"
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


def analyze_brody_clicks(trials: list[CanonicalTrial]) -> dict[str, Any]:
    from behavtaskatlas.ibl import analyze_canonical_psychometric

    return analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.auditory-clicks.descriptive-psychometric",
        protocol_id=BRODY_CLICKS_PROTOCOL_ID,
        dataset_id=BRODY_CLICKS_DATASET_ID,
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


def analyze_brody_clicks_evidence_kernel(
    trials: list[CanonicalTrial],
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    examples = [_trial_bin_evidence(trial, n_bins=n_bins) for trial in trials]
    included = [example for example in examples if example is not None]
    rows = _evidence_kernel_rows(included, n_bins=n_bins)
    return {
        "analysis_id": "analysis.auditory-clicks.evidence-kernel",
        "analysis_type": "choice_triggered_evidence_kernel",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": BRODY_CLICKS_PROTOCOL_ID,
        "dataset_id": BRODY_CLICKS_DATASET_ID,
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


def write_evidence_kernel_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(evidence_kernel_svg(rows), encoding="utf-8")


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


def _mean(values: list[int]) -> float | None:
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
