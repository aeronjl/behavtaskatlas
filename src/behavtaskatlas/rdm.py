from __future__ import annotations

import csv
import hashlib
import math
import statistics
import urllib.request
import zipfile
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from behavtaskatlas.models import CanonicalTrial

ROITMAN_RDM_PROTOCOL_ID = "protocol.random-dot-motion-classic-macaque"
ROITMAN_RDM_DATASET_ID = "dataset.roitman-shadlen-rdm-pyddm"
DEFAULT_RDM_RAW_CSV = Path("data/raw/random_dot_motion/roitman_rts.csv")
DEFAULT_RDM_DERIVED_DIR = Path("derived/random_dot_motion")
DEFAULT_RDM_SESSION_ID = "roitman-shadlen-pyddm"
PYDDM_COMMIT = "cf161c11e8f99f18cf805a7ae1da8623faddad86"
DEFAULT_RDM_CSV_URL = (
    "https://raw.githubusercontent.com/mwshinn/PyDDM/"
    f"{PYDDM_COMMIT}/doc/downloads/roitman_rts.csv"
)
RDM_PSYCHOMETRIC_X_AXIS_LABEL = "Signed motion coherence (%; target 1 positive)"

HUMAN_RDM_PROTOCOL_ID = "protocol.human-rdm-button-reaction-time"
HUMAN_RDM_DATASET_ID = "dataset.palmer-huk-shadlen-human-rdm-cosmo2017"
DEFAULT_HUMAN_RDM_RAW_DIR = Path("data/raw/human_random_dot_motion/palmer_huk_shadlen")
DEFAULT_HUMAN_RDM_DERIVED_DIR = Path("derived/human_random_dot_motion")
DEFAULT_HUMAN_RDM_SESSION_ID = "palmer-huk-shadlen-cosmo2017"
COSMO2017_COMMIT = "5fbffc45adea2e7e30407a33931e39fb84219c83"
COSMO2017_REPOSITORY_URL = "https://github.com/DrugowitschLab/CoSMo2017"
COSMO2017_RAW_BASE_URL = (
    f"https://raw.githubusercontent.com/DrugowitschLab/CoSMo2017/{COSMO2017_COMMIT}"
)
HUMAN_RDM_SUBJECT_IDS = ("ah", "eh", "jd", "jp", "mk", "mm")
HUMAN_RDM_SUPPORT_FILES = ("phs_data_README.txt", "LICENSE")
HUMAN_RDM_PSYCHOMETRIC_X_AXIS_LABEL = "Signed motion coherence (%; right positive)"

MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID = "protocol.macaque-rdm-confidence-wager"
MACAQUE_RDM_CONFIDENCE_DATASET_ID = (
    "dataset.khalvati-kiani-rao-rdm-confidence-source-data"
)
DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_ZIP = Path(
    "data/raw/macaque_rdm_confidence_khalvati/source_data.zip"
)
DEFAULT_MACAQUE_RDM_CONFIDENCE_DERIVED_DIR = Path("derived/macaque_rdm_confidence")
DEFAULT_MACAQUE_RDM_CONFIDENCE_SESSION_ID = (
    "khalvati-kiani-rao-natcomm2021-source-data"
)
KHALVATI_RDM_CONFIDENCE_ARTICLE_URL = "https://www.nature.com/articles/s41467-021-25419-4"
KHALVATI_RDM_CONFIDENCE_SOURCE_DATA_URL = (
    "https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-021-25419-4/"
    "MediaObjects/41467_2021_25419_MOESM3_ESM.zip"
)
KHALVATI_RDM_CONFIDENCE_CODE_URL = "https://github.com/koosha66/POMDP-Confidence"
RDM_CHRONOMETRIC_FIELDS = [
    "evidence_strength",
    "n_trials",
    "n_response",
    "n_correct",
    "p_correct",
    "median_response_time",
    "mean_response_time",
]
MACAQUE_RDM_CONFIDENCE_ACCURACY_FIELDS = [
    "source_measure",
    "monkey",
    "motion_strength_percent",
    "n_source_rows",
    "n_correct",
    "p_correct",
    "median_motion_duration_ms",
    "mean_motion_duration_ms",
]
MACAQUE_RDM_CONFIDENCE_CONFIDENCE_FIELDS = [
    "monkey",
    "motion_strength_percent",
    "n_source_rows",
    "n_sure_target",
    "p_sure_target",
    "median_motion_duration_ms",
    "mean_motion_duration_ms",
]

MACAQUE_RDM_CONFIDENCE_SOURCE_TABLES = [
    {
        "source_measure": "accuracy_no_sure_target",
        "figure_panels": "Fig. 1b black dots and Fig. 4a",
        "monkey": "M1",
        "strength_file": "source_data/1b(black dots)&4a_strength_M1.csv",
        "duration_file": "source_data/1b(black dots)&4a_duration_M1.csv",
        "outcome_field": "Correct",
        "sure_target_available": False,
        "sure_target_chosen": None,
        "drop_zero_strength_before_pairing": False,
    },
    {
        "source_measure": "accuracy_no_sure_target",
        "figure_panels": "Fig. 1b black dots and Fig. 4a",
        "monkey": "M2",
        "strength_file": "source_data/1b(black dots)&4a_strength_M2.csv",
        "duration_file": "source_data/1b(black dots)&4a_duration_M2.csv",
        "outcome_field": "Correct",
        "sure_target_available": False,
        "sure_target_chosen": None,
        "drop_zero_strength_before_pairing": False,
    },
    {
        "source_measure": "accuracy_sure_available_direction_chosen",
        "figure_panels": "Fig. 1b white dots and Fig. 4d",
        "monkey": "M1",
        "strength_file": "source_data/1b(white dots)&4d_strength_M1.csv",
        "duration_file": "source_data/1b(white dots)&4d_duration_M1.csv",
        "outcome_field": "Correct",
        "sure_target_available": True,
        "sure_target_chosen": False,
        "drop_zero_strength_before_pairing": True,
    },
    {
        "source_measure": "accuracy_sure_available_direction_chosen",
        "figure_panels": "Fig. 1b white dots and Fig. 4d",
        "monkey": "M2",
        "strength_file": "source_data/1b(white dots)&4d_coh_M2.csv",
        "duration_file": "source_data/1b(white dots)&4d_duration_M2.csv",
        "outcome_field": "Correct",
        "sure_target_available": True,
        "sure_target_chosen": False,
        "drop_zero_strength_before_pairing": True,
    },
    {
        "source_measure": "sure_target_choice",
        "figure_panels": "Fig. 1c and Fig. 4c",
        "monkey": "M1",
        "strength_file": "source_data/1c&4c_strength_M1.csv",
        "duration_file": "source_data/1c&4c_duration_M1.csv",
        "outcome_field": "Sure target",
        "sure_target_available": True,
        "sure_target_chosen": None,
        "drop_zero_strength_before_pairing": False,
    },
    {
        "source_measure": "sure_target_choice",
        "figure_panels": "Fig. 1c and Fig. 4c",
        "monkey": "M2",
        "strength_file": "source_data/1c&4c_strength_M2.csv",
        "duration_file": "source_data/1c&4c_duration_M2.csv",
        "outcome_field": "Sure target",
        "sure_target_available": True,
        "sure_target_chosen": None,
        "drop_zero_strength_before_pairing": False,
    },
]


