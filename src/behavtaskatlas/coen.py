from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import numpy as np

from behavtaskatlas.ibl import (
    analyze_canonical_psychometric,
    current_git_commit,
    current_git_dirty,
)
from behavtaskatlas.models import CanonicalTrial

COEN_PROTOCOL_ID = "protocol.mouse-audiovisual-spatial-wheel"
COEN_DATASET_ID = "dataset.coen-audiovisual-decisions-ucl"
DEFAULT_COEN_SESSION_ID = "coen-audiovisual-spatial-wheel-ucl"
DEFAULT_COEN_RAW_FILE = Path("data/raw/coen_audiovisual_decisions/coen_behavior_export.mat")
DEFAULT_COEN_DERIVED_DIR = Path("derived/coen_audiovisual_decisions")
COEN_UCL_RDR_URL = (
    "https://rdr.ucl.ac.uk/articles/dataset/"
    "Mouse_frontal_cortex_mediates_additive_multisensory_decisions/22363180"
)
COEN_UCL_DOI = "10.5522/04/22363180.v1"
COEN_CODE_GITHUB_URL = "https://github.com/pipcoen/2023_CoenSit"
COEN_CODE_ZENODO_DOI = "10.5281/zenodo.7892397"
COEN_CODE_ZENODO_URL = "https://doi.org/10.5281/zenodo.7892397"

COEN_SOURCE_FIELDS = [
    "visDiff",
    "audDiff",
    "responseCalc",
    "correctResponse",
    "reactionTime",
    "responseRecorded",
    "timeToFeedback",
    "validTrial",
    "repeatNum",
    "visual",
    "auditory",
    "coherent",
    "conflict",
    "blank",
    "laserType",
    "galvoPosition",
]

COEN_CONDITION_FIELDS = [
    "modality",
    "trial_class",
    "cue_congruence",
    "visual_diff",
    "auditory_diff",
    "n_trials",
    "n_response",
    "n_no_response",
    "n_left",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "median_response_time",
    "n_laser",
]

COEN_MODALITY_FIELDS = [
    "modality",
    "n_trials",
    "n_response",
    "n_no_response",
    "n_left",
    "n_right",
    "p_right",
    "n_correct",
    "p_correct",
    "median_response_time",
    "n_laser",
]

COEN_CONFLICT_FIELDS = [
    "visual_side",
    "auditory_side",
    "n_trials",
    "n_response",
    "n_visual_choice",
    "n_auditory_choice",
    "p_visual_choice",
    "p_auditory_choice",
    "median_response_time",
]


def load_coen_audiovisual_source(
    source_file: Path = DEFAULT_COEN_RAW_FILE,
    *,
    session_id: str = DEFAULT_COEN_SESSION_ID,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    if source_file.suffix.lower() in {".csv", ".tsv"}:
        rows = load_coen_trial_rows_csv(source_file)
        source_kind = "trial_csv"
        source_variable = source_file.name
    elif source_file.suffix.lower() == ".mat":
        rows, source_variable = load_coen_trial_rows_mat(source_file)
        source_kind = "matlab_block"
    else:
        raise ValueError(
            f"Unsupported Coen source file type: {source_file.suffix}. "
            "Expected a CSV/TSV trial export or MATLAB .mat block file."
        )
    trials = harmonize_coen_audiovisual_rows(rows, base_session_id=session_id, limit=limit)
    details = {
        "source_file": str(source_file),
        "source_file_name": source_file.name,
        "source_file_sha256": file_sha256(source_file),
        "source_kind": source_kind,
        "source_variable": source_variable,
        "source_url": COEN_UCL_RDR_URL,
        "source_doi": COEN_UCL_DOI,
        "code_github_url": COEN_CODE_GITHUB_URL,
        "code_zenodo_url": COEN_CODE_ZENODO_URL,
        "code_zenodo_doi": COEN_CODE_ZENODO_DOI,
        "n_source_rows": len(rows),
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "sessions": sorted({trial.session_id for trial in trials if trial.session_id}),
        "modalities": sorted(
            {
                str(trial.task_variables.get("modality_condition"))
                for trial in trials
                if trial.task_variables.get("modality_condition")
            }
        ),
    }
    return trials, details


def load_coen_trial_rows_csv(path: Path) -> list[dict[str, Any]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter=delimiter)]


