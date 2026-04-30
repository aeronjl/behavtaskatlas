import json
import math

import numpy as np
import pytest

from behavtaskatlas.ibl import load_canonical_trials_csv, write_canonical_trials_csv
from behavtaskatlas.steinmetz import (
    STEINMETZ_DATASET_ID,
    STEINMETZ_PROTOCOL_ID,
    analyze_steinmetz_session_aggregate,
    analyze_steinmetz_visual_decision,
    harmonize_steinmetz_visual_trials,
    load_steinmetz_derived_sessions,
    load_steinmetz_session_dir,
    response_time_seconds,
    signed_contrast_difference_percent,
    steinmetz_aggregate_choice_svg,
    steinmetz_aggregate_report_html,
    steinmetz_choice_label,
    steinmetz_choice_svg,
    steinmetz_provenance_payload,
    steinmetz_report_html,
    steinmetz_stimulus_side,
    summarize_steinmetz_choice_by_contrast_pair,
    summarize_steinmetz_choice_by_signed_contrast,
    write_steinmetz_aggregate_outputs,
    write_steinmetz_choice_svg,
    write_steinmetz_condition_csv,
    write_steinmetz_summary_csv,
)


def test_steinmetz_labels_keep_nogo_as_withhold() -> None:
    assert signed_contrast_difference_percent(0.5, 0.0) == -50.0
    assert signed_contrast_difference_percent(0.0, 1.0) == 100.0
    assert signed_contrast_difference_percent(0.25, 0.25) == 0.0
    assert steinmetz_stimulus_side(0.0, 1.0) == "right"
    assert steinmetz_stimulus_side(0.5, 0.0) == "left"
    assert steinmetz_stimulus_side(0.0, 0.0) == "none"
    assert steinmetz_stimulus_side(0.25, 0.25) == "unknown"
    assert steinmetz_choice_label(-1) == "right"
    assert steinmetz_choice_label(1) == "left"
    assert steinmetz_choice_label(0) == "withhold"
    assert response_time_seconds(10.0, 10.42) == pytest.approx(0.42)
    assert response_time_seconds(math.nan, 10.42) is None


def test_load_and_harmonize_extracted_steinmetz_session(tmp_path) -> None:
    session_dir = _write_steinmetz_session(tmp_path)
    source_trials, details = load_steinmetz_session_dir(session_dir)
    trials = harmonize_steinmetz_visual_trials(
        source_trials,
        session_id="steinmetz-test",
        subject_id="mouse-a",
    )

    assert details["n_trials"] == 4
    assert details["figshare_doi"] == "10.6084/m9.figshare.9974357.v3"
    assert len(trials) == 4
    assert trials[0].protocol_id == STEINMETZ_PROTOCOL_ID
    assert trials[0].dataset_id == STEINMETZ_DATASET_ID
    assert trials[0].stimulus_value == 100.0
    assert trials[0].stimulus_side == "right"
    assert trials[0].choice == "right"
    assert trials[0].correct is True
    assert trials[0].response_time == pytest.approx(0.5)
    assert trials[0].task_variables["right_contrast"] == 100.0
    assert trials[1].stimulus_value == -50.0
    assert trials[1].choice == "left"
    assert trials[2].choice == "withhold"
    assert trials[2].stimulus_side == "none"
    assert trials[2].task_variables["no_go_condition"] is True
    assert trials[3].stimulus_value == 0.0
    assert trials[3].stimulus_side == "unknown"
    assert trials[3].task_variables["bilateral_condition"] is True


def test_steinmetz_harmonizes_singleton_column_vectors(tmp_path) -> None:
    session_dir = _write_steinmetz_session(tmp_path, column_vectors=True)
    source_trials, _ = load_steinmetz_session_dir(session_dir)
    trials = harmonize_steinmetz_visual_trials(source_trials, session_id="steinmetz-test")

    assert trials[0].stimulus_value == 100.0
    assert trials[0].choice == "right"
    assert trials[0].correct is True
    assert trials[0].task_variables["left_contrast"] == 0.0
    assert trials[1].stimulus_value == -50.0
    assert trials[1].choice == "left"
    assert trials[2].choice == "withhold"


def test_steinmetz_summary_and_analysis_count_withhold_choices(tmp_path) -> None:
    trials = _harmonized_trials(tmp_path)
    summary = summarize_steinmetz_choice_by_signed_contrast(trials)
    conditions = summarize_steinmetz_choice_by_contrast_pair(trials)
    result = analyze_steinmetz_visual_decision(trials)

    zero_row = next(row for row in summary if row["stimulus_value"] == 0.0)
    assert len(summary) == 3
    assert len(conditions) == 4
    assert zero_row["n_trials"] == 2
    assert zero_row["n_right"] == 1
    assert zero_row["n_withhold"] == 1
    assert zero_row["p_right"] == 1.0
    assert zero_row["p_withhold"] == 0.5
    assert result["analysis_type"] == "descriptive_choice_surface"
    assert result["n_trials"] == 4
    assert result["n_choice_trials"] == 3
    assert result["n_withhold_trials"] == 1
    assert result["choice_psychometric_fit"]["status"] == "insufficient_data"


