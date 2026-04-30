from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
import urllib.request
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize

from behavtaskatlas.ibl import (
    analyze_canonical_psychometric,
    current_git_commit,
    current_git_dirty,
)
from behavtaskatlas.models import CanonicalTrial

FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID = (
    "protocol.mouse-visual-contrast-wheel-temporal-regularities"
)
FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID = (
    "dataset.fritsche-temporal-regularities-figshare"
)
DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR = Path(
    "data/raw/fritsche_temporal_regularities"
)
DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_ZIP = (
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR / "data.zip"
)
DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_CODE_ZIP = (
    DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR / "code.zip"
)
DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR = Path(
    "derived/fritsche_temporal_regularities"
)
DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID = "fritsche-temporal-regularities"

FRITSCHE_FIGSHARE_URL = (
    "https://figshare.com/articles/dataset/"
    "_b_Temporal_regularities_shape_perceptual_decisions_and_striatal_dopamine_signals_b_/"
    "24179829"
)
FRITSCHE_FIGSHARE_DOI = "10.6084/m9.figshare.24179829.v2"
FRITSCHE_NATURE_URL = "https://www.nature.com/articles/s41467-024-51393-8"
FRITSCHE_NATURE_DOI = "10.1038/s41467-024-51393-8"
FRITSCHE_DATA_ZIP_URL = "https://ndownloader.figshare.com/files/47397445"
FRITSCHE_DATA_ZIP_FILE_ID = "47397445"
FRITSCHE_CODE_ZIP_URL = "https://ndownloader.figshare.com/files/47397427"
FRITSCHE_CODE_ZIP_FILE_ID = "47397427"
FRITSCHE_CODE_MANIFEST_ANALYSIS_ID = "analysis.fritsche-temporal-regularities.code-manifest"

FRITSCHE_EXPERIMENT_FILES = {
    "exp1_transitional_regularities": "data/data_exp1_transitional_regularities.csv",
    "exp2_adaptation_test": "data/data_exp2_adaptation_test.csv",
    "exp3_photometry_behavior": "data/data_exp3_photometry_behavior.csv",
}

FRITSCHE_TEXT_CODE_EXTENSIONS = {
    ".m",
    ".py",
    ".r",
    ".R",
    ".txt",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".csv",
    ".stan",
}

FRITSCHE_SCRIPT_CLASSIFICATIONS = {
    "code/1_behavioral_analysis.r": {
        "role": "exp1 behavioral sequence-regime analysis",
        "atlas_status": "reused_as_reference",
        "notes": (
            "Reference for environment derivation, behavior CSV preparation, and "
            "history-model context; atlas uses generated CSVs rather than rerunning R."
        ),
    },
    "code/5_adaptation_analysis.r": {
        "role": "exp2 adaptation and altitude/history analysis",
        "atlas_status": "reused_as_reference",
        "notes": (
            "Reference for exp2 source columns, session-level exclusions, and "
            "lagged adaptation variables; atlas implements independent operational "
            "session-order summaries."
        ),
    },
    "code/7_dopamine_analysis.r": {
        "role": "dopamine photometry analysis",
        "atlas_status": "deferred",
        "notes": (
            "Photometry joins and dopamine-model alignment are outside the "
            "behavior-first slice."
        ),
    },
    "code/6_ibl_analysis.r": {
        "role": "IBL comparison analysis",
        "atlas_status": "deferred",
        "notes": (
            "IBL behavior is represented by dedicated atlas slices instead of this "
            "comparison table."
        ),
    },
    "code/3_hidden_markov_model/3_1_export4glmhmm.R": {
        "role": "GLM-HMM neutral export",
        "atlas_status": "deferred",
        "notes": "Latent-state GLM-HMM fitting is deferred until behavior-first outputs stabilize.",
    },
    "code/3_hidden_markov_model/3_2_fit_glmhmm_neutral.py": {
        "role": "GLM-HMM neutral fit",
        "atlas_status": "deferred",
        "notes": "Latent-state GLM-HMM fitting is deferred until behavior-first outputs stabilize.",
    },
    "code/3_hidden_markov_model/3_4_fit_glmhmm_neutral_withHistory.py": {
        "role": "GLM-HMM neutral fit with history",
        "atlas_status": "deferred",
        "notes": "Latent-state GLM-HMM fitting is deferred until behavior-first outputs stabilize.",
    },
    "code/4_rl_model/fitting_pompd_main.m": {
        "role": "POMDP/RL model fitting",
        "atlas_status": "deferred",
        "notes": "Full reinforcement-learning model refit is deferred.",
    },
    "code/2_parameter_recovery_simulation/2_2_glmnet_parameter_recovery.R": {
        "role": "parameter recovery simulation",
        "atlas_status": "deferred",
        "notes": "Simulation and parameter recovery are not part of the MVP behavior slice.",
    },
}

FRITSCHE_REQUIRED_FIELDS = {
    "mouseName",
    "expRef",
    "trialNumber",
    "contrastLeft",
    "contrastRight",
    "correctResponse",
    "choice",
    "feedback",
    "environment",
    "stimulusOnsetTime",
}

FRITSCHE_OPTIONAL_FIELDS = {
    "sessionNum",
    "stage",
    "repeatIncorrect",
    "repeatNumber",
    "rewardContingency",
    "choiceCompleteTime",
    "choiceStartTime",
    "punishSoundOnsetTime",
    "goCueTime",
    "rewardTime",
    "rewardVolume",
    "altitude",
    "outcomeTime",
    "contrast",
    "rt",
    "abs(contrast)",
    "exclude_rt",
    "accuracy_easy",
    "exclude_session",
    "repeatChoice",
    "exclude_repeatChoice",
    "include_session_pf",
}

FRITSCHE_TRANSITION_SUMMARY_FIELDS = [
    "experiment",
    "environment",
    "transition_type",
    "previous_stimulus_side",
    "current_stimulus_side",
    "n_trials",
    "n_subjects",
    "n_sessions",
    "n_choice",
    "n_no_response",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "n_choice_pairs",
    "n_choice_repeat",
    "p_choice_repeat",
    "median_response_time",
]

FRITSCHE_CHOICE_HISTORY_SUMMARY_FIELDS = [
    "experiment",
    "environment",
    "previous_choice",
    "previous_feedback",
    "previous_stimulus_side",
    "n_trials",
    "n_subjects",
    "n_sessions",
    "n_choice",
    "n_no_response",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "n_choice_pairs",
    "n_choice_repeat",
    "p_choice_repeat",
    "median_response_time",
]

FRITSCHE_SUBJECT_ENVIRONMENT_FIELDS = [
    "experiment",
    "environment",
    "subject_id",
    "n_sessions",
    "n_trials",
    "n_choice",
    "n_no_response",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "n_lagged_trials",
    "n_stimulus_side_pairs",
    "n_stimulus_side_repeat",
    "p_stimulus_side_repeat",
    "n_choice_pairs",
    "n_choice_repeat",
    "p_choice_repeat",
    "median_response_time",
]

FRITSCHE_CHOICE_HISTORY_MODEL_ID = "fritsche_lag1_choice_history_logistic"
FRITSCHE_CHOICE_HISTORY_MODEL_TERMS = [
    (
        "intercept",
        "Intercept",
        "baseline log-odds of right choice",
    ),
    (
        "signed_contrast",
        "Current signed contrast",
        "current signed contrast divided by 100",
    ),
    (
        "previous_choice_right",
        "Previous choice right",
        "previous right choice = +1, previous left choice = -1",
    ),
    (
        "previous_stimulus_right",
        "Previous stimulus side right",
        "previous right stimulus = +1, previous left stimulus = -1, zero/unknown = 0",
    ),
    (
        "previous_rewarded",
        "Previous reward",
        "previous reward = +1, previous error = -1, unknown = 0",
    ),
    (
        "previous_choice_x_reward",
        "Previous choice x reward",
        "previous choice sign multiplied by previous feedback sign",
    ),
]
FRITSCHE_CHOICE_HISTORY_MODEL_FIELDS = [
    "model_id",
    "model_scope",
    "experiment",
    "environment",
    "term",
    "term_label",
    "predictor_coding",
    "coefficient_log_odds",
    "standard_error",
    "z",
    "odds_ratio_per_unit",
    "n_trials",
    "n_subjects",
    "n_sessions",
    "n_right",
    "p_right",
    "log_likelihood",
    "aic",
    "bic",
    "status",
    "message",
    "method",
]

FRITSCHE_NEUTRAL_ADAPTATION_SESSION_FIELDS = [
    "experiment",
    "subject_id",
    "session_id",
    "session_date",
    "session_num",
    "subject_session_index",
    "environment",
    "previous_session_environment",
    "previous_non_neutral_environment",
    "previous_non_neutral_experiment",
    "previous_non_neutral_session_id",
    "neutral_run_id",
    "neutral_day_index",
    "sessions_since_non_neutral",
    "altitude",
    "n_trials",
    "n_choice",
    "n_no_response",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "n_lagged_trials",
    "n_stimulus_side_pairs",
    "n_stimulus_side_repeat",
    "p_stimulus_side_repeat",
    "n_choice_pairs",
    "n_choice_repeat",
    "p_choice_repeat",
    "median_response_time",
]

FRITSCHE_NEUTRAL_ADAPTATION_SUMMARY_FIELDS = [
    "experiment",
    "previous_non_neutral_environment",
    "previous_non_neutral_experiment",
    "neutral_day_index",
    "n_sessions",
    "n_subjects",
    "n_trials",
    "n_choice",
    "n_no_response",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "mean_session_p_right",
    "sem_session_p_right",
    "mean_session_p_correct",
    "sem_session_p_correct",
    "mean_session_p_choice_repeat",
    "sem_session_p_choice_repeat",
    "mean_session_p_stimulus_side_repeat",
    "sem_session_p_stimulus_side_repeat",
    "mean_sessions_since_non_neutral",
    "median_session_response_time",
]

FRITSCHE_ARTIFACT_PROVENANCE_FIELDS = [
    "artifact_path",
    "artifact_label",
    "artifact_kind",
    "generated_by_cli",
    "atlas_functions",
    "source_data_files",
    "source_fields",
    "source_scripts",
    "source_script_status",
    "code_manifest_paths",
    "transformation_summary",
    "reuse_decision",
    "deferred_scope",
]


