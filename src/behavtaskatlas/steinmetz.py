from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import numpy as np

from behavtaskatlas.ibl import (
    current_git_commit,
    current_git_dirty,
    fit_psychometric_rows,
)
from behavtaskatlas.ibl import (
    load_canonical_trials_csv as _load_canonical_trials_csv,
)
from behavtaskatlas.models import CanonicalTrial

STEINMETZ_PROTOCOL_ID = "protocol.mouse-unforced-visual-contrast-wheel"
STEINMETZ_DATASET_ID = "dataset.steinmetz-visual-decision-figshare"
DEFAULT_STEINMETZ_SESSION_ID = "steinmetz-session"
DEFAULT_STEINMETZ_RAW_DIR = Path("data/raw/steinmetz_visual_decision")
DEFAULT_STEINMETZ_DERIVED_DIR = Path("derived/steinmetz_visual_decision")
STEINMETZ_FIGSHARE_URL = (
    "https://figshare.com/articles/dataset/"
    "Distributed_coding_of_choice_action_and_engagement_across_the_mouse_brain/9974357"
)
STEINMETZ_SOURCE_DOI = "10.6084/m9.figshare.9974357.v3"
STEINMETZ_WIKI_URL = "https://github.com/nsteinme/steinmetz-et-al-2019/wiki/data-files"

STEINMETZ_TRIAL_FILES = {
    "feedbackType": "trials.feedbackType.npy",
    "feedback_times": "trials.feedback_times.npy",
    "goCue_times": "trials.goCue_times.npy",
    "included": "trials.included.npy",
    "intervals": "trials.intervals.npy",
    "repNum": "trials.repNum.npy",
    "response_choice": "trials.response_choice.npy",
    "response_times": "trials.response_times.npy",
    "visualStim_contrastLeft": "trials.visualStim_contrastLeft.npy",
    "visualStim_contrastRight": "trials.visualStim_contrastRight.npy",
    "visualStim_times": "trials.visualStim_times.npy",
}

STEINMETZ_REQUIRED_TRIAL_FIELDS = {
    "feedbackType",
    "response_choice",
    "response_times",
    "visualStim_contrastLeft",
    "visualStim_contrastRight",
    "visualStim_times",
}

STEINMETZ_OPTIONAL_TRIAL_FIELDS = set(STEINMETZ_TRIAL_FILES) - STEINMETZ_REQUIRED_TRIAL_FIELDS

STEINMETZ_CHOICE_SUMMARY_FIELDS = [
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
    "n_included",
]

STEINMETZ_CONDITION_SUMMARY_FIELDS = [
    "left_contrast",
    "right_contrast",
    *STEINMETZ_CHOICE_SUMMARY_FIELDS[1:],
]

STEINMETZ_AGGREGATE_SESSION_FIELDS = [
    "session_id",
    "subject_id",
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
    "n_included",
    "n_signed_contrast_levels",
    "n_contrast_conditions",
]

STEINMETZ_AGGREGATE_SUBJECT_FIELDS = [
    "subject_id",
    "session_ids",
    "n_sessions",
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
    "n_included",
    "n_signed_contrast_levels",
    "n_contrast_conditions",
]

STEINMETZ_AGGREGATE_SIGNED_CONTRAST_FIELDS = [
    "stimulus_value",
    "session_ids",
    "subject_ids",
    "n_sessions",
    "n_subjects",
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
    "n_included",
    "mean_session_n_trials",
    "mean_session_p_right",
    "sem_session_p_right",
    "mean_session_p_withhold",
    "sem_session_p_withhold",
    "mean_session_p_correct",
    "sem_session_p_correct",
    "mean_subject_n_trials",
    "mean_subject_p_right",
    "sem_subject_p_right",
    "mean_subject_p_withhold",
    "sem_subject_p_withhold",
    "mean_subject_p_correct",
    "sem_subject_p_correct",
]