def test_steinmetz_outputs_round_trip_and_render(tmp_path) -> None:
    trials = _harmonized_trials(tmp_path)
    result = analyze_steinmetz_visual_decision(trials)
    artifact_dir = tmp_path / "derived"
    trials_path = artifact_dir / "trials.csv"
    summary_path = artifact_dir / "choice_summary.csv"
    condition_path = artifact_dir / "condition_summary.csv"
    svg_path = artifact_dir / "choice_summary.svg"

    write_canonical_trials_csv(trials_path, trials)
    write_steinmetz_summary_csv(summary_path, result["summary_rows"])
    write_steinmetz_condition_csv(condition_path, result["condition_rows"])
    write_steinmetz_choice_svg(svg_path, result["summary_rows"])

    provenance = steinmetz_provenance_payload(
        session_dir=tmp_path / "raw",
        session_id="steinmetz-test",
        subject_id="mouse-a",
        details={"figshare_doi": "10.6084/m9.figshare.9974357.v3", "n_trials": 4},
        trials=trials,
        output_files={"trials": str(trials_path)},
    )
    html = steinmetz_report_html(
        result,
        provenance=provenance,
        choice_svg_text=svg_path.read_text(encoding="utf-8"),
        artifact_links={"trials": "trials.csv"},
    )

    assert load_canonical_trials_csv(trials_path) == trials
    assert "p_withhold" in summary_path.read_text(encoding="utf-8")
    assert "right_contrast" in condition_path.read_text(encoding="utf-8")
    assert "P(withhold)" in steinmetz_choice_svg(result["summary_rows"])
    assert "Steinmetz Visual Decision Report" in html
    assert "NoGo choices" in html
    assert provenance["exclusions"]["withhold_choices"] == 1
    assert json.loads(json.dumps(result))["n_trials"] == 4


def test_steinmetz_aggregate_outputs_session_and_subject_summaries(tmp_path) -> None:
    source_trials, _ = load_steinmetz_session_dir(_write_steinmetz_session(tmp_path))
    trials_a = harmonize_steinmetz_visual_trials(
        source_trials,
        session_id="session-a",
        subject_id="mouse-a",
    )
    trials_b = harmonize_steinmetz_visual_trials(
        source_trials,
        session_id="session-b",
        subject_id="mouse-a",
    )
    trials_c = harmonize_steinmetz_visual_trials(
        source_trials,
        session_id="session-c",
        subject_id="mouse-b",
    )
    derived_dir = tmp_path / "derived"
    write_canonical_trials_csv(derived_dir / "session-a" / "trials.csv", trials_a)
    write_canonical_trials_csv(derived_dir / "session-b" / "trials.csv", trials_b)
    write_canonical_trials_csv(derived_dir / "session-c" / "trials.csv", trials_c)

    loaded_sessions = load_steinmetz_derived_sessions(derived_dir)
    result = analyze_steinmetz_session_aggregate(loaded_sessions)
    out_paths = write_steinmetz_aggregate_outputs(tmp_path / "aggregate", result)
    zero_row = next(row for row in result["signed_contrast_rows"] if row["stimulus_value"] == 0)

    assert result["analysis_type"] == "session_aggregate"
    assert result["n_sessions"] == 3
    assert result["n_subjects"] == 2
    assert result["n_trials"] == 12
    assert len(result["session_rows"]) == 3
    assert len(result["subject_rows"]) == 2
    assert zero_row["n_sessions"] == 3
    assert zero_row["n_subjects"] == 2
    assert zero_row["mean_session_p_withhold"] == 0.5
    assert zero_row["mean_subject_p_withhold"] == 0.5
    assert "<svg" in steinmetz_aggregate_choice_svg(result["signed_contrast_rows"])
    assert "Steinmetz Visual Decision Aggregate Report" in steinmetz_aggregate_report_html(
        result
    )
    assert "aggregate_session_summary" in out_paths["report"].read_text(encoding="utf-8")
    assert "mean_subject_p_withhold" in out_paths["signed_contrast_summary"].read_text(
        encoding="utf-8"
    )
    assert json.loads(out_paths["aggregate_result"].read_text(encoding="utf-8"))[
        "n_sessions"
    ] == 3


def test_load_steinmetz_session_requires_core_files(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing required Steinmetz trial files"):
        load_steinmetz_session_dir(tmp_path)


def _harmonized_trials(tmp_path):
    source_trials, _ = load_steinmetz_session_dir(_write_steinmetz_session(tmp_path))
    return harmonize_steinmetz_visual_trials(source_trials, session_id="steinmetz-test")


def _write_steinmetz_session(tmp_path, *, column_vectors: bool = False):
    session_dir = tmp_path / "steinmetz-session"
    session_dir.mkdir()
    arrays = {
        "trials.feedbackType.npy": np.array([1, 1, 1, -1]),
        "trials.feedback_times.npy": np.array([10.7, 12.6, 14.4, 16.2]),
        "trials.goCue_times.npy": np.array([10.1, 12.1, 14.1, 15.6]),
        "trials.included.npy": np.array([True, True, False, True]),
        "trials.intervals.npy": np.array(
            [[9.8, 10.8], [11.8, 12.8], [13.8, 14.8], [15.3, 16.4]]
        ),
        "trials.repNum.npy": np.array([1, 1, 2, 1]),
        "trials.response_choice.npy": np.array([-1, 1, 0, -1]),
        "trials.response_times.npy": np.array([10.5, 12.4, 14.2, 16.0]),
        "trials.visualStim_contrastLeft.npy": np.array([0.0, 0.5, 0.0, 0.25]),
        "trials.visualStim_contrastRight.npy": np.array([1.0, 0.0, 0.0, 0.25]),
        "trials.visualStim_times.npy": np.array([10.0, 12.0, 14.0, 15.5]),
    }
    for filename, values in arrays.items():
        if column_vectors and values.ndim == 1:
            values = values.reshape(-1, 1)
        np.save(session_dir / filename, values)
    return session_dir
