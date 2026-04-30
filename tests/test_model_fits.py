import csv
import json
from datetime import date

import numpy as np
import pytest

from behavtaskatlas.model_fits import clicks as clicks_module
from behavtaskatlas.model_fits.accuracy import (
    fit as fit_accuracy_strength,
)
from behavtaskatlas.model_fits.accuracy import (
    fit_rate_null as fit_accuracy_rate_null,
)
from behavtaskatlas.model_fits.bernoulli import (
    fit as fit_bernoulli_rate,
)
from behavtaskatlas.model_fits.bernoulli import (
    fit_saturated as fit_bernoulli_saturated,
)
from behavtaskatlas.model_fits.chronometric import (
    fit as fit_chronometric_rt,
)
from behavtaskatlas.model_fits.chronometric import (
    fit_constant as fit_chronometric_constant_rt,
)
from behavtaskatlas.model_fits.sdt import fit_yes_no
from behavtaskatlas.model_layer import (
    _model_coverage_gaps,
    build_model_coverage_roadmap,
    build_models_index,
    infer_model_fit_caveat_tags,
    model_coverage_roadmap_csv_rows,
    model_fit_comparison_scope,
    model_selection_confidence,
    model_selection_csv_rows,
)
from behavtaskatlas.models import (
    CurvePoint,
    Finding,
    FitMethod,
    FitProvenance,
    ModelFamily,
    ModelFit,
    ModelVariant,
    Provenance,
    ResultCurve,
    StratificationKey,
)


def _yes_no_finding(points: list[CurvePoint]) -> Finding:
    return Finding(
        object_type="finding",
        schema_version="0.1.0",
        id="finding.demo.yes-no",
        paper_id="paper.demo",
        protocol_id="protocol.demo",
        dataset_id="dataset.demo",
        source_data_level="raw-trial",
        n_trials=sum(point.n for point in points),
        stratification=StratificationKey(condition="yes_no"),
        curve=ResultCurve(
            curve_type="hit_rate_by_condition",
            x_label="Signal present",
            x_units="binary",
            y_label="p_go",
            points=points,
        ),
        extraction_method="harmonized-pipeline",
        provenance=Provenance(
            curators=["test"],
            created=date.today(),
            updated=date.today(),
        ),
    )


def _model_family(
    family_id: str,
    curve_types: list[str],
) -> ModelFamily:
    return ModelFamily(
        object_type="model_family",
        schema_version="0.1.0",
        id=family_id,
        name=family_id,
        description="Test model family.",
        parameter_definitions=[],
        applicable_curve_types=curve_types,
        curation_status="test",
        provenance=Provenance(
            curators=["test"],
            created=date.today(),
            updated=date.today(),
        ),
    )


def _model_variant(
    variant_id: str,
    family_id: str,
    requires: list[str],
) -> ModelVariant:
    return ModelVariant(
        object_type="model_variant",
        schema_version="0.1.0",
        id=variant_id,
        family_id=family_id,
        name=variant_id,
        description="Test model variant.",
        free_parameters=[],
        requires=requires,
        curation_status="test",
        provenance=Provenance(
            curators=["test"],
            created=date.today(),
            updated=date.today(),
        ),
    )


def test_yes_no_sdt_fits_binary_signal_axis() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=100, y=0.1),
            CurvePoint(x=1.0, n=100, y=0.8),
        ]
    )

    result = fit_yes_no(finding)

    assert result["success"] is True
    assert result["parameters"]["d_prime"] > 0
    assert len(result["predictions"]) == 2
    assert result["quality"]["n_free_params"] == pytest.approx(2.0)


def test_yes_no_sdt_rejects_non_binary_condition_axis() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=100, y=0.1),
            CurvePoint(x=2.0, n=100, y=0.8),
        ]
    )

    with pytest.raises(ValueError, match="Yes/no SDT fits require"):
        fit_yes_no(finding)


def test_bernoulli_rate_fits_condition_invariant_hit_rate() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=10, y=0.2),
            CurvePoint(x=1.0, n=30, y=0.8),
        ]
    )

    result = fit_bernoulli_rate(finding)

    assert result["success"] is True
    assert result["parameters"]["response_rate"] == pytest.approx(0.65)
    assert result["quality"]["n_free_params"] == pytest.approx(1.0)
    assert [p["y"] for p in result["predictions"]] == pytest.approx([0.65, 0.65])


def test_bernoulli_saturated_fits_per_condition_hit_rates() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=10, y=0.2),
            CurvePoint(x=1.0, n=20, y=0.5),
            CurvePoint(x=2.0, n=10, y=0.9),
        ]
    )

    result = fit_bernoulli_saturated(finding)

    assert result["success"] is True
    assert result["parameters"]["response_rate_x0"] == pytest.approx(0.2)
    assert result["parameters"]["response_rate_x1"] == pytest.approx(0.5)
    assert result["parameters"]["response_rate_x2"] == pytest.approx(0.9)
    assert result["quality"]["n_free_params"] == pytest.approx(3.0)
    assert [p["y"] for p in result["predictions"]] == pytest.approx([0.2, 0.5, 0.9])


