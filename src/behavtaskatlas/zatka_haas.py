from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import zipfile
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat

from behavtaskatlas.ibl import current_git_commit, current_git_dirty, fit_psychometric_rows
from behavtaskatlas.models import CanonicalTrial

ZATKA_HAAS_PROTOCOL_ID = "protocol.mouse-unforced-visual-contrast-wheel"
ZATKA_HAAS_DATASET_ID = "dataset.zatka-haas-visual-decision-figshare"
ZATKA_HAAS_SLICE_ID = "slice.zatka-haas-visual-decision"
ZATKA_HAAS_ANALYSIS_ID = "analysis.zatka-haas-visual-decision.source-manifest"
DEFAULT_ZATKA_HAAS_SESSION_ID = "zatka-haas-visual-decision"
DEFAULT_ZATKA_HAAS_HIGHER_POWER_SESSION_ID = "zatka-haas-inactivation-higher-power"
DEFAULT_ZATKA_HAAS_RAW_DIR = Path("data/raw/zatka_haas_visual_decision")
DEFAULT_ZATKA_HAAS_CODE_ZIP = DEFAULT_ZATKA_HAAS_RAW_DIR / "code.zip"
DEFAULT_ZATKA_HAAS_DERIVED_DIR = Path("derived/zatka_haas_visual_decision")
ZATKA_HAAS_FIGSHARE_URL = (
    "https://figshare.com/articles/dataset/Zatka-Haas_et_al_2020_dataset/13008038"
)
ZATKA_HAAS_SOURCE_DOI = "10.6084/m9.figshare.13008038.v1"
ZATKA_HAAS_CODE_FILE_ID = "24786170"
ZATKA_HAAS_CODE_DOWNLOAD_URL = "https://ndownloader.figshare.com/files/24786170"
ZATKA_HAAS_HIGHER_POWER_MEMBER = "OptogeneticInactivation/Inactivation_HigherPower.mat"

ZATKA_HAAS_REQUIRED_FIELDS = {"stimulus", "response", "feedbackType"}
ZATKA_HAAS_OPTIONAL_FIELDS = {
    "RT",
    "responseTime",
    "time_choiceMade",
    "time_feedback",
    "time_goCue",
    "time_startMove",
    "time_stimulusOn",
    "sessionID",
    "subjectID",
    "repeatNum",
    "prev_stimulus",
    "prev_response",
    "prev_feedback",
    "laserType",
    "laserRegion",
    "laserCoord",
    "laserPower",
    "laserDuration",
    "laserOnset",
    "laserIdx",
}

ZATKA_HAAS_CHOICE_SUMMARY_FIELDS = [
    "stimulus_value",
    "n_trials",
    "n_left",
    "n_right",
    "n_withhold",
    "n_unknown",
    "n_choice",
    "p_left",
    "p_right",
    "p_withhold",
    "n_correct",
    "p_correct",
    "median_response_time",
    "n_laser_trials",
]

ZATKA_HAAS_CONDITION_SUMMARY_FIELDS = [
    "left_contrast",
    "right_contrast",
    *ZATKA_HAAS_CHOICE_SUMMARY_FIELDS[1:],
]

ZATKA_HAAS_LASER_STATE_SUMMARY_FIELDS = [
    "laser_state",
    *ZATKA_HAAS_CHOICE_SUMMARY_FIELDS,
]

ZATKA_HAAS_LASER_REGION_SUMMARY_FIELDS = [
    "laser_region",
    *ZATKA_HAAS_CHOICE_SUMMARY_FIELDS,
]

ZATKA_HAAS_PERTURBATION_DELTA_FIELDS = [
    "laser_region",
    "region_family",
    "hemisphere",
    "stimulus_value",
    "n_laser_trials",
    "n_non_laser_trials",
    "n_laser_left",
    "n_laser_right",
    "n_laser_withhold",
    "n_laser_choice",
    "n_non_laser_left",
    "n_non_laser_right",
    "n_non_laser_withhold",
    "n_non_laser_choice",
    "p_right_laser",
    "p_right_non_laser",
    "delta_p_right",
    "p_withhold_laser",
    "p_withhold_non_laser",
    "delta_p_withhold",
    "p_correct_laser",
    "p_correct_non_laser",
    "delta_p_correct",
    "median_response_time_laser",
    "median_response_time_non_laser",
    "delta_median_response_time",
]

