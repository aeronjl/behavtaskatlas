import json
import math
import zipfile

import numpy as np
import pytest
from scipy.io import savemat

from behavtaskatlas.ibl import load_canonical_trials_csv, write_canonical_trials_csv
from behavtaskatlas.zatka_haas import (
    ZATKA_HAAS_DATASET_ID,
    ZATKA_HAAS_PROTOCOL_ID,
    analyze_zatka_haas_visual_decision,
    build_zatka_haas_code_manifest,
    harmonize_zatka_haas_visual_trials,
    load_zatka_haas_processed_mat,
    summarize_zatka_haas_choice_by_contrast_pair,
    summarize_zatka_haas_choice_by_signed_contrast,
    summarize_zatka_haas_perturbation_deltas,
    write_zatka_haas_choice_svg,
    write_zatka_haas_code_manifest,
    write_zatka_haas_condition_csv,
    write_zatka_haas_laser_region_csv,
    write_zatka_haas_laser_state_csv,
    write_zatka_haas_perturbation_delta_csv,
    write_zatka_haas_perturbation_region_effect_csv,
    write_zatka_haas_report_html,
    write_zatka_haas_summary_csv,
    zatka_haas_choice_label,
    zatka_haas_provenance_payload,
)


def test_zatka_haas_code_manifest_extracts_loader_and_choice_encoding(tmp_path) -> None:
    code_zip = tmp_path / "code.zip"
    with zipfile.ZipFile(code_zip, "w") as archive:
        archive.writestr(
            "Fig1.m",
            "\n".join(
                [
                    "load('../data/inactivation/Inactivation_HigherPower.mat','D');",
                    "fit = load('../data/modelFits/fit_psych_model_with_inactivations.mat');",
                    "dat = struct('contrastLeft', D.stimulus(:,1), 'choice', D.response);",
                ]
            ),
        )
        archive.writestr(
            "utility/loadBehaviouralData.m",
            "\n".join(
                [
                    (
                        "D.stimulus = [block.events.contrastLeftValues' "
                        "block.events.contrastRightValues'];"
                    ),
                    "D.response(D.response==0) = 3;",
                    "D.feedbackType = block.events.feedbackValues';",
                    "D.RT = D.time_startMove - D.time_goCue;",
                ]
            ),
        )
        archive.writestr(
            "utility/stanModels/Two-Level.stan",
            "int<lower=1,upper=3> choice[numTrials]; // 1=Left, 2=Right, 3=NoGo",
        )
        archive.writestr(
            "utility/neuropixels_inclusionData/trials/Cori_2016-12-14_hasLeft.npy",
            b"npy",
        )

    manifest = build_zatka_haas_code_manifest(code_zip)
    manifest_path = tmp_path / "manifest.json"
    write_zatka_haas_code_manifest(manifest_path, manifest)
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert loaded["dataset_id"] == ZATKA_HAAS_DATASET_ID
    assert loaded["zip"]["root_scripts"] == ["Fig1.m"]
    assert "../data/inactivation/Inactivation_HigherPower.mat" in {
        row["path"] for row in loaded["source_data_dependencies"]
    }
    assert "stimulus" in loaded["behavior_field_candidates"]
    assert "response" in loaded["behavior_field_candidates"]
    assert loaded["neuropixels_inclusion_files"]["trial_file_count"] == 1
    assert loaded["stan_choice_encoding_evidence"] == [
        {"file": "utility/stanModels/Two-Level.stan", "line": 1}
    ]


