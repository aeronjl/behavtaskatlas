import math

import pytest

from behavtaskatlas.ibl import (
    choice_label,
    feedback_label,
    harmonize_ibl_visual_trial,
    response_time_seconds,
    signed_contrast_percent,
    stimulus_side,
)


def test_signed_contrast_uses_right_positive_left_negative() -> None:
    assert signed_contrast_percent(math.nan, 0.25) == 25.0
    assert signed_contrast_percent(0.125, math.nan) == -12.5
    assert signed_contrast_percent(math.nan, math.nan) is None


def test_ibl_labels() -> None:
    assert stimulus_side(math.nan, 1.0) == "right"
    assert stimulus_side(0.5, math.nan) == "left"
    assert choice_label(1) == "right"
    assert choice_label(-1) == "left"
    assert choice_label(0) == "no-response"
    assert feedback_label(1) == "reward"
    assert feedback_label(-1) == "error"


def test_response_time_seconds() -> None:
    assert response_time_seconds(10.0, 10.42) == pytest.approx(0.42)
    assert response_time_seconds(math.nan, 10.42) is None


def test_harmonize_ibl_visual_trial() -> None:
    trial = harmonize_ibl_visual_trial(
        {
            "contrastLeft": math.nan,
            "contrastRight": 0.25,
            "choice": 1,
            "feedbackType": 1,
            "response_times": 12.7,
            "stimOn_times": 12.1,
            "probabilityLeft": 0.2,
            "rewardVolume": 1.5,
        },
        session_id="example-session",
        subject_id="example-subject",
        trial_index=7,
    )

    assert trial.protocol_id == "protocol.ibl-visual-decision-v1"
    assert trial.stimulus_value == 25.0
    assert trial.stimulus_side == "right"
    assert trial.evidence_strength == 25.0
    assert trial.choice == "right"
    assert trial.correct is True
    assert trial.feedback == "reward"
    assert trial.response_time == pytest.approx(0.6)
    assert trial.prior_context == "p_left=0.2"


def test_harmonize_ibl_visual_trial_requires_core_fields() -> None:
    with pytest.raises(ValueError, match="Missing required IBL trial fields"):
        harmonize_ibl_visual_trial({}, session_id="s", trial_index=0)