def download_roitman_rdm_csv(
    path: Path = DEFAULT_RDM_RAW_CSV,
    *,
    url: str = DEFAULT_RDM_CSV_URL,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        content = response.read()
    path.write_bytes(content)
    return {
        "source_url": url,
        "output_path": str(path),
        "n_bytes": len(content),
        "sha256": file_sha256(path),
    }


def download_human_rdm_phs_files(
    out_dir: Path = DEFAULT_HUMAN_RDM_RAW_DIR,
    *,
    subjects: list[str] | None = None,
    commit: str = COSMO2017_COMMIT,
) -> dict[str, Any]:
    selected_subjects = _normalize_human_rdm_subjects(subjects)
    filenames = [f"phs_{subject}.mat" for subject in selected_subjects]
    filenames.extend(HUMAN_RDM_SUPPORT_FILES)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for filename in filenames:
        url = _cosmo2017_raw_url(filename, commit=commit)
        path = out_dir / filename
        with urllib.request.urlopen(url) as response:
            content = response.read()
        path.write_bytes(content)
        files.append(
            {
                "file_name": filename,
                "source_url": url,
                "output_path": str(path),
                "n_bytes": len(content),
                "sha256": file_sha256(path),
            }
        )

    return {
        "source_repository_url": COSMO2017_REPOSITORY_URL,
        "source_repository_commit": commit,
        "output_dir": str(out_dir),
        "subjects": [f"phs-{subject}" for subject in selected_subjects],
        "n_files": len(files),
        "n_bytes": sum(int(file["n_bytes"]) for file in files),
        "files": files,
    }


def download_macaque_rdm_confidence_source_data(
    out_file: Path = DEFAULT_MACAQUE_RDM_CONFIDENCE_RAW_ZIP,
    *,
    url: str = KHALVATI_RDM_CONFIDENCE_SOURCE_DATA_URL,
) -> dict[str, Any]:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        content = response.read()
    out_file.write_bytes(content)
    return {
        "source_url": url,
        "output_path": str(out_file),
        "n_bytes": len(content),
        "sha256": file_sha256(out_file),
    }


def load_roitman_rdm_csv(
    csv_file: Path,
    *,
    session_id: str = DEFAULT_RDM_SESSION_ID,
    monkey: int | None = None,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if monkey is not None:
        rows = [row for row in rows if _optional_int(row.get("monkey")) == monkey]
    if limit is not None:
        rows = rows[:limit]

    trials = [
        harmonize_roitman_rdm_trial(
            row,
            session_id=session_id,
            trial_index=index,
        )
        for index, row in enumerate(rows)
    ]
    details = {
        "source_file": str(csv_file),
        "source_file_name": csv_file.name,
        "source_file_sha256": file_sha256(csv_file),
        "source_url": DEFAULT_RDM_CSV_URL,
        "source_repository_commit": PYDDM_COMMIT,
        "n_trials": len(trials),
        "monkeys": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "coherence_levels": sorted(
            {
                trial.evidence_strength
                for trial in trials
                if trial.evidence_strength is not None
            }
        ),
    }
    return trials, details


def load_human_rdm_phs_mats(
    raw_dir: Path,
    *,
    session_id: str = DEFAULT_HUMAN_RDM_SESSION_ID,
    subjects: list[str] | None = None,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    selected_subjects = _normalize_human_rdm_subjects(subjects)
    trials: list[CanonicalTrial] = []
    source_files = []

    for subject in selected_subjects:
        mat_file = raw_dir / f"phs_{subject}.mat"
        if not mat_file.exists():
            raise FileNotFoundError(
                f"Human RDM MATLAB file not found: {mat_file}. "
                "Run `uv run --extra rdm behavtaskatlas human-rdm-download` first."
            )
        rows = _load_human_rdm_phs_rows(mat_file)
        source_files.append(
            {
                "subject_id": f"phs-{subject}",
                "source_file": str(mat_file),
                "source_file_name": mat_file.name,
                "source_file_sha256": file_sha256(mat_file),
                "source_url": _cosmo2017_raw_url(mat_file.name),
                "n_trials": len(rows),
            }
        )
        for row in rows:
            if limit is not None and len(trials) >= limit:
                break
            trials.append(
                harmonize_human_rdm_phs_trial(
                    row,
                    subject_id=f"phs-{subject}",
                    session_id=session_id,
                    trial_index=len(trials),
                )
            )
        if limit is not None and len(trials) >= limit:
            break

    details = {
        "source_repository_url": COSMO2017_REPOSITORY_URL,
        "source_repository_commit": COSMO2017_COMMIT,
        "source_readme_url": _cosmo2017_raw_url("phs_data_README.txt"),
        "source_license_url": _cosmo2017_raw_url("LICENSE"),
        "source_files": source_files,
        "n_source_files": len(source_files),
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "signed_coherence_levels": sorted(
            {
                trial.stimulus_value
                for trial in trials
                if trial.stimulus_value is not None
            }
        ),
        "coherence_levels": sorted(
            {
                trial.evidence_strength
                for trial in trials
                if trial.evidence_strength is not None
            }
        ),
    }
    return trials, details


def load_macaque_rdm_confidence_source_data(
    source_zip: Path,
    *,
    session_id: str = DEFAULT_MACAQUE_RDM_CONFIDENCE_SESSION_ID,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    if not source_zip.exists():
        raise FileNotFoundError(
            f"Macaque RDM confidence source-data ZIP not found: {source_zip}. "
            "Run `uv run behavtaskatlas macaque-rdm-confidence-download` first."
        )

    trials: list[CanonicalTrial] = []
    source_tables = []
    dropped_zero_rows = 0
    with zipfile.ZipFile(source_zip) as archive:
        archive_names = set(archive.namelist())
        for spec in MACAQUE_RDM_CONFIDENCE_SOURCE_TABLES:
            strength_file = str(spec["strength_file"])
            duration_file = str(spec["duration_file"])
            missing = sorted({strength_file, duration_file} - archive_names)
            if missing:
                raise ValueError(
                    "Missing required source-data CSV(s) in "
                    f"{source_zip}: {', '.join(missing)}"
                )

            strength_rows = _read_source_data_csv(archive, strength_file)
            duration_rows = _read_source_data_csv(archive, duration_file)
            if spec["drop_zero_strength_before_pairing"]:
                before = len(strength_rows)
                strength_rows = [
                    row for row in strength_rows if _source_motion_strength_percent(row) != 0.0
                ]
                dropped_zero_rows += before - len(strength_rows)

            if len(strength_rows) != len(duration_rows):
                raise ValueError(
                    f"Cannot align {strength_file} and {duration_file}: "
                    f"{len(strength_rows)} strength rows vs {len(duration_rows)} duration rows"
                )

            outcome_field = str(spec["outcome_field"])
            mismatches = sum(
                1
                for strength_row, duration_row in zip(strength_rows, duration_rows, strict=True)
                if strength_row.get(outcome_field) != duration_row.get(outcome_field)
            )
            if mismatches:
                raise ValueError(
                    f"Cannot align {strength_file} and {duration_file}: "
                    f"{mismatches} outcome value mismatches"
                )

            source_tables.append(
                {
                    "source_measure": spec["source_measure"],
                    "figure_panels": spec["figure_panels"],
                    "monkey": spec["monkey"],
                    "strength_file": strength_file,
                    "duration_file": duration_file,
                    "outcome_field": outcome_field,
                    "n_rows": len(strength_rows),
                    "drop_zero_strength_before_pairing": spec[
                        "drop_zero_strength_before_pairing"
                    ],
                }
            )
            for source_row_index, (strength_row, duration_row) in enumerate(
                zip(strength_rows, duration_rows, strict=True)
            ):
                if limit is not None and len(trials) >= limit:
                    break
                source_row = {
                    **strength_row,
                    **duration_row,
                    "_source_measure": spec["source_measure"],
                    "_figure_panels": spec["figure_panels"],
                    "_monkey": spec["monkey"],
                    "_strength_file": strength_file,
                    "_duration_file": duration_file,
                    "_source_row_index": source_row_index,
                    "_outcome_field": outcome_field,
                    "_sure_target_available": spec["sure_target_available"],
                    "_sure_target_chosen": spec["sure_target_chosen"],
                    "_zero_strength_rows_dropped_before_pairing": spec[
                        "drop_zero_strength_before_pairing"
                    ],
                }
                trials.append(
                    harmonize_macaque_rdm_confidence_source_row(
                        source_row,
                        session_id=session_id,
                        trial_index=len(trials),
                    )
                )
            if limit is not None and len(trials) >= limit:
                break

    details = {
        "source_file": str(source_zip),
        "source_file_name": source_zip.name,
        "source_file_sha256": file_sha256(source_zip),
        "source_url": KHALVATI_RDM_CONFIDENCE_SOURCE_DATA_URL,
        "article_url": KHALVATI_RDM_CONFIDENCE_ARTICLE_URL,
        "code_url": KHALVATI_RDM_CONFIDENCE_CODE_URL,
        "source_tables": source_tables,
        "n_source_tables": len(source_tables),
        "n_trials": len(trials),
        "n_source_rows": len(trials),
        "dropped_zero_strength_accuracy_rows": dropped_zero_rows,
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "source_measures": sorted(
            {
                str(trial.task_variables.get("source_measure"))
                for trial in trials
                if trial.task_variables.get("source_measure")
            }
        ),
        "motion_strength_levels": sorted(
            {
                trial.evidence_strength
                for trial in trials
                if trial.evidence_strength is not None
            }
        ),
        "motion_duration_ms_range": _numeric_range(
            trial.task_variables.get("motion_duration_ms") for trial in trials
        ),
    }
    return trials, details


def harmonize_roitman_rdm_trial(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
) -> CanonicalTrial:
    missing = sorted(
        field for field in ["monkey", "rt", "coh", "correct", "trgchoice"] if field not in source
    )
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Roitman RDM fields: {joined}")

    monkey = _required_int(source["monkey"], field="monkey")
    coherence_fraction = _required_float(source["coh"], field="coh")
    correct = _correct_label(source["correct"])
    target_choice = _required_int(
        _required_float(source["trgchoice"], field="trgchoice"),
        field="trgchoice",
    )
    signed_fraction = _signed_coherence_fraction(
        coherence_fraction=coherence_fraction,
        target_choice=target_choice,
        correct=correct,
    )
    signed_percent = signed_fraction * 100.0

    return CanonicalTrial(
        protocol_id=ROITMAN_RDM_PROTOCOL_ID,
        dataset_id=ROITMAN_RDM_DATASET_ID,
        subject_id=f"monkey-{monkey}",
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_percent,
        stimulus_units="percent motion coherence, signed target 1 positive",
        stimulus_side=_target_side_from_signed_coherence(signed_percent),
        evidence_strength=abs(signed_percent),
        evidence_units="absolute percent motion coherence",
        choice=_target_choice_label(target_choice),
        correct=correct,
        response_time=_required_float(source["rt"], field="rt"),
        response_time_origin="saccade time minus stimulus onset, from PyDDM processed CSV",
        feedback="reward" if correct else "error",
        prior_context=None,
        task_variables={
            "monkey": monkey,
            "coherence_fraction": coherence_fraction,
            "signed_coherence_fraction_target1_positive": signed_fraction,
            "target_choice": target_choice,
            "target_choice_label": f"target_{target_choice}",
            "correct_code": _required_float(source["correct"], field="correct"),
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_human_rdm_phs_trial(
    source: dict[str, Any],
    *,
    subject_id: str,
    session_id: str,
    trial_index: int,
) -> CanonicalTrial:
    missing = sorted(field for field in ["rt", "choice", "cohs"] if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required human RDM fields: {joined}")

    choice_code = _required_int(source["choice"], field="choice")
    if choice_code not in {0, 1}:
        raise ValueError(f"Field choice must be 0 or 1, got {source['choice']!r}")
    signed_fraction = _required_float(source["cohs"], field="cohs")
    signed_percent = signed_fraction * 100.0

    return CanonicalTrial(
        protocol_id=HUMAN_RDM_PROTOCOL_ID,
        dataset_id=HUMAN_RDM_DATASET_ID,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_percent,
        stimulus_units="percent motion coherence, signed right positive",
        stimulus_side=_target_side_from_signed_coherence(signed_percent),
        evidence_strength=abs(signed_percent),
        evidence_units="absolute percent motion coherence",
        choice=_human_rdm_choice_label(choice_code),
        correct=_human_rdm_correct_label(signed_fraction, choice_code),
        response_time=_required_float(source["rt"], field="rt"),
        response_time_origin="reaction time in seconds from CoSMo2017 PHS MATLAB file",
        feedback="none",
        prior_context=None,
        task_variables={
            "subject": subject_id,
            "coherence_fraction": signed_fraction,
            "signed_coherence_fraction_right_positive": signed_fraction,
            "choice_code": choice_code,
            "zero_coherence_correct_choice_convention": "right",
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_macaque_rdm_confidence_source_row(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
) -> CanonicalTrial:
    missing = sorted(
        field
        for field in [
            "_source_measure",
            "_figure_panels",
            "_monkey",
            "_strength_file",
            "_duration_file",
            "_source_row_index",
            "_outcome_field",
            "_sure_target_available",
        ]
        if field not in source
    )
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required macaque RDM confidence source fields: {joined}")

    source_measure = str(source["_source_measure"])
    monkey = str(source["_monkey"])
    outcome_field = str(source["_outcome_field"])
    motion_strength = _source_motion_strength_percent(source)
    motion_duration_ms = _source_motion_duration_ms(source)
    correct = None
    sure_target_chosen = _optional_bool(source.get("_sure_target_chosen"))
    feedback = "unknown"

    if outcome_field == "Correct":
        correct = _binary_bool(source.get("Correct"), field="Correct")
        feedback = "reward" if correct else "error"
    elif outcome_field == "Sure target":
        sure_target_chosen = _binary_bool(source.get("Sure target"), field="Sure target")
        feedback = "reward" if sure_target_chosen else "unknown"
    else:
        raise ValueError(f"Unsupported confidence source outcome field: {outcome_field!r}")

    stimulus_side = "none" if motion_strength == 0.0 else "unknown"
    return CanonicalTrial(
        protocol_id=MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID,
        dataset_id=MACAQUE_RDM_CONFIDENCE_DATASET_ID,
        subject_id=f"kiani-shadlen-{monkey.lower()}",
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=motion_strength,
        stimulus_units="absolute percent motion coherence; sign not available in source data",
        stimulus_side=stimulus_side,
        evidence_strength=motion_strength,
        evidence_units="absolute percent motion coherence",
        choice="unknown",
        correct=correct,
        response_time=None,
        response_time_origin=None,
        feedback=feedback,
        prior_context=source_measure,
        task_variables={
            "source_measure": source_measure,
            "figure_panels": source["_figure_panels"],
            "monkey": monkey,
            "motion_strength_percent": motion_strength,
            "motion_duration_ms": motion_duration_ms,
            "sure_target_available": bool(source["_sure_target_available"]),
            "sure_target_chosen": sure_target_chosen,
            "correct_code": _optional_float(source.get("Correct")),
            "sure_target_code": _optional_float(source.get("Sure target")),
            "source_strength_file": source["_strength_file"],
            "source_duration_file": source["_duration_file"],
            "source_row_index": _required_int(
                source["_source_row_index"],
                field="_source_row_index",
            ),
            "zero_strength_rows_dropped_before_pairing": bool(
                source.get("_zero_strength_rows_dropped_before_pairing", False)
            ),
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def analyze_roitman_rdm(trials: list[CanonicalTrial]) -> dict[str, Any]:
    from behavtaskatlas.ibl import analyze_canonical_psychometric

    result = analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.random-dot-motion.descriptive-psychometric",
        protocol_id=ROITMAN_RDM_PROTOCOL_ID,
        dataset_id=ROITMAN_RDM_DATASET_ID,
        report_title="Random-Dot Motion Report",
        stimulus_label="Signed motion coherence",
        stimulus_units="percent coherence, signed target 1 positive",
        stimulus_metric_name="coherence",
        caveats=[
            (
                "The PyDDM CSV stores unsigned coherence, target choice, and correctness. "
                "Signed coherence is reconstructed using the documented PyDDM "
                "target-coding transform."
            ),
            (
                "Canonical left/right labels are used as target-2/target-1 labels because the "
                "processed CSV does not preserve a stable screen-side mapping."
            ),
            (
                "Reaction times are reported from the processed PyDDM CSV without "
                "excluding short or long trials."
            ),
        ],
    )
    result["chronometric_rows"] = summarize_rdm_chronometric(trials)
    return result


def analyze_human_rdm(trials: list[CanonicalTrial]) -> dict[str, Any]:
    from behavtaskatlas.ibl import analyze_canonical_psychometric

    result = analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.human-rdm.descriptive-psychometric",
        protocol_id=HUMAN_RDM_PROTOCOL_ID,
        dataset_id=HUMAN_RDM_DATASET_ID,
        report_title="Human Random-Dot Motion Report",
        stimulus_label="Signed motion coherence",
        stimulus_units="percent coherence, signed right positive",
        stimulus_metric_name="coherence",
        caveats=[
            (
                "The CoSMo2017 PHS MATLAB files are modified from the original "
                "Palmer-Huk-Shadlen Experiment 1 data: bad trials were removed, "
                "motion direction and coherence were combined into signed coherence, "
                "and reaction times were converted to seconds."
            ),
            (
                "Choice is coded as 0 left and 1 right. Correctness is reconstructed "
                "from signed coherence and choice using the CoSMo2017 analysis "
                "convention that treats zero-coherence trials as rightward."
            ),
            (
                "Empirical bias and threshold use linear interpolation over empirical "
                "p(right). Fitted values use a four-parameter logistic model rather "
                "than the Palmer-Huk-Shadlen diffusion-model fit."
            ),
        ],
    )
    result["chronometric_rows"] = summarize_rdm_chronometric(trials)
    return result


def analyze_macaque_rdm_confidence(trials: list[CanonicalTrial]) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    accuracy_rows = summarize_macaque_rdm_confidence_accuracy(trials)
    confidence_rows = summarize_macaque_rdm_confidence_choice(trials)
    source_measure_counts: dict[str, int] = {}
    for trial in trials:
        source_measure = str(trial.task_variables.get("source_measure", "unknown"))
        source_measure_counts[source_measure] = source_measure_counts.get(source_measure, 0) + 1

    return {
        "analysis_id": "analysis.macaque-rdm-confidence.source-data-summary",
        "analysis_type": "descriptive_accuracy_confidence_source_data",
        "report_title": "Macaque RDM Confidence Wagering Report",
        "protocol_id": MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID,
        "dataset_id": MACAQUE_RDM_CONFIDENCE_DATASET_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "n_trials": len(trials),
        "n_source_rows": len(trials),
        "n_response_trials": len(trials),
        "n_accuracy_rows": sum(
            count
            for measure, count in source_measure_counts.items()
            if measure.startswith("accuracy_")
        ),
        "n_sure_target_choice_rows": source_measure_counts.get("sure_target_choice", 0),
        "n_source_measures": len(source_measure_counts),
        "source_measure_counts": source_measure_counts,
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "motion_strength_levels": sorted(
            {
                trial.evidence_strength
                for trial in trials
                if trial.evidence_strength is not None
            }
        ),
        "motion_duration_ms_range": _numeric_range(
            trial.task_variables.get("motion_duration_ms") for trial in trials
        ),
        "summary_rows": confidence_rows,
        "confidence_rows": confidence_rows,
        "accuracy_rows": accuracy_rows,
        "stimulus_metric_name": "motion_strength",
        "stimulus_label": "Motion strength",
        "stimulus_units": "absolute percent coherence",
        "caveats": [
            (
                "The Nature Communications ZIP provides source-data rows for figure panels, "
                "not the complete raw behavioral export. Rows should be interpreted as "
                "source-data records and may not be unique raw trial identifiers across panels."
            ),
            (
                "Motion direction, signed coherence, direction choice, and saccade response time "
                "are not preserved in these CSVs. The adapter therefore maps motion strength to "
                "absolute evidence strength and keeps choice as unknown."
            ),
            (
                "White-dot direction-choice accuracy rows are paired after dropping zero-strength "
                "rows, because direction correctness is not defined for zero coherence in the "
                "duration source table."
            ),
        ],
    }


def summarize_macaque_rdm_confidence_accuracy(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float], list[CanonicalTrial]] = {}
    for trial in trials:
        source_measure = str(trial.task_variables.get("source_measure", ""))
        if not source_measure.startswith("accuracy_") or trial.evidence_strength is None:
            continue
        monkey = str(trial.task_variables.get("monkey", trial.subject_id or "unknown"))
        key = (source_measure, monkey, trial.evidence_strength)
        grouped.setdefault(key, []).append(trial)

    rows = []
    for (source_measure, monkey, motion_strength), group in sorted(grouped.items()):
        correct_trials = [trial for trial in group if trial.correct is not None]
        n_correct = sum(1 for trial in correct_trials if trial.correct)
        durations = [
            _required_float(value, field="motion_duration_ms")
            for value in (trial.task_variables.get("motion_duration_ms") for trial in group)
            if _optional_float(value) is not None
        ]
        rows.append(
            {
                "source_measure": source_measure,
                "monkey": monkey,
                "motion_strength_percent": motion_strength,
                "n_source_rows": len(group),
                "n_correct": n_correct,
                "p_correct": _safe_ratio(n_correct, len(correct_trials)),
                "median_motion_duration_ms": statistics.median(durations)
                if durations
                else None,
                "mean_motion_duration_ms": statistics.mean(durations) if durations else None,
            }
        )
    return rows


def summarize_macaque_rdm_confidence_choice(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float], list[CanonicalTrial]] = {}
    for trial in trials:
        if trial.task_variables.get("source_measure") != "sure_target_choice":
            continue
        if trial.evidence_strength is None:
            continue
        monkey = str(trial.task_variables.get("monkey", trial.subject_id or "unknown"))
        key = (monkey, trial.evidence_strength)
        grouped.setdefault(key, []).append(trial)

    rows = []
    for (monkey, motion_strength), group in sorted(grouped.items()):
        sure_values = [
            bool(trial.task_variables["sure_target_chosen"])
            for trial in group
            if trial.task_variables.get("sure_target_chosen") is not None
        ]
        n_sure = sum(1 for chosen in sure_values if chosen)
        durations = [
            _required_float(value, field="motion_duration_ms")
            for value in (trial.task_variables.get("motion_duration_ms") for trial in group)
            if _optional_float(value) is not None
        ]
        rows.append(
            {
                "monkey": monkey,
                "motion_strength_percent": motion_strength,
                "n_source_rows": len(group),
                "n_sure_target": n_sure,
                "p_sure_target": _safe_ratio(n_sure, len(sure_values)),
                "median_motion_duration_ms": statistics.median(durations)
                if durations
                else None,
                "mean_motion_duration_ms": statistics.mean(durations) if durations else None,
            }
        )
    return rows


def summarize_rdm_chronometric(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[float, list[CanonicalTrial]] = {}
    for trial in trials:
        if trial.evidence_strength is None:
            continue
        grouped.setdefault(trial.evidence_strength, []).append(trial)

    rows = []
    for evidence_strength, group in sorted(grouped.items()):
        response_times = [trial.response_time for trial in group if trial.response_time is not None]
        correct_trials = [trial for trial in group if trial.correct is not None]
        n_correct = sum(1 for trial in correct_trials if trial.correct)
        rows.append(
            {
                "evidence_strength": evidence_strength,
                "n_trials": len(group),
                "n_response": len(response_times),
                "n_correct": n_correct,
                "p_correct": _safe_ratio(n_correct, len(correct_trials)),
                "median_response_time": statistics.median(response_times)
                if response_times
                else None,
                "mean_response_time": statistics.mean(response_times) if response_times else None,
            }
        )
    return rows


def write_rdm_chronometric_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RDM_CHRONOMETRIC_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_rdm_chronometric_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rdm_chronometric_svg(rows), encoding="utf-8")


def write_macaque_rdm_confidence_accuracy_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MACAQUE_RDM_CONFIDENCE_ACCURACY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_macaque_rdm_confidence_choice_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MACAQUE_RDM_CONFIDENCE_CONFIDENCE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_macaque_rdm_confidence_accuracy_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(macaque_rdm_confidence_accuracy_svg(rows), encoding="utf-8")


def write_macaque_rdm_confidence_choice_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(macaque_rdm_confidence_choice_svg(rows), encoding="utf-8")


def write_rdm_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    chronometric_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        rdm_report_html(
            analysis_result,
            provenance=provenance,
            psychometric_svg_text=psychometric_svg_text,
            chronometric_svg_text=chronometric_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def write_macaque_rdm_confidence_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    accuracy_svg_text: str | None = None,
    confidence_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        macaque_rdm_confidence_report_html(
            analysis_result,
            provenance=provenance,
            accuracy_svg_text=accuracy_svg_text,
            confidence_svg_text=confidence_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def rdm_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": ROITMAN_RDM_PROTOCOL_ID,
        "dataset_id": ROITMAN_RDM_DATASET_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "source": {
            "pyddm_raw_csv_url": DEFAULT_RDM_CSV_URL,
            "pyddm_repository_commit": PYDDM_COMMIT,
            "shadlen_lab_source": "https://shadlenlab.columbia.edu/resources/RoitmanDataCode.html",
            **details,
        },
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "source_fields": ["monkey", "rt", "coh", "correct", "trgchoice"],
        "outputs": output_files,
        "caveats": [
            (
                "The CSV is a processed PyDDM convenience file derived from the "
                "Roitman-Shadlen dataset."
            ),
            (
                "Target identity is preserved, but a stable left/right screen-side mapping is not "
                "available in the processed CSV."
            ),
        ],
    }


def human_rdm_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": HUMAN_RDM_PROTOCOL_ID,
        "dataset_id": HUMAN_RDM_DATASET_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "source": {
            "cosmo2017_repository_url": COSMO2017_REPOSITORY_URL,
            "cosmo2017_repository_commit": COSMO2017_COMMIT,
            **details,
        },
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "source_fields": ["rt", "choice", "cohs"],
        "outputs": output_files,
        "caveats": [
            (
                "The PHS files are distributed by CoSMo2017 as MATLAB files derived "
                "from Palmer, Huk, and Shadlen Experiment 1."
            ),
            (
                "CoSMo2017 pre-processing assigned random choices to zero-coherence "
                "trials and its fitting scripts treat zero coherence as rightward for "
                "correctness reconstruction."
            ),
        ],
    }


def macaque_rdm_confidence_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": MACAQUE_RDM_CONFIDENCE_PROTOCOL_ID,
        "dataset_id": MACAQUE_RDM_CONFIDENCE_DATASET_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "source": {
            "article_url": KHALVATI_RDM_CONFIDENCE_ARTICLE_URL,
            "source_data_url": KHALVATI_RDM_CONFIDENCE_SOURCE_DATA_URL,
            "code_url": KHALVATI_RDM_CONFIDENCE_CODE_URL,
            **details,
        },
        "n_trials": len(trials),
        "n_source_rows": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "source_fields": [
            "Motion Strength (%)",
            "Motion strength (%)",
            "Motion duration (msc)",
            "Correct",
            "Sure target",
        ],
        "outputs": output_files,
        "caveats": [
            (
                "The source-data ZIP supports figure-level source-data summaries, "
                "not reconstruction of signed direction choices or raw session ids."
            ),
            (
                "Canonical rows preserve source panel identity in task_variables so "
                "duplicate underlying behavioral trials across figure panels are not "
                "mistaken for unique raw trials."
            ),
        ],
    }


def rdm_chronometric_svg(rows: list[dict[str, Any]]) -> str:
    width = 720
    height = 420
    left = 72
    right = 28
    top = 34
    bottom = 66
    plot_width = width - left - right
    plot_height = height - top - bottom
    if not rows:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No chronometric data available</text></svg>\n'
        )

    x_values = [float(row["evidence_strength"]) for row in rows]
    y_values = [
        float(row["median_response_time"])
        for row in rows
        if row.get("median_response_time") is not None
    ]
    if not x_values or not y_values:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No chronometric data available</text></svg>\n'
        )
    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0
    if y_min == y_max:
        y_min -= 0.1
        y_max += 0.1

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def y_scale(value: float) -> float:
        return top + (1.0 - (value - y_min) / (y_max - y_min)) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" '
        'stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 18}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14">Motion coherence (% absolute)</text>',
        f'<text x="18" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 18 '
        f'{top + plot_height / 2})">Median response time (s)</text>',
    ]
    points = []
    for row in rows:
        if row.get("median_response_time") is None:
            continue
        x = x_scale(float(row["evidence_strength"]))
        y = y_scale(float(row["median_response_time"]))
        points.append((x, y))
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#145f91"/>')
        elements.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="10">{float(row["evidence_strength"]):g}</text>'
        )
    if len(points) > 1:
        point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        elements.append(
            f'<polyline points="{point_attr}" fill="none" stroke="#145f91" stroke-width="2"/>'
        )
    for y_value in [y_min, (y_min + y_max) / 2.0, y_max]:
        y = y_scale(y_value)
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{y_value:.2g}</text>'
        )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def macaque_rdm_confidence_accuracy_svg(rows: list[dict[str, Any]]) -> str:
    return _macaque_rdm_confidence_line_svg(
        rows,
        y_key="p_correct",
        title="Accuracy by motion strength",
        y_label="P(correct)",
        group_keys=("monkey", "source_measure"),
    )


def macaque_rdm_confidence_choice_svg(rows: list[dict[str, Any]]) -> str:
    return _macaque_rdm_confidence_line_svg(
        rows,
        y_key="p_sure_target",
        title="Sure-target choice by motion strength",
        y_label="P(sure target)",
        group_keys=("monkey",),
    )


def _macaque_rdm_confidence_line_svg(
    rows: list[dict[str, Any]],
    *,
    y_key: str,
    title: str,
    y_label: str,
    group_keys: tuple[str, ...],
) -> str:
    width = 760
    height = 440
    left = 76
    right = 170
    top = 42
    bottom = 68
    plot_width = width - left - right
    plot_height = height - top - bottom
    points_by_group: dict[str, list[tuple[float, float, int | None]]] = {}
    for row in rows:
        x = _optional_float(row.get("motion_strength_percent"))
        y = _optional_float(row.get(y_key))
        if x is None or y is None:
            continue
        label = " / ".join(str(row.get(key, "unknown")) for key in group_keys)
        n_source_rows = _optional_int(row.get("n_source_rows"))
        points_by_group.setdefault(label, []).append((x, y, n_source_rows))

    if not points_by_group:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="120">'
            f'<text x="20" y="60">{escape(title)} not available</text></svg>\n'
        )

    x_values = [point[0] for points in points_by_group.values() for point in points]
    x_min = min(x_values)
    x_max = max(x_values)
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0
    y_min = 0.0
    y_max = 1.0

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def y_scale(value: float) -> float:
        return top + (1.0 - (value - y_min) / (y_max - y_min)) * plot_height

    colors = ["#145f91", "#b63f2c", "#2b7a3d", "#6b4aa0", "#9a6a12", "#374151"]
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="24" font-family="sans-serif" font-size="15" '
        f'font-weight="700">{escape(title)}</text>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" '
        'stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 18}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14">Motion strength (% coherence)</text>',
        f'<text x="20" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 20 '
        f'{top + plot_height / 2})">{escape(y_label)}</text>',
    ]
    for y_value in [0.0, 0.5, 1.0]:
        y = y_scale(y_value)
        elements.append(
            f'<line x1="{left - 4}" y1="{y:.1f}" x2="{left + plot_width}" '
            'y2="{:.1f}" stroke="#e5e7eb"/>'.format(y)
        )
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{y_value:.1f}</text>'
        )
    for x_value in sorted(set(x_values)):
        x = x_scale(x_value)
        elements.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="10">{x_value:g}</text>'
        )

    for index, (label, points) in enumerate(sorted(points_by_group.items())):
        color = colors[index % len(colors)]
        sorted_points = sorted(points)
        point_attr = " ".join(
            f"{x_scale(point[0]):.1f},{y_scale(point[1]):.1f}" for point in sorted_points
        )
        if len(sorted_points) > 1:
            elements.append(
                f'<polyline points="{point_attr}" fill="none" stroke="{color}" '
                'stroke-width="2"/>'
            )
        for x_value, y_value, n_rows in sorted_points:
            x = x_scale(x_value)
            y = y_scale(y_value)
            title_attr = (
                f"{label}: {x_value:g}% {y_label}={y_value:.3f}"
                + (f", n={n_rows}" if n_rows is not None else "")
            )
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}">'
                f"<title>{escape(title_attr)}</title></circle>"
            )
        legend_y = top + 18 + index * 22
        elements.append(
            f'<line x1="{left + plot_width + 24}" y1="{legend_y}" '
            f'x2="{left + plot_width + 44}" y2="{legend_y}" stroke="{color}" '
            'stroke-width="2"/>'
        )
        elements.append(
            f'<text x="{left + plot_width + 50}" y="{legend_y + 4}" '
            f'font-family="sans-serif" font-size="11">{escape(label)}</text>'
        )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def rdm_report_html(
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    chronometric_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    provenance = provenance or {}
    artifact_links = artifact_links or {}
    prior_results = analysis_result.get("prior_results", [])
    summary_rows = analysis_result.get("summary_rows", [])
    chronometric_rows = analysis_result.get("chronometric_rows", [])
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    subjects = _source_subjects(source)
    title = str(analysis_result.get("report_title") or "Random-Dot Motion Report")
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
        f"<p class=\"lede\">{escape(_rdm_report_lede(analysis_result))}</p>",
        "</header>",
        '<section class="metrics" aria-label="Report metrics">',
        _metric("Trials", analysis_result.get("n_trials")),
        _metric("Response trials", analysis_result.get("n_response_trials")),
        _metric("Subjects", len(subjects)),
        _metric("Coherence levels", len(chronometric_rows)),
        _metric("Psychometric rows", len(summary_rows)),
        _metric("Prior blocks", len(prior_results)),
        "</section>",
        '<section class="grid-two">',
        "<div>",
        "<h2>Source</h2>",
        _definition_list(
            [
                ("Dataset", analysis_result.get("dataset_id")),
                ("Protocol", analysis_result.get("protocol_id")),
                ("Source commit", source.get("source_repository_commit")),
                ("Source files", _source_file_summary(source)),
                ("Subjects", ", ".join(subjects)),
            ]
        ),
        "</div>",
        "<div>",
        "<h2>Provenance</h2>",
        _definition_list(
            [
                ("Generated", analysis_result.get("generated_at")),
                ("Commit", analysis_result.get("behavtaskatlas_commit")),
                ("Git dirty", analysis_result.get("behavtaskatlas_git_dirty")),
                ("Response time", analysis_result.get("response_time_origin")),
            ]
        ),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Psychometric Summary</h2>",
        '<div class="figure-wrap">',
        psychometric_svg_text or _missing_svg("Psychometric plot not available"),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Chronometric Summary</h2>",
        '<div class="figure-wrap">',
        chronometric_svg_text or _missing_svg("Chronometric plot not available"),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Psychometric Fit</h2>",
        _html_table(
            _prior_report_rows(prior_results),
            [
                ("prior_context", "Prior"),
                ("n_trials", "Trials"),
                ("n_response_trials", "Responses"),
                ("n_coherence_levels", "Coherence levels"),
                ("empirical_bias_coherence", "Empirical bias"),
                ("empirical_threshold_coherence", "Empirical threshold"),
                ("fit_bias_coherence", "Fit bias"),
                ("fit_threshold_coherence", "Fit threshold"),
                ("fit_status", "Fit status"),
            ],
        ),
        "</section>",
        "<section>",
        "<h2>Chronometric Rows</h2>",
        _html_table(
            chronometric_rows,
            [
                ("evidence_strength", "Coherence"),
                ("n_trials", "Trials"),
                ("p_correct", "P(correct)"),
                ("median_response_time", "Median RT"),
                ("mean_response_time", "Mean RT"),
            ],
        ),
        "</section>",
    ]
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


