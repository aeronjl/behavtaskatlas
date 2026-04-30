import csv
import json

import pytest

from behavtaskatlas.ibl import load_canonical_trials_csv, write_canonical_trials_csv
from behavtaskatlas.rodgers import (
    RODGERS_DATASET_ID,
    RODGERS_PROTOCOL_ID,
    analyze_rodgers_whisker_object_recognition,
    harmonize_rodgers_whisker_rows,
    load_rodgers_whisker_source,
    rodgers_provenance_payload,
    write_rodgers_accuracy_svg,
    write_rodgers_condition_csv,
    write_rodgers_detection_csv,
    write_rodgers_report_html,
    write_rodgers_task_rule_csv,
)


def _row(**overrides):
    base = {
        "start_time": 10.0,
        "stop_time": 20.0,
        "direct_delivery": False,
        "stim_is_random": True,
        "optogenetic": False,
        "outcome": "correct",
        "choice": "right",
        "rewarded_side": "right",
        "servo_position": "close",
        "stimulus": "convex",
        "ignore_trial": False,
        "choice_time": 12.42,
        "response_window_open_time": 12.0,
        "trial": 7,
        "n_contacts_total": 4,
    }
    base.update(overrides)
    return base


def test_harmonize_discrimination_rows_preserves_shape_rule_and_latency() -> None:
    trials = harmonize_rodgers_whisker_rows(
        [
            _row(stimulus="convex", choice="right", rewarded_side="right", trial=1),
            _row(stimulus="concave", choice="left", rewarded_side="left", trial=2),
        ],
        base_session_id="session-1",
        subject_id="mouse-a",
    )

    assert len(trials) == 2
    assert trials[0].protocol_id == RODGERS_PROTOCOL_ID
    assert trials[0].dataset_id == RODGERS_DATASET_ID
    assert trials[0].stimulus_modality == "somatosensory"
    assert trials[0].stimulus_side == "none"
    assert trials[0].stimulus_value is None
    assert trials[0].choice == "right"
    assert trials[0].correct is True
    assert trials[0].feedback == "reward"
    assert trials[0].response_time == pytest.approx(0.42)
    assert trials[0].task_variables["task_rule"] == "shape_discrimination"
    assert trials[0].task_variables["stimulus"] == "convex"
    assert trials[0].task_variables["analysis_eligible"] is True
    assert trials[1].choice == "left"


def test_harmonize_detection_rows_maps_catch_and_spoil_trials() -> None:
    trials = harmonize_rodgers_whisker_rows(
        [
            _row(stimulus="concave", choice="right", rewarded_side="right", trial=1),
            _row(stimulus="nothing", choice="left", rewarded_side="left", trial=2),
            _row(
                stimulus="nothing",
                choice="nogo",
                rewarded_side="left",
                outcome="spoil",
                ignore_trial=True,
                trial=3,
            ),
        ],
        base_session_id="session-2",
    )

    assert {trial.task_variables["task_rule"] for trial in trials} == {"shape_detection"}
    assert trials[1].choice == "left"
    assert trials[1].correct is True
    assert trials[2].choice == "no-response"
    assert trials[2].correct is None
    assert trials[2].task_variables["ignore_trial"] is True
    assert trials[2].task_variables["analysis_eligible"] is False


def test_load_rodgers_csv_source_round_trips_canonical_trials(tmp_path) -> None:
    source_path = tmp_path / "rodgers_trials.csv"
    rows = [
        _row(stimulus="concave", choice="right", rewarded_side="right", trial=1),
        _row(stimulus="nothing", choice="left", rewarded_side="left", trial=2),
    ]
    with source_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    trials, details = load_rodgers_whisker_source(
        source_path,
        session_id="session-csv",
        subject_id="mouse-csv",
    )

    assert len(trials) == 2
    assert details["source_kind"] == "trial_csv"
    assert details["n_trials"] == 2
    assert details["task_rules"] == ["shape_detection"]
    assert details["stimuli"] == ["concave", "nothing"]

    trials_path = tmp_path / "trials.csv"
    write_canonical_trials_csv(trials_path, trials)
    loaded = load_canonical_trials_csv(trials_path)
    assert loaded[0].subject_id == "mouse-csv"
    assert loaded[0].task_variables["stimulus"] == "concave"


