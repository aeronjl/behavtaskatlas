import pytest

from behavtaskatlas.rdm import (
    HUMAN_RDM_PROTOCOL_ID,
    MACAQUE_RDM_CONFIDENCE_DATASET_ID,
    MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID,
    analyze_human_rdm,
    analyze_macaque_rdm_confidence,
    analyze_roitman_rdm,
    harmonize_human_rdm_phs_trial,
    harmonize_macaque_rdm_confidence_source_row,
    harmonize_roitman_rdm_trial,
    macaque_rdm_confidence_choice_svg,
    macaque_rdm_confidence_report_html,
    rdm_chronometric_svg,
    rdm_report_html,
    summarize_rdm_chronometric,
)


def test_harmonize_roitman_rdm_trial_reconstructs_signed_coherence() -> None:
    trial = harmonize_roitman_rdm_trial(
        {
            "monkey": "1",
            "rt": "0.355",
            "coh": "0.512",
            "correct": "1.0",
            "trgchoice": "2.0",
        },
        session_id="session",
        trial_index=0,
    )

    assert trial.protocol_id == "protocol.random-dot-motion-classic-macaque"
    assert trial.dataset_id == "dataset.roitman-shadlen-rdm-pyddm"
    assert trial.subject_id == "monkey-1"
    assert trial.stimulus_value == pytest.approx(-51.2)
    assert trial.stimulus_side == "left"
    assert trial.choice == "left"
    assert trial.correct is True
    assert trial.response_time == pytest.approx(0.355)
    assert trial.task_variables["target_choice"] == 2


def test_harmonize_human_rdm_phs_trial_uses_signed_coherence() -> None:
    trial = harmonize_human_rdm_phs_trial(
        {
            "rt": 0.612,
            "choice": 0,
            "cohs": -0.128,
        },
        subject_id="phs-ah",
        session_id="session",
        trial_index=0,
    )

    assert trial.protocol_id == HUMAN_RDM_PROTOCOL_ID
    assert trial.dataset_id == "dataset.palmer-huk-shadlen-human-rdm-cosmo2017"
    assert trial.subject_id == "phs-ah"
    assert trial.stimulus_value == pytest.approx(-12.8)
    assert trial.stimulus_side == "left"
    assert trial.choice == "left"
    assert trial.correct is True
    assert trial.response_time == pytest.approx(0.612)
    assert trial.feedback == "none"


def test_harmonize_human_rdm_phs_trial_zero_coherence_matches_source_convention() -> None:
    right_trial = harmonize_human_rdm_phs_trial(
        {
            "rt": 0.5,
            "choice": 1,
            "cohs": 0.0,
        },
        subject_id="phs-ah",
        session_id="session",
        trial_index=0,
    )
    left_trial = harmonize_human_rdm_phs_trial(
        {
            "rt": 0.6,
            "choice": 0,
            "cohs": 0.0,
        },
        subject_id="phs-ah",
        session_id="session",
        trial_index=1,
    )

    assert right_trial.stimulus_side == "none"
    assert right_trial.correct is True
    assert left_trial.correct is False


def test_harmonize_macaque_rdm_confidence_accuracy_source_row() -> None:
    trial = harmonize_macaque_rdm_confidence_source_row(
        {
            "Motion Strength (%)": "6.4",
            "Motion duration (msc)": "229",
            "Correct": "1",
            "_source_measure": "accuracy_no_sure_target",
            "_figure_panels": "Fig. 1b black dots and Fig. 4a",
            "_monkey": "M1",
            "_strength_file": "strength.csv",
            "_duration_file": "duration.csv",
            "_source_row_index": 2,
            "_outcome_field": "Correct",
            "_sure_target_available": False,
            "_sure_target_chosen": None,
        },
        session_id="session",
        trial_index=0,
    )

    assert trial.protocol_id == MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID
    assert trial.dataset_id == MACAQUE_RDM_CONFIDENCE_DATASET_ID
    assert trial.subject_id == "kiani-shadlen-m1"
    assert trial.stimulus_value == pytest.approx(6.4)
    assert trial.stimulus_side == "unknown"
    assert trial.choice == "unknown"
    assert trial.correct is True
    assert trial.response_time is None
    assert trial.task_variables["motion_duration_ms"] == pytest.approx(229)
    assert trial.task_variables["sure_target_available"] is False