def _demo_click_rows() -> list[dict[str, str]]:
    rows = []
    for choice in ["left", "left", "left", "left"]:
        rows.append(
            {
                "subject_id": "R1",
                "choice": choice,
                "stimulus_value": "-2",
                "task_variables_json": json.dumps(
                    {
                        "left_click_times": [0.1, 0.2],
                        "right_click_times": [],
                        "stimulus_duration": 1.0,
                    }
                ),
            }
        )
    for choice in ["left", "right"]:
        rows.append(
            {
                "subject_id": "R1",
                "choice": choice,
                "stimulus_value": "0",
                "task_variables_json": json.dumps(
                    {
                        "left_click_times": [0.1],
                        "right_click_times": [0.2],
                        "stimulus_duration": 1.0,
                    }
                ),
            }
        )
    for choice in ["right", "right", "right", "right"]:
        rows.append(
            {
                "subject_id": "R1",
                "choice": choice,
                "stimulus_value": "2",
                "task_variables_json": json.dumps(
                    {
                        "left_click_times": [],
                        "right_click_times": [0.1, 0.2],
                        "stimulus_duration": 1.0,
                    }
                ),
            }
        )
    return rows


def _write_demo_click_trials(
    trials_path, rows: list[dict[str, str]]
) -> None:
    with trials_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "subject_id",
                "choice",
                "stimulus_value",
                "task_variables_json",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_demo_compact_click_trials(
    compact_path, rows: list[dict[str, str]]
) -> None:
    subject_labels = ["R1"]
    subject_code = []
    stimulus_values = []
    choices = []
    durations = []
    right_offsets = [0]
    left_offsets = [0]
    right_times_all = []
    left_times_all = []
    for row in rows:
        task_variables = json.loads(row["task_variables_json"])
        right_times = [float(value) for value in task_variables["right_click_times"]]
        left_times = [float(value) for value in task_variables["left_click_times"]]
        subject_code.append(0)
        stimulus_values.append(float(row["stimulus_value"]))
        choices.append(1 if row["choice"] == "right" else 0)
        durations.append(float(task_variables["stimulus_duration"]))
        right_times_all.extend(right_times)
        left_times_all.extend(left_times)
        right_offsets.append(len(right_times_all))
        left_offsets.append(len(left_times_all))
    np.savez_compressed(
        compact_path,
        schema_version=np.array(["0.1.0"]),
        source_path=np.array(["test"]),
        subject_labels=np.asarray(subject_labels, dtype=str),
        subject_code=np.asarray(subject_code, dtype=np.int16),
        stimulus_values=np.asarray(stimulus_values, dtype=np.float64),
        choices=np.asarray(choices, dtype=np.int8),
        durations=np.asarray(durations, dtype=np.float64),
        right_offsets=np.asarray(right_offsets, dtype=np.int64),
        left_offsets=np.asarray(left_offsets, dtype=np.int64),
        right_times=np.asarray(right_times_all, dtype=np.float64),
        left_times=np.asarray(left_times_all, dtype=np.float64),
    )


def _demo_click_finding() -> Finding:
    finding = _yes_no_finding(
        [
            CurvePoint(x=-2.0, n=4, y=0.0),
            CurvePoint(x=0.0, n=2, y=0.5),
            CurvePoint(x=2.0, n=4, y=1.0),
        ]
    ).model_copy(
        update={
            "id": "finding.demo.clicks.subject.r1",
            "slice_id": "slice.auditory-clicks",
            "stratification": StratificationKey(subject_id="R1"),
            "curve": ResultCurve(
                curve_type="psychometric",
                x_label="Right minus left clicks",
                x_units="click count difference",
                y_label="p_right",
                points=[
                    CurvePoint(x=-2.0, n=4, y=0.0),
                    CurvePoint(x=0.0, n=2, y=0.5),
                    CurvePoint(x=2.0, n=4, y=1.0),
                ],
            ),
        }
    )
    return finding


