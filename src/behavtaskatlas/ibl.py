from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from subprocess import CalledProcessError, check_output
from typing import Any

from behavtaskatlas.models import CanonicalTrial

IBL_VISUAL_PROTOCOL_ID = "protocol.ibl-visual-decision-v1"
IBL_PUBLIC_BEHAVIOR_DATASET_ID = "dataset.ibl-public-behavior"
DEFAULT_IBL_EID = "ebce500b-c530-47de-8cb1-963c552703ea"
DEFAULT_DERIVED_DIR = Path("derived/ibl_visual_decision")

IBL_REQUIRED_TRIAL_FIELDS = {
    "contrastLeft",
    "contrastRight",
    "choice",
    "feedbackType",
    "response_times",
    "stimOn_times",
    "probabilityLeft",
}
IBL_TRIALS_TABLE = "_ibl_trials.table.pqt"

CANONICAL_TRIAL_CSV_FIELDS = [
    "protocol_id",
    "dataset_id",
    "subject_id",
    "session_id",
    "trial_index",
    "stimulus_modality",
    "stimulus_value",
    "stimulus_units",
    "stimulus_side",
    "evidence_strength",
    "evidence_units",
    "choice",
    "correct",
    "response_time",
    "response_time_origin",
    "feedback",
    "reward",
    "reward_units",
    "block_id",
    "prior_context",
    "training_stage",
    "task_variables_json",
    "source_json",
]

PSYCHOMETRIC_SUMMARY_FIELDS = [
    "prior_context",
    "stimulus_value",
    "n_trials",
    "n_response",
    "n_no_response",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "median_response_time",
]