def load_steinmetz_session_dir(session_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load one extracted Steinmetz ALF session directory.

    The full Figshare archive is large, so this loader expects the user to extract one
    session directory locally and points only at the trial-level `.npy` files.
    """

    missing = [
        field
        for field in sorted(STEINMETZ_REQUIRED_TRIAL_FIELDS)
        if _find_steinmetz_file(session_dir, STEINMETZ_TRIAL_FILES[field]) is None
    ]
    if missing:
        filenames = ", ".join(STEINMETZ_TRIAL_FILES[field] for field in missing)
        raise FileNotFoundError(
            f"Missing required Steinmetz trial files under {session_dir}: {filenames}"
        )

    trials: dict[str, Any] = {}
    source_files: dict[str, str] = {}
    for field, filename in sorted(STEINMETZ_TRIAL_FILES.items()):
        path = _find_steinmetz_file(session_dir, filename)
        if path is None:
            continue
        trials[field] = np.load(path, allow_pickle=False)
        source_files[field] = str(path)

    _validate_steinmetz_trials_object(trials)
    n_trials = len(trials["response_choice"])
    details = {
        "session_dir": str(session_dir),
        "source_files": source_files,
        "source_fields": sorted(trials),
        "n_trials": n_trials,
        "figshare_url": STEINMETZ_FIGSHARE_URL,
        "figshare_doi": STEINMETZ_SOURCE_DOI,
        "data_dictionary_url": STEINMETZ_WIKI_URL,
    }
    return trials, details


def harmonize_steinmetz_visual_trial(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
    subject_id: str | None = None,
    dataset_id: str = STEINMETZ_DATASET_ID,
    protocol_id: str = STEINMETZ_PROTOCOL_ID,
) -> CanonicalTrial:
    missing = sorted(field for field in STEINMETZ_REQUIRED_TRIAL_FIELDS if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Steinmetz trial fields: {joined}")

    left_contrast = source.get("visualStim_contrastLeft")
    right_contrast = source.get("visualStim_contrastRight")
    signed_contrast = signed_contrast_difference_percent(left_contrast, right_contrast)
    response_time = response_time_seconds(
        source.get("visualStim_times"),
        source.get("response_times"),
    )
    left_percent = contrast_percent(left_contrast)
    right_percent = contrast_percent(right_contrast)
    interval = _json_safe_value(source.get("intervals"))
    task_variables = {
        "left_contrast": left_percent,
        "right_contrast": right_percent,
        "signed_contrast_difference": signed_contrast,
        "source_choice_code": _json_safe_value(source.get("response_choice")),
        "source_feedback_type": _json_safe_value(source.get("feedbackType")),
        "visual_stim_time": _json_safe_value(source.get("visualStim_times")),
        "go_cue_time": _json_safe_value(source.get("goCue_times")),
        "feedback_time": _json_safe_value(source.get("feedback_times")),
        "included": _json_safe_value(source.get("included")),
        "rep_num": _json_safe_value(source.get("repNum")),
        "trial_interval": interval,
        "no_go_condition": _is_zero(left_contrast) and _is_zero(right_contrast),
        "bilateral_condition": _is_positive(left_contrast) and _is_positive(right_contrast),
    }

    return CanonicalTrial(
        protocol_id=protocol_id,
        dataset_id=dataset_id,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_contrast,
        stimulus_units="percent contrast difference, right minus left",
        stimulus_side=steinmetz_stimulus_side(left_contrast, right_contrast),
        evidence_strength=abs(signed_contrast) if signed_contrast is not None else None,
        evidence_units="percent contrast difference",
        choice=steinmetz_choice_label(source.get("response_choice")),
        correct=correct_label(source.get("feedbackType")),
        response_time=response_time,
        response_time_origin="response_times - visualStim_times",
        feedback=feedback_label(source.get("feedbackType")),
        task_variables={
            key: value for key, value in task_variables.items() if value is not None
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_steinmetz_visual_trials(
    trials: dict[str, Any],
    *,
    session_id: str,
    subject_id: str | None = None,
    dataset_id: str = STEINMETZ_DATASET_ID,
    protocol_id: str = STEINMETZ_PROTOCOL_ID,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    _validate_steinmetz_trials_object(trials)
    n_trials = len(trials["response_choice"])
    if limit is not None:
        n_trials = min(n_trials, limit)

    return [
        harmonize_steinmetz_visual_trial(
            _trial_source_row(trials, index),
            session_id=session_id,
            subject_id=subject_id,
            trial_index=index,
            dataset_id=dataset_id,
            protocol_id=protocol_id,
        )
        for index in range(n_trials)
    ]


def load_steinmetz_derived_sessions(
    derived_dir: Path = DEFAULT_STEINMETZ_DERIVED_DIR,
    *,
    session_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Load generated Steinmetz canonical trial CSVs for aggregate summaries."""

    if session_ids is None:
        candidate_dirs = sorted(path for path in derived_dir.iterdir() if path.is_dir())
        if len(candidate_dirs) > 1:
            candidate_dirs = [
                path for path in candidate_dirs if path.name != DEFAULT_STEINMETZ_SESSION_ID
            ]
    else:
        candidate_dirs = [derived_dir / session_id for session_id in session_ids]

    sessions: list[dict[str, Any]] = []
    for session_dir in candidate_dirs:
        if session_dir.name == "aggregate":
            continue
        trials_path = session_dir / "trials.csv"
        if not trials_path.exists():
            continue
        trials = _load_canonical_trials_csv(trials_path)
        if not trials:
            continue
        session_id = _single_value([trial.session_id for trial in trials]) or session_dir.name
        subject_id = _single_value([trial.subject_id for trial in trials])
        sessions.append(
            {
                "session_id": str(session_id),
                "subject_id": str(subject_id) if subject_id is not None else None,
                "trials_path": trials_path,
                "trials": trials,
            }
        )
    return sessions


def summarize_steinmetz_choice_by_signed_contrast(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[float | None, list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        grouped[trial.stimulus_value].append(trial)
    return [
        {"stimulus_value": stimulus_value, **_choice_summary_counts(group)}
        for stimulus_value, group in sorted(
            grouped.items(),
            key=lambda item: _none_safe_float(item[0]),
        )
    ]


def summarize_steinmetz_choice_by_contrast_pair(
    trials: list[CanonicalTrial],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[float | None, float | None], list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        grouped[
            (
                _task_float(trial, "left_contrast"),
                _task_float(trial, "right_contrast"),
            )
        ].append(trial)
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


def analyze_steinmetz_visual_decision(trials: list[CanonicalTrial]) -> dict[str, Any]:
    summary_rows = summarize_steinmetz_choice_by_signed_contrast(trials)
    condition_rows = summarize_steinmetz_choice_by_contrast_pair(trials)
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
    n_left = sum(1 for trial in trials if trial.choice == "left")
    n_right = sum(1 for trial in trials if trial.choice == "right")
    n_withhold = sum(1 for trial in trials if trial.choice == "withhold")
    n_unknown = sum(1 for trial in trials if trial.choice == "unknown")

    return {
        "analysis_id": "analysis.steinmetz-visual-decision.descriptive-choice-surface",
        "analysis_type": "descriptive_choice_surface",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": STEINMETZ_PROTOCOL_ID,
        "dataset_id": STEINMETZ_DATASET_ID,
        "report_title": "Steinmetz Visual Decision Report",
        "n_trials": len(trials),
        "n_response_trials": n_left + n_right,
        "n_choice_trials": n_left + n_right,
        "n_withhold_trials": n_withhold,
        "n_unknown_choice_trials": n_unknown,
        "n_no_response_trials": 0,
        "n_contrast_conditions": len(condition_rows),
        "response_time_origin": "response_times - visualStim_times",
        "stimulus_label": "Signed contrast difference",
        "stimulus_units": "percent contrast difference, right minus left",
        "summary_rows": summary_rows,
        "condition_rows": condition_rows,
        "choice_psychometric_fit": choice_fit,
        "caveats": [
            (
                "NoGo trials are represented as canonical withhold choices because they are "
                "valid behavioral outcomes in this task, not missing responses."
            ),
            (
                "The fitted binary psychometric summary excludes withhold choices and is "
                "therefore a convenience comparison to 2AFC slices, not a full multinomial "
                "model of the Steinmetz task."
            ),
            (
                "Signed contrast is right minus left; bilateral and blank conditions are "
                "kept explicit in condition_rows so operational stimulus variables are not "
                "collapsed into a prose-only interpretation."
            ),
        ],
    }


def analyze_steinmetz_session_aggregate(
    loaded_sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    all_trials: list[CanonicalTrial] = []
    session_rows: list[dict[str, Any]] = []
    subject_trials: dict[str, list[CanonicalTrial]] = defaultdict(list)
    subject_sessions: dict[str, set[str]] = defaultdict(set)
    annotated_trials: list[tuple[str, str, CanonicalTrial]] = []

    for loaded in sorted(loaded_sessions, key=lambda item: str(item.get("session_id") or "")):
        trials = list(loaded.get("trials") or [])
        if not trials:
            continue
        session_id = str(
            loaded.get("session_id")
            or _single_value([trial.session_id for trial in trials])
        )
        subject_id = str(
            loaded.get("subject_id")
            or _single_value([trial.subject_id for trial in trials])
            or "unknown-subject"
        )
        all_trials.extend(trials)
        subject_trials[subject_id].extend(trials)
        subject_sessions[subject_id].add(session_id)
        annotated_trials.extend((session_id, subject_id, trial) for trial in trials)
        session_rows.append(_aggregate_session_row(session_id, subject_id, trials))

    subject_rows = [
        _aggregate_subject_row(subject_id, sorted(subject_sessions[subject_id]), trials)
        for subject_id, trials in sorted(subject_trials.items())
    ]
    signed_contrast_rows = _aggregate_signed_contrast_rows(annotated_trials)
    n_left = sum(1 for trial in all_trials if trial.choice == "left")
    n_right = sum(1 for trial in all_trials if trial.choice == "right")
    n_withhold = sum(1 for trial in all_trials if trial.choice == "withhold")
    n_unknown = sum(1 for trial in all_trials if trial.choice == "unknown")
    return {
        "analysis_id": "analysis.steinmetz-visual-decision.session-aggregate",
        "analysis_type": "session_aggregate",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": STEINMETZ_PROTOCOL_ID,
        "dataset_id": STEINMETZ_DATASET_ID,
        "report_title": "Steinmetz Visual Decision Aggregate Report",
        "figshare_url": STEINMETZ_FIGSHARE_URL,
        "figshare_doi": STEINMETZ_SOURCE_DOI,
        "data_dictionary_url": STEINMETZ_WIKI_URL,
        "n_sessions": len(session_rows),
        "n_subjects": len(subject_rows),
        "n_trials": len(all_trials),
        "n_choice_trials": n_left + n_right,
        "n_left_trials": n_left,
        "n_right_trials": n_right,
        "n_withhold_trials": n_withhold,
        "n_unknown_choice_trials": n_unknown,
        "n_signed_contrast_levels": len(
            {trial.stimulus_value for trial in all_trials if trial.stimulus_value is not None}
        ),
        "n_contrast_conditions": len(
            {
                (_task_float(trial, "left_contrast"), _task_float(trial, "right_contrast"))
                for trial in all_trials
            }
        ),
        "input_sessions": [row["session_id"] for row in session_rows],
        "input_trial_csvs": [
            str(loaded.get("trials_path"))
            for loaded in sorted(
                loaded_sessions,
                key=lambda item: str(item.get("session_id") or ""),
            )
            if loaded.get("trials_path") is not None
        ],
        "session_rows": session_rows,
        "subject_rows": subject_rows,
        "signed_contrast_rows": signed_contrast_rows,
        "caveats": [
            (
                "This aggregate reads generated local canonical trial CSVs; it does not "
                "download the full Steinmetz Figshare archive."
            ),
            (
                "NoGo source responses are preserved as canonical withhold choices, so "
                "p(right) is movement-conditional while p(withhold) uses all trials."
            ),
            (
                "Session- and subject-balanced columns average already summarized bins "
                "and are descriptive replication summaries, not a multinomial task model."
            ),
        ],
    }


def write_steinmetz_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, STEINMETZ_CHOICE_SUMMARY_FIELDS)


def write_steinmetz_condition_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(path, rows, STEINMETZ_CONDITION_SUMMARY_FIELDS)


def write_steinmetz_choice_svg(path: Path, summary_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(steinmetz_choice_svg(summary_rows), encoding="utf-8")


def write_steinmetz_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    choice_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        steinmetz_report_html(
            analysis_result,
            provenance=provenance,
            choice_svg_text=choice_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def write_steinmetz_aggregate_outputs(
    out_dir: Path,
    analysis_result: dict[str, Any],
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "aggregate_result": out_dir / "aggregate_result.json",
        "session_summary": out_dir / "aggregate_session_summary.csv",
        "subject_summary": out_dir / "aggregate_subject_summary.csv",
        "signed_contrast_summary": out_dir / "aggregate_signed_contrast_summary.csv",
        "choice_svg": out_dir / "aggregate_choice_summary.svg",
        "report": out_dir / "report.html",
    }
    paths["aggregate_result"].write_text(
        json.dumps(analysis_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        paths["session_summary"],
        analysis_result["session_rows"],
        STEINMETZ_AGGREGATE_SESSION_FIELDS,
    )
    _write_csv(
        paths["subject_summary"],
        analysis_result["subject_rows"],
        STEINMETZ_AGGREGATE_SUBJECT_FIELDS,
    )
    _write_csv(
        paths["signed_contrast_summary"],
        analysis_result["signed_contrast_rows"],
        STEINMETZ_AGGREGATE_SIGNED_CONTRAST_FIELDS,
    )
    paths["choice_svg"].write_text(
        steinmetz_aggregate_choice_svg(analysis_result["signed_contrast_rows"]),
        encoding="utf-8",
    )
    paths["report"].write_text(
        steinmetz_aggregate_report_html(
            analysis_result,
            choice_svg_text=paths["choice_svg"].read_text(encoding="utf-8"),
            artifact_links={
                "Aggregate result JSON": "aggregate_result.json",
                "Session summary CSV": "aggregate_session_summary.csv",
                "Subject summary CSV": "aggregate_subject_summary.csv",
                "Signed contrast summary CSV": "aggregate_signed_contrast_summary.csv",
                "Aggregate choice SVG": "aggregate_choice_summary.svg",
            },
        ),
        encoding="utf-8",
    )
    return paths


def steinmetz_provenance_payload(
    *,
    session_dir: Path,
    session_id: str,
    details: dict[str, Any],
    trials: list[CanonicalTrial],
    output_files: dict[str, str],
    subject_id: str | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "subject_id": subject_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": STEINMETZ_PROTOCOL_ID,
        "dataset_id": STEINMETZ_DATASET_ID,
        "source": {
            "session_dir": str(session_dir),
            "figshare_url": details.get("figshare_url"),
            "figshare_doi": details.get("figshare_doi"),
            "data_dictionary_url": details.get("data_dictionary_url"),
            "source_files": details.get("source_files", {}),
            "source_fields": details.get("source_fields", []),
            "n_source_trials": details.get("n_trials"),
        },
        "source_fields": sorted(STEINMETZ_REQUIRED_TRIAL_FIELDS | STEINMETZ_OPTIONAL_TRIAL_FIELDS),
        "response_time_origin": "response_times - visualStim_times",
        "n_trials": len(trials),
        "exclusions": {
            "missing_stimulus": sum(1 for trial in trials if trial.stimulus_value is None),
            "withhold_choices": sum(1 for trial in trials if trial.choice == "withhold"),
            "unknown_choice": sum(1 for trial in trials if trial.choice == "unknown"),
            "missing_response_time": sum(1 for trial in trials if trial.response_time is None),
            "not_included_by_source": sum(
                1 for trial in trials if trial.task_variables.get("included") is False
            ),
        },
        "outputs": output_files,
        "caveats": [
            (
                "Raw Steinmetz source archives and generated derived artifacts stay under "
                "ignored local paths until release policy is settled."
            ),
            (
                "This adapter targets extracted ALF `.npy` session directories and does not "
                "download the multi-gigabyte Figshare archive automatically."
            ),
        ],
    }


def steinmetz_choice_svg(summary_rows: list[dict[str, Any]]) -> str:
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
            '<text x="20" y="60">No Steinmetz choice data available</text></svg>\n'
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
            radius = 3.0 + min(n_trials, 50) / 25.0
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


def steinmetz_aggregate_choice_svg(rows: list[dict[str, Any]]) -> str:
    width = 880
    height = 460
    left = 78
    right = 32
    top = 42
    bottom = 66
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [
        float(row["stimulus_value"])
        for row in rows
        if row.get("stimulus_value") is not None
    ]
    if not values:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No Steinmetz aggregate data available</text></svg>\n'
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
        f'<text x="{left}" y="24" font-family="sans-serif" font-size="16" '
        'font-weight="700">Steinmetz aggregate choice curves</text>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" '
        'stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 18}" text-anchor="middle" '
        'font-family="sans-serif" font-size="13">Signed contrast difference '
        "(%; right positive)</text>",
        f'<text x="20" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="13" transform="rotate(-90 20 '
        f'{top + plot_height / 2})">Probability</text>',
    ]
    for y_value in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = y_scale(y_value)
        elements.extend(
            [
                f'<line x1="{left - 4}" y1="{y:.1f}" x2="{left + plot_width}" '
                f'y2="{y:.1f}" stroke="#ddd"/>',
                f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                f'font-family="sans-serif" font-size="11">{y_value:.2g}</text>',
            ]
        )
    for x_value in _axis_tick_values(x_min, x_max):
        x = x_scale(x_value)
        elements.extend(
            [
                f'<line x1="{x:.1f}" y1="{top + plot_height}" x2="{x:.1f}" '
                f'y2="{top + plot_height + 4}" stroke="#222"/>',
                f'<text x="{x:.1f}" y="{top + plot_height + 20}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="10">{x_value:g}</text>',
            ]
        )

    series = [
        ("p_right", "P(right | movement), pooled", "#145f91"),
        ("p_withhold", "P(withhold), pooled", "#8a4b0f"),
        ("mean_subject_p_right", "P(right), subject-balanced", "#3b82f6"),
        ("mean_subject_p_withhold", "P(withhold), subject-balanced", "#d97706"),
    ]
    for index, (key, label, color) in enumerate(series):
        points = []
        for row in sorted(rows, key=lambda item: _none_safe_float(item["stimulus_value"])):
            stimulus_value = _finite_float(row.get("stimulus_value"))
            value = _finite_float(row.get(key))
            if stimulus_value is None or value is None:
                continue
            points.append((x_scale(stimulus_value), y_scale(value), int(row["n_trials"])))
        if not points:
            continue
        point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        dash = ' stroke-dasharray="5 4"' if key.startswith("mean_subject") else ""
        elements.append(
            f'<polyline points="{point_attr}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        for x, y, n_trials in points:
            radius = 2.5 + min(n_trials, 800) / 400.0
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" '
                'fill-opacity="0.75"/>'
            )
        legend_x = left + 15 + (index % 2) * 310
        legend_y = top + 18 + (index // 2) * 22
        elements.extend(
            [
                f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 24}" '
                f'y2="{legend_y}" stroke="{color}" stroke-width="2"{dash}/>',
                f'<text x="{legend_x + 32}" y="{legend_y + 4}" '
                f'font-family="sans-serif" font-size="12">{escape(label)}</text>',
            ]
        )
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def steinmetz_report_html(
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    choice_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    provenance = provenance or {}
    artifact_links = artifact_links or {}
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    title = str(analysis_result.get("report_title") or "Steinmetz Visual Decision Report")
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
        ("Contrast conditions", analysis_result.get("n_contrast_conditions")),
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
        "<p class=\"lede\">Adapter-backed visual contrast report for an extracted "
        "Steinmetz ALF session, keeping left, right, and NoGo choices distinct.</p>",
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
                    ("Subject", provenance.get("subject_id")),
                    ("Session directory", source.get("session_dir")),
                    ("Figshare DOI", source.get("figshare_doi")),
                    ("Field dictionary", source.get("data_dictionary_url")),
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


def steinmetz_aggregate_report_html(
    analysis_result: dict[str, Any],
    *,
    choice_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    artifact_links = artifact_links or {}
    title = str(
        analysis_result.get("report_title") or "Steinmetz Visual Decision Aggregate Report"
    )
    svg = choice_svg_text or steinmetz_aggregate_choice_svg(
        analysis_result.get("signed_contrast_rows", [])
        if isinstance(analysis_result.get("signed_contrast_rows"), list)
        else []
    )
    metrics = [
        ("Sessions", analysis_result.get("n_sessions")),
        ("Subjects", analysis_result.get("n_subjects")),
        ("Trials", analysis_result.get("n_trials")),
        ("Choice trials", analysis_result.get("n_choice_trials")),
        ("Withhold trials", analysis_result.get("n_withhold_trials")),
        ("Signed contrasts", analysis_result.get("n_signed_contrast_levels")),
        ("Contrast conditions", analysis_result.get("n_contrast_conditions")),
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
        "<p class=\"lede\">Across-session summary of extracted Steinmetz visual "
        "decision behavior, preserving valid NoGo/withhold choices while showing "
        "pooled, session-balanced, and subject-balanced contrast curves.</p>",
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
                    ("Dataset", analysis_result.get("dataset_id")),
                    ("Protocol", analysis_result.get("protocol_id")),
                    ("Figshare DOI", analysis_result.get("figshare_doi")),
                    ("Field dictionary", analysis_result.get("data_dictionary_url")),
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
                ]
            ),
            "</div>",
            "</section>",
            '<section class="figure-section">',
            "<h2>Aggregate Choice Summary</h2>",
            '<div class="figure-wrap">',
            svg,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Signed Contrast Summary</h2>",
            _html_table(
                analysis_result.get("signed_contrast_rows", []),
                [
                    ("stimulus_value", "Signed contrast"),
                    ("n_sessions", "Sessions"),
                    ("n_subjects", "Subjects"),
                    ("n_trials", "Trials"),
                    ("p_right", "P(right | movement)"),
                    ("p_withhold", "P(withhold)"),
                    ("mean_session_p_withhold", "Session mean P(withhold)"),
                    ("mean_subject_p_withhold", "Subject mean P(withhold)"),
                    ("p_correct", "P(correct)"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Subjects</h2>",
            _html_table(
                analysis_result.get("subject_rows", []),
                [
                    ("subject_id", "Subject"),
                    ("n_sessions", "Sessions"),
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
            "<h2>Sessions</h2>",
            _html_table(
                analysis_result.get("session_rows", []),
                [
                    ("session_id", "Session"),
                    ("subject_id", "Subject"),
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


def signed_contrast_difference_percent(contrast_left: Any, contrast_right: Any) -> float | None:
    left_value = _finite_float(contrast_left)
    right_value = _finite_float(contrast_right)
    if left_value is None and right_value is None:
        return None
    return ((right_value or 0.0) - (left_value or 0.0)) * 100.0


def contrast_percent(value: Any) -> float | None:
    numeric = _finite_float(value)
    if numeric is None:
        return None
    return numeric * 100.0


def steinmetz_stimulus_side(contrast_left: Any, contrast_right: Any) -> str:
    left_value = _finite_float(contrast_left)
    right_value = _finite_float(contrast_right)
    if left_value is None and right_value is None:
        return "unknown"
    diff = (right_value or 0.0) - (left_value or 0.0)
    if diff > 0.0:
        return "right"
    if diff < 0.0:
        return "left"
    if _is_zero(left_value) and _is_zero(right_value):
        return "none"
    return "unknown"


def steinmetz_choice_label(choice: Any) -> str:
    if choice == -1:
        return "right"
    if choice == 1:
        return "left"
    if choice == 0:
        return "withhold"
    return "unknown"


def correct_label(feedback_type: Any) -> bool | None:
    if feedback_type == 1:
        return True
    if feedback_type == -1:
        return False
    return None


def feedback_label(feedback_type: Any) -> str:
    if feedback_type == 1:
        return "reward"
    if feedback_type == -1:
        return "error"
    if feedback_type == 0:
        return "none"
    return "unknown"


def response_time_seconds(stim_on_time: Any, response_time: Any) -> float | None:
    stim_on = _finite_float(stim_on_time)
    response = _finite_float(response_time)
    if stim_on is None or response is None:
        return None
    return response - stim_on


def _find_steinmetz_file(session_dir: Path, filename: str) -> Path | None:
    direct = session_dir / filename
    if direct.exists():
        return direct
    matches = sorted(session_dir.rglob(filename))
    return matches[0] if matches else None


def _validate_steinmetz_trials_object(trials: dict[str, Any]) -> None:
    missing = sorted(field for field in STEINMETZ_REQUIRED_TRIAL_FIELDS if field not in trials)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Steinmetz trials fields: {joined}")
    n_trials = len(trials["response_choice"])
    for field, values in trials.items():
        if len(values) != n_trials:
            actual = len(values)
            raise ValueError(f"Field {field!r} has length {actual}, expected {n_trials}")


def _trial_source_row(trials: dict[str, Any], index: int) -> dict[str, Any]:
    return {field: _index_value(values, index) for field, values in trials.items()}


def _index_value(values: Any, index: int) -> Any:
    value = values[index]
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        if value.size == 1:
            item = value.reshape(-1)[0]
            return item.item() if hasattr(item, "item") else item
        return value.tolist()
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value.tolist()
    return value


def _choice_summary_counts(group: list[CanonicalTrial]) -> dict[str, Any]:
    n_left = sum(1 for trial in group if trial.choice == "left")
    n_right = sum(1 for trial in group if trial.choice == "right")
    n_withhold = sum(1 for trial in group if trial.choice == "withhold")
    n_unknown = sum(1 for trial in group if trial.choice == "unknown")
    n_choice = n_left + n_right
    correct_trials = [trial for trial in group if trial.correct is not None]
    n_correct = sum(1 for trial in correct_trials if trial.correct)
    response_times = [trial.response_time for trial in group if trial.response_time is not None]
    included_values = [
        trial.task_variables["included"]
        for trial in group
        if "included" in trial.task_variables
    ]
    return {
        "n_trials": len(group),
        "n_left": n_left,
        "n_right": n_right,
        "n_withhold": n_withhold,
        "n_unknown": n_unknown,
        "n_choice": n_choice,
        "p_left": _safe_ratio(n_left, n_choice),
        "p_right": _safe_ratio(n_right, n_choice),
        "p_withhold": _safe_ratio(n_withhold, len(group)),
        "n_correct": n_correct,
        "p_correct": _safe_ratio(n_correct, len(correct_trials)),
        "median_response_time": statistics.median(response_times) if response_times else None,
        "n_included": sum(1 for value in included_values if value is True)
        if included_values
        else None,
    }


def _choice_count(analysis_result: dict[str, Any], key: str) -> Any:
    summary_rows = analysis_result.get("summary_rows", [])
    if not isinstance(summary_rows, list):
        return None
    return sum(int(row.get(key, 0) or 0) for row in summary_rows if isinstance(row, dict))


def _aggregate_session_row(
    session_id: str,
    subject_id: str,
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "subject_id": subject_id,
        **_choice_summary_counts(trials),
        "n_signed_contrast_levels": len(
            {trial.stimulus_value for trial in trials if trial.stimulus_value is not None}
        ),
        "n_contrast_conditions": len(
            {
                (_task_float(trial, "left_contrast"), _task_float(trial, "right_contrast"))
                for trial in trials
            }
        ),
    }


def _aggregate_subject_row(
    subject_id: str,
    session_ids: list[str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    return {
        "subject_id": subject_id,
        "session_ids": ",".join(session_ids),
        "n_sessions": len(session_ids),
        **_choice_summary_counts(trials),
        "n_signed_contrast_levels": len(
            {trial.stimulus_value for trial in trials if trial.stimulus_value is not None}
        ),
        "n_contrast_conditions": len(
            {
                (_task_float(trial, "left_contrast"), _task_float(trial, "right_contrast"))
                for trial in trials
            }
        ),
    }


def _aggregate_signed_contrast_rows(
    annotated_trials: list[tuple[str, str, CanonicalTrial]],
) -> list[dict[str, Any]]:
    grouped: dict[float | None, list[tuple[str, str, CanonicalTrial]]] = defaultdict(list)
    session_bins: dict[tuple[float | None, str, str], list[CanonicalTrial]] = defaultdict(list)
    subject_bins: dict[tuple[float | None, str], list[CanonicalTrial]] = defaultdict(list)
    for session_id, subject_id, trial in annotated_trials:
        grouped[trial.stimulus_value].append((session_id, subject_id, trial))
        session_bins[(trial.stimulus_value, session_id, subject_id)].append(trial)
        subject_bins[(trial.stimulus_value, subject_id)].append(trial)

    rows: list[dict[str, Any]] = []
    for stimulus_value, group in sorted(
        grouped.items(),
        key=lambda item: _none_safe_float(item[0]),
    ):
        sessions = sorted({session_id for session_id, _, _ in group})
        subjects = sorted({subject_id for _, subject_id, _ in group})
        session_rows = [
            _choice_summary_counts(trials)
            for (value, _, _), trials in session_bins.items()
            if value == stimulus_value
        ]
        subject_rows = [
            _choice_summary_counts(trials)
            for (value, _), trials in subject_bins.items()
            if value == stimulus_value
        ]
        rows.append(
            {
                "stimulus_value": stimulus_value,
                "session_ids": ",".join(sessions),
                "subject_ids": ",".join(subjects),
                "n_sessions": len(sessions),
                "n_subjects": len(subjects),
                **_choice_summary_counts([trial for _, _, trial in group]),
                "mean_session_n_trials": _mean_values(
                    row.get("n_trials") for row in session_rows
                ),
                "mean_session_p_right": _mean_values(
                    row.get("p_right") for row in session_rows
                ),
                "sem_session_p_right": _sem_values(row.get("p_right") for row in session_rows),
                "mean_session_p_withhold": _mean_values(
                    row.get("p_withhold") for row in session_rows
                ),
                "sem_session_p_withhold": _sem_values(
                    row.get("p_withhold") for row in session_rows
                ),
                "mean_session_p_correct": _mean_values(
                    row.get("p_correct") for row in session_rows
                ),
                "sem_session_p_correct": _sem_values(
                    row.get("p_correct") for row in session_rows
                ),
                "mean_subject_n_trials": _mean_values(
                    row.get("n_trials") for row in subject_rows
                ),
                "mean_subject_p_right": _mean_values(
                    row.get("p_right") for row in subject_rows
                ),
                "sem_subject_p_right": _sem_values(row.get("p_right") for row in subject_rows),
                "mean_subject_p_withhold": _mean_values(
                    row.get("p_withhold") for row in subject_rows
                ),
                "sem_subject_p_withhold": _sem_values(
                    row.get("p_withhold") for row in subject_rows
                ),
                "mean_subject_p_correct": _mean_values(
                    row.get("p_correct") for row in subject_rows
                ),
                "sem_subject_p_correct": _sem_values(
                    row.get("p_correct") for row in subject_rows
                ),
            }
        )
    return rows


def _task_float(trial: CanonicalTrial, key: str) -> float | None:
    value = trial.task_variables.get(key)
    return float(value) if _finite_float(value) is not None else None


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _is_zero(value: Any) -> bool:
    numeric = _finite_float(value)
    return numeric is not None and abs(numeric) < 1e-12


def _is_positive(value: Any) -> bool:
    numeric = _finite_float(value)
    return numeric is not None and numeric > 0.0


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _none_safe_float(value: Any) -> float:
    numeric = _finite_float(value)
    return numeric if numeric is not None else float("inf")


def _single_value(values: list[Any]) -> Any:
    unique = sorted({value for value in values if value is not None})
    if len(unique) == 1:
        return unique[0]
    if not unique:
        return None
    return ",".join(str(value) for value in unique)


def _mean_values(values: Any) -> float | None:
    numeric_values = [
        numeric
        for value in values
        if (numeric := _finite_float(value)) is not None
    ]
    return statistics.mean(numeric_values) if numeric_values else None


def _sem_values(values: Any) -> float | None:
    numeric_values = [
        numeric
        for value in values
        if (numeric := _finite_float(value)) is not None
    ]
    if not numeric_values:
        return None
    if len(numeric_values) == 1:
        return 0.0
    return statistics.stdev(numeric_values) / math.sqrt(len(numeric_values))


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        return [_json_safe_value(item) for item in value.tolist()]
    if isinstance(value, list | tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, bool | int | str):
        return value
    numeric = _finite_float(value)
    if numeric is not None:
        return numeric
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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
    numeric = _finite_float(value)
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
  max-width: 760px;
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