def test_click_summary_baselines_fit_per_subject_trials(
    tmp_path, monkeypatch
) -> None:
    trials_path = tmp_path / "trials.csv"
    rows = _demo_click_rows()
    _write_demo_click_trials(trials_path, rows)

    finding = _demo_click_finding()

    monkeypatch.setattr(clicks_module, "SLICE_TRIALS_PATH", trials_path)
    clicks_module._TRIAL_CACHE.clear()

    logistic = clicks_module.fit_count_logistic(finding)
    rate_null = clicks_module.fit_choice_rate_null(finding)

    assert logistic["success"] is True
    assert logistic["parameters"]["sensitivity"] > 0
    assert logistic["quality"]["n_free_params"] == pytest.approx(3.0)
    assert rate_null["parameters"]["response_rate"] == pytest.approx(0.5)
    assert rate_null["quality"]["n_free_params"] == pytest.approx(1.0)
    assert logistic["quality"]["aic"] < rate_null["quality"]["aic"]
    predictions = [point["y"] for point in logistic["predictions"]]
    assert predictions == sorted(predictions)


def test_click_forwards_use_compact_cache_when_trials_csv_missing(
    tmp_path, monkeypatch
) -> None:
    rows = _demo_click_rows()
    trials_path = tmp_path / "trials.csv"
    compact_path = tmp_path / "trials_compact.npz"
    _write_demo_click_trials(trials_path, rows)
    _write_demo_compact_click_trials(compact_path, rows)
    finding = _demo_click_finding()
    leaky_params = {
        "input_gain": 1.4,
        "leak": 0.3,
        "noise_input": 0.4,
        "noise_accumulator": 0.2,
        "bias": 0.0,
        "lapse": 0.05,
    }
    logistic_params = {
        "sensitivity": 1.2,
        "bias": 0.0,
        "lapse": 0.05,
    }

    monkeypatch.setattr(clicks_module, "SLICE_TRIALS_PATH", trials_path)
    monkeypatch.setattr(clicks_module, "COMPACT_CLICK_TRIALS_PATH", compact_path)
    clicks_module._TRIAL_CACHE.clear()
    raw_leaky = clicks_module.forward(leaky_params, finding)
    raw_logistic = clicks_module.forward_count_logistic(logistic_params, finding)

    monkeypatch.setattr(clicks_module, "SLICE_TRIALS_PATH", tmp_path / "missing.csv")
    clicks_module._TRIAL_CACHE.clear()
    compact_leaky = clicks_module.forward(leaky_params, finding)
    compact_logistic = clicks_module.forward_count_logistic(logistic_params, finding)

    assert [point.y for point in compact_leaky] == pytest.approx(
        [point.y for point in raw_leaky]
    )
    assert [point.y for point in compact_logistic] == pytest.approx(
        [point.y for point in raw_logistic]
    )
    assert [point.y for point in compact_leaky] != [0.5, 0.5, 0.5]


def test_chance_floor_accuracy_logistic_fits_strength_curve() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=1.6, n=100, y=0.55),
            CurvePoint(x=3.2, n=100, y=0.6),
            CurvePoint(x=6.4, n=100, y=0.72),
            CurvePoint(x=12.8, n=100, y=0.88),
            CurvePoint(x=25.6, n=100, y=0.96),
            CurvePoint(x=51.2, n=100, y=0.99),
        ]
    ).model_copy(
        update={
            "id": "finding.demo.accuracy",
            "curve": ResultCurve(
                curve_type="accuracy_by_strength",
                x_label="Motion strength",
                x_units="percent",
                y_label="p_correct",
                points=[
                    CurvePoint(x=1.6, n=100, y=0.55),
                    CurvePoint(x=3.2, n=100, y=0.6),
                    CurvePoint(x=6.4, n=100, y=0.72),
                    CurvePoint(x=12.8, n=100, y=0.88),
                    CurvePoint(x=25.6, n=100, y=0.96),
                    CurvePoint(x=51.2, n=100, y=0.99),
                ],
            ),
        }
    )

    result = fit_accuracy_strength(finding)

    assert result["success"] is True
    assert result["parameters"]["threshold_strength"] > 0
    assert result["parameters"]["slope_log2"] > 0
    assert 0 <= result["parameters"]["lapse"] <= 0.49
    assert result["quality"]["n_free_params"] == pytest.approx(3.0)
    predictions = [p["y"] for p in result["predictions"]]
    assert predictions == sorted(predictions)


def test_accuracy_rate_null_fits_strength_invariant_summary() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=1.6, n=10, y=0.6),
            CurvePoint(x=3.2, n=30, y=0.8),
        ]
    ).model_copy(
        update={
            "id": "finding.demo.accuracy.rate-null",
            "curve": ResultCurve(
                curve_type="accuracy_by_strength",
                x_label="Motion strength",
                x_units="percent",
                y_label="p_correct",
                points=[
                    CurvePoint(x=1.6, n=10, y=0.6),
                    CurvePoint(x=3.2, n=30, y=0.8),
                ],
            ),
        }
    )

    result = fit_accuracy_rate_null(finding)

    assert result["success"] is True
    assert result["parameters"]["accuracy_rate"] == pytest.approx(0.75)
    assert result["quality"]["n_free_params"] == pytest.approx(1.0)
    assert [p["y"] for p in result["predictions"]] == pytest.approx([0.75, 0.75])


