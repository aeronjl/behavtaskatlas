import pytest

from behavtaskatlas.human_visual import (
    HUMAN_VISUAL_CONTRAST_DATASET_ID,
    HUMAN_VISUAL_CONTRAST_PROTOCOL_ID,
    analyze_human_visual_contrast,
    harmonize_walsh_human_visual_contrast_row,
    harmonize_walsh_human_visual_contrast_rows,
)


def test_harmonize_walsh_row_maps_lower_frequency_target_positive() -> None:
    trial = harmonize_walsh_human_visual_contrast_row(
        [0.75, 1, 2, 1, 3, 1, 1, 0.61, 50],
        session_id="session",
        trial_index=0,
    )

    assert trial.protocol_id == HUMAN_VISUAL_CONTRAST_PROTOCOL_ID
    assert trial.dataset_id == HUMAN_VISUAL_CONTRAST_DATASET_ID
    assert trial.subject_id == "subject-A"
    assert trial.stimulus_value == pytest.approx(22.0)
    assert trial.stimulus_side == "right"
    assert trial.choice == "right"
    assert trial.correct is True
    assert trial.feedback == "reward"
    assert trial.reward == 50
    assert trial.prior_context == "cue=valid"
    assert trial.training_stage == "exposure_bin_3"
    assert trial.task_variables["target_lower_frequency"] is True
    assert trial.task_variables["pulse"] == "no_pulse"
    assert "right=lower-frequency response" in trial.task_variables["canonical_choice_convention"]


def test_harmonize_walsh_row_reconstructs_target_from_error() -> None:
    trial = harmonize_walsh_human_visual_contrast_row(
        [0.62, 2, 3, 4, 5, 12, 1, 0.56, -25],
        session_id="session",
        trial_index=7,
    )

    assert trial.subject_id == "subject-L"
    assert trial.stimulus_value == pytest.approx(-12.0)
    assert trial.stimulus_side == "left"
    assert trial.choice == "right"
    assert trial.correct is False
    assert trial.feedback == "error"
    assert trial.prior_context == "cue=invalid"
    assert trial.task_variables["target_lower_frequency"] is False
    assert trial.task_variables["pulse"] == "reverse"


def test_analyze_human_visual_contrast_uses_slice_metadata() -> None:
    rows = [
        [0.7, 1, 1, 1, 1, 1, 0, 0.55, 50],
        [0.8, 1, 1, 1, 1, 1, 0, 0.60, 50],
        [0.9, 1, 1, 1, 1, 1, 1, 0.55, 50],
        [1.0, 1, 1, 1, 1, 1, 1, 0.60, 50],
    ]
    trials = harmonize_walsh_human_visual_contrast_rows(rows, session_id="session")

    result = analyze_human_visual_contrast(trials)

    assert result["analysis_id"] == "analysis.human-visual-contrast.descriptive-psychometric"
    assert result["protocol_id"] == HUMAN_VISUAL_CONTRAST_PROTOCOL_ID
    assert result["dataset_id"] == HUMAN_VISUAL_CONTRAST_DATASET_ID
    assert result["report_title"] == "Human Visual Contrast Prior-Cue Report"
    assert result["n_trials"] == 4
    assert result["prior_results"][0]["prior_context"] == "cue=neutral"
    assert any("lower-frequency" in caveat for caveat in result["caveats"])