def test_load_and_harmonize_zatka_haas_processed_mat(tmp_path) -> None:
    mat_path = _write_processed_mat(tmp_path)
    source = load_zatka_haas_processed_mat(mat_path)
    trials = harmonize_zatka_haas_visual_trials(source, session_id="fallback-session")

    assert len(trials) == 4
    assert trials[0].protocol_id == ZATKA_HAAS_PROTOCOL_ID
    assert trials[0].dataset_id == ZATKA_HAAS_DATASET_ID
    assert trials[0].subject_id == "7"
    assert trials[0].session_id == "11"
    assert trials[0].stimulus_value == 100.0
    assert trials[0].stimulus_side == "right"
    assert trials[0].choice == "right"
    assert trials[0].correct is True
    assert trials[0].response_time == pytest.approx(0.33)
    assert trials[0].response_time_origin == "D.RT"
    assert trials[0].task_variables["laser_type"] == 0
    assert trials[1].stimulus_value == -50.0
    assert trials[1].choice == "left"
    assert trials[2].choice == "withhold"
    assert trials[2].stimulus_side == "none"
    assert trials[2].task_variables["no_go_condition"] is True
    assert trials[3].stimulus_side == "unknown"
    assert trials[3].task_variables["bilateral_condition"] is True
    assert trials[3].task_variables["laser_type"] == 1
    assert zatka_haas_choice_label(3) == "withhold"


def test_load_zatka_haas_v73_hdf5_table(tmp_path) -> None:
    mat_path = _write_hdf5_table_mat(tmp_path)
    source = load_zatka_haas_processed_mat(mat_path)
    trials = harmonize_zatka_haas_visual_trials(source, session_id="higher-power")

    assert set(source) >= {"stimulus", "response", "feedbackType", "laserRegion"}
    assert source["stimulus"].shape == (4, 2)
    assert source["laserRegion"].tolist() == [None, "LeftVIS", None, "RightM2"]
    assert len(trials) == 4
    assert trials[0].stimulus_value == 100.0
    assert trials[1].choice == "left"
    assert trials[1].correct is False
    assert trials[1].feedback == "error"
    assert trials[1].task_variables["laser_region"] == "LeftVIS"
    assert trials[3].task_variables["laser_coord"] == [1.0, -1.0]