def test_chronometric_hyperbolic_rt_fits_zero_strength_curve() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=50, y=0.82),
            CurvePoint(x=0.05, n=50, y=0.72),
            CurvePoint(x=0.1, n=50, y=0.63),
            CurvePoint(x=0.2, n=50, y=0.55),
            CurvePoint(x=0.4, n=50, y=0.49),
        ]
    ).model_copy(
        update={
            "id": "finding.demo.chronometric",
            "curve": ResultCurve(
                curve_type="chronometric",
                x_label="Motion strength",
                x_units="fraction",
                y_label="median_rt_s",
                points=[
                    CurvePoint(x=0.0, n=50, y=0.82),
                    CurvePoint(x=0.05, n=50, y=0.72),
                    CurvePoint(x=0.1, n=50, y=0.63),
                    CurvePoint(x=0.2, n=50, y=0.55),
                    CurvePoint(x=0.4, n=50, y=0.49),
                ],
            ),
        }
    )

    result = fit_chronometric_rt(finding)

    assert result["success"] is True
    assert result["parameters"]["rt_floor"] >= 0
    assert result["parameters"]["rt_span"] > 0
    assert result["parameters"]["half_saturation_strength"] > 0
    assert result["quality"]["n_free_params"] == pytest.approx(3.0)
    predictions = [p["y"] for p in result["predictions"]]
    assert predictions == sorted(predictions, reverse=True)


def test_chronometric_constant_rt_fits_weighted_summary_null() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=10, y=0.8),
            CurvePoint(x=0.2, n=30, y=0.5),
        ]
    ).model_copy(
        update={
            "id": "finding.demo.chronometric.constant",
            "curve": ResultCurve(
                curve_type="chronometric",
                x_label="Motion strength",
                x_units="fraction",
                y_label="median_rt_s",
                points=[
                    CurvePoint(x=0.0, n=10, y=0.8),
                    CurvePoint(x=0.2, n=30, y=0.5),
                ],
            ),
        }
    )

    result = fit_chronometric_constant_rt(finding)

    assert result["success"] is True
    assert result["parameters"]["rt_level"] == pytest.approx(0.575)
    assert result["quality"]["n_free_params"] == pytest.approx(1.0)
    assert [p["y"] for p in result["predictions"]] == pytest.approx([0.575, 0.575])


def test_caveat_tags_are_inferred_for_khalvati_ddm_proxy() -> None:
    psychometric = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=100, y=0.55),
            CurvePoint(x=1.0, n=100, y=0.8),
        ]
    ).model_copy(
        update={
            "id": (
                "finding.khalvati-kiani-rao-2021.psychometric."
                "direction-choice-proxy.demo"
            ),
            "source_data_level": "figure-source-data",
        }
    )
    chronometric = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=100, y=0.7),
            CurvePoint(x=1.0, n=100, y=0.5),
        ]
    ).model_copy(
        update={
            "id": (
                "finding.khalvati-kiani-rao-2021.chronometric."
                "direction-choice-proxy.demo"
            ),
            "curve": ResultCurve(
                curve_type="chronometric",
                x_label="Absolute coherence",
                x_units="fraction",
                y_label="median_rt_s",
                points=[
                    CurvePoint(x=0.0, n=100, y=0.7),
                    CurvePoint(x=1.0, n=100, y=0.5),
                ],
            ),
            "source_data_level": "figure-source-data",
        }
    )
    fit = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id="model_fit.demo",
        variant_id="model_variant.ddm-vanilla",
        finding_ids=[psychometric.id, chronometric.id],
        parameters={"drift_per_unit_evidence": 1.0, "boundary": 1.0},
        quality={"aic": 10.0},
        fit_method=FitMethod(type="manual"),
        curation_status="analysis-ready",
        provenance=FitProvenance(created=date.today(), updated=date.today()),
    )

    tags = infer_model_fit_caveat_tags(
        fit,
        {psychometric.id: psychometric, chronometric.id: chronometric},
    )

    assert "figure_source_data" in tags
    assert "target_coded_choice_proxy" in tags
    assert "motion_duration_rt_proxy" in tags
    assert "ddm_rt_approximation" in tags


def test_caveat_tags_are_inferred_for_condition_rate_null() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=10, y=0.2),
            CurvePoint(x=1.0, n=30, y=0.8),
        ]
    )
    fit = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id="model_fit.demo.rate-null",
        variant_id="model_variant.bernoulli-condition-rate",
        finding_ids=[finding.id],
        parameters={"response_rate": 0.65},
        quality={"aic": 10.0},
        fit_method=FitMethod(type="manual"),
        curation_status="analysis-ready",
        provenance=FitProvenance(created=date.today(), updated=date.today()),
    )

    tags = infer_model_fit_caveat_tags(fit, {finding.id: finding})

    assert tags == ["condition_rate_null"]


