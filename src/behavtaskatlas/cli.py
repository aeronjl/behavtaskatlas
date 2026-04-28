from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from behavtaskatlas.allen import (
    DEFAULT_ALLEN_VISUAL_BEHAVIOR_DERIVED_DIR,
    DEFAULT_ALLEN_VISUAL_BEHAVIOR_RAW_DIR,
    allen_visual_behavior_provenance_payload,
    analyze_allen_change_detection,
    download_allen_visual_behavior_session,
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
from behavtaskatlas.findings import (
    build_comparisons_index,
    build_findings_index,
    extract_accuracy_findings_for_slice,
    extract_chronometric_findings_for_slice,
    extract_psychometric_findings_for_slice,
    extract_subject_condition_psychometric_findings_for_slice,
    extract_subject_psychometric_findings_for_slice,
    import_csv_findings,
    load_import_mapping,
    write_finding_yaml,
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
    DEFAULT_IBL_EID,
    DEFAULT_MOUSE_UNBIASED_DERIVED_DIR,
    DEFAULT_MOUSE_UNBIASED_EID,
    IBL_VISUAL_PROTOCOL_ID,
    MOUSE_UNBIASED_VISUAL_PROTOCOL_ID,
    analyze_ibl_visual_protocol,
    harmonize_ibl_visual_trials,
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
from behavtaskatlas.rdm import (
    DEFAULT_HUMAN_RDM_DERIVED_DIR,
    DEFAULT_HUMAN_RDM_RAW_DIR,
    DEFAULT_HUMAN_RDM_SESSION_ID,
    DEFAULT_MACAQUE_RDM_CONFIDENCE_DERIVED_DIR,
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
    download_human_rdm_phs_files,
    download_macaque_rdm_confidence_source_data,
    download_roitman_rdm_csv,
    human_rdm_provenance_payload,
    load_human_rdm_phs_mats,
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
from behavtaskatlas.validation import validate_repository


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
            "For psychometric only: read trials.csv and emit one finding "
            "per subject_id rather than the pooled summary."
        ),
    )
    extract_finding_parser.add_argument(
        "--by-subject-condition",
        default=None,
        help=(
            "For psychometric only: read trials.csv and emit one finding "
            "per (subject_id × <column>) cell. Pass the trials column to "
            "stratify on, typically `prior_context`. Implies --by-subject."
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
    if args.command == "macaque-rdm-confidence-harmonize":
        return _macaque_rdm_confidence_harmonize(
            source_zip=Path(args.source_zip),
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
    if args.command == "extract-finding":
        return _extract_finding(
            slice_id=args.slice_id,
            paper_id=args.paper_id,
            finding_id_prefix=args.finding_id_prefix,
            curve_type=args.curve_type,
            by_subject=bool(args.by_subject),
            by_subject_condition=args.by_subject_condition,
            x_label=args.x_label,
            x_units=args.x_units,
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
    x_label: str | None,
    x_units: str | None,
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
    if by_subject_active and curve_type != "psychometric":
        print(
            f"--by-subject / --by-subject-condition is only supported for "
            f"curve_type=psychometric; got {curve_type!r}.",
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

    try:
        if curve_type == "psychometric":
            extractor_kwargs.setdefault("x_label", "Signed evidence")
            extractor_kwargs.setdefault("x_units", "")
            if by_subject_condition is not None:
                findings = extract_subject_condition_psychometric_findings_for_slice(
                    slice_record,
                    condition_column=by_subject_condition,
                    **extractor_kwargs,
                )
            elif by_subject:
                findings = extract_subject_psychometric_findings_for_slice(
                    slice_record, **extractor_kwargs
                )
            else:
                findings = extract_psychometric_findings_for_slice(
                    slice_record, **extractor_kwargs
                )
        elif curve_type == "chronometric":
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
    from behavtaskatlas.models import Comparison, Finding, Paper, Protocol, TaskFamily
    from behavtaskatlas.models import ModelFit as _ModelFit
    from behavtaskatlas.models import ModelVariant as _ModelVariant
    findings_payload = build_findings_index(
        papers=[r for r in records if isinstance(r, Paper)],
        findings=[r for r in records if isinstance(r, Finding)],
        protocols=[r for r in records if isinstance(r, Protocol)],
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
    from behavtaskatlas.models import Dataset, VerticalSlice
    from behavtaskatlas.search import build_search_index

    citations_dir = derived_dir / "citations"
    paper_records = [r for r in records if isinstance(r, Paper)]
    citation_counts = write_citation_files(paper_records, citations_dir)
    papers_index_path = derived_dir / "papers.json"
    papers_index_path.write_text(
        json.dumps(build_papers_index(paper_records), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    search_payload = build_search_index(
        papers=paper_records,
        families=[r for r in records if isinstance(r, TaskFamily)],
        protocols=[r for r in records if isinstance(r, Protocol)],
        datasets=[r for r in records if isinstance(r, Dataset)],
        slices=[r for r in records if isinstance(r, VerticalSlice)],
        findings=[r for r in records if isinstance(r, Finding)],
        comparisons=[r for r in records if isinstance(r, Comparison)],
    )
    search_path = derived_dir / "search.json"
    search_path.write_text(
        json.dumps(search_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    from behavtaskatlas.audit import audit_pooled_vs_by_subject

    finding_records = [r for r in records if isinstance(r, Finding)]
    audit_payload = audit_pooled_vs_by_subject(finding_records)
    audit_path = derived_dir / "audit.json"
    audit_path.write_text(
        json.dumps(audit_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    from behavtaskatlas.model_layer import build_models_index
    from behavtaskatlas.models import ModelFamily, ModelFit, ModelVariant

    models_payload = build_models_index(
        families=[r for r in records if isinstance(r, ModelFamily)],
        variants=[r for r in records if isinstance(r, ModelVariant)],
        fits=[r for r in records if isinstance(r, ModelFit)],
        slices=[r for r in records if isinstance(r, VerticalSlice)],
        derived_dir=derived_dir,
    )
    models_path = derived_dir / "models.json"
    models_path.write_text(
        json.dumps(models_payload, indent=2, sort_keys=True, default=str) + "\n",
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
        f"Wrote models index ({models_payload['counts']['families']} families, "
        f"{models_payload['counts']['variants']} variants, "
        f"{models_payload['counts']['fits']} fits) to {models_path}"
    )
    print(f"Indexed {len(payload['slices'])} vertical slices; {available} report available")
    n_findings = findings_payload["counts"]["findings"]
    n_papers = findings_payload["counts"]["papers"]
    n_comparisons = comparisons_payload["counts"]["comparisons"]
    print(f"Indexed {n_findings} findings across {n_papers} papers")
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

    fitter_by_variant = {
        logistic_module.VARIANT_ID: lambda f: logistic_module.fit(f),
        sdt_module.VARIANT_ID: lambda f: sdt_module.fit(f),
        ddm_module.VARIANT_VANILLA: lambda f: ddm_module.fit(
            f, chronometric=paired_chronometric
        ),
        ddm_module.VARIANT_Z_BIAS: lambda f: ddm_module.fit_z_bias(
            f, chronometric=paired_chronometric
        ),
        ddm_module.VARIANT_V_BIAS: lambda f: ddm_module.fit_v_bias(
            f, chronometric=paired_chronometric
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
    fitter_variants = {
        logistic_module.VARIANT_ID,
        sdt_module.VARIANT_ID,
        *ddm_variants_set,
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
            if variant.id in ddm_variants_set and (
                _find_paired_chronometric(finding, records) is None
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