def test_harmonize_macaque_rdm_confidence_sure_target_source_row() -> None:
    trial = harmonize_macaque_rdm_confidence_source_row(
        {
            "Motion strength (%)": "0.0",
            "Motion duration (msc)": "108",
            "Sure target": "1",
            "_source_measure": "sure_target_choice",
            "_figure_panels": "Fig. 1c and Fig. 4c",
            "_monkey": "M2",
            "_strength_file": "strength.csv",
            "_duration_file": "duration.csv",
            "_source_row_index": 3,
            "_outcome_field": "Sure target",
            "_sure_target_available": True,
            "_sure_target_chosen": None,
        },
        session_id="session",
        trial_index=1,
    )

    assert trial.subject_id == "kiani-shadlen-m2"
    assert trial.stimulus_value == pytest.approx(0.0)
    assert trial.stimulus_side == "none"
    assert trial.correct is None
    assert trial.feedback == "reward"
    assert trial.task_variables["sure_target_chosen"] is True


def test_harmonize_roitman_rdm_trial_uses_errors_to_infer_stimulus() -> None:
    trial = harmonize_roitman_rdm_trial(
        {
            "monkey": "2",
            "rt": "0.400",
            "coh": "0.256",
            "correct": "0.0",
            "trgchoice": "2.0",
        },
        session_id="session",
        trial_index=1,
    )

    assert trial.choice == "left"
    assert trial.correct is False
    assert trial.stimulus_value == pytest.approx(25.6)
    assert trial.stimulus_side == "right"


def test_analyze_roitman_rdm_adds_chronometric_rows() -> None:
    trials = [
        harmonize_roitman_rdm_trial(
            {
                "monkey": "1",
                "rt": "0.3",
                "coh": "0.032",
                "correct": "1.0",
                "trgchoice": "1.0",
            },
            session_id="session",
            trial_index=0,
        ),
        harmonize_roitman_rdm_trial(
            {
                "monkey": "1",
                "rt": "0.5",
                "coh": "0.032",
                "correct": "0.0",
                "trgchoice": "1.0",
            },
            session_id="session",
            trial_index=1,
        ),
    ]

    result = analyze_roitman_rdm(trials)
    chrono = summarize_rdm_chronometric(trials)

    assert result["analysis_type"] == "descriptive_psychometric"
    assert result["stimulus_metric_name"] == "coherence"
    assert result["chronometric_rows"] == chrono
    assert chrono[0]["evidence_strength"] == pytest.approx(3.2)
    assert chrono[0]["median_response_time"] == pytest.approx(0.4)
    assert chrono[0]["p_correct"] == pytest.approx(0.5)


def test_analyze_human_rdm_adds_chronometric_rows() -> None:
    trials = [
        harmonize_human_rdm_phs_trial(
            {"rt": 0.6, "choice": 0, "cohs": -0.032},
            subject_id="phs-ah",
            session_id="session",
            trial_index=0,
        ),
        harmonize_human_rdm_phs_trial(
            {"rt": 0.4, "choice": 1, "cohs": 0.032},
            subject_id="phs-ah",
            session_id="session",
            trial_index=1,
        ),
    ]

    result = analyze_human_rdm(trials)
    chrono = summarize_rdm_chronometric(trials)

    assert result["analysis_id"] == "analysis.human-rdm.descriptive-psychometric"
    assert result["report_title"] == "Human Random-Dot Motion Report"
    assert result["protocol_id"] == HUMAN_RDM_PROTOCOL_ID
    assert result["chronometric_rows"] == chrono
    assert chrono[0]["evidence_strength"] == pytest.approx(3.2)
    assert chrono[0]["p_correct"] == pytest.approx(1.0)


