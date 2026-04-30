import csv
import json
import zipfile

import pytest

from behavtaskatlas.fritsche import (
    FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID,
    FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
    analyze_fritsche_temporal_regularities,
    build_fritsche_code_manifest,
    fritsche_artifact_provenance_rows,
    fritsche_temporal_regularities_provenance_payload,
    harmonize_fritsche_temporal_regularities_row,
    harmonize_fritsche_temporal_regularities_rows,
    load_fritsche_temporal_regularities_rows,
    write_fritsche_artifact_provenance_csv,
    write_fritsche_code_manifest,
)
from behavtaskatlas.models import CanonicalTrial


def test_fritsche_harmonizes_temporal_regularities_rows(tmp_path) -> None:
    zip_path = _write_fritsche_zip(tmp_path)
    source_rows, details = load_fritsche_temporal_regularities_rows(
        zip_path,
        experiments=["exp1_transitional_regularities"],
    )
    trials = harmonize_fritsche_temporal_regularities_rows(source_rows)

    assert details["n_rows"] == 4
    assert details["source_files"][0]["member"] == "data/data_exp1_transitional_regularities.csv"
    assert len(trials) == 4
    assert trials[0].protocol_id == FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID
    assert trials[0].dataset_id == FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID
    assert trials[0].subject_id == "MFE001"
    assert trials[0].session_id == "2024-01-01_1_MFE001"
    assert trials[0].stimulus_value == 25.0
    assert trials[0].stimulus_side == "right"
    assert trials[0].choice == "right"
    assert trials[0].correct is True
    assert trials[0].feedback == "reward"
    assert trials[0].response_time == pytest.approx(0.3)
    assert trials[0].prior_context == "Repeating"
    assert trials[0].task_variables["environment"] == "Repeating"
    assert trials[0].task_variables["right_contrast"] == 25.0
    assert trials[1].stimulus_value == -50.0
    assert trials[1].choice == "left"
    assert trials[2].choice == "no-response"
    assert trials[2].response_time is None
    assert trials[3].prior_context == "Alternating"


def test_fritsche_analysis_groups_by_environment(tmp_path) -> None:
    source_rows, details = load_fritsche_temporal_regularities_rows(_write_fritsche_zip(tmp_path))
    trials = harmonize_fritsche_temporal_regularities_rows(source_rows)
    result = analyze_fritsche_temporal_regularities(trials)
    provenance = fritsche_temporal_regularities_provenance_payload(
        zip_file=tmp_path / "source.zip",
        details=details,
        trials=trials,
        output_files={"trials": "trials.csv"},
    )

    assert result["analysis_type"] == "descriptive_psychometric"
    assert result["n_trials"] == 5
    assert result["n_subjects"] == 2
    assert result["n_sessions"] == 2
    assert result["environments"] == ["Alternating", "Neutral", "Repeating"]
    assert result["n_experiments"] == 2
    assert result["n_lagged_trials"] == 3
    assert result["n_choice_history_model_fits"] >= 1
    repeating_zero = next(
        row
        for row in result["summary_rows"]
        if row["prior_context"] == "Repeating" and row["stimulus_value"] == 0
    )
    assert repeating_zero["n_no_response"] == 1
    alternating_transition = next(
        row
        for row in result["transition_rows"]
        if row["environment"] == "Repeating"
        and row["transition_type"] == "alternate_stimulus_side"
    )
    assert alternating_transition["previous_stimulus_side"] == "right"
    assert alternating_transition["current_stimulus_side"] == "left"
    assert alternating_transition["n_trials"] == 1
    assert alternating_transition["p_choice_repeat"] == 0
    previous_reward_left = next(
        row
        for row in result["choice_history_rows"]
        if row["environment"] == "Repeating"
        and row["previous_choice"] == "left"
        and row["previous_feedback"] == "reward"
    )
    assert previous_reward_left["n_trials"] == 1
    assert previous_reward_left["n_choice_pairs"] == 0
    subject_row = next(
        row
        for row in result["subject_environment_rows"]
        if row["subject_id"] == "MFE001" and row["environment"] == "Repeating"
    )
    assert subject_row["n_trials"] == 3
    assert subject_row["n_lagged_trials"] == 2
    assert subject_row["p_stimulus_side_repeat"] == 0
    assert provenance["source"]["n_source_rows"] == 5
    assert provenance["exclusions"]["no_response_choices"] == 1


def test_fritsche_choice_history_logistic_model_estimates_previous_choice() -> None:
    trials = _choice_history_trials()
    result = analyze_fritsche_temporal_regularities(trials)
    previous_choice_row = next(
        row
        for row in result["choice_history_model_term_rows"]
        if row["model_scope"] == "all_experiments"
        and row["environment"] == "Repeating"
        and row["term"] == "previous_choice_right"
    )

    assert result["n_choice_history_model_ok"] == 2
    assert previous_choice_row["status"] == "ok"
    assert previous_choice_row["n_trials"] == 119
    assert previous_choice_row["coefficient_log_odds"] > 0
    assert previous_choice_row["standard_error"] > 0


def test_fritsche_neutral_adaptation_tracks_previous_sequence_exposure() -> None:
    trials = (
        _session_trials("2024-01-01_1_MFE-adapt", 1, "Repeating")
        + _session_trials("2024-01-02_1_MFE-adapt", 2, "Neutral")
        + _session_trials("2024-01-03_1_MFE-adapt", 3, "Neutral")
        + _session_trials("2024-01-04_1_MFE-adapt", 4, "Alternating")
        + _session_trials("2024-01-05_1_MFE-adapt", 5, "Neutral")
    )
    result = analyze_fritsche_temporal_regularities(trials)
    session_rows = result["neutral_adaptation_session_rows"]

    assert result["n_neutral_adaptation_sessions"] == 3
    first_neutral = next(row for row in session_rows if row["session_num"] == 2)
    second_neutral = next(row for row in session_rows if row["session_num"] == 3)
    post_alternating = next(row for row in session_rows if row["session_num"] == 5)
    assert first_neutral["previous_non_neutral_environment"] == "Repeating"
    assert first_neutral["neutral_day_index"] == 1
    assert second_neutral["previous_non_neutral_environment"] == "Repeating"
    assert second_neutral["neutral_day_index"] == 2
    assert post_alternating["previous_non_neutral_environment"] == "Alternating"
    assert post_alternating["neutral_day_index"] == 1

    repeating_day_1 = next(
        row
        for row in result["neutral_adaptation_rows"]
        if row["previous_non_neutral_environment"] == "Repeating"
        and row["neutral_day_index"] == 1
    )
    assert repeating_day_1["n_sessions"] == 1
    assert repeating_day_1["n_subjects"] == 1
    assert repeating_day_1["p_correct"] == 1


def test_fritsche_code_manifest_inventories_scripts_and_reuse_decisions(tmp_path) -> None:
    code_zip = tmp_path / "code.zip"
    with zipfile.ZipFile(code_zip, "w") as archive:
        archive.writestr(
            "code/1_behavioral_analysis.r",
            "\n".join(
                [
                    'data <- read_csv("../data/data_exp1_transitional_regularities.csv")',
                    "data <- data %>% mutate(environment = empRepeatProb)",
                    "fit <- glmnet::glmnet(x, y)",
                ]
            ),
        )
        archive.writestr(
            "code/5_adaptation_analysis.r",
            "\n".join(
                [
                    'data <- read_csv("../data/data_exp2_adaptation_test.csv")',
                    "data_hist <- data %>% mutate(p1_altitude = lag(altitude,1))",
                    "fit <- quickpsy(fit_data, x = contrast, k = choice_int)",
                ]
            ),
        )
        archive.writestr(
            "code/4_rl_model/fitting_pompd_main.m",
            "data = readtable('Grating2AFC_TransProb_behav_history_clean_4fitting.csv');",
        )
        archive.writestr("code/3_hidden_markov_model/fit_models/model.pickle", b"binary")

    manifest = build_fritsche_code_manifest(code_zip)
    manifest_path = tmp_path / "code_manifest.json"
    write_fritsche_code_manifest(manifest_path, manifest)
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert loaded["analysis_type"] == "source_code_manifest"
    assert loaded["dataset_id"] == FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID
    assert loaded["zip"]["n_files"] == 4
    assert loaded["zip"]["n_reused_reference_scripts"] == 2
    script_by_path = {row["path"]: row for row in loaded["source_scripts"]}
    assert script_by_path["code/5_adaptation_analysis.r"]["atlas_status"] == (
        "reused_as_reference"
    )
    assert script_by_path["code/5_adaptation_analysis.r"]["sha256"]
    assert "../data/data_exp2_adaptation_test.csv" in {
        row["path"] for row in loaded["source_data_dependencies"]
    }
    assert {
        row["decision"] for row in loaded["atlas_reuse_decisions"]
    } >= {"reused", "reused_as_reference", "deferred"}
    assert any(row["pattern"] == "lagged_history" for row in loaded["operational_line_references"])


def test_fritsche_artifact_provenance_links_outputs_to_source_scripts(tmp_path) -> None:
    rows = fritsche_artifact_provenance_rows(
        derived_dir=tmp_path / "derived",
        session_id="fritsche-test",
    )
    provenance_path = tmp_path / "artifact_provenance.csv"
    write_fritsche_artifact_provenance_csv(provenance_path, rows)
    loaded = list(csv.DictReader(provenance_path.open(encoding="utf-8", newline="")))
    by_file = {row["artifact_path"].split("/")[-1]: row for row in loaded}

    assert len(loaded) == 15
    assert set(by_file) >= {
        "trials.csv",
        "choice_history_model_coefficients.csv",
        "code_manifest.json",
        "artifact_provenance.csv",
    }
    trials = by_file["trials.csv"]
    assert trials["generated_by_cli"] == "fritsche-harmonize"
    assert "data/data_exp1_transitional_regularities.csv" in trials["source_data_files"]
    assert "contrastLeft" in trials["source_fields"]
    assert "code/1_behavioral_analysis.r" in trials["source_scripts"]
    assert "code/5_adaptation_analysis.r" in trials["source_scripts"]
    assert by_file["code_manifest.json"]["source_script_status"] == "hashed_and_classified"
    assert by_file["artifact_provenance.csv"]["reuse_decision"] == "generated"


def test_fritsche_rejects_unknown_experiment(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unknown Fritsche experiment"):
        load_fritsche_temporal_regularities_rows(
            _write_fritsche_zip(tmp_path),
            experiments=["not-an-experiment"],
        )


def test_fritsche_row_requires_core_fields() -> None:
    with pytest.raises(ValueError, match="Missing required Fritsche source fields"):
        harmonize_fritsche_temporal_regularities_row({}, trial_index=0)


def _write_fritsche_zip(tmp_path):
    zip_path = tmp_path / "source.zip"
    fieldnames = [
        "mouseName",
        "sessionNum",
        "expRef",
        "stage",
        "repeatIncorrect",
        "trialNumber",
        "repeatNumber",
        "rewardContingency",
        "contrastLeft",
        "contrastRight",
        "correctResponse",
        "choice",
        "choiceCompleteTime",
        "choiceStartTime",
        "feedback",
        "punishSoundOnsetTime",
        "environment",
        "stimulusOnsetTime",
        "goCueTime",
        "rewardTime",
        "rewardVolume",
    ]
    exp1_rows = [
        _row(
            "MFE001",
            "2024-01-01_1_MFE001",
            trial_number=1,
            contrast_left="0",
            contrast_right="0.25",
            correct_response="Right",
            choice="Right",
            feedback="Rewarded",
            environment="Repeating",
        ),
        _row(
            "MFE001",
            "2024-01-01_1_MFE001",
            trial_number=2,
            contrast_left="0.5",
            contrast_right="0",
            correct_response="Left",
            choice="Left",
            feedback="Rewarded",
            environment="Repeating",
        ),
        _row(
            "MFE001",
            "2024-01-01_1_MFE001",
            trial_number=3,
            contrast_left="0",
            contrast_right="0",
            correct_response="Left",
            choice="NoGo",
            feedback="Unrewarded",
            environment="Repeating",
            choice_start="NaN",
        ),
        _row(
            "MFE001",
            "2024-01-01_1_MFE001",
            trial_number=4,
            contrast_left="0",
            contrast_right="1",
            correct_response="Right",
            choice="Left",
            feedback="Unrewarded",
            environment="Alternating",
        ),
    ]
    exp2_rows = [
        _row(
            "MFE002",
            "2024-01-02_1_MFE002",
            trial_number=1,
            contrast_left="0",
            contrast_right="0.125",
            correct_response="Right",
            choice="Right",
            feedback="Rewarded",
            environment="Neutral",
        )
    ]
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "data/data_exp1_transitional_regularities.csv",
            _csv_text(fieldnames, exp1_rows),
        )
        archive.writestr("data/data_exp2_adaptation_test.csv", _csv_text(fieldnames, exp2_rows))
        archive.writestr(
            "data/data_exp3_photometry_behavior.csv",
            _csv_text(fieldnames, []),
        )
    return zip_path


def _row(
    mouse,
    session,
    *,
    trial_number,
    contrast_left,
    contrast_right,
    correct_response,
    choice,
    feedback,
    environment,
    choice_start="1.3",
):
    return {
        "mouseName": mouse,
        "sessionNum": "1",
        "expRef": session,
        "stage": "fullTask",
        "repeatIncorrect": "FALSE",
        "trialNumber": str(trial_number),
        "repeatNumber": "1",
        "rewardContingency": "SymmetricReward",
        "contrastLeft": contrast_left,
        "contrastRight": contrast_right,
        "correctResponse": correct_response,
        "choice": choice,
        "choiceCompleteTime": "1.4",
        "choiceStartTime": choice_start,
        "feedback": feedback,
        "punishSoundOnsetTime": "NaN",
        "environment": environment,
        "stimulusOnsetTime": "1.0",
        "goCueTime": "1.1",
        "rewardTime": "1.5" if feedback == "Rewarded" else "NaN",
        "rewardVolume": "3" if feedback == "Rewarded" else "NaN",
    }


def _csv_text(fieldnames, rows):
    from io import StringIO

    handle = StringIO()
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def _choice_history_trials():
    trials = []
    for index in range(120):
        choice = "right" if (index // 4) % 2 == 0 else "left"
        stimulus_value = 25.0 if index % 2 == 0 else -25.0
        stimulus_side = "right" if stimulus_value > 0 else "left"
        feedback = "error" if index % 5 == 0 else "reward"
        trials.append(
            CanonicalTrial(
                protocol_id=FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
                dataset_id=FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID,
                subject_id="MFE-history",
                session_id="history-session",
                trial_index=index,
                stimulus_modality="visual",
                stimulus_value=stimulus_value,
                stimulus_units="percent contrast, signed right positive",
                stimulus_side=stimulus_side,
                evidence_strength=abs(stimulus_value),
                evidence_units="percent contrast",
                choice=choice,
                correct=feedback == "reward",
                response_time=0.3,
                response_time_origin="synthetic",
                feedback=feedback,
                block_id="Repeating",
                prior_context="Repeating",
                training_stage="synthetic",
                task_variables={
                    "experiment": "exp1_transitional_regularities",
                    "environment": "Repeating",
                    "source_trial_number": index + 1,
                },
            )
        )
    return trials


def _session_trials(session_id, session_num, environment):
    trials = []
    for offset, choice in enumerate(["right", "left", "right", "left"]):
        stimulus_value = 25.0 if choice == "right" else -25.0
        trials.append(
            CanonicalTrial(
                protocol_id=FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
                dataset_id=FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID,
                subject_id="MFE-adapt",
                session_id=session_id,
                trial_index=(session_num - 1) * 10 + offset,
                stimulus_modality="visual",
                stimulus_value=stimulus_value,
                stimulus_units="percent contrast, signed right positive",
                stimulus_side="right" if choice == "right" else "left",
                evidence_strength=abs(stimulus_value),
                evidence_units="percent contrast",
                choice=choice,
                correct=True,
                response_time=0.25 + 0.01 * offset,
                response_time_origin="synthetic",
                feedback="reward",
                block_id=environment,
                prior_context=environment,
                training_stage="synthetic",
                task_variables={
                    "experiment": "exp1_transitional_regularities",
                    "environment": environment,
                    "session_num": session_num,
                    "source_trial_number": offset + 1,
                },
            )
        )
    return trials