def test_caveat_tags_are_inferred_for_condition_rate_saturated() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=10, y=0.2),
            CurvePoint(x=2.0, n=30, y=0.8),
        ]
    )
    fit = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id="model_fit.demo.rate-saturated",
        variant_id="model_variant.bernoulli-condition-saturated",
        finding_ids=[finding.id],
        parameters={"response_rate_x0": 0.2, "response_rate_x2": 0.8},
        quality={"aic": 10.0},
        fit_method=FitMethod(type="manual"),
        curation_status="analysis-ready",
        provenance=FitProvenance(created=date.today(), updated=date.today()),
    )

    tags = infer_model_fit_caveat_tags(fit, {finding.id: finding})

    assert tags == ["condition_rate_saturated"]


def test_caveat_tags_are_inferred_for_accuracy_summary_fit() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=1.6, n=100, y=0.55),
            CurvePoint(x=3.2, n=100, y=0.6),
        ]
    )
    fit = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id="model_fit.demo.accuracy",
        variant_id="model_variant.chance-floor-accuracy-logistic",
        finding_ids=[finding.id],
        parameters={"threshold_strength": 5.0, "slope_log2": 1.0, "lapse": 0.01},
        quality={"aic": 10.0},
        fit_method=FitMethod(type="manual"),
        curation_status="analysis-ready",
        provenance=FitProvenance(created=date.today(), updated=date.today()),
    )

    tags = infer_model_fit_caveat_tags(fit, {finding.id: finding})

    assert tags == ["accuracy_summary_fit"]


def test_caveat_tags_are_inferred_for_chronometric_summary_fit() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=50, y=0.82),
            CurvePoint(x=0.2, n=50, y=0.55),
        ]
    )
    fit = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id="model_fit.demo.chronometric",
        variant_id="model_variant.chronometric-hyperbolic-rt",
        finding_ids=[finding.id],
        parameters={
            "rt_floor": 0.45,
            "rt_span": 0.4,
            "half_saturation_strength": 0.1,
        },
        quality={"aic": 10.0},
        fit_method=FitMethod(type="manual"),
        curation_status="analysis-ready",
        provenance=FitProvenance(created=date.today(), updated=date.today()),
    )

    tags = infer_model_fit_caveat_tags(fit, {finding.id: finding})

    assert tags == ["chronometric_summary_fit"]


def test_model_fit_comparison_scope_separates_summary_and_joint_fits() -> None:
    finding = _yes_no_finding([CurvePoint(x=0.0, n=10, y=0.2)])
    base_fit = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id="model_fit.demo",
        variant_id="model_variant.sdt-2afc",
        finding_ids=[finding.id],
        parameters={},
        quality={"aic": 10.0},
        fit_method=FitMethod(type="manual"),
        curation_status="analysis-ready",
        provenance=FitProvenance(created=date.today(), updated=date.today()),
    )

    assert model_fit_comparison_scope(base_fit) == "direct_choice"
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={"variant_id": "model_variant.ddm-vanilla"}
            )
        )
        == "joint_choice_rt"
    )
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={
                    "variant_id": "model_variant.chronometric-hyperbolic-rt"
                }
            )
        )
        == "chronometric_summary"
    )
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={"variant_id": "model_variant.chronometric-constant-rt"}
            )
        )
        == "chronometric_summary"
    )
    assert infer_model_fit_caveat_tags(
        base_fit.model_copy(
            update={"variant_id": "model_variant.chronometric-constant-rt"}
        ),
        {finding.id: finding},
    ) == ["chronometric_summary_fit"]
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={
                    "variant_id": "model_variant.chance-floor-accuracy-logistic"
                }
            )
        )
        == "accuracy_summary"
    )
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(update={"variant_id": "model_variant.accuracy-rate-null"})
        )
        == "accuracy_summary"
    )
    assert infer_model_fit_caveat_tags(
        base_fit.model_copy(update={"variant_id": "model_variant.accuracy-rate-null"}),
        {finding.id: finding},
    ) == ["accuracy_summary_fit"]
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={"variant_id": "model_variant.click-count-logistic"}
            )
        )
        == "click_summary"
    )
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={"variant_id": "model_variant.click-choice-rate-null"}
            )
        )
        == "click_summary"
    )
    assert infer_model_fit_caveat_tags(
        base_fit.model_copy(
            update={"variant_id": "model_variant.click-count-logistic"}
        ),
        {finding.id: finding},
    ) == ["click_summary_baseline"]
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={"variant_id": "model_variant.bernoulli-condition-rate"}
            )
        )
        == "condition_rate"
    )
    assert (
        model_fit_comparison_scope(
            base_fit.model_copy(
                update={
                    "variant_id": "model_variant.bernoulli-condition-saturated"
                }
            )
        )
        == "condition_rate"
    )


