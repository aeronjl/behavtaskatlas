from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from subprocess import CalledProcessError, check_output
from typing import Any

from behavtaskatlas.models import CanonicalTrial

IBL_VISUAL_PROTOCOL_ID = "protocol.ibl-visual-decision-v1"
IBL_PUBLIC_BEHAVIOR_DATASET_ID = "dataset.ibl-public-behavior"
DEFAULT_IBL_EID = "ebce500b-c530-47de-8cb1-963c552703ea"

IBL_REQUIRED_TRIAL_FIELDS = {
    "contrastLeft",
    "contrastRight",
    "choice",
    "feedbackType",
    "response_times",
    "stimOn_times",
    "probabilityLeft",
}


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
    trials = one.load_object(eid, "trials", collection="alf")
    return trials, details


def write_canonical_trials_csv(path: Path, trials: list[CanonicalTrial]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
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
        "source_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for trial in trials:
            row = trial.model_dump(mode="json")
            source = row.pop("source")
            row["source_json"] = json.dumps(source, sort_keys=True)
            writer.writerow(row)


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "prior_context",
        "stimulus_value",
        "n_trials",
        "n_right",
        "p_right",
        "n_correct",
        "p_correct",
        "median_response_time",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
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
        right = sum(1 for trial in group if trial.choice == "right")
        correct_trials = [trial for trial in group if trial.correct is not None]
        correct = sum(1 for trial in correct_trials if trial.correct)
        response_times = [trial.response_time for trial in group if trial.response_time is not None]
        rows.append(
            {
                "prior_context": prior_context,
                "stimulus_value": stimulus_value,
                "n_trials": len(group),
                "n_right": right,
                "p_right": _safe_ratio(right, len(group)),
                "n_correct": correct,
                "p_correct": _safe_ratio(correct, len(correct_trials)),
                "median_response_time": statistics.median(response_times)
                if response_times
                else None,
            }
        )
    return rows


def provenance_payload(
    *,
    eid: str,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
    source_revision_note: str | None = None,
) -> dict[str, Any]:
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
                "IBL may expose multiple dataset revisions for a session; provenance should "
                "be tightened before public release."
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
        return "right"
    if choice == -1:
        return "left"
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


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _none_safe_float(value: float | None) -> float:
    if value is None:
        return float("inf")
    return value