def test_analyze_rodgers_detection_summarizes_rates_and_contacts() -> None:
    trials = harmonize_rodgers_whisker_rows(
        [
            _row(stimulus="convex", choice="right", rewarded_side="right", trial=1),
            _row(
                stimulus="concave",
                choice="left",
                rewarded_side="right",
                outcome="error",
                trial=2,
                n_contacts_total=2,
            ),
            _row(stimulus="nothing", choice="left", rewarded_side="left", trial=3),
            _row(
                stimulus="nothing",
                choice="right",
                rewarded_side="left",
                outcome="error",
                trial=4,
            ),
            _row(stimulus="nothing", choice="nogo", outcome="spoil", ignore_trial=True, trial=5),
        ],
        base_session_id="session-analysis",
    )

    result = analyze_rodgers_whisker_object_recognition(trials)

    assert result["protocol_id"] == RODGERS_PROTOCOL_ID
    assert result["dataset_id"] == RODGERS_DATASET_ID
    assert result["n_trials"] == 5
    assert result["n_analysis_trials"] == 4
    assert result["n_ignored_trials"] == 1
    assert result["outcome_counts"]["correct"] == 2
    assert result["outcome_counts"]["error"] == 2
    detection = result["detection_rows"][0]
    assert detection["n_signal_trials"] == 2
    assert detection["n_catch_trials"] == 2
    assert detection["hit_rate"] == pytest.approx(0.5)
    assert detection["false_alarm_rate"] == pytest.approx(0.5)
    assert detection["p_correct"] == pytest.approx(0.5)
    task_row = result["task_rule_rows"][0]
    assert task_row["mean_contacts_total"] == pytest.approx(3.5)


def test_rodgers_outputs_render(tmp_path) -> None:
    trials = harmonize_rodgers_whisker_rows(
        [
            _row(stimulus="convex", choice="right", rewarded_side="right", trial=1),
            _row(stimulus="nothing", choice="left", rewarded_side="left", trial=2),
        ],
        base_session_id="session-output",
    )
    result = analyze_rodgers_whisker_object_recognition(trials)
    provenance = rodgers_provenance_payload(
        details={
            "source_file": "rodgers_trials.csv",
            "source_file_name": "rodgers_trials.csv",
            "source_file_sha256": "abc123",
            "source_kind": "trial_csv",
            "n_source_rows": 2,
            "n_trials": 2,
            "subjects": [],
            "sessions": ["session-output"],
            "task_rules": ["shape_detection"],
        },
        trials=trials,
        output_files={"trials": "trials.csv"},
    )
    condition_path = tmp_path / "condition_summary.csv"
    task_path = tmp_path / "task_rule_summary.csv"
    detection_path = tmp_path / "detection_summary.csv"
    svg_path = tmp_path / "accuracy.svg"
    report_path = tmp_path / "report.html"
    result_path = tmp_path / "analysis_result.json"

    write_rodgers_condition_csv(condition_path, result["condition_rows"])
    write_rodgers_task_rule_csv(task_path, result["task_rule_rows"])
    write_rodgers_detection_csv(detection_path, result["detection_rows"])
    write_rodgers_accuracy_svg(svg_path, result["condition_rows"])
    result_path.write_text(json.dumps(result), encoding="utf-8")
    write_rodgers_report_html(
        report_path,
        result,
        provenance=provenance,
        accuracy_svg_text=svg_path.read_text(encoding="utf-8"),
        artifact_links={"analysis result JSON": "analysis_result.json"},
    )

    assert "shape_detection" in condition_path.read_text(encoding="utf-8")
    assert "hit_rate" in detection_path.read_text(encoding="utf-8")
    assert "<svg" in svg_path.read_text(encoding="utf-8")
    assert "Rodgers Whisker Object Recognition" in report_path.read_text(encoding="utf-8")