def test_model_selection_confidence_labels_delta_aic_gaps() -> None:
    assert model_selection_confidence(None, 1) == "single_candidate"
    assert model_selection_confidence(1.99, 2) == "close"
    assert model_selection_confidence(2.0, 2) == "supported"
    assert model_selection_confidence(9.99, 2) == "supported"
    assert model_selection_confidence(10.0, 2) == "decisive"


def test_models_index_splits_choice_and_joint_rt_aic_scopes(tmp_path) -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=-1.0, n=50, y=0.2),
            CurvePoint(x=1.0, n=50, y=0.8),
        ]
    ).model_copy(
        update={
            "id": "finding.demo.psychometric",
            "curve": ResultCurve(
                curve_type="psychometric",
                x_label="Signed evidence",
                x_units="a.u.",
                y_label="p_right",
                points=[
                    CurvePoint(x=-1.0, n=50, y=0.2),
                    CurvePoint(x=1.0, n=50, y=0.8),
                ],
            ),
        }
    )
    direct_fit = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id="model_fit.demo.direct",
        variant_id="model_variant.sdt-2afc",
        finding_ids=[finding.id],
        parameters={},
        quality={"aic": 12.0},
        fit_method=FitMethod(type="manual"),
        curation_status="analysis-ready",
        provenance=FitProvenance(created=date.today(), updated=date.today()),
    )
    joint_fit = direct_fit.model_copy(
        update={
            "id": "model_fit.demo.joint",
            "variant_id": "model_variant.ddm-vanilla",
            "quality": {"aic": 10.0},
        }
    )

    payload = build_models_index(
        families=[],
        variants=[],
        fits=[direct_fit, joint_fit],
        slices=[],
        derived_dir=tmp_path,
        findings=[finding],
    )

    overall = payload["model_selection_by_finding"][0]
    by_scope = payload["model_selection_by_finding_scope"]

    assert overall["has_mixed_aic_scopes"] is True
    assert overall["interpretation_warning"] is None
    assert overall["scope_selection_ids"] == [
        "model_selection.finding-demo-psychometric.direct-choice",
        "model_selection.finding-demo-psychometric.joint-choice-rt",
    ]
    assert {row["comparison_scope"] for row in by_scope} == {
        "direct_choice",
        "joint_choice_rt",
    }
    assert all(row["n_candidate_fits"] == 1 for row in by_scope)
    assert payload["model_selection_interpretation_warning_counts"] == {}


def test_model_selection_csv_rows_include_caveat_tags() -> None:
    rows = model_selection_csv_rows(
        models_payload={
            "model_selection_by_finding": [
                {
                    "finding_id": "finding.demo",
                    "selection_id": "model_selection.finding-demo",
                    "selection_level": "finding",
                    "best_fit_id": "model_fit.demo",
                    "best_variant_id": "model_variant.sdt-yes-no",
                    "best_aic": 12.3456789,
                    "delta_aic_to_next": None,
                    "confidence_label": "single_candidate",
                    "comparison_scope": "direct_choice",
                    "n_candidate_fits": 1,
                    "has_mixed_aic_scopes": True,
                    "scope_selection_ids": [
                        "model_selection.finding-demo.direct-choice"
                    ],
                    "candidate_scope_counts": {"direct_choice": 1},
                    "candidate_fit_ids": ["model_fit.demo"],
                    "candidate_variant_ids": ["model_variant.sdt-yes-no"],
                    "candidate_comparison_scopes": ["direct_choice"],
                    "best_caveat_tags": ["binary_yes_no_sdt"],
                    "candidate_caveat_tags": ["binary_yes_no_sdt"],
                    "interpretation_warning": None,
                }
            ]
        },
        findings_payload={
            "findings": [
                {
                    "finding_id": "finding.demo",
                    "paper_id": "paper.demo",
                    "curve_type": "hit_rate_by_condition",
                    "protocol_id": "protocol.demo",
                    "species": "mouse",
                    "source_data_level": "processed-trial",
                    "stratification": {"condition": "image-change"},
                }
            ]
        },
    )

    assert rows == [
        {
            "selection_id": "model_selection.finding-demo",
            "selection_level": "finding",
            "finding_id": "finding.demo",
            "paper_id": "paper.demo",
            "curve_type": "hit_rate_by_condition",
            "protocol_id": "protocol.demo",
            "species": "mouse",
            "source_data_level": "processed-trial",
            "condition": "image-change",
            "subject_id": "",
            "best_fit_id": "model_fit.demo",
            "best_variant_id": "model_variant.sdt-yes-no",
            "best_aic": "12.3456789",
            "delta_aic_to_next": "",
            "confidence_label": "single_candidate",
            "comparison_scope": "direct_choice",
            "n_candidate_fits": 1,
            "has_mixed_aic_scopes": "true",
            "scope_selection_ids": "model_selection.finding-demo.direct-choice",
            "candidate_scope_counts": "direct_choice:1",
            "candidate_fit_ids": "model_fit.demo",
            "candidate_variant_ids": "model_variant.sdt-yes-no",
            "candidate_comparison_scopes": "direct_choice",
            "best_caveat_tags": "binary_yes_no_sdt",
            "candidate_caveat_tags": "binary_yes_no_sdt",
            "interpretation_warning_type": "",
        }
    ]