def test_analyze_macaque_rdm_confidence_summarizes_accuracy_and_sure_choice() -> None:
    trials = [
        harmonize_macaque_rdm_confidence_source_row(
            {
                "Motion Strength (%)": "3.2",
                "Motion duration (msc)": "200",
                "Correct": "1",
                "_source_measure": "accuracy_no_sure_target",
                "_figure_panels": "Fig. 1b black dots and Fig. 4a",
                "_monkey": "M1",
                "_strength_file": "strength.csv",
                "_duration_file": "duration.csv",
                "_source_row_index": 0,
                "_outcome_field": "Correct",
                "_sure_target_available": False,
                "_sure_target_chosen": None,
            },
            session_id="session",
            trial_index=0,
        ),
        harmonize_macaque_rdm_confidence_source_row(
            {
                "Motion Strength (%)": "3.2",
                "Motion duration (msc)": "300",
                "Correct": "0",
                "_source_measure": "accuracy_no_sure_target",
                "_figure_panels": "Fig. 1b black dots and Fig. 4a",
                "_monkey": "M1",
                "_strength_file": "strength.csv",
                "_duration_file": "duration.csv",
                "_source_row_index": 1,
                "_outcome_field": "Correct",
                "_sure_target_available": False,
                "_sure_target_chosen": None,
            },
            session_id="session",
            trial_index=1,
        ),
        harmonize_macaque_rdm_confidence_source_row(
            {
                "Motion strength (%)": "3.2",
                "Motion duration (msc)": "250",
                "Sure target": "1",
                "_source_measure": "sure_target_choice",
                "_figure_panels": "Fig. 1c and Fig. 4c",
                "_monkey": "M1",
                "_strength_file": "strength.csv",
                "_duration_file": "duration.csv",
                "_source_row_index": 2,
                "_outcome_field": "Sure target",
                "_sure_target_available": True,
                "_sure_target_chosen": None,
            },
            session_id="session",
            trial_index=2,
        ),
        harmonize_macaque_rdm_confidence_source_row(
            {
                "Motion strength (%)": "3.2",
                "Motion duration (msc)": "350",
                "Sure target": "0",
                "_source_measure": "sure_target_choice",
                "_figure_panels": "Fig. 1c and Fig. 4c",
                "_monkey": "M1",
                "_strength_file": "strength.csv",
                "_duration_file": "duration.csv",
                "_source_row_index": 3,
                "_outcome_field": "Sure target",
                "_sure_target_available": True,
                "_sure_target_chosen": None,
            },
            session_id="session",
            trial_index=3,
        ),
    ]

    result = analyze_macaque_rdm_confidence(trials)

    assert result["analysis_id"] == "analysis.macaque-rdm-confidence.source-data-summary"
    assert result["protocol_id"] == MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID
    assert result["n_accuracy_rows"] == 2
    assert result["n_sure_target_choice_rows"] == 2
    assert result["accuracy_rows"][0]["p_correct"] == pytest.approx(0.5)
    assert result["accuracy_rows"][0]["median_motion_duration_ms"] == pytest.approx(250)
    assert result["confidence_rows"][0]["p_sure_target"] == pytest.approx(0.5)
    assert result["confidence_rows"][0]["median_motion_duration_ms"] == pytest.approx(300)


def test_rdm_chronometric_svg_contains_axis_label() -> None:
    svg = rdm_chronometric_svg(
        [
            {
                "evidence_strength": 3.2,
                "n_trials": 2,
                "n_response": 2,
                "n_correct": 1,
                "p_correct": 0.5,
                "median_response_time": 0.4,
                "mean_response_time": 0.4,
            }
        ]
    )

    assert "<svg" in svg
    assert "Motion coherence" in svg


def test_macaque_rdm_confidence_svg_contains_axis_label() -> None:
    svg = macaque_rdm_confidence_choice_svg(
        [
            {
                "monkey": "M1",
                "motion_strength_percent": 3.2,
                "n_source_rows": 2,
                "n_sure_target": 1,
                "p_sure_target": 0.5,
                "median_motion_duration_ms": 300,
                "mean_motion_duration_ms": 300,
            }
        ]
    )

    assert "<svg" in svg
    assert "P(sure target)" in svg


