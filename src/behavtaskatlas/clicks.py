from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from behavtaskatlas.models import CanonicalTrial

BRODY_CLICKS_PROTOCOL_ID = "protocol.poisson-clicks-evidence-accumulation"
BRODY_CLICKS_DATASET_ID = "dataset.brody-lab-poisson-clicks-2009-2024"
DEFAULT_CLICKS_DERIVED_DIR = Path("derived/auditory_clicks")


def harmonize_brody_clicks_trial(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
    subject_id: str | None = None,
    dataset_id: str = BRODY_CLICKS_DATASET_ID,
    protocol_id: str = BRODY_CLICKS_PROTOCOL_ID,
) -> CanonicalTrial:
    missing = sorted(field for field in ["nL", "nR", "gr", "hh", "sd"] if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Brody clicks trial fields: {joined}")

    n_left = int(source["nL"])
    n_right = int(source["nR"])
    click_difference = n_right - n_left
    stimulus_duration = _optional_float(source.get("sd"))
    left_times = _float_list(source.get("left_click_times", []))
    right_times = _float_list(source.get("right_click_times", []))

    return CanonicalTrial(
        protocol_id=protocol_id,
        dataset_id=dataset_id,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="auditory",
        stimulus_value=float(click_difference),
        stimulus_units="right minus left clicks",
        stimulus_side=_evidence_side(click_difference),
        evidence_strength=abs(float(click_difference)),
        evidence_units="absolute click count difference",
        choice=_go_right_label(source["gr"]),
        correct=_optional_hit(source.get("hh")),
        response_time=None,
        response_time_origin=None,
        feedback=_feedback_label(source.get("hh")),
        prior_context=_optional_gamma(source.get("ga")),
        task_variables={
            "left_click_count": n_left,
            "right_click_count": n_right,
            "click_count_difference": click_difference,
            "stimulus_duration": stimulus_duration,
            "left_click_times": left_times,
            "right_click_times": right_times,
            "gamma": _optional_float(source.get("ga")),
            "reward_gamma": _optional_float(source.get("rg")),
            "task_type": source.get("task_type"),
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_brody_clicks_trials(
    parsed: dict[str, Any],
    *,
    session_id: str,
    subject_id: str | None = None,
    task_type: str | None = None,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    n_trials = _parsed_length(parsed)
    if limit is not None:
        n_trials = min(n_trials, limit)
    return [
        harmonize_brody_clicks_trial(
            _parsed_trial_source(parsed, index, task_type=task_type),
            session_id=session_id,
            subject_id=subject_id,
            trial_index=index,
        )
        for index in range(n_trials)
    ]


def load_brody_clicks_mat(
    mat_file: Path,
    *,
    parsed_field: str = "parsed",
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    try:
        import scipy.io
    except ImportError as exc:
        raise RuntimeError(
            "Brody clicks ingestion requires scipy. Install it with `uv sync --extra clicks`."
        ) from exc

    try:
        loaded = scipy.io.loadmat(mat_file, squeeze_me=True, simplify_cells=True)
    except NotImplementedError as exc:
        raise RuntimeError(
            "This MATLAB file appears to require v7.3/HDF5 support. "
            "Add an h5py-backed loader before ingesting this file."
        ) from exc

    ratdata = loaded.get("ratdata")
    if not isinstance(ratdata, dict):
        raise ValueError("Expected MATLAB variable `ratdata` to load as a mapping")
    parsed = ratdata.get(parsed_field)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected ratdata.{parsed_field} to load as a mapping")

    subject_id = mat_file.stem
    trials = harmonize_brody_clicks_trials(
        parsed,
        session_id=f"{subject_id}-{parsed_field}",
        subject_id=subject_id,
        task_type=ratdata.get("task_type"),
        limit=limit,
    )
    details = {
        "source_file": str(mat_file),
        "source_file_name": mat_file.name,
        "source_file_sha256": file_sha256(mat_file),
        "parsed_field": parsed_field,
        "subject_id": subject_id,
        "task_type": ratdata.get("task_type"),
        "n_trials": len(trials),
    }
    return trials, details


def brody_clicks_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    return {
        "protocol_id": BRODY_CLICKS_PROTOCOL_ID,
        "dataset_id": BRODY_CLICKS_DATASET_ID,
        "source": {
            "zenodo_url": "https://zenodo.org/records/13352119",
            "doi": "10.5281/zenodo.13352119",
            **details,
        },
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "n_trials": len(trials),
        "source_fields": ["nL", "nR", "sd", "gr", "hh", "ga", "rg", "bt.left", "bt.right"],
        "outputs": output_files,
        "caveats": [
            "The full Zenodo archive is large and should remain in ignored local raw-data storage.",
            (
                "The archive uses ZIP64/Deflate64 compression; macOS unzip and "
                "Python zipfile may not extract it."
            ),
            "The parsed release excludes violations, frozen trials, and trials longer than 1 s.",
            "Day/session breaks are not identified in the parsed release.",
        ],
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parsed_trial_source(
    parsed: dict[str, Any],
    index: int,
    *,
    task_type: str | None,
) -> dict[str, Any]:
    source = {
        "nL": _index_value(parsed["nL"], index),
        "nR": _index_value(parsed["nR"], index),
        "sd": _index_value(parsed["sd"], index),
        "gr": _index_value(parsed["gr"], index),
        "hh": _index_value(parsed["hh"], index),
        "task_type": task_type,
    }
    for optional_field in ["ga", "rg"]:
        if optional_field in parsed:
            source[optional_field] = _index_value(parsed[optional_field], index)
    if "bt" in parsed:
        bup_times = _index_value(parsed["bt"], index)
        source["left_click_times"] = _extract_click_times(bup_times, "left")
        source["right_click_times"] = _extract_click_times(bup_times, "right")
    return source


def _parsed_length(parsed: dict[str, Any]) -> int:
    required = ["nL", "nR", "sd", "gr", "hh"]
    missing = sorted(field for field in required if field not in parsed)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Brody clicks parsed fields: {joined}")
    n_trials = len(parsed["nL"])
    for field in required:
        if len(parsed[field]) != n_trials:
            actual = len(parsed[field])
            raise ValueError(f"Field {field!r} has length {actual}, expected {n_trials}")
    return n_trials


def _extract_click_times(bup_times: Any, side: str) -> list[float]:
    if isinstance(bup_times, dict):
        return _float_list(bup_times.get(side, []))
    value = getattr(bup_times, side, [])
    return _float_list(value)


def _go_right_label(value: Any) -> str:
    if _as_float(value) == 1.0:
        return "right"
    if _as_float(value) == 0.0:
        return "left"
    return "unknown"


def _optional_hit(value: Any) -> bool | None:
    numeric = _as_float(value)
    if numeric == 1.0:
        return True
    if numeric == 0.0:
        return False
    return None


def _feedback_label(value: Any) -> str:
    hit = _optional_hit(value)
    if hit is True:
        return "reward"
    if hit is False:
        return "error"
    return "unknown"


def _evidence_side(click_difference: int) -> str:
    if click_difference > 0:
        return "right"
    if click_difference < 0:
        return "left"
    return "none"


def _optional_gamma(value: Any) -> str | None:
    numeric = _optional_float(value)
    if numeric is None:
        return None
    return f"gamma={numeric:.3g}"


def _index_value(values: Any, index: int) -> Any:
    value = values[index]
    if hasattr(value, "item"):
        return value.item()
    return value


def _float_list(values: Any) -> list[float]:
    if values is None:
        return []
    try:
        iterator = iter(values)
    except TypeError:
        return [float(values)]
    return [float(value) for value in iterator]


def _optional_float(value: Any) -> float | None:
    numeric = _as_float(value)
    if numeric is None or math.isnan(numeric):
        return None
    return numeric


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe_value(item) for item in value]
    numeric = _as_float(value)
    if numeric is not None and math.isfinite(numeric):
        return numeric
    if value is None:
        return None
    if isinstance(value, str | int | bool):
        return value
    return str(value)
