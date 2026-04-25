from __future__ import annotations

import hashlib
import math
import urllib.request
from pathlib import Path
from typing import Any

from behavtaskatlas.models import CanonicalTrial

HUMAN_VISUAL_CONTRAST_PROTOCOL_ID = "protocol.human-visual-contrast-2afc-keyboard"
HUMAN_VISUAL_CONTRAST_DATASET_ID = "dataset.walsh-prior-cue-human-contrast-osf"
DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_DIR = Path("data/raw/human_visual_contrast_walsh")
DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_MAT = (
    DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_DIR / "behavioural_analysis.mat"
)
DEFAULT_HUMAN_VISUAL_CONTRAST_DERIVED_DIR = Path("derived/human_visual_contrast")
DEFAULT_HUMAN_VISUAL_CONTRAST_SESSION_ID = "walsh-prior-cue-human-contrast-osf"
HUMAN_VISUAL_CONTRAST_PSYCHOMETRIC_X_AXIS_LABEL = (
    "Signed target-distractor contrast difference "
    "(percentage points; lower-frequency target positive)"
)

WALSH_OSF_PROJECT_URL = "https://osf.io/b92wm/"
WALSH_OSF_DOI = "10.17605/OSF.IO/B92WM"
WALSH_BEHAVIOURAL_ANALYSIS_MAT_URL = "https://osf.io/download/39hka/"
WALSH_BEHAVIOURAL_ANALYSIS_SCRIPT_URL = "https://osf.io/download/bspdh/"
WALSH_EXPERIMENT_TASK_SCRIPT_URL = "https://osf.io/download/c7phy/"
WALSH_ELIFE_URL = "https://elifesciences.org/articles/91135"
WALSH_ELIFE_DOI = "10.7554/eLife.91135.3"

WALSH_DATASET_COLUMNS = [
    "response_time",
    "performance_code",
    "cue_code",
    "pulse_code",
    "trial_bin",
    "subject_code",
    "lower_frequency_response",
    "delta_c",
    "reward_points",
]
WALSH_SUBJECT_LABELS = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L")
WALSH_CUE_LABELS = {1: "neutral", 2: "valid", 3: "invalid"}
WALSH_PULSE_LABELS = {1: "no_pulse", 2: "positive", 3: "neutral", 4: "reverse"}


def download_walsh_human_visual_contrast_files(
    raw_dir: Path = DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_DIR,
) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    downloads = [
        ("behavioural_analysis.mat", WALSH_BEHAVIOURAL_ANALYSIS_MAT_URL),
        ("behavioural_analysis.m", WALSH_BEHAVIOURAL_ANALYSIS_SCRIPT_URL),
        ("experiment_task.m", WALSH_EXPERIMENT_TASK_SCRIPT_URL),
    ]
    files = []
    for file_name, url in downloads:
        path = raw_dir / file_name
        request = urllib.request.Request(url, headers={"User-Agent": "behavtaskatlas/0.1"})
        with urllib.request.urlopen(request) as response:
            content = response.read()
        path.write_bytes(content)
        files.append(
            {
                "file_name": file_name,
                "url": url,
                "path": str(path),
                "n_bytes": len(content),
                "sha256": file_sha256(path),
            }
        )
    return {
        "source_url": WALSH_OSF_PROJECT_URL,
        "osf_doi": WALSH_OSF_DOI,
        "raw_dir": str(raw_dir),
        "n_files": len(files),
        "n_bytes": sum(int(file["n_bytes"]) for file in files),
        "files": files,
    }


