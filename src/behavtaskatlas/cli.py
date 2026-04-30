from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from behavtaskatlas.allen import (
    DEFAULT_ALLEN_VBN_DERIVED_DIR,
    DEFAULT_ALLEN_VBN_RAW_DIR,
    DEFAULT_ALLEN_VISUAL_BEHAVIOR_DERIVED_DIR,
    DEFAULT_ALLEN_VISUAL_BEHAVIOR_RAW_DIR,
    allen_vbn_provenance_payload,
    allen_visual_behavior_provenance_payload,
    analyze_allen_change_detection,
    analyze_allen_vbn_change_detection,
    download_allen_visual_behavior_session,
    load_allen_vbn_session,
    load_allen_visual_behavior_session,
    write_change_detection_report_html,
    write_image_pair_csv,
    write_lick_latency_svg,
    write_outcome_summary_csv,
)
from behavtaskatlas.allen import write_analysis_json as write_allen_analysis_json
from behavtaskatlas.allen import (
    write_canonical_trials_csv as write_allen_canonical_trials_csv,
)
from behavtaskatlas.clicks import (
    CLICKS_PSYCHOMETRIC_X_AXIS_LABEL,
    DEFAULT_CLICKS_DERIVED_DIR,
    DEFAULT_CLICKS_SESSION_ID,
    DEFAULT_HUMAN_CLICKS_DERIVED_DIR,
    DEFAULT_HUMAN_CLICKS_RAW_MAT,
    DEFAULT_HUMAN_CLICKS_SESSION_ID,
    HUMAN_CLICKS_PSYCHOMETRIC_X_AXIS_LABEL,
    aggregate_brody_clicks_batch,
    analyze_brody_clicks,
    analyze_brody_clicks_evidence_kernel,
    analyze_human_clicks,
    analyze_human_clicks_evidence_kernel,
    brody_clicks_aggregate_provenance_payload,
    brody_clicks_provenance_payload,
    concatenate_brody_clicks_trials,
    download_human_clicks_mendeley_mat,
    human_clicks_provenance_payload,
    load_brody_clicks_mat,
    load_human_clicks_mendeley_mat,
    write_aggregate_kernel_summary_csv,
    write_aggregate_kernel_svg,
    write_aggregate_psychometric_bias_csv,
    write_clicks_aggregate_report_html,
    write_clicks_batch_summary_csv,
    write_clicks_session_report_html,
    write_evidence_kernel_summary_csv,
    write_evidence_kernel_svg,
)
from behavtaskatlas.coen import (
    DEFAULT_COEN_DERIVED_DIR,
    DEFAULT_COEN_RAW_FILE,
    DEFAULT_COEN_SESSION_ID,
    analyze_coen_audiovisual_decisions,
    coen_provenance_payload,
    load_coen_audiovisual_source,
    write_coen_condition_csv,
    write_coen_condition_svg,
    write_coen_conflict_csv,
    write_coen_modality_csv,
    write_coen_report_html,
)
from behavtaskatlas.findings import (
    build_comparisons_index,
    build_findings_index,
    extract_accuracy_findings_for_slice,
    extract_chronometric_findings_for_slice,
    extract_psychometric_findings_for_slice,
    extract_subject_chronometric_findings_for_slice,
    extract_subject_condition_psychometric_findings_for_slice,
    extract_subject_psychometric_findings_for_slice,
    import_csv_findings,
    load_import_mapping,
    write_finding_yaml,
)
from behavtaskatlas.fritsche import (
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_CODE_ZIP,
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR,
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR,
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID,
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_ZIP,
    analyze_fritsche_temporal_regularities,
    build_fritsche_code_manifest,
    download_fritsche_temporal_regularities_code,
    download_fritsche_temporal_regularities_data,
    fritsche_artifact_provenance_rows,
    fritsche_temporal_regularities_provenance_payload,
    harmonize_fritsche_temporal_regularities_rows,
    load_fritsche_temporal_regularities_rows,
    write_fritsche_artifact_provenance_csv,
    write_fritsche_choice_history_csv,
    write_fritsche_choice_history_model_csv,
    write_fritsche_code_manifest,
    write_fritsche_neutral_adaptation_csv,
    write_fritsche_neutral_adaptation_session_csv,
    write_fritsche_report_html,
    write_fritsche_subject_environment_csv,
    write_fritsche_transition_csv,
)
from behavtaskatlas.human_visual import (
    DEFAULT_HUMAN_VISUAL_CONTRAST_DERIVED_DIR,
    DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_DIR,
    DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_MAT,
    DEFAULT_HUMAN_VISUAL_CONTRAST_SESSION_ID,
    HUMAN_VISUAL_CONTRAST_PSYCHOMETRIC_X_AXIS_LABEL,
    analyze_human_visual_contrast,
    download_walsh_human_visual_contrast_files,
    human_visual_contrast_provenance_payload,
    load_walsh_human_visual_contrast_mat,
)
from behavtaskatlas.ibl import (
    DEFAULT_DERIVED_DIR,
    DEFAULT_IBL_BRAINWIDE_MAP_DERIVED_DIR,
    DEFAULT_IBL_BRAINWIDE_MAP_EID,
    DEFAULT_IBL_EID,
    DEFAULT_MOUSE_UNBIASED_DERIVED_DIR,
    DEFAULT_MOUSE_UNBIASED_EID,
    IBL_BRAINWIDE_MAP_DATASET_ID,
    IBL_VISUAL_PROTOCOL_ID,
    MOUSE_UNBIASED_VISUAL_PROTOCOL_ID,
    analyze_ibl_brainwide_map_behavior,
    analyze_ibl_visual_protocol,
    harmonize_ibl_visual_trials,
    ibl_brainwide_map_provenance_payload,
    load_canonical_trials_csv,
    load_ibl_trials_from_openalyx,
    provenance_payload,
    summarize_canonical_trials,
    write_analysis_json,
    write_canonical_trials_csv,
    write_ibl_visual_report_html,
    write_provenance_json,
    write_psychometric_svg,
    write_summary_csv,
)
from behavtaskatlas.models import SCHEMA_MODELS, CanonicalTrial
from behavtaskatlas.odoemene import (
    DEFAULT_ODOEMENE_DERIVED_DIR,
    DEFAULT_ODOEMENE_RAW_MAT,
    DEFAULT_ODOEMENE_SESSION_ID,
    analyze_odoemene_visual_accumulation,
    load_odoemene_visual_accumulation_mat,
    odoemene_provenance_payload,
    write_odoemene_kernel_csv,
    write_odoemene_kernel_svg,
    write_odoemene_report_html,
)
from behavtaskatlas.rdm import (
    DEFAULT_HUMAN_RDM_DERIVED_DIR,
    DEFAULT_HUMAN_RDM_RAW_DIR,
    DEFAULT_HUMAN_RDM_SESSION_ID,
    DEFAULT_MACAQUE_RDM_CONFIDENCE_DERIVED_DIR,
    DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_BEHAVIOR_DIR,
    DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_ZIP,
    DEFAULT_MACAQUE_RDM_CONFIDENCE_SESSION_ID,
    DEFAULT_RDM_DERIVED_DIR,
    DEFAULT_RDM_RAW_CSV,
    DEFAULT_RDM_SESSION_ID,
    HUMAN_RDM_PSYCHOMETRIC_X_AXIS_LABEL,
    HUMAN_RDM_SUBJECT_IDS,
    RDM_PSYCHOMETRIC_X_AXIS_LABEL,
    analyze_human_rdm,
    analyze_macaque_rdm_confidence,
    analyze_roitman_rdm,
    check_macaque_rdm_confidence_raw_behavior_intake,
    download_human_rdm_phs_files,
    download_macaque_rdm_confidence_source_data,
    download_roitman_rdm_csv,
    format_macaque_rdm_confidence_raw_behavior_intake_report,
    human_rdm_provenance_payload,
    load_human_rdm_phs_mats,
    load_macaque_rdm_confidence_raw_behavior_mats,
    load_macaque_rdm_confidence_source_data,
    load_roitman_rdm_csv,
    macaque_rdm_confidence_provenance_payload,
    rdm_provenance_payload,
    write_macaque_rdm_confidence_accuracy_csv,
    write_macaque_rdm_confidence_accuracy_svg,
    write_macaque_rdm_confidence_choice_csv,
    write_macaque_rdm_confidence_choice_svg,
    write_macaque_rdm_confidence_report_html,
    write_rdm_chronometric_csv,
    write_rdm_chronometric_svg,
    write_rdm_report_html,
)
from behavtaskatlas.release import (
    build_release_check_payload,
    write_release_check_html,
    write_release_check_json,
)
from behavtaskatlas.rodgers import (
    DEFAULT_RODGERS_DERIVED_DIR,
    DEFAULT_RODGERS_RAW_FILE,
    DEFAULT_RODGERS_SESSION_ID,
    analyze_rodgers_whisker_object_recognition,
    load_rodgers_whisker_source,
    rodgers_provenance_payload,
    write_rodgers_accuracy_svg,
    write_rodgers_condition_csv,
    write_rodgers_detection_csv,
    write_rodgers_report_html,
    write_rodgers_task_rule_csv,
)
from behavtaskatlas.static_site import (
    build_catalog_payload,
    build_curation_queue_payload,
    build_relationship_graph_payload,
    build_static_index_payload,
    load_repository_records,
    write_static_catalog_json,
    write_static_curation_queue_json,
    write_static_graph_json,
    write_static_manifest_json,
)
from behavtaskatlas.steinmetz import (
    DEFAULT_STEINMETZ_DERIVED_DIR,
    DEFAULT_STEINMETZ_RAW_DIR,
    DEFAULT_STEINMETZ_SESSION_ID,
    analyze_steinmetz_session_aggregate,
    analyze_steinmetz_visual_decision,
    harmonize_steinmetz_visual_trials,
    load_steinmetz_derived_sessions,
    load_steinmetz_session_dir,
    steinmetz_provenance_payload,
    summarize_steinmetz_choice_by_contrast_pair,
    summarize_steinmetz_choice_by_signed_contrast,
    write_steinmetz_aggregate_outputs,
    write_steinmetz_choice_svg,
    write_steinmetz_condition_csv,
    write_steinmetz_report_html,
    write_steinmetz_summary_csv,
)
from behavtaskatlas.validation import validate_repository
from behavtaskatlas.visual_contrast_family import (
    DEFAULT_VISUAL_CONTRAST_FAMILY_DERIVED_DIR,
    analyze_visual_contrast_family,
    load_visual_contrast_family_perturbation_effects,
    load_visual_contrast_family_trials,
    write_visual_contrast_family_outputs,
)
from behavtaskatlas.zatka_haas import (
    DEFAULT_ZATKA_HAAS_CODE_ZIP,
    DEFAULT_ZATKA_HAAS_DERIVED_DIR,
    DEFAULT_ZATKA_HAAS_HIGHER_POWER_SESSION_ID,
    DEFAULT_ZATKA_HAAS_SESSION_ID,
    analyze_zatka_haas_visual_decision,
    build_zatka_haas_code_manifest,
    harmonize_zatka_haas_visual_trials,
    load_zatka_haas_processed_mat,
    write_zatka_haas_choice_svg,
    write_zatka_haas_code_manifest,
    write_zatka_haas_condition_csv,
    write_zatka_haas_laser_region_csv,
    write_zatka_haas_laser_state_csv,
    write_zatka_haas_perturbation_delta_csv,
    write_zatka_haas_perturbation_region_effect_csv,
    write_zatka_haas_report_html,
    write_zatka_haas_summary_csv,
    zatka_haas_provenance_payload,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="behavtaskatlas")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate repository records")
    validate_parser.add_argument("root", nargs="?", default=".", help="Repository root")

    schema_parser = subparsers.add_parser(
        "export-schemas", help="Export JSON schemas from the Python models"
    )
    schema_parser.add_argument("output_dir", nargs="?", default="schemas")

    ibl_parser = subparsers.add_parser(
        "ibl-harmonize", help="Harmonize one IBL visual decision session"
    )
    ibl_parser.add_argument("--eid", default=DEFAULT_IBL_EID, help="IBL session UUID/eid")
    ibl_parser.add_argument(
        "--protocol-id",
        default=IBL_VISUAL_PROTOCOL_ID,
        help="Protocol id to stamp into canonical trials",
    )
    ibl_parser.add_argument(
        "--out-dir",
        default="derived/ibl_visual_decision",
        help="Directory for generated artifacts",
    )
    ibl_parser.add_argument("--cache-dir", default=None, help="Optional ONE cache directory")
    ibl_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")
    ibl_parser.add_argument(
        "--revision",
        default=None,
        help="Optional IBL dataset revision to load, e.g. 2025-03-03",
    )

    analyze_parser = subparsers.add_parser(
        "ibl-analyze", help="Analyze a harmonized IBL visual decision session"
    )
    analyze_parser.add_argument("--eid", default=DEFAULT_IBL_EID, help="IBL session UUID/eid")
    analyze_parser.add_argument(
        "--protocol-id",
        default=None,
        help="Optional protocol id override for the analysis payload",
    )
    analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_DERIVED_DIR),
        help="Directory containing generated IBL artifacts",
    )
    analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    ibl_report_parser = subparsers.add_parser(
        "ibl-report",
        help="Render a static HTML report from an analyzed IBL visual decision session",
    )
    ibl_report_parser.add_argument("--eid", default=DEFAULT_IBL_EID, help="IBL session UUID/eid")
    ibl_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_DERIVED_DIR),
        help="Directory containing generated IBL artifacts",
    )
    ibl_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    ibl_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    ibl_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    ibl_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    ibl_brainwide_parser = subparsers.add_parser(
        "ibl-brainwide-harmonize",
        help="Harmonize one IBL Brainwide Map visual decision session",
    )
    ibl_brainwide_parser.add_argument(
        "--eid",
        default=DEFAULT_IBL_BRAINWIDE_MAP_EID,
        help="IBL Brainwide Map session UUID/eid",
    )
    ibl_brainwide_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_IBL_BRAINWIDE_MAP_DERIVED_DIR),
        help="Directory for generated Brainwide Map artifacts",
    )
    ibl_brainwide_parser.add_argument(
        "--cache-dir",
        default=None,
        help="Optional ONE cache directory",
    )
    ibl_brainwide_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional trial limit",
    )
    ibl_brainwide_parser.add_argument(
        "--revision",
        default=None,
        help="Optional IBL dataset revision to load",
    )

    ibl_brainwide_analyze_parser = subparsers.add_parser(
        "ibl-brainwide-analyze",
        help="Analyze a harmonized IBL Brainwide Map behavior session",
    )
    ibl_brainwide_analyze_parser.add_argument(
        "--eid",
        default=DEFAULT_IBL_BRAINWIDE_MAP_EID,
        help="IBL Brainwide Map session UUID/eid",
    )
    ibl_brainwide_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_IBL_BRAINWIDE_MAP_DERIVED_DIR),
        help="Directory containing generated Brainwide Map artifacts",
    )
    ibl_brainwide_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    ibl_brainwide_report_parser = subparsers.add_parser(
        "ibl-brainwide-report",
        help="Render a static HTML report from an IBL Brainwide Map behavior analysis",
    )
    ibl_brainwide_report_parser.add_argument(
        "--eid",
        default=DEFAULT_IBL_BRAINWIDE_MAP_EID,
        help="IBL Brainwide Map session UUID/eid",
    )
    ibl_brainwide_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_IBL_BRAINWIDE_MAP_DERIVED_DIR),
        help="Directory containing generated Brainwide Map artifacts",
    )
    ibl_brainwide_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    ibl_brainwide_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    ibl_brainwide_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    ibl_brainwide_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    mouse_unbiased_parser = subparsers.add_parser(
        "mouse-unbiased-harmonize",
        help="Harmonize one IBL trainingChoiceWorld visual contrast session",
    )
    mouse_unbiased_parser.add_argument(
        "--eid",
        default=DEFAULT_MOUSE_UNBIASED_EID,
        help="IBL trainingChoiceWorld session UUID/eid",
    )
    mouse_unbiased_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_MOUSE_UNBIASED_DERIVED_DIR),
        help="Directory for generated artifacts",
    )
    mouse_unbiased_parser.add_argument(
        "--cache-dir",
        default=None,
        help="Optional ONE cache directory",
    )
    mouse_unbiased_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional trial limit",
    )
    mouse_unbiased_parser.add_argument(
        "--revision",
        default=None,
        help="Optional IBL dataset revision to load",
    )

    mouse_unbiased_analyze_parser = subparsers.add_parser(
        "mouse-unbiased-analyze",
        help="Analyze a harmonized IBL trainingChoiceWorld visual contrast session",
    )
    mouse_unbiased_analyze_parser.add_argument(
        "--eid",
        default=DEFAULT_MOUSE_UNBIASED_EID,
        help="IBL trainingChoiceWorld session UUID/eid",
    )
    mouse_unbiased_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_MOUSE_UNBIASED_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    mouse_unbiased_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    mouse_unbiased_report_parser = subparsers.add_parser(
        "mouse-unbiased-report",
        help="Render a static HTML report from an IBL trainingChoiceWorld analysis",
    )
    mouse_unbiased_report_parser.add_argument(
        "--eid",
        default=DEFAULT_MOUSE_UNBIASED_EID,
        help="IBL trainingChoiceWorld session UUID/eid",
    )
    mouse_unbiased_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_MOUSE_UNBIASED_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    mouse_unbiased_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    mouse_unbiased_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    mouse_unbiased_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    mouse_unbiased_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    fritsche_download_parser = subparsers.add_parser(
        "fritsche-download",
        help="Download the Fritsche et al. temporal-regularities Figshare data ZIP",
    )
    fritsche_download_parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR),
        help="Directory for the downloaded Fritsche Figshare data ZIP",
    )

    fritsche_code_download_parser = subparsers.add_parser(
        "fritsche-code-download",
        help="Download the Fritsche et al. temporal-regularities Figshare code ZIP",
    )
    fritsche_code_download_parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR),
        help="Directory for the downloaded Fritsche Figshare code ZIP",
    )

    fritsche_code_manifest_parser = subparsers.add_parser(
        "fritsche-code-manifest",
        help="Build a source-code manifest from the Fritsche Figshare code ZIP",
    )
    fritsche_code_manifest_parser.add_argument(
        "--code-zip",
        default=str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_CODE_ZIP),
        help="Path to the downloaded Fritsche Figshare code.zip file",
    )
    fritsche_code_manifest_parser.add_argument(
        "--out-file",
        default=str(
            DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR
            / DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID
            / "code_manifest.json"
        ),
        help="Output path for the Fritsche code manifest JSON",
    )

    fritsche_parser = subparsers.add_parser(
        "fritsche-harmonize",
        help="Harmonize Fritsche et al. temporal-regularities visual wheel trials",
    )
    fritsche_parser.add_argument(
        "--zip-file",
        default=str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_ZIP),
        help="Path to Figshare data.zip",
    )
    fritsche_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR),
        help="Directory for generated Fritsche artifacts",
    )
    fritsche_parser.add_argument(
        "--session-id",
        default=DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID,
        help="Aggregate session directory name for generated artifacts",
    )
    fritsche_parser.add_argument(
        "--experiment",
        action="append",
        default=None,
        help=(
            "Experiment key to include; repeat for multiple. Defaults to exp1, "
            "exp2, and exp3 behavior CSVs."
        ),
    )
    fritsche_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    fritsche_analyze_parser = subparsers.add_parser(
        "fritsche-analyze",
        help="Analyze harmonized Fritsche temporal-regularities trials",
    )
    fritsche_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID,
        help="Generated session directory name",
    )
    fritsche_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR),
        help="Directory containing generated Fritsche artifacts",
    )
    fritsche_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    fritsche_report_parser = subparsers.add_parser(
        "fritsche-report",
        help="Render a static HTML report from a Fritsche temporal-regularities analysis",
    )
    fritsche_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID,
        help="Generated session directory name",
    )
    fritsche_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR),
        help="Directory containing generated Fritsche artifacts",
    )
    fritsche_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    fritsche_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    fritsche_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    fritsche_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    steinmetz_parser = subparsers.add_parser(
        "steinmetz-harmonize",
        help="Harmonize one extracted Steinmetz et al. visual decision ALF session",
    )
    steinmetz_parser.add_argument(
        "--session-dir",
        default=str(DEFAULT_STEINMETZ_RAW_DIR / DEFAULT_STEINMETZ_SESSION_ID),
        help="Directory containing extracted Steinmetz `trials.*.npy` files",
    )
    steinmetz_parser.add_argument(
        "--session-id",
        default=None,
        help="Harmonized session directory name; defaults to --session-dir basename",
    )
    steinmetz_parser.add_argument(
        "--subject-id",
        default=None,
        help="Optional subject id to stamp into canonical trials",
    )
    steinmetz_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_STEINMETZ_DERIVED_DIR),
        help="Directory for generated Steinmetz artifacts",
    )
    steinmetz_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    steinmetz_analyze_parser = subparsers.add_parser(
        "steinmetz-analyze",
        help="Analyze a harmonized Steinmetz visual decision session",
    )
    steinmetz_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_STEINMETZ_SESSION_ID,
        help="Harmonized session directory name",
    )
    steinmetz_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_STEINMETZ_DERIVED_DIR),
        help="Directory containing generated Steinmetz artifacts",
    )
    steinmetz_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    steinmetz_report_parser = subparsers.add_parser(
        "steinmetz-report",
        help="Render a static HTML report from a Steinmetz visual decision analysis",
    )
    steinmetz_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_STEINMETZ_SESSION_ID,
        help="Harmonized session directory name",
    )
    steinmetz_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_STEINMETZ_DERIVED_DIR),
        help="Directory containing generated Steinmetz artifacts",
    )
    steinmetz_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    steinmetz_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    steinmetz_report_parser.add_argument(
        "--choice-svg",
        default=None,
        help="Optional explicit path to choice_summary.svg",
    )
    steinmetz_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    steinmetz_aggregate_parser = subparsers.add_parser(
        "steinmetz-aggregate",
        help="Aggregate generated Steinmetz visual decision sessions",
    )
    steinmetz_aggregate_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_STEINMETZ_DERIVED_DIR),
        help="Directory containing generated Steinmetz session artifacts",
    )
    steinmetz_aggregate_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_STEINMETZ_DERIVED_DIR / "aggregate"),
        help="Directory for aggregate Steinmetz outputs",
    )
    steinmetz_aggregate_parser.add_argument(
        "--session-id",
        action="append",
        default=None,
        help="Optional session id to include; repeat for multiple sessions",
    )

    zatka_manifest_parser = subparsers.add_parser(
        "zatka-haas-code-manifest",
        help=(
            "Inspect the public Zatka-Haas Figshare code ZIP without downloading "
            "the full data archive"
        ),
    )
    zatka_manifest_parser.add_argument(
        "--code-zip",
        default=str(DEFAULT_ZATKA_HAAS_CODE_ZIP),
        help="Path to the downloaded Zatka-Haas code.zip file",
    )
    zatka_manifest_parser.add_argument(
        "--out-file",
        default=str(
            DEFAULT_ZATKA_HAAS_DERIVED_DIR
            / DEFAULT_ZATKA_HAAS_SESSION_ID
            / "code_manifest.json"
        ),
        help="Output path for the code manifest JSON",
    )

    zatka_harmonize_parser = subparsers.add_parser(
        "zatka-haas-harmonize",
        help="Harmonize a processed Zatka-Haas behavioral MATLAB D struct",
    )
    zatka_harmonize_parser.add_argument(
        "--mat-file",
        required=True,
        help="Path to a processed Zatka-Haas MAT file containing variable D",
    )
    zatka_harmonize_parser.add_argument(
        "--source-variable",
        default="D",
        help="MATLAB variable name containing the processed behavior struct/table",
    )
    zatka_harmonize_parser.add_argument(
        "--session-id",
        default=DEFAULT_ZATKA_HAAS_HIGHER_POWER_SESSION_ID,
        help="Fallback session id when the source does not carry sessionID",
    )
    zatka_harmonize_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_ZATKA_HAAS_DERIVED_DIR),
        help="Directory for generated Zatka-Haas artifacts",
    )
    zatka_harmonize_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional trial limit",
    )

    visual_contrast_family_parser = subparsers.add_parser(
        "visual-contrast-family-summary",
        help="Summarize available real-trial visual contrast slices as a family",
    )
    visual_contrast_family_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_VISUAL_CONTRAST_FAMILY_DERIVED_DIR),
        help="Directory for generated visual contrast family artifacts",
    )

    odoemene_parser = subparsers.add_parser(
        "odoemene-harmonize",
        help="Harmonize the Odoemene et al. visual evidence accumulation MATLAB file",
    )
    odoemene_parser.add_argument(
        "--mat-file",
        default=str(DEFAULT_ODOEMENE_RAW_MAT),
        help="Path to the local Odoemene CSHL `.mat` file",
    )
    odoemene_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_ODOEMENE_DERIVED_DIR),
        help="Directory for generated Odoemene artifacts",
    )
    odoemene_parser.add_argument(
        "--session-id",
        default=DEFAULT_ODOEMENE_SESSION_ID,
        help="Base session id for generated subject-session rows",
    )
    odoemene_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")
    odoemene_parser.add_argument(
        "--max-subjects",
        type=int,
        default=None,
        help="Optional maximum number of subjects to harmonize",
    )

    odoemene_analyze_parser = subparsers.add_parser(
        "odoemene-analyze",
        help="Analyze a harmonized Odoemene visual evidence accumulation dataset",
    )
    odoemene_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_ODOEMENE_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    odoemene_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_ODOEMENE_DERIVED_DIR),
        help="Directory containing generated Odoemene artifacts",
    )
    odoemene_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    odoemene_report_parser = subparsers.add_parser(
        "odoemene-report",
        help="Render a static HTML report from an Odoemene visual accumulation analysis",
    )
    odoemene_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_ODOEMENE_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    odoemene_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_ODOEMENE_DERIVED_DIR),
        help="Directory containing generated Odoemene artifacts",
    )
    odoemene_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    odoemene_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    odoemene_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    odoemene_report_parser.add_argument(
        "--kernel-svg",
        default=None,
        help="Optional explicit path to event_kernel.svg",
    )
    odoemene_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    coen_parser = subparsers.add_parser(
        "coen-harmonize",
        help="Harmonize Coen et al. audiovisual spatial decision trials",
    )
    coen_parser.add_argument(
        "--source-file",
        default=str(DEFAULT_COEN_RAW_FILE),
        help="Path to a local Coen CSV/TSV trial export or MATLAB block file",
    )
    coen_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_COEN_DERIVED_DIR),
        help="Directory for generated Coen artifacts",
    )
    coen_parser.add_argument(
        "--session-id",
        default=DEFAULT_COEN_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    coen_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    coen_analyze_parser = subparsers.add_parser(
        "coen-analyze",
        help="Analyze a harmonized Coen audiovisual spatial decision dataset",
    )
    coen_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_COEN_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    coen_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_COEN_DERIVED_DIR),
        help="Directory containing generated Coen artifacts",
    )
    coen_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    coen_report_parser = subparsers.add_parser(
        "coen-report",
        help="Render a static HTML report from a Coen audiovisual decision analysis",
    )
    coen_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_COEN_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    coen_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_COEN_DERIVED_DIR),
        help="Directory containing generated Coen artifacts",
    )
    coen_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    coen_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    coen_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    coen_report_parser.add_argument(
        "--condition-svg",
        default=None,
        help="Optional explicit path to condition_summary.svg",
    )
    coen_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    rodgers_parser = subparsers.add_parser(
        "rodgers-harmonize",
        help="Harmonize Rodgers DANDI whisker object-recognition trials",
    )
    rodgers_parser.add_argument(
        "--source-file",
        default=str(DEFAULT_RODGERS_RAW_FILE),
        help="Path to a local Rodgers NWB file or exported CSV/TSV trials table",
    )
    rodgers_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_RODGERS_DERIVED_DIR),
        help="Directory for generated Rodgers artifacts",
    )
    rodgers_parser.add_argument(
        "--session-id",
        default=DEFAULT_RODGERS_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    rodgers_parser.add_argument(
        "--subject-id",
        default=None,
        help="Optional subject id for CSV exports without NWB subject metadata",
    )
    rodgers_parser.add_argument(
        "--task-rule",
        choices=["shape_detection", "shape_discrimination", "unknown"],
        default=None,
        help="Optional task rule override; inferred from rows by default",
    )
    rodgers_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    rodgers_analyze_parser = subparsers.add_parser(
        "rodgers-analyze",
        help="Analyze a harmonized Rodgers whisker object-recognition dataset",
    )
    rodgers_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_RODGERS_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    rodgers_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_RODGERS_DERIVED_DIR),
        help="Directory containing generated Rodgers artifacts",
    )
    rodgers_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    rodgers_report_parser = subparsers.add_parser(
        "rodgers-report",
        help="Render a static HTML report from a Rodgers whisker object analysis",
    )
    rodgers_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_RODGERS_SESSION_ID,
        help="Harmonized artifact directory name",
    )
    rodgers_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_RODGERS_DERIVED_DIR),
        help="Directory containing generated Rodgers artifacts",
    )
    rodgers_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    rodgers_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    rodgers_report_parser.add_argument(
        "--accuracy-svg",
        default=None,
        help="Optional explicit path to accuracy.svg",
    )
    rodgers_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    human_visual_download_parser = subparsers.add_parser(
        "human-visual-download",
        help="Download Walsh et al. OSF human visual contrast source files",
    )
    human_visual_download_parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_DIR),
        help="Directory for downloaded OSF source files",
    )

    human_visual_parser = subparsers.add_parser(
        "human-visual-harmonize",
        help="Harmonize Walsh et al. OSF human visual contrast trials",
    )
    human_visual_parser.add_argument(
        "--mat-file",
        default=str(DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_MAT),
        help="Path to the downloaded `1. Behavioural Analysis.mat` file",
    )
    human_visual_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_HUMAN_VISUAL_CONTRAST_DERIVED_DIR),
        help="Directory for generated artifacts",
    )
    human_visual_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_VISUAL_CONTRAST_SESSION_ID,
        help="Harmonized session directory name",
    )
    human_visual_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    human_visual_analyze_parser = subparsers.add_parser(
        "human-visual-analyze",
        help="Analyze a harmonized Walsh et al. human visual contrast dataset",
    )
    human_visual_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_VISUAL_CONTRAST_SESSION_ID,
        help="Harmonized session directory name",
    )
    human_visual_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_HUMAN_VISUAL_CONTRAST_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    human_visual_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    human_visual_report_parser = subparsers.add_parser(
        "human-visual-report",
        help="Render a static HTML report from the human visual contrast analysis",
    )
    human_visual_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_VISUAL_CONTRAST_SESSION_ID,
        help="Harmonized session directory name",
    )
    human_visual_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_HUMAN_VISUAL_CONTRAST_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    human_visual_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    human_visual_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    human_visual_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    human_visual_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    clicks_parser = subparsers.add_parser(
        "clicks-harmonize",
        help="Harmonize one local Brody Lab Poisson Clicks `.mat` file",
    )
    clicks_parser.add_argument("--mat-file", required=True, help="Path to a local `.mat` file")
    clicks_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory for generated artifacts",
    )
    clicks_parser.add_argument(
        "--parsed-field",
        default="parsed",
        choices=["parsed", "parsed_frozen"],
        help="ratdata field to harmonize",
    )
    clicks_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    clicks_analyze_parser = subparsers.add_parser(
        "clicks-analyze",
        help="Analyze a harmonized Brody Lab Poisson Clicks session",
    )
    clicks_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_CLICKS_SESSION_ID,
        help="Harmonized session directory name",
    )
    clicks_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory containing generated auditory-clicks artifacts",
    )
    clicks_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )
    clicks_analyze_parser.add_argument(
        "--kernel-bins",
        type=int,
        default=10,
        help="Number of normalized time bins for the evidence-kernel analysis",
    )

    clicks_batch_parser = subparsers.add_parser(
        "clicks-batch",
        help="Harmonize and analyze multiple local Brody Lab Poisson Clicks `.mat` files",
    )
    clicks_batch_sources = clicks_batch_parser.add_mutually_exclusive_group(required=True)
    clicks_batch_sources.add_argument(
        "--mat-dir",
        default=None,
        help="Directory containing extracted `.mat` files",
    )
    clicks_batch_sources.add_argument(
        "--mat-file",
        action="append",
        default=None,
        dest="mat_files",
        help="Path to a local `.mat` file; may be passed more than once",
    )
    clicks_batch_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory for generated artifacts and batch_summary.csv",
    )
    clicks_batch_parser.add_argument(
        "--parsed-field",
        default="parsed",
        choices=["parsed", "parsed_frozen"],
        help="ratdata field to harmonize",
    )
    clicks_batch_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")
    clicks_batch_parser.add_argument(
        "--kernel-bins",
        type=int,
        default=10,
        help="Number of normalized time bins for the evidence-kernel analysis",
    )
    clicks_batch_parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional maximum number of `.mat` files after filename sorting",
    )
    clicks_batch_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first file that fails",
    )

    clicks_aggregate_parser = subparsers.add_parser(
        "clicks-aggregate",
        help="Aggregate existing Brody Lab clicks batch outputs",
    )
    clicks_aggregate_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory containing generated auditory-clicks batch artifacts",
    )
    clicks_aggregate_parser.add_argument(
        "--batch-summary",
        default=None,
        help="Optional explicit path to a clicks batch_summary.csv",
    )

    clicks_aggregate_trials_parser = subparsers.add_parser(
        "clicks-aggregate-trials",
        help=(
            "Concatenate per-rat canonical trials into a slice-level "
            "trials.csv for downstream cross-rat extraction"
        ),
    )
    clicks_aggregate_trials_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory containing generated auditory-clicks batch artifacts",
    )
    clicks_aggregate_trials_parser.add_argument(
        "--batch-summary",
        default=None,
        help="Optional explicit path to a clicks batch_summary.csv",
    )
    clicks_aggregate_trials_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional explicit output path (default: <derived-dir>/trials.csv)",
    )

    clicks_report_parser = subparsers.add_parser(
        "clicks-report",
        help="Render a static HTML report from existing clicks aggregate outputs",
    )
    clicks_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_CLICKS_DERIVED_DIR),
        help="Directory containing generated auditory-clicks aggregate artifacts",
    )
    clicks_report_parser.add_argument(
        "--aggregate-result",
        default=None,
        help="Optional explicit path to aggregate_result.json",
    )
    clicks_report_parser.add_argument(
        "--aggregate-kernel-svg",
        default=None,
        help="Optional explicit path to aggregate_kernel.svg",
    )
    clicks_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    human_clicks_download_parser = subparsers.add_parser(
        "human-clicks-download",
        help="Download the Mendeley human Poisson clicks DBS MATLAB file",
    )
    human_clicks_download_parser.add_argument(
        "--out-file",
        default=str(DEFAULT_HUMAN_CLICKS_RAW_MAT),
        help="Local output path under ignored raw-data storage",
    )

    human_clicks_parser = subparsers.add_parser(
        "human-clicks-harmonize",
        help="Harmonize the Mendeley human Poisson clicks DBS MATLAB file",
    )
    human_clicks_parser.add_argument(
        "--mat-file",
        default=str(DEFAULT_HUMAN_CLICKS_RAW_MAT),
        help="Path to the local Mendeley `.mat` file",
    )
    human_clicks_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_HUMAN_CLICKS_DERIVED_DIR),
        help="Directory for generated human auditory-clicks artifacts",
    )
    human_clicks_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_CLICKS_SESSION_ID,
        help="Base session id for generated patient-session rows",
    )
    human_clicks_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    human_clicks_analyze_parser = subparsers.add_parser(
        "human-clicks-analyze",
        help="Analyze harmonized Mendeley human Poisson clicks artifacts",
    )
    human_clicks_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_CLICKS_SESSION_ID,
        help="Session directory name for the processed dataset",
    )
    human_clicks_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_HUMAN_CLICKS_DERIVED_DIR),
        help="Directory containing generated human auditory-clicks artifacts",
    )
    human_clicks_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )
    human_clicks_analyze_parser.add_argument(
        "--kernel-bins",
        type=int,
        default=10,
        help="Number of normalized time bins for the evidence-kernel analysis",
    )

    human_clicks_report_parser = subparsers.add_parser(
        "human-clicks-report",
        help="Render a static HTML report from analyzed human auditory-clicks artifacts",
    )
    human_clicks_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_CLICKS_SESSION_ID,
        help="Analyzed session directory name",
    )
    human_clicks_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_HUMAN_CLICKS_DERIVED_DIR),
        help="Directory containing generated human auditory-clicks artifacts",
    )
    human_clicks_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    human_clicks_report_parser.add_argument(
        "--kernel-result",
        default=None,
        help="Optional explicit path to evidence_kernel_result.json",
    )
    human_clicks_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    human_clicks_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    human_clicks_report_parser.add_argument(
        "--evidence-kernel-svg",
        default=None,
        help="Optional explicit path to evidence_kernel.svg",
    )
    human_clicks_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    rdm_download_parser = subparsers.add_parser(
        "rdm-download",
        help="Download the processed Roitman-Shadlen random-dot motion CSV",
    )
    rdm_download_parser.add_argument(
        "--out-file",
        default=str(DEFAULT_RDM_RAW_CSV),
        help="Local output path under ignored raw-data storage",
    )

    rdm_parser = subparsers.add_parser(
        "rdm-harmonize",
        help="Harmonize the processed Roitman-Shadlen random-dot motion CSV",
    )
    rdm_parser.add_argument(
        "--csv-file",
        default=str(DEFAULT_RDM_RAW_CSV),
        help="Path to the processed Roitman-Shadlen CSV",
    )
    rdm_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_RDM_DERIVED_DIR),
        help="Directory for generated random-dot motion artifacts",
    )
    rdm_parser.add_argument(
        "--session-id",
        default=DEFAULT_RDM_SESSION_ID,
        help="Session directory name for the processed dataset",
    )
    rdm_parser.add_argument("--monkey", type=int, default=None, help="Optional monkey id")
    rdm_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    rdm_analyze_parser = subparsers.add_parser(
        "rdm-analyze",
        help="Analyze a harmonized Roitman-Shadlen random-dot motion dataset",
    )
    rdm_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_RDM_SESSION_ID,
        help="Harmonized session directory name",
    )
    rdm_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_RDM_DERIVED_DIR),
        help="Directory containing generated random-dot motion artifacts",
    )
    rdm_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    rdm_report_parser = subparsers.add_parser(
        "rdm-report",
        help="Render a static HTML report from analyzed random-dot motion artifacts",
    )
    rdm_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_RDM_SESSION_ID,
        help="Analyzed session directory name",
    )
    rdm_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_RDM_DERIVED_DIR),
        help="Directory containing generated random-dot motion artifacts",
    )
    rdm_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    rdm_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    rdm_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    rdm_report_parser.add_argument(
        "--chronometric-svg",
        default=None,
        help="Optional explicit path to chronometric.svg",
    )
    rdm_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    human_rdm_download_parser = subparsers.add_parser(
        "human-rdm-download",
        help="Download Palmer-Huk-Shadlen human RDM MATLAB files from CoSMo2017",
    )
    human_rdm_download_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_HUMAN_RDM_RAW_DIR),
        help="Local output directory under ignored raw-data storage",
    )
    human_rdm_download_parser.add_argument(
        "--subject",
        action="append",
        choices=HUMAN_RDM_SUBJECT_IDS,
        default=None,
        help="Optional PHS subject id to download; may be passed more than once",
    )

    human_rdm_parser = subparsers.add_parser(
        "human-rdm-harmonize",
        help="Harmonize Palmer-Huk-Shadlen human RDM MATLAB files",
    )
    human_rdm_parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_HUMAN_RDM_RAW_DIR),
        help="Directory containing downloaded PHS MATLAB files",
    )
    human_rdm_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_HUMAN_RDM_DERIVED_DIR),
        help="Directory for generated human RDM artifacts",
    )
    human_rdm_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_RDM_SESSION_ID,
        help="Session directory name for the processed dataset",
    )
    human_rdm_parser.add_argument(
        "--subject",
        action="append",
        choices=HUMAN_RDM_SUBJECT_IDS,
        default=None,
        help="Optional PHS subject id to harmonize; may be passed more than once",
    )
    human_rdm_parser.add_argument("--limit", type=int, default=None, help="Optional trial limit")

    human_rdm_analyze_parser = subparsers.add_parser(
        "human-rdm-analyze",
        help="Analyze harmonized Palmer-Huk-Shadlen human RDM artifacts",
    )
    human_rdm_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_RDM_SESSION_ID,
        help="Harmonized session directory name",
    )
    human_rdm_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_HUMAN_RDM_DERIVED_DIR),
        help="Directory containing generated human RDM artifacts",
    )
    human_rdm_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    human_rdm_report_parser = subparsers.add_parser(
        "human-rdm-report",
        help="Render a static HTML report from analyzed human RDM artifacts",
    )
    human_rdm_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_HUMAN_RDM_SESSION_ID,
        help="Analyzed session directory name",
    )
    human_rdm_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_HUMAN_RDM_DERIVED_DIR),
        help="Directory containing generated human RDM artifacts",
    )
    human_rdm_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    human_rdm_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    human_rdm_report_parser.add_argument(
        "--psychometric-svg",
        default=None,
        help="Optional explicit path to psychometric.svg",
    )
    human_rdm_report_parser.add_argument(
        "--chronometric-svg",
        default=None,
        help="Optional explicit path to chronometric.svg",
    )
    human_rdm_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    macaque_confidence_download_parser = subparsers.add_parser(
        "macaque-rdm-confidence-download",
        help="Download Khalvati-Kiani-Rao macaque RDM confidence source-data ZIP",
    )
    macaque_confidence_download_parser.add_argument(
        "--out-file",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_ZIP),
        help="Local output path under ignored raw-data storage",
    )

    macaque_confidence_intake_parser = subparsers.add_parser(
        "macaque-rdm-confidence-intake-check",
        help="Preflight requested Khalvati raw behavioral MATLAB files",
    )
    macaque_confidence_intake_parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_BEHAVIOR_DIR),
        help="Directory containing beh_data.monkey1.mat and beh_data.monkey2.mat",
    )
    macaque_confidence_intake_parser.add_argument(
        "--redistribution-status",
        default=None,
        help=(
            "Optional YAML file recording raw/derived redistribution terms "
            "(default: <raw-dir>/redistribution_status.yaml)"
        ),
    )
    macaque_confidence_intake_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional JSON report output path",
    )

    macaque_confidence_parser = subparsers.add_parser(
        "macaque-rdm-confidence-harmonize",
        help="Harmonize macaque RDM confidence source-data rows",
    )
    macaque_confidence_parser.add_argument(
        "--source-zip",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_ZIP),
        help="Path to the downloaded Nature Communications source-data ZIP",
    )
    macaque_confidence_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_DERIVED_DIR),
        help="Directory for generated macaque confidence artifacts",
    )
    macaque_confidence_parser.add_argument(
        "--session-id",
        default=DEFAULT_MACAQUE_RDM_CONFIDENCE_SESSION_ID,
        help="Session directory name for the processed source-data rows",
    )
    macaque_confidence_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional source-row limit",
    )

    macaque_confidence_raw_parser = subparsers.add_parser(
        "macaque-rdm-confidence-raw-harmonize",
        help="Placeholder harmonizer for requested Khalvati raw behavioral MATLAB files",
    )
    macaque_confidence_raw_parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_BEHAVIOR_DIR),
        help="Directory containing beh_data.monkey1.mat and beh_data.monkey2.mat",
    )
    macaque_confidence_raw_parser.add_argument(
        "--redistribution-status",
        default=None,
        help=(
            "Optional YAML file recording raw/derived redistribution terms "
            "(default: <raw-dir>/redistribution_status.yaml)"
        ),
    )
    macaque_confidence_raw_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_DERIVED_DIR),
        help="Directory for future raw-trial macaque confidence artifacts",
    )
    macaque_confidence_raw_parser.add_argument(
        "--session-id",
        default="khalvati-kiani-rao-raw-behavior",
        help="Session directory name for future raw-trial outputs",
    )
    macaque_confidence_raw_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional raw-trial limit for future importer implementation",
    )

    macaque_confidence_analyze_parser = subparsers.add_parser(
        "macaque-rdm-confidence-analyze",
        help="Analyze harmonized macaque RDM confidence source-data artifacts",
    )
    macaque_confidence_analyze_parser.add_argument(
        "--session-id",
        default=DEFAULT_MACAQUE_RDM_CONFIDENCE_SESSION_ID,
        help="Harmonized session directory name",
    )
    macaque_confidence_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_DERIVED_DIR),
        help="Directory containing generated macaque confidence artifacts",
    )
    macaque_confidence_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    macaque_confidence_report_parser = subparsers.add_parser(
        "macaque-rdm-confidence-report",
        help="Render a static HTML report from macaque RDM confidence artifacts",
    )
    macaque_confidence_report_parser.add_argument(
        "--session-id",
        default=DEFAULT_MACAQUE_RDM_CONFIDENCE_SESSION_ID,
        help="Analyzed session directory name",
    )
    macaque_confidence_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_MACAQUE_RDM_CONFIDENCE_DERIVED_DIR),
        help="Directory containing generated macaque confidence artifacts",
    )
    macaque_confidence_report_parser.add_argument(
        "--analysis-result",
        default=None,
        help="Optional explicit path to analysis_result.json",
    )
    macaque_confidence_report_parser.add_argument(
        "--provenance",
        default=None,
        help="Optional explicit path to provenance.json",
    )
    macaque_confidence_report_parser.add_argument(
        "--accuracy-svg",
        default=None,
        help="Optional explicit path to accuracy.svg",
    )
    macaque_confidence_report_parser.add_argument(
        "--confidence-svg",
        default=None,
        help="Optional explicit path to confidence.svg",
    )
    macaque_confidence_report_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional report HTML output path",
    )

    allen_download_parser = subparsers.add_parser(
        "allen-visual-behavior-download",
        help="Download one Allen Visual Behavior NWB file from a public URL",
    )
    allen_download_parser.add_argument(
        "--nwb-url",
        required=True,
        help="Public HTTPS URL pointing at a Visual Behavior behavior session NWB file",
    )
    allen_download_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional output NWB path; defaults to data/raw/allen_visual_behavior/<basename>",
    )

    allen_harmonize_parser = subparsers.add_parser(
        "allen-visual-behavior-harmonize",
        help="Harmonize one Allen Visual Behavior NWB file",
    )
    allen_harmonize_parser.add_argument(
        "--nwb-file",
        required=True,
        help="Path to a downloaded Visual Behavior behavior session NWB file",
    )
    allen_harmonize_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_ALLEN_VISUAL_BEHAVIOR_DERIVED_DIR),
        help="Directory for generated artifacts",
    )
    allen_harmonize_parser.add_argument(
        "--limit", type=int, default=None, help="Optional trial limit"
    )

    allen_analyze_parser = subparsers.add_parser(
        "allen-visual-behavior-analyze",
        help="Analyze a harmonized Allen Visual Behavior session",
    )
    allen_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_ALLEN_VISUAL_BEHAVIOR_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    allen_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    allen_report_parser = subparsers.add_parser(
        "allen-visual-behavior-report",
        help="Render a static HTML report for the Allen Visual Behavior slice",
    )
    allen_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_ALLEN_VISUAL_BEHAVIOR_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    allen_report_parser.add_argument(
        "--analysis-result", default=None, help="Optional explicit path to analysis_result.json"
    )
    allen_report_parser.add_argument(
        "--provenance", default=None, help="Optional explicit path to provenance.json"
    )
    allen_report_parser.add_argument(
        "--lick-latency-svg", default=None, help="Optional explicit path to lick_latency.svg"
    )
    allen_report_parser.add_argument(
        "--out-file", default=None, help="Optional report HTML output path"
    )

    allen_vbn_download_parser = subparsers.add_parser(
        "allen-vbn-download",
        help="Download one Allen Visual Behavior Neuropixels NWB file from a public URL",
    )
    allen_vbn_download_parser.add_argument(
        "--nwb-url",
        required=True,
        help="Public HTTPS URL pointing at a Visual Behavior Neuropixels NWB file",
    )
    allen_vbn_download_parser.add_argument(
        "--out-file",
        default=None,
        help=(
            "Optional output NWB path; defaults to "
            "data/raw/allen_visual_behavior_neuropixels/<basename>"
        ),
    )

    allen_vbn_harmonize_parser = subparsers.add_parser(
        "allen-vbn-harmonize",
        help="Harmonize one Allen Visual Behavior Neuropixels NWB trials table",
    )
    allen_vbn_harmonize_parser.add_argument(
        "--nwb-file",
        required=True,
        help="Path to a downloaded Visual Behavior Neuropixels NWB file",
    )
    allen_vbn_harmonize_parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_ALLEN_VBN_DERIVED_DIR),
        help="Directory for generated artifacts",
    )
    allen_vbn_harmonize_parser.add_argument(
        "--limit", type=int, default=None, help="Optional trial limit"
    )

    allen_vbn_analyze_parser = subparsers.add_parser(
        "allen-vbn-analyze",
        help="Analyze a harmonized Allen Visual Behavior Neuropixels session",
    )
    allen_vbn_analyze_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_ALLEN_VBN_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    allen_vbn_analyze_parser.add_argument(
        "--trials-csv",
        default=None,
        help="Optional explicit canonical trial CSV path",
    )

    allen_vbn_report_parser = subparsers.add_parser(
        "allen-vbn-report",
        help="Render a static HTML report for the Allen Visual Behavior Neuropixels slice",
    )
    allen_vbn_report_parser.add_argument(
        "--derived-dir",
        default=str(DEFAULT_ALLEN_VBN_DERIVED_DIR),
        help="Directory containing generated artifacts",
    )
    allen_vbn_report_parser.add_argument(
        "--analysis-result", default=None, help="Optional explicit path to analysis_result.json"
    )
    allen_vbn_report_parser.add_argument(
        "--provenance", default=None, help="Optional explicit path to provenance.json"
    )
    allen_vbn_report_parser.add_argument(
        "--lick-latency-svg", default=None, help="Optional explicit path to lick_latency.svg"
    )
    allen_vbn_report_parser.add_argument(
        "--out-file", default=None, help="Optional report HTML output path"
    )

    extract_finding_parser = subparsers.add_parser(
        "extract-finding",
        help="Extract a Finding YAML from a slice's per-curve summary CSV",
    )
    extract_finding_parser.add_argument(
        "--slice",
        dest="slice_id",
        required=True,
        help="Vertical slice id (e.g. slice.random-dot-motion)",
    )
    extract_finding_parser.add_argument(
        "--paper-id",
        required=True,
        help="Paper id to attribute the extracted finding to",
    )
    extract_finding_parser.add_argument(
        "--finding-id-prefix",
        required=True,
        help="Finding id prefix; per-condition findings append a slug",
    )
    extract_finding_parser.add_argument(
        "--curve-type",
        default="psychometric",
        choices=["psychometric", "chronometric", "accuracy_by_strength"],
        help="Which summary CSV to read and what curve to produce",
    )
    extract_finding_parser.add_argument(
        "--by-subject",
        action="store_true",
        help=(
            "For psychometric or chronometric curves: read trials.csv and emit "
            "one finding per subject_id rather than the pooled summary."
        ),
    )
    extract_finding_parser.add_argument(
        "--by-subject-condition",
        default=None,
        help=(
            "For psychometric or chronometric curves: read trials.csv and emit "
            "one finding per (subject_id × <column>) cell. Pass the trials "
            "column to stratify on, typically `prior_context`. Implies "
            "--by-subject."
        ),
    )
    extract_finding_parser.add_argument(
        "--condition-value",
        action="append",
        default=None,
        help=(
            "Optional value filter for --by-subject-condition. May be passed "
            "multiple times."
        ),
    )
    extract_finding_parser.add_argument(
        "--x-label",
        default=None,
        help="X-axis label written into the curve (curve-type default if omitted)",
    )
    extract_finding_parser.add_argument(
        "--x-units",
        default=None,
        help="X-axis units written into the curve",
    )
    extract_finding_parser.add_argument(
        "--summary-filename",
        default=None,
        help=(
            "For pooled psychometric extraction, summary CSV filename under "
            "the slice derived directory."
        ),
    )
    extract_finding_parser.add_argument(
        "--condition-column",
        default=None,
        help=(
            "For pooled psychometric extraction, column used to split "
            "condition-specific findings."
        ),
    )
    extract_finding_parser.add_argument(
        "--y-column",
        default=None,
        help="For pooled psychometric extraction, response fraction column.",
    )
    extract_finding_parser.add_argument(
        "--y-label",
        default=None,
        help="For pooled psychometric extraction, y-axis label.",
    )
    extract_finding_parser.add_argument(
        "--n-column",
        default=None,
        help=(
            "For pooled psychometric extraction, denominator column. If omitted, "
            "n_response then n_trials are used."
        ),
    )
    extract_finding_parser.add_argument(
        "--derived-dir",
        default="derived",
        help="Derived artifact root containing the slice's summary CSV",
    )

    import_supplement_parser = subparsers.add_parser(
        "import-supplement",
        help=(
            "Import findings from an external CSV using a YAML mapping spec. "
            "Used for supplement-csv, figure-trace, and table-transcription "
            "extraction methods."
        ),
    )
    import_supplement_parser.add_argument(
        "--csv",
        dest="csv_path",
        required=True,
        help="Path to the supplement / figure-trace CSV",
    )
    import_supplement_parser.add_argument(
        "--mapping",
        required=True,
        help="Path to the YAML mapping spec (paper_id, columns, groupby, etc.)",
    )

    site_index_parser = subparsers.add_parser(
        "site-index",
        help="Export static JSON manifests consumed by the Astro web app",
    )
    site_index_parser.add_argument(
        "--derived-dir",
        default="derived",
        help="Derived artifact root containing generated slice reports",
    )
    site_index_parser.add_argument(
        "--manifest-file",
        default=None,
        help="Optional manifest JSON output path",
    )
    site_index_parser.add_argument(
        "--catalog-json-file",
        default=None,
        help="Optional catalog JSON output path",
    )
    site_index_parser.add_argument(
        "--graph-json-file",
        default=None,
        help="Optional relationship graph JSON output path",
    )
    site_index_parser.add_argument(
        "--curation-queue-json-file",
        default=None,
        help="Optional curation queue JSON output path",
    )

    data_request_export_parser = subparsers.add_parser(
        "data-request-export",
        help="Render ready-to-send Markdown packets for tracked external data requests",
    )
    data_request_export_parser.add_argument(
        "request_id",
        nargs="?",
        default=None,
        help=(
            "Optional request id or slug to export. If omitted, all data "
            "requests are exported."
        ),
    )
    data_request_export_parser.add_argument(
        "--root",
        default=".",
        help="Repository root containing data_request records",
    )
    data_request_export_parser.add_argument(
        "--out-dir",
        default="derived/data_requests",
        help="Output directory for Markdown request packets",
    )
    data_request_export_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print a single request packet instead of writing files",
    )

    data_request_queue_parser = subparsers.add_parser(
        "data-request-queue",
        help="Print the operational queue for tracked external data requests",
    )
    data_request_queue_parser.add_argument(
        "--root",
        default=".",
        help="Repository root containing data_request records",
    )
    data_request_queue_parser.add_argument(
        "--today",
        default=None,
        help="Queue date in YYYY-MM-DD form; defaults to today",
    )
    data_request_queue_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the queue payload as JSON",
    )
    data_request_queue_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional JSON queue output path",
    )

    data_request_event_parser = subparsers.add_parser(
        "data-request-event",
        help="Append a workflow event to a tracked external data request",
    )
    data_request_event_parser.add_argument(
        "request_id",
        help="Data request id or slug",
    )
    data_request_event_parser.add_argument(
        "--event-type",
        required=True,
        choices=[
            "drafted",
            "sent",
            "follow_up_due",
            "followed_up",
            "received",
            "declined",
            "license_confirmed",
            "closed",
            "note",
        ],
        help="Workflow event type to append",
    )
    data_request_event_parser.add_argument(
        "--event-date",
        default=None,
        help="Event date in YYYY-MM-DD form; defaults to today",
    )
    data_request_event_parser.add_argument(
        "--actor",
        required=True,
        help="Person or process recording the event",
    )
    data_request_event_parser.add_argument(
        "--notes",
        required=True,
        help="Short evidence-backed event note",
    )
    data_request_event_parser.add_argument(
        "--status",
        choices=[
            "draft",
            "ready_to_send",
            "requested",
            "fulfilled",
            "declined",
            "blocked",
            "closed",
        ],
        default=None,
        help="Optional data_request status to set after appending the event",
    )
    data_request_event_parser.add_argument(
        "--evidence-url",
        default=None,
        help="Optional URL proving the event occurred",
    )
    data_request_event_parser.add_argument(
        "--evidence-path",
        default=None,
        help="Optional local evidence path to record on the event",
    )
    data_request_event_parser.add_argument(
        "--next-follow-up-date",
        default=None,
        help="Optional follow-up date in YYYY-MM-DD form",
    )
    data_request_event_parser.add_argument(
        "--create-evidence-stub",
        action="store_true",
        help="Create a local Markdown evidence stub from the request draft",
    )
    data_request_event_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing evidence stub",
    )
    data_request_event_parser.add_argument(
        "--root",
        default=".",
        help="Repository root containing data_request records",
    )

    audit_findings_parser = subparsers.add_parser(
        "audit-findings",
        help=(
            "Reproducibility audit: confirm pooled findings reconcile with "
            "n-weighted aggregates of their per-subject findings"
        ),
    )
    audit_findings_parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Maximum tolerated |pooled_y - aggregated_y| at any matching x",
    )
    audit_findings_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional JSON output path for the audit report",
    )

    fit_model_parser = subparsers.add_parser(
        "fit-model",
        help="Fit a registered ModelVariant to one Finding and emit a ModelFit YAML",
    )
    fit_model_parser.add_argument(
        "--variant",
        dest="variant_id",
        required=True,
        help="ModelVariant id (e.g. model_variant.logistic-4param)",
    )
    fit_model_parser.add_argument(
        "--finding",
        dest="finding_id",
        required=True,
        help="Finding id to fit",
    )
    fit_model_parser.add_argument(
        "--out-dir",
        default="model_fits",
        help="Output directory for the ModelFit YAML (default: model_fits)",
    )

    fit_stale_parser = subparsers.add_parser(
        "fit-stale-models",
        help=(
            "Fit every (registered variant × eligible finding) pair that "
            "doesn't already have a committed ModelFit"
        ),
    )
    fit_stale_parser.add_argument(
        "--variant",
        dest="variant_filter",
        default=None,
        help="Restrict to a single variant id",
    )
    fit_stale_parser.add_argument(
        "--out-dir",
        default="model_fits",
        help="Output directory for emitted ModelFit YAMLs",
    )
    fit_stale_parser.add_argument(
        "--curve-types",
        default="psychometric",
        help=(
            "Comma-separated curve types to fit (default: psychometric). "
            "Variants are still gated by their declared requires."
        ),
    )

    audit_models_parser = subparsers.add_parser(
        "audit-models",
        help=(
            "Model audit: forward-evaluate each ModelFit and report drift "
            "against its referenced findings"
        ),
    )
    audit_models_parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Maximum tolerated |predicted_y - observed_y| at any matching x",
    )
    audit_models_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional JSON output path for the model audit report",
    )

    release_check_parser = subparsers.add_parser(
        "release-check",
        help="Run static release-readiness checks and render status artifacts",
    )
    release_check_parser.add_argument(
        "--root",
        default=".",
        help="Repository root containing committed atlas records",
    )
    release_check_parser.add_argument(
        "--derived-dir",
        default="derived",
        help="Derived artifact root containing generated static site files",
    )
    release_check_parser.add_argument(
        "--out-file",
        default=None,
        help="Optional machine-readable release status JSON output path",
    )
    release_check_parser.add_argument(
        "--html-file",
        default=None,
        help="Optional release status HTML output path",
    )

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(Path(args.root))
    if args.command == "export-schemas":
        return _export_schemas(Path(args.output_dir))
    if args.command == "ibl-harmonize":
        return _ibl_harmonize(
            eid=args.eid,
            out_dir=Path(args.out_dir),
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            limit=args.limit,
            revision=args.revision,
            protocol_id=args.protocol_id,
        )
    if args.command == "ibl-analyze":
        return _ibl_analyze(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
            protocol_id=args.protocol_id,
        )
    if args.command == "ibl-report":
        return _ibl_report(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "ibl-brainwide-harmonize":
        return _ibl_brainwide_harmonize(
            eid=args.eid,
            out_dir=Path(args.out_dir),
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            limit=args.limit,
            revision=args.revision,
        )
    if args.command == "ibl-brainwide-analyze":
        return _ibl_brainwide_analyze(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "ibl-brainwide-report":
        return _ibl_report(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "mouse-unbiased-harmonize":
        return _ibl_harmonize(
            eid=args.eid,
            out_dir=Path(args.out_dir),
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            limit=args.limit,
            revision=args.revision,
            protocol_id=MOUSE_UNBIASED_VISUAL_PROTOCOL_ID,
        )
    if args.command == "mouse-unbiased-analyze":
        return _ibl_analyze(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
            protocol_id=MOUSE_UNBIASED_VISUAL_PROTOCOL_ID,
        )
    if args.command == "mouse-unbiased-report":
        return _ibl_report(
            eid=args.eid,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "fritsche-download":
        return _fritsche_download(raw_dir=Path(args.raw_dir))
    if args.command == "fritsche-code-download":
        return _fritsche_code_download(raw_dir=Path(args.raw_dir))
    if args.command == "fritsche-code-manifest":
        return _fritsche_code_manifest(
            code_zip=Path(args.code_zip),
            out_file=Path(args.out_file),
        )
    if args.command == "fritsche-harmonize":
        return _fritsche_harmonize(
            zip_file=Path(args.zip_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            experiments=args.experiment,
            limit=args.limit,
        )
    if args.command == "fritsche-analyze":
        return _fritsche_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "fritsche-report":
        return _fritsche_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "steinmetz-harmonize":
        return _steinmetz_harmonize(
            session_dir=Path(args.session_dir),
            session_id=args.session_id,
            subject_id=args.subject_id,
            out_dir=Path(args.out_dir),
            limit=args.limit,
        )
    if args.command == "steinmetz-analyze":
        return _steinmetz_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "steinmetz-report":
        return _steinmetz_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            choice_svg=Path(args.choice_svg) if args.choice_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "steinmetz-aggregate":
        return _steinmetz_aggregate(
            derived_dir=Path(args.derived_dir),
            out_dir=Path(args.out_dir),
            session_ids=args.session_id,
        )
    if args.command == "zatka-haas-code-manifest":
        return _zatka_haas_code_manifest(
            code_zip=Path(args.code_zip),
            out_file=Path(args.out_file),
        )
    if args.command == "zatka-haas-harmonize":
        return _zatka_haas_harmonize(
            mat_file=Path(args.mat_file),
            source_variable=args.source_variable,
            session_id=args.session_id,
            out_dir=Path(args.out_dir),
            limit=args.limit,
        )
    if args.command == "visual-contrast-family-summary":
        return _visual_contrast_family_summary(out_dir=Path(args.out_dir))
    if args.command == "odoemene-harmonize":
        return _odoemene_harmonize(
            mat_file=Path(args.mat_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            limit=args.limit,
            max_subjects=args.max_subjects,
        )
    if args.command == "odoemene-analyze":
        return _odoemene_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "odoemene-report":
        return _odoemene_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            kernel_svg=Path(args.kernel_svg) if args.kernel_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "coen-harmonize":
        return _coen_harmonize(
            source_file=Path(args.source_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            limit=args.limit,
        )
    if args.command == "coen-analyze":
        return _coen_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "coen-report":
        return _coen_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            condition_svg=Path(args.condition_svg) if args.condition_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "rodgers-harmonize":
        return _rodgers_harmonize(
            source_file=Path(args.source_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            subject_id=args.subject_id,
            task_rule=args.task_rule,
            limit=args.limit,
        )
    if args.command == "rodgers-analyze":
        return _rodgers_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "rodgers-report":
        return _rodgers_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            accuracy_svg=Path(args.accuracy_svg) if args.accuracy_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "human-visual-download":
        return _human_visual_download(raw_dir=Path(args.raw_dir))
    if args.command == "human-visual-harmonize":
        return _human_visual_harmonize(
            mat_file=Path(args.mat_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            limit=args.limit,
        )
    if args.command == "human-visual-analyze":
        return _human_visual_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "human-visual-report":
        return _human_visual_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "clicks-harmonize":
        return _clicks_harmonize(
            mat_file=Path(args.mat_file),
            out_dir=Path(args.out_dir),
            parsed_field=args.parsed_field,
            limit=args.limit,
        )
    if args.command == "clicks-analyze":
        return _clicks_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
            kernel_bins=args.kernel_bins,
        )
    if args.command == "clicks-batch":
        return _clicks_batch(
            mat_files=[Path(path) for path in args.mat_files] if args.mat_files else None,
            mat_dir=Path(args.mat_dir) if args.mat_dir else None,
            out_dir=Path(args.out_dir),
            parsed_field=args.parsed_field,
            limit=args.limit,
            kernel_bins=args.kernel_bins,
            max_files=args.max_files,
            fail_fast=args.fail_fast,
        )
    if args.command == "clicks-aggregate":
        return _clicks_aggregate(
            derived_dir=Path(args.derived_dir),
            batch_summary=Path(args.batch_summary) if args.batch_summary else None,
        )
    if args.command == "clicks-aggregate-trials":
        return _clicks_aggregate_trials(
            derived_dir=Path(args.derived_dir),
            batch_summary=Path(args.batch_summary) if args.batch_summary else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "clicks-report":
        return _clicks_report(
            derived_dir=Path(args.derived_dir),
            aggregate_result=Path(args.aggregate_result) if args.aggregate_result else None,
            aggregate_kernel_svg=Path(args.aggregate_kernel_svg)
            if args.aggregate_kernel_svg
            else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "human-clicks-download":
        return _human_clicks_download(out_file=Path(args.out_file))
    if args.command == "human-clicks-harmonize":
        return _human_clicks_harmonize(
            mat_file=Path(args.mat_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            limit=args.limit,
        )
    if args.command == "human-clicks-analyze":
        return _human_clicks_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
            kernel_bins=args.kernel_bins,
        )
    if args.command == "human-clicks-report":
        return _human_clicks_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            kernel_result=Path(args.kernel_result) if args.kernel_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            evidence_kernel_svg=Path(args.evidence_kernel_svg)
            if args.evidence_kernel_svg
            else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "rdm-download":
        return _rdm_download(out_file=Path(args.out_file))
    if args.command == "rdm-harmonize":
        return _rdm_harmonize(
            csv_file=Path(args.csv_file),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            monkey=args.monkey,
            limit=args.limit,
        )
    if args.command == "rdm-analyze":
        return _rdm_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "rdm-report":
        return _rdm_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            chronometric_svg=Path(args.chronometric_svg) if args.chronometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "human-rdm-download":
        return _human_rdm_download(
            out_dir=Path(args.out_dir),
            subjects=args.subject,
        )
    if args.command == "human-rdm-harmonize":
        return _human_rdm_harmonize(
            raw_dir=Path(args.raw_dir),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            subjects=args.subject,
            limit=args.limit,
        )
    if args.command == "human-rdm-analyze":
        return _human_rdm_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "human-rdm-report":
        return _rdm_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            psychometric_svg=Path(args.psychometric_svg) if args.psychometric_svg else None,
            chronometric_svg=Path(args.chronometric_svg) if args.chronometric_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "macaque-rdm-confidence-download":
        return _macaque_rdm_confidence_download(out_file=Path(args.out_file))
    if args.command == "macaque-rdm-confidence-intake-check":
        return _macaque_rdm_confidence_intake_check(
            raw_dir=Path(args.raw_dir),
            redistribution_status=(
                Path(args.redistribution_status) if args.redistribution_status else None
            ),
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "macaque-rdm-confidence-harmonize":
        return _macaque_rdm_confidence_harmonize(
            source_zip=Path(args.source_zip),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            limit=args.limit,
        )
    if args.command == "macaque-rdm-confidence-raw-harmonize":
        return _macaque_rdm_confidence_raw_harmonize(
            raw_dir=Path(args.raw_dir),
            redistribution_status=(
                Path(args.redistribution_status) if args.redistribution_status else None
            ),
            out_dir=Path(args.out_dir),
            session_id=args.session_id,
            limit=args.limit,
        )
    if args.command == "macaque-rdm-confidence-analyze":
        return _macaque_rdm_confidence_analyze(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "macaque-rdm-confidence-report":
        return _macaque_rdm_confidence_report(
            session_id=args.session_id,
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            accuracy_svg=Path(args.accuracy_svg) if args.accuracy_svg else None,
            confidence_svg=Path(args.confidence_svg) if args.confidence_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "allen-visual-behavior-download":
        return _allen_visual_behavior_download(
            nwb_url=args.nwb_url,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "allen-visual-behavior-harmonize":
        return _allen_visual_behavior_harmonize(
            nwb_file=Path(args.nwb_file),
            out_dir=Path(args.out_dir),
            limit=args.limit,
        )
    if args.command == "allen-visual-behavior-analyze":
        return _allen_visual_behavior_analyze(
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "allen-visual-behavior-report":
        return _allen_visual_behavior_report(
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            lick_latency_svg=Path(args.lick_latency_svg) if args.lick_latency_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "allen-vbn-download":
        return _allen_vbn_download(
            nwb_url=args.nwb_url,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "allen-vbn-harmonize":
        return _allen_vbn_harmonize(
            nwb_file=Path(args.nwb_file),
            out_dir=Path(args.out_dir),
            limit=args.limit,
        )
    if args.command == "allen-vbn-analyze":
        return _allen_vbn_analyze(
            derived_dir=Path(args.derived_dir),
            trials_csv=Path(args.trials_csv) if args.trials_csv else None,
        )
    if args.command == "allen-vbn-report":
        return _allen_vbn_report(
            derived_dir=Path(args.derived_dir),
            analysis_result=Path(args.analysis_result) if args.analysis_result else None,
            provenance=Path(args.provenance) if args.provenance else None,
            lick_latency_svg=Path(args.lick_latency_svg) if args.lick_latency_svg else None,
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "extract-finding":
        return _extract_finding(
            slice_id=args.slice_id,
            paper_id=args.paper_id,
            finding_id_prefix=args.finding_id_prefix,
            curve_type=args.curve_type,
            by_subject=bool(args.by_subject),
            by_subject_condition=args.by_subject_condition,
            condition_values=(
                tuple(args.condition_value) if args.condition_value else None
            ),
            x_label=args.x_label,
            x_units=args.x_units,
            summary_filename=args.summary_filename,
            condition_column=args.condition_column,
            y_column=args.y_column,
            y_label=args.y_label,
            n_column=args.n_column,
            derived_dir=Path(args.derived_dir),
        )
    if args.command == "import-supplement":
        return _import_supplement(
            csv_path=Path(args.csv_path),
            mapping_path=Path(args.mapping),
        )
    if args.command == "site-index":
        return _site_index(
            derived_dir=Path(args.derived_dir),
            manifest_file=Path(args.manifest_file) if args.manifest_file else None,
            catalog_json_file=Path(args.catalog_json_file)
            if args.catalog_json_file
            else None,
            graph_json_file=Path(args.graph_json_file) if args.graph_json_file else None,
            curation_queue_json_file=Path(args.curation_queue_json_file)
            if args.curation_queue_json_file
            else None,
        )
    if args.command == "data-request-export":
        return _data_request_export(
            request_id=args.request_id,
            root=Path(args.root),
            out_dir=Path(args.out_dir),
            stdout=bool(args.stdout),
        )
    if args.command == "data-request-queue":
        return _data_request_queue(
            root=Path(args.root),
            today=args.today,
            json_output=bool(args.json),
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "data-request-event":
        return _data_request_event(
            request_id=args.request_id,
            root=Path(args.root),
            event_type=args.event_type,
            event_date=args.event_date,
            actor=args.actor,
            notes=args.notes,
            status=args.status,
            evidence_url=args.evidence_url,
            evidence_path=Path(args.evidence_path) if args.evidence_path else None,
            next_follow_up_date=args.next_follow_up_date,
            create_evidence_stub=bool(args.create_evidence_stub),
            force=bool(args.force),
        )
    if args.command == "release-check":
        return _release_check(
            root=Path(args.root),
            derived_dir=Path(args.derived_dir),
            out_file=Path(args.out_file) if args.out_file else None,
            html_file=Path(args.html_file) if args.html_file else None,
        )
    if args.command == "audit-findings":
        return _audit_findings(
            tolerance=float(args.tolerance),
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "audit-models":
        return _audit_models(
            tolerance=float(args.tolerance),
            out_file=Path(args.out_file) if args.out_file else None,
        )
    if args.command == "fit-model":
        return _fit_model(
            variant_id=args.variant_id,
            finding_id=args.finding_id,
            out_dir=Path(args.out_dir),
        )
    if args.command == "fit-stale-models":
        return _fit_stale_models(
            variant_filter=args.variant_filter,
            curve_types=tuple(t.strip() for t in args.curve_types.split(",") if t.strip()),
            out_dir=Path(args.out_dir),
        )
    parser.error(f"Unknown command {args.command!r}")
    return 2


def _validate(root: Path) -> int:
    report = validate_repository(root.resolve())
    if report.ok:
        print(f"Validated {len(report.records)} records.")
        return 0

    for issue in report.issues:
        print(f"{issue.path}: {issue.message}", file=sys.stderr)
    return 1


def _export_schemas(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    for schema_name, model in SCHEMA_MODELS.items():
        path = output_dir / f"{schema_name}.schema.json"
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(path)
    return 0


def _ibl_harmonize(
    *,
    eid: str,
    out_dir: Path,
    cache_dir: Path | None,
    limit: int | None,
    revision: str | None,
    protocol_id: str,
) -> int:
    try:
        source_trials, details = load_ibl_trials_from_openalyx(
            eid,
            cache_dir=cache_dir,
            revision=revision,
        )
        trials = harmonize_ibl_visual_trials(
            source_trials,
            session_id=eid,
            subject_id=details.get("subject"),
            protocol_id=protocol_id,
            limit=limit,
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / eid
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"

    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        provenance_payload(
            eid=eid,
            details=details,
            trials=trials,
            protocol_id=protocol_id,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _ibl_analyze(
    *,
    eid: str,
    derived_dir: Path,
    trials_csv: Path | None,
    protocol_id: str | None,
) -> int:
    session_dir = derived_dir / eid
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra ibl behavtaskatlas ibl-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_ibl_visual_protocol(trials, protocol_id=protocol_id)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(plot_path, result["summary_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    return 0


def _ibl_report(
    *,
    eid: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / eid
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or session_dir / "psychometric.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"IBL-style visual analysis result not found: {analysis_path}. "
            "Run the matching analyze command first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = None
    if psychometric_svg_path.exists():
        psychometric_svg_text = psychometric_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", session_dir / "psychometric_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("canonical trials CSV", session_dir / "trials.csv"),
            ("harmonization summary CSV", session_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_ibl_visual_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote IBL-style visual report to {report_path}")
    if psychometric_svg_text is None:
        print(
            "Psychometric SVG not found, wrote report without inline plot: "
            f"{psychometric_svg_path}"
        )
    return 0


def _fritsche_download(*, raw_dir: Path) -> int:
    try:
        details = download_fritsche_temporal_regularities_data(raw_dir)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded Fritsche Figshare data ZIP to {details['path']}")
    print(f"File size: {details['n_bytes']} bytes")
    print(f"SHA-256: {details['sha256']}")
    return 0


def _fritsche_code_download(*, raw_dir: Path) -> int:
    try:
        details = download_fritsche_temporal_regularities_code(raw_dir)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded Fritsche Figshare code ZIP to {details['path']}")
    print(f"File size: {details['n_bytes']} bytes")
    print(f"SHA-256: {details['sha256']}")
    return 0


def _fritsche_code_manifest(*, code_zip: Path, out_file: Path) -> int:
    try:
        manifest = build_fritsche_code_manifest(code_zip)
    except (OSError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    write_fritsche_code_manifest(out_file, manifest)
    artifact_provenance_path = out_file.with_name("artifact_provenance.csv")
    session_dir = out_file.parent
    if session_dir.name:
        artifact_rows = fritsche_artifact_provenance_rows(
            derived_dir=session_dir.parent,
            session_id=session_dir.name,
        )
    else:
        artifact_rows = fritsche_artifact_provenance_rows()
    write_fritsche_artifact_provenance_csv(artifact_provenance_path, artifact_rows)
    print(f"Wrote Fritsche code manifest to {out_file}")
    print(
        "Wrote Fritsche artifact provenance table to "
        f"{artifact_provenance_path} ({len(artifact_rows)} artifact row(s))"
    )
    print(
        "Inventoried "
        f"{manifest.get('zip', {}).get('n_files', 0)} ZIP file(s), "
        f"{manifest.get('zip', {}).get('n_source_scripts_hashed', 0)} hashed source script(s)"
    )
    return 0


def _fritsche_harmonize(
    *,
    zip_file: Path,
    out_dir: Path,
    session_id: str,
    experiments: list[str] | None,
    limit: int | None,
) -> int:
    try:
        source_rows, details = load_fritsche_temporal_regularities_rows(
            zip_file,
            experiments=experiments,
            limit=limit,
        )
        trials = harmonize_fritsche_temporal_regularities_rows(source_rows)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)

    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        fritsche_temporal_regularities_provenance_payload(
            zip_file=zip_file,
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} Fritsche temporal-regularities trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _fritsche_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical Fritsche temporal-regularities trials CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas fritsche-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_fritsche_temporal_regularities(trials)
    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"
    transition_path = session_dir / "transition_summary.csv"
    choice_history_path = session_dir / "choice_history_summary.csv"
    subject_environment_path = session_dir / "subject_environment_summary.csv"
    choice_history_model_path = session_dir / "choice_history_model_coefficients.csv"
    neutral_adaptation_path = session_dir / "neutral_adaptation_summary.csv"
    neutral_adaptation_session_path = session_dir / "neutral_adaptation_session_summary.csv"

    write_summary_csv(summary_path, result["summary_rows"])
    write_fritsche_transition_csv(transition_path, result["transition_rows"])
    write_fritsche_choice_history_csv(choice_history_path, result["choice_history_rows"])
    write_fritsche_subject_environment_csv(
        subject_environment_path,
        result["subject_environment_rows"],
    )
    write_fritsche_choice_history_model_csv(
        choice_history_model_path,
        result["choice_history_model_term_rows"],
    )
    write_fritsche_neutral_adaptation_csv(
        neutral_adaptation_path,
        result["neutral_adaptation_rows"],
    )
    write_fritsche_neutral_adaptation_session_csv(
        neutral_adaptation_session_path,
        result["neutral_adaptation_session_rows"],
    )
    write_analysis_json(result_path, result)
    write_psychometric_svg(plot_path, result["summary_rows"])

    print(f"Analyzed {len(trials)} Fritsche temporal-regularities trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote transition summary to {transition_path}")
    print(f"Wrote choice-history summary to {choice_history_path}")
    print(f"Wrote subject-environment summary to {subject_environment_path}")
    print(f"Wrote choice-history model coefficients to {choice_history_model_path}")
    print(f"Wrote neutral-adaptation summary to {neutral_adaptation_path}")
    print(f"Wrote neutral-adaptation session summary to {neutral_adaptation_session_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    return 0


def _fritsche_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or session_dir / "psychometric.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Fritsche temporal-regularities analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas fritsche-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = None
    if psychometric_svg_path.exists():
        psychometric_svg_text = psychometric_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", session_dir / "psychometric_summary.csv"),
            ("transition summary CSV", session_dir / "transition_summary.csv"),
            ("choice-history summary CSV", session_dir / "choice_history_summary.csv"),
            ("subject-environment summary CSV", session_dir / "subject_environment_summary.csv"),
            (
                "choice-history model coefficients CSV",
                session_dir / "choice_history_model_coefficients.csv",
            ),
            ("neutral adaptation summary CSV", session_dir / "neutral_adaptation_summary.csv"),
            (
                "neutral adaptation session CSV",
                session_dir / "neutral_adaptation_session_summary.csv",
            ),
            ("artifact provenance CSV", session_dir / "artifact_provenance.csv"),
            ("code manifest JSON", session_dir / "code_manifest.json"),
            ("psychometric SVG", psychometric_svg_path),
            ("canonical trials CSV", session_dir / "trials.csv"),
            ("harmonization summary CSV", session_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_fritsche_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote Fritsche temporal-regularities report to {report_path}")
    if psychometric_svg_text is None:
        print(
            "Psychometric SVG not found, wrote report without inline plot: "
            f"{psychometric_svg_path}"
        )
    return 0


def _ibl_brainwide_harmonize(
    *,
    eid: str,
    out_dir: Path,
    cache_dir: Path | None,
    limit: int | None,
    revision: str | None,
) -> int:
    try:
        source_trials, details = load_ibl_trials_from_openalyx(
            eid,
            cache_dir=cache_dir,
            revision=revision,
        )
        trials = harmonize_ibl_visual_trials(
            source_trials,
            session_id=eid,
            subject_id=details.get("subject"),
            dataset_id=IBL_BRAINWIDE_MAP_DATASET_ID,
            protocol_id=IBL_VISUAL_PROTOCOL_ID,
            limit=limit,
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / eid
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)

    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        ibl_brainwide_map_provenance_payload(
            eid=eid,
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} Brainwide Map trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _ibl_brainwide_analyze(
    *,
    eid: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / eid
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical IBL Brainwide Map trials CSV not found: {trials_path}. "
            "Run `uv run --extra ibl behavtaskatlas ibl-brainwide-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_ibl_brainwide_map_behavior(trials)
    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(plot_path, result["summary_rows"])

    print(f"Analyzed {len(trials)} Brainwide Map trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    return 0


def _steinmetz_harmonize(
    *,
    session_dir: Path,
    session_id: str | None,
    subject_id: str | None,
    out_dir: Path,
    limit: int | None,
) -> int:
    selected_session_id = session_id or session_dir.name
    if not session_dir.exists():
        print(
            f"Steinmetz session directory not found: {session_dir}. "
            "Extract one session from the Figshare archive and point --session-dir at "
            "the directory containing trials.*.npy files.",
            file=sys.stderr,
        )
        return 2

    try:
        source_trials, details = load_steinmetz_session_dir(session_dir)
        trials = harmonize_steinmetz_visual_trials(
            source_trials,
            session_id=selected_session_id,
            subject_id=subject_id,
            limit=limit,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    artifact_dir = out_dir / selected_session_id
    trials_path = artifact_dir / "trials.csv"
    summary_path = artifact_dir / "summary.csv"
    condition_path = artifact_dir / "condition_summary.csv"
    provenance_path = artifact_dir / "provenance.json"
    summary = summarize_steinmetz_choice_by_signed_contrast(trials)
    condition_summary = summarize_steinmetz_choice_by_contrast_pair(trials)

    write_canonical_trials_csv(trials_path, trials)
    write_steinmetz_summary_csv(summary_path, summary)
    write_steinmetz_condition_csv(condition_path, condition_summary)
    write_provenance_json(
        provenance_path,
        steinmetz_provenance_payload(
            session_dir=session_dir,
            session_id=selected_session_id,
            subject_id=subject_id,
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "condition_summary": str(condition_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} signed-contrast summary rows to {summary_path}")
    print(f"Wrote {len(condition_summary)} contrast-condition rows to {condition_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _steinmetz_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    trials_path = trials_csv or artifact_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical Steinmetz trials CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas steinmetz-harmonize --session-dir <dir>` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_steinmetz_visual_decision(trials)
    summary_path = artifact_dir / "choice_summary.csv"
    condition_path = artifact_dir / "condition_summary.csv"
    result_path = artifact_dir / "analysis_result.json"
    plot_path = artifact_dir / "choice_summary.svg"

    write_steinmetz_summary_csv(summary_path, result["summary_rows"])
    write_steinmetz_condition_csv(condition_path, result["condition_rows"])
    write_analysis_json(result_path, result)
    write_steinmetz_choice_svg(plot_path, result["summary_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote choice summary to {summary_path}")
    print(f"Wrote condition summary to {condition_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote choice plot to {plot_path}")
    return 0


def _steinmetz_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    choice_svg: Path | None,
    out_file: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    analysis_path = analysis_result or artifact_dir / "analysis_result.json"
    provenance_path = provenance or artifact_dir / "provenance.json"
    choice_svg_path = choice_svg or artifact_dir / "choice_summary.svg"
    report_path = out_file or artifact_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Steinmetz analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas steinmetz-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    choice_svg_text = None
    if choice_svg_path.exists():
        choice_svg_text = choice_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("choice summary CSV", artifact_dir / "choice_summary.csv"),
            ("condition summary CSV", artifact_dir / "condition_summary.csv"),
            ("choice summary SVG", choice_svg_path),
            ("canonical trials CSV", artifact_dir / "trials.csv"),
        ]
        if path.exists()
    }
    write_steinmetz_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        choice_svg_text=choice_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote Steinmetz visual decision report to {report_path}")
    if choice_svg_text is None:
        print(
            "Choice summary SVG not found, wrote report without inline plot: "
            f"{choice_svg_path}"
        )
    return 0


def _steinmetz_aggregate(
    *,
    derived_dir: Path,
    out_dir: Path,
    session_ids: list[str] | None,
) -> int:
    try:
        loaded_sessions = load_steinmetz_derived_sessions(
            derived_dir,
            session_ids=session_ids,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not loaded_sessions:
        print(
            f"No generated Steinmetz session trials found under {derived_dir}",
            file=sys.stderr,
        )
        return 2

    result = analyze_steinmetz_session_aggregate(loaded_sessions)
    paths = write_steinmetz_aggregate_outputs(out_dir, result)
    print(
        "Aggregated Steinmetz visual decision sessions: "
        f"{result['n_sessions']} session(s), {result['n_subjects']} subject(s), "
        f"{result['n_trials']} trial(s)"
    )
    print(f"Wrote aggregate result to {paths['aggregate_result']}")
    print(f"Wrote session summary to {paths['session_summary']}")
    print(f"Wrote subject summary to {paths['subject_summary']}")
    print(f"Wrote signed contrast summary to {paths['signed_contrast_summary']}")
    print(f"Wrote aggregate choice SVG to {paths['choice_svg']}")
    print(f"Wrote aggregate report to {paths['report']}")
    return 0


def _zatka_haas_code_manifest(*, code_zip: Path, out_file: Path) -> int:
    try:
        manifest = build_zatka_haas_code_manifest(code_zip)
    except (OSError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    write_zatka_haas_code_manifest(out_file, manifest)
    print(f"Wrote Zatka-Haas code manifest to {out_file}")
    print(
        "Found "
        f"{len(manifest.get('source_data_dependencies', []))} source data dependency path(s)"
    )
    return 0


def _zatka_haas_harmonize(
    *,
    mat_file: Path,
    source_variable: str,
    session_id: str,
    out_dir: Path,
    limit: int | None,
) -> int:
    try:
        source = load_zatka_haas_processed_mat(mat_file, variable=source_variable)
        trials = harmonize_zatka_haas_visual_trials(
            source,
            session_id=session_id,
            limit=limit,
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    artifact_dir = out_dir / session_id
    trials_path = artifact_dir / "trials.csv"
    summary_path = artifact_dir / "choice_summary.csv"
    choice_svg_path = artifact_dir / "choice_summary.svg"
    condition_path = artifact_dir / "condition_summary.csv"
    laser_state_path = artifact_dir / "laser_state_summary.csv"
    laser_region_path = artifact_dir / "laser_region_summary.csv"
    perturbation_delta_path = artifact_dir / "perturbation_delta_summary.csv"
    perturbation_region_effect_path = artifact_dir / "perturbation_region_effect_summary.csv"
    result_path = artifact_dir / "analysis_result.json"
    provenance_path = artifact_dir / "provenance.json"
    report_path = artifact_dir / "report.html"
    result = analyze_zatka_haas_visual_decision(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_zatka_haas_summary_csv(summary_path, result["summary_rows"])
    write_zatka_haas_choice_svg(choice_svg_path, result["summary_rows"])
    write_zatka_haas_condition_csv(condition_path, result["condition_rows"])
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
    write_analysis_json(result_path, result)
    output_files = {
        "trials": str(trials_path),
        "choice_summary": str(summary_path),
        "choice_summary_svg": str(choice_svg_path),
        "condition_summary": str(condition_path),
        "laser_state_summary": str(laser_state_path),
        "laser_region_summary": str(laser_region_path),
        "perturbation_delta_summary": str(perturbation_delta_path),
        "perturbation_region_effect_summary": str(perturbation_region_effect_path),
        "analysis_result": str(result_path),
        "provenance": str(provenance_path),
        "report": str(report_path),
    }
    provenance = zatka_haas_provenance_payload(
        source_file=mat_file,
        session_id=session_id,
        details={
            "source_fields": sorted(source),
            "n_trials": len(trials),
            "source_variable": source_variable,
        },
        trials=trials,
        output_files=output_files,
    )
    write_provenance_json(
        provenance_path,
        provenance,
    )
    write_zatka_haas_report_html(
        report_path,
        result,
        provenance=provenance,
        choice_svg_text=choice_svg_path.read_text(encoding="utf-8"),
        artifact_links={
            "Canonical trials CSV": "trials.csv",
            "Choice summary CSV": "choice_summary.csv",
            "Choice summary SVG": "choice_summary.svg",
            "Condition summary CSV": "condition_summary.csv",
            "Laser-state summary CSV": "laser_state_summary.csv",
            "Laser-region summary CSV": "laser_region_summary.csv",
            "Perturbation delta summary CSV": "perturbation_delta_summary.csv",
            "Perturbation region effect CSV": "perturbation_region_effect_summary.csv",
            "Analysis result JSON": "analysis_result.json",
            "Provenance JSON": "provenance.json",
        },
    )

    print(f"Wrote {len(trials)} Zatka-Haas trials to {trials_path}")
    print(f"Wrote choice summary to {summary_path}")
    print(f"Wrote choice summary SVG to {choice_svg_path}")
    print(f"Wrote condition summary to {condition_path}")
    print(f"Wrote laser-state summary to {laser_state_path}")
    print(f"Wrote laser-region summary to {laser_region_path}")
    print(f"Wrote perturbation delta summary to {perturbation_delta_path}")
    print(f"Wrote perturbation region effect summary to {perturbation_region_effect_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote provenance to {provenance_path}")
    print(f"Wrote report to {report_path}")
    return 0


def _visual_contrast_family_summary(*, out_dir: Path) -> int:
    try:
        loaded_sources = load_visual_contrast_family_trials()
        perturbation_effect_rows = load_visual_contrast_family_perturbation_effects()
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    result = analyze_visual_contrast_family(
        loaded_sources,
        perturbation_effect_rows=perturbation_effect_rows,
    )
    paths = write_visual_contrast_family_outputs(out_dir, result)
    print(
        "Wrote visual contrast family summary for "
        f"{result['n_sources']} source(s) and {result['n_trials']} trial(s)"
    )
    print(f"Wrote analysis result to {paths['analysis_result']}")
    print(f"Wrote source summary to {paths['source_summary']}")
    print(f"Wrote signed contrast summary to {paths['signed_contrast_summary']}")
    print(f"Wrote pooled signed contrast summary to {paths['pooled_signed_contrast_summary']}")
    print(f"Wrote response format summary to {paths['response_format_summary']}")
    print(
        "Wrote protocol-normalized signed contrast summary to "
        f"{paths['protocol_normalized_signed_contrast_summary']}"
    )
    print(
        "Wrote protocol-normalized choice SVG to "
        f"{paths['protocol_normalized_choice_svg']}"
    )
    print(
        "Wrote source-balanced protocol-normalized summary to "
        f"{paths['source_balanced_protocol_normalized_summary']}"
    )
    print(
        "Wrote source-balanced protocol-normalized SVG to "
        f"{paths['source_balanced_protocol_normalized_svg']}"
    )
    print(
        "Wrote session-balanced protocol-normalized summary to "
        f"{paths['session_balanced_protocol_normalized_summary']}"
    )
    print(
        "Wrote session-balanced protocol-normalized SVG to "
        f"{paths['session_balanced_protocol_normalized_svg']}"
    )
    print(
        "Wrote subject-balanced protocol-normalized summary to "
        f"{paths['subject_balanced_protocol_normalized_summary']}"
    )
    print(
        "Wrote subject-balanced protocol-normalized SVG to "
        f"{paths['subject_balanced_protocol_normalized_svg']}"
    )
    print(
        "Wrote perturbation region effect summary to "
        f"{paths['perturbation_region_effect_summary']}"
    )
    print(
        "Wrote perturbation region effect SVG to "
        f"{paths['perturbation_region_effects_svg']}"
    )
    print(f"Wrote report to {paths['report']}")
    return 0


def _odoemene_harmonize(
    *,
    mat_file: Path,
    out_dir: Path,
    session_id: str,
    limit: int | None,
    max_subjects: int | None,
) -> int:
    if not mat_file.exists():
        print(
            f"Odoemene MATLAB file not found: {mat_file}. "
            "Download the CSHL dataset into ignored raw-data storage first.",
            file=sys.stderr,
        )
        return 2
    try:
        trials, details = load_odoemene_visual_accumulation_mat(
            mat_file,
            session_id=session_id,
            limit=limit,
            max_subjects=max_subjects,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    artifact_dir = out_dir / session_id
    trials_path = artifact_dir / "trials.csv"
    summary_path = artifact_dir / "summary.csv"
    provenance_path = artifact_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)

    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        odoemene_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _odoemene_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    trials_path = trials_csv or artifact_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical Odoemene trials CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas odoemene-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_odoemene_visual_accumulation(trials)
    summary_path = artifact_dir / "psychometric_summary.csv"
    result_path = artifact_dir / "analysis_result.json"
    psychometric_path = artifact_dir / "psychometric.svg"
    kernel_path = artifact_dir / "event_kernel.csv"
    kernel_svg_path = artifact_dir / "event_kernel.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        psychometric_path,
        result["summary_rows"],
        x_axis_label="Signed flash rate (flashes/s minus 12 Hz boundary)",
    )
    write_odoemene_kernel_csv(kernel_path, result["event_kernel_rows"])
    write_odoemene_kernel_svg(kernel_svg_path, result["event_kernel_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {psychometric_path}")
    print(f"Wrote event kernel to {kernel_path}")
    print(f"Wrote event-kernel plot to {kernel_svg_path}")
    return 0


def _odoemene_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    kernel_svg: Path | None,
    out_file: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    analysis_path = analysis_result or artifact_dir / "analysis_result.json"
    provenance_path = provenance or artifact_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or artifact_dir / "psychometric.svg"
    kernel_svg_path = kernel_svg or artifact_dir / "event_kernel.svg"
    report_path = out_file or artifact_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Odoemene analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas odoemene-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = None
    if psychometric_svg_path.exists():
        psychometric_svg_text = psychometric_svg_path.read_text(encoding="utf-8")
    kernel_svg_text = None
    if kernel_svg_path.exists():
        kernel_svg_text = kernel_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", artifact_dir / "psychometric_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("event kernel CSV", artifact_dir / "event_kernel.csv"),
            ("event kernel SVG", kernel_svg_path),
            ("canonical trials CSV", artifact_dir / "trials.csv"),
            ("harmonization summary CSV", artifact_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_odoemene_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        kernel_svg_text=kernel_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote Odoemene visual accumulation report to {report_path}")
    if psychometric_svg_text is None:
        print(
            "Psychometric SVG not found, wrote report without inline psychometric plot: "
            f"{psychometric_svg_path}"
        )
    if kernel_svg_text is None:
        print(
            "Event-kernel SVG not found, wrote report without inline kernel plot: "
            f"{kernel_svg_path}"
        )
    return 0


def _coen_harmonize(
    *,
    source_file: Path,
    out_dir: Path,
    session_id: str,
    limit: int | None,
) -> int:
    if not source_file.exists():
        print(
            f"Coen audiovisual source file not found: {source_file}. "
            "Download the UCL release or export the combined block into ignored "
            "raw-data storage first.",
            file=sys.stderr,
        )
        return 2
    try:
        trials, details = load_coen_audiovisual_source(
            source_file,
            session_id=session_id,
            limit=limit,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    artifact_dir = out_dir / session_id
    trials_path = artifact_dir / "trials.csv"
    summary_path = artifact_dir / "summary.csv"
    provenance_path = artifact_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)

    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        coen_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _coen_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    trials_path = trials_csv or artifact_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical Coen trials CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas coen-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_coen_audiovisual_decisions(trials)
    summary_path = artifact_dir / "psychometric_summary.csv"
    modality_path = artifact_dir / "modality_summary.csv"
    condition_path = artifact_dir / "condition_summary.csv"
    conflict_path = artifact_dir / "conflict_summary.csv"
    result_path = artifact_dir / "analysis_result.json"
    psychometric_path = artifact_dir / "psychometric.svg"
    condition_svg_path = artifact_dir / "condition_summary.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_coen_modality_csv(modality_path, result["modality_rows"])
    write_coen_condition_csv(condition_path, result["condition_rows"])
    write_coen_conflict_csv(conflict_path, result["conflict_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        psychometric_path,
        result["summary_rows"],
        x_axis_label="Signed audiovisual evidence proxy (visDiff + audDiff)",
    )
    write_coen_condition_svg(condition_svg_path, result["condition_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote modality summary to {modality_path}")
    print(f"Wrote condition summary to {condition_path}")
    print(f"Wrote conflict summary to {conflict_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {psychometric_path}")
    print(f"Wrote condition-surface plot to {condition_svg_path}")
    return 0


def _coen_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    condition_svg: Path | None,
    out_file: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    analysis_path = analysis_result or artifact_dir / "analysis_result.json"
    provenance_path = provenance or artifact_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or artifact_dir / "psychometric.svg"
    condition_svg_path = condition_svg or artifact_dir / "condition_summary.svg"
    report_path = out_file or artifact_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Coen analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas coen-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = None
    if psychometric_svg_path.exists():
        psychometric_svg_text = psychometric_svg_path.read_text(encoding="utf-8")
    condition_svg_text = None
    if condition_svg_path.exists():
        condition_svg_text = condition_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", artifact_dir / "psychometric_summary.csv"),
            ("modality summary CSV", artifact_dir / "modality_summary.csv"),
            ("condition summary CSV", artifact_dir / "condition_summary.csv"),
            ("conflict summary CSV", artifact_dir / "conflict_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("condition summary SVG", condition_svg_path),
            ("canonical trials CSV", artifact_dir / "trials.csv"),
            ("harmonization summary CSV", artifact_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_coen_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        condition_svg_text=condition_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote Coen audiovisual decision report to {report_path}")
    if psychometric_svg_text is None:
        print(
            "Psychometric SVG not found, wrote report without inline psychometric plot: "
            f"{psychometric_svg_path}"
        )
    if condition_svg_text is None:
        print(
            "Condition summary SVG not found, wrote report without inline condition plot: "
            f"{condition_svg_path}"
        )
    return 0


def _rodgers_harmonize(
    *,
    source_file: Path,
    out_dir: Path,
    session_id: str,
    subject_id: str | None,
    task_rule: str | None,
    limit: int | None,
) -> int:
    if not source_file.exists():
        print(
            f"Rodgers source file not found: {source_file}. Download a DANDI NWB "
            "session or export the NWB trials table into ignored raw-data storage first.",
            file=sys.stderr,
        )
        return 2
    try:
        trials, details = load_rodgers_whisker_source(
            source_file,
            session_id=session_id,
            subject_id=subject_id,
            task_rule=task_rule,
            limit=limit,
        )
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    artifact_dir = out_dir / session_id
    trials_path = artifact_dir / "trials.csv"
    summary_path = artifact_dir / "summary.csv"
    provenance_path = artifact_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)

    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        rodgers_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _rodgers_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    trials_path = trials_csv or artifact_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical Rodgers trials CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas rodgers-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_rodgers_whisker_object_recognition(trials)
    task_rule_path = artifact_dir / "task_rule_summary.csv"
    condition_path = artifact_dir / "condition_summary.csv"
    detection_path = artifact_dir / "detection_summary.csv"
    result_path = artifact_dir / "analysis_result.json"
    accuracy_path = artifact_dir / "accuracy.svg"

    write_rodgers_task_rule_csv(task_rule_path, result["task_rule_rows"])
    write_rodgers_condition_csv(condition_path, result["condition_rows"])
    write_rodgers_detection_csv(detection_path, result["detection_rows"])
    write_analysis_json(result_path, result)
    write_rodgers_accuracy_svg(accuracy_path, result["condition_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote task-rule summary to {task_rule_path}")
    print(f"Wrote condition summary to {condition_path}")
    print(f"Wrote detection summary to {detection_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote accuracy plot to {accuracy_path}")
    return 0


def _rodgers_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    accuracy_svg: Path | None,
    out_file: Path | None,
) -> int:
    artifact_dir = derived_dir / session_id
    analysis_path = analysis_result or artifact_dir / "analysis_result.json"
    provenance_path = provenance or artifact_dir / "provenance.json"
    accuracy_svg_path = accuracy_svg or artifact_dir / "accuracy.svg"
    report_path = out_file or artifact_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Rodgers analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas rodgers-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    accuracy_svg_text = None
    if accuracy_svg_path.exists():
        accuracy_svg_text = accuracy_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("task-rule summary CSV", artifact_dir / "task_rule_summary.csv"),
            ("condition summary CSV", artifact_dir / "condition_summary.csv"),
            ("detection summary CSV", artifact_dir / "detection_summary.csv"),
            ("accuracy SVG", accuracy_svg_path),
            ("canonical trials CSV", artifact_dir / "trials.csv"),
            ("harmonization summary CSV", artifact_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_rodgers_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        accuracy_svg_text=accuracy_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote Rodgers whisker object-recognition report to {report_path}")
    if accuracy_svg_text is None:
        print(
            "Accuracy SVG not found, wrote report without inline accuracy plot: "
            f"{accuracy_svg_path}"
        )
    return 0


def _human_visual_download(*, raw_dir: Path) -> int:
    try:
        details = download_walsh_human_visual_contrast_files(raw_dir)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded {details['n_files']} files ({details['n_bytes']} bytes) to {raw_dir}")
    for file in details["files"]:
        print(f"SHA256 {file['file_name']} {file['sha256']}")
    return 0


def _human_visual_harmonize(
    *,
    mat_file: Path,
    out_dir: Path,
    session_id: str,
    limit: int | None,
) -> int:
    if not mat_file.exists():
        print(
            f"Human visual contrast MAT file not found: {mat_file}. "
            "Run `uv run --extra visual behavtaskatlas human-visual-download` first.",
            file=sys.stderr,
        )
        return 2
    try:
        trials, details = load_walsh_human_visual_contrast_mat(
            mat_file,
            session_id=session_id,
            limit=limit,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        human_visual_contrast_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _human_visual_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra visual behavtaskatlas human-visual-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_human_visual_contrast(trials)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        plot_path,
        result["summary_rows"],
        x_axis_label=HUMAN_VISUAL_CONTRAST_PSYCHOMETRIC_X_AXIS_LABEL,
    )

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    return 0


def _human_visual_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or session_dir / "psychometric.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Human visual contrast analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas human-visual-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = None
    if psychometric_svg_path.exists():
        psychometric_svg_text = psychometric_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", session_dir / "psychometric_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("canonical trials CSV", session_dir / "trials.csv"),
            ("harmonization summary CSV", session_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_ibl_visual_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote human visual contrast report to {report_path}")
    if psychometric_svg_text is None:
        print(
            "Psychometric SVG not found, wrote report without inline plot: "
            f"{psychometric_svg_path}"
        )
    return 0


def _allen_visual_behavior_download(
    *,
    nwb_url: str,
    out_file: Path | None,
) -> int:
    target = out_file or DEFAULT_ALLEN_VISUAL_BEHAVIOR_RAW_DIR / nwb_url.rsplit("/", 1)[-1]
    try:
        details = download_allen_visual_behavior_session(
            nwb_url=nwb_url,
            out_file=target,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        f"Downloaded {details['nwb_file_bytes']} bytes from {nwb_url} to "
        f"{details['nwb_file']}"
    )
    print(f"SHA256 {details['nwb_file_sha256']}")
    return 0


def _allen_visual_behavior_harmonize(
    *,
    nwb_file: Path,
    out_dir: Path,
    limit: int | None,
) -> int:
    try:
        trials, details = load_allen_visual_behavior_session(
            nwb_file=nwb_file,
            limit=limit,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    trials_path = out_dir / "trials.csv"
    outcome_path = out_dir / "outcome_summary.csv"
    provenance_path = out_dir / "provenance.json"

    write_allen_canonical_trials_csv(trials_path, trials)
    outcome_counts: dict[str, int] = {}
    for trial in trials:
        outcome = str(trial.task_variables.get("outcome", "unknown"))
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    write_outcome_summary_csv(outcome_path, outcome_counts)
    write_provenance_json(
        provenance_path,
        allen_visual_behavior_provenance_payload(
            details=details,
            output_files={
                "trials": str(trials_path),
                "outcome_summary": str(outcome_path),
                "provenance": str(provenance_path),
            },
            trials=trials,
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote outcome summary to {outcome_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _allen_visual_behavior_analyze(
    *,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    trials_path = trials_csv or derived_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra allen behavtaskatlas allen-visual-behavior-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_allen_change_detection(trials)

    image_pair_path = derived_dir / "image_pair_summary.csv"
    result_path = derived_dir / "analysis_result.json"
    plot_path = derived_dir / "lick_latency.svg"

    write_image_pair_csv(image_pair_path, result["image_pair_summary"])
    write_allen_analysis_json(result_path, result)
    write_lick_latency_svg(plot_path, trials)

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote image pair summary to {image_pair_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote lick latency plot to {plot_path}")
    return 0


def _allen_visual_behavior_report(
    *,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    lick_latency_svg: Path | None,
    out_file: Path | None,
) -> int:
    analysis_path = analysis_result or derived_dir / "analysis_result.json"
    provenance_path = provenance or derived_dir / "provenance.json"
    lick_latency_path = lick_latency_svg or derived_dir / "lick_latency.svg"
    report_path = out_file or derived_dir / "report.html"

    if not analysis_path.exists():
        print(
            f"Allen Visual Behavior analysis result not found: {analysis_path}. "
            "Run `behavtaskatlas allen-visual-behavior-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        analysis = _read_json_object_file(analysis_path)
        provenance_payload_data = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else {}
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not lick_latency_path.exists():
        print(
            "Lick latency SVG not found at "
            f"{lick_latency_path}; report will reference a missing image."
        )

    write_change_detection_report_html(
        report_path,
        analysis=analysis,
        provenance=provenance_payload_data,
        image_pair_rows=list(analysis.get("image_pair_summary") or []),
    )

    print(f"Wrote Allen Visual Behavior report to {report_path}")
    return 0


def _allen_vbn_download(
    *,
    nwb_url: str,
    out_file: Path | None,
) -> int:
    target = out_file or DEFAULT_ALLEN_VBN_RAW_DIR / nwb_url.rsplit("/", 1)[-1]
    try:
        details = download_allen_visual_behavior_session(
            nwb_url=nwb_url,
            out_file=target,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        f"Downloaded {details['nwb_file_bytes']} bytes from {nwb_url} to "
        f"{details['nwb_file']}"
    )
    print(f"SHA256 {details['nwb_file_sha256']}")
    return 0


def _allen_vbn_harmonize(
    *,
    nwb_file: Path,
    out_dir: Path,
    limit: int | None,
) -> int:
    try:
        trials, details = load_allen_vbn_session(
            nwb_file=nwb_file,
            limit=limit,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    trials_path = out_dir / "trials.csv"
    outcome_path = out_dir / "outcome_summary.csv"
    provenance_path = out_dir / "provenance.json"

    write_allen_canonical_trials_csv(trials_path, trials)
    outcome_counts: dict[str, int] = {}
    for trial in trials:
        outcome = str(trial.task_variables.get("outcome", "unknown"))
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    write_outcome_summary_csv(outcome_path, outcome_counts)
    write_provenance_json(
        provenance_path,
        allen_vbn_provenance_payload(
            details=details,
            output_files={
                "trials": str(trials_path),
                "outcome_summary": str(outcome_path),
                "provenance": str(provenance_path),
            },
            trials=trials,
        ),
    )

    print(f"Wrote {len(trials)} VBN trials to {trials_path}")
    print(f"Wrote outcome summary to {outcome_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _allen_vbn_analyze(
    *,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    trials_path = trials_csv or derived_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical VBN trials CSV not found: {trials_path}. "
            "Run `uv run --extra allen behavtaskatlas allen-vbn-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_allen_vbn_change_detection(trials)

    image_pair_path = derived_dir / "image_pair_summary.csv"
    result_path = derived_dir / "analysis_result.json"
    plot_path = derived_dir / "lick_latency.svg"

    write_image_pair_csv(image_pair_path, result["image_pair_summary"])
    write_allen_analysis_json(result_path, result)
    write_lick_latency_svg(
        plot_path,
        trials,
        title="VBN hit lick latency (seconds after change)",
    )

    print(f"Analyzed {len(trials)} VBN trials from {trials_path}")
    print(f"Wrote image pair summary to {image_pair_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote lick latency plot to {plot_path}")
    return 0


def _allen_vbn_report(
    *,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    lick_latency_svg: Path | None,
    out_file: Path | None,
) -> int:
    analysis_path = analysis_result or derived_dir / "analysis_result.json"
    provenance_path = provenance or derived_dir / "provenance.json"
    lick_latency_path = lick_latency_svg or derived_dir / "lick_latency.svg"
    report_path = out_file or derived_dir / "report.html"

    if not analysis_path.exists():
        print(
            f"Allen Visual Behavior Neuropixels analysis result not found: {analysis_path}. "
            "Run `behavtaskatlas allen-vbn-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        analysis = _read_json_object_file(analysis_path)
        provenance_payload_data = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else {}
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not lick_latency_path.exists():
        print(
            "VBN lick latency SVG not found at "
            f"{lick_latency_path}; report will reference a missing image."
        )

    write_change_detection_report_html(
        report_path,
        analysis=analysis,
        provenance=provenance_payload_data,
        image_pair_rows=list(analysis.get("image_pair_summary") or []),
    )

    print(f"Wrote Allen Visual Behavior Neuropixels report to {report_path}")
    return 0


def _clicks_harmonize(
    *,
    mat_file: Path,
    out_dir: Path,
    parsed_field: str,
    limit: int | None,
) -> int:
    if not mat_file.exists():
        print(f"MATLAB file not found: {mat_file}", file=sys.stderr)
        return 2
    try:
        trials, details = load_brody_clicks_mat(
            mat_file,
            parsed_field=parsed_field,
            limit=limit,
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    outputs = _write_clicks_harmonization_outputs(
        trials=trials,
        details=details,
        mat_file=mat_file,
        out_dir=out_dir,
        parsed_field=parsed_field,
    )

    print(f"Wrote {len(trials)} trials to {outputs['trials_path']}")
    print(f"Wrote {len(outputs['summary_rows'])} summary rows to {outputs['summary_path']}")
    print(f"Wrote provenance to {outputs['provenance_path']}")
    return 0


def _clicks_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
    kernel_bins: int,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra clicks behavtaskatlas clicks-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    try:
        outputs = _write_clicks_analysis_outputs(
            trials=trials,
            session_dir=session_dir,
            kernel_bins=kernel_bins,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {outputs['psychometric_summary_path']}")
    print(f"Wrote analysis result to {outputs['analysis_result_path']}")
    print(f"Wrote psychometric plot to {outputs['psychometric_plot_path']}")
    print(f"Wrote evidence-kernel summary to {outputs['evidence_kernel_summary_path']}")
    print(f"Wrote evidence-kernel result to {outputs['evidence_kernel_result_path']}")
    print(f"Wrote evidence-kernel plot to {outputs['evidence_kernel_plot_path']}")
    return 0


def _clicks_batch(
    *,
    mat_files: list[Path] | None,
    mat_dir: Path | None,
    out_dir: Path,
    parsed_field: str,
    limit: int | None,
    kernel_bins: int,
    max_files: int | None,
    fail_fast: bool,
) -> int:
    try:
        paths = _clicks_batch_mat_files(mat_files=mat_files, mat_dir=mat_dir, max_files=max_files)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not paths:
        print("No `.mat` files found for clicks batch.", file=sys.stderr)
        return 2

    rows = []
    n_failed = 0
    for mat_file in paths:
        row = _clicks_batch_row_template(mat_file=mat_file, parsed_field=parsed_field)
        try:
            trials, details = load_brody_clicks_mat(
                mat_file,
                parsed_field=parsed_field,
                limit=limit,
            )
            harmonization_outputs = _write_clicks_harmonization_outputs(
                trials=trials,
                details=details,
                mat_file=mat_file,
                out_dir=out_dir,
                parsed_field=parsed_field,
            )
            analysis_outputs = _write_clicks_analysis_outputs(
                trials=trials,
                session_dir=harmonization_outputs["session_dir"],
                kernel_bins=kernel_bins,
            )
            psychometric_contexts = sorted(
                {
                    row["prior_context"]
                    for row in analysis_outputs["psychometric_result"]["summary_rows"]
                    if row["prior_context"]
                }
            )
            row.update(
                {
                    "session_id": harmonization_outputs["session_id"],
                    "subject_id": details.get("subject_id"),
                    "task_type": details.get("task_type"),
                    "status": "ok",
                    "n_trials": len(trials),
                    "harmonization_summary_rows": len(harmonization_outputs["summary_rows"]),
                    "psychometric_summary_rows": len(
                        analysis_outputs["psychometric_result"]["summary_rows"]
                    ),
                    "psychometric_prior_contexts": ";".join(psychometric_contexts),
                    "evidence_kernel_rows": len(
                        analysis_outputs["evidence_kernel_result"]["summary_rows"]
                    ),
                    "evidence_kernel_analyzed_trials": analysis_outputs[
                        "evidence_kernel_result"
                    ]["n_analyzed_trials"],
                    "evidence_kernel_excluded_trials": analysis_outputs[
                        "evidence_kernel_result"
                    ]["n_excluded_trials"],
                    "source_file_sha256": details.get("source_file_sha256"),
                    "output_dir": str(harmonization_outputs["session_dir"]),
                }
            )
            print(f"OK {mat_file}: {len(trials)} trials")
        except Exception as exc:
            n_failed += 1
            row.update({"status": "error", "error": str(exc)})
            print(f"ERROR {mat_file}: {exc}", file=sys.stderr)
            rows.append(row)
            if fail_fast:
                break
            continue
        rows.append(row)

    summary_path = out_dir / "batch_summary.csv"
    write_clicks_batch_summary_csv(summary_path, rows)
    print(f"Wrote batch summary to {summary_path}")
    print(f"Processed {len(rows)} files: {len(rows) - n_failed} ok, {n_failed} failed")
    return 1 if n_failed else 0


def _clicks_aggregate(*, derived_dir: Path, batch_summary: Path | None) -> int:
    batch_summary_path = batch_summary or derived_dir / "batch_summary.csv"
    if not batch_summary_path.exists():
        print(
            f"Clicks batch summary not found: {batch_summary_path}. "
            "Run `uv run behavtaskatlas clicks-batch` first.",
            file=sys.stderr,
        )
        return 2

    try:
        result = aggregate_brody_clicks_batch(batch_summary_path)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output_dir = derived_dir
    psychometric_path = output_dir / "aggregate_psychometric_bias.csv"
    kernel_summary_path = output_dir / "aggregate_kernel_summary.csv"
    result_path = output_dir / "aggregate_result.json"
    kernel_plot_path = output_dir / "aggregate_kernel.svg"
    trials_path = output_dir / "trials.csv"
    provenance_path = output_dir / "provenance.json"

    write_aggregate_psychometric_bias_csv(
        psychometric_path,
        result["psychometric_bias_rows"],
    )
    write_aggregate_kernel_summary_csv(kernel_summary_path, result["kernel_summary_rows"])
    write_analysis_json(result_path, result)
    write_aggregate_kernel_svg(kernel_plot_path, result["kernel_summary_rows"])
    trials_summary = concatenate_brody_clicks_trials(batch_summary_path, trials_path)
    write_provenance_json(
        provenance_path,
        brody_clicks_aggregate_provenance_payload(
            result=result,
            batch_summary_path=batch_summary_path,
            output_files={
                "aggregate_psychometric_bias": str(psychometric_path),
                "aggregate_kernel_summary": str(kernel_summary_path),
                "aggregate_result": str(result_path),
                "aggregate_kernel": str(kernel_plot_path),
                "trials": str(trials_path),
                "provenance": str(provenance_path),
            },
            trials_summary=trials_summary,
        ),
    )

    print(f"Aggregated {result['n_ok']} ok batch rows from {batch_summary_path}")
    print(f"Wrote aggregate psychometric bias table to {psychometric_path}")
    print(f"Wrote aggregate kernel summary to {kernel_summary_path}")
    print(f"Wrote aggregate result to {result_path}")
    print(f"Wrote aggregate kernel plot to {kernel_plot_path}")
    print(
        f"Wrote concatenated trials ({trials_summary['n_rows']} rows from "
        f"{trials_summary['n_subjects']} subjects) to {trials_path}"
    )
    if trials_summary["missing_paths"]:
        print(
            f"Note: {len(trials_summary['missing_paths'])} per-rat trials.csv "
            "were missing from output dirs; concatenation skipped them."
        )
    print(f"Wrote aggregate provenance to {provenance_path}")
    if result["n_artifact_errors"]:
        print(f"Encountered {result['n_artifact_errors']} aggregate artifact errors")
        return 1
    return 0


def _clicks_aggregate_trials(
    *,
    derived_dir: Path,
    batch_summary: Path | None,
    out_file: Path | None,
) -> int:
    batch_summary_path = batch_summary or derived_dir / "batch_summary.csv"
    if not batch_summary_path.exists():
        print(
            f"Clicks batch summary not found: {batch_summary_path}. "
            "Run `uv run behavtaskatlas clicks-batch` first.",
            file=sys.stderr,
        )
        return 2
    out_path = out_file or derived_dir / "trials.csv"
    try:
        summary = concatenate_brody_clicks_trials(batch_summary_path, out_path)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        f"Wrote {summary['n_rows']} trials from {summary['n_subjects']} "
        f"subjects to {out_path}"
    )
    if summary["missing_paths"]:
        print(
            f"Note: {len(summary['missing_paths'])} per-rat trials.csv were "
            "missing from output dirs; concatenation skipped them.",
            file=sys.stderr,
        )
    return 0


def _clicks_report(
    *,
    derived_dir: Path,
    aggregate_result: Path | None,
    aggregate_kernel_svg: Path | None,
    out_file: Path | None,
) -> int:
    result_path = aggregate_result or derived_dir / "aggregate_result.json"
    kernel_svg_path = aggregate_kernel_svg or derived_dir / "aggregate_kernel.svg"
    provenance_path = derived_dir / "provenance.json"
    report_path = out_file or derived_dir / "report.html"
    if not result_path.exists():
        print(
            f"Clicks aggregate result not found: {result_path}. "
            "Run `uv run behavtaskatlas clicks-aggregate` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not isinstance(loaded, dict):
        print(f"Expected JSON object in {result_path}", file=sys.stderr)
        return 2

    kernel_svg_text = None
    if kernel_svg_path.exists():
        kernel_svg_text = kernel_svg_path.read_text(encoding="utf-8")

    report_dir = report_path.parent
    artifact_links = {
        "aggregate result JSON": _relative_artifact_link(result_path, report_dir),
        "aggregate psychometric bias CSV": _relative_artifact_link(
            derived_dir / "aggregate_psychometric_bias.csv",
            report_dir,
        ),
        "aggregate kernel summary CSV": _relative_artifact_link(
            derived_dir / "aggregate_kernel_summary.csv",
            report_dir,
        ),
        "aggregate kernel SVG": _relative_artifact_link(kernel_svg_path, report_dir),
        "aggregate provenance JSON": _relative_artifact_link(provenance_path, report_dir),
        "batch summary CSV": _relative_artifact_link(
            derived_dir / "batch_summary.csv",
            report_dir,
        ),
    }
    write_clicks_aggregate_report_html(
        report_path,
        loaded,
        aggregate_kernel_svg_text=kernel_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote clicks aggregate report to {report_path}")
    if kernel_svg_text is None:
        print(
            "Aggregate kernel SVG not found, wrote report without inline plot: "
            f"{kernel_svg_path}"
        )
    return 0


def _human_clicks_download(*, out_file: Path) -> int:
    try:
        details = download_human_clicks_mendeley_mat(out_file)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded {details['n_bytes']} bytes to {out_file}")
    print(f"SHA256 {details['sha256']}")
    return 0


def _human_clicks_harmonize(
    *,
    mat_file: Path,
    out_dir: Path,
    session_id: str,
    limit: int | None,
) -> int:
    if not mat_file.exists():
        print(
            f"Human clicks MATLAB file not found: {mat_file}. "
            "Run `uv run --extra clicks behavtaskatlas human-clicks-download` first.",
            file=sys.stderr,
        )
        return 2
    try:
        trials, details = load_human_clicks_mendeley_mat(
            mat_file,
            session_id=session_id,
            limit=limit,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        human_clicks_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _human_clicks_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
    kernel_bins: int,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra clicks behavtaskatlas human-clicks-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    try:
        result = analyze_human_clicks(trials)
        kernel_result = analyze_human_clicks_evidence_kernel(trials, n_bins=kernel_bins)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"
    kernel_summary_path = session_dir / "evidence_kernel_summary.csv"
    kernel_result_path = session_dir / "evidence_kernel_result.json"
    kernel_plot_path = session_dir / "evidence_kernel.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        plot_path,
        result["summary_rows"],
        x_axis_label=HUMAN_CLICKS_PSYCHOMETRIC_X_AXIS_LABEL,
    )
    write_evidence_kernel_summary_csv(kernel_summary_path, kernel_result["summary_rows"])
    write_analysis_json(kernel_result_path, kernel_result)
    write_evidence_kernel_svg(kernel_plot_path, kernel_result["summary_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    print(f"Wrote evidence-kernel summary to {kernel_summary_path}")
    print(f"Wrote evidence-kernel result to {kernel_result_path}")
    print(f"Wrote evidence-kernel plot to {kernel_plot_path}")
    return 0


def _human_clicks_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    kernel_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    evidence_kernel_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    kernel_path = kernel_result or session_dir / "evidence_kernel_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or session_dir / "psychometric.svg"
    evidence_kernel_svg_path = evidence_kernel_svg or session_dir / "evidence_kernel.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Human clicks analysis result not found: {analysis_path}. "
            "Run `uv run --extra clicks behavtaskatlas human-clicks-analyze` first.",
            file=sys.stderr,
        )
        return 2

    try:
        loaded = _read_json_object_file(analysis_path)
        loaded_kernel = _read_json_object_file(kernel_path) if kernel_path.exists() else None
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = (
        psychometric_svg_path.read_text(encoding="utf-8")
        if psychometric_svg_path.exists()
        else None
    )
    evidence_kernel_svg_text = (
        evidence_kernel_svg_path.read_text(encoding="utf-8")
        if evidence_kernel_svg_path.exists()
        else None
    )
    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("evidence-kernel result JSON", kernel_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", session_dir / "psychometric_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("evidence-kernel summary CSV", session_dir / "evidence_kernel_summary.csv"),
            ("evidence-kernel SVG", evidence_kernel_svg_path),
            ("canonical trials CSV", session_dir / "trials.csv"),
        ]
        if path.exists()
    }
    write_clicks_session_report_html(
        report_path,
        loaded,
        kernel_result=loaded_kernel,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        evidence_kernel_svg_text=evidence_kernel_svg_text,
        artifact_links=artifact_links,
    )
    print(f"Wrote human clicks report to {report_path}")
    return 0


def _rdm_download(*, out_file: Path) -> int:
    try:
        details = download_roitman_rdm_csv(out_file)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded {details['n_bytes']} bytes to {out_file}")
    print(f"SHA256 {details['sha256']}")
    return 0


def _human_rdm_download(*, out_dir: Path, subjects: list[str] | None) -> int:
    try:
        details = download_human_rdm_phs_files(out_dir, subjects=subjects)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded {details['n_files']} files ({details['n_bytes']} bytes) to {out_dir}")
    for file in details["files"]:
        print(f"SHA256 {file['file_name']} {file['sha256']}")
    return 0


def _rdm_harmonize(
    *,
    csv_file: Path,
    out_dir: Path,
    session_id: str,
    monkey: int | None,
    limit: int | None,
) -> int:
    if not csv_file.exists():
        print(
            f"RDM CSV not found: {csv_file}. Run `uv run behavtaskatlas rdm-download` first.",
            file=sys.stderr,
        )
        return 2
    try:
        trials, details = load_roitman_rdm_csv(
            csv_file,
            session_id=session_id,
            monkey=monkey,
            limit=limit,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        rdm_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _human_rdm_harmonize(
    *,
    raw_dir: Path,
    out_dir: Path,
    session_id: str,
    subjects: list[str] | None,
    limit: int | None,
) -> int:
    try:
        trials, details = load_human_rdm_phs_mats(
            raw_dir,
            session_id=session_id,
            subjects=subjects,
            limit=limit,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        human_rdm_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} trials to {trials_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _rdm_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas rdm-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_roitman_rdm(trials)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"
    chronometric_path = session_dir / "chronometric_summary.csv"
    chronometric_plot_path = session_dir / "chronometric.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        plot_path,
        result["summary_rows"],
        x_axis_label=RDM_PSYCHOMETRIC_X_AXIS_LABEL,
    )
    write_rdm_chronometric_csv(chronometric_path, result["chronometric_rows"])
    write_rdm_chronometric_svg(chronometric_plot_path, result["chronometric_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    print(f"Wrote chronometric summary to {chronometric_path}")
    print(f"Wrote chronometric plot to {chronometric_plot_path}")
    return 0


def _human_rdm_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical trials CSV not found: {trials_path}. "
            "Run `uv run --extra rdm behavtaskatlas human-rdm-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_human_rdm(trials)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"
    chronometric_path = session_dir / "chronometric_summary.csv"
    chronometric_plot_path = session_dir / "chronometric.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        plot_path,
        result["summary_rows"],
        x_axis_label=HUMAN_RDM_PSYCHOMETRIC_X_AXIS_LABEL,
    )
    write_rdm_chronometric_csv(chronometric_path, result["chronometric_rows"])
    write_rdm_chronometric_svg(chronometric_plot_path, result["chronometric_rows"])

    print(f"Analyzed {len(trials)} trials from {trials_path}")
    print(f"Wrote psychometric summary to {summary_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote psychometric plot to {plot_path}")
    print(f"Wrote chronometric summary to {chronometric_path}")
    print(f"Wrote chronometric plot to {chronometric_plot_path}")
    return 0


def _macaque_rdm_confidence_download(*, out_file: Path) -> int:
    try:
        details = download_macaque_rdm_confidence_source_data(out_file)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Downloaded {details['n_bytes']} bytes to {out_file}")
    print(f"SHA256 {details['sha256']}")
    return 0


def _macaque_rdm_confidence_intake_check(
    *,
    raw_dir: Path,
    redistribution_status: Path | None,
    out_file: Path | None,
) -> int:
    report = check_macaque_rdm_confidence_raw_behavior_intake(
        raw_dir,
        redistribution_status_file=redistribution_status,
    )
    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote intake report to {out_file}")
    print(format_macaque_rdm_confidence_raw_behavior_intake_report(report))
    return 0 if report["overall_status"] == "ready" else 2


def _macaque_rdm_confidence_harmonize(
    *,
    source_zip: Path,
    out_dir: Path,
    session_id: str,
    limit: int | None,
) -> int:
    try:
        trials, details = load_macaque_rdm_confidence_source_data(
            source_zip,
            session_id=session_id,
            limit=limit,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"
    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        macaque_rdm_confidence_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )

    print(f"Wrote {len(trials)} source rows to {trials_path}")
    print(f"Wrote {len(summary)} generic summary rows to {summary_path}")
    print(f"Wrote provenance to {provenance_path}")
    return 0


def _macaque_rdm_confidence_raw_harmonize(
    *,
    raw_dir: Path,
    redistribution_status: Path | None,
    out_dir: Path,
    session_id: str,
    limit: int | None,
) -> int:
    try:
        load_macaque_rdm_confidence_raw_behavior_mats(
            raw_dir,
            redistribution_status_file=redistribution_status,
            session_id=session_id,
            limit=limit,
        )
    except (FileNotFoundError, NotImplementedError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        print(
            "No raw-trial files were written. Future outputs will be rooted at "
            f"{out_dir / session_id}.",
            file=sys.stderr,
        )
        return 2
    return 0


def _macaque_rdm_confidence_analyze(
    *,
    session_id: str,
    derived_dir: Path,
    trials_csv: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    trials_path = trials_csv or session_dir / "trials.csv"
    if not trials_path.exists():
        print(
            f"Canonical source-row CSV not found: {trials_path}. "
            "Run `uv run behavtaskatlas macaque-rdm-confidence-harmonize` first.",
            file=sys.stderr,
        )
        return 2

    trials = load_canonical_trials_csv(trials_path)
    result = analyze_macaque_rdm_confidence(trials)

    result_path = session_dir / "analysis_result.json"
    accuracy_summary_path = session_dir / "accuracy_summary.csv"
    confidence_summary_path = session_dir / "confidence_summary.csv"
    accuracy_plot_path = session_dir / "accuracy.svg"
    confidence_plot_path = session_dir / "confidence.svg"

    write_analysis_json(result_path, result)
    write_macaque_rdm_confidence_accuracy_csv(accuracy_summary_path, result["accuracy_rows"])
    write_macaque_rdm_confidence_choice_csv(confidence_summary_path, result["confidence_rows"])
    write_macaque_rdm_confidence_accuracy_svg(accuracy_plot_path, result["accuracy_rows"])
    write_macaque_rdm_confidence_choice_svg(confidence_plot_path, result["confidence_rows"])

    print(f"Analyzed {len(trials)} source rows from {trials_path}")
    print(f"Wrote analysis result to {result_path}")
    print(f"Wrote accuracy summary to {accuracy_summary_path}")
    print(f"Wrote confidence summary to {confidence_summary_path}")
    print(f"Wrote accuracy plot to {accuracy_plot_path}")
    print(f"Wrote confidence plot to {confidence_plot_path}")
    return 0


def _macaque_rdm_confidence_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    accuracy_svg: Path | None,
    confidence_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    accuracy_svg_path = accuracy_svg or session_dir / "accuracy.svg"
    confidence_svg_path = confidence_svg or session_dir / "confidence.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"Macaque RDM confidence analysis result not found: {analysis_path}. "
            "Run `uv run behavtaskatlas macaque-rdm-confidence-analyze` first.",
            file=sys.stderr,
        )
        return 2
    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    accuracy_svg_text = (
        accuracy_svg_path.read_text(encoding="utf-8") if accuracy_svg_path.exists() else None
    )
    confidence_svg_text = (
        confidence_svg_path.read_text(encoding="utf-8")
        if confidence_svg_path.exists()
        else None
    )
    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("accuracy summary CSV", session_dir / "accuracy_summary.csv"),
            ("confidence summary CSV", session_dir / "confidence_summary.csv"),
            ("accuracy SVG", accuracy_svg_path),
            ("confidence SVG", confidence_svg_path),
            ("canonical source-row CSV", session_dir / "trials.csv"),
            ("generic harmonization summary CSV", session_dir / "summary.csv"),
        ]
        if path.exists()
    }
    write_macaque_rdm_confidence_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        accuracy_svg_text=accuracy_svg_text,
        confidence_svg_text=confidence_svg_text,
        artifact_links=artifact_links,
    )

    print(f"Wrote macaque RDM confidence report to {report_path}")
    return 0


def _rdm_report(
    *,
    session_id: str,
    derived_dir: Path,
    analysis_result: Path | None,
    provenance: Path | None,
    psychometric_svg: Path | None,
    chronometric_svg: Path | None,
    out_file: Path | None,
) -> int:
    session_dir = derived_dir / session_id
    analysis_path = analysis_result or session_dir / "analysis_result.json"
    provenance_path = provenance or session_dir / "provenance.json"
    psychometric_svg_path = psychometric_svg or session_dir / "psychometric.svg"
    chronometric_svg_path = chronometric_svg or session_dir / "chronometric.svg"
    report_path = out_file or session_dir / "report.html"
    if not analysis_path.exists():
        print(
            f"RDM analysis result not found: {analysis_path}. "
            "Run the matching RDM analyze command first.",
            file=sys.stderr,
        )
        return 2
    try:
        loaded = _read_json_object_file(analysis_path)
        provenance_payload = (
            _read_json_object_file(provenance_path) if provenance_path.exists() else None
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    psychometric_svg_text = (
        psychometric_svg_path.read_text(encoding="utf-8")
        if psychometric_svg_path.exists()
        else None
    )
    chronometric_svg_text = (
        chronometric_svg_path.read_text(encoding="utf-8")
        if chronometric_svg_path.exists()
        else None
    )
    report_dir = report_path.parent
    artifact_links = {
        label: _relative_artifact_link(path, report_dir)
        for label, path in [
            ("analysis result JSON", analysis_path),
            ("provenance JSON", provenance_path),
            ("psychometric summary CSV", session_dir / "psychometric_summary.csv"),
            ("psychometric SVG", psychometric_svg_path),
            ("chronometric summary CSV", session_dir / "chronometric_summary.csv"),
            ("chronometric SVG", chronometric_svg_path),
            ("canonical trials CSV", session_dir / "trials.csv"),
        ]
        if path.exists()
    }
    write_rdm_report_html(
        report_path,
        loaded,
        provenance=provenance_payload,
        psychometric_svg_text=psychometric_svg_text,
        chronometric_svg_text=chronometric_svg_text,
        artifact_links=artifact_links,
    )
    print(f"Wrote random-dot motion report to {report_path}")
    return 0


def _extract_finding(
    *,
    slice_id: str,
    paper_id: str,
    finding_id_prefix: str,
    curve_type: str,
    by_subject: bool = False,
    by_subject_condition: str | None = None,
    condition_values: tuple[str, ...] | None = None,
    x_label: str | None,
    x_units: str | None,
    summary_filename: str | None,
    condition_column: str | None,
    y_column: str | None,
    y_label: str | None,
    n_column: str | None,
    derived_dir: Path,
) -> int:
    from behavtaskatlas.models import VerticalSlice

    records = load_repository_records(Path("."))
    slice_record = next(
        (
            r
            for r in records
            if isinstance(r, VerticalSlice) and r.id == slice_id
        ),
        None,
    )
    if slice_record is None:
        print(f"Unknown slice id: {slice_id!r}", file=sys.stderr)
        return 2

    by_subject_active = by_subject or by_subject_condition is not None
    if by_subject_active and curve_type not in {"psychometric", "chronometric"}:
        print(
            f"--by-subject / --by-subject-condition is only supported for "
            f"curve_type=psychometric or chronometric; got {curve_type!r}.",
            file=sys.stderr,
        )
        return 2
    if condition_values is not None and by_subject_condition is None:
        print(
            "--condition-value requires --by-subject-condition.",
            file=sys.stderr,
        )
        return 2

    extractor_kwargs: dict[str, Any] = {
        "paper_id": paper_id,
        "derived_dir": derived_dir,
        "finding_id_prefix": finding_id_prefix,
    }
    if x_label is not None:
        extractor_kwargs["x_label"] = x_label
    if x_units is not None:
        extractor_kwargs["x_units"] = x_units
    if summary_filename is not None:
        extractor_kwargs["summary_filename"] = summary_filename
    if condition_column is not None:
        extractor_kwargs["condition_column"] = condition_column
    if y_column is not None:
        extractor_kwargs["y_column"] = y_column
    if y_label is not None:
        extractor_kwargs["y_label"] = y_label
    if n_column is not None:
        extractor_kwargs["n_column"] = n_column

    try:
        if curve_type == "psychometric":
            extractor_kwargs.setdefault("x_label", "Signed evidence")
            extractor_kwargs.setdefault("x_units", "")
            if by_subject_condition is not None:
                for key in (
                    "summary_filename",
                    "condition_column",
                    "y_column",
                    "y_label",
                    "n_column",
                ):
                    extractor_kwargs.pop(key, None)
                findings = extract_subject_condition_psychometric_findings_for_slice(
                    slice_record,
                    condition_column=by_subject_condition,
                    condition_values=condition_values,
                    **extractor_kwargs,
                )
            elif by_subject:
                for key in (
                    "summary_filename",
                    "condition_column",
                    "y_column",
                    "y_label",
                    "n_column",
                ):
                    extractor_kwargs.pop(key, None)
                findings = extract_subject_psychometric_findings_for_slice(
                    slice_record, **extractor_kwargs
                )
            else:
                findings = extract_psychometric_findings_for_slice(
                    slice_record, **extractor_kwargs
                )
        elif curve_type == "chronometric":
            if by_subject_condition is not None:
                findings = extract_subject_chronometric_findings_for_slice(
                    slice_record,
                    condition_column=by_subject_condition,
                    condition_values=condition_values,
                    **extractor_kwargs,
                )
            elif by_subject:
                findings = extract_subject_chronometric_findings_for_slice(
                    slice_record, **extractor_kwargs
                )
            else:
                findings = extract_chronometric_findings_for_slice(
                    slice_record, **extractor_kwargs
                )
        elif curve_type == "accuracy_by_strength":
            findings = extract_accuracy_findings_for_slice(
                slice_record, **extractor_kwargs
            )
        else:
            print(f"Unsupported curve_type: {curve_type!r}", file=sys.stderr)
            return 2
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not findings:
        print(
            f"No points extracted from {slice_id!r} ({curve_type}); "
            "summary CSV may be empty.",
            file=sys.stderr,
        )
        return 2

    for finding in findings:
        path = write_finding_yaml(finding)
        print(f"Wrote {path} ({len(finding.curve.points)} points)")
    return 0


def _import_supplement(
    *,
    csv_path: Path,
    mapping_path: Path,
) -> int:
    try:
        mapping = load_import_mapping(mapping_path)
    except (OSError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not isinstance(mapping, dict):
        print(f"Mapping {mapping_path} must be a YAML mapping", file=sys.stderr)
        return 2

    required = {
        "paper_id",
        "protocol_id",
        "source_data_level",
        "extraction_method",
        "curve_type",
        "x_label",
        "x_units",
        "y_label",
        "x_column",
        "y_column",
        "n_column",
        "finding_id_prefix",
    }
    missing = required - set(mapping.keys())
    if missing:
        joined = ", ".join(sorted(missing))
        print(f"Mapping is missing required keys: {joined}", file=sys.stderr)
        return 2

    groupby_columns = tuple(mapping.get("groupby_columns") or ())

    try:
        findings = import_csv_findings(
            csv_path=csv_path,
            paper_id=str(mapping["paper_id"]),
            protocol_id=str(mapping["protocol_id"]),
            dataset_id=str(mapping["dataset_id"]) if mapping.get("dataset_id") else None,
            source_data_level=str(mapping["source_data_level"]),
            extraction_method=str(mapping["extraction_method"]),
            curve_type=str(mapping["curve_type"]),
            x_label=str(mapping["x_label"]),
            x_units=str(mapping["x_units"]),
            y_label=str(mapping["y_label"]),
            x_column=str(mapping["x_column"]),
            y_column=str(mapping["y_column"]),
            n_column=str(mapping["n_column"]),
            groupby_columns=groupby_columns,
            finding_id_prefix=str(mapping["finding_id_prefix"]),
            extraction_notes=mapping.get("extraction_notes"),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not findings:
        print(f"No points extracted from {csv_path!s}", file=sys.stderr)
        return 2

    for finding in findings:
        path = write_finding_yaml(finding)
        print(f"Wrote {path} ({len(finding.curve.points)} points)")
    return 0


def _data_request_export(
    *,
    request_id: str | None,
    root: Path,
    out_dir: Path,
    stdout: bool,
) -> int:
    from behavtaskatlas.data_requests import (
        data_request_slug,
        render_data_request_markdown,
        write_data_request_markdown_exports,
    )
    from behavtaskatlas.models import DataRequest, Dataset, Paper

    records = load_repository_records(root)
    requests = [record for record in records if isinstance(record, DataRequest)]
    datasets = [record for record in records if isinstance(record, Dataset)]
    papers = [record for record in records if isinstance(record, Paper)]
    if request_id:
        requests = [
            request
            for request in requests
            if request.id == request_id or data_request_slug(request.id) == request_id
        ]
        if not requests:
            print(f"No data request matched {request_id!r}", file=sys.stderr)
            return 2

    if stdout:
        if len(requests) != 1:
            print(
                "--stdout requires exactly one selected data request",
                file=sys.stderr,
            )
            return 2
        print(render_data_request_markdown(requests[0], datasets=datasets, papers=papers))
        return 0

    written = write_data_request_markdown_exports(
        requests=requests,
        datasets=datasets,
        papers=papers,
        out_dir=out_dir,
    )
    if not written:
        print("No data requests to export", file=sys.stderr)
        return 2

    print(f"Wrote {len(written)} data request export(s) to {out_dir}")
    for path in written:
        print(f"  {path}")
    return 0


def _data_request_event(
    *,
    request_id: str,
    root: Path,
    event_type: str,
    event_date: str | None,
    actor: str,
    notes: str,
    status: str | None,
    evidence_url: str | None,
    evidence_path: Path | None,
    next_follow_up_date: str | None,
    create_evidence_stub: bool,
    force: bool,
) -> int:
    from behavtaskatlas.data_requests import append_data_request_event

    try:
        parsed_event_date = _parse_iso_date(
            event_date,
            field="event-date",
            default=date.today(),
        )
        parsed_follow_up_date = (
            _parse_iso_date(next_follow_up_date, field="next-follow-up-date")
            if next_follow_up_date
            else None
        )
        result = append_data_request_event(
            root=root,
            request_id=request_id,
            event_type=event_type,
            event_date=parsed_event_date,
            actor=actor,
            notes=notes,
            status=status,
            evidence_url=evidence_url,
            evidence_path=evidence_path,
            next_follow_up_date=parsed_follow_up_date,
            create_evidence_stub=create_evidence_stub,
            force=force,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        f"Updated {result['request_id']}: "
        f"{result['previous_status']} -> {result['status']}"
    )
    print(f"Appended {event_type} event to {result['path']}")
    if result.get("evidence_stub_path"):
        print(f"Wrote evidence stub to {result['evidence_stub_path']}")
    return 0


def _data_request_queue(
    *,
    root: Path,
    today: str | None,
    json_output: bool,
    out_file: Path | None,
) -> int:
    from behavtaskatlas.data_requests import build_data_requests_index
    from behavtaskatlas.models import DataRequest, Dataset, Paper

    try:
        queue_date = _parse_iso_date(today, field="today", default=date.today())
        records = load_repository_records(root)
        payload = build_data_requests_index(
            requests=[record for record in records if isinstance(record, DataRequest)],
            datasets=[record for record in records if isinstance(record, Dataset)],
            papers=[record for record in records if isinstance(record, Paper)],
            today=queue_date,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote data request queue to {out_file}")

    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(_format_data_request_queue(payload))
    return 0


def _format_data_request_queue(payload: dict[str, Any]) -> str:
    rows = list(payload.get("requests", []))
    lines = [
        f"Data request queue: {len(rows)} request(s)",
        "Action states: "
        + ", ".join(
            f"{state}={count}"
            for state, count in sorted(payload.get("action_state_counts", {}).items())
        ),
    ]
    if not rows:
        return "\n".join(lines)
    for row in sorted(
        rows,
        key=lambda item: (
            _data_request_action_sort_key(str(item.get("action_state") or "")),
            str(item.get("priority") or ""),
            str(item.get("request_id") or ""),
        ),
    ):
        lines.extend(
            [
                "",
                f"- {row['request_id']} [{row.get('action_state', 'unknown')}]",
                f"  status: {row.get('status')} priority: {row.get('priority')}",
                f"  action: {row.get('action_summary')}",
            ]
        )
        if row.get("next_follow_up_date"):
            lines.append(
                "  follow-up: "
                f"{row['next_follow_up_date']} "
                f"({row.get('days_until_follow_up')} day(s))"
            )
        if row.get("suggested_command"):
            lines.append(f"  command: {row['suggested_command']}")
    return "\n".join(lines)


def _data_request_action_sort_key(action_state: str) -> int:
    order = {
        "overdue": 0,
        "follow_up_due": 1,
        "ready_to_send": 2,
        "fulfilled_pending_intake": 3,
        "waiting": 4,
        "blocked": 5,
        "draft": 6,
        "closed": 7,
    }
    return order.get(action_state, 99)


def _parse_iso_date(value: str | None, *, field: str, default: date | None = None) -> date:
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"--{field} is required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"--{field} must use YYYY-MM-DD format: {value!r}") from exc


def _site_index(
    *,
    derived_dir: Path,
    manifest_file: Path | None,
    catalog_json_file: Path | None,
    graph_json_file: Path | None,
    curation_queue_json_file: Path | None,
) -> int:
    manifest_path = manifest_file or derived_dir / "manifest.json"
    catalog_json_path = catalog_json_file or derived_dir / "catalog.json"
    graph_json_path = graph_json_file or derived_dir / "graph.json"
    curation_queue_json_path = (
        curation_queue_json_file or derived_dir / "curation_queue.json"
    )
    # Synthesize HTML paths internally so build_*_payload can compute the
    # relative-link fields they emit into the JSON. These files are never
    # written; they exist only as URL anchors that downstream consumers can
    # resolve if they want HTML siblings, but the Astro frontend ignores them.
    index_path = derived_dir / "index.html"
    catalog_path = derived_dir / "catalog.html"
    graph_path = derived_dir / "graph.html"
    curation_queue_path = derived_dir / "curation_queue.html"
    catalog_payload = build_catalog_payload(
        root=Path("."),
        derived_dir=derived_dir,
        catalog_path=catalog_path,
        catalog_json_path=catalog_json_path,
        report_index_path=index_path,
        graph_path=graph_path,
        graph_json_path=graph_json_path,
        curation_queue_path=curation_queue_path,
    )
    graph_payload = build_relationship_graph_payload(
        catalog_payload,
        graph_path=graph_path,
        graph_json_path=graph_json_path,
        catalog_path=catalog_path,
        curation_queue_path=curation_queue_path,
    )
    curation_queue_payload = build_curation_queue_payload(
        graph_payload,
        queue_path=curation_queue_path,
        queue_json_path=curation_queue_json_path,
        graph_path=graph_path,
    )
    catalog_payload["health"]["curation_queue"] = curation_queue_payload["counts"]
    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=index_path,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        graph_path=graph_path,
        curation_queue_path=curation_queue_path,
        queue_counts=curation_queue_payload["counts"],
    )
    write_static_manifest_json(manifest_path, payload)
    write_static_catalog_json(catalog_json_path, catalog_payload)
    write_static_graph_json(graph_json_path, graph_payload)
    write_static_curation_queue_json(curation_queue_json_path, curation_queue_payload)

    findings_path = derived_dir / "findings.json"
    comparisons_path = derived_dir / "comparisons.json"
    records = load_repository_records(Path("."))
    from behavtaskatlas.models import (
        Comparison,
        DataRequest,
        Dataset,
        Finding,
        Paper,
        Protocol,
        TaskFamily,
        VerticalSlice,
    )
    from behavtaskatlas.models import ModelFit as _ModelFit
    from behavtaskatlas.models import ModelVariant as _ModelVariant
    paper_records = [r for r in records if isinstance(r, Paper)]
    finding_records = [r for r in records if isinstance(r, Finding)]
    protocol_records = [r for r in records if isinstance(r, Protocol)]
    dataset_records = [r for r in records if isinstance(r, Dataset)]
    slice_records = [r for r in records if isinstance(r, VerticalSlice)]
    findings_payload = build_findings_index(
        papers=paper_records,
        findings=finding_records,
        protocols=protocol_records,
        families=[r for r in records if isinstance(r, TaskFamily)],
        fits=[r for r in records if isinstance(r, _ModelFit)],
        variants=[r for r in records if isinstance(r, _ModelVariant)],
    )
    findings_path.parent.mkdir(parents=True, exist_ok=True)
    findings_path.write_text(
        json.dumps(findings_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    comparisons_payload = build_comparisons_index(
        comparisons=[r for r in records if isinstance(r, Comparison)],
    )
    comparisons_path.write_text(
        json.dumps(comparisons_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    from behavtaskatlas.citations import build_papers_index, write_citation_files
    from behavtaskatlas.search import build_search_index

    citations_dir = derived_dir / "citations"
    citation_counts = write_citation_files(paper_records, citations_dir)
    papers_index_path = derived_dir / "papers.json"
    papers_payload = build_papers_index(
        paper_records,
        findings=finding_records,
        protocols=protocol_records,
        datasets=dataset_records,
        slices=slice_records,
    )
    papers_index_path.write_text(
        json.dumps(papers_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    search_payload = build_search_index(
        papers=paper_records,
        families=[r for r in records if isinstance(r, TaskFamily)],
        protocols=protocol_records,
        datasets=dataset_records,
        slices=slice_records,
        findings=finding_records,
        comparisons=[r for r in records if isinstance(r, Comparison)],
    )
    search_path = derived_dir / "search.json"
    search_path.write_text(
        json.dumps(search_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    from behavtaskatlas.audit import audit_pooled_vs_by_subject

    audit_payload = audit_pooled_vs_by_subject(finding_records)
    audit_path = derived_dir / "audit.json"
    audit_path.write_text(
        json.dumps(audit_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    from behavtaskatlas.data_requests import (
        build_data_requests_index,
        write_data_request_markdown_exports,
    )

    data_request_records = [r for r in records if isinstance(r, DataRequest)]
    data_requests_payload = build_data_requests_index(
        requests=data_request_records,
        datasets=dataset_records,
        papers=paper_records,
    )
    data_requests_path = derived_dir / "data_requests.json"
    data_requests_path.write_text(
        json.dumps(data_requests_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    data_request_export_paths = write_data_request_markdown_exports(
        requests=data_request_records,
        datasets=dataset_records,
        papers=paper_records,
        out_dir=derived_dir / "data_requests",
        generated_at=str(data_requests_payload["generated_at"]),
    )

    from behavtaskatlas.model_layer import (
        build_models_index,
        write_model_selection_exports,
    )
    from behavtaskatlas.models import ModelFamily, ModelFit, ModelVariant

    models_payload = build_models_index(
        families=[r for r in records if isinstance(r, ModelFamily)],
        variants=[r for r in records if isinstance(r, ModelVariant)],
        fits=[r for r in records if isinstance(r, ModelFit)],
        slices=slice_records,
        derived_dir=derived_dir,
        findings=finding_records,
    )
    models_path = derived_dir / "models.json"
    models_path.write_text(
        json.dumps(models_payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    model_export_payload = write_model_selection_exports(
        derived_dir=derived_dir,
        models_payload=models_payload,
        findings_payload=findings_payload,
    )

    from behavtaskatlas.link_integrity import build_link_integrity_payload

    link_integrity_payload = build_link_integrity_payload(
        papers_payload=papers_payload,
        catalog_payload=catalog_payload,
        findings_payload=findings_payload,
        models_payload=models_payload,
        search_payload=search_payload,
        graph_payload=graph_payload,
        curation_queue_payload=curation_queue_payload,
        data_requests_payload=data_requests_payload,
    )
    link_integrity_path = derived_dir / "link_integrity.json"
    link_integrity_path.write_text(
        json.dumps(link_integrity_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    available = sum(1 for item in payload["slices"] if item.get("report_status") == "available")
    print(f"Wrote report manifest to {manifest_path}")
    print(f"Wrote catalog JSON to {catalog_json_path}")
    print(f"Wrote relationship graph JSON to {graph_json_path}")
    print(f"Wrote curation queue JSON to {curation_queue_json_path}")
    print(f"Wrote findings index to {findings_path}")
    print(f"Wrote comparisons index to {comparisons_path}")
    print(f"Wrote {citation_counts['files']} citation files to {citations_dir}")
    print(f"Wrote papers index to {papers_index_path}")
    print(
        f"Wrote search index ({search_payload['counts']['total']} entries) "
        f"to {search_path}"
    )
    print(
        f"Wrote audit report ({audit_payload['n_groups_audited']} groups, "
        f"{audit_payload['overall_status']}) to {audit_path}"
    )
    print(
        "Wrote data requests index "
        f"({data_requests_payload['counts']['requests']} requests) "
        f"to {data_requests_path}"
    )
    print(
        "Wrote data request Markdown exports "
        f"({len(data_request_export_paths)} requests) to {derived_dir / 'data_requests'}"
    )
    print(
        f"Wrote models index ({models_payload['counts']['families']} families, "
        f"{models_payload['counts']['variants']} variants, "
        f"{models_payload['counts']['fits']} fits) to {models_path}"
    )
    print(
        "Wrote model-selection CSV exports "
        f"({model_export_payload['model_selection']['rows']} winners, "
        f"{model_export_payload['model_selection_by_scope']['rows']} "
        "scope winners, "
        f"{model_export_payload['fits_by_finding']['rows']} fit rows, "
        f"{model_export_payload['model_roadmap']['rows']} roadmap rows)"
    )
    print(
        f"Wrote link-integrity report ({link_integrity_payload['overall_status']}, "
        f"{link_integrity_payload['counts']['checked_links']} links checked) "
        f"to {link_integrity_path}"
    )
    print(f"Indexed {len(payload['slices'])} vertical slices; {available} report available")
    n_findings = findings_payload["counts"]["findings"]
    n_papers = findings_payload["counts"]["papers"]
    n_finding_papers = findings_payload["counts"].get("finding_papers", n_papers)
    n_comparisons = comparisons_payload["counts"]["comparisons"]
    print(
        f"Indexed {n_findings} findings across {n_finding_papers} "
        f"finding-backed papers ({n_papers} curated papers)"
    )
    print(f"Indexed {n_comparisons} curated comparisons")
    return 0


def _release_check(
    *,
    root: Path,
    derived_dir: Path,
    out_file: Path | None,
    html_file: Path | None,
) -> int:
    root = root.resolve()
    derived_root = derived_dir if derived_dir.is_absolute() else root / derived_dir
    out_path = out_file or derived_root / "release_status.json"
    html_path = html_file or derived_root / "release_status.html"
    payload = build_release_check_payload(root=root, derived_dir=derived_dir)
    write_release_check_json(out_path, payload)
    write_release_check_html(html_path, payload)
    counts = payload["counts"]
    print(f"Wrote release status JSON to {out_path}")
    print(f"Wrote release status HTML to {html_path}")
    print(
        "Release check "
        f"{payload['overall_status']}: {counts.get('errors', 0)} error(s), "
        f"{counts.get('warnings', 0)} warning(s)"
    )
    return 1 if payload["overall_status"] == "error" else 0


def _audit_findings(*, tolerance: float, out_file: Path | None) -> int:
    from behavtaskatlas.audit import audit_pooled_vs_by_subject, format_audit_report
    from behavtaskatlas.models import Finding

    records = load_repository_records(Path("."))
    finding_records = [r for r in records if isinstance(r, Finding)]
    report = audit_pooled_vs_by_subject(finding_records, tolerance=tolerance)
    print(format_audit_report(report))
    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote audit report to {out_file}")
    if report["overall_status"] == "drift":
        return 1
    return 0


def _model_fit_id(variant_id: str, finding_id: str) -> str:
    variant_slug = variant_id.removeprefix("model_variant.")
    finding_slug = finding_id.removeprefix("finding.")
    return f"model_fit.{variant_slug}.{finding_slug}"


def _find_paired_chronometric(finding: Any, records: list[Any]) -> Any | None:
    """Find a chronometric Finding with the same paper_id and matching
    stratification (condition + subject_id) as the given psychometric
    finding. Returns None if not found."""
    from behavtaskatlas.models import Finding

    if finding.curve.curve_type != "psychometric":
        return None
    target_condition = finding.stratification.condition or ""
    target_subject = finding.stratification.subject_id or ""
    for r in records:
        if not isinstance(r, Finding):
            continue
        if r.curve.curve_type != "chronometric":
            continue
        if r.paper_id != finding.paper_id:
            continue
        cond = r.stratification.condition or ""
        subj = r.stratification.subject_id or ""
        if cond == target_condition and subj == target_subject:
            return r
    return None


def _model_fit_yaml_path(out_dir: Path, fit_id: str) -> Path:
    return out_dir / f"{fit_id.removeprefix('model_fit.')}.yaml"


def _do_fit_one(
    *,
    variant_id: str,
    finding_id: str,
    out_dir: Path,
    records: list[Any] | None = None,
) -> Path:
    import time

    from behavtaskatlas.ibl import current_git_commit, current_git_dirty
    from behavtaskatlas.model_fits import accuracy as accuracy_module
    from behavtaskatlas.model_fits import bernoulli as bernoulli_module
    from behavtaskatlas.model_fits import chronometric as chronometric_module
    from behavtaskatlas.model_fits import ddm as ddm_module
    from behavtaskatlas.model_fits import logistic as logistic_module
    from behavtaskatlas.model_fits import sdt as sdt_module
    from behavtaskatlas.models import (
        Finding,
        ModelFit,
        ModelVariant,
        ResultCurve,
    )

    if records is None:
        records = load_repository_records(Path("."))
    variant = next(
        (
            r
            for r in records
            if isinstance(r, ModelVariant) and r.id == variant_id
        ),
        None,
    )
    if variant is None:
        raise ValueError(f"Unknown ModelVariant id: {variant_id!r}")
    finding = next(
        (r for r in records if isinstance(r, Finding) and r.id == finding_id),
        None,
    )
    if finding is None:
        raise ValueError(f"Unknown Finding id: {finding_id!r}")

    paired_chronometric: Finding | None = None
    ddm_variants = (
        ddm_module.VARIANT_VANILLA,
        ddm_module.VARIANT_Z_BIAS,
        ddm_module.VARIANT_V_BIAS,
    )
    if variant_id in ddm_variants:
        paired_chronometric = _find_paired_chronometric(finding, records)

    from behavtaskatlas.model_fits import clicks as clicks_module
    fitter_by_variant = {
        accuracy_module.VARIANT_LOGISTIC_ID: lambda f: accuracy_module.fit(f),
        accuracy_module.VARIANT_RATE_NULL_ID: (
            lambda f: accuracy_module.fit_rate_null(f)
        ),
        bernoulli_module.VARIANT_RATE_ID: lambda f: bernoulli_module.fit(f),
        bernoulli_module.VARIANT_SATURATED_ID: (
            lambda f: bernoulli_module.fit_saturated(f)
        ),
        chronometric_module.VARIANT_HYPERBOLIC_ID: (
            lambda f: chronometric_module.fit(f)
        ),
        chronometric_module.VARIANT_CONSTANT_ID: (
            lambda f: chronometric_module.fit_constant(f)
        ),
        logistic_module.VARIANT_ID: lambda f: logistic_module.fit(f),
        sdt_module.VARIANT_ID: lambda f: sdt_module.fit(f),
        sdt_module.VARIANT_YES_NO_ID: lambda f: sdt_module.fit_yes_no(f),
        ddm_module.VARIANT_VANILLA: lambda f: ddm_module.fit(
            f, chronometric=paired_chronometric
        ),
        ddm_module.VARIANT_Z_BIAS: lambda f: ddm_module.fit_z_bias(
            f, chronometric=paired_chronometric
        ),
        ddm_module.VARIANT_V_BIAS: lambda f: ddm_module.fit_v_bias(
            f, chronometric=paired_chronometric
        ),
        clicks_module.VARIANT_LEAKY_ID: lambda f: clicks_module.fit(f),
        clicks_module.VARIANT_COUNT_LOGISTIC_ID: (
            lambda f: clicks_module.fit_count_logistic(f)
        ),
        clicks_module.VARIANT_CHOICE_RATE_NULL_ID: (
            lambda f: clicks_module.fit_choice_rate_null(f)
        ),
    }
    fitter = fitter_by_variant.get(variant_id)
    if fitter is None:
        raise ValueError(
            f"No registered fitter for variant {variant_id!r}."
        )

    started = time.time()
    result = fitter(finding)
    elapsed = time.time() - started

    fit_id = _model_fit_id(variant_id, finding_id)
    predictions_curve = ResultCurve(
        curve_type=finding.curve.curve_type,
        x_label=finding.curve.x_label,
        x_units=finding.curve.x_units,
        y_label=finding.curve.y_label,
        points=[
            {"x": p["x"], "n": p["n"], "y": p["y"]}
            for p in result["predictions"]
        ],
    )
    fit_method = {
        **result["fit_method"],
        "duration_seconds": float(elapsed),
    }
    finding_ids_for_record = [finding_id]
    if paired_chronometric is not None:
        finding_ids_for_record.append(paired_chronometric.id)
    fit_record = ModelFit(
        object_type="model_fit",
        schema_version="0.1.0",
        id=fit_id,
        variant_id=variant_id,
        finding_ids=finding_ids_for_record,
        parameters={k: float(v) for k, v in result["parameters"].items()},
        quality={k: float(v) for k, v in result["quality"].items()},
        predictions=predictions_curve,
        fit_method=fit_method,
        caveats=None,
        curation_status="data-linked",
        provenance={
            "curators": ["behavtaskatlas"],
            "created": date.today(),
            "updated": date.today(),
            "fit_commit": current_git_commit(),
            "fit_dirty": current_git_dirty(),
            "source_notes": (
                f"Fitted with {fit_method['type']} via "
                f"behavtaskatlas.model_fits.{variant_id.split('.', 1)[-1]}; "
                f"success={result['success']}; {result['message']}"
            ),
        },
    )

    out_path = _model_fit_yaml_path(out_dir, fit_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = fit_record.model_dump(mode="json", exclude_none=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return out_path


def _fit_model(*, variant_id: str, finding_id: str, out_dir: Path) -> int:
    try:
        path = _do_fit_one(
            variant_id=variant_id,
            finding_id=finding_id,
            out_dir=out_dir,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Wrote {path}")
    return 0


def _fit_stale_models(
    *,
    variant_filter: str | None,
    curve_types: tuple[str, ...],
    out_dir: Path,
) -> int:
    from behavtaskatlas.model_fits import accuracy as accuracy_module
    from behavtaskatlas.model_fits import bernoulli as bernoulli_module
    from behavtaskatlas.model_fits import chronometric as chronometric_module
    from behavtaskatlas.model_fits import ddm as ddm_module
    from behavtaskatlas.model_fits import logistic as logistic_module
    from behavtaskatlas.model_fits import sdt as sdt_module
    from behavtaskatlas.models import Finding, ModelFit, ModelVariant

    records = load_repository_records(Path("."))
    variants = [r for r in records if isinstance(r, ModelVariant)]
    findings = [r for r in records if isinstance(r, Finding)]
    existing_fits = {
        (r.variant_id, fid)
        for r in records
        if isinstance(r, ModelFit)
        for fid in r.finding_ids
    }

    ddm_variants_set = {
        ddm_module.VARIANT_VANILLA,
        ddm_module.VARIANT_Z_BIAS,
        ddm_module.VARIANT_V_BIAS,
    }
    from behavtaskatlas.model_fits import clicks as clicks_module
    fitter_variants = {
        *accuracy_module.ACCURACY_SUMMARY_VARIANT_IDS,
        *bernoulli_module.CONDITION_RATE_VARIANT_IDS,
        *chronometric_module.CHRONOMETRIC_SUMMARY_VARIANT_IDS,
        logistic_module.VARIANT_ID,
        sdt_module.VARIANT_ID,
        sdt_module.VARIANT_YES_NO_ID,
        *ddm_variants_set,
        *clicks_module.CLICK_SUMMARY_VARIANT_IDS,
    }
    if variant_filter is not None:
        fitter_variants = {variant_filter}
    eligible = [v for v in variants if v.id in fitter_variants]

    n_fitted = 0
    n_skipped = 0
    n_failed = 0
    for variant in eligible:
        for finding in findings:
            if finding.curve.curve_type not in curve_types:
                continue
            if (variant.id, finding.id) in existing_fits:
                n_skipped += 1
                continue
            # DDM anchors on psychometric findings only; chronometric is
            # picked up as the paired finding inside _do_fit_one.
            if (
                variant.id in ddm_variants_set
                and finding.curve.curve_type != "psychometric"
            ):
                continue
            if (
                variant.id in chronometric_module.CHRONOMETRIC_SUMMARY_VARIANT_IDS
                and finding.curve.curve_type != "chronometric"
            ):
                continue
            if (
                variant.id in accuracy_module.ACCURACY_SUMMARY_VARIANT_IDS
                and finding.curve.curve_type != "accuracy_by_strength"
            ):
                continue
            if (
                variant.id in bernoulli_module.CONDITION_RATE_VARIANT_IDS
                and finding.curve.curve_type != "hit_rate_by_condition"
            ):
                continue
            if (
                variant.id == bernoulli_module.VARIANT_SATURATED_ID
                and {float(p.x) for p in finding.curve.points} == {0.0, 1.0}
            ):
                continue
            if variant.id == sdt_module.VARIANT_YES_NO_ID and (
                finding.curve.curve_type != "hit_rate_by_condition"
                or {float(p.x) for p in finding.curve.points} != {0.0, 1.0}
            ):
                continue
            if variant.id in ddm_variants_set and (
                _find_paired_chronometric(finding, records) is None
            ):
                continue
            # Click-summary variants only apply to per-subject Brunton
            # psychometrics; they require click-task trial rows.
            if variant.id in clicks_module.CLICK_SUMMARY_VARIANT_IDS and (
                finding.slice_id != "slice.auditory-clicks"
                or finding.stratification.subject_id is None
            ):
                continue
            try:
                path = _do_fit_one(
                    variant_id=variant.id,
                    finding_id=finding.id,
                    out_dir=out_dir,
                    records=records,
                )
            except (ValueError, ZeroDivisionError) as exc:
                print(
                    f"  ✗ {variant.id} × {finding.id}: {exc}",
                    file=sys.stderr,
                )
                n_failed += 1
                continue
            print(f"  ✓ {path}")
            n_fitted += 1

    print(
        f"fit-stale-models: {n_fitted} fitted, {n_skipped} skipped (already "
        f"had fit), {n_failed} failed"
    )
    return 1 if n_failed else 0


def _audit_models(*, tolerance: float, out_file: Path | None) -> int:
    from behavtaskatlas.model_layer import (
        audit_model_fits,
        format_model_audit_report,
    )
    from behavtaskatlas.models import Finding, ModelFit, ModelVariant

    records = load_repository_records(Path("."))
    fits = [r for r in records if isinstance(r, ModelFit)]
    variants = [r for r in records if isinstance(r, ModelVariant)]
    findings_by_id = {r.id: r for r in records if isinstance(r, Finding)}
    report = audit_model_fits(
        fits=fits,
        variants=variants,
        findings_by_id=findings_by_id,
        tolerance=tolerance,
    )
    print(format_model_audit_report(report))
    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote model audit report to {out_file}")
    if report["overall_status"] == "drift":
        return 1
    return 0


def _write_clicks_harmonization_outputs(
    *,
    trials: list[CanonicalTrial],
    details: dict[str, Any],
    mat_file: Path,
    out_dir: Path,
    parsed_field: str,
) -> dict[str, Any]:
    session_id = f"{mat_file.stem}-{parsed_field}"
    session_dir = out_dir / session_id
    trials_path = session_dir / "trials.csv"
    summary_path = session_dir / "summary.csv"
    provenance_path = session_dir / "provenance.json"

    summary = summarize_canonical_trials(trials)
    write_canonical_trials_csv(trials_path, trials)
    write_summary_csv(summary_path, summary)
    write_provenance_json(
        provenance_path,
        brody_clicks_provenance_payload(
            details=details,
            trials=trials,
            output_files={
                "trials": str(trials_path),
                "summary": str(summary_path),
                "provenance": str(provenance_path),
            },
        ),
    )
    return {
        "session_id": session_id,
        "session_dir": session_dir,
        "trials_path": trials_path,
        "summary_path": summary_path,
        "provenance_path": provenance_path,
        "summary_rows": summary,
    }


def _write_clicks_analysis_outputs(
    *,
    trials: list[CanonicalTrial],
    session_dir: Path,
    kernel_bins: int,
) -> dict[str, Any]:
    result = analyze_brody_clicks(trials)
    kernel_result = analyze_brody_clicks_evidence_kernel(trials, n_bins=kernel_bins)

    summary_path = session_dir / "psychometric_summary.csv"
    result_path = session_dir / "analysis_result.json"
    plot_path = session_dir / "psychometric.svg"
    kernel_summary_path = session_dir / "evidence_kernel_summary.csv"
    kernel_result_path = session_dir / "evidence_kernel_result.json"
    kernel_plot_path = session_dir / "evidence_kernel.svg"

    write_summary_csv(summary_path, result["summary_rows"])
    write_analysis_json(result_path, result)
    write_psychometric_svg(
        plot_path,
        result["summary_rows"],
        x_axis_label=CLICKS_PSYCHOMETRIC_X_AXIS_LABEL,
    )
    write_evidence_kernel_summary_csv(kernel_summary_path, kernel_result["summary_rows"])
    write_analysis_json(kernel_result_path, kernel_result)
    write_evidence_kernel_svg(kernel_plot_path, kernel_result["summary_rows"])
    return {
        "psychometric_summary_path": summary_path,
        "analysis_result_path": result_path,
        "psychometric_plot_path": plot_path,
        "evidence_kernel_summary_path": kernel_summary_path,
        "evidence_kernel_result_path": kernel_result_path,
        "evidence_kernel_plot_path": kernel_plot_path,
        "psychometric_result": result,
        "evidence_kernel_result": kernel_result,
    }


def _clicks_batch_mat_files(
    *,
    mat_files: list[Path] | None,
    mat_dir: Path | None,
    max_files: int | None,
) -> list[Path]:
    if max_files is not None and max_files <= 0:
        raise ValueError("max_files must be positive")
    if mat_files is not None:
        paths = mat_files
    elif mat_dir is not None:
        if not mat_dir.exists():
            raise ValueError(f"MATLAB file directory not found: {mat_dir}")
        if not mat_dir.is_dir():
            raise ValueError(f"MATLAB file path is not a directory: {mat_dir}")
        paths = sorted(path for path in mat_dir.iterdir() if path.suffix.lower() == ".mat")
    else:
        paths = []
    sorted_paths = sorted(paths, key=lambda path: path.name)
    return sorted_paths[:max_files] if max_files is not None else sorted_paths


def _clicks_batch_row_template(*, mat_file: Path, parsed_field: str) -> dict:
    return {
        "mat_file": str(mat_file),
        "session_id": f"{mat_file.stem}-{parsed_field}",
        "parsed_field": parsed_field,
        "subject_id": mat_file.stem,
        "task_type": None,
        "status": None,
        "error": None,
        "n_trials": None,
        "harmonization_summary_rows": None,
        "psychometric_summary_rows": None,
        "psychometric_prior_contexts": None,
        "evidence_kernel_rows": None,
        "evidence_kernel_analyzed_trials": None,
        "evidence_kernel_excluded_trials": None,
        "source_file_sha256": None,
        "output_dir": None,
    }
    return 0


def _relative_artifact_link(path: Path, base_dir: Path) -> str:
    return os.path.relpath(path, base_dir).replace(os.sep, "/")


def _read_json_object_file(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return loaded


if __name__ == "__main__":
    raise SystemExit(main())
