from __future__ import annotations

import math
from typing import Any

from behavtaskatlas.models import CanonicalTrial

IBL_VISUAL_PROTOCOL_ID = "protocol.ibl-visual-decision-v1"
IBL_PUBLIC_BEHAVIOR_DATASET_ID = "dataset.ibl-public-behavior"

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
