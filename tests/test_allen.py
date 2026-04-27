import math

import pytest

from behavtaskatlas.allen import (
    ALLEN_VISUAL_BEHAVIOR_DATASET_ID,
    ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID,
    allen_visual_behavior_provenance_payload,
    analyze_allen_change_detection,
    harmonize_allen_change_detection_row,
    harmonize_allen_change_detection_rows,
)


def _trial_row(**overrides):
    base = {
        "go": True,
        "catch": False,
        "hit": True,
        "miss": False,
        "false_alarm": False,
        "correct_reject": False,
        "aborted": False,
        "auto_rewarded": False,
        "initial_image_name": "im000",
        "change_image_name": "im001",
        "response_latency": 0.32,
        "reward_volume": 0.005,
        "change_time_no_display_delay": 4.5,
        "trial_length": 6.0,
        "lick_times": [4.82],
    }
    base.update(overrides)
    return base


def test_harmonize_hit_row_yields_go_choice_with_reward() -> None:
    trial = harmonize_allen_change_detection_row(
        _trial_row(),
        session_id="session-1",
        trial_index=0,
        subject_id="mouse-A",
    )

    assert trial.protocol_id == ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID
    assert trial.dataset_id == ALLEN_VISUAL_BEHAVIOR_DATASET_ID
    assert trial.subject_id == "mouse-A"
    assert trial.session_id == "session-1"
    assert trial.choice == "go"
    assert trial.correct is True
    assert trial.feedback == "reward"
    assert trial.reward == pytest.approx(0.005)
    assert trial.reward_units == "mL"
    assert trial.stimulus_side == "none"
    assert trial.stimulus_value is None
    assert trial.evidence_strength is None
    assert trial.task_variables["outcome"] == "hit"
    assert trial.task_variables["is_change"] is True
    assert trial.task_variables["image_pair"] == "im000->im001"


def test_harmonize_correct_reject_yields_withhold_no_reward() -> None:
    trial = harmonize_allen_change_detection_row(
        _trial_row(
            go=False,
            catch=True,
            hit=False,
            correct_reject=True,
            response_latency=float("nan"),
            reward_volume=0.0,
            change_image_name="im000",
            lick_times=[],
        ),
        session_id="session-1",
        trial_index=1,
    )

    assert trial.choice == "withhold"
    assert trial.correct is True
    assert trial.feedback == "none"
    assert trial.response_time is None
    assert trial.task_variables["outcome"] == "correct_reject"


def test_harmonize_false_alarm_marks_incorrect_go() -> None:
    trial = harmonize_allen_change_detection_row(
        _trial_row(
            go=False,
            catch=True,
            hit=False,
            false_alarm=True,
            reward_volume=0.0,
        ),
        session_id="session-1",
        trial_index=2,
    )

    assert trial.choice == "go"
    assert trial.correct is False
    assert trial.feedback == "none"
    assert trial.task_variables["outcome"] == "false_alarm"


def test_harmonize_aborted_yields_no_response() -> None:
    trial = harmonize_allen_change_detection_row(
        _trial_row(hit=False, aborted=True, response_latency=float("nan")),
        session_id="session-1",
        trial_index=3,
    )

    assert trial.choice == "no-response"
    assert trial.correct is None
    assert trial.task_variables["outcome"] == "aborted"


def test_harmonize_missing_required_field_raises() -> None:
    incomplete = _trial_row()
    incomplete.pop("hit")
    with pytest.raises(ValueError, match="Missing required Allen"):
        harmonize_allen_change_detection_row(
            incomplete,
            session_id="session-1",
            trial_index=0,
        )


def test_analyze_change_detection_computes_rates_and_d_prime() -> None:
    rows = [
        _trial_row(),  # hit
        _trial_row(hit=False, miss=True, response_latency=float("nan")),
        _trial_row(go=False, catch=True, hit=False, correct_reject=True, reward_volume=0.0),
        _trial_row(
            go=False,
            catch=True,
            hit=False,
            false_alarm=True,
            reward_volume=0.0,
            change_image_name="im000",
        ),
        _trial_row(hit=False, aborted=True),  # filtered from rate
    ]
    trials = harmonize_allen_change_detection_rows(rows, session_id="session-1")

    result = analyze_allen_change_detection(trials)

    assert result["protocol_id"] == ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID
    assert result["dataset_id"] == ALLEN_VISUAL_BEHAVIOR_DATASET_ID
    assert result["n_trials"] == 5
    assert result["n_go_trials"] == 2
    assert result["n_catch_trials"] == 2
    assert result["outcome_counts"]["hit"] == 1
    assert result["outcome_counts"]["miss"] == 1
    assert result["outcome_counts"]["false_alarm"] == 1
    assert result["outcome_counts"]["correct_reject"] == 1
    assert result["outcome_counts"]["aborted"] == 1
    assert result["hit_rate"] == pytest.approx(0.5)
    assert result["false_alarm_rate"] == pytest.approx(0.5)
    assert result["d_prime"] == pytest.approx(0.0, abs=1e-9)
    pair = next(
        row for row in result["image_pair_summary"] if row["initial_image"] == "im000"
    )
    assert pair["n_trials"] == 2
    assert pair["n_hit"] == 1
    assert pair["n_miss"] == 1
    assert pair["hit_rate"] == pytest.approx(0.5)


def test_provenance_payload_records_outcome_counts_and_session() -> None:
    trials = harmonize_allen_change_detection_rows([_trial_row()], session_id="session-9")
    payload = allen_visual_behavior_provenance_payload(
        details={
            "behavior_session_id": 12345,
            "subject_id": "mouse-A",
            "session_type": "OPHYS_1_images_A",
            "cache": {"cache_dir": "data/raw/allen_visual_behavior"},
            "session_meta": {"selected_id": 12345},
        },
        output_files={"trials": "derived/allen_visual_behavior/trials.csv"},
        trials=trials,
    )

    assert payload["protocol_id"] == ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID
    assert payload["dataset_id"] == ALLEN_VISUAL_BEHAVIOR_DATASET_ID
    assert payload["source"]["behavior_session_id"] == 12345
    assert payload["source"]["session_type"] == "OPHYS_1_images_A"
    assert payload["outcome_counts"]["hit"] == 1
    assert payload["n_trials"] == 1


def test_d_prime_is_finite_with_extreme_rates() -> None:
    rows = [_trial_row() for _ in range(5)]
    rows.extend(
        _trial_row(go=False, catch=True, hit=False, correct_reject=True, reward_volume=0.0)
        for _ in range(5)
    )
    trials = harmonize_allen_change_detection_rows(rows, session_id="session-1")
    result = analyze_allen_change_detection(trials)
    assert result["d_prime"] is not None
    assert math.isfinite(result["d_prime"])
    assert result["d_prime"] > 0
