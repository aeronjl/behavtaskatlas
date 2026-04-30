from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from behavtaskatlas.fritsche import (
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR,
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID,
    FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
)
from behavtaskatlas.ibl import (
    DEFAULT_IBL_BRAINWIDE_MAP_DERIVED_DIR,
    DEFAULT_IBL_EID,
    DEFAULT_MOUSE_UNBIASED_EID,
    current_git_commit,
    current_git_dirty,
    load_canonical_trials_csv,
)
from behavtaskatlas.models import CanonicalTrial
from behavtaskatlas.steinmetz import DEFAULT_STEINMETZ_DERIVED_DIR
from behavtaskatlas.zatka_haas import (
    DEFAULT_ZATKA_HAAS_HIGHER_POWER_SESSION_ID,
    ZATKA_HAAS_DATASET_ID,
    ZATKA_HAAS_PROTOCOL_ID,
)

VISUAL_CONTRAST_FAMILY_ID = "family.visual-2afc-contrast"
DEFAULT_VISUAL_CONTRAST_FAMILY_DERIVED_DIR = Path("derived/visual_2afc_contrast_family")


@dataclass(frozen=True)
class VisualContrastFamilySource:
    source_id: str
    source_label: str
    slice_id: str
    trials_path: Path


@dataclass(frozen=True)
class VisualContrastFamilyPerturbationSource:
    source_id: str
    source_label: str
    slice_id: str
    dataset_id: str
    protocol_id: str
    effect_path: Path
    comparison_label: str


IBL_BRAINWIDE_MAP_VISUAL_CONTRAST_SESSIONS = [
    ("a7eba2cf-427f-4df9-879b-e53e962eae18", "MFD_08 2023-09-08 churchlandlab_ucla"),
    ("5ae68c54-2897-4d3a-8120-426150704385", "MFD_08 2023-09-07 churchlandlab_ucla"),
    ("3a3ea015-b5f4-4e8b-b189-9364d1fc7435", "NR_0029 2023-09-07 steinmetzlab"),
    ("d85c454e-8737-4cba-b6ad-b2339429d99b", "NR_0029 2023-09-05 steinmetzlab"),
    ("004d8fd5-41e7-4f1b-a45b-0d4ad76fe446", "MFD_05 2023-08-17 churchlandlab_ucla"),
    ("ca4ecb4c-4b60-4723-9b9e-2c54a6290a53", "MFD_05 2023-08-16 churchlandlab_ucla"),
    ("caa5dddc-9290-4e27-9f5e-575ba3598614", "NR_0031 2023-07-14 steinmetzlab"),
    ("642c97ea-fe89-4ec9-8629-5e492ea4019d", "NR_0031 2023-07-12 steinmetzlab"),
    ("e6bdb1f4-b0bf-4451-8f23-4384f2102f91", "PL050 2023-06-15 hausserlab"),
    ("2584ce3c-db10-4076-89cb-5d313138dd38", "PL050 2023-06-13 hausserlab"),
]

STEINMETZ_VISUAL_CONTRAST_SESSIONS = [
    ("Cori-2016-12-14-001", "Cori 2016-12-14"),
    ("Cori-2016-12-17-001", "Cori 2016-12-17"),
    ("Cori-2016-12-18-001", "Cori 2016-12-18"),
    ("Forssmann-2017-11-01-001", "Forssmann 2017-11-01"),
    ("Forssmann-2017-11-02-001", "Forssmann 2017-11-02"),
    ("Forssmann-2017-11-04-001", "Forssmann 2017-11-04"),
    ("Forssmann-2017-11-05-001", "Forssmann 2017-11-05"),
    ("Hench-2017-06-15-001", "Hench 2017-06-15"),
    ("Hench-2017-06-16-001", "Hench 2017-06-16"),
    ("Hench-2017-06-17-001", "Hench 2017-06-17"),
    ("Hench-2017-06-18-001", "Hench 2017-06-18"),
    ("Lederberg-2017-12-05-001", "Lederberg 2017-12-05"),
    ("Lederberg-2017-12-06-001", "Lederberg 2017-12-06"),
    ("Lederberg-2017-12-07-001", "Lederberg 2017-12-07"),
    ("Lederberg-2017-12-08-001", "Lederberg 2017-12-08"),
    ("Lederberg-2017-12-09-001", "Lederberg 2017-12-09"),
    ("Lederberg-2017-12-10-001", "Lederberg 2017-12-10"),
    ("Lederberg-2017-12-11-001", "Lederberg 2017-12-11"),
    ("Moniz-2017-05-15-001", "Moniz 2017-05-15"),
    ("Moniz-2017-05-16-001", "Moniz 2017-05-16"),
    ("Moniz-2017-05-18-001", "Moniz 2017-05-18"),
    ("Muller-2017-01-07-001", "Muller 2017-01-07"),
    ("Muller-2017-01-08-001", "Muller 2017-01-08"),
    ("Muller-2017-01-09-001", "Muller 2017-01-09"),
    ("Radnitz-2017-01-08-001", "Radnitz 2017-01-08"),
    ("Radnitz-2017-01-09-001", "Radnitz 2017-01-09"),
    ("Radnitz-2017-01-10-001", "Radnitz 2017-01-10"),
    ("Radnitz-2017-01-11-001", "Radnitz 2017-01-11"),
    ("Radnitz-2017-01-12-001", "Radnitz 2017-01-12"),
    ("Richards-2017-10-29-001", "Richards 2017-10-29"),
    ("Richards-2017-10-30-001", "Richards 2017-10-30"),
    ("Richards-2017-10-31-001", "Richards 2017-10-31"),
    ("Richards-2017-11-01-001", "Richards 2017-11-01"),
    ("Richards-2017-11-02-001", "Richards 2017-11-02"),
    ("Tatum-2017-12-06-001", "Tatum 2017-12-06"),
    ("Tatum-2017-12-07-001", "Tatum 2017-12-07"),
    ("Tatum-2017-12-08-001", "Tatum 2017-12-08"),
    ("Tatum-2017-12-09-001", "Tatum 2017-12-09"),
    ("Theiler-2017-10-11-001", "Theiler 2017-10-11"),
]


DEFAULT_VISUAL_CONTRAST_FAMILY_SOURCES = [
    VisualContrastFamilySource(
        source_id="ibl-standard-visual-decision",
        source_label="IBL visual decision",
        slice_id="slice.ibl-visual-decision",
        trials_path=Path("derived/ibl_visual_decision") / DEFAULT_IBL_EID / "trials.csv",
    ),
    VisualContrastFamilySource(
        source_id="ibl-training-choiceworld",
        source_label="IBL trainingChoiceWorld",
        slice_id="slice.mouse-visual-contrast-unbiased",
        trials_path=Path("derived/mouse_visual_contrast_unbiased")
        / DEFAULT_MOUSE_UNBIASED_EID
        / "trials.csv",
    ),
    VisualContrastFamilySource(
        source_id="fritsche-temporal-regularities",
        source_label="Fritsche temporal regularities",
        slice_id="slice.fritsche-temporal-regularities",
        trials_path=DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR
        / DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID
        / "trials.csv",
    ),
    *[
        VisualContrastFamilySource(
            source_id=f"ibl-brainwide-map-{eid[:8]}",
            source_label=f"IBL Brainwide Map {label}",
            slice_id="slice.ibl-brainwide-map-behavior",
            trials_path=DEFAULT_IBL_BRAINWIDE_MAP_DERIVED_DIR / eid / "trials.csv",
        )
        for eid, label in IBL_BRAINWIDE_MAP_VISUAL_CONTRAST_SESSIONS
    ],
    *[
        VisualContrastFamilySource(
            source_id=f"steinmetz-{session_id.lower()}",
            source_label=f"Steinmetz {label}",
            slice_id="slice.steinmetz-visual-decision",
            trials_path=DEFAULT_STEINMETZ_DERIVED_DIR / session_id / "trials.csv",
        )
        for session_id, label in STEINMETZ_VISUAL_CONTRAST_SESSIONS
    ],
    VisualContrastFamilySource(
        source_id="zatka-haas-higher-power",
        source_label="Zatka-Haas higher-power inactivation",
        slice_id="slice.zatka-haas-visual-decision",
        trials_path=Path("derived/zatka_haas_visual_decision")
        / DEFAULT_ZATKA_HAAS_HIGHER_POWER_SESSION_ID
        / "trials.csv",
    ),
]

DEFAULT_VISUAL_CONTRAST_FAMILY_PERTURBATION_SOURCES = [
    VisualContrastFamilyPerturbationSource(
        source_id="zatka-haas-higher-power",
        source_label="Zatka-Haas higher-power inactivation",
        slice_id="slice.zatka-haas-visual-decision",
        dataset_id=ZATKA_HAAS_DATASET_ID,
        protocol_id=ZATKA_HAAS_PROTOCOL_ID,
        effect_path=Path("derived/zatka_haas_visual_decision")
        / DEFAULT_ZATKA_HAAS_HIGHER_POWER_SESSION_ID
        / "perturbation_region_effect_summary.csv",
        comparison_label="laser region vs matched non-laser signed contrast",
    ),
]

VISUAL_CONTRAST_SOURCE_SUMMARY_FIELDS = [
    "source_id",
    "source_label",
    "slice_id",
    "dataset_id",
    "protocol_id",
    "response_format",
    "response_format_label",
    "n_trials",
    "n_choice",
    "n_left",
    "n_right",
    "n_withhold",
    "n_no_response",
    "n_unknown",
    "n_correct",
    "p_correct",
    "p_right",
    "p_withhold",
    "p_no_response",
    "median_response_time",
    "n_laser_trials",
    "n_signed_contrast_levels",
]

VISUAL_CONTRAST_SIGNED_SUMMARY_FIELDS = [
    "source_id",
    "source_label",
    "slice_id",
    "dataset_id",
    "protocol_id",
    "response_format",
    "response_format_label",
    "stimulus_value",
    "n_trials",
    "n_choice",
    "n_left",
    "n_right",
    "n_withhold",
    "n_no_response",
    "n_unknown",
    "n_correct",
    "p_correct",
    "p_right",
    "p_withhold",
    "p_no_response",
    "median_response_time",
    "n_laser_trials",
]