def test_model_coverage_gaps_filter_near_misses_by_slice_context() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=-1.0, n=50, y=0.25),
            CurvePoint(x=1.0, n=50, y=0.75),
        ]
    ).model_copy(
        update={
            "id": "finding.demo.psychometric",
            "slice_id": "slice.demo-rdm",
            "curve": ResultCurve(
                curve_type="psychometric",
                x_label="Motion strength",
                x_units="signed coherence",
                y_label="p_right",
                points=[
                    CurvePoint(x=-1.0, n=50, y=0.25),
                    CurvePoint(x=1.0, n=50, y=0.75),
                ],
            ),
        }
    )
    families = [
        _model_family(
            "model_family.drift-diffusion",
            ["psychometric", "chronometric", "rt_distribution"],
        ),
        _model_family("model_family.signal-detection", ["psychometric"]),
        _model_family("model_family.click-summary-choice", ["psychometric"]),
    ]
    variants = [
        _model_variant(
            "model_variant.click-count-logistic",
            "model_family.click-summary-choice",
            ["choice_lr", "click_times", "subject_id"],
        ),
        _model_variant(
            "model_variant.ddm-vanilla",
            "model_family.drift-diffusion",
            ["stimulus_value", "choice_lr", "response_time"],
        ),
        _model_variant(
            "model_variant.sdt-yes-no",
            "model_family.signal-detection",
            ["choice_go_withhold"],
        ),
    ]

    gaps = _model_coverage_gaps(
        findings_by_id={finding.id: finding},
        fits_by_finding={},
        selections=[],
        slice_coverage=[
            {
                "slice_id": "slice.demo-rdm",
                "family_id": "family.random-dot-motion",
                "choice_type": "2afc",
                "capabilities": {
                    "stimulus_value": True,
                    "choice_lr": True,
                    "choice_go_withhold": False,
                    "correct_outcome": True,
                    "response_time": False,
                    "prior_context": False,
                    "click_times": False,
                    "subject_id": True,
                },
                "n_trials": 100,
                "n_subjects": 1,
            }
        ],
        families=families,
        variants=variants,
    )

    near_misses = gaps["near_miss_slices"]
    assert [row["variant_id"] for row in near_misses] == [
        "model_variant.ddm-vanilla"
    ]
    assert near_misses[0]["missing_requirements"] == ["response_time"]
    assert near_misses[0]["slice_curve_types"] == ["psychometric"]

    no_findings_gaps = _model_coverage_gaps(
        findings_by_id={},
        fits_by_finding={},
        selections=[],
        slice_coverage=[
            {
                "slice_id": "slice.demo-no-finding",
                "family_id": "family.visual-2afc-contrast",
                "choice_type": "2afc",
                "capabilities": {
                    "choice_go_withhold": False,
                },
                "n_trials": 100,
                "n_subjects": 1,
            }
        ],
        families=[_model_family("model_family.signal-detection", ["psychometric"])],
        variants=[
            _model_variant(
                "model_variant.sdt-yes-no",
                "model_family.signal-detection",
                ["choice_go_withhold"],
            )
        ],
    )

    assert no_findings_gaps["near_miss_slices"] == []

    unavailable_gaps = _model_coverage_gaps(
        findings_by_id={finding.id: finding},
        fits_by_finding={},
        selections=[],
        slice_coverage=[
            {
                "slice_id": "slice.auditory-clicks",
                "family_id": "family.auditory-click-accumulation",
                "choice_type": "2afc",
                "capabilities": {
                    "stimulus_value": True,
                    "choice_lr": True,
                    "response_time": False,
                },
                "n_trials": 100,
                "n_subjects": 1,
            }
        ],
        families=[
            _model_family(
                "model_family.drift-diffusion",
                ["psychometric", "chronometric", "rt_distribution"],
            )
        ],
        variants=[
            _model_variant(
                "model_variant.ddm-vanilla",
                "model_family.drift-diffusion",
                ["stimulus_value", "choice_lr", "response_time"],
            )
        ],
    )

    assert unavailable_gaps["near_miss_slices"] == []
    assert unavailable_gaps["counts"]["intentionally_inapplicable_near_misses"] == 1
    assert (
        "parsed schema"
        in unavailable_gaps["intentionally_inapplicable_near_misses"][0][
            "inapplicable_reason"
        ]
    )