def macaque_rdm_confidence_report_html(
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    accuracy_svg_text: str | None = None,
    confidence_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    provenance = provenance or {}
    artifact_links = artifact_links or {}
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    title = str(analysis_result.get("report_title") or "Macaque RDM Confidence Report")
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
        "<p class=\"lede\">Kiani-Shadlen macaque random-dot motion confidence slice "
        "generated from the Nature Communications figure source-data ZIP, with "
        "motion-strength summaries for accuracy and sure-target choice.</p>",
        "</header>",
        '<section class="metrics" aria-label="Report metrics">',
        _metric("Source rows", analysis_result.get("n_source_rows")),
        _metric("Accuracy rows", analysis_result.get("n_accuracy_rows")),
        _metric("Sure-target rows", analysis_result.get("n_sure_target_choice_rows")),
        _metric("Subjects", len(analysis_result.get("subjects", []))),
        _metric("Strength levels", len(analysis_result.get("motion_strength_levels", []))),
        _metric("Confidence rows", len(analysis_result.get("confidence_rows", []))),
        "</section>",
        '<section class="grid-two">',
        "<div>",
        "<h2>Source</h2>",
        _definition_list(
            [
                ("Dataset", analysis_result.get("dataset_id")),
                ("Protocol", analysis_result.get("protocol_id")),
                ("Article", source.get("article_url")),
                ("Source data", source.get("source_data_url")),
                ("Source files", _source_file_summary(source)),
                ("Subjects", ", ".join(str(item) for item in analysis_result.get("subjects", []))),
            ]
        ),
        "</div>",
        "<div>",
        "<h2>Provenance</h2>",
        _definition_list(
            [
                ("Generated", analysis_result.get("generated_at")),
                ("Commit", analysis_result.get("behavtaskatlas_commit")),
                ("Git dirty", analysis_result.get("behavtaskatlas_git_dirty")),
                ("Code", source.get("code_url")),
            ]
        ),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Sure-Target Choice</h2>",
        '<div class="figure-wrap">',
        confidence_svg_text or _missing_svg("Sure-target plot not available"),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Accuracy</h2>",
        '<div class="figure-wrap">',
        accuracy_svg_text or _missing_svg("Accuracy plot not available"),
        "</div>",
        "</section>",
        "<section>",
        "<h2>Sure-Target Rows</h2>",
        _html_table(
            analysis_result.get("confidence_rows", []),
            [
                ("monkey", "Monkey"),
                ("motion_strength_percent", "Strength"),
                ("n_source_rows", "Rows"),
                ("n_sure_target", "Sure target"),
                ("p_sure_target", "P(sure)"),
                ("median_motion_duration_ms", "Median duration ms"),
                ("mean_motion_duration_ms", "Mean duration ms"),
            ],
        ),
        "</section>",
        "<section>",
        "<h2>Accuracy Rows</h2>",
        _html_table(
            analysis_result.get("accuracy_rows", []),
            [
                ("source_measure", "Measure"),
                ("monkey", "Monkey"),
                ("motion_strength_percent", "Strength"),
                ("n_source_rows", "Rows"),
                ("n_correct", "Correct"),
                ("p_correct", "P(correct)"),
                ("median_motion_duration_ms", "Median duration ms"),
                ("mean_motion_duration_ms", "Mean duration ms"),
            ],
        ),
        "</section>",
    ]
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