VISUAL_CONTRAST_RESPONSE_FORMAT_SUMMARY_FIELDS = [
    "response_format",
    "response_format_label",
    "source_ids",
    "n_sources",
    "n_trials",
    "n_choice",
    "n_left",
    "n_right",
    "n_withhold",
    "n_no_response",
    "n_unknown",
    "n_correct",
    "p_correct",
    "p_right",
    "p_withhold",
    "p_no_response",
    "median_response_time",
    "n_laser_trials",
    "n_signed_contrast_levels",
]

VISUAL_CONTRAST_PROTOCOL_NORMALIZED_FIELDS = [
    "response_format",
    "response_format_label",
    "stimulus_value",
    "source_ids",
    "n_sources",
    "n_trials",
    "n_choice",
    "n_left",
    "n_right",
    "n_withhold",
    "n_no_response",
    "n_unknown",
    "n_correct",
    "p_correct",
    "p_right",
    "p_withhold",
    "p_no_response",
    "median_response_time",
    "n_laser_trials",
]

VISUAL_CONTRAST_SOURCE_BALANCED_PROTOCOL_FIELDS = [
    "response_format",
    "response_format_label",
    "stimulus_value",
    "source_ids",
    "n_sources",
    "n_trials",
    "mean_source_n_trials",
    "n_laser_trials",
    "mean_p_right",
    "sem_p_right",
    "mean_p_withhold",
    "sem_p_withhold",
    "mean_p_no_response",
    "sem_p_no_response",
    "mean_p_correct",
    "sem_p_correct",
    "mean_median_response_time",
    "sem_median_response_time",
]

VISUAL_CONTRAST_SESSION_BALANCED_PROTOCOL_FIELDS = [
    "response_format",
    "response_format_label",
    "stimulus_value",
    "source_ids",
    "session_ids",
    "n_sources",
    "n_sessions",
    "n_trials",
    "mean_session_n_trials",
    "n_laser_trials",
    "mean_p_right",
    "sem_p_right",
    "mean_p_withhold",
    "sem_p_withhold",
    "mean_p_no_response",
    "sem_p_no_response",
    "mean_p_correct",
    "sem_p_correct",
    "mean_median_response_time",
    "sem_median_response_time",
]

VISUAL_CONTRAST_SUBJECT_BALANCED_PROTOCOL_FIELDS = [
    "response_format",
    "response_format_label",
    "stimulus_value",
    "source_ids",
    "subject_ids",
    "n_sources",
    "n_subjects",
    "n_trials",
    "mean_subject_n_trials",
    "n_laser_trials",
    "mean_p_right",
    "sem_p_right",
    "mean_p_withhold",
    "sem_p_withhold",
    "mean_p_no_response",
    "sem_p_no_response",
    "mean_p_correct",
    "sem_p_correct",
    "mean_median_response_time",
    "sem_median_response_time",
]

VISUAL_CONTRAST_PERTURBATION_EFFECT_FIELDS = [
    "source_id",
    "source_label",
    "slice_id",
    "dataset_id",
    "protocol_id",
    "effect_path",
    "comparison_label",
    "laser_region",
    "region_family",
    "hemisphere",
    "n_matched_contrasts",
    "stimulus_values",
    "n_laser_trials",
    "n_non_laser_trials",
    "weighted_delta_p_right",
    "weighted_delta_p_withhold",
    "weighted_delta_p_correct",
    "weighted_delta_median_response_time",
    "max_abs_delta_p_right",
    "max_abs_delta_p_withhold",
]

VISUAL_CONTRAST_POOLED_SUMMARY_FIELDS = [
    "stimulus_value",
    "n_sources",
    "n_trials",
    "n_choice",
    "n_left",
    "n_right",
    "n_withhold",
    "n_no_response",
    "n_unknown",
    "n_correct",
    "p_correct",
    "p_right",
    "p_withhold",
    "p_no_response",
    "median_response_time",
    "n_laser_trials",
]


def load_visual_contrast_family_trials(
    sources: list[VisualContrastFamilySource] | None = None,
) -> list[dict[str, Any]]:
    loaded_sources: list[dict[str, Any]] = []
    for source in sources or DEFAULT_VISUAL_CONTRAST_FAMILY_SOURCES:
        if not source.trials_path.exists():
            raise FileNotFoundError(f"Canonical trials CSV not found: {source.trials_path}")
        trials = load_canonical_trials_csv(source.trials_path)
        loaded_sources.append({"source": source, "trials": trials})
    return loaded_sources


def load_visual_contrast_family_perturbation_effects(
    sources: list[VisualContrastFamilyPerturbationSource] | None = None,
) -> list[dict[str, Any]]:
    effect_rows: list[dict[str, Any]] = []
    for source in sources or DEFAULT_VISUAL_CONTRAST_FAMILY_PERTURBATION_SOURCES:
        if not source.effect_path.exists():
            raise FileNotFoundError(
                f"Perturbation region effect CSV not found: {source.effect_path}"
            )
        with source.effect_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                effect_rows.append(_perturbation_effect_row(source, row))
    return effect_rows