def load_coen_trial_rows_mat(path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        import scipy.io
    except ImportError as exc:
        raise RuntimeError(
            "Coen audiovisual MATLAB ingestion requires scipy. "
            "Install it with `uv sync --extra visual`."
        ) from exc

    loaded = scipy.io.loadmat(path, squeeze_me=True, simplify_cells=True)
    candidates = ["blks", "blk", "block", "blockData", "data", "trials", "trial_table"]
    for name in candidates:
        if name in loaded:
            rows = _coen_rows_from_object(loaded[name])
            if rows:
                return rows, name
    for name, value in loaded.items():
        if name.startswith("__"):
            continue
        rows = _coen_rows_from_object(value)
        if rows:
            return rows, name
    raise ValueError(
        "Could not find Coen audiovisual trial data in MATLAB file. Expected a "
        "combined spatialAnalysis block with tri.stim/outcome/trialType fields, "
        "or an exported trial table."
    )


def harmonize_coen_audiovisual_rows(
    rows: list[dict[str, Any]],
    *,
    base_session_id: str = DEFAULT_COEN_SESSION_ID,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    trials: list[CanonicalTrial] = []
    for index, row in enumerate(rows):
        trials.append(
            harmonize_coen_audiovisual_trial(
                row,
                base_session_id=base_session_id,
                trial_index=index,
            )
        )
        if limit is not None and len(trials) >= limit:
            break
    return trials


def harmonize_coen_audiovisual_trial(
    source: dict[str, Any],
    *,
    base_session_id: str,
    trial_index: int,
) -> CanonicalTrial:
    visual_diff = _optional_float(_row_alias(source, ["visDiff", "vis_diff", "stim.visDiff"]))
    auditory_diff = _optional_float(_row_alias(source, ["audDiff", "aud_diff", "stim.audDiff"]))
    if visual_diff is None and auditory_diff is None:
        raise ValueError("Coen trial row requires at least one of visDiff or audDiff")

    response_code = _optional_float(
        _row_alias(source, ["responseCalc", "response_calc", "outcome.responseCalc"])
    )
    response_recorded = _optional_bool(
        _row_alias(source, ["responseRecorded", "response_recorded", "outcome.responseRecorded"])
    )
    valid_trial = _optional_bool(
        _row_alias(source, ["validTrial", "valid_trial", "trialType.validTrial"])
    )
    repeat_num = _optional_int(
        _row_alias(source, ["repeatNum", "repeat_num", "trialType.repeatNum"])
    )
    correct_response = _optional_float(
        _row_alias(source, ["correctResponse", "correct_response", "stim.correctResponse"])
    )
    choice = coen_choice_label(response_code, response_recorded=response_recorded)
    correct = _coen_correct(choice, correct_response)
    feedback = "none"
    if choice in {"left", "right"} and correct is True:
        feedback = "reward"
    elif choice in {"left", "right"} and correct is False:
        feedback = "error"
    response_time = (
        _optional_float(
            _row_alias(source, ["reactionTime", "reaction_time", "outcome.reactionTime"])
        )
        if choice in {"left", "right"}
        else None
    )

    subject_id = _coen_subject_id(source)
    session_id = _coen_session_id(source, base_session_id=base_session_id, subject_id=subject_id)
    stimulus_value = signed_audiovisual_evidence(visual_diff, auditory_diff)
    modality = coen_modality(source, visual_diff=visual_diff, auditory_diff=auditory_diff)
    trial_class = coen_trial_class(source, visual_diff=visual_diff, auditory_diff=auditory_diff)
    cue_congruence = coen_cue_congruence(visual_diff, auditory_diff, source=source)
    visual_side = _side_from_signed(visual_diff)
    auditory_side = _side_from_signed(auditory_diff)
    laser_type = _optional_int(
        _row_alias(source, ["laserType", "laser_type", "inactivation.laserType"])
    )
    galvo_position = _galvo_position(source)
    task_variables = {
        "visual_diff": visual_diff,
        "auditory_diff": auditory_diff,
        "visual_contrast": _optional_float(
            _row_alias(source, ["visContrast", "vis_contrast", "stim.visContrast"])
        ),
        "source_response_code": response_code,
        "source_correct_response_code": correct_response,
        "response_recorded": response_recorded,
        "valid_trial": valid_trial,
        "repeat_num": repeat_num,
        "time_to_feedback": _optional_float(
            _row_alias(source, ["timeToFeedback", "time_to_feedback", "outcome.timeToFeedback"])
        ),
        "condition_label": _json_safe_value(
            _row_alias(source, ["conditionLabel", "condition_label", "stim.conditionLabel"])
        ),
        "modality_condition": modality,
        "trial_class": trial_class,
        "cue_congruence": cue_congruence,
        "visual_side": visual_side,
        "auditory_side": auditory_side,
        "laser_type": laser_type,
        "laser_on": laser_type is not None and laser_type != 0,
        "galvo_position": galvo_position,
        "laser_onset_delay": _optional_float(
            _row_alias(source, ["laserOnsetDelay", "laser_onset_delay"])
        ),
        "source_choice_convention": "responseCalc 1=left, 2=right",
        "source_evidence_convention": "positive visDiff/audDiff indicates rightward evidence",
    }

    return CanonicalTrial(
        protocol_id=COEN_PROTOCOL_ID,
        dataset_id=COEN_DATASET_ID,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality=modality,
        stimulus_value=stimulus_value,
        stimulus_units="source signed visual plus auditory evidence; right positive",
        stimulus_side=_side_from_signed(stimulus_value),
        evidence_strength=abs(stimulus_value) if stimulus_value is not None else None,
        evidence_units="absolute source signed audiovisual evidence proxy",
        choice=choice,
        correct=correct if valid_trial is not False else None,
        response_time=response_time,
        response_time_origin="outcome.reactionTime relative to stimulus onset",
        feedback=feedback if valid_trial is not False else "none",
        block_id=str(_row_alias(source, ["expRef", "exp_ref", "source_exp_ref"]) or session_id),
        prior_context=modality,
        task_variables={key: value for key, value in task_variables.items() if value is not None},
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def signed_audiovisual_evidence(
    visual_diff: float | None,
    auditory_diff: float | None,
) -> float | None:
    if visual_diff is None and auditory_diff is None:
        return None
    return (visual_diff or 0.0) + (auditory_diff or 0.0)


def coen_choice_label(value: Any, *, response_recorded: bool | None = None) -> str:
    code = _optional_float(value)
    if response_recorded is False or code is None:
        return "no-response"
    if math.isclose(code, 1.0):
        return "left"
    if math.isclose(code, 2.0):
        return "right"
    return "unknown"


def coen_modality(
    source: dict[str, Any],
    *,
    visual_diff: float | None,
    auditory_diff: float | None,
) -> str:
    if _source_flag(source, ["visual", "trialType.visual"]):
        return "visual"
    if _source_flag(source, ["auditory", "trialType.auditory"]):
        return "auditory"
    if _source_flag(source, ["coherent", "conflict", "trialType.coherent", "trialType.conflict"]):
        return "multisensory"
    has_visual = visual_diff is not None and not math.isclose(visual_diff, 0.0)
    has_auditory = auditory_diff is not None and not math.isclose(auditory_diff, 0.0)
    if has_visual and has_auditory:
        return "multisensory"
    if has_visual:
        return "visual"
    if has_auditory:
        return "auditory"
    return "none"


def coen_trial_class(
    source: dict[str, Any],
    *,
    visual_diff: float | None,
    auditory_diff: float | None,
) -> str:
    if _source_flag(source, ["blank", "trialType.blank"]):
        return "blank"
    if _source_flag(source, ["visual", "trialType.visual"]):
        return "visual"
    if _source_flag(source, ["auditory", "trialType.auditory"]):
        return "auditory"
    if _source_flag(source, ["coherent", "trialType.coherent"]):
        return "coherent"
    if _source_flag(source, ["conflict", "trialType.conflict"]):
        return "conflict"
    congruence = coen_cue_congruence(visual_diff, auditory_diff, source=source)
    if congruence in {"coherent", "conflict"}:
        return congruence
    return coen_modality(source, visual_diff=visual_diff, auditory_diff=auditory_diff)


def coen_cue_congruence(
    visual_diff: float | None,
    auditory_diff: float | None,
    *,
    source: dict[str, Any] | None = None,
) -> str | None:
    source = source or {}
    if _source_flag(source, ["coherent", "trialType.coherent"]):
        return "coherent"
    if _source_flag(source, ["conflict", "trialType.conflict"]):
        return "conflict"
    if visual_diff is None or auditory_diff is None:
        return None
    if math.isclose(visual_diff, 0.0) or math.isclose(auditory_diff, 0.0):
        return None
    product = visual_diff * auditory_diff
    if product > 0:
        return "coherent"
    if product < 0:
        return "conflict"
    return None


def analyze_coen_audiovisual_decisions(trials: list[CanonicalTrial]) -> dict[str, Any]:
    psychometric_trials = [trial for trial in trials if trial.choice in {"left", "right"}]
    result = analyze_canonical_psychometric(
        psychometric_trials,
        analysis_id="analysis.coen-audiovisual-spatial-wheel.descriptive-multisensory",
        protocol_id=COEN_PROTOCOL_ID,
        dataset_id=COEN_DATASET_ID,
        report_title="Coen Audiovisual Spatial Decision Report",
        stimulus_label="Signed audiovisual evidence proxy",
        stimulus_units="source visDiff + audDiff, right positive",
        stimulus_metric_name="audiovisual_evidence",
        caveats=[
            (
                "The scalar psychometric axis is a descriptive proxy formed from "
                "source visDiff plus audDiff. Visual and auditory evidence values "
                "are preserved separately in task_variables and condition summaries."
            ),
            (
                "Conflict-trial correctness follows the source correctResponse code "
                "when present; alternative conflict policies should be represented as "
                "separate analyses."
            ),
            (
                "Laser/inactivation metadata is retained, but the default summary "
                "does not estimate causal inactivation effects."
            ),
            (
                "No-response trials are retained in canonical trials and condition "
                "summaries, but excluded from the descriptive psychometric proxy fit."
            ),
        ],
    )
    result["analysis_type"] = "descriptive_multisensory_psychometric"
    result["n_trials"] = len(trials)
    result["n_response_trials"] = len(psychometric_trials)
    result["n_no_response_trials"] = len(trials) - len(psychometric_trials)
    result["condition_rows"] = coen_condition_summary_rows(trials)
    result["modality_rows"] = coen_modality_summary_rows(trials)
    result["conflict_rows"] = coen_conflict_summary_rows(trials)
    result["n_subjects"] = len({trial.subject_id for trial in trials if trial.subject_id})
    result["n_sessions"] = len({trial.session_id for trial in trials if trial.session_id})
    result["n_conditions"] = len(result["condition_rows"])
    result["n_laser_trials"] = sum(
        1 for trial in trials if trial.task_variables.get("laser_on") is True
    )
    result["n_control_trials"] = len(trials) - result["n_laser_trials"]
    return result


def coen_condition_summary_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        grouped[
            (
                trial.task_variables.get("modality_condition"),
                trial.task_variables.get("trial_class"),
                trial.task_variables.get("cue_congruence"),
                trial.task_variables.get("visual_diff"),
                trial.task_variables.get("auditory_diff"),
            )
        ].append(trial)
    rows = []
    for key, group in sorted(grouped.items(), key=lambda item: _condition_sort_key(item[0])):
        modality, trial_class, cue_congruence, visual_diff, auditory_diff = key
        rows.append(
            {
                "modality": modality,
                "trial_class": trial_class,
                "cue_congruence": cue_congruence,
                "visual_diff": visual_diff,
                "auditory_diff": auditory_diff,
                **_choice_summary(group),
            }
        )
    return rows


def coen_modality_summary_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[str, list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        modality = str(trial.task_variables.get("modality_condition") or trial.stimulus_modality)
        grouped[modality].append(trial)
    return [
        {"modality": modality, **_choice_summary(group)}
        for modality, group in sorted(grouped.items())
    ]


def coen_conflict_summary_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        if trial.task_variables.get("cue_congruence") != "conflict":
            continue
        visual_side = str(trial.task_variables.get("visual_side") or "unknown")
        auditory_side = str(trial.task_variables.get("auditory_side") or "unknown")
        grouped[(visual_side, auditory_side)].append(trial)

    rows = []
    for (visual_side, auditory_side), group in sorted(grouped.items()):
        response_trials = [trial for trial in group if trial.choice in {"left", "right"}]
        visual_choice = sum(1 for trial in response_trials if trial.choice == visual_side)
        auditory_choice = sum(1 for trial in response_trials if trial.choice == auditory_side)
        response_times = [
            trial.response_time for trial in response_trials if trial.response_time is not None
        ]
        rows.append(
            {
                "visual_side": visual_side,
                "auditory_side": auditory_side,
                "n_trials": len(group),
                "n_response": len(response_trials),
                "n_visual_choice": visual_choice,
                "n_auditory_choice": auditory_choice,
                "p_visual_choice": _safe_ratio(visual_choice, len(response_trials)),
                "p_auditory_choice": _safe_ratio(auditory_choice, len(response_trials)),
                "median_response_time": statistics.median(response_times)
                if response_times
                else None,
            }
        )
    return rows


def write_coen_condition_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_rows(path, rows, COEN_CONDITION_FIELDS)


def write_coen_modality_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_rows(path, rows, COEN_MODALITY_FIELDS)


def write_coen_conflict_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_rows(path, rows, COEN_CONFLICT_FIELDS)


def write_coen_condition_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(coen_condition_svg(rows), encoding="utf-8")


def write_coen_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    condition_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        coen_report_html(
            analysis_result,
            provenance=provenance,
            psychometric_svg_text=psychometric_svg_text,
            condition_svg_text=condition_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def coen_provenance_payload(
    *,
    details: dict[str, Any],
    trials: list[CanonicalTrial],
    output_files: dict[str, str],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": COEN_PROTOCOL_ID,
        "dataset_id": COEN_DATASET_ID,
        "source": details,
        "source_fields": COEN_SOURCE_FIELDS,
        "response_time_origin": "outcome.reactionTime relative to stimulus onset",
        "n_trials": len(trials),
        "exclusions": {
            "no_response_trials": sum(1 for trial in trials if trial.choice == "no-response"),
            "invalid_trials": sum(
                1 for trial in trials if trial.task_variables.get("valid_trial") is False
            ),
            "missing_response_time": sum(1 for trial in trials if trial.response_time is None),
        },
        "outputs": output_files,
        "caveats": [
            (
                "The UCL release is large and CC BY-NC-ND 4.0; this adapter expects "
                "local ignored source files and does not redistribute raw or processed data."
            ),
            (
                "CSV exports should retain source field names from the combined "
                "spatialAnalysis block so provenance remains auditable."
            ),
        ],
    }


def coen_condition_svg(rows: list[dict[str, Any]]) -> str:
    plotted = [
        row
        for row in rows
        if row.get("visual_diff") is not None
        and row.get("auditory_diff") is not None
        and row.get("p_right") is not None
    ]
    if not plotted:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No Coen condition-summary data available</text></svg>\n'
        )
    width = 720
    height = 420
    left = 86
    right = 118
    top = 34
    bottom = 62
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_values = [float(row["visual_diff"]) for row in plotted]
    y_values = [float(row["auditory_diff"]) for row in plotted]
    x_min, x_max = _padded_extent(x_values)
    y_min, y_max = _padded_extent(y_values)

    def x_scale(value: float) -> float:
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def y_scale(value: float) -> float:
        return top + ((y_max - value) / (y_max - y_min)) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="22" text-anchor="middle" '
        'font-family="sans-serif" font-size="16">Audiovisual condition surface</text>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 18}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14">Visual evidence (visDiff)</text>',
        f'<text x="20" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 20 '
        f'{top + plot_height / 2})">Auditory evidence (audDiff)</text>',
    ]
    for value in _axis_tick_values(x_min, x_max):
        x = x_scale(value)
        elements.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="10">{value:g}</text>'
        )
    for value in _axis_tick_values(y_min, y_max):
        y = y_scale(value)
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="10">{value:g}</text>'
        )
    zero_x = x_scale(0.0) if x_min <= 0.0 <= x_max else None
    zero_y = y_scale(0.0) if y_min <= 0.0 <= y_max else None
    if zero_x is not None:
        elements.append(
            f'<line x1="{zero_x:.1f}" y1="{top}" x2="{zero_x:.1f}" '
            f'y2="{top + plot_height}" stroke="#ccc" stroke-dasharray="4 4"/>'
        )
    if zero_y is not None:
        elements.append(
            f'<line x1="{left}" y1="{zero_y:.1f}" x2="{left + plot_width}" '
            f'y2="{zero_y:.1f}" stroke="#ccc" stroke-dasharray="4 4"/>'
        )
    for row in plotted:
        x = x_scale(float(row["visual_diff"]))
        y = y_scale(float(row["auditory_diff"]))
        p_right = float(row["p_right"])
        radius = 4.0 + min(int(row.get("n_trials", 0) or 0), 80) / 12.0
        color = _p_right_color(p_right)
        elements.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" '
            'fill-opacity="0.82" stroke="#222" stroke-width="0.5"/>'
        )
    legend_x = left + plot_width + 28
    for idx, value in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
        y = top + 36 + idx * 32
        elements.append(
            f'<rect x="{legend_x}" y="{y - 12}" width="18" height="18" '
            f'fill="{_p_right_color(value)}" stroke="#222" stroke-width="0.4"/>'
        )
        elements.append(
            f'<text x="{legend_x + 26}" y="{y + 2}" font-family="sans-serif" '
            f'font-size="11">P(right) {value:.2g}</text>'
        )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def coen_report_html(
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    condition_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    provenance = provenance or {}
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    artifact_links = artifact_links or {}
    psychometric_svg_text = psychometric_svg_text or (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        '<text x="20" y="60">Psychometric plot not available</text></svg>'
    )
    condition_svg_text = condition_svg_text or (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        '<text x="20" y="60">Condition surface not available</text></svg>'
    )
    title = str(analysis_result.get("report_title") or "Coen Audiovisual Decision Report")
    metrics = [
        ("Trials", analysis_result.get("n_trials")),
        ("Response trials", analysis_result.get("n_response_trials")),
        ("No-response trials", analysis_result.get("n_no_response_trials")),
        ("Subjects", analysis_result.get("n_subjects")),
        ("Sessions", analysis_result.get("n_sessions")),
        ("Conditions", analysis_result.get("n_conditions")),
        ("Laser trials", analysis_result.get("n_laser_trials")),
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
        "<p class=\"lede\">Audiovisual spatial choice report over visual, auditory, "
        "coherent, and conflict trial conditions.</p>",
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
                    ("UCL repository", source.get("source_url")),
                    ("Dataset DOI", source.get("source_doi")),
                    ("Code", source.get("code_github_url")),
                    ("Source file", source.get("source_file_name")),
                    ("Source kind", source.get("source_kind")),
                    ("Source variable", source.get("source_variable")),
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
            "<section>",
            "<h2>Psychometric Proxy</h2>",
            '<div class="figure-wrap">',
            psychometric_svg_text,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Condition Surface</h2>",
            '<div class="figure-wrap">',
            condition_svg_text,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Modality Summary</h2>",
            _html_table(
                analysis_result.get("modality_rows", []),
                [
                    ("modality", "Modality"),
                    ("n_trials", "Trials"),
                    ("n_response", "Responses"),
                    ("p_right", "P(right)"),
                    ("p_correct", "P(correct)"),
                    ("median_response_time", "Median RT"),
                    ("n_laser", "Laser"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Condition Summary</h2>",
            _html_table(
                analysis_result.get("condition_rows", []),
                [
                    ("modality", "Modality"),
                    ("trial_class", "Class"),
                    ("cue_congruence", "Congruence"),
                    ("visual_diff", "visDiff"),
                    ("auditory_diff", "audDiff"),
                    ("n_trials", "Trials"),
                    ("p_right", "P(right)"),
                    ("p_correct", "P(correct)"),
                    ("median_response_time", "Median RT"),
                ],
            ),
            "</section>",
        ]
    )
    conflict_rows = analysis_result.get("conflict_rows", [])
    if conflict_rows:
        html.extend(
            [
                "<section>",
                "<h2>Conflict Choices</h2>",
                _html_table(
                    conflict_rows,
                    [
                        ("visual_side", "Visual side"),
                        ("auditory_side", "Auditory side"),
                        ("n_trials", "Trials"),
                        ("n_response", "Responses"),
                        ("p_visual_choice", "P(visual choice)"),
                        ("p_auditory_choice", "P(auditory choice)"),
                        ("median_response_time", "Median RT"),
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _coen_rows_from_object(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if _looks_like_trial_table(value):
            return _rows_from_table_dict(value)
        if "tri" in value and isinstance(value["tri"], dict):
            return _rows_from_combined_block(value)
        if _looks_like_proc_block(value):
            return _rows_from_proc_block(value)
    if isinstance(value, list | tuple):
        rows: list[dict[str, Any]] = []
        for item in value:
            rows.extend(_coen_rows_from_object(item))
        return rows
    if isinstance(value, np.ndarray):
        rows = []
        for item in value.flat:
            rows.extend(_coen_rows_from_object(item))
        return rows
    return []


def _looks_like_trial_table(value: dict[str, Any]) -> bool:
    lowered = {key.lower() for key in value}
    return (
        bool({"visdiff", "vis_diff", "stim.visdiff"} & lowered)
        and bool({"auddiff", "aud_diff", "stim.auddiff"} & lowered)
        and bool({"responsecalc", "response_calc", "outcome.responsecalc"} & lowered)
    )


def _looks_like_proc_block(value: dict[str, Any]) -> bool:
    return (
        isinstance(value.get("stim"), dict)
        and isinstance(value.get("outcome"), dict)
        and isinstance(value.get("trialType"), dict)
        and ("visDiff" in value["stim"] or "audDiff" in value["stim"])
        and "responseCalc" in value["outcome"]
    )


def _rows_from_table_dict(table: dict[str, Any]) -> list[dict[str, Any]]:
    keys = [key for key, value in table.items() if _is_row_vector(value)]
    if not keys:
        return []
    n_rows = max(len(_as_vector(table[key])) for key in keys)
    return [
        {
            key: _index_value(table[key], index)
            for key in keys
            if len(_as_vector(table[key])) > index
        }
        for index in range(n_rows)
    ]


def _rows_from_proc_block(block: dict[str, Any]) -> list[dict[str, Any]]:
    stim = block.get("stim", {})
    n_trials = len(_as_vector(stim.get("visDiff", stim.get("audDiff", []))))
    if n_trials == 0:
        return []
    subject = _optional_text(block.get("subject"))
    exp_date = _optional_text(block.get("expDate"))
    exp_num = _optional_text(block.get("expNum"))
    session_id = ".".join(
        _session_token(part) for part in [subject, exp_date, exp_num] if part
    )
    trial_type = block.get("trialType", {})
    outcome = block.get("outcome", {})
    inactivation = block.get("inactivation", {})
    return [
        {
            "source_trial_index": index,
            "subject": subject,
            "session_id": session_id or None,
            "expDate": exp_date,
            "expNum": exp_num,
            "visDiff": _index_nested(block, ["stim", "visDiff"], index),
            "audDiff": _index_nested(block, ["stim", "audDiff"], index),
            "visContrast": _index_nested(block, ["stim", "visContrast"], index),
            "correctResponse": _index_nested(block, ["stim", "correctResponse"], index),
            "conditionLabel": _index_nested(block, ["stim", "conditionLabel"], index),
            "responseCalc": _index_value(outcome.get("responseCalc"), index),
            "reactionTime": _index_value(outcome.get("reactionTime"), index),
            "responseRecorded": _index_value(outcome.get("responseRecorded"), index),
            "timeToFeedback": _index_value(outcome.get("timeToFeedback"), index),
            "validTrial": _index_value(trial_type.get("validTrial"), index),
            "repeatNum": _index_value(trial_type.get("repeatNum"), index),
            "visual": _index_value(trial_type.get("visual"), index),
            "auditory": _index_value(trial_type.get("auditory"), index),
            "coherent": _index_value(trial_type.get("coherent"), index),
            "conflict": _index_value(trial_type.get("conflict"), index),
            "blank": _index_value(trial_type.get("blank"), index),
            "laserType": _index_value(inactivation.get("laserType"), index),
            "galvoPosition": _index_value(inactivation.get("galvoPosition"), index),
            "laserOnsetDelay": _index_value(inactivation.get("laserOnsetDelay"), index),
        }
        for index in range(n_trials)
    ]


def _rows_from_combined_block(block: dict[str, Any]) -> list[dict[str, Any]]:
    tri = block.get("tri", {})
    stim = tri.get("stim", {}) if isinstance(tri, dict) else {}
    n_trials = len(_as_vector(stim.get("visDiff", stim.get("audDiff", []))))
    if n_trials == 0:
        return []
    exp = block.get("exp", {}) if isinstance(block.get("exp"), dict) else {}
    rows = []
    for index in range(n_trials):
        exp_ref = _optional_int(_index_nested(tri, ["expRef"], index))
        subject_ref = _optional_int(_index_nested(tri, ["subjectRef"], index))
        rows.append(
            {
                "source_trial_index": index,
                "subject": _exp_field(exp, "subject", exp_ref),
                "subjectRef": subject_ref,
                "session_id": _session_from_exp(exp, exp_ref),
                "expRef": exp_ref,
                "expDate": _exp_field(exp, "expDate", exp_ref),
                "expNum": _exp_field(exp, "expNum", exp_ref),
                "visDiff": _index_nested(tri, ["stim", "visDiff"], index),
                "audDiff": _index_nested(tri, ["stim", "audDiff"], index),
                "visContrast": _index_nested(tri, ["stim", "visContrast"], index),
                "correctResponse": _index_nested(tri, ["stim", "correctResponse"], index),
                "conditionLabel": _index_nested(tri, ["stim", "conditionLabel"], index),
                "responseCalc": _index_nested(tri, ["outcome", "responseCalc"], index),
                "reactionTime": _index_nested(tri, ["outcome", "reactionTime"], index),
                "responseRecorded": _index_nested(tri, ["outcome", "responseRecorded"], index),
                "timeToFeedback": _index_nested(tri, ["outcome", "timeToFeedback"], index),
                "validTrial": _index_nested(tri, ["trialType", "validTrial"], index),
                "repeatNum": _index_nested(tri, ["trialType", "repeatNum"], index),
                "visual": _index_nested(tri, ["trialType", "visual"], index),
                "auditory": _index_nested(tri, ["trialType", "auditory"], index),
                "coherent": _index_nested(tri, ["trialType", "coherent"], index),
                "conflict": _index_nested(tri, ["trialType", "conflict"], index),
                "blank": _index_nested(tri, ["trialType", "blank"], index),
                "laserType": _index_nested(tri, ["inactivation", "laserType"], index),
                "galvoPosition": _index_nested(tri, ["inactivation", "galvoPosition"], index),
                "laserOnsetDelay": _index_nested(
                    tri, ["inactivation", "laserOnsetDelay"], index
                ),
            }
        )
    return rows


def _index_nested(mapping: dict[str, Any], path: list[str], index: int) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return _index_value(value, index)


def _exp_field(exp: dict[str, Any], key: str, exp_ref: int | None) -> Any:
    if exp_ref is None or key not in exp:
        return None
    return _index_value(exp[key], max(exp_ref - 1, 0))


def _session_from_exp(exp: dict[str, Any], exp_ref: int | None) -> str | None:
    subject = _optional_text(_exp_field(exp, "subject", exp_ref))
    exp_date = _optional_text(_exp_field(exp, "expDate", exp_ref))
    exp_num = _optional_text(_exp_field(exp, "expNum", exp_ref))
    if not any([subject, exp_date, exp_num]):
        return None
    return ".".join(_session_token(part) for part in [subject, exp_date, exp_num] if part)


def _coen_subject_id(source: dict[str, Any]) -> str | None:
    value = _row_alias(source, ["subject_id", "subject", "mouse", "mouse_id"])
    text = _optional_text(value)
    return _session_token(text) if text else None


def _coen_session_id(
    source: dict[str, Any],
    *,
    base_session_id: str,
    subject_id: str | None,
) -> str:
    value = _row_alias(source, ["session_id", "session", "sessionID"])
    text = _optional_text(value)
    if text:
        return _session_token(text)
    exp_date = _optional_text(_row_alias(source, ["expDate", "exp_date"]))
    exp_num = _optional_text(_row_alias(source, ["expNum", "exp_num"]))
    parts = [base_session_id]
    if subject_id:
        parts.append(subject_id)
    if exp_date:
        parts.append(exp_date)
    if exp_num:
        parts.append(exp_num)
    return ".".join(_session_token(part) for part in parts)


def _coen_correct(choice: str, correct_response: float | None) -> bool | None:
    if choice not in {"left", "right"} or correct_response is None:
        return None
    expected = coen_choice_label(correct_response)
    if expected not in {"left", "right"}:
        return None
    return choice == expected


def _choice_summary(group: list[CanonicalTrial]) -> dict[str, Any]:
    response_trials = [trial for trial in group if trial.choice in {"left", "right"}]
    n_left = sum(1 for trial in response_trials if trial.choice == "left")
    n_right = sum(1 for trial in response_trials if trial.choice == "right")
    correct_trials = [trial for trial in response_trials if trial.correct is not None]
    n_correct = sum(1 for trial in correct_trials if trial.correct)
    response_times = [
        trial.response_time for trial in response_trials if trial.response_time is not None
    ]
    return {
        "n_trials": len(group),
        "n_response": len(response_trials),
        "n_no_response": len(group) - len(response_trials),
        "n_left": n_left,
        "n_right": n_right,
        "p_right": _safe_ratio(n_right, len(response_trials)),
        "n_correct": n_correct,
        "p_correct": _safe_ratio(n_correct, len(correct_trials)),
        "median_response_time": statistics.median(response_times) if response_times else None,
        "n_laser": sum(1 for trial in group if trial.task_variables.get("laser_on") is True),
    }


def _condition_sort_key(key: tuple[Any, ...]) -> tuple[str, str, str, float, float]:
    modality, trial_class, cue_congruence, visual_diff, auditory_diff = key
    return (
        str(modality or ""),
        str(trial_class or ""),
        str(cue_congruence or ""),
        _none_safe_float(visual_diff),
        _none_safe_float(auditory_diff),
    )


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _row_alias(row: dict[str, Any], names: list[str]) -> Any:
    lowered = {str(key).lower(): key for key in row}
    for name in names:
        key = lowered.get(name.lower())
        if key is not None:
            return row[key]
    return None


def _source_flag(source: dict[str, Any], names: list[str]) -> bool:
    return any(_optional_bool(_row_alias(source, [name])) is True for name in names)


def _galvo_position(source: dict[str, Any]) -> Any:
    direct = _row_alias(source, ["galvoPosition", "galvo_position", "inactivation.galvoPosition"])
    if direct is not None:
        return _json_safe_value(direct)
    x_value = _row_alias(source, ["galvoPositionX", "galvo_x", "galvoPosition_1"])
    y_value = _row_alias(source, ["galvoPositionY", "galvo_y", "galvoPosition_2"])
    if x_value is None and y_value is None:
        return None
    return [_optional_float(x_value), _optional_float(y_value)]


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped in {"", "nan", "none", "null"}:
            return None
        if stripped in {"true", "t", "yes", "y"}:
            return True
        if stripped in {"false", "f", "no", "n"}:
            return False
        try:
            return bool(int(float(stripped)))
        except ValueError:
            return None
    if isinstance(value, bool | np.bool_):
        return bool(value)
    number = _optional_float(value)
    if number is None:
        return None
    return not math.isclose(number, 0.0)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "" or stripped.lower() in {"nan", "none", "null"}:
            return None
        try:
            value = float(stripped)
        except ValueError:
            return None
    if isinstance(value, np.ndarray):
        if value.size != 1:
            return None
        value = value.item()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def _optional_int(value: Any) -> int | None:
    number = _optional_float(value)
    return int(number) if number is not None else None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        if value.size != 1:
            return None
        value = value.item()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _side_from_signed(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > 0:
        return "right"
    if value < 0:
        return "left"
    return "none"


def _as_vector(values: Any) -> list[Any]:
    if isinstance(values, np.ndarray):
        if values.ndim == 0:
            return [values.item()]
        return list(values.tolist())
    if isinstance(values, list | tuple):
        return list(values)
    if values is None:
        return []
    return [values]


def _is_row_vector(value: Any) -> bool:
    return len(_as_vector(value)) > 0


def _index_value(values: Any, index: int) -> Any:
    vector = _as_vector(values)
    if index >= len(vector):
        return None
    value = vector[index]
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return value.item()
        return value.tolist()
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value.tolist()
    return value


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list | tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    return value


def _session_token(value: str) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(":", "-")
    )


def _safe_ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _none_safe_float(value: Any) -> float:
    number = _optional_float(value)
    return float("inf") if number is None else number


def _padded_extent(values: list[float]) -> tuple[float, float]:
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        return min_value - 1.0, max_value + 1.0
    padding = (max_value - min_value) * 0.08
    return min_value - padding, max_value + padding


def _axis_tick_values(min_value: float, max_value: float) -> list[float]:
    if not math.isfinite(min_value) or not math.isfinite(max_value):
        return []
    if math.isclose(min_value, max_value):
        return [min_value]
    step = (max_value - min_value) / 4
    return [min_value + step * index for index in range(5)]


def _p_right_color(value: float) -> str:
    value = max(0.0, min(1.0, value))
    if value < 0.5:
        mix = value / 0.5
        r = int(40 + mix * (245 - 40))
        g = int(96 + mix * (245 - 96))
        b = int(170 + mix * (245 - 170))
    else:
        mix = (value - 0.5) / 0.5
        r = int(245 + mix * (190 - 245))
        g = int(245 + mix * (55 - 245))
        b = int(245 + mix * (45 - 245))
    return f"#{r:02x}{g:02x}{b:02x}"


def _format_cell(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        return f"{value:.3g}"
    if isinstance(value, list):
        return ", ".join(_format_cell(item) for item in value)
    return str(value)


def _definition_list(items: list[tuple[str, Any]]) -> str:
    rows = ["<dl>"]
    for label, value in items:
        rows.append(f"<dt>{escape(label)}</dt><dd>{escape(_format_cell(value))}</dd>")
    rows.append("</dl>")
    return "\n".join(rows)


def _html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "<p>No rows available.</p>"
    html = ["<div class=\"table-wrap\"><table><thead><tr>"]
    html.extend(f"<th>{escape(label)}</th>" for _, label in columns)
    html.extend(["</tr></thead><tbody>"])
    for row in rows:
        html.append("<tr>")
        for key, _ in columns:
            html.append(f"<td>{escape(_format_cell(row.get(key)))}</td>")
        html.append("</tr>")
    html.extend(["</tbody></table></div>"])
    return "\n".join(html)


def _report_css() -> str:
    return """
:root {
  color-scheme: light;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
}
body { margin: 0; background: #f7f8f9; color: #1f2933; }
main { max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }
header, section { margin-bottom: 24px; }
h1 { margin: 0 0 10px; font-size: 32px; line-height: 1.15; }
h2 { margin: 0 0 12px; font-size: 20px; }
.eyebrow { margin: 0 0 8px; color: #5f6b7a; font-size: 13px; letter-spacing: 0; }
.lede { max-width: 760px; color: #4b5563; font-size: 16px; line-height: 1.55; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
.metric { background: white; border: 1px solid #dce2e8; border-radius: 8px; padding: 12px; }
.metric span { display: block; color: #667085; font-size: 12px; margin-bottom: 4px; }
.metric strong { font-size: 20px; }
.grid-two { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }
section { background: white; border: 1px solid #dce2e8; border-radius: 8px; padding: 18px; }
dl { display: grid; grid-template-columns: 130px 1fr; gap: 8px 12px; margin: 0; }
dt { color: #667085; }
dd { margin: 0; overflow-wrap: anywhere; }
.figure-wrap { overflow-x: auto; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { border-bottom: 1px solid #e5e9ef; padding: 8px 10px; text-align: left; }
th { color: #344054; background: #f8fafc; }
.artifact-list { columns: 2; padding-left: 20px; }
a { color: #145f91; }
""".strip()