def harmonize_ibl_visual_trial(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
    subject_id: str | None = None,
    dataset_id: str = IBL_PUBLIC_BEHAVIOR_DATASET_ID,
    protocol_id: str = IBL_VISUAL_PROTOCOL_ID,
) -> CanonicalTrial:
    missing = sorted(field for field in IBL_REQUIRED_TRIAL_FIELDS if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required IBL trial fields: {joined}")

    signed_contrast = signed_contrast_percent(source["contrastLeft"], source["contrastRight"])
    return CanonicalTrial(
        protocol_id=protocol_id,
        dataset_id=dataset_id,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_contrast,
        stimulus_units="percent contrast, signed left negative",
        stimulus_side=stimulus_side(source["contrastLeft"], source["contrastRight"]),
        evidence_strength=abs(signed_contrast) if signed_contrast is not None else None,
        evidence_units="percent contrast",
        choice=choice_label(source["choice"]),
        correct=correct_label(source["feedbackType"]),
        response_time=response_time_seconds(source["stimOn_times"], source["response_times"]),
        response_time_origin="response_times - stimOn_times",
        feedback=feedback_label(source["feedbackType"]),
        reward=source.get("rewardVolume"),
        reward_units="uL" if source.get("rewardVolume") is not None else None,
        prior_context=prior_context_label(source["probabilityLeft"]),
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_ibl_visual_trials(
    trials: Any,
    *,
    session_id: str,
    subject_id: str | None = None,
    dataset_id: str = IBL_PUBLIC_BEHAVIOR_DATASET_ID,
    protocol_id: str = IBL_VISUAL_PROTOCOL_ID,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    _validate_trials_object(trials)
    n_trials = len(trials["choice"])
    if limit is not None:
        n_trials = min(n_trials, limit)

    return [
        harmonize_ibl_visual_trial(
            _trial_source_row(trials, index),
            session_id=session_id,
            subject_id=subject_id,
            trial_index=index,
            dataset_id=dataset_id,
            protocol_id=protocol_id,
        )
        for index in range(n_trials)
    ]


def load_ibl_trials_from_openalyx(
    eid: str,
    *,
    cache_dir: Path | None = None,
    revision: str | None = None,
    base_url: str = "https://openalyx.internationalbrainlab.org",
    password: str = "international",
) -> tuple[Any, dict[str, Any]]:
    try:
        from one.api import ONE
    except ImportError as exc:
        raise RuntimeError(
            "IBL ingestion requires the optional ONE-api dependency. "
            "Install it with `uv sync --extra ibl`."
        ) from exc

    ONE.setup(base_url=base_url, silent=True)
    kwargs: dict[str, Any] = {"base_url": base_url, "password": password, "silent": True}
    if cache_dir is not None:
        kwargs["cache_dir"] = cache_dir
    one = ONE(**kwargs)
    details = dict(one.get_details(eid))
    revision_info = ibl_trials_revision_info(one, eid, requested_revision=revision)
    selected_revision = revision_info.get("selected_revision")
    trials = one.load_dataset(
        eid,
        IBL_TRIALS_TABLE,
        collection="alf",
        revision=selected_revision,
    )
    details["_behavtaskatlas_trials_revision"] = revision_info
    return trials, details


def ibl_trials_revision_info(
    one: Any,
    eid: str,
    *,
    requested_revision: str | None = None,
) -> dict[str, Any]:
    datasets = one.list_datasets(
        eid,
        filename=IBL_TRIALS_TABLE,
        collection="alf",
        details=True,
    )
    available = []
    if hasattr(datasets, "iterrows"):
        for dataset_id, row in datasets.iterrows():
            rel_path = str(row.get("rel_path", ""))
            available.append(
                {
                    "dataset_id": str(dataset_id),
                    "revision": _revision_from_rel_path(rel_path),
                    "rel_path": rel_path,
                    "file_size": _optional_int(row.get("file_size")),
                    "hash": _optional_string(row.get("hash")),
                    "default_revision": bool(row.get("default_revision", False)),
                    "qc": str(row.get("qc")) if row.get("qc") is not None else None,
                }
            )

    selected_revision = requested_revision
    if requested_revision is None:
        default_revisions = [item for item in available if item["default_revision"]]
        if default_revisions:
            selected_revision = default_revisions[0]["revision"]

    selected = next(
        (item for item in available if item["revision"] == selected_revision),
        None,
    )
    return {
        "requested_revision": requested_revision,
        "selected_revision": selected_revision,
        "selected": selected,
        "available": available,
    }


def write_canonical_trials_csv(path: Path, trials: list[CanonicalTrial]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_TRIAL_CSV_FIELDS)
        writer.writeheader()
        for trial in trials:
            row = trial.model_dump(mode="json")
            source = row.pop("source")
            task_variables = row.pop("task_variables")
            row["task_variables_json"] = json.dumps(task_variables, sort_keys=True)
            row["source_json"] = json.dumps(source, sort_keys=True)
            writer.writerow(row)


def load_canonical_trials_csv(path: Path) -> list[CanonicalTrial]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [_canonical_trial_from_csv_row(row) for row in csv.DictReader(handle)]


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PSYCHOMETRIC_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def summarize_canonical_trials(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str | None, float | None], list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        grouped[(trial.prior_context, trial.stimulus_value)].append(trial)

    rows: list[dict[str, Any]] = []
    for (prior_context, stimulus_value), group in sorted(
        grouped.items(), key=lambda item: (item[0][0] or "", _none_safe_float(item[0][1]))
    ):
        response_trials = [trial for trial in group if trial.choice != "no-response"]
        right = sum(1 for trial in group if trial.choice == "right")
        correct_trials = [trial for trial in group if trial.correct is not None]
        correct = sum(1 for trial in correct_trials if trial.correct)
        response_times = [trial.response_time for trial in group if trial.response_time is not None]
        rows.append(
            {
                "prior_context": prior_context,
                "stimulus_value": stimulus_value,
                "n_trials": len(group),
                "n_response": len(response_trials),
                "n_no_response": len(group) - len(response_trials),
                "n_right": right,
                "p_right": _safe_ratio(right, len(response_trials)),
                "n_correct": correct,
                "p_correct": _safe_ratio(correct, len(correct_trials)),
                "median_response_time": statistics.median(response_times)
                if response_times
                else None,
            }
        )
    return rows


def analyze_canonical_psychometric(
    trials: list[CanonicalTrial],
    *,
    analysis_id: str,
    protocol_id: str,
    dataset_id: str,
    stimulus_label: str,
    stimulus_units: str | None,
    stimulus_metric_name: str,
    caveats: list[str],
) -> dict[str, Any]:
    summary_rows = summarize_canonical_trials(trials)
    by_prior: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        by_prior[row["prior_context"]].append(row)

    prior_results = []
    for prior_context, rows in sorted(by_prior.items(), key=lambda item: item[0] or ""):
        sorted_rows = sorted(rows, key=lambda row: _none_safe_float(row["stimulus_value"]))
        p25 = _interpolate_crossing(sorted_rows, 0.25)
        p50 = _interpolate_crossing(sorted_rows, 0.5)
        p75 = _interpolate_crossing(sorted_rows, 0.75)
        min_row = sorted_rows[0] if sorted_rows else None
        max_row = sorted_rows[-1] if sorted_rows else None
        fit = fit_psychometric_rows(sorted_rows, stimulus_metric_name=stimulus_metric_name)
        prior_results.append(
            {
                "prior_context": prior_context,
                "n_trials": sum(int(row["n_trials"]) for row in sorted_rows),
                "n_response_trials": sum(int(row["n_response"]) for row in sorted_rows),
                "n_stimulus_levels": len(sorted_rows),
                f"n_{stimulus_metric_name}_levels": len(sorted_rows),
                "empirical_bias": p50,
                f"empirical_bias_{stimulus_metric_name}": p50,
                "empirical_threshold": ((p75 - p25) / 2.0)
                if p25 is not None and p75 is not None
                else None,
                f"empirical_threshold_{stimulus_metric_name}": ((p75 - p25) / 2.0)
                if p25 is not None and p75 is not None
                else None,
                "left_lapse_empirical": min_row["p_right"] if min_row else None,
                "right_lapse_empirical": (1.0 - max_row["p_right"]) if max_row else None,
                "fit": fit,
            }
        )

    return {
        "analysis_id": analysis_id,
        "analysis_type": "descriptive_psychometric",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": protocol_id,
        "dataset_id": dataset_id,
        "n_trials": len(trials),
        "n_response_trials": sum(1 for trial in trials if trial.choice != "no-response"),
        "n_no_response_trials": sum(1 for trial in trials if trial.choice == "no-response"),
        "response_time_origin": _common_value(
            [trial.response_time_origin for trial in trials if trial.response_time_origin]
        ),
        "stimulus_label": stimulus_label,
        "stimulus_units": stimulus_units,
        "stimulus_metric_name": stimulus_metric_name,
        "summary_rows": summary_rows,
        "prior_results": prior_results,
        "caveats": caveats,
    }


def analyze_ibl_visual_decision(trials: list[CanonicalTrial]) -> dict[str, Any]:
    return analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.ibl-visual-decision.descriptive-psychometric",
        protocol_id=IBL_VISUAL_PROTOCOL_ID,
        dataset_id=IBL_PUBLIC_BEHAVIOR_DATASET_ID,
        stimulus_label="Signed contrast",
        stimulus_units="percent contrast, signed right positive",
        stimulus_metric_name="contrast",
        caveats=[
            (
                "Empirical bias and threshold use linear interpolation over empirical "
                "p(right). Fitted values use a four-parameter logistic model, not the "
                "full IBL psychofit implementation."
            ),
            (
                "No-response trials are included in total trial counts but excluded from "
                "the p(right) denominator."
            ),
        ],
    )


def fit_psychometric_rows(
    rows: list[dict[str, Any]],
    *,
    stimulus_metric_name: str = "contrast",
) -> dict[str, Any]:
    points = [
        (
            float(row["stimulus_value"]),
            int(row["n_right"]),
            int(row["n_response"]),
        )
        for row in rows
        if row["stimulus_value"] is not None and int(row["n_response"]) > 0
    ]
    if len(points) < 4:
        return {
            "status": "insufficient_data",
            "method": "four_parameter_logistic_binomial_mle",
            "n_points": len(points),
        }

    initial = _initial_psychometric_params(rows)
    bounds = [(-100.0, 100.0), (0.5, 200.0), (0.0, 0.4), (0.0, 0.4)]

    try:
        from scipy.optimize import minimize

        result = minimize(
            lambda params: _psychometric_negative_log_likelihood(points, params),
            initial,
            method="L-BFGS-B",
            bounds=bounds,
        )
        params = result.x.tolist()
        optimizer = "scipy.optimize.minimize"
        success = bool(result.success)
        nll = float(result.fun)
    except ImportError:
        params, nll = _grid_search_psychometric(points, initial)
        optimizer = "grid_search_fallback"
        success = True

    bias, scale, left_lapse, right_lapse = [float(value) for value in params]
    return {
        "status": "ok" if success else "optimizer_failed",
        "method": "four_parameter_logistic_binomial_mle",
        "optimizer": optimizer,
        "n_points": len(points),
        "n_response_trials": sum(n_response for _, _, n_response in points),
        "negative_log_likelihood": nll,
        f"bias_{stimulus_metric_name}": bias,
        f"scale_{stimulus_metric_name}": scale,
        f"threshold_{stimulus_metric_name}": scale * math.log(3.0),
        "left_lapse": left_lapse,
        "right_lapse": right_lapse,
    }


def psychometric_probability(
    x_value: float,
    bias: float,
    scale: float,
    left_lapse: float,
    right_lapse: float,
) -> float:
    exponent = max(min(-(x_value - bias) / scale, 60.0), -60.0)
    logistic = 1.0 / (1.0 + math.exp(exponent))
    return left_lapse + (1.0 - left_lapse - right_lapse) * logistic


def write_analysis_json(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")


def write_psychometric_svg(
    path: Path,
    summary_rows: list[dict[str, Any]],
    *,
    x_axis_label: str = "Signed contrast (%; right positive)",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(psychometric_svg(summary_rows, x_axis_label=x_axis_label), encoding="utf-8")


def psychometric_svg(
    summary_rows: list[dict[str, Any]],
    *,
    x_axis_label: str = "Signed contrast (%; right positive)",
) -> str:
    width = 720
    height = 420
    left = 72
    right = 28
    top = 30
    bottom = 62
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [
        float(row["stimulus_value"])
        for row in summary_rows
        if row["stimulus_value"] is not None
    ]
    if not values:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No psychometric data available</text></svg>\n'
        )

    x_min = min(values)
    x_max = max(values)
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def y_scale(value: float) -> float:
        return top + (1.0 - value) * plot_height

    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e"]
    by_prior: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        by_prior[str(row["prior_context"])].append(row)

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" '
        f'stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 18}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="14">{escape(x_axis_label)}</text>',
        f'<text x="18" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 18 '
        f'{top + plot_height / 2})">P(right)</text>',
    ]

    for y_value in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = y_scale(y_value)
        elements.append(
            f'<line x1="{left - 4}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" '
            'stroke="#ddd"/>'
        )
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{y_value:.2g}</text>'
        )

    for x_value in _axis_tick_values(x_min, x_max):
        x = x_scale(x_value)
        elements.append(
            f'<line x1="{x:.1f}" y1="{top + plot_height}" x2="{x:.1f}" '
            f'y2="{top + plot_height + 4}" stroke="#222"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="10">{x_value:g}</text>'
        )

    for index, (prior_context, rows) in enumerate(sorted(by_prior.items())):
        color = colors[index % len(colors)]
        points = []
        for row in sorted(rows, key=lambda item: _none_safe_float(item["stimulus_value"])):
            if row["stimulus_value"] is None or row["p_right"] is None:
                continue
            x = x_scale(float(row["stimulus_value"]))
            y = y_scale(float(row["p_right"]))
            points.append((x, y, int(row["n_trials"])))
        if not points:
            continue
        point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        elements.append(
            f'<polyline points="{point_attr}" fill="none" stroke="{color}" '
            'stroke-width="2"/>'
        )
        for x, y, n_trials in points:
            radius = 3.0 + min(n_trials, 50) / 25.0
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" '
                'fill-opacity="0.75"/>'
            )
        legend_y = top + 18 + index * 20
        elements.append(
            f'<line x1="{left + 12}" y1="{legend_y}" x2="{left + 36}" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2"/>'
        )
        elements.append(
            f'<text x="{left + 44}" y="{legend_y + 4}" font-family="sans-serif" '
            f'font-size="12">{escape(prior_context)}</text>'
        )

    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def _axis_tick_values(x_min: float, x_max: float, max_ticks: int = 9) -> list[float]:
    if x_min == x_max:
        return [x_min]
    span = x_max - x_min
    raw_step = span / max(max_ticks - 1, 1)
    magnitude = 10.0 ** math.floor(math.log10(raw_step))
    step = next(
        candidate * magnitude
        for candidate in [1.0, 2.0, 5.0, 10.0]
        if candidate * magnitude >= raw_step
    )
    start = math.ceil(x_min / step) * step
    ticks = []
    value = start
    while value <= x_max + step * 1e-9:
        ticks.append(0.0 if abs(value) < step * 1e-9 else value)
        value += step
    if x_min < 0.0 < x_max and all(abs(tick) > step * 1e-9 for tick in ticks):
        ticks.append(0.0)
    return sorted(ticks)


