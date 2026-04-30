import csv
import json

import numpy as np
import pytest
import scipy.io

from behavtaskatlas.coen import (
    COEN_DATASET_ID,
    COEN_PROTOCOL_ID,
    analyze_coen_audiovisual_decisions,
    coen_condition_svg,
    coen_provenance_payload,
    coen_report_html,
    harmonize_coen_audiovisual_rows,
    load_coen_audiovisual_source,
    write_coen_condition_csv,
    write_coen_condition_svg,
    write_coen_conflict_csv,
    write_coen_modality_csv,
)
from behavtaskatlas.ibl import load_canonical_trials_csv, write_canonical_trials_csv


def test_harmonize_coen_rows_maps_audiovisual_fields() -> None:
    trials = harmonize_coen_audiovisual_rows(_trial_rows(), base_session_id="coen-test")

    assert len(trials) == 6
    assert trials[0].protocol_id == COEN_PROTOCOL_ID
    assert trials[0].dataset_id == COEN_DATASET_ID
    assert trials[0].subject_id == "pc001"
    assert trials[0].stimulus_modality == "visual"
    assert trials[0].stimulus_value == pytest.approx(0.4)
    assert trials[0].stimulus_side == "right"
    assert trials[0].choice == "right"
    assert trials[0].correct is True
    assert trials[0].feedback == "reward"
    assert trials[0].response_time == pytest.approx(0.31)
    assert trials[0].prior_context == "visual"
    assert trials[0].task_variables["visual_diff"] == pytest.approx(0.4)
    assert trials[0].task_variables["auditory_diff"] == pytest.approx(0.0)
    assert trials[2].stimulus_modality == "auditory"
    assert trials[2].choice == "left"
    assert trials[3].choice == "no-response"
    assert trials[3].correct is None
    assert trials[4].stimulus_modality == "multisensory"
    assert trials[4].task_variables["cue_congruence"] == "coherent"
    assert trials[4].task_variables["laser_on"] is True
    assert trials[5].task_variables["cue_congruence"] == "conflict"
    assert trials[5].task_variables["visual_side"] == "right"
    assert trials[5].task_variables["auditory_side"] == "left"


def test_load_coen_csv_source(tmp_path) -> None:
    csv_path = tmp_path / "coen_trials.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_trial_rows()[0]))
        writer.writeheader()
        writer.writerows(_trial_rows())

    trials, details = load_coen_audiovisual_source(csv_path, session_id="coen-test")

    assert len(trials) == 6
    assert details["source_kind"] == "trial_csv"
    assert details["source_doi"] == "10.5522/04/22363180.v1"
    assert details["code_zenodo_doi"] == "10.5281/zenodo.7892397"
    assert details["subjects"] == ["pc001"]
    assert details["modalities"] == ["auditory", "multisensory", "visual"]


def test_load_coen_mat_combined_block(tmp_path) -> None:
    mat_path = tmp_path / "coen_block.mat"
    scipy.io.savemat(mat_path, {"blks": _combined_block()})

    trials, details = load_coen_audiovisual_source(mat_path, session_id="coen-test")

    assert len(trials) == 6
    assert details["source_kind"] == "matlab_block"
    assert details["source_variable"] == "blks"
    assert trials[0].session_id == "pc001.2020-01-01.1"
    assert trials[4].task_variables["galvo_position"] == [1.5, 2.5]
    assert trials[5].task_variables["cue_congruence"] == "conflict"


def test_load_coen_mat_proc_block(tmp_path) -> None:
    mat_path = tmp_path / "coen_proc.mat"
    scipy.io.savemat(mat_path, {"blk": _proc_block()})

    trials, details = load_coen_audiovisual_source(mat_path, session_id="coen-test")

    assert len(trials) == 6
    assert details["source_kind"] == "matlab_block"
    assert details["source_variable"] == "blk"
    assert trials[0].subject_id == "pc001"
    assert trials[0].session_id == "pc001.2020-01-10.2"
    assert trials[4].task_variables["galvo_position"] == [1.5, 2.5]
    assert trials[5].task_variables["cue_congruence"] == "conflict"