def test_zatka_haas_summaries_outputs_and_provenance_round_trip(tmp_path) -> None:
    source = load_zatka_haas_processed_mat(_write_processed_mat(tmp_path))
    trials = harmonize_zatka_haas_visual_trials(source, session_id="fallback-session")
    summary = summarize_zatka_haas_choice_by_signed_contrast(trials)
    conditions = summarize_zatka_haas_choice_by_contrast_pair(trials)
    perturbation_deltas = summarize_zatka_haas_perturbation_deltas(trials)
    result = analyze_zatka_haas_visual_decision(trials)

    zero_row = next(row for row in summary if row["stimulus_value"] == 0.0)
    left_m2_delta = next(row for row in perturbation_deltas if row["laser_region"] == "LeftM2")
    assert len(summary) == 3
    assert len(conditions) == 4
    assert zero_row["n_trials"] == 2
    assert zero_row["n_right"] == 1
    assert zero_row["n_withhold"] == 1
    assert zero_row["p_withhold"] == 0.5
    assert result["n_laser_trials"] == 1
    assert result["n_withhold_trials"] == 1
    assert {row["laser_state"] for row in result["laser_state_rows"]} == {
        "non_laser",
        "laser",
    }
    assert "LeftM2" in {row["laser_region"] for row in result["laser_region_rows"]}
    assert result["perturbation_delta_count"] == 1
    assert result["perturbation_region_effect_count"] == 1
    assert left_m2_delta["region_family"] == "M2"
    assert left_m2_delta["hemisphere"] == "left"
    assert left_m2_delta["delta_p_withhold"] == -1.0
    assert left_m2_delta["delta_p_right"] is None
    assert result["perturbation_region_effect_rows"][0]["weighted_delta_p_withhold"] == -1.0

    artifact_dir = tmp_path / "derived"
    trials_path = artifact_dir / "trials.csv"
    summary_path = artifact_dir / "choice_summary.csv"
    svg_path = artifact_dir / "choice_summary.svg"
    condition_path = artifact_dir / "condition_summary.csv"
    laser_state_path = artifact_dir / "laser_state_summary.csv"
    laser_region_path = artifact_dir / "laser_region_summary.csv"
    perturbation_delta_path = artifact_dir / "perturbation_delta_summary.csv"
    perturbation_region_effect_path = artifact_dir / "perturbation_region_effect_summary.csv"
    report_path = artifact_dir / "report.html"
    write_canonical_trials_csv(trials_path, trials)
    write_zatka_haas_summary_csv(summary_path, summary)
    write_zatka_haas_choice_svg(svg_path, summary)
    write_zatka_haas_condition_csv(condition_path, conditions)
    write_zatka_haas_laser_state_csv(laser_state_path, result["laser_state_rows"])
    write_zatka_haas_laser_region_csv(laser_region_path, result["laser_region_rows"])
    write_zatka_haas_perturbation_delta_csv(
        perturbation_delta_path,
        result["perturbation_delta_rows"],
    )
    write_zatka_haas_perturbation_region_effect_csv(
        perturbation_region_effect_path,
        result["perturbation_region_effect_rows"],
    )
    provenance = zatka_haas_provenance_payload(
        source_file=tmp_path / "source.mat",
        session_id="fallback-session",
        details={
            "source_fields": sorted(source),
            "n_trials": 4,
            "source_variable": "D",
        },
        trials=trials,
        output_files={"trials": str(trials_path)},
    )

    assert load_canonical_trials_csv(trials_path) == trials
    assert "n_laser_trials" in summary_path.read_text(encoding="utf-8")
    assert "<svg" in svg_path.read_text(encoding="utf-8")
    assert "right_contrast" in condition_path.read_text(encoding="utf-8")
    assert "laser_state" in laser_state_path.read_text(encoding="utf-8")
    assert "laser_region" in laser_region_path.read_text(encoding="utf-8")
    assert "delta_p_withhold" in perturbation_delta_path.read_text(encoding="utf-8")
    assert "weighted_delta_p_withhold" in perturbation_region_effect_path.read_text(
        encoding="utf-8"
    )
    assert provenance["exclusions"]["withhold_choices"] == 1
    assert provenance["exclusions"]["laser_trials"] == 1
    assert json.loads(json.dumps(result))["n_trials"] == 4
    write_zatka_haas_report_html(
        report_path,
        result,
        provenance=provenance,
        choice_svg_text=svg_path.read_text(encoding="utf-8"),
        artifact_links={"Trials": "trials.csv"},
    )
    report_html = report_path.read_text(encoding="utf-8")
    assert "Zatka-Haas" in report_html
    assert "Laser trials" in report_html
    assert "Laser-State Summary" in report_html
    assert "Laser-Region Summary" in report_html
    assert "Perturbation Deltas vs Non-Laser" in report_html
    assert "Perturbation Region Effects" in report_html


def test_load_zatka_haas_processed_mat_requires_core_fields(tmp_path) -> None:
    mat_path = tmp_path / "bad.mat"
    savemat(mat_path, {"D": {"stimulus": np.zeros((2, 2))}})

    with pytest.raises(ValueError, match="Missing required Zatka-Haas fields"):
        load_zatka_haas_processed_mat(mat_path)


def _write_processed_mat(tmp_path):
    mat_path = tmp_path / "zatka.mat"
    source = {
        "stimulus": np.array(
            [
                [0.0, 1.0],
                [0.5, 0.0],
                [0.0, 0.0],
                [0.25, 0.25],
            ]
        ),
        "response": np.array([[2], [1], [3], [2]]),
        "feedbackType": np.array([[1], [1], [1], [-1]]),
        "RT": np.array([[0.33], [0.42], [math.nan], [0.51]]),
        "sessionID": np.array([[11], [11], [12], [12]]),
        "subjectID": np.array([[7], [7], [8], [8]]),
        "repeatNum": np.array([[1], [1], [2], [1]]),
        "laserType": np.array([[0], [0], [0], [1]]),
        "laserPower": np.array([[0.0], [0.0], [0.0], [1.5]]),
        "laserRegion": np.array(["", "", "", "LeftM2"], dtype=object).reshape(4, 1),
        "laserCoord": np.array(
            [
                [math.nan, math.nan],
                [math.nan, math.nan],
                [math.nan, math.nan],
                [1.0, 2.0],
            ]
        ),
        "prev_response": np.array([[math.nan], [2], [1], [3]]),
        "prev_feedback": np.array([[math.nan], [1], [1], [1]]),
    }
    savemat(mat_path, {"D": source})
    return mat_path