def provenance_payload(
    *,
    eid: str,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
    source_revision_note: str | None = None,
) -> dict[str, Any]:
    revision_info = details.get("_behavtaskatlas_trials_revision")
    return {
        "eid": eid,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "one_api_version": installed_package_version("ONE-api"),
        "protocol_id": IBL_VISUAL_PROTOCOL_ID,
        "dataset_id": IBL_PUBLIC_BEHAVIOR_DATASET_ID,
        "source": {
            "base_url": "https://openalyx.internationalbrainlab.org",
            "session_url": details.get("url"),
            "subject": details.get("subject"),
            "lab": details.get("lab"),
            "start_time": details.get("start_time"),
            "task_protocol": details.get("task_protocol"),
            "revision_note": source_revision_note,
            "revision": revision_info,
        },
        "source_fields": sorted(IBL_REQUIRED_TRIAL_FIELDS | {"rewardVolume"}),
        "response_time_origin": "response_times - stimOn_times",
        "n_trials": len(trials),
        "exclusions": {
            "missing_stimulus": sum(1 for trial in trials if trial.stimulus_value is None),
            "no_response": sum(1 for trial in trials if trial.choice == "no-response"),
            "unknown_choice": sum(1 for trial in trials if trial.choice == "unknown"),
            "missing_response_time": sum(1 for trial in trials if trial.response_time is None),
            "unknown_feedback": sum(1 for trial in trials if trial.feedback == "unknown"),
        },
        "outputs": output_files,
        "caveats": [
            (
                "Generated artifacts are ignored by git until dataset licensing and release "
                "policy are confirmed."
            ),
            (
                "The selected IBL trials table revision is recorded; related non-table trial "
                "arrays are not used by this slice."
            ),
        ],
    }