def harmonize_walsh_human_visual_contrast_row(
    row: Any,
    *,
    session_id: str,
    trial_index: int,
) -> CanonicalTrial:
    source = _walsh_row_source(row)
    performance_code = _required_int(source["performance_code"], field="performance_code")
    correct = _performance_correct(performance_code)
    lower_frequency_response = _required_bool(
        source["lower_frequency_response"], field="lower_frequency_response"
    )
    target_lower_frequency = (
        lower_frequency_response if correct else not lower_frequency_response
    )
    delta_c = _required_float(source["delta_c"], field="delta_c")
    contrast_difference = _contrast_difference_percent(delta_c)
    signed_contrast = contrast_difference if target_lower_frequency else -contrast_difference
    subject_code = _required_int(source["subject_code"], field="subject_code")
    subject_label = _subject_label(subject_code)
    cue_code = _required_int(source["cue_code"], field="cue_code")
    cue_label = _cue_label(cue_code)
    pulse_code = _required_int(source["pulse_code"], field="pulse_code")
    pulse_label = _pulse_label(pulse_code)
    trial_bin = _required_int(source["trial_bin"], field="trial_bin")
    response_time = _required_float(source["response_time"], field="response_time")
    reward = _required_float(source["reward_points"], field="reward_points")

    return CanonicalTrial(
        protocol_id=HUMAN_VISUAL_CONTRAST_PROTOCOL_ID,
        dataset_id=HUMAN_VISUAL_CONTRAST_DATASET_ID,
        subject_id=f"subject-{subject_label}",
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_contrast,
        stimulus_units=(
            "target minus distractor contrast percentage points; "
            "lower-frequency target positive"
        ),
        stimulus_side="right" if target_lower_frequency else "left",
        evidence_strength=abs(signed_contrast),
        evidence_units="absolute target-distractor contrast difference percentage points",
        choice="right" if lower_frequency_response else "left",
        correct=correct,
        response_time=response_time,
        response_time_origin="seconds from evidence onset to button response",
        feedback="reward" if correct else "error",
        reward=reward,
        reward_units="points",
        prior_context=f"cue={cue_label}",
        training_stage=f"exposure_bin_{trial_bin}",
        task_variables={
            "subject_code": subject_code,
            "source_subject_label": subject_label,
            "cue_code": cue_code,
            "cue": cue_label,
            "pulse_code": pulse_code,
            "pulse": pulse_label,
            "exposure_bin": trial_bin,
            "delta_c": delta_c,
            "target_contrast": delta_c,
            "distractor_contrast": 1.0 - delta_c,
            "contrast_difference_percent": contrast_difference,
            "lower_frequency_response": lower_frequency_response,
            "target_lower_frequency": target_lower_frequency,
            "canonical_choice_convention": (
                "right=lower-frequency response; left=higher-frequency response"
            ),
            "canonical_stimulus_convention": (
                "right=lower-frequency target; left=higher-frequency target"
            ),
            "source_performance_code": performance_code,
            "reward_points": reward,
        },
        source=source,
    )