def download_fritsche_temporal_regularities_data(
    raw_dir: Path = DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR,
) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "data.zip"
    request = urllib.request.Request(
        FRITSCHE_DATA_ZIP_URL,
        headers={"User-Agent": "behavtaskatlas/0.1"},
    )
    with urllib.request.urlopen(request) as response:
        content = response.read()
    path.write_bytes(content)
    return {
        "source_url": FRITSCHE_FIGSHARE_URL,
        "figshare_doi": FRITSCHE_FIGSHARE_DOI,
        "data_zip_url": FRITSCHE_DATA_ZIP_URL,
        "data_zip_file_id": FRITSCHE_DATA_ZIP_FILE_ID,
        "path": str(path),
        "n_bytes": len(content),
        "sha256": _file_sha256(path),
    }


def download_fritsche_temporal_regularities_code(
    raw_dir: Path = DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_RAW_DIR,
) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "code.zip"
    request = urllib.request.Request(
        FRITSCHE_CODE_ZIP_URL,
        headers={"User-Agent": "behavtaskatlas/0.1"},
    )
    with urllib.request.urlopen(request) as response:
        content = response.read()
    path.write_bytes(content)
    return {
        "source_url": FRITSCHE_FIGSHARE_URL,
        "figshare_doi": FRITSCHE_FIGSHARE_DOI,
        "code_zip_url": FRITSCHE_CODE_ZIP_URL,
        "code_zip_file_id": FRITSCHE_CODE_ZIP_FILE_ID,
        "path": str(path),
        "n_bytes": len(content),
        "sha256": _file_sha256(path),
    }


def build_fritsche_code_manifest(
    code_zip: Path = DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_CODE_ZIP,
) -> dict[str, Any]:
    if not code_zip.exists():
        raise FileNotFoundError(
            f"Fritsche Figshare code ZIP not found: {code_zip}. "
            "Run `uv run behavtaskatlas fritsche-code-download` first."
        )

    with zipfile.ZipFile(code_zip) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        file_rows: list[dict[str, Any]] = []
        script_rows: list[dict[str, Any]] = []
        source_mentions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        operational_line_refs: list[dict[str, Any]] = []
        for info in infos:
            path = info.filename
            classification = _fritsche_code_file_classification(path)
            file_row = {
                "path": path,
                "size_bytes": info.file_size,
                "compressed_size_bytes": info.compress_size,
                "suffix": Path(path).suffix,
                "role": classification["role"],
                "atlas_status": classification["atlas_status"],
            }
            if _is_source_script_member(path):
                content = archive.read(info)
                text = content.decode("utf-8", errors="replace")
                script_sha256 = hashlib.sha256(content).hexdigest()
                file_row["sha256"] = script_sha256
                dependencies, line_refs = _fritsche_script_line_refs(path, text)
                for dependency in dependencies:
                    source_mentions[dependency["path"]].append(
                        {
                            "file": path,
                            "line": dependency["line"],
                        }
                    )
                operational_line_refs.extend(line_refs)
                script_rows.append(
                    {
                        "path": path,
                        "size_bytes": info.file_size,
                        "sha256": script_sha256,
                        "line_count": len(text.splitlines()),
                        "role": classification["role"],
                        "atlas_status": classification["atlas_status"],
                        "notes": classification["notes"],
                        "source_dependency_paths": sorted(
                            {dependency["path"] for dependency in dependencies}
                        ),
                        "operational_reference_count": len(line_refs),
                    }
                )
            file_rows.append(file_row)

    top_level = sorted({row["path"].split("/")[0] for row in file_rows if row["path"]})
    source_scripts = [row for row in script_rows if row["atlas_status"] == "reused_as_reference"]
    deferred_scripts = [row for row in script_rows if row["atlas_status"] == "deferred"]
    return {
        "analysis_id": FRITSCHE_CODE_MANIFEST_ANALYSIS_ID,
        "analysis_type": "source_code_manifest",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
        "dataset_id": FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID,
        "source": {
            "code_zip": str(code_zip),
            "figshare_url": FRITSCHE_FIGSHARE_URL,
            "figshare_doi": FRITSCHE_FIGSHARE_DOI,
            "figshare_file_id": FRITSCHE_CODE_ZIP_FILE_ID,
            "download_url": FRITSCHE_CODE_ZIP_URL,
            "code_zip_size_bytes": code_zip.stat().st_size,
            "code_zip_sha256": _file_sha256(code_zip),
        },
        "zip": {
            "n_files": len(file_rows),
            "n_source_scripts_hashed": len(script_rows),
            "n_reused_reference_scripts": len(source_scripts),
            "n_deferred_scripts": len(deferred_scripts),
            "top_level_entries": top_level,
        },
        "files": sorted(file_rows, key=lambda row: row["path"]),
        "source_scripts": sorted(script_rows, key=lambda row: row["path"]),
        "source_data_dependencies": [
            {
                "path": path,
                "mentioned_by": mentions,
            }
            for path, mentions in sorted(source_mentions.items())
        ],
        "operational_line_references": sorted(
            operational_line_refs,
            key=lambda row: (row["file"], row["line"], row["pattern"]),
        ),
        "atlas_reuse_decisions": [
            {
                "component": "generated behavior CSVs",
                "decision": "reused",
                "implication": (
                    "The adapter ingests Figshare data.zip CSVs directly rather than "
                    "rerunning the R preprocessing scripts."
                ),
            },
            {
                "component": "adaptation analysis script",
                "decision": "reused_as_reference",
                "implication": (
                    "The atlas reproduces operational session-order and lagged-variable "
                    "summaries in Python, preserving source variables such as altitude."
                ),
            },
            {
                "component": "GLM-HMM, POMDP/RL, and photometry scripts",
                "decision": "deferred",
                "implication": (
                    "These remain out of the MVP behavior-first slice until model and "
                    "photometry provenance contracts are explicit."
                ),
            },
        ],
        "source_data_files": {
            "included_behavior_csvs": list(FRITSCHE_EXPERIMENT_FILES.values()),
            "deferred_tables": [
                "data/data_exp3_photometry_dopamine.csv",
                "data/data_ibl.csv",
            ],
        },
        "artifact_provenance": {
            "csv_fields": FRITSCHE_ARTIFACT_PROVENANCE_FIELDS,
            "default_csv": str(
                DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR
                / DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID
                / "artifact_provenance.csv"
            ),
            "description": (
                "One row per generated atlas artifact linking output files to "
                "source data files, source fields, and reused source scripts."
            ),
        },
        "recommended_next_steps": [
            "Use artifact_provenance.csv to audit script-to-output reuse decisions.",
            "Defer GLM-HMM/POMDP reproduction until model-fit schemas cover latent-state models.",
        ],
    }