def test_model_coverage_roadmap_ranks_warning_and_near_miss_items() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=50, y=0.82),
            CurvePoint(x=0.2, n=50, y=0.55),
        ]
    )
    roadmap = build_model_coverage_roadmap(
        findings_by_id={finding.id: finding},
        model_selection_by_finding=[
            {
                "finding_id": finding.id,
                "best_variant_id": "model_variant.chronometric-hyperbolic-rt",
                "comparison_scope": "chronometric_summary",
                "confidence_label": "decisive",
                "n_candidate_fits": 2,
                "candidate_caveat_tags": ["chronometric_summary_fit"],
            }
        ],
        model_coverage_gaps={
            "findings_with_no_fits": [],
            "findings_with_single_candidate": [],
            "proxy_backed_findings": [],
            "near_miss_slices": [
                {
                    "slice_id": "slice.demo",
                    "variant_id": "model_variant.ddm-vanilla",
                    "missing_requirements": ["response_time"],
                }
            ],
        },
        interpretation_warnings=[
            {
                "finding_id": finding.id,
                "best_fit_id": "model_fit.demo",
                "best_variant_id": "model_variant.chronometric-hyperbolic-rt",
                "comparison_scope": "chronometric_summary",
                "candidate_comparison_scopes": [
                    "joint_choice_rt",
                    "chronometric_summary",
                ],
                "confidence_label": "decisive",
                "delta_aic_to_next": 10.0,
                "severity": "high",
                "warning_type": "summary_baseline_winner",
                "message": "summary model beat process candidate",
            }
        ],
    )

    assert roadmap["counts"]["items"] == 2
    assert roadmap["items"][0]["issue_type"] == "summary_baseline_winner"
    assert roadmap["items"][0]["priority_label"] == "high"
    assert roadmap["items"][1]["issue_type"] == "near_miss_slice"
    assert roadmap["items"][1]["missing_requirements"] == ["response_time"]

    rows = model_coverage_roadmap_csv_rows(
        models_payload={"model_coverage_roadmap": roadmap}
    )

    assert rows[0]["caveat_tags"] == "chronometric_summary_fit"
    assert rows[1]["missing_requirements"] == "response_time"


def test_model_coverage_roadmap_marks_external_data_blockers() -> None:
    finding = _yes_no_finding(
        [
            CurvePoint(x=0.0, n=50, y=0.82),
            CurvePoint(x=0.2, n=50, y=0.55),
        ]
    ).model_copy(
        update={
            "id": "finding.khalvati.demo",
            "paper_id": "paper.khalvati-kiani-rao-2021",
            "dataset_id": "dataset.khalvati-kiani-rao-rdm-confidence-source-data",
            "source_data_level": "figure-source-data",
        }
    )

    roadmap = build_model_coverage_roadmap(
        findings_by_id={finding.id: finding},
        model_selection_by_finding=[
            {
                "finding_id": finding.id,
                "best_variant_id": "model_variant.ddm-vanilla",
                "comparison_scope": "joint_choice_rt",
                "confidence_label": "supported",
                "n_candidate_fits": 2,
                "candidate_caveat_tags": [
                    "figure_source_data",
                    "target_coded_choice_proxy",
                ],
            }
        ],
        model_coverage_gaps={
            "findings_with_no_fits": [],
            "findings_with_single_candidate": [],
            "proxy_backed_findings": [
                {
                    "finding_id": finding.id,
                    "paper_id": finding.paper_id,
                    "dataset_id": finding.dataset_id,
                    "curve_type": "hit_rate_by_condition",
                    "source_data_level": finding.source_data_level,
                    "best_variant_id": "model_variant.ddm-vanilla",
                    "proxy_caveat_tags": [
                        "figure_source_data",
                        "target_coded_choice_proxy",
                    ],
                    "n_candidate_fits": 2,
                }
            ],
            "near_miss_slices": [],
        },
        interpretation_warnings=[],
    )

    item = roadmap["items"][0]
    assert item["status"] == "blocked_external_data"
    assert item["blocker_type"] == "author_request_raw_trials"
    assert "beh_data.monkey1.mat" in item["blocker_detail"]
    assert roadmap["counts"]["by_status"]["blocked_external_data"] == 1

    rows = model_coverage_roadmap_csv_rows(
        models_payload={"model_coverage_roadmap": roadmap}
    )

    assert rows[0]["status"] == "blocked_external_data"