ZATKA_HAAS_PERTURBATION_REGION_EFFECT_FIELDS = [
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


def build_zatka_haas_code_manifest(code_zip: Path) -> dict[str, Any]:
    """Return a compact manifest from the public Zatka-Haas Figshare code ZIP."""

    if not code_zip.exists():
        raise FileNotFoundError(f"Zatka-Haas code ZIP not found: {code_zip}")
    with zipfile.ZipFile(code_zip) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        text_members = [
            name
            for name in names
            if name.endswith((".m", ".stan", ".txt", ".md"))
            and not _is_embedded_git_path(name)
        ]
        source_mentions: dict[str, list[dict[str, Any]]] = {}
        matlab_fields: set[str] = set()
        stan_choice_encodings: list[dict[str, Any]] = []
        for name in text_members:
            text = archive.read(name).decode("utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), start=1):
                for source_path in _data_path_mentions(line):
                    source_mentions.setdefault(source_path, []).append(
                        {"file": name, "line": line_no}
                    )
                matlab_fields.update(_matlab_behavior_fields(line))
                if "choice" in line and "1=Left" in line and "3=NoGo" in line:
                    stan_choice_encodings.append({"file": name, "line": line_no})

    top_level = sorted({name.split("/")[0] for name in names if name})
    root_scripts = sorted(
        name for name in names if "/" not in name and name.lower().endswith(".m")
    )
    stan_models = sorted(name for name in names if name.endswith(".stan"))
    inclusion_trial_files = sorted(
        name
        for name in names
        if name.startswith("utility/neuropixels_inclusionData/trials/")
        and name.endswith(".npy")
    )
    inclusion_neuron_files = sorted(
        name
        for name in names
        if name.startswith("utility/neuropixels_inclusionData/neurons/")
        and name.endswith(".npy")
    )

    return {
        "analysis_id": ZATKA_HAAS_ANALYSIS_ID,
        "analysis_type": "source_code_manifest",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": ZATKA_HAAS_PROTOCOL_ID,
        "dataset_id": ZATKA_HAAS_DATASET_ID,
        "source": {
            "code_zip": str(code_zip),
            "figshare_url": ZATKA_HAAS_FIGSHARE_URL,
            "figshare_doi": ZATKA_HAAS_SOURCE_DOI,
            "figshare_file_id": ZATKA_HAAS_CODE_FILE_ID,
            "download_url": ZATKA_HAAS_CODE_DOWNLOAD_URL,
            "code_zip_size_bytes": code_zip.stat().st_size,
            "code_zip_sha256": _sha256(code_zip),
        },
        "zip": {
            "n_files": len(infos),
            "n_text_files_scanned": len(text_members),
            "top_level_entries": top_level,
            "root_scripts": root_scripts,
            "stan_model_count": len(stan_models),
            "stan_models": stan_models,
        },
        "source_data_dependencies": [
            {
                "path": path,
                "mentioned_by": mentions,
            }
            for path, mentions in sorted(source_mentions.items())
        ],
        "behavior_source_files": {
            "processed_inactivation": "../data/inactivation/Inactivation_HigherPower.mat",
            "processed_widefield": "../data/widefield/behaviouralData.mat",
            "model_fit": "../data/modelFits/fit_psych_model_with_inactivations.mat",
            "loader": "utility/loadBehaviouralData.m",
            "inactivation_preprocessing": "utility/inactivation_preprocessing.m",
            "widefield_preprocessing": "utility/widefield_preprocessing.m",
        },
        "behavior_field_candidates": sorted(
            field
            for field in matlab_fields
            if field in ZATKA_HAAS_REQUIRED_FIELDS | ZATKA_HAAS_OPTIONAL_FIELDS
        ),
        "canonical_mapping": {
            "left_contrast": "D.stimulus(:, 1), stored as proportion and harmonized to percent",
            "right_contrast": "D.stimulus(:, 2), stored as proportion and harmonized to percent",
            "choice": "D.response / D.choice codes: 1=left, 2=right, 3=NoGo-withhold",
            "correct": "D.feedbackType > 0",
            "response_time": "D.RT when present; otherwise timing differences where available",
            "perturbation": (
                "laserType, laserRegion, laserCoord, laserPower, laserOnset, "
                "laserDuration"
            ),
        },
        "neuropixels_inclusion_files": {
            "trial_file_count": len(inclusion_trial_files),
            "neuron_file_count": len(inclusion_neuron_files),
            "trial_file_examples": inclusion_trial_files[:8],
            "neuron_file_examples": inclusion_neuron_files[:8],
        },
        "stan_choice_encoding_evidence": stan_choice_encodings,
        "recommended_next_steps": [
            (
                "Use the targeted split-ZIP range extraction for "
                "OptogeneticInactivation/Inactivation_HigherPower.mat before downloading "
                "neural-heavy files."
            ),
            "Run the MATLAB v7.3 table harmonizer on the higher-power inactivation table.",
            "Generate non-laser versus laser and region-stratified behavior summaries.",
            "Keep laser variables explicit rather than collapsing them into a cognitive label.",
        ],
    }


def write_zatka_haas_code_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_zatka_haas_processed_mat(path: Path, *, variable: str = "D") -> dict[str, Any]:
    """Load a processed Zatka-Haas MATLAB behavior struct/table variable.

    The public code writes processed tables named `D` into files such as
    `Inactivation_HigherPower.mat` and `behaviouralData.mat`. This loader covers
    both standard MATLAB MAT structs and the MATLAB v7.3/HDF5 table layout used
    by the public inactivation archive.
    """

    if not path.exists():
        raise FileNotFoundError(f"Zatka-Haas processed MAT file not found: {path}")
    try:
        loaded = loadmat(path, squeeze_me=True, struct_as_record=False)
    except (NotImplementedError, ValueError):
        if not _looks_like_hdf5(path):
            raise
        source = _load_zatka_haas_hdf5_table(path, variable=variable)
    else:
        if variable not in loaded:
            available = ", ".join(sorted(k for k in loaded if not k.startswith("__")))
            raise KeyError(f"Variable {variable!r} not found in {path}; available: {available}")
        source = _mat_object_to_dict(loaded[variable])
    missing = sorted(field for field in ZATKA_HAAS_REQUIRED_FIELDS if field not in source)
    if missing:
        raise ValueError(f"Missing required Zatka-Haas fields in {path}: {', '.join(missing)}")
    return source


def harmonize_zatka_haas_visual_trial(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
    subject_id: str | None = None,
) -> CanonicalTrial:
    missing = sorted(field for field in ZATKA_HAAS_REQUIRED_FIELDS if field not in source)
    if missing:
        raise ValueError(f"Missing required Zatka-Haas trial fields: {', '.join(missing)}")

    left_contrast = _stimulus_contrast(source, 0)
    right_contrast = _stimulus_contrast(source, 1)
    left_percent = _contrast_percent(left_contrast)
    right_percent = _contrast_percent(right_contrast)
    signed_contrast = _signed_contrast_percent(left_contrast, right_contrast)
    choice_code = _scalar(source.get("response"))
    response_time, response_time_origin = _response_time(source)
    source_subject = _source_id(source.get("subjectID"))
    source_session = _source_id(source.get("sessionID"))
    selected_subject_id = subject_id or source_subject
    selected_session_id = session_id or source_session or DEFAULT_ZATKA_HAAS_SESSION_ID

    task_variables = {
        "left_contrast": left_percent,
        "right_contrast": right_percent,
        "signed_contrast_difference": signed_contrast,
        "source_response_code": _json_safe_value(choice_code),
        "source_feedback_type": _json_safe_value(_scalar(source.get("feedbackType"))),
        "source_session_id": source_session,
        "source_subject_id": source_subject,
        "repeat_num": _json_safe_value(_scalar(source.get("repeatNum"))),
        "prev_response": _json_safe_value(_scalar(source.get("prev_response"))),
        "prev_feedback": _json_safe_value(_scalar(source.get("prev_feedback"))),
        "prev_stimulus": _json_safe_value(source.get("prev_stimulus")),
        "laser_type": _json_safe_value(_scalar(source.get("laserType"))),
        "laser_region": _json_safe_value(_scalar(source.get("laserRegion"))),
        "laser_coord": _json_safe_value(source.get("laserCoord")),
        "laser_power": _json_safe_value(_scalar(source.get("laserPower"))),
        "laser_duration": _json_safe_value(_scalar(source.get("laserDuration"))),
        "laser_onset": _json_safe_value(_scalar(source.get("laserOnset"))),
        "laser_idx": _json_safe_value(_scalar(source.get("laserIdx"))),
        "time_stimulus_on": _json_safe_value(_scalar(source.get("time_stimulusOn"))),
        "time_go_cue": _json_safe_value(_scalar(source.get("time_goCue"))),
        "time_start_move": _json_safe_value(_scalar(source.get("time_startMove"))),
        "time_choice_made": _json_safe_value(_scalar(source.get("time_choiceMade"))),
        "time_feedback": _json_safe_value(_scalar(source.get("time_feedback"))),
        "no_go_condition": _is_zero(left_contrast) and _is_zero(right_contrast),
        "bilateral_condition": _is_positive(left_contrast) and _is_positive(right_contrast),
    }

    return CanonicalTrial(
        protocol_id=ZATKA_HAAS_PROTOCOL_ID,
        dataset_id=ZATKA_HAAS_DATASET_ID,
        subject_id=selected_subject_id,
        session_id=selected_session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_contrast,
        stimulus_units="percent contrast difference, right minus left",
        stimulus_side=_stimulus_side(left_contrast, right_contrast),
        evidence_strength=abs(signed_contrast) if signed_contrast is not None else None,
        evidence_units="percent contrast difference",
        choice=zatka_haas_choice_label(choice_code),
        correct=_correct_label(source.get("feedbackType")),
        response_time=response_time,
        response_time_origin=response_time_origin,
        feedback=_feedback_label(source.get("feedbackType")),
        task_variables={key: value for key, value in task_variables.items() if value is not None},
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_zatka_haas_visual_trials(
    source: dict[str, Any],
    *,
    session_id: str = DEFAULT_ZATKA_HAAS_SESSION_ID,
    subject_id: str | None = None,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    missing = sorted(field for field in ZATKA_HAAS_REQUIRED_FIELDS if field not in source)
    if missing:
        raise ValueError(f"Missing required Zatka-Haas fields: {', '.join(missing)}")
    n_trials = _n_trials(source)
    if limit is not None:
        n_trials = min(n_trials, limit)
    trials: list[CanonicalTrial] = []
    for index in range(n_trials):
        row = _source_row(source, index)
        row_session = _source_id(row.get("sessionID")) or session_id
        row_subject = _source_id(row.get("subjectID")) or subject_id
        trials.append(
            harmonize_zatka_haas_visual_trial(
                row,
                session_id=row_session,
                subject_id=row_subject,
                trial_index=index,
            )
        )
    return trials


def summarize_zatka_haas_choice_by_signed_contrast(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[float | None, list[CanonicalTrial]] = {}
    for trial in trials:
        grouped.setdefault(trial.stimulus_value, []).append(trial)
    return [
        {"stimulus_value": stimulus_value, **_choice_summary_counts(group)}
        for stimulus_value, group in sorted(
            grouped.items(),
            key=lambda item: _none_safe_float(item[0]),
        )
    ]


def summarize_zatka_haas_choice_by_contrast_pair(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[float | None, float | None], list[CanonicalTrial]] = {}
    for trial in trials:
        key = (
            _task_float(trial, "left_contrast"),
            _task_float(trial, "right_contrast"),
        )
        grouped.setdefault(key, []).append(trial)
    return [
        {
            "left_contrast": left_contrast,
            "right_contrast": right_contrast,
            **_choice_summary_counts(group),
        }
        for (left_contrast, right_contrast), group in sorted(
            grouped.items(),
            key=lambda item: (_none_safe_float(item[0][0]), _none_safe_float(item[0][1])),
        )
    ]


def summarize_zatka_haas_choice_by_laser_state(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float | None], list[CanonicalTrial]] = {}
    for trial in trials:
        key = (_laser_state_label(trial), trial.stimulus_value)
        grouped.setdefault(key, []).append(trial)
    return [
        {
            "laser_state": laser_state,
            "stimulus_value": stimulus_value,
            **_choice_summary_counts(group),
        }
        for (laser_state, stimulus_value), group in sorted(
            grouped.items(),
            key=lambda item: (_laser_state_sort_key(item[0][0]), _none_safe_float(item[0][1])),
        )
    ]


def summarize_zatka_haas_choice_by_laser_region(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float | None], list[CanonicalTrial]] = {}
    for trial in trials:
        key = (_laser_region_label(trial), trial.stimulus_value)
        grouped.setdefault(key, []).append(trial)
    return [
        {
            "laser_region": laser_region,
            "stimulus_value": stimulus_value,
            **_choice_summary_counts(group),
        }
        for (laser_region, stimulus_value), group in sorted(
            grouped.items(),
            key=lambda item: (_laser_region_sort_key(item[0][0]), _none_safe_float(item[0][1])),
        )
    ]


def summarize_zatka_haas_perturbation_deltas(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    region_rows = summarize_zatka_haas_choice_by_laser_region(trials)
    non_laser_by_stimulus = {
        row.get("stimulus_value"): row
        for row in region_rows
        if row.get("laser_region") == "non_laser"
    }
    delta_rows: list[dict[str, Any]] = []
    for laser_row in region_rows:
        laser_region = str(laser_row.get("laser_region") or "unknown_laser_region")
        if laser_region == "non_laser":
            continue
        non_laser_row = non_laser_by_stimulus.get(laser_row.get("stimulus_value"))
        if non_laser_row is None:
            continue
        metadata = _perturbation_region_metadata(laser_region)
        delta_rows.append(
            {
                "laser_region": laser_region,
                **metadata,
                "stimulus_value": laser_row.get("stimulus_value"),
                "n_laser_trials": _int_count(laser_row.get("n_trials")),
                "n_non_laser_trials": _int_count(non_laser_row.get("n_trials")),
                "n_laser_left": _int_count(laser_row.get("n_left")),
                "n_laser_right": _int_count(laser_row.get("n_right")),
                "n_laser_withhold": _int_count(laser_row.get("n_withhold")),
                "n_laser_choice": _int_count(laser_row.get("n_choice")),
                "n_non_laser_left": _int_count(non_laser_row.get("n_left")),
                "n_non_laser_right": _int_count(non_laser_row.get("n_right")),
                "n_non_laser_withhold": _int_count(non_laser_row.get("n_withhold")),
                "n_non_laser_choice": _int_count(non_laser_row.get("n_choice")),
                "p_right_laser": laser_row.get("p_right"),
                "p_right_non_laser": non_laser_row.get("p_right"),
                "delta_p_right": _row_delta(laser_row, non_laser_row, "p_right"),
                "p_withhold_laser": laser_row.get("p_withhold"),
                "p_withhold_non_laser": non_laser_row.get("p_withhold"),
                "delta_p_withhold": _row_delta(laser_row, non_laser_row, "p_withhold"),
                "p_correct_laser": laser_row.get("p_correct"),
                "p_correct_non_laser": non_laser_row.get("p_correct"),
                "delta_p_correct": _row_delta(laser_row, non_laser_row, "p_correct"),
                "median_response_time_laser": laser_row.get("median_response_time"),
                "median_response_time_non_laser": non_laser_row.get("median_response_time"),
                "delta_median_response_time": _row_delta(
                    laser_row,
                    non_laser_row,
                    "median_response_time",
                ),
            }
        )
    return sorted(
        delta_rows,
        key=lambda row: (
            _laser_region_sort_key(str(row["laser_region"])),
            _none_safe_float(row["stimulus_value"]),
        ),
    )


def summarize_zatka_haas_perturbation_region_effects(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    return _summarize_zatka_haas_perturbation_region_effects_from_deltas(
        summarize_zatka_haas_perturbation_deltas(trials)
    )


def analyze_zatka_haas_visual_decision(trials: list[CanonicalTrial]) -> dict[str, Any]:
    summary_rows = summarize_zatka_haas_choice_by_signed_contrast(trials)
    condition_rows = summarize_zatka_haas_choice_by_contrast_pair(trials)
    laser_state_rows = summarize_zatka_haas_choice_by_laser_state(trials)
    laser_region_rows = summarize_zatka_haas_choice_by_laser_region(trials)
    perturbation_delta_rows = summarize_zatka_haas_perturbation_deltas(trials)
    perturbation_region_effect_rows = (
        _summarize_zatka_haas_perturbation_region_effects_from_deltas(
            perturbation_delta_rows
        )
    )
    fit_rows = [
        {
            "stimulus_value": row["stimulus_value"],
            "n_right": row["n_right"],
            "n_response": row["n_choice"],
            "p_right": row["p_right"],
        }
        for row in summary_rows
    ]
    choice_fit = fit_psychometric_rows(
        fit_rows,
        stimulus_metric_name="contrast_difference",
    )
    return {
        "analysis_id": "analysis.zatka-haas-visual-decision.descriptive-choice-surface",
        "analysis_type": "descriptive_choice_surface",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": ZATKA_HAAS_PROTOCOL_ID,
        "dataset_id": ZATKA_HAAS_DATASET_ID,
        "report_title": "Zatka-Haas Inactivation Visual Decision Report",
        "n_trials": len(trials),
        "n_response_trials": sum(1 for trial in trials if trial.choice in {"left", "right"}),
        "n_choice_trials": sum(1 for trial in trials if trial.choice in {"left", "right"}),
        "n_withhold_trials": sum(1 for trial in trials if trial.choice == "withhold"),
        "n_unknown_choice_trials": sum(1 for trial in trials if trial.choice == "unknown"),
        "n_laser_trials": sum(1 for trial in trials if _trial_has_laser(trial)),
        "n_contrast_conditions": len(condition_rows),
        "response_time_origin": "D.RT or timing-derived fallback",
        "stimulus_label": "Signed contrast difference",
        "stimulus_units": "percent contrast difference, right minus left",
        "summary_rows": summary_rows,
        "condition_rows": condition_rows,
        "laser_state_rows": laser_state_rows,
        "laser_region_rows": laser_region_rows,
        "perturbation_delta_rows": perturbation_delta_rows,
        "perturbation_region_effect_rows": perturbation_region_effect_rows,
        "laser_state_counts": _group_count_rows(trials, _laser_state_label, "laser_state"),
        "laser_region_counts": _group_count_rows(trials, _laser_region_label, "laser_region"),
        "perturbation_delta_count": len(perturbation_delta_rows),
        "perturbation_region_effect_count": len(perturbation_region_effect_rows),
        "choice_psychometric_fit": choice_fit,
        "caveats": [
            "NoGo trials are represented as canonical withhold choices.",
            (
                "Laser and inactivation variables are kept in task_variables for explicit "
                "stratification."
            ),
            "This adapter targets processed behavioral D structs before neural-heavy joins.",
            (
                "The top-level binary psychometric fit excludes withhold choices and pools "
                "laser and non-laser trials; laser_state_rows and laser_region_rows preserve "
                "the operational perturbation splits for comparison."
            ),
            (
                "Perturbation delta rows compare each laser region only to non-laser "
                "trials at the same signed contrast; the compact region effects reuse "
                "that matched baseline across regions and are descriptive, not causal "
                "model estimates."
            ),
        ],
    }


def write_zatka_haas_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, ZATKA_HAAS_CHOICE_SUMMARY_FIELDS)


def write_zatka_haas_condition_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, ZATKA_HAAS_CONDITION_SUMMARY_FIELDS)


def write_zatka_haas_laser_state_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, ZATKA_HAAS_LASER_STATE_SUMMARY_FIELDS)


def write_zatka_haas_laser_region_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, ZATKA_HAAS_LASER_REGION_SUMMARY_FIELDS)


def write_zatka_haas_perturbation_delta_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    _write_csv(path, rows, ZATKA_HAAS_PERTURBATION_DELTA_FIELDS)


def write_zatka_haas_perturbation_region_effect_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    _write_csv(path, rows, ZATKA_HAAS_PERTURBATION_REGION_EFFECT_FIELDS)


def write_zatka_haas_choice_svg(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(zatka_haas_choice_svg(summary_rows), encoding="utf-8")


def write_zatka_haas_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    choice_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        zatka_haas_report_html(
            analysis_result,
            provenance=provenance,
            choice_svg_text=choice_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def zatka_haas_provenance_payload(
    *,
    source_file: Path,
    session_id: str,
    details: dict[str, Any],
    trials: list[CanonicalTrial],
    output_files: dict[str, str],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": ZATKA_HAAS_PROTOCOL_ID,
        "dataset_id": ZATKA_HAAS_DATASET_ID,
        "source": {
            "source_file": str(source_file),
            "source_file_size_bytes": source_file.stat().st_size if source_file.exists() else None,
            "source_file_sha256": _sha256(source_file) if source_file.exists() else None,
            "figshare_url": ZATKA_HAAS_FIGSHARE_URL,
            "figshare_doi": ZATKA_HAAS_SOURCE_DOI,
            "archive_member": ZATKA_HAAS_HIGHER_POWER_MEMBER
            if source_file.name == "Inactivation_HigherPower.mat"
            else None,
            "source_fields": details.get("source_fields", []),
            "n_source_trials": details.get("n_trials"),
            "source_variable": details.get("source_variable", "D"),
        },
        "source_fields": sorted(ZATKA_HAAS_REQUIRED_FIELDS | ZATKA_HAAS_OPTIONAL_FIELDS),
        "n_trials": len(trials),
        "exclusions": {
            "missing_stimulus": sum(1 for trial in trials if trial.stimulus_value is None),
            "withhold_choices": sum(1 for trial in trials if trial.choice == "withhold"),
            "unknown_choice": sum(1 for trial in trials if trial.choice == "unknown"),
            "missing_response_time": sum(1 for trial in trials if trial.response_time is None),
            "laser_trials": sum(1 for trial in trials if _trial_has_laser(trial)),
        },
        "outputs": output_files,
        "caveats": [
            (
                "This behavior-first adapter targets processed D structs from the large "
                "Figshare archive."
            ),
            "Neural and widefield joins are deferred until behavioral field coverage is verified.",
        ],
    }


def zatka_haas_choice_svg(summary_rows: list[dict[str, Any]]) -> str:
    width = 720
    height = 420
    left = 72
    right = 28
    top = 30
    bottom = 62
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [
        float(row["stimulus_value"])
        for row in summary_rows
        if row.get("stimulus_value") is not None
    ]
    if not values:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No Zatka-Haas choice data available</text></svg>\n'
        )

    x_min = min(values)
    x_max = max(values)
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def y_scale(value: float) -> float:
        return top + (1.0 - value) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 18}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14">Signed contrast difference (%; right '
        "positive)</text>",
        f'<text x="18" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 18 '
        f'{top + plot_height / 2})">Choice probability</text>',
    ]
    for y_value in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = y_scale(y_value)
        elements.append(
            f'<line x1="{left - 4}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" '
            'stroke="#ddd"/>'
        )
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{y_value:.2g}</text>'
        )
    for x_value in _axis_tick_values(x_min, x_max):
        x = x_scale(x_value)
        elements.append(
            f'<line x1="{x:.1f}" y1="{top + plot_height}" x2="{x:.1f}" '
            f'y2="{top + plot_height + 4}" stroke="#222"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="10">{x_value:g}</text>'
        )

    series = [
        ("p_right", "P(right | movement)", "#145f91"),
        ("p_withhold", "P(withhold)", "#8a4b0f"),
    ]
    for index, (key, label, color) in enumerate(series):
        points = []
        for row in sorted(summary_rows, key=lambda item: _none_safe_float(item["stimulus_value"])):
            if row.get("stimulus_value") is None or row.get(key) is None:
                continue
            points.append(
                (
                    x_scale(float(row["stimulus_value"])),
                    y_scale(float(row[key])),
                    int(row["n_trials"]),
                )
            )
        if not points:
            continue
        point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        elements.append(
            f'<polyline points="{point_attr}" fill="none" stroke="{color}" stroke-width="2"/>'
        )
        for x, y, n_trials in points:
            radius = 3.0 + min(n_trials, 100) / 50.0
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" '
                'fill-opacity="0.75"/>'
            )
        legend_y = top + 18 + index * 20
        elements.append(
            f'<line x1="{left + 12}" y1="{legend_y}" x2="{left + 36}" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2"/>'
        )
        elements.append(
            f'<text x="{left + 44}" y="{legend_y + 4}" font-family="sans-serif" '
            f'font-size="12">{escape(label)}</text>'
        )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def zatka_haas_report_html(
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    choice_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    provenance = provenance or {}
    artifact_links = artifact_links or {}
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    title = str(analysis_result.get("report_title") or "Zatka-Haas Visual Decision Report")
    svg = choice_svg_text or (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        '<text x="20" y="60">Choice summary plot not available</text></svg>'
    )
    fit = analysis_result.get("choice_psychometric_fit")
    if not isinstance(fit, dict):
        fit = {}
    metrics = [
        ("Trials", analysis_result.get("n_trials")),
        ("Left choices", _choice_count(analysis_result, "n_left")),
        ("Right choices", _choice_count(analysis_result, "n_right")),
        ("Withhold choices", analysis_result.get("n_withhold_trials")),
        ("Laser trials", analysis_result.get("n_laser_trials")),
        ("Contrast conditions", analysis_result.get("n_contrast_conditions")),
        ("Matched perturbation rows", analysis_result.get("perturbation_delta_count")),
        ("Perturbation regions", analysis_result.get("perturbation_region_effect_count")),
        ("Fit status", fit.get("status")),
    ]

    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title>",
        "<style>",
        _report_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        f"<p class=\"eyebrow\">{escape(str(analysis_result.get('analysis_id', 'analysis')))}</p>",
        f"<h1>{escape(title)}</h1>",
        "<p class=\"lede\">Behavior-first visual contrast report for the public "
        "Zatka-Haas higher-power optogenetic inactivation table, keeping left, "
        "right, and NoGo choices distinct from perturbation variables.</p>",
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
                    ("Session", provenance.get("session_id")),
                    ("Source file", source.get("source_file")),
                    ("Source variable", source.get("source_variable")),
                    ("Figshare DOI", source.get("figshare_doi")),
                    ("Source trials", source.get("n_source_trials")),
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
            "<h2>Choice Summary</h2>",
            '<div class="figure-wrap">',
            svg,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Signed Contrast Summary</h2>",
            _html_table(
                analysis_result.get("summary_rows", []),
                [
                    ("stimulus_value", "Signed contrast"),
                    ("n_trials", "Trials"),
                    ("n_left", "Left"),
                    ("n_right", "Right"),
                    ("n_withhold", "Withhold"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_correct", "P(correct)"),
                    ("median_response_time", "Median RT"),
                    ("n_laser_trials", "Laser trials"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Contrast-Pair Conditions</h2>",
            _html_table(
                analysis_result.get("condition_rows", []),
                [
                    ("left_contrast", "Left contrast"),
                    ("right_contrast", "Right contrast"),
                    ("n_trials", "Trials"),
                    ("n_left", "Left"),
                    ("n_right", "Right"),
                    ("n_withhold", "Withhold"),
                    ("p_correct", "P(correct)"),
                    ("n_laser_trials", "Laser trials"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Laser-State Summary</h2>",
            _html_table(
                analysis_result.get("laser_state_rows", []),
                [
                    ("laser_state", "Laser state"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_trials", "Trials"),
                    ("n_left", "Left"),
                    ("n_right", "Right"),
                    ("n_withhold", "Withhold"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_correct", "P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Laser-Region Summary</h2>",
            _html_table(
                analysis_result.get("laser_region_rows", []),
                [
                    ("laser_region", "Laser region"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_trials", "Trials"),
                    ("n_left", "Left"),
                    ("n_right", "Right"),
                    ("n_withhold", "Withhold"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("p_correct", "P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Perturbation Deltas vs Non-Laser</h2>",
            _html_table(
                analysis_result.get("perturbation_delta_rows", []),
                [
                    ("laser_region", "Laser region"),
                    ("stimulus_value", "Signed contrast"),
                    ("n_laser_trials", "Laser trials"),
                    ("n_non_laser_trials", "Non-laser trials"),
                    ("delta_p_right", "Delta P(right)"),
                    ("delta_p_withhold", "Delta P(withhold)"),
                    ("delta_p_correct", "Delta P(correct)"),
                    ("delta_median_response_time", "Delta median RT"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Perturbation Region Effects</h2>",
            _html_table(
                analysis_result.get("perturbation_region_effect_rows", []),
                [
                    ("laser_region", "Laser region"),
                    ("region_family", "Region family"),
                    ("hemisphere", "Hemisphere"),
                    ("n_matched_contrasts", "Matched contrasts"),
                    ("n_laser_trials", "Laser trials"),
                    ("n_non_laser_trials", "Non-laser trials"),
                    ("weighted_delta_p_right", "Weighted delta P(right)"),
                    ("weighted_delta_p_withhold", "Weighted delta P(withhold)"),
                    ("weighted_delta_p_correct", "Weighted delta P(correct)"),
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


def zatka_haas_choice_label(value: Any) -> str:
    code = _scalar(value)
    if code is None:
        return "unknown"
    try:
        numeric = int(float(code))
    except (TypeError, ValueError):
        return "unknown"
    if numeric == 1:
        return "left"
    if numeric == 2:
        return "right"
    if numeric == 3:
        return "withhold"
    return "unknown"


def _source_row(source: dict[str, Any], index: int) -> dict[str, Any]:
    return {field: _row_value(value, index) for field, value in source.items()}


def _n_trials(source: dict[str, Any]) -> int:
    counts = []
    for field in sorted(ZATKA_HAAS_REQUIRED_FIELDS):
        value = np.asarray(source[field])
        if value.ndim == 0:
            counts.append(1)
        else:
            counts.append(int(value.shape[0]))
    if len(set(counts)) != 1:
        raise ValueError(f"Inconsistent Zatka-Haas field lengths: {counts}")
    return counts[0]


def _row_value(value: Any, index: int) -> Any:
    arr = np.asarray(value)
    if arr.ndim == 0:
        return arr.item()
    if arr.ndim == 1:
        value = arr[index]
        if isinstance(value, np.ndarray):
            if value.size == 0:
                return None
            if value.size == 1:
                return value.reshape(-1)[0].item()
            return value
        return value.item() if hasattr(value, "item") else value
    row = arr[index]
    if isinstance(row, np.ndarray) and row.size == 1:
        return row.reshape(-1)[0].item()
    return row


def _stimulus_contrast(source: dict[str, Any], side_index: int) -> Any:
    stimulus = np.asarray(source.get("stimulus"))
    if stimulus.ndim == 1 and stimulus.size >= 2:
        return stimulus[side_index]
    if stimulus.ndim >= 2 and stimulus.shape[-1] >= 2:
        return stimulus[..., side_index].reshape(-1)[0]
    return None


def _signed_contrast_percent(left: Any, right: Any) -> float | None:
    left_value = _numeric(left)
    right_value = _numeric(right)
    if left_value is None or right_value is None:
        return None
    return round(100.0 * (right_value - left_value), 6)


def _contrast_percent(value: Any) -> float | None:
    numeric = _numeric(value)
    if numeric is None:
        return None
    return round(100.0 * numeric, 6)


def _stimulus_side(left: Any, right: Any) -> str:
    left_value = _numeric(left)
    right_value = _numeric(right)
    if left_value is None or right_value is None:
        return "unknown"
    if _is_zero(left_value) and _is_zero(right_value):
        return "none"
    if right_value > left_value:
        return "right"
    if left_value > right_value:
        return "left"
    return "unknown"


def _response_time(source: dict[str, Any]) -> tuple[float | None, str | None]:
    rt = _numeric(_scalar(source.get("RT")))
    if rt is not None:
        return rt, "D.RT"
    response_time = _numeric(_scalar(source.get("responseTime")))
    go_cue = _numeric(_scalar(source.get("time_goCue")))
    if response_time is not None and go_cue is not None:
        return response_time - go_cue, "D.responseTime - D.time_goCue"
    choice_time = _numeric(_scalar(source.get("time_choiceMade")))
    stim_time = _numeric(_scalar(source.get("time_stimulusOn")))
    if choice_time is not None and stim_time is not None:
        return choice_time - stim_time, "D.time_choiceMade - D.time_stimulusOn"
    return None, None


def _correct_label(value: Any) -> bool | None:
    numeric = _numeric(_scalar(value))
    if numeric is None:
        return None
    if numeric > 0:
        return True
    return False


def _feedback_label(value: Any) -> str:
    correct = _correct_label(value)
    if correct is True:
        return "reward"
    if correct is False:
        return "error"
    return "unknown"


def _source_id(value: Any) -> str | None:
    scalar = _scalar(value)
    safe = _json_safe_value(scalar)
    if safe is None:
        return None
    if isinstance(safe, float) and safe.is_integer():
        return str(int(safe))
    return str(safe)


def _scalar(value: Any) -> Any:
    if value is None:
        return None
    arr = np.asarray(value)
    if arr.size == 0:
        return None
    if arr.size == 1:
        item = arr.reshape(-1)[0]
        return item.item() if hasattr(item, "item") else item
    return value


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _is_zero(value: Any) -> bool:
    numeric = _numeric(value)
    return numeric is not None and abs(numeric) <= 1e-12


def _is_positive(value: Any) -> bool:
    numeric = _numeric(value)
    return numeric is not None and numeric > 0


def _mat_object_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "_fieldnames"):
        return {field: getattr(value, field) for field in value._fieldnames}
    arr = np.asarray(value)
    if arr.dtype.names:
        record = arr.reshape(-1)[0]
        return {field: record[field] for field in arr.dtype.names}
    if isinstance(value, dict):
        return dict(value)
    raise TypeError(f"Unsupported MATLAB object for Zatka-Haas source: {type(value)!r}")


def _load_zatka_haas_hdf5_table(path: Path, *, variable: str) -> dict[str, Any]:
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - exercised only without optional deps
        raise ImportError(
            "Loading MATLAB v7.3 Zatka-Haas files requires h5py; install the nwb "
            "or allen extra, or add h5py to the environment."
        ) from exc

    with h5py.File(path, "r") as handle:
        if variable not in handle:
            available = ", ".join(sorted(key for key in handle.keys() if not key.startswith("#")))
            raise KeyError(f"Variable {variable!r} not found in {path}; available: {available}")
        table = handle[variable]
        matlab_class = _hdf5_attr_text(table.attrs.get("MATLAB_class"))
        if matlab_class != "table":
            raise TypeError(
                f"Variable {variable!r} in {path} is MATLAB class {matlab_class!r}, expected table"
            )
        names, value_refs = _hdf5_table_variable_refs(handle)
        supported = ZATKA_HAAS_REQUIRED_FIELDS | ZATKA_HAAS_OPTIONAL_FIELDS
        return {
            name: _hdf5_table_value(handle, name, value_ref)
            for name, value_ref in zip(names, value_refs, strict=True)
            if name in supported
        }


def _looks_like_hdf5(path: Path) -> bool:
    try:
        import h5py
    except ImportError:
        pass
    else:
        try:
            return bool(h5py.is_hdf5(path))
        except OSError:
            return False
    try:
        with path.open("rb") as handle:
            header = handle.read(128)
            return header.startswith(b"\x89HDF\r\n\x1a\n") or (
                header.startswith(b"MATLAB 7.3") and b"HDF5" in header
            )
    except OSError:
        return False


def _hdf5_table_variable_refs(handle: Any) -> tuple[list[str], list[Any]]:
    refs = handle.get("#refs#")
    if refs is None:
        raise TypeError("MATLAB v7.3 table is missing #refs# group")

    if "1" in refs and "y" in refs:
        names = _hdf5_cellstr(handle, refs["1"])
        value_refs = list(np.asarray(refs["y"]).reshape(-1))
        if ZATKA_HAAS_REQUIRED_FIELDS.issubset(set(names)) and len(names) == len(value_refs):
            return names, value_refs

    name_candidates: list[tuple[Any, list[str]]] = []
    for item in refs.values():
        if not _is_hdf5_ref_cell(item):
            continue
        names = _hdf5_cellstr(handle, item)
        if ZATKA_HAAS_REQUIRED_FIELDS.issubset(set(names)):
            name_candidates.append((item, names))
    if not name_candidates:
        raise TypeError("Could not find Zatka-Haas table variable names in MATLAB v7.3 file")

    name_cell, names = max(name_candidates, key=lambda item: len(item[1]))
    for item in refs.values():
        if item.name == name_cell.name or not _is_hdf5_ref_cell(item):
            continue
        value_refs = list(np.asarray(item).reshape(-1))
        if len(value_refs) == len(names) and _hdf5_ref_cell_looks_like_table_values(
            handle, value_refs
        ):
            return names, value_refs
    raise TypeError("Could not pair Zatka-Haas table variable names with value references")


def _is_hdf5_ref_cell(item: Any) -> bool:
    return hasattr(item, "dtype") and item.dtype == object


def _hdf5_ref_cell_looks_like_table_values(handle: Any, refs: list[Any]) -> bool:
    for ref in refs[: min(len(refs), 8)]:
        if not ref:
            continue
        obj = handle[ref]
        if hasattr(obj, "dtype") and obj.dtype != object and np.asarray(obj).size > 100:
            return True
    return False


def _hdf5_cellstr(handle: Any, dataset: Any) -> list[str]:
    values: list[str] = []
    for ref in np.asarray(dataset).reshape(-1):
        if not ref:
            values.append("")
            continue
        values.append(_decode_hdf5_char_dataset(handle[ref]))
    return values


def _decode_hdf5_char_dataset(dataset: Any) -> str:
    arr = np.asarray(dataset).reshape(-1)
    return "".join(chr(int(value)) for value in arr if int(value) != 0)


def _hdf5_table_value(handle: Any, field_name: str, value_ref: Any) -> Any:
    dataset = handle[value_ref]
    if field_name == "laserRegion":
        categorical = _decode_hdf5_laser_region(handle)
        if categorical is not None:
            return categorical
    return _orient_hdf5_table_array(np.asarray(dataset))


def _decode_hdf5_laser_region(handle: Any) -> np.ndarray | None:
    refs = handle.get("#refs#")
    if refs is None or "x" not in refs or "c" not in refs:
        return None
    codes = np.asarray(refs["x"]).reshape(-1)
    category_names = _hdf5_cellstr(handle, refs["c"])
    if not category_names:
        return None
    labels: list[str | None] = []
    for value in codes:
        code = int(value)
        if code <= 0:
            labels.append(None)
        elif code <= len(category_names):
            labels.append(category_names[code - 1])
        else:
            labels.append(None)
    return np.asarray(labels, dtype=object)


def _orient_hdf5_table_array(value: np.ndarray) -> np.ndarray:
    if value.ndim != 2:
        return value
    if 1 in value.shape:
        return value.reshape(-1)
    if value.shape[0] <= 4 and value.shape[1] > value.shape[0]:
        return value.T
    return value


def _hdf5_attr_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.bytes_):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _matlab_behavior_fields(line: str) -> set[str]:
    fields = set(re.findall(r"\b(?:D|dd|E|data|fit\.data)\.([A-Za-z]\w+)", line))
    if "D.stimulus" in line or "dd.contrastLeft" in line:
        fields.add("stimulus")
    if "dd.choice" in line:
        fields.add("response")
    return fields


def _data_path_mentions(line: str) -> list[str]:
    normalized = line.replace("\\", "/")
    paths = []
    for match in re.finditer(r"['\"](?P<path>(?:\.\./)?data/[^'\"]+)['\"]", normalized):
        path = match.group("path")
        if path:
            paths.append(path)
    return paths


def _is_embedded_git_path(name: str) -> bool:
    return "/.git/" in name or name.startswith(".git/")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _choice_summary_counts(trials: list[CanonicalTrial]) -> dict[str, Any]:
    n_trials = len(trials)
    n_left = sum(1 for trial in trials if trial.choice == "left")
    n_right = sum(1 for trial in trials if trial.choice == "right")
    n_withhold = sum(1 for trial in trials if trial.choice == "withhold")
    n_unknown = sum(1 for trial in trials if trial.choice == "unknown")
    n_choice = n_left + n_right
    correct_values = [trial.correct for trial in trials if trial.correct is not None]
    response_times = [
        float(trial.response_time)
        for trial in trials
        if trial.response_time is not None and math.isfinite(float(trial.response_time))
    ]
    return {
        "n_trials": n_trials,
        "n_left": n_left,
        "n_right": n_right,
        "n_withhold": n_withhold,
        "n_unknown": n_unknown,
        "n_choice": n_choice,
        "p_left": _safe_ratio(n_left, n_choice),
        "p_right": _safe_ratio(n_right, n_choice),
        "p_withhold": _safe_ratio(n_withhold, n_trials),
        "n_correct": sum(1 for value in correct_values if value),
        "p_correct": _safe_ratio(sum(1 for value in correct_values if value), len(correct_values)),
        "median_response_time": _median(response_times),
        "n_laser_trials": sum(1 for trial in trials if _trial_has_laser(trial)),
    }


def _trial_has_laser(trial: CanonicalTrial) -> bool:
    laser_type = _numeric(trial.task_variables.get("laser_type"))
    laser_power = _numeric(trial.task_variables.get("laser_power"))
    return (laser_type is not None and laser_type > 0) or (
        laser_power is not None and laser_power > 0
    )


def _laser_state_label(trial: CanonicalTrial) -> str:
    return "laser" if _trial_has_laser(trial) else "non_laser"


def _laser_region_label(trial: CanonicalTrial) -> str:
    if not _trial_has_laser(trial):
        return "non_laser"
    region = trial.task_variables.get("laser_region")
    if isinstance(region, str) and region.strip():
        return region.strip()
    laser_idx = _numeric(trial.task_variables.get("laser_idx"))
    if laser_idx is not None and laser_idx > 0:
        return f"laser_idx_{int(laser_idx)}"
    return "unknown_laser_region"


def _laser_state_sort_key(value: str) -> tuple[int, str]:
    order = {"non_laser": 0, "laser": 1}
    return (order.get(value, 99), value)


def _laser_region_sort_key(value: str) -> tuple[int, str]:
    if value == "non_laser":
        return (0, value)
    if value == "unknown_laser_region":
        return (98, value)
    return (1, value)


def _group_count_rows(
    trials: list[CanonicalTrial],
    labeler: Any,
    field_name: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[CanonicalTrial]] = {}
    for trial in trials:
        grouped.setdefault(str(labeler(trial)), []).append(trial)
    sort_key = _laser_state_sort_key if field_name == "laser_state" else _laser_region_sort_key
    return [
        {
            field_name: label,
            "n_trials": len(group),
            "n_laser_trials": sum(1 for trial in group if _trial_has_laser(trial)),
            "n_withhold": sum(1 for trial in group if trial.choice == "withhold"),
            "n_choice": sum(1 for trial in group if trial.choice in {"left", "right"}),
        }
        for label, group in sorted(grouped.items(), key=lambda item: sort_key(item[0]))
    ]


def _summarize_zatka_haas_perturbation_region_effects_from_deltas(
    delta_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in delta_rows:
        key = (
            str(row.get("laser_region") or "unknown_laser_region"),
            str(row.get("region_family") or "unknown"),
            str(row.get("hemisphere") or "unknown"),
        )
        grouped.setdefault(key, []).append(row)

    effect_rows = []
    for (laser_region, region_family, hemisphere), rows in sorted(
        grouped.items(),
        key=lambda item: _laser_region_sort_key(item[0][0]),
    ):
        effect_rows.append(
            {
                "laser_region": laser_region,
                "region_family": region_family,
                "hemisphere": hemisphere,
                "n_matched_contrasts": len(rows),
                "stimulus_values": _matched_stimulus_values(rows),
                "n_laser_trials": sum(_int_count(row.get("n_laser_trials")) for row in rows),
                "n_non_laser_trials": sum(
                    _int_count(row.get("n_non_laser_trials")) for row in rows
                ),
                "weighted_delta_p_right": _weighted_delta(
                    rows,
                    "delta_p_right",
                    "n_laser_choice",
                    "n_non_laser_choice",
                ),
                "weighted_delta_p_withhold": _weighted_delta(
                    rows,
                    "delta_p_withhold",
                    "n_laser_trials",
                    "n_non_laser_trials",
                ),
                "weighted_delta_p_correct": _weighted_delta(
                    rows,
                    "delta_p_correct",
                    "n_laser_trials",
                    "n_non_laser_trials",
                ),
                "weighted_delta_median_response_time": _weighted_delta(
                    rows,
                    "delta_median_response_time",
                    "n_laser_trials",
                    "n_non_laser_trials",
                ),
                "max_abs_delta_p_right": _max_abs_delta(rows, "delta_p_right"),
                "max_abs_delta_p_withhold": _max_abs_delta(rows, "delta_p_withhold"),
            }
        )
    return effect_rows


def _perturbation_region_metadata(laser_region: str) -> dict[str, str]:
    return {
        "region_family": _laser_region_family(laser_region),
        "hemisphere": _laser_region_hemisphere(laser_region),
    }


def _laser_region_family(laser_region: str) -> str:
    if laser_region == "non_laser":
        return "non_laser"
    if laser_region == "unknown_laser_region":
        return "unknown"
    if laser_region.startswith("laser_idx_"):
        return "laser_idx"
    match = re.match(r"^(Left|Right|Bilateral|Bilat)(?P<family>.+)$", laser_region)
    if match:
        return match.group("family")
    return laser_region


def _laser_region_hemisphere(laser_region: str) -> str:
    if laser_region == "non_laser":
        return "non_laser"
    lowered = laser_region.lower()
    if lowered.startswith("left"):
        return "left"
    if lowered.startswith("right"):
        return "right"
    if lowered.startswith(("bilateral", "bilat")):
        return "bilateral"
    return "unknown"


def _row_delta(
    laser_row: dict[str, Any],
    non_laser_row: dict[str, Any],
    key: str,
) -> float | None:
    laser_value = _numeric(laser_row.get(key))
    non_laser_value = _numeric(non_laser_row.get(key))
    if laser_value is None or non_laser_value is None:
        return None
    return laser_value - non_laser_value


def _weighted_delta(
    rows: list[dict[str, Any]],
    delta_key: str,
    laser_weight_key: str,
    non_laser_weight_key: str,
) -> float | None:
    weighted_sum = 0.0
    weight_sum = 0
    for row in rows:
        delta = _numeric(row.get(delta_key))
        if delta is None:
            continue
        weight = min(
            _int_count(row.get(laser_weight_key)),
            _int_count(row.get(non_laser_weight_key)),
        )
        if weight <= 0:
            continue
        weighted_sum += delta * weight
        weight_sum += weight
    if weight_sum == 0:
        return None
    return weighted_sum / weight_sum


def _max_abs_delta(rows: list[dict[str, Any]], key: str) -> float | None:
    deltas = [_numeric(row.get(key)) for row in rows]
    finite_deltas = [abs(delta) for delta in deltas if delta is not None]
    if not finite_deltas:
        return None
    return max(finite_deltas)


def _matched_stimulus_values(rows: list[dict[str, Any]]) -> str:
    values = sorted({row.get("stimulus_value") for row in rows}, key=_none_safe_float)
    return ",".join(_compact_number(value) for value in values)


def _compact_number(value: Any) -> str:
    numeric = _numeric(value)
    if numeric is None:
        return "NA"
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:g}"


def _int_count(value: Any) -> int:
    numeric = _numeric(value)
    if numeric is None:
        return 0
    return int(numeric)


def _task_float(trial: CanonicalTrial, key: str) -> float | None:
    return _numeric(trial.task_variables.get(key))


def _none_safe_float(value: Any) -> float:
    numeric = _numeric(value)
    return float("inf") if numeric is None else numeric


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


def _choice_count(analysis_result: dict[str, Any], key: str) -> Any:
    summary_rows = analysis_result.get("summary_rows", [])
    if not isinstance(summary_rows, list):
        return None
    return sum(int(row.get(key, 0) or 0) for row in summary_rows if isinstance(row, dict))


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


def _definition_list(rows: list[tuple[str, Any]]) -> str:
    parts = ["<dl>"]
    for label, value in rows:
        parts.append(f"<dt>{escape(label)}</dt>")
        parts.append(f"<dd>{escape(_format_cell(value))}</dd>")
    parts.append("</dl>")
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
  max-width: 800px;
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
.grid-two {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}
dl {
  display: grid;
  grid-template-columns: minmax(120px, 0.34fr) 1fr;
  gap: 8px 14px;
  margin: 0;
}
dt {
  color: var(--muted);
  font-weight: 800;
}
dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
}
.figure-wrap,
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.figure-wrap {
  padding: 12px;
}
.figure-wrap svg {
  display: block;
  max-width: 100%;
  height: auto;
}
table {
  width: 100%;
  min-width: 800px;
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
  dl {
    grid-template-columns: 1fr;
  }
  .artifact-list {
    columns: 1;
  }
}
""".strip()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        if value.size == 1:
            return _json_safe_value(value.reshape(-1)[0])
        return [_json_safe_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe_value(value.item())
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    return str(value)