def analyze_visual_contrast_family(
    loaded_sources: list[dict[str, Any]],
    *,
    perturbation_effect_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_rows: list[dict[str, Any]] = []
    signed_rows: list[dict[str, Any]] = []
    all_trials: list[CanonicalTrial] = []
    all_annotated_trials: list[tuple[str, CanonicalTrial]] = []
    all_format_trials: list[tuple[str, str, CanonicalTrial]] = []
    all_session_trials: list[tuple[str, str, str, CanonicalTrial]] = []
    for loaded in loaded_sources:
        source = loaded["source"]
        trials = loaded["trials"]
        response_format = _source_response_format(trials)
        all_trials.extend(trials)
        all_annotated_trials.extend((source.source_id, trial) for trial in trials)
        all_format_trials.extend((response_format, source.source_id, trial) for trial in trials)
        all_session_trials.extend(
            (response_format, source.source_id, trial.session_id, trial) for trial in trials
        )
        source_rows.append(_source_summary_row(source, trials, response_format))
        signed_rows.extend(_signed_contrast_rows(source, trials, response_format))

    pooled_rows = _pooled_signed_contrast_rows(all_annotated_trials)
    response_format_rows = _response_format_summary_rows(all_format_trials)
    protocol_normalized_rows = _protocol_normalized_signed_contrast_rows(
        all_format_trials
    )
    source_balanced_protocol_rows = _source_balanced_protocol_normalized_rows(
        signed_rows
    )
    session_balanced_protocol_rows = _session_balanced_protocol_normalized_rows(
        all_session_trials
    )
    subject_balanced_protocol_rows = _subject_balanced_protocol_normalized_rows(
        all_format_trials
    )
    perturbation_rows = sorted(
        perturbation_effect_rows or [],
        key=_perturbation_effect_sort_key,
    )
    return {
        "analysis_id": "analysis.visual-2afc-contrast-family.real-trial-summary",
        "analysis_type": "family_real_trial_summary",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "family_id": VISUAL_CONTRAST_FAMILY_ID,
        "n_sources": len(loaded_sources),
        "n_trials": len(all_trials),
        "n_choice_trials": sum(1 for trial in all_trials if trial.choice in {"left", "right"}),
        "n_withhold_trials": sum(1 for trial in all_trials if trial.choice == "withhold"),
        "n_no_response_trials": sum(1 for trial in all_trials if trial.choice == "no-response"),
        "n_laser_trials": sum(1 for trial in all_trials if _trial_has_laser(trial)),
        "n_response_format_groups": len(response_format_rows),
        "n_source_balanced_protocol_bins": len(source_balanced_protocol_rows),
        "n_session_balanced_protocol_bins": len(session_balanced_protocol_rows),
        "n_subject_balanced_protocol_bins": len(subject_balanced_protocol_rows),
        "n_sessions": len(
            {(source_id, trial.session_id) for source_id, trial in all_annotated_trials}
        ),
        "n_subjects": len(
            {_subject_key(source_id, trial) for source_id, trial in all_annotated_trials}
        ),
        "n_perturbation_effect_sources": len(
            {row.get("source_id") for row in perturbation_rows}
        ),
        "n_perturbation_region_effects": len(perturbation_rows),
        "source_rows": source_rows,
        "signed_contrast_rows": signed_rows,
        "pooled_signed_contrast_rows": pooled_rows,
        "response_format_rows": response_format_rows,
        "protocol_normalized_signed_contrast_rows": protocol_normalized_rows,
        "source_balanced_protocol_normalized_rows": source_balanced_protocol_rows,
        "session_balanced_protocol_normalized_rows": session_balanced_protocol_rows,
        "subject_balanced_protocol_normalized_rows": subject_balanced_protocol_rows,
        "perturbation_region_effect_rows": perturbation_rows,
        "caveats": [
            (
                "This is a descriptive family summary over available real canonical trial "
                "tables, not an exhaustive meta-analysis over every visual contrast paper."
            ),
            (
                "The pooled rows mix strict 2AFC sessions with unforced wheel sessions; "
                "source_rows and signed_contrast_rows preserve source identity and "
                "withhold/no-response rates so operational task differences remain visible."
            ),
            (
                "Protocol-normalized rows split strict wheel 2AFC-style sources from "
                "unforced wheel sources before plotting choice and non-choice rates."
            ),
            (
                "Source-balanced protocol-normalized rows average source-level rates "
                "within each response-format and signed-contrast bin so larger trial "
                "tables do not dominate the descriptive family curve."
            ),
            (
                "Session-balanced protocol-normalized rows average session-level "
                "rates within each response-format and signed-contrast bin; current "
                "session counts include original Zatka-Haas session identifiers."
            ),
            (
                "Subject-balanced protocol-normalized rows first pool repeated "
                "sessions by dataset-qualified subject id before averaging across "
                "subjects within each response-format and signed-contrast bin."
            ),
            (
                "Perturbation region effect rows currently come from the Zatka-Haas "
                "higher-power inactivation table and compare each laser target to "
                "non-laser trials at matched signed contrasts; they are descriptive "
                "family-facing summaries, not causal model estimates."
            ),
        ],
    }


def write_visual_contrast_family_outputs(
    out_dir: Path,
    analysis_result: dict[str, Any],
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "analysis_result": out_dir / "analysis_result.json",
        "source_summary": out_dir / "source_summary.csv",
        "signed_contrast_summary": out_dir / "signed_contrast_summary.csv",
        "pooled_signed_contrast_summary": out_dir / "pooled_signed_contrast_summary.csv",
        "response_format_summary": out_dir / "response_format_summary.csv",
        "protocol_normalized_signed_contrast_summary": out_dir
        / "protocol_normalized_signed_contrast_summary.csv",
        "protocol_normalized_choice_svg": out_dir / "protocol_normalized_choice.svg",
        "source_balanced_protocol_normalized_summary": out_dir
        / "source_balanced_protocol_normalized_summary.csv",
        "source_balanced_protocol_normalized_svg": out_dir
        / "source_balanced_protocol_normalized.svg",
        "session_balanced_protocol_normalized_summary": out_dir
        / "session_balanced_protocol_normalized_summary.csv",
        "session_balanced_protocol_normalized_svg": out_dir
        / "session_balanced_protocol_normalized.svg",
        "subject_balanced_protocol_normalized_summary": out_dir
        / "subject_balanced_protocol_normalized_summary.csv",
        "subject_balanced_protocol_normalized_svg": out_dir
        / "subject_balanced_protocol_normalized.svg",
        "perturbation_region_effect_summary": out_dir
        / "perturbation_region_effect_summary.csv",
        "perturbation_region_effects_svg": out_dir / "perturbation_region_effects.svg",
        "report": out_dir / "report.html",
    }
    paths["analysis_result"].write_text(
        json.dumps(analysis_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        paths["source_summary"],
        analysis_result["source_rows"],
        VISUAL_CONTRAST_SOURCE_SUMMARY_FIELDS,
    )
    _write_csv(
        paths["signed_contrast_summary"],
        analysis_result["signed_contrast_rows"],
        VISUAL_CONTRAST_SIGNED_SUMMARY_FIELDS,
    )
    _write_csv(
        paths["pooled_signed_contrast_summary"],
        analysis_result["pooled_signed_contrast_rows"],
        VISUAL_CONTRAST_POOLED_SUMMARY_FIELDS,
    )
    _write_csv(
        paths["response_format_summary"],
        analysis_result["response_format_rows"],
        VISUAL_CONTRAST_RESPONSE_FORMAT_SUMMARY_FIELDS,
    )
    _write_csv(
        paths["protocol_normalized_signed_contrast_summary"],
        analysis_result["protocol_normalized_signed_contrast_rows"],
        VISUAL_CONTRAST_PROTOCOL_NORMALIZED_FIELDS,
    )
    paths["protocol_normalized_choice_svg"].write_text(
        visual_contrast_protocol_normalized_svg(
            analysis_result["protocol_normalized_signed_contrast_rows"]
        ),
        encoding="utf-8",
    )
    _write_csv(
        paths["source_balanced_protocol_normalized_summary"],
        analysis_result["source_balanced_protocol_normalized_rows"],
        VISUAL_CONTRAST_SOURCE_BALANCED_PROTOCOL_FIELDS,
    )
    paths["source_balanced_protocol_normalized_svg"].write_text(
        visual_contrast_source_balanced_protocol_svg(
            analysis_result["source_balanced_protocol_normalized_rows"]
        ),
        encoding="utf-8",
    )
    _write_csv(
        paths["session_balanced_protocol_normalized_summary"],
        analysis_result["session_balanced_protocol_normalized_rows"],
        VISUAL_CONTRAST_SESSION_BALANCED_PROTOCOL_FIELDS,
    )
    paths["session_balanced_protocol_normalized_svg"].write_text(
        visual_contrast_session_balanced_protocol_svg(
            analysis_result["session_balanced_protocol_normalized_rows"]
        ),
        encoding="utf-8",
    )
    _write_csv(
        paths["subject_balanced_protocol_normalized_summary"],
        analysis_result["subject_balanced_protocol_normalized_rows"],
        VISUAL_CONTRAST_SUBJECT_BALANCED_PROTOCOL_FIELDS,
    )
    paths["subject_balanced_protocol_normalized_svg"].write_text(
        visual_contrast_subject_balanced_protocol_svg(
            analysis_result["subject_balanced_protocol_normalized_rows"]
        ),
        encoding="utf-8",
    )
    _write_csv(
        paths["perturbation_region_effect_summary"],
        analysis_result["perturbation_region_effect_rows"],
        VISUAL_CONTRAST_PERTURBATION_EFFECT_FIELDS,
    )
    paths["perturbation_region_effects_svg"].write_text(
        visual_contrast_perturbation_svg(
            analysis_result["perturbation_region_effect_rows"]
        ),
        encoding="utf-8",
    )
    paths["report"].write_text(
        visual_contrast_family_report_html(
            analysis_result,
            protocol_normalized_svg_text=paths[
                "protocol_normalized_choice_svg"
            ].read_text(encoding="utf-8"),
            source_balanced_protocol_svg_text=paths[
                "source_balanced_protocol_normalized_svg"
            ].read_text(encoding="utf-8"),
            session_balanced_protocol_svg_text=paths[
                "session_balanced_protocol_normalized_svg"
            ].read_text(encoding="utf-8"),
            subject_balanced_protocol_svg_text=paths[
                "subject_balanced_protocol_normalized_svg"
            ].read_text(encoding="utf-8"),
            perturbation_svg_text=paths["perturbation_region_effects_svg"].read_text(
                encoding="utf-8"
            ),
            artifact_links={
                "Analysis result JSON": "analysis_result.json",
                "Source summary CSV": "source_summary.csv",
                "Signed contrast summary CSV": "signed_contrast_summary.csv",
                "Pooled signed contrast summary CSV": "pooled_signed_contrast_summary.csv",
                "Response format summary CSV": "response_format_summary.csv",
                (
                    "Protocol-normalized signed contrast CSV"
                ): "protocol_normalized_signed_contrast_summary.csv",
                "Protocol-normalized choice SVG": "protocol_normalized_choice.svg",
                (
                    "Source-balanced protocol-normalized CSV"
                ): "source_balanced_protocol_normalized_summary.csv",
                (
                    "Source-balanced protocol-normalized SVG"
                ): "source_balanced_protocol_normalized.svg",
                (
                    "Session-balanced protocol-normalized CSV"
                ): "session_balanced_protocol_normalized_summary.csv",
                (
                    "Session-balanced protocol-normalized SVG"
                ): "session_balanced_protocol_normalized.svg",
                (
                    "Subject-balanced protocol-normalized CSV"
                ): "subject_balanced_protocol_normalized_summary.csv",
                (
                    "Subject-balanced protocol-normalized SVG"
                ): "subject_balanced_protocol_normalized.svg",
                "Perturbation region effect CSV": "perturbation_region_effect_summary.csv",
                "Perturbation region effect SVG": "perturbation_region_effects.svg",
            },
        ),
        encoding="utf-8",
    )
    return paths


def visual_contrast_family_report_html(
    analysis_result: dict[str, Any],
    *,
    protocol_normalized_svg_text: str | None = None,
    source_balanced_protocol_svg_text: str | None = None,
    session_balanced_protocol_svg_text: str | None = None,
    subject_balanced_protocol_svg_text: str | None = None,
    perturbation_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    artifact_links = artifact_links or {}
    protocol_normalized_rows = analysis_result.get(
        "protocol_normalized_signed_contrast_rows",
        [],
    )
    protocol_normalized_svg = (
        protocol_normalized_svg_text
        or visual_contrast_protocol_normalized_svg(
            protocol_normalized_rows if isinstance(protocol_normalized_rows, list) else []
        )
    )
    source_balanced_rows = analysis_result.get(
        "source_balanced_protocol_normalized_rows",
        [],
    )
    source_balanced_svg = (
        source_balanced_protocol_svg_text
        or visual_contrast_source_balanced_protocol_svg(
            source_balanced_rows if isinstance(source_balanced_rows, list) else []
        )
    )
    session_balanced_rows = analysis_result.get(
        "session_balanced_protocol_normalized_rows",
        [],
    )
    session_balanced_svg = (
        session_balanced_protocol_svg_text
        or visual_contrast_session_balanced_protocol_svg(
            session_balanced_rows if isinstance(session_balanced_rows, list) else []
        )
    )
    subject_balanced_rows = analysis_result.get(
        "subject_balanced_protocol_normalized_rows",
        [],
    )
    subject_balanced_svg = (
        subject_balanced_protocol_svg_text
        or visual_contrast_subject_balanced_protocol_svg(
            subject_balanced_rows if isinstance(subject_balanced_rows, list) else []
        )
    )
    perturbation_rows = analysis_result.get("perturbation_region_effect_rows", [])
    perturbation_svg = perturbation_svg_text or visual_contrast_perturbation_svg(
        perturbation_rows if isinstance(perturbation_rows, list) else []
    )
    metrics = [
        ("Sources", analysis_result.get("n_sources")),
        ("Trials", analysis_result.get("n_trials")),
        ("Sessions", analysis_result.get("n_sessions")),
        ("Subjects", analysis_result.get("n_subjects")),
        ("Choice trials", analysis_result.get("n_choice_trials")),
        ("Withhold trials", analysis_result.get("n_withhold_trials")),
        ("No-response trials", analysis_result.get("n_no_response_trials")),
        ("Laser trials", analysis_result.get("n_laser_trials")),
        ("Response formats", analysis_result.get("n_response_format_groups")),
        ("Source-balanced bins", analysis_result.get("n_source_balanced_protocol_bins")),
        ("Session-balanced bins", analysis_result.get("n_session_balanced_protocol_bins")),
        ("Subject-balanced bins", analysis_result.get("n_subject_balanced_protocol_bins")),
        ("Perturbation sources", analysis_result.get("n_perturbation_effect_sources")),
        ("Perturbation effects", analysis_result.get("n_perturbation_region_effects")),
    ]
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Visual Contrast Family Summary</title>",
        "<style>",
        _report_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        f"<p class=\"eyebrow\">{escape(str(analysis_result.get('analysis_id', 'analysis')))}</p>",
        "<h1>Visual Contrast Family Summary</h1>",
        "<p class=\"lede\">Real-trial comparison across available visual contrast "
        "slices, preserving source identity, choice format, withhold outcomes, and "
        "perturbation scope.</p>",
        "</header>",
        '<section class="metrics" aria-label="Report metrics">',
    ]
    for label, value in metrics:
        html.extend(
            [
                '<div class="metric">',
                f"<span>{escape(label)}</span>",
                f"<strong>{escape(_format_cell(value))}</strong>",
                "</div>",
            ]
        )
    html.extend(
        [
            "</section>",
            "<section>",
            "<h2>Sources</h2>",
            _html_table(
                analysis_result.get("source_rows", []),
                [
                    ("source_label", "Source"),
                    ("response_format_label", "Response format"),
                    ("n_trials", "Trials"),
                    ("n_choice", "Choices"),
                    ("n_withhold", "Withhold"),
                    ("n_no_response", "No response"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_correct", "P(correct)"),
                    ("n_laser_trials", "Laser trials"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Protocol-Normalized Choice</h2>",
            '<div class="figure-wrap">',
            protocol_normalized_svg,
            "</div>",
            _html_table(
                analysis_result.get("response_format_rows", []),
                [
                    ("response_format_label", "Response format"),
                    ("n_sources", "Sources"),
                    ("n_trials", "Trials"),
                    ("n_choice", "Choices"),
                    ("n_withhold", "Withhold"),
                    ("n_no_response", "No response"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_no_response", "P(no response)"),
                    ("p_correct", "P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Source-Balanced Protocol-Normalized Choice</h2>",
            '<div class="figure-wrap">',
            source_balanced_svg,
            "</div>",
            _html_table(
                analysis_result.get("source_balanced_protocol_normalized_rows", []),
                [
                    ("response_format_label", "Response format"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_sources", "Sources"),
                    ("n_trials", "Trials"),
                    ("mean_p_right", "Mean P(right)"),
                    ("sem_p_right", "SEM P(right)"),
                    ("mean_p_withhold", "Mean P(withhold)"),
                    ("mean_p_no_response", "Mean P(no response)"),
                    ("mean_p_correct", "Mean P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Session-Balanced Protocol-Normalized Choice</h2>",
            '<div class="figure-wrap">',
            session_balanced_svg,
            "</div>",
            _html_table(
                analysis_result.get("session_balanced_protocol_normalized_rows", []),
                [
                    ("response_format_label", "Response format"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_sessions", "Sessions"),
                    ("n_sources", "Sources"),
                    ("n_trials", "Trials"),
                    ("mean_p_right", "Mean P(right)"),
                    ("sem_p_right", "SEM P(right)"),
                    ("mean_p_withhold", "Mean P(withhold)"),
                    ("mean_p_no_response", "Mean P(no response)"),
                    ("mean_p_correct", "Mean P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Subject-Balanced Protocol-Normalized Choice</h2>",
            '<div class="figure-wrap">',
            subject_balanced_svg,
            "</div>",
            _html_table(
                analysis_result.get("subject_balanced_protocol_normalized_rows", []),
                [
                    ("response_format_label", "Response format"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_subjects", "Subjects"),
                    ("n_sources", "Sources"),
                    ("n_trials", "Trials"),
                    ("mean_p_right", "Mean P(right)"),
                    ("sem_p_right", "SEM P(right)"),
                    ("mean_p_withhold", "Mean P(withhold)"),
                    ("mean_p_no_response", "Mean P(no response)"),
                    ("mean_p_correct", "Mean P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Signed Contrast By Source</h2>",
            _html_table(
                analysis_result.get("signed_contrast_rows", []),
                [
                    ("source_label", "Source"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_trials", "Trials"),
                    ("n_right", "Right"),
                    ("n_withhold", "Withhold"),
                    ("n_no_response", "No response"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_correct", "P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Pooled Signed Contrast</h2>",
            _html_table(
                analysis_result.get("pooled_signed_contrast_rows", []),
                [
                    ("stimulus_value", "Signed contrast"),
                    ("n_sources", "Sources"),
                    ("n_trials", "Trials"),
                    ("n_right", "Right"),
                    ("n_withhold", "Withhold"),
                    ("n_no_response", "No response"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_correct", "P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Protocol-Normalized Signed Contrast</h2>",
            _html_table(
                analysis_result.get("protocol_normalized_signed_contrast_rows", []),
                [
                    ("response_format_label", "Response format"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_sources", "Sources"),
                    ("n_trials", "Trials"),
                    ("n_right", "Right"),
                    ("n_withhold", "Withhold"),
                    ("n_no_response", "No response"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_no_response", "P(no response)"),
                    ("p_correct", "P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Perturbation Region Effects</h2>",
            '<div class="figure-wrap">',
            perturbation_svg,
            "</div>",
            _html_table(
                analysis_result.get("perturbation_region_effect_rows", []),
                [
                    ("source_label", "Source"),
                    ("laser_region", "Laser region"),
                    ("region_family", "Region"),
                    ("hemisphere", "Hemisphere"),
                    ("n_matched_contrasts", "Matched contrasts"),
                    ("n_laser_trials", "Laser trials"),
                    ("weighted_delta_p_right", "Delta P(right)"),
                    ("weighted_delta_p_withhold", "Delta P(withhold)"),
                    ("weighted_delta_p_correct", "Delta P(correct)"),
                    ("weighted_delta_median_response_time", "Delta median RT"),
                ],
            ),
            "</section>",
        ]
    )
    if artifact_links:
        html.extend(["<section>", "<h2>Generated Files</h2>", '<ul class="artifact-list">'])
        for label, href in artifact_links.items():
            html.append(f'<li><a href="{escape(href, quote=True)}">{escape(label)}</a></li>')
        html.extend(["</ul>", "</section>"])

    caveats = analysis_result.get("caveats", [])
    if caveats:
        html.extend(["<section>", "<h2>Caveats</h2>", "<ul>"])
        html.extend(f"<li>{escape(str(caveat))}</li>" for caveat in caveats)
        html.extend(["</ul>", "</section>"])
    html.extend(["</main>", "</body>", "</html>"])
    return "\n".join(html) + "\n"


def visual_contrast_perturbation_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No perturbation effect rows available</text></svg>\n'
        )

    row_height = 34
    width = 980
    left = 194
    right = 32
    top = 72
    bottom = 46
    plot_width = width - left - right
    height = top + bottom + len(rows) * row_height
    metrics = [
        ("weighted_delta_p_right", "Delta P(right)", "#145f91", -8),
        ("weighted_delta_p_withhold", "Delta P(withhold)", "#9a5b00", 0),
        ("weighted_delta_p_correct", "Delta P(correct)", "#287852", 8),
    ]
    values = [
        abs(value)
        for row in rows
        for key, _, _, _ in metrics
        if (value := _numeric(row.get(key))) is not None
    ]
    x_extent = max(0.1, _rounded_axis_extent(max(values) if values else 0.1))
    zero_x = left + plot_width / 2

    def x_scale(value: float) -> float:
        return zero_x + (value / x_extent) * (plot_width / 2)

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{left}" y="26" font-family="sans-serif" font-size="16" '
            'font-weight="700">Matched Zatka-Haas region effects</text>'
        ),
        (
            f'<text x="{left}" y="46" font-family="sans-serif" font-size="12" '
            'fill="#5f6c76">Weighted deltas versus non-laser trials at matched '
            'signed contrasts</text>'
        ),
        (
            f'<line x1="{zero_x:.1f}" y1="{top - 16}" x2="{zero_x:.1f}" '
            f'y2="{height - bottom + 10}" stroke="#4b5563" stroke-width="1"/>'
        ),
    ]
    for tick in [-x_extent, -x_extent / 2, 0.0, x_extent / 2, x_extent]:
        x = x_scale(tick)
        elements.extend(
            [
                (
                    f'<line x1="{x:.1f}" y1="{top - 10}" x2="{x:.1f}" '
                    f'y2="{height - bottom + 10}" stroke="#e5e7eb"/>'
                ),
                (
                    f'<text x="{x:.1f}" y="{height - 16}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="11">{tick:.2g}</text>'
                ),
            ]
        )

    for index, row in enumerate(rows):
        y = top + index * row_height + row_height / 2
        label = str(row.get("laser_region") or "")
        elements.extend(
            [
                (
                    f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" '
                    f'font-family="sans-serif" font-size="12">{escape(label)}</text>'
                ),
                (
                    f'<line x1="{left}" y1="{y + row_height / 2:.1f}" '
                    f'x2="{width - right}" y2="{y + row_height / 2:.1f}" '
                    'stroke="#edf0f2"/>'
                ),
            ]
        )
        for key, _, color, offset in metrics:
            value = _numeric(row.get(key))
            if value is None:
                continue
            x = x_scale(value)
            x0 = min(zero_x, x)
            bar_width = abs(x - zero_x)
            elements.append(
                f'<rect x="{x0:.1f}" y="{y + offset - 3:.1f}" '
                f'width="{bar_width:.1f}" height="6" fill="{color}"/>'
            )

    legend_x = left + 360
    for index, (_, label, color, _) in enumerate(metrics):
        x = legend_x + index * 150
        elements.extend(
            [
                f'<rect x="{x}" y="18" width="12" height="8" fill="{color}"/>',
                (
                    f'<text x="{x + 18}" y="26" font-family="sans-serif" '
                    f'font-size="11">{escape(label)}</text>'
                ),
            ]
        )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def visual_contrast_protocol_normalized_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No protocol-normalized rows available</text></svg>\n'
        )

    row_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        row_groups.setdefault(str(row.get("response_format") or "other"), []).append(row)
    ordered_groups = sorted(row_groups.items(), key=lambda item: _response_format_sort_key(item[0]))
    width = 980
    panel_height = 250
    left = 78
    right = 34
    top = 62
    bottom = 52
    height = top + bottom + panel_height * len(ordered_groups)
    plot_width = width - left - right
    values = [
        float(row["stimulus_value"])
        for row in rows
        if row.get("stimulus_value") is not None
    ]
    x_min = min(values) if values else -100.0
    x_max = max(values) if values else 100.0
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{left}" y="28" font-family="sans-serif" font-size="16" '
            'font-weight="700">Protocol-normalized visual contrast curves</text>'
        ),
        (
            f'<text x="{left}" y="48" font-family="sans-serif" font-size="12" '
            'fill="#5f6c76">Strict 2AFC-style wheel rows are plotted separately '
            'from unforced wheel rows with withholds</text>'
        ),
    ]
    series = [
        ("p_right", "P(right | movement)", "#145f91"),
        ("p_withhold", "P(withhold)", "#9a5b00"),
        ("p_no_response", "P(no response)", "#6b7280"),
    ]
    for panel_index, (response_format, group_rows) in enumerate(ordered_groups):
        panel_top = top + panel_index * panel_height
        plot_top = panel_top + 28
        plot_height = panel_height - 74
        baseline_y = plot_top + plot_height

        def y_scale(
            value: float,
            *,
            panel_plot_top: float = plot_top,
            panel_plot_height: float = plot_height,
        ) -> float:
            return panel_plot_top + (1.0 - value) * panel_plot_height

        elements.extend(
            [
                (
                    f'<text x="{left}" y="{panel_top + 8}" font-family="sans-serif" '
                    f'font-size="13" font-weight="700">'
                    f'{escape(_response_format_label(response_format))}</text>'
                ),
                (
                    f'<line x1="{left}" y1="{baseline_y:.1f}" x2="{width - right}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
                (
                    f'<line x1="{left}" y1="{plot_top}" x2="{left}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
            ]
        )
        for y_value in [0.0, 0.5, 1.0]:
            y = y_scale(y_value)
            elements.extend(
                [
                    (
                        f'<line x1="{left - 4}" y1="{y:.1f}" x2="{width - right}" '
                        f'y2="{y:.1f}" stroke="#e5e7eb"/>'
                    ),
                    (
                        f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                        f'font-family="sans-serif" font-size="11">{y_value:g}</text>'
                    ),
                ]
            )
        for x_value in _axis_tick_values(x_min, x_max):
            x = x_scale(x_value)
            elements.append(
                f'<line x1="{x:.1f}" y1="{baseline_y:.1f}" x2="{x:.1f}" '
                f'y2="{baseline_y + 4:.1f}" stroke="#222"/>'
            )
            if panel_index == len(ordered_groups) - 1:
                elements.append(
                    f'<text x="{x:.1f}" y="{baseline_y + 20:.1f}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="10">{x_value:g}</text>'
                )

        for series_index, (key, label, color) in enumerate(series):
            points = []
            for row in sorted(
                group_rows,
                key=lambda item: _none_safe_float(item["stimulus_value"]),
            ):
                value = _numeric(row.get(key))
                stimulus_value = _numeric(row.get("stimulus_value"))
                if value is None or stimulus_value is None:
                    continue
                if key in {"p_withhold", "p_no_response"} and value == 0:
                    continue
                points.append((x_scale(stimulus_value), y_scale(value), int(row["n_trials"])))
            if not points:
                continue
            point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
            elements.append(
                f'<polyline points="{point_attr}" fill="none" stroke="{color}" '
                'stroke-width="2"/>'
            )
            for x, y, n_trials in points:
                radius = 2.5 + min(n_trials, 300) / 120.0
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" '
                    f'fill="{color}" fill-opacity="0.75"/>'
                )
            legend_x = left + 270 + series_index * 170
            legend_y = panel_top + 4
            elements.extend(
                [
                    (
                        f'<line x1="{legend_x}" y1="{legend_y}" '
                        f'x2="{legend_x + 22}" y2="{legend_y}" '
                        f'stroke="{color}" stroke-width="2"/>'
                    ),
                    (
                        f'<text x="{legend_x + 28}" y="{legend_y + 4}" '
                        f'font-family="sans-serif" font-size="11">{escape(label)}</text>'
                    ),
                ]
            )

    elements.append(
        f'<text x="{left + plot_width / 2}" y="{height - 16}" text-anchor="middle" '
        'font-family="sans-serif" font-size="12">Signed contrast difference '
        "(%; right positive)</text>"
    )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def visual_contrast_source_balanced_protocol_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No source-balanced protocol rows available</text></svg>\n'
        )

    row_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        row_groups.setdefault(str(row.get("response_format") or "other"), []).append(row)
    ordered_groups = sorted(row_groups.items(), key=lambda item: _response_format_sort_key(item[0]))
    width = 980
    panel_height = 250
    left = 78
    right = 34
    top = 62
    bottom = 52
    height = top + bottom + panel_height * len(ordered_groups)
    plot_width = width - left - right
    values = [
        float(row["stimulus_value"])
        for row in rows
        if row.get("stimulus_value") is not None
    ]
    x_min = min(values) if values else -100.0
    x_max = max(values) if values else 100.0
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{left}" y="28" font-family="sans-serif" font-size="16" '
            'font-weight="700">Source-balanced protocol-normalized curves</text>'
        ),
        (
            f'<text x="{left}" y="48" font-family="sans-serif" font-size="12" '
            'fill="#5f6c76">Each source contributes one estimate per '
            'response-format and signed-contrast bin</text>'
        ),
    ]
    series = [
        ("mean_p_right", "Mean P(right | movement)", "#145f91"),
        ("mean_p_withhold", "Mean P(withhold)", "#9a5b00"),
        ("mean_p_no_response", "Mean P(no response)", "#6b7280"),
    ]
    for panel_index, (response_format, group_rows) in enumerate(ordered_groups):
        panel_top = top + panel_index * panel_height
        plot_top = panel_top + 28
        plot_height = panel_height - 74
        baseline_y = plot_top + plot_height

        def y_scale(
            value: float,
            *,
            panel_plot_top: float = plot_top,
            panel_plot_height: float = plot_height,
        ) -> float:
            return panel_plot_top + (1.0 - value) * panel_plot_height

        elements.extend(
            [
                (
                    f'<text x="{left}" y="{panel_top + 8}" font-family="sans-serif" '
                    f'font-size="13" font-weight="700">'
                    f'{escape(_response_format_label(response_format))}</text>'
                ),
                (
                    f'<line x1="{left}" y1="{baseline_y:.1f}" x2="{width - right}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
                (
                    f'<line x1="{left}" y1="{plot_top}" x2="{left}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
            ]
        )
        for y_value in [0.0, 0.5, 1.0]:
            y = y_scale(y_value)
            elements.extend(
                [
                    (
                        f'<line x1="{left - 4}" y1="{y:.1f}" x2="{width - right}" '
                        f'y2="{y:.1f}" stroke="#e5e7eb"/>'
                    ),
                    (
                        f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                        f'font-family="sans-serif" font-size="11">{y_value:g}</text>'
                    ),
                ]
            )
        for x_value in _axis_tick_values(x_min, x_max):
            x = x_scale(x_value)
            elements.append(
                f'<line x1="{x:.1f}" y1="{baseline_y:.1f}" x2="{x:.1f}" '
                f'y2="{baseline_y + 4:.1f}" stroke="#222"/>'
            )
            if panel_index == len(ordered_groups) - 1:
                elements.append(
                    f'<text x="{x:.1f}" y="{baseline_y + 20:.1f}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="10">{x_value:g}</text>'
                )

        for series_index, (key, label, color) in enumerate(series):
            points = []
            for row in sorted(
                group_rows,
                key=lambda item: _none_safe_float(item["stimulus_value"]),
            ):
                value = _numeric(row.get(key))
                stimulus_value = _numeric(row.get("stimulus_value"))
                if value is None or stimulus_value is None:
                    continue
                if key in {"mean_p_withhold", "mean_p_no_response"} and value == 0:
                    continue
                points.append(
                    (x_scale(stimulus_value), y_scale(value), int(row["n_sources"]))
                )
            if not points:
                continue
            point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
            elements.append(
                f'<polyline points="{point_attr}" fill="none" stroke="{color}" '
                'stroke-width="2"/>'
            )
            for x, y, n_sources in points:
                radius = 3.0 + n_sources
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" '
                    f'fill="{color}" fill-opacity="0.75"/>'
                )
            legend_x = left + 250 + series_index * 190
            legend_y = panel_top + 4
            elements.extend(
                [
                    (
                        f'<line x1="{legend_x}" y1="{legend_y}" '
                        f'x2="{legend_x + 22}" y2="{legend_y}" '
                        f'stroke="{color}" stroke-width="2"/>'
                    ),
                    (
                        f'<text x="{legend_x + 28}" y="{legend_y + 4}" '
                        f'font-family="sans-serif" font-size="11">{escape(label)}</text>'
                    ),
                ]
            )

    elements.append(
        f'<text x="{left + plot_width / 2}" y="{height - 16}" text-anchor="middle" '
        'font-family="sans-serif" font-size="12">Signed contrast difference '
        "(%; right positive)</text>"
    )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def visual_contrast_session_balanced_protocol_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No session-balanced protocol rows available</text></svg>\n'
        )

    row_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        row_groups.setdefault(str(row.get("response_format") or "other"), []).append(row)
    ordered_groups = sorted(row_groups.items(), key=lambda item: _response_format_sort_key(item[0]))
    width = 980
    panel_height = 250
    left = 78
    right = 34
    top = 62
    bottom = 52
    height = top + bottom + panel_height * len(ordered_groups)
    plot_width = width - left - right
    values = [
        float(row["stimulus_value"])
        for row in rows
        if row.get("stimulus_value") is not None
    ]
    x_min = min(values) if values else -100.0
    x_max = max(values) if values else 100.0
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{left}" y="28" font-family="sans-serif" font-size="16" '
            'font-weight="700">Session-balanced protocol-normalized curves</text>'
        ),
        (
            f'<text x="{left}" y="48" font-family="sans-serif" font-size="12" '
            'fill="#5f6c76">Each session contributes one estimate per '
            'response-format and signed-contrast bin</text>'
        ),
    ]
    series = [
        ("mean_p_right", "Mean P(right | movement)", "#145f91"),
        ("mean_p_withhold", "Mean P(withhold)", "#9a5b00"),
        ("mean_p_no_response", "Mean P(no response)", "#6b7280"),
    ]
    for panel_index, (response_format, group_rows) in enumerate(ordered_groups):
        panel_top = top + panel_index * panel_height
        plot_top = panel_top + 28
        plot_height = panel_height - 74
        baseline_y = plot_top + plot_height

        def y_scale(
            value: float,
            *,
            panel_plot_top: float = plot_top,
            panel_plot_height: float = plot_height,
        ) -> float:
            return panel_plot_top + (1.0 - value) * panel_plot_height

        elements.extend(
            [
                (
                    f'<text x="{left}" y="{panel_top + 8}" font-family="sans-serif" '
                    f'font-size="13" font-weight="700">'
                    f'{escape(_response_format_label(response_format))}</text>'
                ),
                (
                    f'<line x1="{left}" y1="{baseline_y:.1f}" x2="{width - right}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
                (
                    f'<line x1="{left}" y1="{plot_top}" x2="{left}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
            ]
        )
        for y_value in [0.0, 0.5, 1.0]:
            y = y_scale(y_value)
            elements.extend(
                [
                    (
                        f'<line x1="{left - 4}" y1="{y:.1f}" x2="{width - right}" '
                        f'y2="{y:.1f}" stroke="#e5e7eb"/>'
                    ),
                    (
                        f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                        f'font-family="sans-serif" font-size="11">{y_value:g}</text>'
                    ),
                ]
            )
        for x_value in _axis_tick_values(x_min, x_max):
            x = x_scale(x_value)
            elements.append(
                f'<line x1="{x:.1f}" y1="{baseline_y:.1f}" x2="{x:.1f}" '
                f'y2="{baseline_y + 4:.1f}" stroke="#222"/>'
            )
            if panel_index == len(ordered_groups) - 1:
                elements.append(
                    f'<text x="{x:.1f}" y="{baseline_y + 20:.1f}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="10">{x_value:g}</text>'
                )

        for series_index, (key, label, color) in enumerate(series):
            points = []
            for row in sorted(
                group_rows,
                key=lambda item: _none_safe_float(item["stimulus_value"]),
            ):
                value = _numeric(row.get(key))
                stimulus_value = _numeric(row.get("stimulus_value"))
                if value is None or stimulus_value is None:
                    continue
                if key in {"mean_p_withhold", "mean_p_no_response"} and value == 0:
                    continue
                points.append(
                    (x_scale(stimulus_value), y_scale(value), int(row["n_sessions"]))
                )
            if not points:
                continue
            point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
            elements.append(
                f'<polyline points="{point_attr}" fill="none" stroke="{color}" '
                'stroke-width="2"/>'
            )
            for x, y, n_sessions in points:
                radius = 3.0 + min(n_sessions, 30) / 8.0
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" '
                    f'fill="{color}" fill-opacity="0.75"/>'
                )
            legend_x = left + 250 + series_index * 190
            legend_y = panel_top + 4
            elements.extend(
                [
                    (
                        f'<line x1="{legend_x}" y1="{legend_y}" '
                        f'x2="{legend_x + 22}" y2="{legend_y}" '
                        f'stroke="{color}" stroke-width="2"/>'
                    ),
                    (
                        f'<text x="{legend_x + 28}" y="{legend_y + 4}" '
                        f'font-family="sans-serif" font-size="11">{escape(label)}</text>'
                    ),
                ]
            )

    elements.append(
        f'<text x="{left + plot_width / 2}" y="{height - 16}" text-anchor="middle" '
        'font-family="sans-serif" font-size="12">Signed contrast difference '
        "(%; right positive)</text>"
    )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def visual_contrast_subject_balanced_protocol_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No subject-balanced protocol rows available</text></svg>\n'
        )

    row_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        row_groups.setdefault(str(row.get("response_format") or "other"), []).append(row)
    ordered_groups = sorted(row_groups.items(), key=lambda item: _response_format_sort_key(item[0]))
    width = 980
    panel_height = 250
    left = 78
    right = 34
    top = 62
    bottom = 52
    height = top + bottom + panel_height * len(ordered_groups)
    plot_width = width - left - right
    values = [
        float(row["stimulus_value"])
        for row in rows
        if row.get("stimulus_value") is not None
    ]
    x_min = min(values) if values else -100.0
    x_max = max(values) if values else 100.0
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        (
            f'<text x="{left}" y="28" font-family="sans-serif" font-size="16" '
            'font-weight="700">Subject-balanced protocol-normalized curves</text>'
        ),
        (
            f'<text x="{left}" y="48" font-family="sans-serif" font-size="12" '
            'fill="#5f6c76">Repeated sessions are pooled within each subject '
            'before averaging response-format and signed-contrast bins</text>'
        ),
    ]
    series = [
        ("mean_p_right", "Mean P(right | movement)", "#145f91"),
        ("mean_p_withhold", "Mean P(withhold)", "#9a5b00"),
        ("mean_p_no_response", "Mean P(no response)", "#6b7280"),
    ]
    for panel_index, (response_format, group_rows) in enumerate(ordered_groups):
        panel_top = top + panel_index * panel_height
        plot_top = panel_top + 28
        plot_height = panel_height - 74
        baseline_y = plot_top + plot_height

        def y_scale(
            value: float,
            *,
            panel_plot_top: float = plot_top,
            panel_plot_height: float = plot_height,
        ) -> float:
            return panel_plot_top + (1.0 - value) * panel_plot_height

        elements.extend(
            [
                (
                    f'<text x="{left}" y="{panel_top + 8}" font-family="sans-serif" '
                    f'font-size="13" font-weight="700">'
                    f'{escape(_response_format_label(response_format))}</text>'
                ),
                (
                    f'<line x1="{left}" y1="{baseline_y:.1f}" x2="{width - right}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
                (
                    f'<line x1="{left}" y1="{plot_top}" x2="{left}" '
                    f'y2="{baseline_y:.1f}" stroke="#222"/>'
                ),
            ]
        )
        for y_value in [0.0, 0.5, 1.0]:
            y = y_scale(y_value)
            elements.extend(
                [
                    (
                        f'<line x1="{left - 4}" y1="{y:.1f}" x2="{width - right}" '
                        f'y2="{y:.1f}" stroke="#e5e7eb"/>'
                    ),
                    (
                        f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                        f'font-family="sans-serif" font-size="11">{y_value:g}</text>'
                    ),
                ]
            )
        for x_value in _axis_tick_values(x_min, x_max):
            x = x_scale(x_value)
            elements.append(
                f'<line x1="{x:.1f}" y1="{baseline_y:.1f}" x2="{x:.1f}" '
                f'y2="{baseline_y + 4:.1f}" stroke="#222"/>'
            )
            if panel_index == len(ordered_groups) - 1:
                elements.append(
                    f'<text x="{x:.1f}" y="{baseline_y + 20:.1f}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="10">{x_value:g}</text>'
                )

        for series_index, (key, label, color) in enumerate(series):
            points = []
            for row in sorted(
                group_rows,
                key=lambda item: _none_safe_float(item["stimulus_value"]),
            ):
                value = _numeric(row.get(key))
                stimulus_value = _numeric(row.get("stimulus_value"))
                if value is None or stimulus_value is None:
                    continue
                if key in {"mean_p_withhold", "mean_p_no_response"} and value == 0:
                    continue
                points.append(
                    (x_scale(stimulus_value), y_scale(value), int(row["n_subjects"]))
                )
            if not points:
                continue
            point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
            elements.append(
                f'<polyline points="{point_attr}" fill="none" stroke="{color}" '
                'stroke-width="2"/>'
            )
            for x, y, n_subjects in points:
                radius = 3.0 + min(n_subjects, 30) / 8.0
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" '
                    f'fill="{color}" fill-opacity="0.75"/>'
                )
            legend_x = left + 250 + series_index * 190
            legend_y = panel_top + 4
            elements.extend(
                [
                    (
                        f'<line x1="{legend_x}" y1="{legend_y}" '
                        f'x2="{legend_x + 22}" y2="{legend_y}" '
                        f'stroke="{color}" stroke-width="2"/>'
                    ),
                    (
                        f'<text x="{legend_x + 28}" y="{legend_y + 4}" '
                        f'font-family="sans-serif" font-size="11">{escape(label)}</text>'
                    ),
                ]
            )

    elements.append(
        f'<text x="{left + plot_width / 2}" y="{height - 16}" text-anchor="middle" '
        'font-family="sans-serif" font-size="12">Signed contrast difference '
        "(%; right positive)</text>"
    )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def _source_summary_row(
    source: VisualContrastFamilySource,
    trials: list[CanonicalTrial],
    response_format: str,
) -> dict[str, Any]:
    counts = _choice_summary_counts(trials)
    return {
        "source_id": source.source_id,
        "source_label": source.source_label,
        "slice_id": source.slice_id,
        "dataset_id": _single_value([trial.dataset_id for trial in trials]),
        "protocol_id": _single_value([trial.protocol_id for trial in trials]),
        "response_format": response_format,
        "response_format_label": _response_format_label(response_format),
        "n_signed_contrast_levels": len(
            {trial.stimulus_value for trial in trials if trial.stimulus_value is not None}
        ),
        **counts,
    }


def _signed_contrast_rows(
    source: VisualContrastFamilySource,
    trials: list[CanonicalTrial],
    response_format: str,
) -> list[dict[str, Any]]:
    grouped: dict[float | None, list[CanonicalTrial]] = {}
    for trial in trials:
        grouped.setdefault(trial.stimulus_value, []).append(trial)
    rows: list[dict[str, Any]] = []
    for stimulus_value, group in sorted(
        grouped.items(),
        key=lambda item: _none_safe_float(item[0]),
    ):
        rows.append(
            {
                "source_id": source.source_id,
                "source_label": source.source_label,
                "slice_id": source.slice_id,
                "dataset_id": _single_value([trial.dataset_id for trial in group]),
                "protocol_id": _single_value([trial.protocol_id for trial in group]),
                "response_format": response_format,
                "response_format_label": _response_format_label(response_format),
                "stimulus_value": stimulus_value,
                **_choice_summary_counts(group),
            }
        )
    return rows


def _pooled_signed_contrast_rows(
    annotated_trials: list[tuple[str, CanonicalTrial]],
) -> list[dict[str, Any]]:
    grouped: dict[float | None, list[tuple[str, CanonicalTrial]]] = {}
    for source_id, trial in annotated_trials:
        grouped.setdefault(trial.stimulus_value, []).append((source_id, trial))
    return [
        {
            "stimulus_value": stimulus_value,
            "n_sources": len({source_id for source_id, _ in group}),
            **_choice_summary_counts([trial for _, trial in group]),
        }
        for stimulus_value, group in sorted(
            grouped.items(),
            key=lambda item: _none_safe_float(item[0]),
        )
    ]


def _response_format_summary_rows(
    annotated_trials: list[tuple[str, str, CanonicalTrial]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[str, CanonicalTrial]]] = {}
    for response_format, source_id, trial in annotated_trials:
        grouped.setdefault(response_format, []).append((source_id, trial))
    return [
        {
            "response_format": response_format,
            "response_format_label": _response_format_label(response_format),
            "source_ids": _source_ids_text(group),
            "n_sources": len({source_id for source_id, _ in group}),
            "n_signed_contrast_levels": len(
                {trial.stimulus_value for _, trial in group if trial.stimulus_value is not None}
            ),
            **_choice_summary_counts([trial for _, trial in group]),
        }
        for response_format, group in sorted(
            grouped.items(),
            key=lambda item: _response_format_sort_key(item[0]),
        )
    ]


def _protocol_normalized_signed_contrast_rows(
    annotated_trials: list[tuple[str, str, CanonicalTrial]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float | None], list[tuple[str, CanonicalTrial]]] = {}
    for response_format, source_id, trial in annotated_trials:
        grouped.setdefault((response_format, trial.stimulus_value), []).append(
            (source_id, trial)
        )
    return [
        {
            "response_format": response_format,
            "response_format_label": _response_format_label(response_format),
            "stimulus_value": stimulus_value,
            "source_ids": _source_ids_text(group),
            "n_sources": len({source_id for source_id, _ in group}),
            **_choice_summary_counts([trial for _, trial in group]),
        }
        for (response_format, stimulus_value), group in sorted(
            grouped.items(),
            key=lambda item: (
                _response_format_sort_key(item[0][0]),
                _none_safe_float(item[0][1]),
            ),
        )
    ]


def _source_balanced_protocol_normalized_rows(
    signed_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float | None], list[dict[str, Any]]] = {}
    for row in signed_rows:
        response_format = str(row.get("response_format") or "unknown")
        grouped.setdefault((response_format, row.get("stimulus_value")), []).append(row)

    balanced_rows: list[dict[str, Any]] = []
    for (response_format, stimulus_value), group in sorted(
        grouped.items(),
        key=lambda item: (
            _response_format_sort_key(item[0][0]),
            _none_safe_float(item[0][1]),
        ),
    ):
        balanced_rows.append(
            {
                "response_format": response_format,
                "response_format_label": _response_format_label(response_format),
                "stimulus_value": stimulus_value,
                "source_ids": ",".join(sorted(str(row["source_id"]) for row in group)),
                "n_sources": len(group),
                "n_trials": sum(_int_value(row.get("n_trials")) for row in group),
                "mean_source_n_trials": _mean_values(row.get("n_trials") for row in group),
                "n_laser_trials": sum(
                    _int_value(row.get("n_laser_trials")) for row in group
                ),
                "mean_p_right": _mean_values(row.get("p_right") for row in group),
                "sem_p_right": _sem_values(row.get("p_right") for row in group),
                "mean_p_withhold": _mean_values(row.get("p_withhold") for row in group),
                "sem_p_withhold": _sem_values(row.get("p_withhold") for row in group),
                "mean_p_no_response": _mean_values(
                    row.get("p_no_response") for row in group
                ),
                "sem_p_no_response": _sem_values(
                    row.get("p_no_response") for row in group
                ),
                "mean_p_correct": _mean_values(row.get("p_correct") for row in group),
                "sem_p_correct": _sem_values(row.get("p_correct") for row in group),
                "mean_median_response_time": _mean_values(
                    row.get("median_response_time") for row in group
                ),
                "sem_median_response_time": _sem_values(
                    row.get("median_response_time") for row in group
                ),
            }
        )
    return balanced_rows


def _session_balanced_protocol_normalized_rows(
    annotated_trials: list[tuple[str, str, str, CanonicalTrial]],
) -> list[dict[str, Any]]:
    session_bins: dict[
        tuple[str, float | None, str, str],
        list[CanonicalTrial],
    ] = {}
    for response_format, source_id, session_id, trial in annotated_trials:
        key = (response_format, trial.stimulus_value, source_id, session_id)
        session_bins.setdefault(key, []).append(trial)

    session_rows_by_bin: dict[tuple[str, float | None], list[dict[str, Any]]] = {}
    for (response_format, stimulus_value, source_id, session_id), trials in session_bins.items():
        row = {
            "response_format": response_format,
            "stimulus_value": stimulus_value,
            "source_id": source_id,
            "session_id": session_id,
            "session_key": _session_key(source_id, session_id),
            **_choice_summary_counts(trials),
        }
        session_rows_by_bin.setdefault((response_format, stimulus_value), []).append(row)

    balanced_rows: list[dict[str, Any]] = []
    for (response_format, stimulus_value), rows in sorted(
        session_rows_by_bin.items(),
        key=lambda item: (
            _response_format_sort_key(item[0][0]),
            _none_safe_float(item[0][1]),
        ),
    ):
        balanced_rows.append(
            {
                "response_format": response_format,
                "response_format_label": _response_format_label(response_format),
                "stimulus_value": stimulus_value,
                "source_ids": ",".join(sorted({str(row["source_id"]) for row in rows})),
                "session_ids": ",".join(sorted(str(row["session_key"]) for row in rows)),
                "n_sources": len({row["source_id"] for row in rows}),
                "n_sessions": len(rows),
                "n_trials": sum(_int_value(row.get("n_trials")) for row in rows),
                "mean_session_n_trials": _mean_values(row.get("n_trials") for row in rows),
                "n_laser_trials": sum(
                    _int_value(row.get("n_laser_trials")) for row in rows
                ),
                "mean_p_right": _mean_values(row.get("p_right") for row in rows),
                "sem_p_right": _sem_values(row.get("p_right") for row in rows),
                "mean_p_withhold": _mean_values(row.get("p_withhold") for row in rows),
                "sem_p_withhold": _sem_values(row.get("p_withhold") for row in rows),
                "mean_p_no_response": _mean_values(
                    row.get("p_no_response") for row in rows
                ),
                "sem_p_no_response": _sem_values(
                    row.get("p_no_response") for row in rows
                ),
                "mean_p_correct": _mean_values(row.get("p_correct") for row in rows),
                "sem_p_correct": _sem_values(row.get("p_correct") for row in rows),
                "mean_median_response_time": _mean_values(
                    row.get("median_response_time") for row in rows
                ),
                "sem_median_response_time": _sem_values(
                    row.get("median_response_time") for row in rows
                ),
            }
        )
    return balanced_rows


def _subject_balanced_protocol_normalized_rows(
    annotated_trials: list[tuple[str, str, CanonicalTrial]],
) -> list[dict[str, Any]]:
    subject_bins: dict[
        tuple[str, float | None, str],
        list[tuple[str, CanonicalTrial]],
    ] = {}
    for response_format, source_id, trial in annotated_trials:
        subject_key = _subject_key(source_id, trial)
        key = (response_format, trial.stimulus_value, subject_key)
        subject_bins.setdefault(key, []).append((source_id, trial))

    subject_rows_by_bin: dict[tuple[str, float | None], list[dict[str, Any]]] = {}
    for (response_format, stimulus_value, subject_key), source_trials in subject_bins.items():
        source_ids = sorted({source_id for source_id, _ in source_trials})
        trials = [trial for _, trial in source_trials]
        row = {
            "response_format": response_format,
            "stimulus_value": stimulus_value,
            "source_ids": ",".join(source_ids),
            "subject_id": subject_key,
            **_choice_summary_counts(trials),
        }
        subject_rows_by_bin.setdefault((response_format, stimulus_value), []).append(row)

    balanced_rows: list[dict[str, Any]] = []
    for (response_format, stimulus_value), rows in sorted(
        subject_rows_by_bin.items(),
        key=lambda item: (
            _response_format_sort_key(item[0][0]),
            _none_safe_float(item[0][1]),
        ),
    ):
        source_ids = sorted(
            {
                source_id
                for row in rows
                for source_id in str(row.get("source_ids", "")).split(",")
                if source_id
            }
        )
        balanced_rows.append(
            {
                "response_format": response_format,
                "response_format_label": _response_format_label(response_format),
                "stimulus_value": stimulus_value,
                "source_ids": ",".join(source_ids),
                "subject_ids": ",".join(sorted(str(row["subject_id"]) for row in rows)),
                "n_sources": len(source_ids),
                "n_subjects": len(rows),
                "n_trials": sum(_int_value(row.get("n_trials")) for row in rows),
                "mean_subject_n_trials": _mean_values(row.get("n_trials") for row in rows),
                "n_laser_trials": sum(
                    _int_value(row.get("n_laser_trials")) for row in rows
                ),
                "mean_p_right": _mean_values(row.get("p_right") for row in rows),
                "sem_p_right": _sem_values(row.get("p_right") for row in rows),
                "mean_p_withhold": _mean_values(row.get("p_withhold") for row in rows),
                "sem_p_withhold": _sem_values(row.get("p_withhold") for row in rows),
                "mean_p_no_response": _mean_values(
                    row.get("p_no_response") for row in rows
                ),
                "sem_p_no_response": _sem_values(
                    row.get("p_no_response") for row in rows
                ),
                "mean_p_correct": _mean_values(row.get("p_correct") for row in rows),
                "sem_p_correct": _sem_values(row.get("p_correct") for row in rows),
                "mean_median_response_time": _mean_values(
                    row.get("median_response_time") for row in rows
                ),
                "sem_median_response_time": _sem_values(
                    row.get("median_response_time") for row in rows
                ),
            }
        )
    return balanced_rows


def _perturbation_effect_row(
    source: VisualContrastFamilyPerturbationSource,
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_label": source.source_label,
        "slice_id": source.slice_id,
        "dataset_id": source.dataset_id,
        "protocol_id": source.protocol_id,
        "effect_path": str(source.effect_path),
        "comparison_label": source.comparison_label,
        "laser_region": row.get("laser_region"),
        "region_family": row.get("region_family"),
        "hemisphere": row.get("hemisphere"),
        "n_matched_contrasts": _csv_int(row, "n_matched_contrasts"),
        "stimulus_values": row.get("stimulus_values"),
        "n_laser_trials": _csv_int(row, "n_laser_trials"),
        "n_non_laser_trials": _csv_int(row, "n_non_laser_trials"),
        "weighted_delta_p_right": _csv_float(row, "weighted_delta_p_right"),
        "weighted_delta_p_withhold": _csv_float(row, "weighted_delta_p_withhold"),
        "weighted_delta_p_correct": _csv_float(row, "weighted_delta_p_correct"),
        "weighted_delta_median_response_time": _csv_float(
            row,
            "weighted_delta_median_response_time",
        ),
        "max_abs_delta_p_right": _csv_float(row, "max_abs_delta_p_right"),
        "max_abs_delta_p_withhold": _csv_float(row, "max_abs_delta_p_withhold"),
    }


def _perturbation_effect_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    family_order = {
        "VIS": 0,
        "M2": 1,
        "S1": 2,
        "RSP": 3,
        "M1": 4,
        "FrontOutside": 5,
    }
    hemisphere_order = {"left": 0, "right": 1, "bilateral": 2}
    return (
        str(row.get("source_id") or ""),
        family_order.get(str(row.get("region_family") or ""), 99),
        hemisphere_order.get(str(row.get("hemisphere") or ""), 99),
        str(row.get("laser_region") or ""),
    )


def _choice_summary_counts(trials: list[CanonicalTrial]) -> dict[str, Any]:
    n_trials = len(trials)
    n_left = sum(1 for trial in trials if trial.choice == "left")
    n_right = sum(1 for trial in trials if trial.choice == "right")
    n_withhold = sum(1 for trial in trials if trial.choice == "withhold")
    n_no_response = sum(1 for trial in trials if trial.choice == "no-response")
    n_unknown = sum(1 for trial in trials if trial.choice == "unknown")
    n_choice = n_left + n_right
    correct_values = [trial.correct for trial in trials if trial.correct is not None]
    n_correct = sum(1 for value in correct_values if value)
    response_times = [
        float(trial.response_time)
        for trial in trials
        if trial.response_time is not None and math.isfinite(float(trial.response_time))
    ]
    return {
        "n_trials": n_trials,
        "n_choice": n_choice,
        "n_left": n_left,
        "n_right": n_right,
        "n_withhold": n_withhold,
        "n_no_response": n_no_response,
        "n_unknown": n_unknown,
        "n_correct": n_correct,
        "p_correct": _safe_ratio(n_correct, len(correct_values)),
        "p_right": _safe_ratio(n_right, n_choice),
        "p_withhold": _safe_ratio(n_withhold, n_trials),
        "p_no_response": _safe_ratio(n_no_response, n_trials),
        "median_response_time": _median(response_times),
        "n_laser_trials": sum(1 for trial in trials if _trial_has_laser(trial)),
    }


def _source_response_format(trials: list[CanonicalTrial]) -> str:
    protocols = {trial.protocol_id for trial in trials if trial.protocol_id}
    formats = {_response_format_for_protocol(protocol_id) for protocol_id in protocols}
    if len(formats) == 1:
        return formats.pop()
    if not formats:
        return "unknown"
    return "mixed"


def _response_format_for_protocol(protocol_id: str) -> str:
    if protocol_id in {
        "protocol.ibl-visual-decision-v1",
        "protocol.mouse-visual-contrast-wheel-unbiased",
        FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
    }:
        return "strict_2afc_wheel"
    if protocol_id == "protocol.mouse-unforced-visual-contrast-wheel":
        return "unforced_wheel"
    return "other"


def _response_format_label(response_format: str) -> str:
    labels = {
        "strict_2afc_wheel": "Strict 2AFC wheel",
        "unforced_wheel": "Unforced wheel",
        "mixed": "Mixed response formats",
        "other": "Other response format",
        "unknown": "Unknown response format",
    }
    return labels.get(response_format, response_format.replace("_", " ").title())


def _response_format_sort_key(response_format: str) -> tuple[int, str]:
    order = {
        "strict_2afc_wheel": 0,
        "unforced_wheel": 1,
        "mixed": 98,
        "other": 99,
        "unknown": 100,
    }
    return (order.get(response_format, 99), response_format)


def _source_ids_text(group: list[tuple[str, CanonicalTrial]]) -> str:
    return ",".join(sorted({source_id for source_id, _ in group}))


def _session_key(source_id: str, session_id: str) -> str:
    return f"{source_id}:{session_id}"


def _subject_key(source_id: str, trial: CanonicalTrial) -> str:
    dataset_id = trial.dataset_id or source_id
    subject_id = trial.subject_id or "unknown-subject"
    return f"{dataset_id}:{subject_id}"


def _trial_has_laser(trial: CanonicalTrial) -> bool:
    laser_type = _numeric(trial.task_variables.get("laser_type"))
    laser_power = _numeric(trial.task_variables.get("laser_power"))
    return (laser_type is not None and laser_type > 0) or (
        laser_power is not None and laser_power > 0
    )


def _single_value(values: list[Any]) -> Any:
    unique = sorted({value for value in values if value is not None})
    if len(unique) == 1:
        return unique[0]
    if not unique:
        return None
    return ";".join(str(value) for value in unique)


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _csv_float(row: dict[str, Any], key: str) -> float | None:
    return _numeric(row.get(key))


def _csv_int(row: dict[str, Any], key: str) -> int | None:
    numeric = _numeric(row.get(key))
    if numeric is None:
        return None
    return int(numeric)


def _int_value(value: Any) -> int:
    numeric = _numeric(value)
    if numeric is None:
        return 0
    return int(numeric)


def _mean_values(values: Any) -> float | None:
    numeric_values = [_numeric(value) for value in values]
    finite_values = [value for value in numeric_values if value is not None]
    if not finite_values:
        return None
    return sum(finite_values) / len(finite_values)


def _sem_values(values: Any) -> float | None:
    numeric_values = [_numeric(value) for value in values]
    finite_values = [value for value in numeric_values if value is not None]
    if len(finite_values) < 2:
        return None
    mean_value = sum(finite_values) / len(finite_values)
    variance = sum((value - mean_value) ** 2 for value in finite_values) / (
        len(finite_values) - 1
    )
    return math.sqrt(variance) / math.sqrt(len(finite_values))


def _none_safe_float(value: Any) -> float:
    numeric = _numeric(value)
    return float("inf") if numeric is None else numeric


def _rounded_axis_extent(value: float) -> float:
    if value <= 0:
        return 0.1
    magnitude = 10.0 ** math.floor(math.log10(value))
    scaled = value / magnitude
    for candidate in [1.0, 2.0, 5.0, 10.0]:
        if scaled <= candidate:
            return candidate * magnitude
    return 10.0 * magnitude


def _axis_tick_values(x_min: float, x_max: float, max_ticks: int = 9) -> list[float]:
    if x_min == x_max:
        return [x_min]
    span = x_max - x_min
    raw_step = span / max(max_ticks - 1, 1)
    magnitude = 10.0 ** math.floor(math.log10(raw_step))
    step = next(
        candidate * magnitude
        for candidate in [1.0, 2.0, 5.0, 10.0]
        if candidate * magnitude >= raw_step
    )
    start = math.ceil(x_min / step) * step
    ticks = []
    value = start
    while value <= x_max + step * 1e-9:
        ticks.append(0.0 if abs(value) < step * 1e-9 else value)
        value += step
    if x_min < 0.0 < x_max and all(abs(tick) > step * 1e-9 for tick in ticks):
        ticks.append(0.0)
    return sorted(ticks)


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def _html_table(rows: Any, columns: list[tuple[str, str]]) -> str:
    if not isinstance(rows, list) or not rows:
        return '<p class="empty">No rows available.</p>'
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for _, label in columns:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        if not isinstance(row, dict):
            continue
        parts.append("<tr>")
        for key, _ in columns:
            parts.append(f"<td>{escape(_format_cell(row.get(key)))}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    numeric = _numeric(value)
    if numeric is not None:
        if numeric.is_integer():
            return f"{int(numeric):,}"
        return f"{numeric:.4g}"
    return str(value)


def _report_css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #17212b;
  --muted: #5f6c76;
  --line: #d8dee4;
  --panel: #f6f8fa;
  --accent: #145f91;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: #ffffff;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  line-height: 1.45;
}
main {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 32px 0 48px;
}
header {
  padding-bottom: 22px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 0.82rem;
  font-weight: 800;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 3.3rem);
  line-height: 1.04;
}
h2 {
  margin: 0 0 14px;
  font-size: 1.15rem;
}
.lede {
  max-width: 820px;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 1.05rem;
}
section {
  margin-top: 28px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.metric {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: var(--panel);
}
.metric span {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}
.metric strong {
  display: block;
  margin-top: 4px;
  font-size: 1.42rem;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.figure-wrap {
  overflow-x: auto;
  margin-bottom: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.figure-wrap svg {
  display: block;
  max-width: 100%;
  height: auto;
}
table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th,
td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--panel);
  color: #2f3b45;
  font-size: 0.76rem;
  text-transform: uppercase;
}
tbody tr:last-child td {
  border-bottom: 0;
}
.artifact-list {
  columns: 2;
  padding-left: 18px;
}
a {
  color: var(--accent);
}
@media (max-width: 720px) {
  main {
    width: min(100vw - 20px, 1180px);
    padding-top: 20px;
  }
  .artifact-list {
    columns: 1;
  }
}
""".strip()