def _rdm_report_lede(analysis_result: dict[str, Any]) -> str:
    if analysis_result.get("protocol_id") == HUMAN_RDM_PROTOCOL_ID:
        return (
            "Palmer-Huk-Shadlen human random-dot motion slice generated from "
            "CoSMo2017 MATLAB files, with signed-coherence psychometric and "
            "chronometric summaries."
        )
    return (
        "Roitman-Shadlen random-dot motion slice generated from the processed "
        "PyDDM trial table, with target-coded psychometric and chronometric summaries."
    )


def _source_subjects(source: dict[str, Any]) -> list[str]:
    for key in ["subjects", "monkeys"]:
        value = source.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def _source_file_summary(source: dict[str, Any]) -> str | None:
    if source.get("source_file_sha256"):
        return str(source["source_file_sha256"])
    source_files = source.get("source_files")
    if isinstance(source_files, list):
        return f"{len(source_files)} files"
    source_tables = source.get("source_tables")
    if isinstance(source_tables, list):
        return f"{len(source_tables)} paired source-data tables"
    return None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_source_data_csv(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with archive.open(name) as handle:
        text = handle.read().decode("utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def _source_motion_strength_percent(source: dict[str, Any]) -> float:
    for field in ["Motion Strength (%)", "Motion strength (%)"]:
        if field in source:
            return _required_float(source[field], field=field)
    raise ValueError("Missing required source-data motion strength field")


def _source_motion_duration_ms(source: dict[str, Any]) -> float:
    for field in ["Motion duration (msc)", "Motion duration (ms)"]:
        if field in source:
            return _required_float(source[field], field=field)
    raise ValueError("Missing required source-data motion duration field")


def _binary_bool(value: Any, *, field: str) -> bool:
    numeric = _required_float(value, field=field)
    if numeric == 1.0:
        return True
    if numeric == 0.0:
        return False
    raise ValueError(f"Field {field} must be 0 or 1, got {value!r}")


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    return _binary_bool(value, field="optional_bool")


def _numeric_range(values: Any) -> list[float | None]:
    numeric_values = [
        numeric
        for numeric in (_optional_float(value) for value in values)
        if numeric is not None
    ]
    if not numeric_values:
        return [None, None]
    return [min(numeric_values), max(numeric_values)]


def _signed_coherence_fraction(
    *,
    coherence_fraction: float,
    target_choice: int,
    correct: bool,
) -> float:
    choice_target1 = target_choice == 1
    return coherence_fraction if choice_target1 == correct else -coherence_fraction


def _target_choice_label(target_choice: int) -> str:
    if target_choice == 1:
        return "right"
    if target_choice == 2:
        return "left"
    return "unknown"


def _target_side_from_signed_coherence(value: float) -> str:
    if value > 0:
        return "right"
    if value < 0:
        return "left"
    return "none"


def _correct_label(value: Any) -> bool:
    numeric = _required_float(value, field="correct")
    if numeric == 1.0:
        return True
    if numeric == 0.0:
        return False
    raise ValueError(f"Field correct must be 0 or 1, got {value!r}")


def _human_rdm_choice_label(choice_code: int) -> str:
    if choice_code == 1:
        return "right"
    if choice_code == 0:
        return "left"
    return "unknown"


def _human_rdm_correct_label(signed_coherence_fraction: float, choice_code: int) -> bool:
    correct_choice_code = 1 if signed_coherence_fraction >= 0 else 0
    return choice_code == correct_choice_code


def _load_human_rdm_phs_rows(mat_file: Path) -> list[dict[str, Any]]:
    try:
        from scipy.io import loadmat
    except ImportError as exc:
        raise RuntimeError(
            "Loading human RDM MATLAB files requires scipy. "
            "Run with `uv run --extra rdm ...`."
        ) from exc

    loaded = loadmat(mat_file, squeeze_me=True)
    rts = _mat_vector(loaded, "rt")
    choices = _mat_vector(loaded, "choice")
    coherences = _mat_vector(loaded, "cohs")
    lengths = {len(rts), len(choices), len(coherences)}
    if len(lengths) != 1:
        raise ValueError(
            f"Human RDM MATLAB vectors have inconsistent lengths in {mat_file}: "
            f"rt={len(rts)}, choice={len(choices)}, cohs={len(coherences)}"
        )
    return [
        {
            "rt": rts[index],
            "choice": choices[index],
            "cohs": coherences[index],
        }
        for index in range(len(rts))
    ]


def _mat_vector(loaded: dict[str, Any], field: str) -> list[Any]:
    if field not in loaded:
        raise ValueError(f"Missing required MATLAB field {field!r}")
    value = loaded[field]
    if hasattr(value, "reshape"):
        return value.reshape(-1).tolist()
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def _normalize_human_rdm_subjects(subjects: list[str] | None) -> tuple[str, ...]:
    if subjects is None:
        return HUMAN_RDM_SUBJECT_IDS
    normalized = tuple(subject.removeprefix("phs_").removeprefix("phs-") for subject in subjects)
    invalid = sorted(set(normalized) - set(HUMAN_RDM_SUBJECT_IDS))
    if invalid:
        joined = ", ".join(invalid)
        valid = ", ".join(HUMAN_RDM_SUBJECT_IDS)
        raise ValueError(f"Unknown PHS subject id(s): {joined}. Expected one of: {valid}")
    return normalized


def _cosmo2017_raw_url(filename: str, *, commit: str = COSMO2017_COMMIT) -> str:
    base_url = (
        COSMO2017_RAW_BASE_URL
        if commit == COSMO2017_COMMIT
        else f"https://raw.githubusercontent.com/DrugowitschLab/CoSMo2017/{commit}"
    )
    return f"{base_url}/{filename}"


def _prior_report_rows(prior_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for prior_result in prior_results:
        fit = prior_result.get("fit")
        if not isinstance(fit, dict):
            fit = {}
        rows.append(
            {
                "prior_context": prior_result.get("prior_context") or "all trials",
                "n_trials": prior_result.get("n_trials"),
                "n_response_trials": prior_result.get("n_response_trials"),
                "n_coherence_levels": prior_result.get("n_coherence_levels"),
                "empirical_bias_coherence": prior_result.get("empirical_bias_coherence"),
                "empirical_threshold_coherence": prior_result.get(
                    "empirical_threshold_coherence"
                ),
                "fit_bias_coherence": fit.get("bias_coherence"),
                "fit_threshold_coherence": fit.get("threshold_coherence"),
                "fit_status": fit.get("status"),
            }
        )
    return rows


def _missing_svg(message: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        f'<text x="20" y="60">{escape(message)}</text></svg>'
    )


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
* { box-sizing: border-box; }
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
  max-width: 760px;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 1.05rem;
}
section { margin-top: 28px; }
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
.figure-wrap { padding: 12px; }
.figure-wrap svg {
  display: block;
  max-width: 100%;
  height: auto;
}
table {
  width: 100%;
  min-width: 760px;
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
tbody tr:last-child td { border-bottom: 0; }
.artifact-list {
  columns: 2;
  padding-left: 18px;
}
a { color: var(--accent); }
@media (max-width: 720px) {
  main {
    width: min(100vw - 20px, 1180px);
    padding-top: 20px;
  }
  dl { grid-template-columns: 1fr; }
  .artifact-list { columns: 1; }
}
""".strip()


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(_format_cell(value))}</strong>"
        "</div>"
    )


def _definition_list(rows: list[tuple[str, Any]]) -> str:
    parts = ["<dl>"]
    for label, value in rows:
        parts.append(f"<dt>{escape(label)}</dt>")
        parts.append(f"<dd>{escape(_format_cell(value))}</dd>")
    parts.append("</dl>")
    return "\n".join(parts)


def _html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="empty">No rows available.</p>'
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for _, label in columns:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
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
    numeric = _optional_float(value)
    if numeric is not None:
        if numeric.is_integer():
            return f"{int(numeric):,}"
        return f"{numeric:.4g}"
    return str(value)


def _json_safe_value(value: Any) -> Any:
    numeric = _optional_float(value)
    if numeric is not None:
        return numeric
    if value is None:
        return None
    if isinstance(value, str | int | bool):
        return value
    return str(value)


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _required_int(value: Any, *, field: str) -> int:
    numeric = _required_float(value, field=field)
    if not numeric.is_integer():
        raise ValueError(f"Field {field} must be an integer-like value, got {value!r}")
    return int(numeric)


def _required_float(value: Any, *, field: str) -> float:
    numeric = _optional_float(value)
    if numeric is None:
        raise ValueError(f"Field {field} must be finite, got {value!r}")
    return numeric


def _optional_int(value: Any) -> int | None:
    numeric = _optional_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric
