import math

import pytest

from behavtaskatlas.ibl import (
    choice_label,
    feedback_label,
    harmonize_ibl_visual_trial,
    harmonize_ibl_visual_trials,
    provenance_payload,
    response_time_seconds,
    signed_contrast_percent,
    stimulus_side,
    summarize_canonical_trials,
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


def test_harmonize_ibl_visual_trials_and_summary() -> None:
    source = {
        "contrastLeft": [math.nan, 0.25, math.nan],
        "contrastRight": [1.0, math.nan, 0.25],
        "choice": [-1, 1, 1],
        "feedbackType": [1, -1, 1],
        "response_times": [10.5, 12.4, 14.2],
        "stimOn_times": [10.0, 12.0, 14.0],
        "probabilityLeft": [0.5, 0.5, 0.2],
        "rewardVolume": [1.5, 0.0, 1.5],
    }

    trials = harmonize_ibl_visual_trials(
        source,
        session_id="session",
        subject_id="subject",
    )
    summary = summarize_canonical_trials(trials)

    assert len(trials) == 3
    assert trials[0].stimulus_value == 100.0
    assert trials[1].stimulus_value == -25.0
    assert summary == [
        {
            "prior_context": "p_left=0.2",
            "stimulus_value": 25.0,
            "n_trials": 1,
            "n_right": 1,
            "p_right": 1.0,
            "n_correct": 1,
            "p_correct": 1.0,
            "median_response_time": pytest.approx(0.2),
        },
        {
            "prior_context": "p_left=0.5",
            "stimulus_value": -25.0,
            "n_trials": 1,
            "n_right": 1,
            "p_right": 1.0,
            "n_correct": 0,
            "p_correct": 0.0,
            "median_response_time": pytest.approx(0.4),
        },
        {
            "prior_context": "p_left=0.5",
            "stimulus_value": 100.0,
            "n_trials": 1,
            "n_right": 0,
            "p_right": 0.0,
            "n_correct": 1,
            "p_correct": 1.0,
            "median_response_time": pytest.approx(0.5),
        },
    ]


def test_provenance_payload_counts_exclusions() -> None:
    trials = [
        harmonize_ibl_visual_trial(
            {
                "contrastLeft": math.nan,
                "contrastRight": math.nan,
                "choice": 0,
                "feedbackType": 0,
                "response_times": math.nan,
                "stimOn_times": 1.0,
                "probabilityLeft": math.nan,
            },
            session_id="session",
            trial_index=0,
        )
    ]

    payload = provenance_payload(
        eid="session",
        details={"subject": "subject", "lab": "lab"},
        output_files={"trials": "trials.csv"},
        trials=trials,
    )

    assert payload["n_trials"] == 1
    assert "behavtaskatlas_git_dirty" in payload
    assert payload["exclusions"]["missing_stimulus"] == 1
    assert payload["exclusions"]["no_response"] == 1
    assert payload["exclusions"]["missing_response_time"] == 1
