import json

import pytest

from behavtaskatlas.clicks import (
    aggregate_brody_clicks_batch,
    aggregate_kernel_svg,
    analyze_brody_clicks,
    analyze_brody_clicks_evidence_kernel,
    clicks_aggregate_report_html,
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


def test_aggregate_brody_clicks_batch_reads_batch_artifacts(tmp_path) -> None:
    derived_dir = tmp_path / "auditory_clicks"
    rat_a_dir = derived_dir / "A080-parsed"
    rat_b_dir = derived_dir / "B075-parsed"
    rat_a_dir.mkdir(parents=True)
    rat_b_dir.mkdir(parents=True)

    batch_summary_path = derived_dir / "batch_summary.csv"
    write_clicks_batch_summary_csv(
        batch_summary_path,
        [
            {
                "mat_file": "A080.mat",
                "session_id": "A080-parsed",
                "parsed_field": "parsed",
                "subject_id": "A080",
                "task_type": "location",
                "status": "ok",
                "error": None,
                "n_trials": 100,
                "harmonization_summary_rows": 10,
                "psychometric_summary_rows": 10,
                "psychometric_prior_contexts": "gamma=-1",
                "evidence_kernel_rows": 2,
                "evidence_kernel_analyzed_trials": 100,
                "evidence_kernel_excluded_trials": 0,
                "source_file_sha256": "hash-a",
                "output_dir": str(rat_a_dir),
            },
            {
                "mat_file": "B075.mat",
                "session_id": "B075-parsed",
                "parsed_field": "parsed",
                "subject_id": "B075",
                "task_type": "location",
                "status": "ok",
                "error": None,
                "n_trials": 80,
                "harmonization_summary_rows": 8,
                "psychometric_summary_rows": 8,
                "psychometric_prior_contexts": "gamma=-1",
                "evidence_kernel_rows": 2,
                "evidence_kernel_analyzed_trials": 80,
                "evidence_kernel_excluded_trials": 0,
                "source_file_sha256": "hash-b",
                "output_dir": str(rat_b_dir),
            },
        ],
    )
    _write_minimal_clicks_results(
        rat_a_dir,
        session_id="A080-parsed",
        n_trials=100,
        choice_differences=[2.0, -1.0],
        bias=-0.5,
    )
    _write_minimal_clicks_results(
        rat_b_dir,
        session_id="B075-parsed",
        n_trials=80,
        choice_differences=[4.0, -3.0],
        bias=0.5,
    )

    result = aggregate_brody_clicks_batch(batch_summary_path)

    assert result["analysis_type"] == "batch_aggregate"
    assert result["n_ok"] == 2
    assert result["n_trials_total"] == 180
    assert result["n_artifact_errors"] == 0
    assert len(result["psychometric_bias_rows"]) == 2
    assert result["psychometric_bias_rows"][0]["fit_status"] == "ok"
    first_kernel_row = result["kernel_summary_rows"][0]
    assert first_kernel_row["n_rats"] == 2
    assert first_kernel_row["total_trials"] == 180
    assert first_kernel_row["mean_choice_difference"] == pytest.approx(3.0)
    assert first_kernel_row["median_choice_difference"] == pytest.approx(3.0)
    assert first_kernel_row["min_choice_difference"] == pytest.approx(2.0)
    assert first_kernel_row["max_choice_difference"] == pytest.approx(4.0)


def test_aggregate_kernel_svg_contains_title() -> None:
    svg = aggregate_kernel_svg(
        [
            {
                "bin_index": 0,
                "bin_start": 0.0,
                "bin_end": 0.5,
                "n_rats": 2,
                "total_trials": 180,
                "mean_choice_difference": 3.0,
                "median_choice_difference": 3.0,
                "min_choice_difference": 2.0,
                "max_choice_difference": 4.0,
                "mean_point_biserial_r": 0.3,
                "mean_normalized_weight": 0.5,
            }
        ]
    )

    assert "<svg" in svg
    assert "Mean choice-triggered evidence" in svg


def test_clicks_aggregate_report_html_contains_artifact_links_and_tables() -> None:
    html = clicks_aggregate_report_html(
        {
            "analysis_id": "analysis.auditory-clicks.batch-aggregate",
            "protocol_id": "protocol.poisson-clicks-evidence-accumulation",
            "dataset_id": "dataset.brody-lab-poisson-clicks-2009-2024",
            "generated_at": "2026-04-24T18:00:00+00:00",
            "behavtaskatlas_commit": "abc1234",
            "behavtaskatlas_git_dirty": False,
            "batch_summary_path": "batch_summary.csv",
            "n_ok": 1,
            "n_failed": 0,
            "n_artifact_errors": 0,
            "n_trials_total": 100,
            "task_types": ["location"],
            "gamma_contexts": ["gamma=-1"],
            "rat_results": [
                {
                    "subject_id": "A080",
                    "task_type": "location",
                    "n_trials": 100,
                    "n_psychometric_prior_contexts": 1,
                    "n_kernel_rows": 2,
                    "n_kernel_excluded_trials": 0,
                    "status": "ok",
                }
            ],
            "psychometric_bias_rows": [
                {
                    "subject_id": "A080",
                    "prior_context": "gamma=-1",
                    "n_trials": 100,
                    "n_click_difference_levels": 4,
                    "empirical_bias_click_difference": -0.5,
                    "fit_bias_click_difference": -0.4,
                    "fit_threshold_click_difference": 4.4,
                    "fit_status": "ok",
                }
            ],
            "kernel_summary_rows": [
                {
                    "bin_index": 0,
                    "bin_start": 0.0,
                    "bin_end": 0.5,
                    "n_rats": 1,
                    "total_trials": 100,
                    "mean_choice_difference": 2.0,
                    "min_choice_difference": 2.0,
                    "max_choice_difference": 2.0,
                    "mean_point_biserial_r": 0.2,
                }
            ],
            "caveats": ["Escape <unsafe> text"],
        },
        aggregate_kernel_svg_text="<svg><text>Plot</text></svg>",
        artifact_links={"aggregate result JSON": "aggregate_result.json"},
    )

    assert "Auditory Clicks Aggregate Report" in html
    assert "A080" in html
    assert "gamma=-1" in html
    assert "aggregate_result.json" in html
    assert "<svg><text>Plot</text></svg>" in html
    assert "Escape &lt;unsafe&gt; text" in html


def test_harmonize_brody_clicks_trial_requires_fields() -> None:
    with pytest.raises(ValueError, match="Missing required Brody clicks trial fields"):
        harmonize_brody_clicks_trial({}, session_id="s", trial_index=0)


def _write_minimal_clicks_results(
    output_dir,
    *,
    session_id: str,
    n_trials: int,
    choice_differences: list[float],
    bias: float,
) -> None:
    analysis_result = {
        "session_id": session_id,
        "prior_results": [
            {
                "prior_context": "gamma=-1",
                "n_trials": n_trials,
                "n_response_trials": n_trials,
                "n_click_difference_levels": 4,
                "empirical_bias_click_difference": bias,
                "empirical_threshold_click_difference": 2.0,
                "left_lapse_empirical": 0.1,
                "right_lapse_empirical": 0.2,
                "fit": {
                    "status": "ok",
                    "bias_click_difference": bias + 0.1,
                    "scale_click_difference": 4.0,
                    "threshold_click_difference": 4.4,
                    "left_lapse": 0.05,
                    "right_lapse": 0.06,
                },
            }
        ]
    }
    kernel_result = {
        "n_analyzed_trials": n_trials,
        "n_excluded_trials": 0,
        "summary_rows": [
            {
                "bin_index": index,
                "bin_start": index / len(choice_differences),
                "bin_end": (index + 1) / len(choice_differences),
                "n_trials": n_trials,
                "choice_difference": choice_difference,
                "point_biserial_r": choice_difference / 10.0,
                "normalized_weight": choice_difference / 10.0,
            }
            for index, choice_difference in enumerate(choice_differences)
        ],
    }
    (output_dir / "analysis_result.json").write_text(json.dumps(analysis_result))
    (output_dir / "evidence_kernel_result.json").write_text(json.dumps(kernel_result))