def write_fritsche_code_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fritsche_artifact_provenance_rows(
    *,
    derived_dir: Path = DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_DERIVED_DIR,
    session_id: str = DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID,
) -> list[dict[str, Any]]:
    session_dir = derived_dir / session_id
    behavior_files = list(FRITSCHE_EXPERIMENT_FILES.values())
    reference_scripts = [
        "code/1_behavioral_analysis.r",
        "code/5_adaptation_analysis.r",
    ]
    trial_source_fields = sorted(FRITSCHE_REQUIRED_FIELDS | FRITSCHE_OPTIONAL_FIELDS)
    canonical_fields = [
        "mouseName",
        "expRef",
        "trialNumber",
        "contrastLeft",
        "contrastRight",
        "correctResponse",
        "choice",
        "feedback",
        "environment",
        "stimulusOnsetTime",
        "choiceStartTime",
        "rt",
    ]
    lagged_fields = [
        "mouseName",
        "expRef",
        "trialNumber",
        "contrastLeft",
        "contrastRight",
        "choice",
        "feedback",
        "environment",
        "sessionNum",
        "stimulusOnsetTime",
        "choiceStartTime",
        "rt",
    ]
    neutral_adaptation_fields = [
        "mouseName",
        "expRef",
        "sessionNum",
        "trialNumber",
        "environment",
        "altitude",
        "contrastLeft",
        "contrastRight",
        "choice",
        "feedback",
        "repeatChoice",
        "exclude_repeatChoice",
        "include_session_pf",
    ]
    deferred_scope = (
        "Photometry joins, IBL comparison-table reuse, GLM-HMM fits, POMDP/RL "
        "refits, and parameter-recovery simulations remain deferred."
    )
    rows = [
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="trials.csv",
            label="Canonical trials CSV",
            artifact_kind="canonical_trial_table",
            generated_by_cli="fritsche-harmonize",
            atlas_functions=[
                "load_fritsche_temporal_regularities_rows",
                "harmonize_fritsche_temporal_regularities_rows",
                "write_canonical_trials_csv",
            ],
            source_data_files=behavior_files,
            source_fields=trial_source_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=[
                "source_scripts[path=code/1_behavioral_analysis.r]",
                "source_scripts[path=code/5_adaptation_analysis.r]",
                "operational_line_references[pattern=environment_derivation]",
                "operational_line_references[pattern=lagged_history]",
            ],
            transformation_summary=(
                "Maps generated behavior CSV rows to canonical trials while preserving "
                "contrast, left/right choice, correctness, timing, environment, source "
                "row provenance, and optional session/history fields."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="summary.csv",
            label="Harmonization summary CSV",
            artifact_kind="canonical_trial_summary",
            generated_by_cli="fritsche-harmonize",
            atlas_functions=["summarize_canonical_trials", "write_summary_csv"],
            source_data_files=behavior_files,
            source_fields=canonical_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["files[atlas_status=reused_as_reference]"],
            transformation_summary=(
                "Aggregates canonical trials by prior context and signed contrast to "
                "check trial counts and basic choice/correctness rates after import."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="provenance.json",
            label="Provenance JSON",
            artifact_kind="harmonization_provenance",
            generated_by_cli="fritsche-harmonize",
            atlas_functions=[
                "fritsche_temporal_regularities_provenance_payload",
                "write_provenance_json",
            ],
            source_data_files=behavior_files,
            source_fields=trial_source_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["artifact_provenance.default_csv"],
            transformation_summary=(
                "Records Figshare data ZIP metadata, source member paths, source field "
                "coverage, output paths, row counts, and behavior-first caveats."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="psychometric_summary.csv",
            label="Psychometric summary CSV",
            artifact_kind="psychometric_summary",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "analyze_fritsche_temporal_regularities",
                "analyze_canonical_psychometric",
                "write_summary_csv",
            ],
            source_data_files=behavior_files,
            source_fields=canonical_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["operational_line_references[pattern=psychometric_fit]"],
            transformation_summary=(
                "Summarizes right choice, correctness, no-response counts, and median "
                "response time by signed contrast and sequence environment."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="transition_summary.csv",
            label="Transition summary CSV",
            artifact_kind="lag1_stimulus_transition_summary",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "_lagged_trial_pairs",
                "_transition_rows",
                "write_fritsche_transition_csv",
            ],
            source_data_files=behavior_files,
            source_fields=lagged_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["operational_line_references[pattern=lagged_history]"],
            transformation_summary=(
                "Uses within-session trial order to summarize repeat versus alternate "
                "stimulus-side transitions by experiment and sequence environment."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="choice_history_summary.csv",
            label="Choice-history summary CSV",
            artifact_kind="lag1_choice_outcome_summary",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "_lagged_trial_pairs",
                "_choice_history_rows",
                "write_fritsche_choice_history_csv",
            ],
            source_data_files=behavior_files,
            source_fields=lagged_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["operational_line_references[pattern=lagged_history]"],
            transformation_summary=(
                "Groups current trials by previous choice, previous feedback, previous "
                "stimulus side, experiment, and environment."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="subject_environment_summary.csv",
            label="Subject-environment summary CSV",
            artifact_kind="subject_environment_replication_summary",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "_subject_environment_rows",
                "write_fritsche_subject_environment_csv",
            ],
            source_data_files=behavior_files,
            source_fields=lagged_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["operational_line_references[pattern=environment_derivation]"],
            transformation_summary=(
                "Computes per-subject environment summaries for replication across "
                "animals, sessions, choice rates, accuracy, and repeat rates."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="choice_history_model_coefficients.csv",
            label="Choice-history model coefficients CSV",
            artifact_kind="choice_history_logistic_coefficients",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "_choice_history_model_rows",
                "_fit_choice_history_logistic_rows",
                "write_fritsche_choice_history_model_csv",
            ],
            source_data_files=behavior_files,
            source_fields=lagged_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=[
                "operational_line_references[pattern=lagged_history]",
                "operational_line_references[pattern=psychometric_fit]",
            ],
            transformation_summary=(
                "Fits compact logistic coefficients for current right choice from "
                "current signed contrast and lag-1 choice, stimulus, reward, and "
                "choice-by-reward predictors."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="neutral_adaptation_session_summary.csv",
            label="Neutral adaptation session CSV",
            artifact_kind="neutral_session_annotation",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "_neutral_adaptation_session_rows",
                "write_fritsche_neutral_adaptation_session_csv",
            ],
            source_data_files=behavior_files,
            source_fields=neutral_adaptation_fields,
            source_scripts=["code/5_adaptation_analysis.r"],
            source_script_status="reused_as_reference",
            code_manifest_paths=[
                "source_scripts[path=code/5_adaptation_analysis.r]",
                "operational_line_references[pattern=lagged_history]",
                "operational_line_references[pattern=session_exclusion]",
            ],
            transformation_summary=(
                "Annotates each Neutral session with the most recent prior non-Neutral "
                "environment for that subject and trial-count/choice-repeat summaries."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="neutral_adaptation_summary.csv",
            label="Neutral adaptation summary CSV",
            artifact_kind="neutral_adaptation_aggregate",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "_neutral_adaptation_rows",
                "write_fritsche_neutral_adaptation_csv",
            ],
            source_data_files=behavior_files,
            source_fields=neutral_adaptation_fields,
            source_scripts=["code/5_adaptation_analysis.r"],
            source_script_status="reused_as_reference",
            code_manifest_paths=[
                "source_scripts[path=code/5_adaptation_analysis.r]",
                "operational_line_references[pattern=lagged_history]",
            ],
            transformation_summary=(
                "Aggregates Neutral sessions by prior Repeating or Alternating exposure "
                "and neutral-day index without inferring a latent adaptation state."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="analysis_result.json",
            label="Analysis result JSON",
            artifact_kind="analysis_payload",
            generated_by_cli="fritsche-analyze",
            atlas_functions=[
                "analyze_fritsche_temporal_regularities",
                "write_analysis_json",
            ],
            source_data_files=behavior_files,
            source_fields=trial_source_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["files[atlas_status=reused_as_reference]"],
            transformation_summary=(
                "Packages all descriptive summaries, model metadata, source/article "
                "links, and caveats for report generation and static-site indexing."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="psychometric.svg",
            label="Psychometric SVG",
            artifact_kind="plot",
            generated_by_cli="fritsche-analyze",
            atlas_functions=["write_psychometric_svg"],
            source_data_files=behavior_files,
            source_fields=canonical_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["operational_line_references[pattern=psychometric_fit]"],
            transformation_summary=(
                "Renders dependency-free psychometric curves from the generated "
                "psychometric summary rows."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="report.html",
            label="Report HTML",
            artifact_kind="static_report",
            generated_by_cli="fritsche-report",
            atlas_functions=["fritsche_report_html", "write_fritsche_report_html"],
            source_data_files=behavior_files,
            source_fields=trial_source_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=[
                "artifact_provenance.default_csv",
                "source_scripts[path=code/1_behavioral_analysis.r]",
                "source_scripts[path=code/5_adaptation_analysis.r]",
            ],
            transformation_summary=(
                "Combines analysis JSON, provenance JSON, psychometric SVG, and "
                "artifact links into a behavior-first static report."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="code_manifest.json",
            label="Code manifest JSON",
            artifact_kind="source_code_manifest",
            generated_by_cli="fritsche-code-manifest",
            atlas_functions=["build_fritsche_code_manifest", "write_fritsche_code_manifest"],
            source_data_files=[str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_CODE_ZIP)],
            source_fields=[],
            source_scripts=["all source scripts in Figshare code.zip"],
            source_script_status="hashed_and_classified",
            code_manifest_paths=["source_scripts", "files", "operational_line_references"],
            transformation_summary=(
                "Inventories code.zip members, hashes source scripts, records source "
                "data dependency mentions, and classifies atlas reuse versus deferral."
            ),
            deferred_scope=deferred_scope,
        ),
        _fritsche_artifact_provenance_row(
            session_dir=session_dir,
            file_name="artifact_provenance.csv",
            label="Artifact provenance CSV",
            artifact_kind="artifact_provenance_table",
            generated_by_cli="fritsche-code-manifest",
            atlas_functions=[
                "fritsche_artifact_provenance_rows",
                "write_fritsche_artifact_provenance_csv",
            ],
            source_data_files=[
                str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_ZIP),
                str(DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_CODE_ZIP),
            ],
            source_fields=trial_source_fields,
            source_scripts=reference_scripts,
            source_script_status="reused_as_reference",
            code_manifest_paths=["artifact_provenance.csv"],
            transformation_summary=(
                "Provides one auditable row per generated atlas artifact linking "
                "outputs to source files, fields, source scripts, and scope decisions."
            ),
            deferred_scope=deferred_scope,
        ),
    ]
    return rows


def write_fritsche_artifact_provenance_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    _write_csv(path, rows, FRITSCHE_ARTIFACT_PROVENANCE_FIELDS)


def load_fritsche_temporal_regularities_rows(
    zip_file: Path = DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_ZIP,
    *,
    experiments: list[str] | None = None,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected_experiments = experiments or list(FRITSCHE_EXPERIMENT_FILES)
    unknown = sorted(set(selected_experiments) - set(FRITSCHE_EXPERIMENT_FILES))
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"Unknown Fritsche experiment(s): {joined}")
    if not zip_file.exists():
        raise FileNotFoundError(
            f"Fritsche Figshare data ZIP not found: {zip_file}. "
            "Run `uv run behavtaskatlas fritsche-download` first."
        )

    rows: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_file) as archive:
        names = set(archive.namelist())
        for experiment in selected_experiments:
            member = FRITSCHE_EXPERIMENT_FILES[experiment]
            if member not in names:
                raise FileNotFoundError(f"Missing source member in {zip_file}: {member}")
            count = 0
            with archive.open(member) as raw:
                text = (line.decode("utf-8-sig") for line in raw)
                reader = csv.DictReader(text)
                if reader.fieldnames is None:
                    raise ValueError(f"Source member has no header: {member}")
                missing = sorted(FRITSCHE_REQUIRED_FIELDS - set(reader.fieldnames))
                if missing:
                    joined = ", ".join(missing)
                    raise ValueError(f"{member} missing required fields: {joined}")
                for source_index, row in enumerate(reader):
                    row = {key: _clean_cell(value) for key, value in row.items()}
                    row["_experiment"] = experiment
                    row["_source_member"] = member
                    row["_source_row_index"] = source_index
                    rows.append(row)
                    count += 1
                    if limit is not None and len(rows) >= limit:
                        break
            source_files.append(
                {
                    "experiment": experiment,
                    "member": member,
                    "n_loaded_rows": count,
                }
            )
            if limit is not None and len(rows) >= limit:
                break

    details = {
        "source_url": FRITSCHE_FIGSHARE_URL,
        "figshare_doi": FRITSCHE_FIGSHARE_DOI,
        "article_url": FRITSCHE_NATURE_URL,
        "article_doi": FRITSCHE_NATURE_DOI,
        "data_zip_url": FRITSCHE_DATA_ZIP_URL,
        "data_zip_file_id": FRITSCHE_DATA_ZIP_FILE_ID,
        "zip_file": str(zip_file),
        "zip_sha256": _file_sha256(zip_file),
        "experiments": selected_experiments,
        "source_files": source_files,
        "n_rows": len(rows),
    }
    return rows, details


def harmonize_fritsche_temporal_regularities_row(
    source: dict[str, Any],
    *,
    trial_index: int,
    dataset_id: str = FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID,
    protocol_id: str = FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
) -> CanonicalTrial:
    missing = sorted(field for field in FRITSCHE_REQUIRED_FIELDS if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Fritsche source fields: {joined}")

    left = _finite_float(source.get("contrastLeft"))
    right = _finite_float(source.get("contrastRight"))
    signed_contrast = _signed_contrast_percent(left, right)
    environment = str(source.get("environment") or "unknown")
    experiment = str(source.get("_experiment") or "unknown")
    session_id = str(source.get("expRef") or DEFAULT_FRITSCHE_TEMPORAL_REGULARITIES_SESSION_ID)
    response_time = _response_time_seconds(source)
    reward = _finite_float(source.get("rewardVolume"))

    task_variables = {
        "experiment": experiment,
        "environment": environment,
        "left_contrast": _contrast_percent(left),
        "right_contrast": _contrast_percent(right),
        "source_contrast_left": left,
        "source_contrast_right": right,
        "correct_response": _choice_label(source.get("correctResponse")),
        "source_choice": source.get("choice"),
        "source_feedback": source.get("feedback"),
        "session_num": _optional_int(source.get("sessionNum")),
        "source_trial_number": _optional_int(source.get("trialNumber")),
        "repeat_number": _optional_int(source.get("repeatNumber")),
        "repeat_incorrect": _optional_bool(source.get("repeatIncorrect")),
        "reward_contingency": source.get("rewardContingency"),
        "altitude": source.get("altitude"),
        "stimulus_onset_time": _finite_float(source.get("stimulusOnsetTime")),
        "go_cue_time": _finite_float(source.get("goCueTime")),
        "choice_start_time": _finite_float(source.get("choiceStartTime")),
        "choice_complete_time": _finite_float(source.get("choiceCompleteTime")),
        "punish_sound_onset_time": _finite_float(source.get("punishSoundOnsetTime")),
        "reward_time": _finite_float(source.get("rewardTime")),
        "outcome_time": _finite_float(source.get("outcomeTime")),
        "source_rt": _finite_float(source.get("rt")),
        "exclude_rt": _optional_bool(source.get("exclude_rt")),
        "exclude_session": _optional_bool(source.get("exclude_session")),
        "exclude_repeat_choice": _optional_bool(source.get("exclude_repeatChoice")),
        "repeat_choice": _optional_int(source.get("repeatChoice")),
        "include_session_pf": _optional_bool(source.get("include_session_pf")),
        "accuracy_easy": _finite_float(source.get("accuracy_easy")),
    }
    if signed_contrast is not None:
        task_variables["signed_contrast_difference"] = signed_contrast

    return CanonicalTrial(
        protocol_id=protocol_id,
        dataset_id=dataset_id,
        subject_id=str(source.get("mouseName")) if source.get("mouseName") else None,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_contrast,
        stimulus_units="percent contrast, signed right positive",
        stimulus_side=_stimulus_side(left, right),
        evidence_strength=abs(signed_contrast) if signed_contrast is not None else None,
        evidence_units="percent contrast",
        choice=_choice_label(source.get("choice")),
        correct=_correct_label(source.get("feedback")),
        response_time=response_time,
        response_time_origin=_response_time_origin(source),
        feedback=_feedback_label(source.get("feedback")),
        reward=reward,
        reward_units="uL" if reward is not None else None,
        block_id=environment,
        prior_context=environment,
        training_stage=source.get("stage") or experiment,
        task_variables={key: value for key, value in task_variables.items() if value is not None},
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_fritsche_temporal_regularities_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    selected_rows = rows[:limit] if limit is not None else rows
    return [
        harmonize_fritsche_temporal_regularities_row(row, trial_index=index)
        for index, row in enumerate(selected_rows)
    ]


def analyze_fritsche_temporal_regularities(
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    result = analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.fritsche-temporal-regularities.descriptive-psychometric",
        protocol_id=FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
        dataset_id=FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID,
        report_title="Fritsche Temporal Regularities Visual Decision Report",
        stimulus_label="Signed contrast",
        stimulus_units="percent contrast, signed right positive",
        stimulus_metric_name="contrast",
        caveats=[
            (
                "This behavior-first slice summarizes generated Figshare CSV trial rows; "
                "photometry traces and reinforcement-learning model internals are deferred."
            ),
            (
                "The source NoGo rows are rare timeout or no-turn outcomes in a wheel 2AFC "
                "task and are mapped to canonical no-response, not to a valid withhold choice."
            ),
            (
                "The source environment column is preserved as prior_context so Neutral, "
                "Repeating, and Alternating stimulus-sequence regimes remain operational "
                "task variables rather than cognitive labels."
            ),
        ],
    )
    environments = sorted({trial.prior_context for trial in trials if trial.prior_context})
    experiments = sorted(
        {
            str(trial.task_variables.get("experiment"))
            for trial in trials
            if trial.task_variables.get("experiment") is not None
        }
    )
    lagged_pairs = _lagged_trial_pairs(trials)
    transition_rows = _transition_rows(lagged_pairs)
    choice_history_rows = _choice_history_rows(lagged_pairs)
    subject_environment_rows = _subject_environment_rows(trials, lagged_pairs)
    neutral_adaptation_session_rows = _neutral_adaptation_session_rows(trials, lagged_pairs)
    neutral_adaptation_rows = _neutral_adaptation_rows(neutral_adaptation_session_rows)
    choice_history_model_rows = _choice_history_model_rows(lagged_pairs)
    n_choice_history_model_fits = _model_fit_count(choice_history_model_rows)
    n_choice_history_model_ok = _model_fit_count(
        [row for row in choice_history_model_rows if row.get("status") == "ok"]
    )
    result.update(
        {
            "figshare_url": FRITSCHE_FIGSHARE_URL,
            "figshare_doi": FRITSCHE_FIGSHARE_DOI,
            "article_url": FRITSCHE_NATURE_URL,
            "article_doi": FRITSCHE_NATURE_DOI,
            "n_subjects": len({trial.subject_id for trial in trials if trial.subject_id}),
            "n_sessions": len({trial.session_id for trial in trials if trial.session_id}),
            "n_environments": len(environments),
            "environments": environments,
            "n_experiments": len(experiments),
            "experiments": experiments,
            "environment_rows": _environment_rows(trials),
            "n_lagged_trials": len(lagged_pairs),
            "transition_rows": transition_rows,
            "choice_history_rows": choice_history_rows,
            "subject_environment_rows": subject_environment_rows,
            "neutral_adaptation_session_rows": neutral_adaptation_session_rows,
            "neutral_adaptation_rows": neutral_adaptation_rows,
            "n_neutral_adaptation_sessions": len(
                [
                    row
                    for row in neutral_adaptation_session_rows
                    if row.get("previous_non_neutral_environment")
                    in {"Alternating", "Repeating"}
                ]
            ),
            "choice_history_model_id": FRITSCHE_CHOICE_HISTORY_MODEL_ID,
            "choice_history_model_formula": (
                "right_choice ~ signed_contrast + previous_choice_right + "
                "previous_stimulus_right + previous_rewarded + "
                "previous_choice_right:previous_rewarded"
            ),
            "choice_history_model_term_rows": choice_history_model_rows,
            "n_choice_history_model_fits": n_choice_history_model_fits,
            "n_choice_history_model_ok": n_choice_history_model_ok,
        }
    )
    return result


def write_fritsche_transition_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, FRITSCHE_TRANSITION_SUMMARY_FIELDS)


def write_fritsche_choice_history_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, FRITSCHE_CHOICE_HISTORY_SUMMARY_FIELDS)


def write_fritsche_subject_environment_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, FRITSCHE_SUBJECT_ENVIRONMENT_FIELDS)


def write_fritsche_choice_history_model_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    _write_csv(path, rows, FRITSCHE_CHOICE_HISTORY_MODEL_FIELDS)


def write_fritsche_neutral_adaptation_session_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    _write_csv(path, rows, FRITSCHE_NEUTRAL_ADAPTATION_SESSION_FIELDS)


def write_fritsche_neutral_adaptation_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    _write_csv(path, rows, FRITSCHE_NEUTRAL_ADAPTATION_SUMMARY_FIELDS)


def write_fritsche_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        fritsche_report_html(
            analysis_result,
            provenance=provenance,
            psychometric_svg_text=psychometric_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def fritsche_report_html(
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    provenance = provenance or {}
    artifact_links = artifact_links or {}
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    title = str(
        analysis_result.get("report_title")
        or "Fritsche Temporal Regularities Visual Decision Report"
    )
    svg = psychometric_svg_text or (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        '<text x="20" y="60">Psychometric plot not available</text></svg>'
    )
    metrics = [
        ("Trials", analysis_result.get("n_trials")),
        ("Response trials", analysis_result.get("n_response_trials")),
        ("No-response trials", analysis_result.get("n_no_response_trials")),
        ("Lag-1 trials", analysis_result.get("n_lagged_trials")),
        ("Subjects", analysis_result.get("n_subjects")),
        ("Sessions", analysis_result.get("n_sessions")),
        ("Environments", analysis_result.get("n_environments")),
        ("Experiments", analysis_result.get("n_experiments")),
        ("Neutral adaptation sessions", analysis_result.get("n_neutral_adaptation_sessions")),
        ("History model fits", analysis_result.get("n_choice_history_model_ok")),
    ]

    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title>",
        "<style>",
        _fritsche_report_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        f"<p class=\"eyebrow\">{escape(str(analysis_result.get('analysis_id', 'analysis')))}</p>",
        f"<h1>{escape(title)}</h1>",
        (
            "<p class=\"lede\">Behavior-first visual wheel report preserving Neutral, "
            "Repeating, and Alternating sequence environments as operational task "
            "variables. Lag-1 summaries use only within-session trial order.</p>"
        ),
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
            '<section class="grid-two">',
            "<div>",
            "<h2>Source</h2>",
            _definition_list(
                [
                    (
                        "Figshare DOI",
                        source.get("figshare_doi") or analysis_result.get("figshare_doi"),
                    ),
                    (
                        "Article DOI",
                        source.get("article_doi") or analysis_result.get("article_doi"),
                    ),
                    ("Data ZIP file id", source.get("data_zip_file_id")),
                    ("ZIP SHA-256", source.get("zip_sha256")),
                    ("Source rows", source.get("n_source_rows")),
                ]
            ),
            "</div>",
            "<div>",
            "<h2>Provenance</h2>",
            _definition_list(
                [
                    ("Dataset", analysis_result.get("dataset_id")),
                    ("Protocol", analysis_result.get("protocol_id")),
                    ("Generated", analysis_result.get("generated_at")),
                    ("Commit", analysis_result.get("behavtaskatlas_commit")),
                    ("Git dirty", analysis_result.get("behavtaskatlas_git_dirty")),
                ]
            ),
            "</div>",
            "</section>",
            '<section class="figure-section">',
            "<h2>Psychometric Summary</h2>",
            '<div class="figure-wrap">',
            svg,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Environment Summary</h2>",
            _html_table(
                analysis_result.get("environment_rows", []),
                [
                    ("environment", "Environment"),
                    ("n_trials", "Trials"),
                    ("n_sessions", "Sessions"),
                    ("n_subjects", "Subjects"),
                    ("n_choice", "Choices"),
                    ("n_no_response", "No response"),
                    ("p_right", "P(right)"),
                    ("p_correct", "P(correct)"),
                    ("n_signed_contrast_levels", "Contrast levels"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Neutral Sessions After Sequence Exposure</h2>",
            _html_table(
                analysis_result.get("neutral_adaptation_rows", []),
                [
                    ("experiment", "Experiment"),
                    ("previous_non_neutral_environment", "Previous exposure"),
                    ("previous_non_neutral_experiment", "Exposure experiment"),
                    ("neutral_day_index", "Neutral day"),
                    ("n_sessions", "Sessions"),
                    ("n_subjects", "Subjects"),
                    ("p_correct", "P(correct)"),
                    ("mean_session_p_correct", "Mean session P(correct)"),
                    ("mean_session_p_choice_repeat", "Mean session P(choice repeat)"),
                    ("mean_sessions_since_non_neutral", "Sessions since exposure"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Choice-History Logistic Coefficients</h2>",
            _html_table(
                analysis_result.get("choice_history_model_term_rows", []),
                [
                    ("model_scope", "Scope"),
                    ("experiment", "Experiment"),
                    ("environment", "Environment"),
                    ("term_label", "Term"),
                    ("coefficient_log_odds", "Coefficient"),
                    ("standard_error", "SE"),
                    ("z", "z"),
                    ("odds_ratio_per_unit", "Odds ratio"),
                    ("n_trials", "Trials"),
                    ("status", "Status"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Lag-1 Stimulus Transitions</h2>",
            _html_table(
                analysis_result.get("transition_rows", []),
                [
                    ("experiment", "Experiment"),
                    ("environment", "Environment"),
                    ("transition_type", "Transition"),
                    ("previous_stimulus_side", "Previous side"),
                    ("current_stimulus_side", "Current side"),
                    ("n_trials", "Trials"),
                    ("p_correct", "P(correct)"),
                    ("p_right", "P(right)"),
                    ("p_choice_repeat", "P(choice repeat)"),
                    ("median_response_time", "Median RT"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Lag-1 Choice History</h2>",
            _html_table(
                analysis_result.get("choice_history_rows", []),
                [
                    ("experiment", "Experiment"),
                    ("environment", "Environment"),
                    ("previous_choice", "Previous choice"),
                    ("previous_feedback", "Previous feedback"),
                    ("previous_stimulus_side", "Previous side"),
                    ("n_trials", "Trials"),
                    ("p_correct", "P(correct)"),
                    ("p_right", "P(right)"),
                    ("p_choice_repeat", "P(choice repeat)"),
                    ("median_response_time", "Median RT"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Subject-Environment Replication</h2>",
            _html_table(
                analysis_result.get("subject_environment_rows", []),
                [
                    ("experiment", "Experiment"),
                    ("environment", "Environment"),
                    ("subject_id", "Subject"),
                    ("n_sessions", "Sessions"),
                    ("n_trials", "Trials"),
                    ("p_correct", "P(correct)"),
                    ("p_right", "P(right)"),
                    ("p_stimulus_side_repeat", "P(stimulus repeat)"),
                    ("p_choice_repeat", "P(choice repeat)"),
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


def fritsche_temporal_regularities_provenance_payload(
    *,
    zip_file: Path,
    details: dict[str, Any],
    trials: list[CanonicalTrial],
    output_files: dict[str, str],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": FRITSCHE_TEMPORAL_REGULARITIES_PROTOCOL_ID,
        "dataset_id": FRITSCHE_TEMPORAL_REGULARITIES_DATASET_ID,
        "source": {
            "zip_file": str(zip_file),
            "source_url": details.get("source_url"),
            "figshare_doi": details.get("figshare_doi"),
            "article_url": details.get("article_url"),
            "article_doi": details.get("article_doi"),
            "data_zip_url": details.get("data_zip_url"),
            "data_zip_file_id": details.get("data_zip_file_id"),
            "zip_sha256": details.get("zip_sha256"),
            "source_files": details.get("source_files", []),
            "n_source_rows": details.get("n_rows"),
        },
        "source_fields": sorted(FRITSCHE_REQUIRED_FIELDS | FRITSCHE_OPTIONAL_FIELDS),
        "response_time_origin": "choiceStartTime - stimulusOnsetTime, falling back to source rt",
        "n_trials": len(trials),
        "n_subjects": len({trial.subject_id for trial in trials if trial.subject_id}),
        "n_sessions": len({trial.session_id for trial in trials if trial.session_id}),
        "exclusions": {
            "no_response_choices": sum(1 for trial in trials if trial.choice == "no-response"),
            "missing_response_time": sum(1 for trial in trials if trial.response_time is None),
            "source_exclude_rt": sum(
                1 for trial in trials if trial.task_variables.get("exclude_rt") is True
            ),
            "source_exclude_session": sum(
                1 for trial in trials if trial.task_variables.get("exclude_session") is True
            ),
        },
        "outputs": output_files,
        "caveats": [
            (
                "Generated derived artifacts remain under ignored local paths until "
                "release policy is settled."
            ),
            (
                "The Figshare deposit also includes photometry traces and an IBL "
                "comparison table; this adapter currently ingests only generated "
                "study behavior CSVs."
            ),
        ],
    }


def _environment_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[str | None, list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        grouped[trial.prior_context].append(trial)
    rows: list[dict[str, Any]] = []
    for environment, group in sorted(grouped.items(), key=lambda item: item[0] or ""):
        n_choice = sum(1 for trial in group if trial.choice in {"left", "right"})
        n_right = sum(1 for trial in group if trial.choice == "right")
        n_correct = sum(1 for trial in group if trial.correct is True)
        correct_known = [trial for trial in group if trial.correct is not None]
        rows.append(
            {
                "environment": environment,
                "n_trials": len(group),
                "n_sessions": len({trial.session_id for trial in group if trial.session_id}),
                "n_subjects": len({trial.subject_id for trial in group if trial.subject_id}),
                "n_choice": n_choice,
                "n_no_response": sum(1 for trial in group if trial.choice == "no-response"),
                "p_right": _safe_ratio(n_right, n_choice),
                "p_correct": _safe_ratio(n_correct, len(correct_known)),
                "n_signed_contrast_levels": len(
                    {trial.stimulus_value for trial in group if trial.stimulus_value is not None}
                ),
            }
        )
    return rows


def _transition_rows(
    lagged_pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[tuple[CanonicalTrial, CanonicalTrial]]] = (
        defaultdict(list)
    )
    for previous, current in lagged_pairs:
        key = (
            _trial_experiment(current),
            _trial_environment(current),
            _transition_type(previous, current),
            previous.stimulus_side,
            current.stimulus_side,
        )
        grouped[key].append((previous, current))

    rows = []
    for key, pairs in sorted(grouped.items()):
        experiment, environment, transition_type, previous_side, current_side = key
        row = _lagged_pair_stats(pairs)
        row.update(
            {
                "experiment": experiment,
                "environment": environment,
                "transition_type": transition_type,
                "previous_stimulus_side": previous_side,
                "current_stimulus_side": current_side,
            }
        )
        rows.append({field: row.get(field) for field in FRITSCHE_TRANSITION_SUMMARY_FIELDS})
    return rows


def _choice_history_rows(
    lagged_pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[tuple[CanonicalTrial, CanonicalTrial]]] = (
        defaultdict(list)
    )
    for previous, current in lagged_pairs:
        key = (
            _trial_experiment(current),
            _trial_environment(current),
            previous.choice,
            previous.feedback,
            previous.stimulus_side,
        )
        grouped[key].append((previous, current))

    rows = []
    for key, pairs in sorted(grouped.items()):
        experiment, environment, previous_choice, previous_feedback, previous_side = key
        row = _lagged_pair_stats(pairs)
        row.update(
            {
                "experiment": experiment,
                "environment": environment,
                "previous_choice": previous_choice,
                "previous_feedback": previous_feedback,
                "previous_stimulus_side": previous_side,
            }
        )
        rows.append({field: row.get(field) for field in FRITSCHE_CHOICE_HISTORY_SUMMARY_FIELDS})
    return rows


def _subject_environment_rows(
    trials: list[CanonicalTrial],
    lagged_pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> list[dict[str, Any]]:
    trials_by_key: dict[tuple[str, str, str], list[CanonicalTrial]] = defaultdict(list)
    pairs_by_key: dict[tuple[str, str, str], list[tuple[CanonicalTrial, CanonicalTrial]]] = (
        defaultdict(list)
    )
    for trial in trials:
        trials_by_key[
            (
                _trial_experiment(trial),
                _trial_environment(trial),
                trial.subject_id or "unknown",
            )
        ].append(trial)
    for previous, current in lagged_pairs:
        pairs_by_key[
            (
                _trial_experiment(current),
                _trial_environment(current),
                current.subject_id or "unknown",
            )
        ].append((previous, current))

    rows = []
    for key, group in sorted(trials_by_key.items()):
        experiment, environment, subject_id = key
        pairs = pairs_by_key.get(key, [])
        stats = _trial_stats(group)
        n_stimulus_side_pairs = sum(
            1
            for previous, current in pairs
            if previous.stimulus_side in {"left", "right"}
            and current.stimulus_side in {"left", "right"}
        )
        n_stimulus_side_repeat = sum(
            1
            for previous, current in pairs
            if previous.stimulus_side in {"left", "right"}
            and current.stimulus_side in {"left", "right"}
            and previous.stimulus_side == current.stimulus_side
        )
        n_choice_pairs = sum(
            1 for previous, current in pairs if _choice_pair_known(previous, current)
        )
        n_choice_repeat = sum(
            1 for previous, current in pairs if _choice_repeated(previous, current)
        )
        row = {
            "experiment": experiment,
            "environment": environment,
            "subject_id": subject_id,
            "n_sessions": len({trial.session_id for trial in group if trial.session_id}),
            "n_trials": len(group),
            "n_choice": stats["n_choice"],
            "n_no_response": stats["n_no_response"],
            "n_right": stats["n_right"],
            "p_right": stats["p_right"],
            "n_correct": stats["n_correct"],
            "p_correct": stats["p_correct"],
            "n_lagged_trials": len(pairs),
            "n_stimulus_side_pairs": n_stimulus_side_pairs,
            "n_stimulus_side_repeat": n_stimulus_side_repeat,
            "p_stimulus_side_repeat": _safe_ratio(
                n_stimulus_side_repeat,
                n_stimulus_side_pairs,
            ),
            "n_choice_pairs": n_choice_pairs,
            "n_choice_repeat": n_choice_repeat,
            "p_choice_repeat": _safe_ratio(n_choice_repeat, n_choice_pairs),
            "median_response_time": stats["median_response_time"],
        }
        rows.append({field: row.get(field) for field in FRITSCHE_SUBJECT_ENVIRONMENT_FIELDS})
    return rows


def _neutral_adaptation_session_rows(
    trials: list[CanonicalTrial],
    lagged_pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> list[dict[str, Any]]:
    sessions = _session_rows(trials, lagged_pairs)
    by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        by_subject[str(session["subject_id"])].append(session)

    rows: list[dict[str, Any]] = []
    for subject_id, subject_sessions in sorted(by_subject.items()):
        ordered = sorted(subject_sessions, key=_session_order_key_from_row)
        last_non_neutral: dict[str, Any] | None = None
        last_session_environment: str | None = None
        neutral_run_id: str | None = None
        neutral_run_counter = 0
        neutral_day_index: int | None = None
        for index, session in enumerate(ordered):
            environment = str(session.get("environment") or "unknown")
            if environment == "Neutral":
                if last_non_neutral is None:
                    neutral_day_index = None
                    neutral_run_id = None
                elif (
                    last_session_environment == "Neutral"
                    and neutral_run_id is not None
                    and neutral_day_index is not None
                ):
                    neutral_day_index += 1
                else:
                    neutral_run_counter += 1
                    neutral_day_index = 1
                    neutral_run_id = f"{subject_id}:neutral-run-{neutral_run_counter}"

                sessions_since_non_neutral = (
                    index - int(last_non_neutral["subject_session_index"])
                    if last_non_neutral is not None
                    else None
                )
                row = {
                    **session,
                    "subject_session_index": index,
                    "previous_session_environment": last_session_environment,
                    "previous_non_neutral_environment": last_non_neutral.get("environment")
                    if last_non_neutral
                    else None,
                    "previous_non_neutral_experiment": last_non_neutral.get("experiment")
                    if last_non_neutral
                    else None,
                    "previous_non_neutral_session_id": last_non_neutral.get("session_id")
                    if last_non_neutral
                    else None,
                    "neutral_run_id": neutral_run_id,
                    "neutral_day_index": neutral_day_index,
                    "sessions_since_non_neutral": sessions_since_non_neutral,
                }
                rows.append(
                    {field: row.get(field) for field in FRITSCHE_NEUTRAL_ADAPTATION_SESSION_FIELDS}
                )
            else:
                last_non_neutral = {**session, "subject_session_index": index}
                neutral_day_index = None
                neutral_run_id = None
            last_session_environment = environment
    return rows


def _neutral_adaptation_rows(
    session_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in session_rows:
        previous_environment = row.get("previous_non_neutral_environment")
        neutral_day_index = row.get("neutral_day_index")
        if previous_environment not in {"Alternating", "Repeating"}:
            continue
        if not isinstance(neutral_day_index, int):
            continue
        grouped[
            (
                str(row.get("experiment") or "unknown"),
                str(previous_environment),
                str(row.get("previous_non_neutral_experiment") or "unknown"),
                neutral_day_index,
            )
        ].append(row)

    rows = []
    for key, group in sorted(grouped.items(), key=lambda item: item[0]):
        experiment, previous_environment, previous_experiment, neutral_day_index = key
        n_choice = sum(int(row.get("n_choice") or 0) for row in group)
        n_right = sum(int(row.get("n_right") or 0) for row in group)
        n_correct = sum(int(row.get("n_correct") or 0) for row in group)
        n_trials = sum(int(row.get("n_trials") or 0) for row in group)
        p_right_values = _finite_values(row.get("p_right") for row in group)
        p_correct_values = _finite_values(row.get("p_correct") for row in group)
        p_choice_repeat_values = _finite_values(row.get("p_choice_repeat") for row in group)
        p_stimulus_repeat_values = _finite_values(
            row.get("p_stimulus_side_repeat") for row in group
        )
        sessions_since_values = _finite_values(
            row.get("sessions_since_non_neutral") for row in group
        )
        median_rt_values = _finite_values(row.get("median_response_time") for row in group)
        row = {
            "experiment": experiment,
            "previous_non_neutral_environment": previous_environment,
            "previous_non_neutral_experiment": previous_experiment,
            "neutral_day_index": neutral_day_index,
            "n_sessions": len(group),
            "n_subjects": len({row.get("subject_id") for row in group if row.get("subject_id")}),
            "n_trials": n_trials,
            "n_choice": n_choice,
            "n_no_response": sum(int(row.get("n_no_response") or 0) for row in group),
            "n_right": n_right,
            "p_right": _safe_ratio(n_right, n_choice),
            "n_correct": n_correct,
            "p_correct": _safe_ratio(n_correct, n_trials),
            "mean_session_p_right": _safe_mean(p_right_values),
            "sem_session_p_right": _safe_sem(p_right_values),
            "mean_session_p_correct": _safe_mean(p_correct_values),
            "sem_session_p_correct": _safe_sem(p_correct_values),
            "mean_session_p_choice_repeat": _safe_mean(p_choice_repeat_values),
            "sem_session_p_choice_repeat": _safe_sem(p_choice_repeat_values),
            "mean_session_p_stimulus_side_repeat": _safe_mean(p_stimulus_repeat_values),
            "sem_session_p_stimulus_side_repeat": _safe_sem(p_stimulus_repeat_values),
            "mean_sessions_since_non_neutral": _safe_mean(sessions_since_values),
            "median_session_response_time": statistics.median(median_rt_values)
            if median_rt_values
            else None,
        }
        rows.append({field: row.get(field) for field in FRITSCHE_NEUTRAL_ADAPTATION_SUMMARY_FIELDS})
    return rows


def _session_rows(
    trials: list[CanonicalTrial],
    lagged_pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> list[dict[str, Any]]:
    trials_by_session: dict[tuple[str, str, str], list[CanonicalTrial]] = defaultdict(list)
    pairs_by_session: dict[tuple[str, str, str], list[tuple[CanonicalTrial, CanonicalTrial]]] = (
        defaultdict(list)
    )
    for trial in trials:
        trials_by_session[_session_key(trial)].append(trial)
    for previous, current in lagged_pairs:
        pairs_by_session[_session_key(current)].append((previous, current))

    rows = []
    for key, group in sorted(trials_by_session.items()):
        subject_id, experiment, session_id = key
        pairs = pairs_by_session.get(key, [])
        stats = _trial_stats(group)
        n_stimulus_side_pairs = sum(
            1
            for previous, current in pairs
            if previous.stimulus_side in {"left", "right"}
            and current.stimulus_side in {"left", "right"}
        )
        n_stimulus_side_repeat = sum(
            1
            for previous, current in pairs
            if previous.stimulus_side in {"left", "right"}
            and current.stimulus_side in {"left", "right"}
            and previous.stimulus_side == current.stimulus_side
        )
        n_choice_pairs = sum(
            1 for previous, current in pairs if _choice_pair_known(previous, current)
        )
        n_choice_repeat = sum(
            1 for previous, current in pairs if _choice_repeated(previous, current)
        )
        row = {
            "experiment": experiment,
            "subject_id": subject_id,
            "session_id": session_id,
            "session_date": _session_date(session_id),
            "session_num": _common_numeric_task_variable(group, "session_num"),
            "environment": _common_string([_trial_environment(trial) for trial in group]),
            "altitude": _common_string(
                [
                    str(trial.task_variables.get("altitude"))
                    for trial in group
                    if trial.task_variables.get("altitude") is not None
                ]
            ),
            "n_trials": len(group),
            "n_choice": stats["n_choice"],
            "n_no_response": stats["n_no_response"],
            "n_right": stats["n_right"],
            "p_right": stats["p_right"],
            "n_correct": stats["n_correct"],
            "p_correct": stats["p_correct"],
            "n_lagged_trials": len(pairs),
            "n_stimulus_side_pairs": n_stimulus_side_pairs,
            "n_stimulus_side_repeat": n_stimulus_side_repeat,
            "p_stimulus_side_repeat": _safe_ratio(
                n_stimulus_side_repeat,
                n_stimulus_side_pairs,
            ),
            "n_choice_pairs": n_choice_pairs,
            "n_choice_repeat": n_choice_repeat,
            "p_choice_repeat": _safe_ratio(n_choice_repeat, n_choice_pairs),
            "median_response_time": stats["median_response_time"],
        }
        rows.append(row)
    return rows


def _choice_history_model_rows(
    lagged_pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[tuple[CanonicalTrial, CanonicalTrial]]] = (
        defaultdict(list)
    )
    for previous, current in lagged_pairs:
        if not _choice_history_model_pair_is_eligible(previous, current):
            continue
        environment = _trial_environment(current)
        experiment = _trial_experiment(current)
        grouped[("all_experiments", "all_experiments", environment)].append(
            (previous, current)
        )
        grouped[("experiment_environment", experiment, environment)].append(
            (previous, current)
        )

    rows: list[dict[str, Any]] = []
    for (model_scope, experiment, environment), pairs in sorted(grouped.items()):
        rows.extend(
            _fit_choice_history_logistic_rows(
                pairs,
                model_scope=model_scope,
                experiment=experiment,
                environment=environment,
            )
        )
    return rows


def _choice_history_model_pair_is_eligible(
    previous: CanonicalTrial,
    current: CanonicalTrial,
) -> bool:
    return (
        current.choice in {"left", "right"}
        and previous.choice in {"left", "right"}
        and current.stimulus_value is not None
    )


def _fit_choice_history_logistic_rows(
    pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
    *,
    model_scope: str,
    experiment: str,
    environment: str,
) -> list[dict[str, Any]]:
    n_trials = len(pairs)
    current_trials = [current for _, current in pairs]
    n_right = sum(1 for current in current_trials if current.choice == "right")
    n_subjects = len({trial.subject_id for trial in current_trials if trial.subject_id})
    n_sessions = len({trial.session_id for trial in current_trials if trial.session_id})
    base = {
        "model_id": FRITSCHE_CHOICE_HISTORY_MODEL_ID,
        "model_scope": model_scope,
        "experiment": experiment,
        "environment": environment,
        "n_trials": n_trials,
        "n_subjects": n_subjects,
        "n_sessions": n_sessions,
        "n_right": n_right,
        "p_right": _safe_ratio(n_right, n_trials),
        "method": "scipy.optimize.minimize L-BFGS-B logistic MLE",
    }
    if n_trials < 10 or n_right == 0 or n_right == n_trials:
        return _choice_history_model_status_rows(
            base,
            status="skipped",
            message="Need at least 10 eligible lagged choice trials with both response classes.",
        )

    x_matrix, y_values = _choice_history_design_matrix(pairs)
    initial = np.zeros(len(FRITSCHE_CHOICE_HISTORY_MODEL_TERMS), dtype=float)
    result = minimize(
        _choice_history_negative_log_likelihood,
        initial,
        args=(x_matrix, y_values),
        jac=_choice_history_gradient,
        method="L-BFGS-B",
        bounds=[(-50.0, 50.0)] * len(FRITSCHE_CHOICE_HISTORY_MODEL_TERMS),
    )
    theta = np.asarray(result.x, dtype=float)
    eta = np.clip(x_matrix @ theta, -50.0, 50.0)
    probabilities = 1.0 / (1.0 + np.exp(-eta))
    probabilities = np.clip(probabilities, 1e-9, 1.0 - 1e-9)
    log_likelihood = float(
        np.sum(y_values * np.log(probabilities) + (1.0 - y_values) * np.log1p(-probabilities))
    )
    n_free = len(FRITSCHE_CHOICE_HISTORY_MODEL_TERMS)
    aic = float(2 * n_free - 2 * log_likelihood)
    bic = float(n_free * math.log(max(n_trials, 1)) - 2 * log_likelihood)
    standard_errors = _choice_history_standard_errors(x_matrix, probabilities)
    status = "ok" if result.success else "warning"
    common = {
        **base,
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
        "status": status,
        "message": str(getattr(result, "message", "")),
    }
    rows = []
    for index, (term, label, coding) in enumerate(FRITSCHE_CHOICE_HISTORY_MODEL_TERMS):
        coefficient = float(theta[index])
        standard_error = standard_errors[index]
        row = {
            **common,
            "term": term,
            "term_label": label,
            "predictor_coding": coding,
            "coefficient_log_odds": coefficient,
            "standard_error": standard_error,
            "z": coefficient / standard_error
            if standard_error is not None and standard_error > 0
            else None,
            "odds_ratio_per_unit": _safe_exp(coefficient),
        }
        rows.append({field: row.get(field) for field in FRITSCHE_CHOICE_HISTORY_MODEL_FIELDS})
    return rows


def _choice_history_model_status_rows(
    base: dict[str, Any],
    *,
    status: str,
    message: str,
) -> list[dict[str, Any]]:
    rows = []
    for term, label, coding in FRITSCHE_CHOICE_HISTORY_MODEL_TERMS:
        row = {
            **base,
            "term": term,
            "term_label": label,
            "predictor_coding": coding,
            "coefficient_log_odds": None,
            "standard_error": None,
            "z": None,
            "odds_ratio_per_unit": None,
            "log_likelihood": None,
            "aic": None,
            "bic": None,
            "status": status,
            "message": message,
        }
        rows.append({field: row.get(field) for field in FRITSCHE_CHOICE_HISTORY_MODEL_FIELDS})
    return rows


def _choice_history_design_matrix(
    pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> tuple[np.ndarray, np.ndarray]:
    x_rows = []
    y_values = []
    for previous, current in pairs:
        previous_choice = _choice_sign(previous.choice)
        previous_reward = _feedback_sign(previous.feedback)
        x_rows.append(
            [
                1.0,
                float(current.stimulus_value or 0.0) / 100.0,
                previous_choice,
                _side_sign(previous.stimulus_side),
                previous_reward,
                previous_choice * previous_reward,
            ]
        )
        y_values.append(1.0 if current.choice == "right" else 0.0)
    return np.asarray(x_rows, dtype=float), np.asarray(y_values, dtype=float)


def _choice_history_negative_log_likelihood(
    theta: np.ndarray,
    x_matrix: np.ndarray,
    y_values: np.ndarray,
) -> float:
    eta = np.clip(x_matrix @ theta, -50.0, 50.0)
    return float(np.sum(np.logaddexp(0.0, eta) - y_values * eta))


def _choice_history_gradient(
    theta: np.ndarray,
    x_matrix: np.ndarray,
    y_values: np.ndarray,
) -> np.ndarray:
    eta = np.clip(x_matrix @ theta, -50.0, 50.0)
    probabilities = 1.0 / (1.0 + np.exp(-eta))
    return x_matrix.T @ (probabilities - y_values)


def _choice_history_standard_errors(
    x_matrix: np.ndarray,
    probabilities: np.ndarray,
) -> list[float | None]:
    weights = probabilities * (1.0 - probabilities)
    hessian = x_matrix.T @ (x_matrix * weights[:, None])
    try:
        covariance = np.linalg.pinv(hessian)
    except np.linalg.LinAlgError:
        return [None] * x_matrix.shape[1]
    standard_errors = []
    for value in np.diag(covariance):
        if not math.isfinite(float(value)) or value < 0:
            standard_errors.append(None)
        else:
            standard_errors.append(float(math.sqrt(float(value))))
    return standard_errors


def _model_fit_count(rows: list[dict[str, Any]]) -> int:
    return len(
        {
            (row.get("model_scope"), row.get("experiment"), row.get("environment"))
            for row in rows
        }
    )


def _lagged_trial_pairs(
    trials: list[CanonicalTrial],
) -> list[tuple[CanonicalTrial, CanonicalTrial]]:
    by_session: dict[str, list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        by_session[trial.session_id].append(trial)

    pairs: list[tuple[CanonicalTrial, CanonicalTrial]] = []
    for session_trials in by_session.values():
        ordered = sorted(session_trials, key=_trial_order_key)
        pairs.extend((ordered[index - 1], ordered[index]) for index in range(1, len(ordered)))
    return pairs


def _trial_order_key(trial: CanonicalTrial) -> tuple[int, int, int]:
    source_trial_number = trial.task_variables.get("source_trial_number")
    if isinstance(source_trial_number, bool):
        source_trial_number = None
    if isinstance(source_trial_number, int):
        return (0, source_trial_number, trial.trial_index)
    if isinstance(source_trial_number, float) and math.isfinite(source_trial_number):
        return (0, int(source_trial_number), trial.trial_index)
    return (1, trial.trial_index, trial.trial_index)


def _session_key(trial: CanonicalTrial) -> tuple[str, str, str]:
    return (
        trial.subject_id or "unknown",
        _trial_experiment(trial),
        trial.session_id,
    )


def _session_order_key_from_row(row: dict[str, Any]) -> tuple[str, float, str]:
    session_date = str(row.get("session_date") or "")
    session_num = row.get("session_num")
    numeric_session_num = float(session_num) if isinstance(session_num, int | float) else math.inf
    return (session_date, numeric_session_num, str(row.get("session_id") or ""))


def _lagged_pair_stats(
    pairs: list[tuple[CanonicalTrial, CanonicalTrial]],
) -> dict[str, Any]:
    current_trials = [current for _, current in pairs]
    stats = _trial_stats(current_trials)
    n_choice_pairs = sum(1 for previous, current in pairs if _choice_pair_known(previous, current))
    n_choice_repeat = sum(1 for previous, current in pairs if _choice_repeated(previous, current))
    stats.update(
        {
            "n_subjects": len({trial.subject_id for trial in current_trials if trial.subject_id}),
            "n_sessions": len({trial.session_id for trial in current_trials if trial.session_id}),
            "n_choice_pairs": n_choice_pairs,
            "n_choice_repeat": n_choice_repeat,
            "p_choice_repeat": _safe_ratio(n_choice_repeat, n_choice_pairs),
        }
    )
    return stats


def _trial_stats(trials: list[CanonicalTrial]) -> dict[str, Any]:
    n_choice = sum(1 for trial in trials if trial.choice in {"left", "right"})
    n_right = sum(1 for trial in trials if trial.choice == "right")
    correct_known = [trial for trial in trials if trial.correct is not None]
    n_correct = sum(1 for trial in trials if trial.correct is True)
    return {
        "n_trials": len(trials),
        "n_choice": n_choice,
        "n_no_response": sum(1 for trial in trials if trial.choice == "no-response"),
        "n_right": n_right,
        "p_right": _safe_ratio(n_right, n_choice),
        "n_correct": n_correct,
        "p_correct": _safe_ratio(n_correct, len(correct_known)),
        "median_response_time": _median_response_time(trials),
    }


def _transition_type(previous: CanonicalTrial, current: CanonicalTrial) -> str:
    if current.stimulus_side == "none":
        return "current_zero_contrast"
    if previous.stimulus_side == "none":
        return "previous_zero_contrast"
    if previous.stimulus_side in {"left", "right"} and current.stimulus_side in {
        "left",
        "right",
    }:
        if previous.stimulus_side == current.stimulus_side:
            return "repeat_stimulus_side"
        return "alternate_stimulus_side"
    return "unclassified"


def _choice_pair_known(previous: CanonicalTrial, current: CanonicalTrial) -> bool:
    return previous.choice in {"left", "right"} and current.choice in {"left", "right"}


def _choice_repeated(previous: CanonicalTrial, current: CanonicalTrial) -> bool:
    return _choice_pair_known(previous, current) and previous.choice == current.choice


def _choice_sign(choice: str) -> float:
    if choice == "right":
        return 1.0
    if choice == "left":
        return -1.0
    return 0.0


def _side_sign(side: str) -> float:
    if side == "right":
        return 1.0
    if side == "left":
        return -1.0
    return 0.0


def _feedback_sign(feedback: str) -> float:
    if feedback == "reward":
        return 1.0
    if feedback == "error":
        return -1.0
    return 0.0


def _trial_experiment(trial: CanonicalTrial) -> str:
    return str(trial.task_variables.get("experiment") or "unknown")


def _trial_environment(trial: CanonicalTrial) -> str:
    return str(trial.prior_context or trial.task_variables.get("environment") or "unknown")


def _session_date(session_id: str) -> str | None:
    prefix = session_id[:10]
    if len(prefix) == 10 and prefix[4] == "-" and prefix[7] == "-":
        return prefix
    return None


def _common_string(values: list[str]) -> str | None:
    cleaned = [value for value in values if value and value != "None"]
    if not cleaned:
        return None
    unique = sorted(set(cleaned))
    return unique[0] if len(unique) == 1 else "mixed"


def _common_numeric_task_variable(
    trials: list[CanonicalTrial],
    key: str,
) -> int | float | None:
    values = [
        value
        for trial in trials
        if (value := trial.task_variables.get(key)) is not None
        and not isinstance(value, bool)
    ]
    if not values:
        return None
    unique = sorted(set(values))
    return unique[0] if len(unique) == 1 else None


def _median_response_time(trials: list[CanonicalTrial]) -> float | None:
    values = [trial.response_time for trial in trials if trial.response_time is not None]
    return statistics.median(values) if values else None


def _signed_contrast_percent(left: float | None, right: float | None) -> float | None:
    if left is None and right is None:
        return None
    return ((right or 0.0) - (left or 0.0)) * 100.0


def _contrast_percent(value: float | None) -> float | None:
    return value * 100.0 if value is not None else None


def _stimulus_side(left: float | None, right: float | None) -> str:
    if left is None and right is None:
        return "unknown"
    diff = (right or 0.0) - (left or 0.0)
    if diff > 0:
        return "right"
    if diff < 0:
        return "left"
    if _is_zero(left) and _is_zero(right):
        return "none"
    return "unknown"


def _choice_label(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "left":
        return "left"
    if normalized == "right":
        return "right"
    if normalized in {"nogo", "no-go", "none", ""}:
        return "no-response"
    return "unknown"


def _correct_label(value: Any) -> bool | None:
    normalized = str(value or "").strip().lower()
    if normalized == "rewarded":
        return True
    if normalized == "unrewarded":
        return False
    return None


def _feedback_label(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "rewarded":
        return "reward"
    if normalized == "unrewarded":
        return "error"
    return "unknown"


def _response_time_seconds(source: dict[str, Any]) -> float | None:
    source_rt = _finite_float(source.get("rt"))
    if source_rt is not None:
        return source_rt
    start = _finite_float(source.get("choiceStartTime"))
    stimulus = _finite_float(source.get("stimulusOnsetTime"))
    if start is None or stimulus is None:
        return None
    return start - stimulus


def _response_time_origin(source: dict[str, Any]) -> str | None:
    if _finite_float(source.get("rt")) is not None:
        return "rt"
    if (
        _finite_float(source.get("choiceStartTime")) is not None
        and _finite_float(source.get("stimulusOnsetTime")) is not None
    ):
        return "choiceStartTime - stimulusOnsetTime"
    return None


def _clean_cell(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "NA", "NaN", "nan"}:
        return None
    return text


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _optional_int(value: Any) -> int | None:
    numeric = _finite_float(value)
    return int(numeric) if numeric is not None else None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def _is_zero(value: float | None) -> bool:
    return value is not None and abs(value) < 1e-12


def _json_safe_value(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _finite_values(values: Any) -> list[float]:
    finite = []
    for value in values:
        numeric = _finite_float(value)
        if numeric is not None:
            finite.append(numeric)
    return finite


def _safe_mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _safe_sem(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return statistics.stdev(values) / math.sqrt(len(values))


def _safe_exp(value: float) -> float | None:
    if value > 700 or value < -700:
        return None
    return float(math.exp(value))


def _fritsche_artifact_provenance_row(
    *,
    session_dir: Path,
    file_name: str,
    label: str,
    artifact_kind: str,
    generated_by_cli: str,
    atlas_functions: list[str],
    source_data_files: list[str],
    source_fields: list[str],
    source_scripts: list[str],
    source_script_status: str,
    code_manifest_paths: list[str],
    transformation_summary: str,
    deferred_scope: str,
    reuse_decision: str = "generated",
) -> dict[str, Any]:
    return {
        "artifact_path": (session_dir / file_name).as_posix(),
        "artifact_label": label,
        "artifact_kind": artifact_kind,
        "generated_by_cli": generated_by_cli,
        "atlas_functions": _join_provenance_values(atlas_functions),
        "source_data_files": _join_provenance_values(source_data_files),
        "source_fields": _join_provenance_values(source_fields),
        "source_scripts": _join_provenance_values(source_scripts),
        "source_script_status": source_script_status,
        "code_manifest_paths": _join_provenance_values(code_manifest_paths),
        "transformation_summary": transformation_summary,
        "reuse_decision": reuse_decision,
        "deferred_scope": deferred_scope,
    }


def _join_provenance_values(values: list[str]) -> str:
    return "; ".join(str(value) for value in values if value)


def _fritsche_code_file_classification(path: str) -> dict[str, str]:
    if path.startswith("__MACOSX/") or "/._" in path:
        return {
            "role": "macos_metadata",
            "atlas_status": "ignored",
            "notes": "Archive metadata sidecar.",
        }
    if path in FRITSCHE_SCRIPT_CLASSIFICATIONS:
        return FRITSCHE_SCRIPT_CLASSIFICATIONS[path]
    if path.startswith("code/3_hidden_markov_model/fit_models/"):
        return {
            "role": "precomputed GLM-HMM model artifact",
            "atlas_status": "deferred",
            "notes": "Binary fitted-model artifact; not part of the behavior-first slice.",
        }
    if path.startswith("code/3_hidden_markov_model/data/"):
        return {
            "role": "GLM-HMM design-matrix export",
            "atlas_status": "deferred",
            "notes": "Model-specific design matrix export.",
        }
    if path.startswith("code/4_rl_model/fitting_results/"):
        return {
            "role": "precomputed POMDP/RL response artifact",
            "atlas_status": "deferred",
            "notes": "Model output artifact; full RL reproduction is deferred.",
        }
    if path.startswith("code/4_rl_model/"):
        return {
            "role": "POMDP/RL model support file",
            "atlas_status": "deferred",
            "notes": "Full reinforcement-learning model refit is deferred.",
        }
    if path.startswith("code/2_parameter_recovery_simulation/"):
        return {
            "role": "parameter recovery support file",
            "atlas_status": "deferred",
            "notes": "Simulation support file outside the behavior-first MVP.",
        }
    if _is_source_script_member(path):
        return {
            "role": "source script or configuration",
            "atlas_status": "inspected",
            "notes": "Script is inventoried but not directly rerun by the atlas.",
        }
    return {
        "role": "archive member",
        "atlas_status": "inventoried",
        "notes": "Non-script archive member.",
    }


def _is_source_script_member(path: str) -> bool:
    if path.startswith("__MACOSX/") or "/._" in path:
        return False
    suffix = Path(path).suffix
    return suffix in {".m", ".py", ".r", ".R", ".stan", ".md", ".txt", ".yml", ".yaml", ".json"}


def _fritsche_script_line_refs(
    path: str,
    text: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dependencies: list[dict[str, Any]] = []
    operational_refs: list[dict[str, Any]] = []
    operational_patterns = {
        "source_data_read": re.compile(r"read_csv|load\(|readtable", re.IGNORECASE),
        "environment_derivation": re.compile(r"environment|empRepeatProb", re.IGNORECASE),
        "session_exclusion": re.compile(
            r"exclude_session|exclude_rt|exclude_repeatChoice|include_session_pf",
            re.IGNORECASE,
        ),
        "lagged_history": re.compile(r"lag\(|p1_|repeatChoice|data_hist", re.IGNORECASE),
        "psychometric_fit": re.compile(r"quickpsy|logistic_fun|glmnet", re.IGNORECASE),
        "latent_or_rl_model": re.compile(r"glmhmm|POMDP|pomdp|belief|model", re.IGNORECASE),
        "photometry": re.compile(r"dopamine|photometry|sensor|dff|DA", re.IGNORECASE),
    }
    for line_no, line in enumerate(text.splitlines(), start=1):
        for dependency in _fritsche_data_path_mentions(line):
            dependencies.append({"path": dependency, "line": line_no})
        for pattern_name, pattern in operational_patterns.items():
            if pattern.search(line):
                operational_refs.append(
                    {
                        "file": path,
                        "line": line_no,
                        "pattern": pattern_name,
                    }
                )
    return dependencies, operational_refs


def _fritsche_data_path_mentions(line: str) -> list[str]:
    patterns = [
        r"[.]{0,2}/?data/[A-Za-z0-9_./-]+[.](?:csv|mat|txt|pickle|npy)",
        r"data_[A-Za-z0-9_./-]+[.](?:csv|mat|txt|pickle|npy)",
    ]
    mentions: set[str] = set()
    for pattern in patterns:
        for match in re.findall(pattern, line):
            mentions.add(match.strip("\"'(),"))
    return sorted(mentions)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def _html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="empty">No rows available.</p>'
    html = ['<div class="table-wrap"><table>', "<thead><tr>"]
    html.extend(f"<th>{escape(label)}</th>" for _, label in columns)
    html.extend(["</tr></thead>", "<tbody>"])
    for row in rows:
        html.append("<tr>")
        for key, _ in columns:
            html.append(f"<td>{escape(_format_cell(row.get(key)))}</td>")
        html.append("</tr>")
    html.extend(["</tbody>", "</table></div>"])
    return "\n".join(html)


def _definition_list(rows: list[tuple[str, Any]]) -> str:
    html = ["<dl>"]
    for label, value in rows:
        html.append(f"<dt>{escape(label)}</dt>")
        html.append(f"<dd>{escape(_format_cell(value))}</dd>")
    html.append("</dl>")
    return "\n".join(html)


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:.4g}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _fritsche_report_css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #17212b;
  --muted: #5f6c76;
  --line: #d8dee4;
  --panel: #f6f8fa;
  --accent: #0f766e;
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
  font-size: clamp(2rem, 5vw, 3.35rem);
  line-height: 1.04;
  letter-spacing: 0;
}
h2 {
  margin: 0 0 14px;
  font-size: 1.25rem;
}
.lede {
  max-width: 860px;
  color: var(--muted);
  font-size: 1.03rem;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
  gap: 12px;
  margin: 24px 0;
}
.metric {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--panel);
}
.metric span {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}
.metric strong {
  display: block;
  margin-top: 4px;
  font-size: 1.45rem;
}
.grid-two {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}
section {
  margin-top: 28px;
}
.figure-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.87rem;
}
th, td {
  border-bottom: 1px solid var(--line);
  padding: 7px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--panel);
  font-size: 0.75rem;
  text-transform: uppercase;
}
dl {
  display: grid;
  grid-template-columns: minmax(110px, 0.35fr) 1fr;
  gap: 7px 14px;
  margin: 0;
}
dt {
  color: var(--muted);
  font-weight: 700;
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.artifact-list {
  columns: 2;
}
.empty {
  color: var(--muted);
}
@media (max-width: 720px) {
  main {
    width: min(100vw - 20px, 1180px);
    padding-top: 20px;
  }
  dl {
    grid-template-columns: 1fr;
  }
  .artifact-list {
    columns: 1;
  }
}
"""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
