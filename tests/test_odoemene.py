import json

import numpy as np
import pytest
import scipy.io

from behavtaskatlas.ibl import load_canonical_trials_csv, write_canonical_trials_csv
from behavtaskatlas.odoemene import (
    ODOEMENE_DATASET_ID,
    ODOEMENE_PROTOCOL_ID,
    analyze_odoemene_visual_accumulation,
    harmonize_odoemene_subjects,
    load_odoemene_visual_accumulation_mat,
    odoemene_event_kernel_rows,
    odoemene_kernel_svg,
    odoemene_provenance_payload,
    odoemene_report_html,
    write_odoemene_kernel_csv,
    write_odoemene_kernel_svg,
)


def test_harmonize_odoemene_subject_maps_high_low_categories() -> None:
    trials = harmonize_odoemene_subjects([_subject_record()], base_session_id="odoemene-test")

    assert len(trials) == 4
    assert trials[0].protocol_id == ODOEMENE_PROTOCOL_ID
    assert trials[0].dataset_id == ODOEMENE_DATASET_ID
    assert trials[0].subject_id == "m01"
    assert trials[0].stimulus_value == pytest.approx(-8.0)
    assert trials[0].stimulus_side == "left"
    assert trials[0].choice == "left"
    assert trials[0].correct is True
    assert trials[0].feedback == "reward"
    assert trials[0].response_time == pytest.approx(0.25)
    assert trials[0].prior_context == "contingency=standard"
    assert trials[0].task_variables["stim_event_count"] == 2
    assert trials[1].stimulus_value == pytest.approx(8.0)
    assert trials[1].stimulus_side == "right"
    assert trials[1].choice == "right"
    assert trials[2].choice == "right"
    assert trials[2].correct is False
    assert trials[2].feedback == "error"
    assert trials[3].choice == "no-response"
    assert trials[3].correct is None
    assert trials[3].response_time is None


def test_load_odoemene_mat_discovers_subject_array(tmp_path) -> None:
    mat_path = tmp_path / "odoemene.mat"
    scipy.io.savemat(mat_path, {"dataset": np.array([_subject_record()], dtype=object)})

    trials, details = load_odoemene_visual_accumulation_mat(
        mat_path,
        session_id="odoemene-test",
    )

    assert len(trials) == 4
    assert details["matlab_variable"] == "dataset"
    assert details["n_subjects_source"] == 1
    assert details["n_trials"] == 4
    assert details["dataset_doi"] == "10.14224/1.38944"
    assert details["subjects"] == ["m01"]


def test_analyze_odoemene_visual_accumulation_adds_event_kernel() -> None:
    trials = harmonize_odoemene_subjects([_subject_record()], base_session_id="odoemene-test")
    result = analyze_odoemene_visual_accumulation(trials)
    kernel_rows = odoemene_event_kernel_rows(trials)

    assert result["analysis_id"] == (
        "analysis.odoemene-visual-accumulation.descriptive-psychometric-kernel"
    )
    assert result["analysis_type"] == "descriptive_psychometric_kernel"
    assert result["protocol_id"] == ODOEMENE_PROTOCOL_ID
    assert result["dataset_id"] == ODOEMENE_DATASET_ID
    assert result["n_trials"] == 4
    assert result["n_response_trials"] == 3
    assert result["n_no_response_trials"] == 1
    assert result["n_subjects"] == 1
    assert result["event_kernel_analyzed_trials"] == 3
    assert len(result["event_kernel_rows"]) == 25
    assert len(kernel_rows) == 25
    assert any(row["normalized_weight"] is not None for row in kernel_rows)


def test_odoemene_outputs_round_trip_and_render(tmp_path) -> None:
    trials = harmonize_odoemene_subjects([_subject_record()], base_session_id="odoemene-test")
    result = analyze_odoemene_visual_accumulation(trials)
    artifact_dir = tmp_path / "derived"
    trials_path = artifact_dir / "trials.csv"
    kernel_path = artifact_dir / "event_kernel.csv"
    kernel_svg_path = artifact_dir / "event_kernel.svg"

    write_canonical_trials_csv(trials_path, trials)
    write_odoemene_kernel_csv(kernel_path, result["event_kernel_rows"])
    write_odoemene_kernel_svg(kernel_svg_path, result["event_kernel_rows"])

    provenance = odoemene_provenance_payload(
        details={"source_file_name": "odoemene.mat", "dataset_doi": "10.14224/1.38944"},
        trials=trials,
        output_files={"trials": str(trials_path)},
    )
    html = odoemene_report_html(
        result,
        provenance=provenance,
        psychometric_svg_text="<svg></svg>",
        kernel_svg_text=kernel_svg_path.read_text(encoding="utf-8"),
        artifact_links={"trials": "trials.csv"},
    )

    assert load_canonical_trials_csv(trials_path) == trials
    assert "normalized_weight" in kernel_path.read_text(encoding="utf-8")
    assert "Normalized event-choice weight" in odoemene_kernel_svg(result["event_kernel_rows"])
    assert "Odoemene Visual Evidence Accumulation Report" in html
    assert "Event Kernel" in html
    assert provenance["exclusions"]["invalid_trials"] == 1
    assert json.loads(json.dumps(result))["n_trials"] == 4


def _subject_record():
    return {
        "subjectID": "M01",
        "species": "mouse",
        "trainingContingency": "standard",
        "rawChoiceData": {
            "stimEventList": [
                [1, 0, 0, 1, *([0] * 21)],
                [0, 1, 1, 0, *([1] * 21)],
                [1, 1, 0, 0, *([0] * 21)],
                [0, 0, 0, 0, *([0] * 21)],
            ],
            "stimRate": [4, 20, 8, 16],
            "subjectResponse": [1, 2, 2, 0],
            "correctResponse": [1, 2, 1, 2],
            "validTrial": [1, 1, 1, 0],
            "success": [1, 1, 0, 0],
            "waitTime": [1.1, 1.12, 1.2, 0.7],
            "moveTime": [0.25, 0.31, 0.4, np.nan],
            "sessionID": [1, 1, 2, 2],
            "numSessions": 2,
        },
    }