def test_analyze_coen_audiovisual_decisions_summarizes_modalities_and_conflict() -> None:
    trials = harmonize_coen_audiovisual_rows(_trial_rows(), base_session_id="coen-test")
    result = analyze_coen_audiovisual_decisions(trials)

    assert result["analysis_id"] == (
        "analysis.coen-audiovisual-spatial-wheel.descriptive-multisensory"
    )
    assert result["analysis_type"] == "descriptive_multisensory_psychometric"
    assert result["protocol_id"] == COEN_PROTOCOL_ID
    assert result["dataset_id"] == COEN_DATASET_ID
    assert result["n_trials"] == 6
    assert result["n_response_trials"] == 5
    assert result["n_no_response_trials"] == 1
    assert result["n_subjects"] == 1
    assert result["n_laser_trials"] == 1
    assert len(result["condition_rows"]) == 6
    assert {row["modality"] for row in result["modality_rows"]} == {
        "visual",
        "auditory",
        "multisensory",
    }
    assert result["conflict_rows"][0]["p_visual_choice"] == pytest.approx(0.0)
    assert result["conflict_rows"][0]["p_auditory_choice"] == pytest.approx(1.0)


def test_coen_outputs_round_trip_and_render(tmp_path) -> None:
    trials = harmonize_coen_audiovisual_rows(_trial_rows(), base_session_id="coen-test")
    result = analyze_coen_audiovisual_decisions(trials)
    artifact_dir = tmp_path / "derived"
    trials_path = artifact_dir / "trials.csv"
    condition_path = artifact_dir / "condition_summary.csv"
    modality_path = artifact_dir / "modality_summary.csv"
    conflict_path = artifact_dir / "conflict_summary.csv"
    condition_svg_path = artifact_dir / "condition_summary.svg"

    write_canonical_trials_csv(trials_path, trials)
    write_coen_condition_csv(condition_path, result["condition_rows"])
    write_coen_modality_csv(modality_path, result["modality_rows"])
    write_coen_conflict_csv(conflict_path, result["conflict_rows"])
    write_coen_condition_svg(condition_svg_path, result["condition_rows"])

    provenance = coen_provenance_payload(
        details={"source_file_name": "coen.mat", "source_kind": "matlab_block"},
        trials=trials,
        output_files={"trials": str(trials_path)},
    )
    html = coen_report_html(
        result,
        provenance=provenance,
        psychometric_svg_text="<svg></svg>",
        condition_svg_text=condition_svg_path.read_text(encoding="utf-8"),
        artifact_links={"trials": "trials.csv"},
    )

    assert load_canonical_trials_csv(trials_path) == trials
    assert "cue_congruence" in condition_path.read_text(encoding="utf-8")
    assert "modality" in modality_path.read_text(encoding="utf-8")
    assert "p_visual_choice" in conflict_path.read_text(encoding="utf-8")
    assert "Audiovisual condition surface" in coen_condition_svg(result["condition_rows"])
    assert "Coen Audiovisual Spatial Decision Report" in html
    assert "Conflict Choices" in html
    assert provenance["exclusions"]["no_response_trials"] == 1
    assert json.loads(json.dumps(result))["n_trials"] == 6


def _trial_rows():
    return [
        {
            "subject": "PC001",
            "session_id": "PC001.2020-01-01.1",
            "visDiff": 0.4,
            "audDiff": 0.0,
            "visContrast": 0.4,
            "responseCalc": 2,
            "correctResponse": 2,
            "reactionTime": 0.31,
            "responseRecorded": 1,
            "timeToFeedback": 0.45,
            "validTrial": 1,
            "repeatNum": 1,
            "visual": 1,
            "auditory": 0,
            "coherent": 0,
            "conflict": 0,
            "blank": 0,
            "laserType": 0,
            "galvoPositionX": 0.0,
            "galvoPositionY": 0.0,
        },
        {
            "subject": "PC001",
            "session_id": "PC001.2020-01-01.1",
            "visDiff": -0.4,
            "audDiff": 0.0,
            "visContrast": 0.4,
            "responseCalc": 1,
            "correctResponse": 1,
            "reactionTime": 0.28,
            "responseRecorded": 1,
            "timeToFeedback": 0.42,
            "validTrial": 1,
            "repeatNum": 1,
            "visual": 1,
            "auditory": 0,
            "coherent": 0,
            "conflict": 0,
            "blank": 0,
            "laserType": 0,
            "galvoPositionX": 0.0,
            "galvoPositionY": 0.0,
        },
        {
            "subject": "PC001",
            "session_id": "PC001.2020-01-02.1",
            "visDiff": 0.0,
            "audDiff": -1.0,
            "visContrast": 0.0,
            "responseCalc": 1,
            "correctResponse": 1,
            "reactionTime": 0.35,
            "responseRecorded": 1,
            "timeToFeedback": 0.51,
            "validTrial": 1,
            "repeatNum": 1,
            "visual": 0,
            "auditory": 1,
            "coherent": 0,
            "conflict": 0,
            "blank": 0,
            "laserType": 0,
            "galvoPositionX": 0.0,
            "galvoPositionY": 0.0,
        },
        {
            "subject": "PC001",
            "session_id": "PC001.2020-01-02.1",
            "visDiff": 0.0,
            "audDiff": 1.0,
            "visContrast": 0.0,
            "responseCalc": "nan",
            "correctResponse": 2,
            "reactionTime": "nan",
            "responseRecorded": 0,
            "timeToFeedback": 2.0,
            "validTrial": 1,
            "repeatNum": 1,
            "visual": 0,
            "auditory": 1,
            "coherent": 0,
            "conflict": 0,
            "blank": 0,
            "laserType": 0,
            "galvoPositionX": 0.0,
            "galvoPositionY": 0.0,
        },
        {
            "subject": "PC001",
            "session_id": "PC001.2020-01-03.1",
            "visDiff": 0.4,
            "audDiff": 1.0,
            "visContrast": 0.4,
            "responseCalc": 2,
            "correctResponse": 2,
            "reactionTime": 0.22,
            "responseRecorded": 1,
            "timeToFeedback": 0.33,
            "validTrial": 1,
            "repeatNum": 1,
            "visual": 0,
            "auditory": 0,
            "coherent": 1,
            "conflict": 0,
            "blank": 0,
            "laserType": 1,
            "galvoPositionX": 1.5,
            "galvoPositionY": 2.5,
        },
        {
            "subject": "PC001",
            "session_id": "PC001.2020-01-03.1",
            "visDiff": 0.4,
            "audDiff": -1.0,
            "visContrast": 0.4,
            "responseCalc": 1,
            "correctResponse": 1,
            "reactionTime": 0.4,
            "responseRecorded": 1,
            "timeToFeedback": 0.55,
            "validTrial": 1,
            "repeatNum": 1,
            "visual": 0,
            "auditory": 0,
            "coherent": 0,
            "conflict": 1,
            "blank": 0,
            "laserType": 0,
            "galvoPositionX": 0.0,
            "galvoPositionY": 0.0,
        },
    ]


def _combined_block():
    rows = _trial_rows()
    return {
        "exp": {
            "subject": np.array(["PC001", "PC001", "PC001"], dtype=object),
            "expDate": np.array(["2020-01-01", "2020-01-02", "2020-01-03"], dtype=object),
            "expNum": np.array([1, 1, 1]),
        },
        "tri": {
            "subjectRef": np.ones(len(rows), dtype=int),
            "expRef": np.array([1, 1, 2, 2, 3, 3]),
            "stim": {
                "visDiff": np.array([row["visDiff"] for row in rows], dtype=float),
                "audDiff": np.array([row["audDiff"] for row in rows], dtype=float),
                "visContrast": np.array([row["visContrast"] for row in rows], dtype=float),
                "correctResponse": np.array([row["correctResponse"] for row in rows], dtype=float),
                "conditionLabel": np.arange(1, len(rows) + 1),
            },
            "outcome": {
                "responseCalc": np.array([2, 1, 1, np.nan, 2, 1], dtype=float),
                "reactionTime": np.array([0.31, 0.28, 0.35, np.nan, 0.22, 0.4]),
                "responseRecorded": np.array([1, 1, 1, 0, 1, 1]),
                "timeToFeedback": np.array([0.45, 0.42, 0.51, 2.0, 0.33, 0.55]),
            },
            "trialType": {
                "validTrial": np.ones(len(rows), dtype=int),
                "repeatNum": np.ones(len(rows), dtype=int),
                "visual": np.array([row["visual"] for row in rows], dtype=int),
                "auditory": np.array([row["auditory"] for row in rows], dtype=int),
                "coherent": np.array([row["coherent"] for row in rows], dtype=int),
                "conflict": np.array([row["conflict"] for row in rows], dtype=int),
                "blank": np.array([row["blank"] for row in rows], dtype=int),
            },
            "inactivation": {
                "laserType": np.array([row["laserType"] for row in rows], dtype=int),
                "galvoPosition": np.array(
                    [[row["galvoPositionX"], row["galvoPositionY"]] for row in rows],
                    dtype=float,
                ),
                "laserOnsetDelay": np.array([0, 0, 0, 0, 0.1, 0], dtype=float),
            },
        },
    }


def _proc_block():
    tri = _combined_block()["tri"]
    return {
        "subject": "PC001",
        "expDate": "2020-01-10",
        "expNum": 2,
        "stim": tri["stim"],
        "outcome": tri["outcome"],
        "trialType": tri["trialType"],
        "inactivation": tri["inactivation"],
    }