def write_provenance_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def installed_package_version(package_name: str) -> str | None:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


def current_git_commit() -> str | None:
    try:
        return (
            check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
            .strip()
            .splitlines()[0]
        )
    except (CalledProcessError, FileNotFoundError, IndexError):
        return None


def current_git_dirty() -> bool | None:
    try:
        return bool(check_output(["git", "status", "--porcelain"], text=True).strip())
    except (CalledProcessError, FileNotFoundError):
        return None


def signed_contrast_percent(contrast_left: Any, contrast_right: Any) -> float | None:
    if _is_finite_number(contrast_right):
        return float(contrast_right) * 100.0
    if _is_finite_number(contrast_left):
        return -float(contrast_left) * 100.0
    return None


def stimulus_side(contrast_left: Any, contrast_right: Any) -> str:
    if _is_finite_number(contrast_right):
        return "right"
    if _is_finite_number(contrast_left):
        return "left"
    return "unknown"


def choice_label(choice: Any) -> str:
    if choice == 1:
        return "left"
    if choice == -1:
        return "right"
    if choice == 0:
        return "no-response"
    return "unknown"


def correct_label(feedback_type: Any) -> bool | None:
    if feedback_type == 1:
        return True
    if feedback_type == -1:
        return False
    return None


def feedback_label(feedback_type: Any) -> str:
    if feedback_type == 1:
        return "reward"
    if feedback_type == -1:
        return "error"
    if feedback_type == 0:
        return "none"
    return "unknown"