def _write_hdf5_table_mat(tmp_path):
    h5py = pytest.importorskip("h5py")
    mat_path = tmp_path / "zatka_v73.mat"
    with h5py.File(mat_path, "w") as handle:
        refs = handle.create_group("#refs#")
        fields = [
            "stimulus",
            "feedbackType",
            "response",
            "RT",
            "laserRegion",
            "laserType",
            "laserPower",
            "sessionID",
            "subjectID",
            "laserCoord",
        ]

        def char_dataset(key, text):
            data = np.asarray([ord(char) for char in text], dtype=np.uint16).reshape(-1, 1)
            dataset = refs.create_dataset(key, data=data)
            dataset.attrs["MATLAB_class"] = np.bytes_("char")
            return dataset.ref

        name_refs = np.empty((len(fields), 1), dtype=h5py.ref_dtype)
        for index, field in enumerate(fields):
            name_refs[index, 0] = char_dataset(f"name_{index}", field)
        names = refs.create_dataset("1", data=name_refs)
        names.attrs["MATLAB_class"] = np.bytes_("cell")

        value_refs = np.empty((len(fields), 1), dtype=h5py.ref_dtype)
        values = {
            "stimulus": np.asarray(
                [
                    [0.0, 0.5, 0.0, 0.25],
                    [1.0, 0.0, 0.0, 0.25],
                ],
                dtype=float,
            ),
            "feedbackType": np.asarray([[1.0, 0.0, 1.0, 1.0]], dtype=float),
            "response": np.asarray([[2.0, 1.0, 3.0, 2.0]], dtype=float),
            "RT": np.asarray([[0.33, 0.42, np.nan, 0.51]], dtype=float),
            "laserRegion": np.asarray([[3707764736, 2, 1, 1, 2, 1]], dtype=np.uint32),
            "laserType": np.asarray([[0.0, 1.0, 0.0, 1.0]], dtype=float),
            "laserPower": np.asarray([[0.0, 4.25, 0.0, 4.25]], dtype=float),
            "sessionID": np.asarray([[11.0, 11.0, 12.0, 12.0]], dtype=float),
            "subjectID": np.asarray([[7.0, 7.0, 8.0, 8.0]], dtype=float),
            "laserCoord": np.asarray(
                [
                    [np.nan, -3.5, np.nan, 1.0],
                    [np.nan, -0.5, np.nan, -1.0],
                ],
                dtype=float,
            ),
        }
        for index, field in enumerate(fields):
            dataset = refs.create_dataset(f"value_{index}", data=values[field])
            dataset.attrs["MATLAB_class"] = np.bytes_("double")
            value_refs[index, 0] = dataset.ref
        table_values = refs.create_dataset("y", data=value_refs)
        table_values.attrs["MATLAB_class"] = np.bytes_("cell")

        category_refs = np.empty((1, 2), dtype=h5py.ref_dtype)
        category_refs[0, 0] = char_dataset("category_0", "LeftVIS")
        category_refs[0, 1] = char_dataset("category_1", "RightM2")
        categories = refs.create_dataset("c", data=category_refs)
        categories.attrs["MATLAB_class"] = np.bytes_("cell")
        codes = refs.create_dataset("x", data=np.asarray([[0, 1, 0, 2]], dtype=np.uint8))
        codes.attrs["MATLAB_class"] = np.bytes_("uint8")

        table = handle.create_dataset(
            "D",
            data=np.asarray([[3707764736, 2, 1, 1, 1, 2]], dtype=np.uint32),
        )
        table.attrs["MATLAB_class"] = np.bytes_("table")
    return mat_path