def harmonize_walsh_human_visual_contrast_rows(
    rows: Any,
    *,
    session_id: str = DEFAULT_HUMAN_VISUAL_CONTRAST_SESSION_ID,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    n_rows = len(rows)
    if limit is not None:
        n_rows = min(n_rows, limit)
    return [
        harmonize_walsh_human_visual_contrast_row(
            rows[index],
            session_id=session_id,
            trial_index=index,
        )
        for index in range(n_rows)
    ]


def load_walsh_human_visual_contrast_mat(
    mat_file: Path = DEFAULT_HUMAN_VISUAL_CONTRAST_RAW_MAT,
    *,
    session_id: str = DEFAULT_HUMAN_VISUAL_CONTRAST_SESSION_ID,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    try:
        import scipy.io
    except ImportError as exc:
        raise RuntimeError(
            "Human visual contrast ingestion requires scipy. "
            "Install it with `uv sync --extra visual`."
        ) from exc

    loaded = scipy.io.loadmat(mat_file, squeeze_me=True, simplify_cells=True)
    dataset = loaded.get("dataset")
    _validate_walsh_dataset(dataset)

    trials = harmonize_walsh_human_visual_contrast_rows(
        dataset,
        session_id=session_id,
        limit=limit,
    )
    details = {
        "source_file": str(mat_file),
        "source_file_name": mat_file.name,
        "source_file_sha256": file_sha256(mat_file),
        "source_url": WALSH_OSF_PROJECT_URL,
        "osf_doi": WALSH_OSF_DOI,
        "behavioural_analysis_mat_url": WALSH_BEHAVIOURAL_ANALYSIS_MAT_URL,
        "behavioural_analysis_script_url": WALSH_BEHAVIOURAL_ANALYSIS_SCRIPT_URL,
        "experiment_task_script_url": WALSH_EXPERIMENT_TASK_SCRIPT_URL,
        "n_source_rows": len(dataset),
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "cue_contexts": sorted({trial.prior_context for trial in trials if trial.prior_context}),
        "delta_c_values": sorted(
            {
                trial.task_variables["delta_c"]
                for trial in trials
                if "delta_c" in trial.task_variables
            }
        ),
        "exposure_bins": sorted(
            {
                trial.task_variables["exposure_bin"]
                for trial in trials
                if "exposure_bin" in trial.task_variables
            }
        ),
    }
    return trials, details


def analyze_human_visual_contrast(trials: list[CanonicalTrial]) -> dict[str, Any]:
    from behavtaskatlas.ibl import analyze_canonical_psychometric

    return analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.human-visual-contrast.descriptive-psychometric",
        protocol_id=HUMAN_VISUAL_CONTRAST_PROTOCOL_ID,
        dataset_id=HUMAN_VISUAL_CONTRAST_DATASET_ID,
        report_title="Human Visual Contrast Prior-Cue Report",
        stimulus_label="Signed target-distractor contrast difference",
        stimulus_units="percentage points; lower-frequency target positive",
        stimulus_metric_name="contrast",
        caveats=[
            (
                "The OSF stats dataset preserves lower-frequency versus higher-frequency "
                "responses, not the original left/right tilt response. Canonical right "
                "therefore means lower-frequency response for this slice."
            ),
            (
                "Stimulus values are reconstructed from deltaC and correctness: positive "
                "values mean the lower-frequency grating was the higher-contrast target."
            ),
            (
                "The source dataset contains trials already filtered by the original "
                "analysis script to RT >= 100 ms and correct/incorrect on-time responses."
            ),
        ],
    )


def human_visual_contrast_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": HUMAN_VISUAL_CONTRAST_PROTOCOL_ID,
        "dataset_id": HUMAN_VISUAL_CONTRAST_DATASET_ID,
        "source": {
            "osf_project_url": WALSH_OSF_PROJECT_URL,
            "osf_doi": WALSH_OSF_DOI,
            "behavioural_analysis_mat_url": WALSH_BEHAVIOURAL_ANALYSIS_MAT_URL,
            "behavioural_analysis_script_url": WALSH_BEHAVIOURAL_ANALYSIS_SCRIPT_URL,
            "experiment_task_script_url": WALSH_EXPERIMENT_TASK_SCRIPT_URL,
            **details,
        },
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "n_trials": len(trials),
        "source_fields": WALSH_DATASET_COLUMNS,
        "response_time_origin": "seconds from evidence onset to button response",
        "outputs": output_files,
        "caveats": [
            (
                "Generated artifacts are ignored by git until dataset licensing and "
                "release policy are confirmed."
            ),
            (
                "The processed OSF stats dataset does not include raw per-session trial "
                "ids or original left/right orientation responses. The slice uses the "
                "available lower-frequency response coding and records the convention in "
                "task_variables."
            ),
        ],
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _walsh_row_source(row: Any) -> dict[str, Any]:
    if len(row) < len(WALSH_DATASET_COLUMNS):
        raise ValueError(
            f"Expected at least {len(WALSH_DATASET_COLUMNS)} Walsh dataset columns, "
            f"got {len(row)}"
        )
    return {
        column: _json_safe_value(row[index])
        for index, column in enumerate(WALSH_DATASET_COLUMNS)
    }


def _validate_walsh_dataset(dataset: Any) -> None:
    if dataset is None:
        raise ValueError("Expected MATLAB variable `dataset`")
    shape = getattr(dataset, "shape", None)
    if shape is None or len(shape) != 2:
        raise ValueError("Expected `dataset` to be a two-dimensional matrix")
    if shape[1] < len(WALSH_DATASET_COLUMNS):
        raise ValueError(
            f"Expected `dataset` to have at least {len(WALSH_DATASET_COLUMNS)} columns, "
            f"got {shape[1]}"
        )


def _contrast_difference_percent(delta_c: float) -> float:
    return (2.0 * delta_c - 1.0) * 100.0


def _performance_correct(value: int) -> bool:
    if value == 1:
        return True
    if value == 2:
        return False
    raise ValueError(f"Expected performance code 1 or 2, got {value!r}")


def _cue_label(value: int) -> str:
    if value not in WALSH_CUE_LABELS:
        raise ValueError(f"Unknown cue code {value!r}")
    return WALSH_CUE_LABELS[value]


def _pulse_label(value: int) -> str:
    if value not in WALSH_PULSE_LABELS:
        raise ValueError(f"Unknown pulse code {value!r}")
    return WALSH_PULSE_LABELS[value]


def _subject_label(value: int) -> str:
    if value < 1 or value > len(WALSH_SUBJECT_LABELS):
        raise ValueError(f"Unknown subject code {value!r}")
    return WALSH_SUBJECT_LABELS[value - 1]


def _required_bool(value: Any, *, field: str) -> bool:
    numeric = _required_float(value, field=field)
    if numeric == 1.0:
        return True
    if numeric == 0.0:
        return False
    raise ValueError(f"Expected {field} to be 0 or 1, got {value!r}")


def _required_int(value: Any, *, field: str) -> int:
    numeric = _required_float(value, field=field)
    if not numeric.is_integer():
        raise ValueError(f"Expected {field} to be integer-coded, got {value!r}")
    return int(numeric)


def _required_float(value: Any, *, field: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected numeric {field}, got {value!r}") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"Expected finite numeric {field}, got {value!r}")
    return numeric


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isfinite(numeric):
        return numeric
    return None
