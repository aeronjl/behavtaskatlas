import json

import pytest

from behavtaskatlas.ibl import write_canonical_trials_csv
from behavtaskatlas.models import CanonicalTrial
from behavtaskatlas.visual_contrast_family import (
    VisualContrastFamilyPerturbationSource,
    VisualContrastFamilySource,
    analyze_visual_contrast_family,
    load_visual_contrast_family_perturbation_effects,
    load_visual_contrast_family_trials,
    write_visual_contrast_family_outputs,
)


def test_visual_contrast_family_summary_preserves_source_and_withhold(tmp_path) -> None:
    ibl_trials = [
        _trial("dataset.ibl-public-behavior", "protocol.ibl-visual-decision-v1", 0, -25, "left"),
        _trial("dataset.ibl-public-behavior", "protocol.ibl-visual-decision-v1", 1, 25, "right"),
        _trial(
            "dataset.ibl-public-behavior",
            "protocol.ibl-visual-decision-v1",
            2,
            0,
            "no-response",
            correct=None,
        ),
    ]
    unforced_trials = [
        _trial(
            "dataset.zatka-haas-visual-decision-figshare",
            "protocol.mouse-unforced-visual-contrast-wheel",
            0,
            -25,
            "left",
            laser=True,
        ),
        _trial(
            "dataset.zatka-haas-visual-decision-figshare",
            "protocol.mouse-unforced-visual-contrast-wheel",
            1,
            0,
            "withhold",
            laser=True,
        ),
    ]
    large_unforced_trials = [
        _trial(
            "dataset.large-unforced",
            "protocol.mouse-unforced-visual-contrast-wheel",
            trial_index,
            0,
            "right",
            session_id=f"large-{trial_index // 2}",
        )
        for trial_index in range(4)
    ]
    ibl_path = tmp_path / "ibl" / "trials.csv"
    unforced_path = tmp_path / "unforced" / "trials.csv"
    large_unforced_path = tmp_path / "large_unforced" / "trials.csv"
    perturbation_path = tmp_path / "zatka" / "perturbation_region_effect_summary.csv"
    write_canonical_trials_csv(ibl_path, ibl_trials)
    write_canonical_trials_csv(unforced_path, unforced_trials)
    write_canonical_trials_csv(large_unforced_path, large_unforced_trials)
    _write_perturbation_effect_csv(perturbation_path)

    sources = [
        VisualContrastFamilySource(
            source_id="ibl",
            source_label="IBL",
            slice_id="slice.ibl-visual-decision",
            trials_path=ibl_path,
        ),
        VisualContrastFamilySource(
            source_id="zatka",
            source_label="Zatka",
            slice_id="slice.zatka-haas-visual-decision",
            trials_path=unforced_path,
        ),
        VisualContrastFamilySource(
            source_id="large-unforced",
            source_label="Large Unforced",
            slice_id="slice.large-unforced",
            trials_path=large_unforced_path,
        ),
    ]
    loaded = load_visual_contrast_family_trials(sources)
    perturbation_effects = load_visual_contrast_family_perturbation_effects(
        [
            VisualContrastFamilyPerturbationSource(
                source_id="zatka",
                source_label="Zatka",
                slice_id="slice.zatka-haas-visual-decision",
                dataset_id="dataset.zatka-haas-visual-decision-figshare",
                protocol_id="protocol.mouse-unforced-visual-contrast-wheel",
                effect_path=perturbation_path,
                comparison_label="laser region vs matched non-laser signed contrast",
            )
        ]
    )
    result = analyze_visual_contrast_family(
        loaded,
        perturbation_effect_rows=perturbation_effects,
    )
    out_paths = write_visual_contrast_family_outputs(tmp_path / "derived", result)

    assert result["n_sources"] == 3
    assert result["n_trials"] == 9
    assert result["n_withhold_trials"] == 1
    assert result["n_no_response_trials"] == 1
    assert result["n_laser_trials"] == 2
    assert result["n_response_format_groups"] == 2
    assert result["n_sessions"] == 4
    assert result["n_subjects"] == 3
    assert result["n_perturbation_effect_sources"] == 1
    assert result["n_perturbation_region_effects"] == 2
    assert len(result["source_rows"]) == 3
    assert {row["response_format"] for row in result["source_rows"]} == {
        "strict_2afc_wheel",
        "unforced_wheel",
    }
    strict_zero = next(
        row
        for row in result["protocol_normalized_signed_contrast_rows"]
        if row["response_format"] == "strict_2afc_wheel" and row["stimulus_value"] == 0
    )
    unforced_zero = next(
        row
        for row in result["protocol_normalized_signed_contrast_rows"]
        if row["response_format"] == "unforced_wheel" and row["stimulus_value"] == 0
    )
    source_balanced_unforced_zero = next(
        row
        for row in result["source_balanced_protocol_normalized_rows"]
        if row["response_format"] == "unforced_wheel" and row["stimulus_value"] == 0
    )
    session_balanced_unforced_zero = next(
        row
        for row in result["session_balanced_protocol_normalized_rows"]
        if row["response_format"] == "unforced_wheel" and row["stimulus_value"] == 0
    )
    subject_balanced_unforced_zero = next(
        row
        for row in result["subject_balanced_protocol_normalized_rows"]
        if row["response_format"] == "unforced_wheel" and row["stimulus_value"] == 0
    )
    assert strict_zero["n_no_response"] == 1
    assert unforced_zero["n_withhold"] == 1
    assert unforced_zero["p_withhold"] == 0.2
    assert source_balanced_unforced_zero["mean_p_withhold"] == 0.5
    assert source_balanced_unforced_zero["sem_p_withhold"] == 0.5
    assert session_balanced_unforced_zero["n_sessions"] == 3
    assert session_balanced_unforced_zero["mean_p_withhold"] == pytest.approx(1 / 3)
    assert session_balanced_unforced_zero["sem_p_withhold"] == pytest.approx(1 / 3)
    assert subject_balanced_unforced_zero["n_subjects"] == 2
    assert subject_balanced_unforced_zero["mean_p_withhold"] == 0.5
    assert subject_balanced_unforced_zero["sem_p_withhold"] == 0.5
    assert result["perturbation_region_effect_rows"][0]["laser_region"] == "LeftVIS"
    assert result["perturbation_region_effect_rows"][0]["weighted_delta_p_right"] == -0.25
    pooled_zero = next(
        row for row in result["pooled_signed_contrast_rows"] if row["stimulus_value"] == 0
    )
    assert pooled_zero["n_withhold"] == 1
    assert pooled_zero["n_no_response"] == 1
    assert "source_id" in out_paths["source_summary"].read_text(encoding="utf-8")
    assert "stimulus_value" in out_paths["signed_contrast_summary"].read_text(encoding="utf-8")
    assert "response_format" in out_paths["response_format_summary"].read_text(
        encoding="utf-8"
    )
    assert "strict_2afc_wheel" in out_paths[
        "protocol_normalized_signed_contrast_summary"
    ].read_text(encoding="utf-8")
    assert "<svg" in out_paths["protocol_normalized_choice_svg"].read_text(
        encoding="utf-8"
    )
    assert "mean_p_withhold" in out_paths[
        "source_balanced_protocol_normalized_summary"
    ].read_text(encoding="utf-8")
    assert "<svg" in out_paths["source_balanced_protocol_normalized_svg"].read_text(
        encoding="utf-8"
    )
    assert "mean_session_n_trials" in out_paths[
        "session_balanced_protocol_normalized_summary"
    ].read_text(encoding="utf-8")
    assert "<svg" in out_paths["session_balanced_protocol_normalized_svg"].read_text(
        encoding="utf-8"
    )
    assert "mean_subject_n_trials" in out_paths[
        "subject_balanced_protocol_normalized_summary"
    ].read_text(encoding="utf-8")
    assert "<svg" in out_paths["subject_balanced_protocol_normalized_svg"].read_text(
        encoding="utf-8"
    )
    assert "weighted_delta_p_right" in out_paths[
        "perturbation_region_effect_summary"
    ].read_text(encoding="utf-8")
    assert "<svg" in out_paths["perturbation_region_effects_svg"].read_text(
        encoding="utf-8"
    )
    assert "Visual Contrast Family Summary" in out_paths["report"].read_text(encoding="utf-8")
    assert "Protocol-Normalized Choice" in out_paths["report"].read_text(encoding="utf-8")
    assert "Source-Balanced Protocol-Normalized Choice" in out_paths[
        "report"
    ].read_text(encoding="utf-8")
    assert "Session-Balanced Protocol-Normalized Choice" in out_paths[
        "report"
    ].read_text(encoding="utf-8")
    assert "Subject-Balanced Protocol-Normalized Choice" in out_paths[
        "report"
    ].read_text(encoding="utf-8")
    assert "Perturbation Region Effects" in out_paths["report"].read_text(encoding="utf-8")
    assert json.loads(out_paths["analysis_result"].read_text(encoding="utf-8"))["n_trials"] == 9


def _trial(
    dataset_id: str,
    protocol_id: str,
    trial_index: int,
    stimulus_value: float,
    choice: str,
    *,
    correct: bool | None = True,
    laser: bool = False,
    session_id: str = "session",
) -> CanonicalTrial:
    task_variables = {}
    if laser:
        task_variables = {"laser_type": 1.0, "laser_power": 4.25}
    return CanonicalTrial(
        protocol_id=protocol_id,
        dataset_id=dataset_id,
        subject_id="mouse",
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=stimulus_value,
        stimulus_units="percent contrast",
        stimulus_side="right" if stimulus_value > 0 else "left" if stimulus_value < 0 else "none",
        evidence_strength=abs(stimulus_value),
        evidence_units="percent contrast",
        choice=choice,
        correct=correct,
        response_time=0.4,
        response_time_origin="synthetic",
        feedback="reward" if correct else "error" if correct is False else "unknown",
        task_variables=task_variables,
        source={},
    )


def _write_perturbation_effect_csv(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                (
                    "laser_region,region_family,hemisphere,n_matched_contrasts,"
                    "stimulus_values,n_laser_trials,n_non_laser_trials,"
                    "weighted_delta_p_right,weighted_delta_p_withhold,"
                    "weighted_delta_p_correct,weighted_delta_median_response_time,"
                    "max_abs_delta_p_right,max_abs_delta_p_withhold"
                ),
                (
                    "LeftVIS,VIS,left,3,\"-25,0,25\",10,30,-0.25,0.1,-0.05,"
                    "0.02,0.4,0.2"
                ),
                (
                    "RightVIS,VIS,right,3,\"-25,0,25\",11,30,0.2,0.08,-0.04,"
                    "0.01,0.35,0.18"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
