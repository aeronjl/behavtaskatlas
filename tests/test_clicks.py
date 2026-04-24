import pytest

from behavtaskatlas.clicks import (
    analyze_brody_clicks,
    analyze_brody_clicks_evidence_kernel,
    evidence_kernel_svg,
    harmonize_brody_clicks_trial,
    harmonize_brody_clicks_trials,
    write_clicks_batch_summary_csv,
)


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


def test_analyze_brody_clicks_returns_click_difference_metrics() -> None:
    trials = harmonize_brody_clicks_trials(
        {
            "nL": [8, 6, 2, 0],
            "nR": [0, 2, 6, 8],
            "sd": [1.0, 1.0, 1.0, 1.0],
            "gr": [0, 0, 1, 1],
            "hh": [1, 1, 1, 1],
            "ga": [0.0, 0.0, 0.0, 0.0],
            "rg": [0, 0, 0, 0],
        },
        session_id="rat-a-parsed",
        subject_id="rat-a",
        task_type="location",
    )

    result = analyze_brody_clicks(trials)

    assert result["analysis_type"] == "descriptive_psychometric"
    assert result["stimulus_metric_name"] == "click_difference"
    assert result["n_trials"] == 4
    assert result["prior_results"][0]["n_click_difference_levels"] == 4
    assert result["prior_results"][0]["empirical_bias_click_difference"] == 0.0
    assert result["prior_results"][0]["fit"]["method"] == "four_parameter_logistic_binomial_mle"


def test_analyze_brody_clicks_evidence_kernel_uses_click_timing() -> None:
    trials = [
        harmonize_brody_clicks_trial(
            {
                "nL": 1,
                "nR": 1,
                "sd": 1.0,
                "gr": 1,
                "hh": 1,
                "left_click_times": [0.75],
                "right_click_times": [0.25],
            },
            session_id="rat-a-parsed",
            trial_index=0,
        ),
        harmonize_brody_clicks_trial(
            {
                "nL": 1,
                "nR": 1,
                "sd": 1.0,
                "gr": 0,
                "hh": 1,
                "left_click_times": [0.25],
                "right_click_times": [0.75],
            },
            session_id="rat-a-parsed",
            trial_index=1,
        ),
    ]

    result = analyze_brody_clicks_evidence_kernel(trials, n_bins=2)

    assert result["analysis_type"] == "choice_triggered_evidence_kernel"
    assert result["n_analyzed_trials"] == 2
    assert result["summary_rows"][0]["choice_difference"] == 2.0
    assert result["summary_rows"][1]["choice_difference"] == -2.0
    assert result["summary_rows"][0]["point_biserial_r"] == pytest.approx(1.0)
    assert result["summary_rows"][1]["point_biserial_r"] == pytest.approx(-1.0)
    assert result["summary_rows"][0]["normalized_weight"] == pytest.approx(0.5)


def test_evidence_kernel_svg_contains_axis_label() -> None:
    svg = evidence_kernel_svg(
        [
            {
                "bin_index": 0,
                "bin_start": 0.0,
                "bin_end": 0.5,
                "n_trials": 2,
                "n_right_choice": 1,
                "n_left_choice": 1,
                "mean_signed_evidence": 0.0,
                "mean_signed_evidence_right_choice": 1.0,
                "mean_signed_evidence_left_choice": -1.0,
                "choice_difference": 2.0,
                "point_biserial_r": 1.0,
                "normalized_weight": 1.0,
            }
        ]
    )

    assert "<svg" in svg
    assert "Normalized stimulus time" in svg


def test_write_clicks_batch_summary_csv(tmp_path) -> None:
    path = tmp_path / "batch_summary.csv"
    write_clicks_batch_summary_csv(
        path,
        [
            {
                "mat_file": "B075.mat",
                "session_id": "B075-parsed",
                "parsed_field": "parsed",
                "subject_id": "B075",
                "task_type": "location",
                "status": "ok",
                "error": None,
                "n_trials": 11285,
                "harmonization_summary_rows": 181,
                "psychometric_summary_rows": 181,
                "psychometric_prior_contexts": "gamma=-1;gamma=1",
                "evidence_kernel_rows": 10,
                "evidence_kernel_analyzed_trials": 11285,
                "evidence_kernel_excluded_trials": 0,
                "source_file_sha256": "hash",
                "output_dir": "derived/auditory_clicks/B075-parsed",
            }
        ],
    )

    text = path.read_text()
    assert "session_id" in text
    assert "B075-parsed" in text


def test_harmonize_brody_clicks_trial_requires_fields() -> None:
    with pytest.raises(ValueError, match="Missing required Brody clicks trial fields"):
        harmonize_brody_clicks_trial({}, session_id="s", trial_index=0)
