import pytest

from behavtaskatlas.clicks import harmonize_brody_clicks_trial, harmonize_brody_clicks_trials


def test_harmonize_brody_clicks_trial() -> None:
    trial = harmonize_brody_clicks_trial(
        {
            "nL": 12,
            "nR": 18,
            "sd": 1.0,
            "gr": 1,
            "hh": 1,
            "ga": 0.0,
            "rg": 0,
            "task_type": "location",
            "left_click_times": [0.1, 0.4],
            "right_click_times": [0.2, 0.3, 0.8],
        },
        session_id="rat-a-parsed",
        subject_id="rat-a",
        trial_index=4,
    )

    assert trial.protocol_id == "protocol.poisson-clicks-evidence-accumulation"
    assert trial.stimulus_modality == "auditory"
    assert trial.stimulus_value == 6.0
    assert trial.stimulus_side == "right"
    assert trial.evidence_strength == 6.0
    assert trial.choice == "right"
    assert trial.correct is True
    assert trial.feedback == "reward"
    assert trial.prior_context == "gamma=0"
    assert trial.task_variables["left_click_count"] == 12
    assert trial.task_variables["right_click_count"] == 18
    assert trial.task_variables["click_count_difference"] == 6
    assert trial.task_variables["left_click_times"] == [0.1, 0.4]


def test_harmonize_brody_clicks_trials_from_parsed_schema() -> None:
    trials = harmonize_brody_clicks_trials(
        {
            "nL": [5, 10],
            "nR": [8, 6],
            "sd": [1.0, 1.0],
            "gr": [1, 0],
            "hh": [1, 1],
            "ga": [0.0, 0.0],
            "rg": [0, 0],
            "bt": [
                {"left": [0.1], "right": [0.2, 0.4]},
                {"left": [0.3, 0.6], "right": [0.7]},
            ],
        },
        session_id="rat-a-parsed",
        subject_id="rat-a",
        task_type="location",
    )

    assert len(trials) == 2
    assert trials[0].choice == "right"
    assert trials[1].choice == "left"
    assert trials[1].stimulus_value == -4.0
    assert trials[1].task_variables["task_type"] == "location"
    assert trials[1].task_variables["right_click_times"] == [0.7]


def test_harmonize_brody_clicks_trials_accepts_scalar_click_time() -> None:
    trials = harmonize_brody_clicks_trials(
        {
            "nL": [1],
            "nR": [2],
            "sd": [1.0],
            "gr": [1],
            "hh": [1],
            "bt": [{"left": 0.1, "right": [0.2, 0.4]}],
        },
        session_id="rat-a-parsed",
    )

    assert trials[0].task_variables["left_click_times"] == [0.1]


def test_harmonize_brody_clicks_trial_requires_fields() -> None:
    with pytest.raises(ValueError, match="Missing required Brody clicks trial fields"):
        harmonize_brody_clicks_trial({}, session_id="s", trial_index=0)