def response_time_seconds(stim_on_time: Any, response_time: Any) -> float | None:
    if not (_is_finite_number(stim_on_time) and _is_finite_number(response_time)):
        return None
    return float(response_time) - float(stim_on_time)


def prior_context_label(probability_left: Any) -> str | None:
    if not _is_finite_number(probability_left):
        return None
    return f"p_left={float(probability_left):.3g}"


def _is_finite_number(value: Any) -> bool:
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _json_safe_value(value: Any) -> Any:
    if _is_finite_number(value):
        return float(value)
    if value is None:
        return None
    if isinstance(value, str | int | bool):
        return value
    return str(value)


def _validate_trials_object(trials: Any) -> None:
    missing = sorted(field for field in IBL_REQUIRED_TRIAL_FIELDS if field not in trials)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required IBL trials fields: {joined}")
    n_trials = len(trials["choice"])
    for field in IBL_REQUIRED_TRIAL_FIELDS:
        if len(trials[field]) != n_trials:
            actual = len(trials[field])
            raise ValueError(f"Field {field!r} has length {actual}, expected {n_trials}")


def _trial_source_row(trials: Any, index: int) -> dict[str, Any]:
    row = {}
    for field in sorted(set(IBL_REQUIRED_TRIAL_FIELDS) | {"rewardVolume"}):
        if field in trials:
            row[field] = _index_value(trials[field], index)
    return row