def test_rdm_report_html_contains_source_and_artifact_links() -> None:
    html = rdm_report_html(
        {
            "analysis_id": "analysis.random-dot-motion.descriptive-psychometric",
            "protocol_id": "protocol.random-dot-motion-classic-macaque",
            "dataset_id": "dataset.roitman-shadlen-rdm-pyddm",
            "generated_at": "2026-04-24T19:00:00+00:00",
            "behavtaskatlas_commit": "abc123",
            "behavtaskatlas_git_dirty": False,
            "n_trials": 2,
            "n_response_trials": 2,
            "prior_results": [
                {
                    "prior_context": None,
                    "n_trials": 2,
                    "n_response_trials": 2,
                    "n_coherence_levels": 2,
                    "empirical_bias_coherence": 0.0,
                    "fit": {"status": "ok", "bias_coherence": 0.0},
                }
            ],
            "summary_rows": [],
            "chronometric_rows": [
                {
                    "evidence_strength": 3.2,
                    "n_trials": 2,
                    "p_correct": 0.5,
                    "median_response_time": 0.4,
                    "mean_response_time": 0.4,
                }
            ],
            "caveats": ["Escape <unsafe> text"],
        },
        provenance={"source": {"monkeys": ["monkey-1"], "source_repository_commit": "abc"}},
        psychometric_svg_text="<svg><text>Psychometric</text></svg>",
        chronometric_svg_text="<svg><text>Chronometric</text></svg>",
        artifact_links={"analysis result JSON": "analysis_result.json"},
    )

    assert "Random-Dot Motion Report" in html
    assert "monkey-1" in html
    assert "analysis_result.json" in html
    assert "<svg><text>Psychometric</text></svg>" in html
    assert "<svg><text>Chronometric</text></svg>" in html
    assert "Escape &lt;unsafe&gt; text" in html


def test_rdm_report_html_supports_human_rdm_source() -> None:
    html = rdm_report_html(
        {
            "analysis_id": "analysis.human-rdm.descriptive-psychometric",
            "report_title": "Human Random-Dot Motion Report",
            "protocol_id": HUMAN_RDM_PROTOCOL_ID,
            "dataset_id": "dataset.palmer-huk-shadlen-human-rdm-cosmo2017",
            "generated_at": "2026-04-25T00:00:00+00:00",
            "behavtaskatlas_commit": "abc123",
            "behavtaskatlas_git_dirty": False,
            "n_trials": 2,
            "n_response_trials": 2,
            "response_time_origin": "reaction time in seconds",
            "prior_results": [],
            "summary_rows": [],
            "chronometric_rows": [],
            "caveats": [],
        },
        provenance={
            "source": {
                "subjects": ["phs-ah"],
                "source_repository_commit": "5fbffc",
                "source_files": [{"source_file_name": "phs_ah.mat"}],
            }
        },
    )

    assert "Human Random-Dot Motion Report" in html
    assert "Palmer-Huk-Shadlen human random-dot motion" in html
    assert "phs-ah" in html


def test_macaque_rdm_confidence_report_html_contains_source_row_caveat() -> None:
    html = macaque_rdm_confidence_report_html(
        {
            "analysis_id": "analysis.macaque-rdm-confidence.source-data-summary",
            "report_title": "Macaque RDM Confidence Wagering Report",
            "protocol_id": MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID,
            "dataset_id": MACAQUE_RDM_CONFIDENCE_DATASET_ID,
            "generated_at": "2026-04-25T12:00:00+00:00",
            "behavtaskatlas_commit": "abc123",
            "behavtaskatlas_git_dirty": False,
            "n_source_rows": 4,
            "n_accuracy_rows": 2,
            "n_sure_target_choice_rows": 2,
            "subjects": ["kiani-shadlen-m1"],
            "motion_strength_levels": [3.2],
            "confidence_rows": [
                {
                    "monkey": "M1",
                    "motion_strength_percent": 3.2,
                    "n_source_rows": 2,
                    "n_sure_target": 1,
                    "p_sure_target": 0.5,
                }
            ],
            "accuracy_rows": [
                {
                    "source_measure": "accuracy_no_sure_target",
                    "monkey": "M1",
                    "motion_strength_percent": 3.2,
                    "n_source_rows": 2,
                    "n_correct": 1,
                    "p_correct": 0.5,
                }
            ],
            "caveats": ["source-data rows are not raw trials"],
        },
        provenance={
            "source": {
                "article_url": "https://www.nature.com/articles/s41467-021-25419-4",
                "source_data_url": "https://example.org/source.zip",
                "source_tables": [{}, {}],
            }
        },
        accuracy_svg_text="<svg><text>Accuracy</text></svg>",
        confidence_svg_text="<svg><text>Confidence</text></svg>",
        artifact_links={"analysis result JSON": "analysis_result.json"},
    )

    assert "Macaque RDM Confidence Wagering Report" in html
    assert "source-data rows are not raw trials" in html
    assert "analysis_result.json" in html