def _index_value(values: Any, index: int) -> Any:
    value = values[index]
    if hasattr(value, "item"):
        return value.item()
    return value


def _revision_from_rel_path(rel_path: str) -> str | None:
    match = re.search(r"#([^#]+)#", rel_path)
    if match:
        return match.group(1)
    return None


def _canonical_trial_from_csv_row(row: dict[str, str]) -> CanonicalTrial:
    source_json = row.pop("source_json", "{}") or "{}"
    return CanonicalTrial(
        protocol_id=row["protocol_id"],
        dataset_id=_optional_string(row.get("dataset_id")),
        subject_id=_optional_string(row.get("subject_id")),
        session_id=row["session_id"],
        trial_index=int(row["trial_index"]),
        stimulus_modality=row["stimulus_modality"],
        stimulus_value=_optional_float(row.get("stimulus_value")),
        stimulus_units=_optional_string(row.get("stimulus_units")),
        stimulus_side=row.get("stimulus_side") or "unknown",
        evidence_strength=_optional_float(row.get("evidence_strength")),
        evidence_units=_optional_string(row.get("evidence_units")),
        choice=row["choice"],
        correct=_optional_bool(row.get("correct")),
        response_time=_optional_float(row.get("response_time")),
        response_time_origin=_optional_string(row.get("response_time_origin")),
        feedback=row.get("feedback") or "unknown",
        reward=_optional_float(row.get("reward")),
        reward_units=_optional_string(row.get("reward_units")),
        block_id=_optional_string(row.get("block_id")),
        prior_context=_optional_string(row.get("prior_context")),
        training_stage=_optional_string(row.get("training_stage")),
        task_variables=json.loads(row.pop("task_variables_json", "{}") or "{}"),
        source=json.loads(source_json),
    )


def _interpolate_crossing(rows: list[dict[str, Any]], target: float) -> float | None:
    points = [
        (float(row["stimulus_value"]), float(row["p_right"]))
        for row in rows
        if row["stimulus_value"] is not None and row["p_right"] is not None
    ]
    points.sort()
    for x_value, p_right in points:
        if p_right == target:
            return x_value
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if y0 == y1:
            continue
        lower = min(y0, y1)
        upper = max(y0, y1)
        if lower <= target <= upper:
            fraction = (target - y0) / (y1 - y0)
            return x0 + fraction * (x1 - x0)
    return None


def _initial_psychometric_params(rows: list[dict[str, Any]]) -> list[float]:
    p50 = _interpolate_crossing(rows, 0.5)
    sorted_rows = sorted(rows, key=lambda row: _none_safe_float(row["stimulus_value"]))
    min_row = sorted_rows[0]
    max_row = sorted_rows[-1]
    left_lapse = _clip(float(min_row["p_right"] or 0.0), 0.0, 0.2)
    right_lapse = _clip(1.0 - float(max_row["p_right"] or 1.0), 0.0, 0.2)
    return [p50 if p50 is not None else 0.0, 20.0, left_lapse, right_lapse]


def _psychometric_negative_log_likelihood(
    points: list[tuple[float, int, int]],
    params: list[float] | tuple[float, float, float, float],
) -> float:
    bias, scale, left_lapse, right_lapse = [float(value) for value in params]
    if scale <= 0 or left_lapse < 0 or right_lapse < 0 or left_lapse + right_lapse >= 1:
        return float("inf")
    nll = 0.0
    for x_value, n_right, n_response in points:
        p_right = _clip(
            psychometric_probability(x_value, bias, scale, left_lapse, right_lapse),
            1e-8,
            1.0 - 1e-8,
        )
        nll -= n_right * math.log(p_right) + (n_response - n_right) * math.log(1.0 - p_right)
    return nll


def _grid_search_psychometric(
    points: list[tuple[float, int, int]],
    initial: list[float],
) -> tuple[list[float], float]:
    bias_candidates = sorted(
        set([-100.0, -50.0, -25.0, -12.5, -6.25, 0.0, 6.25, 12.5, 25.0, 50.0, 100.0])
        | {round(initial[0], 6)}
    )
    scale_candidates = [5.0, 10.0, 20.0, 40.0, 80.0]
    lapse_candidates = [0.0, 0.025, 0.05, 0.1, 0.2]
    best_params = initial
    best_nll = float("inf")
    for bias in bias_candidates:
        for scale in scale_candidates:
            for left_lapse in lapse_candidates:
                for right_lapse in lapse_candidates:
                    params = [bias, scale, left_lapse, right_lapse]
                    nll = _psychometric_negative_log_likelihood(points, params)
                    if nll < best_nll:
                        best_params = params
                        best_nll = nll
    return best_params, best_nll


def _common_value(values: list[str]) -> str | None:
    unique_values = sorted(set(values))
    if len(unique_values) == 1:
        return unique_values[0]
    if unique_values:
        return "mixed"
    return None


def _optional_string(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        if math.isnan(float(value)):
            return None
    except (TypeError, ValueError):
        pass
    return int(value)


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"Cannot parse boolean value {value!r}")


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _none_safe_float(value: float | None) -> float:
    if value is None:
        return float("inf")
    return value


def _clip(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)
