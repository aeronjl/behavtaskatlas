from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from behavtaskatlas.ibl import (
    current_git_commit,
    current_git_dirty,
    installed_package_version,
)
from behavtaskatlas.models import CanonicalTrial

RODGERS_PROTOCOL_ID = "protocol.mouse-whisker-object-recognition-lick"
RODGERS_DATASET_ID = "dataset.rodgers-whisker-object-recognition-dandi"
DEFAULT_RODGERS_SESSION_ID = "rodgers-whisker-object-recognition-dandi"
DEFAULT_RODGERS_RAW_FILE = Path(
    "data/raw/rodgers_whisker_object_recognition/rodgers_session.nwb"
)
DEFAULT_RODGERS_DERIVED_DIR = Path("derived/rodgers_whisker_object_recognition")
RODGERS_DANDI_URL = "https://dandiarchive.org/dandiset/000231/0.220904.1554"
RODGERS_DANDI_API_URL = (
    "https://api.dandiarchive.org/api/dandisets/000231/versions/0.220904.1554/"
)
RODGERS_DANDI_ASSETS_MANIFEST_URL = (
    "https://dandiarchive.s3.amazonaws.com/dandisets/000231/0.220904.1554/assets.yaml"
)
RODGERS_DANDI_DOI = "10.48324/dandi.000231/0.220904.1554"
RODGERS_PAPER_URL = "https://www.nature.com/articles/s41597-022-01728-1"
RODGERS_PAPER_DOI = "10.1038/s41597-022-01728-1"
RODGERS_COMPANION_CODE_URL = "https://github.com/cxrodgers/NwbDandiData2022"

RODGERS_SOURCE_FIELDS = [
    "start_time",
    "stop_time",
    "direct_delivery",
    "stim_is_random",
    "optogenetic",
    "outcome",
    "choice",
    "rewarded_side",
    "servo_position",
    "stimulus",
    "ignore_trial",
    "choice_time",
    "response_window_open_time",
    "trial",
]

RODGERS_TASK_RULE_FIELDS = [
    "task_rule",
    "n_trials",
    "n_analysis_trials",
    "n_ignored_trials",
    "n_left",
    "n_right",
    "n_no_response",
    "n_correct",
    "p_correct",
    "median_response_time",
    "mean_contacts_total",
]

RODGERS_CONDITION_FIELDS = [
    "task_rule",
    "stimulus",
    "servo_position",
    "n_trials",
    "n_analysis_trials",
    "n_ignored_trials",
    "n_left",
    "n_right",
    "n_no_response",
    "n_correct",
    "p_correct",
    "median_response_time",
    "mean_contacts_total",
]

RODGERS_DETECTION_FIELDS = [
    "task_rule",
    "n_signal_trials",
    "n_catch_trials",
    "n_hits",
    "n_misses",
    "n_false_alarms",
    "n_correct_rejects",
    "hit_rate",
    "false_alarm_rate",
    "p_correct",
]


def load_rodgers_whisker_source(
    source_file: Path = DEFAULT_RODGERS_RAW_FILE,
    *,
    session_id: str = DEFAULT_RODGERS_SESSION_ID,
    subject_id: str | None = None,
    task_rule: str | None = None,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    if source_file.suffix.lower() in {".csv", ".tsv"}:
        rows = load_rodgers_trial_rows_csv(source_file)
        source_kind = "trial_csv"
        nwb_meta: dict[str, Any] = {}
    elif source_file.suffix.lower() in {".nwb", ".h5", ".hdf5"}:
        rows, nwb_meta = read_rodgers_nwb_trials(source_file)
        source_kind = "nwb"
        subject_id = subject_id or _string_or_none(nwb_meta.get("subject_id"))
        session_id = _string_or_none(nwb_meta.get("session_id")) or session_id
    else:
        raise ValueError(
            f"Unsupported Rodgers source file type: {source_file.suffix}. "
            "Expected a CSV/TSV trial export or NWB/HDF5 session file."
        )

    selected_task_rule = normalize_task_rule(task_rule) if task_rule else infer_task_rule(rows)
    trials = harmonize_rodgers_whisker_rows(
        rows,
        base_session_id=session_id,
        subject_id=subject_id,
        task_rule=selected_task_rule,
        limit=limit,
    )
    details = {
        "source_file": str(source_file),
        "source_file_name": source_file.name,
        "source_file_sha256": file_sha256(source_file),
        "source_kind": source_kind,
        "n_source_rows": len(rows),
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "sessions": sorted({trial.session_id for trial in trials if trial.session_id}),
        "task_rules": sorted(
            {
                str(trial.task_variables.get("task_rule"))
                for trial in trials
                if trial.task_variables.get("task_rule")
            }
        ),
        "stimuli": sorted(
            {
                str(trial.task_variables.get("stimulus"))
                for trial in trials
                if trial.task_variables.get("stimulus")
            }
        ),
        "servo_positions": sorted(
            {
                str(trial.task_variables.get("servo_position"))
                for trial in trials
                if trial.task_variables.get("servo_position")
            }
        ),
        "dandi_url": RODGERS_DANDI_URL,
        "dandi_api_url": RODGERS_DANDI_API_URL,
        "dandi_doi": RODGERS_DANDI_DOI,
        "paper_url": RODGERS_PAPER_URL,
        "paper_doi": RODGERS_PAPER_DOI,
        "companion_code_url": RODGERS_COMPANION_CODE_URL,
    }
    details.update(nwb_meta)
    return trials, details


def load_rodgers_trial_rows_csv(path: Path) -> list[dict[str, Any]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter=delimiter)]


def read_rodgers_nwb_trials(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError(
            "Rodgers NWB ingestion requires h5py. Install it with "
            "`uv sync --extra nwb` or export the NWB trials table to CSV."
        ) from exc

    if not path.exists():
        raise FileNotFoundError(f"NWB file not found: {path}")

    meta: dict[str, Any] = {
        "nwb_file": str(path),
        "nwb_file_sha256": file_sha256(path),
        "nwb_file_bytes": path.stat().st_size,
    }
    with h5py.File(path, "r") as handle:
        rows = _nwb_trials_to_rows(handle)
        meta.update(_nwb_session_metadata(handle))
        contact_starts = _nwb_contact_starts_by_whisker(handle)
        if contact_starts:
            _attach_contact_counts(rows, contact_starts)
            meta["contact_whiskers"] = sorted(contact_starts)
            meta["n_contacts_total"] = sum(len(values) for values in contact_starts.values())
    return rows, meta


def harmonize_rodgers_whisker_rows(
    rows: list[dict[str, Any]],
    *,
    base_session_id: str = DEFAULT_RODGERS_SESSION_ID,
    subject_id: str | None = None,
    task_rule: str | None = None,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    selected_task_rule = normalize_task_rule(task_rule) if task_rule else infer_task_rule(rows)
    trials: list[CanonicalTrial] = []
    for index, row in enumerate(rows):
        trials.append(
            harmonize_rodgers_whisker_trial(
                row,
                base_session_id=base_session_id,
                subject_id=subject_id,
                task_rule=selected_task_rule,
                row_index=index,
            )
        )
        if limit is not None and len(trials) >= limit:
            break
    return trials


def harmonize_rodgers_whisker_trial(
    source: dict[str, Any],
    *,
    base_session_id: str,
    row_index: int,
    subject_id: str | None = None,
    task_rule: str = "unknown",
) -> CanonicalTrial:
    stimulus = normalize_stimulus(_row_alias(source, ["stimulus", "shape", "object"]))
    servo_position = normalize_servo_position(
        _row_alias(source, ["servo_position", "position", "object_position"])
    )
    choice = rodgers_choice_label(_row_alias(source, ["choice", "response", "lick_side"]))
    outcome = normalize_outcome(_row_alias(source, ["outcome", "trial_outcome"]))
    correct = rodgers_correct(outcome)
    rewarded_side = normalize_side(_row_alias(source, ["rewarded_side", "correct_side"]))
    response_window_open = _optional_float(
        _row_alias(
            source,
            [
                "response_window_open_time",
                "response_window_open",
                "response_window",
            ],
        )
    )
    choice_time = _optional_float(_row_alias(source, ["choice_time", "response_time"]))
    response_time = rodgers_response_latency(
        choice=choice,
        choice_time=choice_time,
        response_window_open_time=response_window_open,
    )
    source_trial_index = _optional_int(_row_alias(source, ["trial", "trial_index", "id"]))
    ignore_trial = rodgers_ignore_trial(source=source, outcome=outcome)
    direct_delivery = _optional_bool(_row_alias(source, ["direct_delivery"]))
    stim_is_random = _optional_bool(_row_alias(source, ["stim_is_random", "random_trial"]))
    optogenetic = _optional_bool(_row_alias(source, ["optogenetic", "laser", "opto"]))
    n_contacts_total = _optional_int(
        _row_alias(source, ["n_contacts_total", "n_contacts", "contact_count"])
    )
    task_variables = {
        "task_rule": task_rule,
        "stimulus": stimulus,
        "servo_position": servo_position,
        "source_outcome": outcome,
        "rewarded_side": rewarded_side,
        "ignore_trial": ignore_trial,
        "analysis_eligible": not ignore_trial and correct is not None,
        "direct_delivery": direct_delivery,
        "stim_is_random": stim_is_random,
        "optogenetic": optogenetic,
        "start_time": _optional_float(_row_alias(source, ["start_time"])),
        "stop_time": _optional_float(_row_alias(source, ["stop_time"])),
        "choice_time": choice_time,
        "response_window_open_time": response_window_open,
        "source_trial": source_trial_index,
        "n_contacts_total": n_contacts_total,
        "canonical_choice_convention": (
            "left/right are lick-pipe choices; nogo/spoil maps to no-response. "
            "The first lick after response_window_open_time determines outcome."
        ),
    }
    for whisker in ("C0", "C1", "C2", "C3"):
        value = _optional_int(
            _row_alias(
                source,
                [
                    f"n_contacts_{whisker}",
                    f"contacts_{whisker}",
                    f"n_contacts_whisker_{whisker}",
                ],
            )
        )
        if value is not None:
            task_variables[f"n_contacts_{whisker}"] = value

    return CanonicalTrial(
        protocol_id=RODGERS_PROTOCOL_ID,
        dataset_id=RODGERS_DATASET_ID,
        subject_id=subject_id or _string_or_none(_row_alias(source, ["subject_id", "subject"])),
        session_id=_string_or_none(_row_alias(source, ["session_id", "session"]))
        or base_session_id,
        trial_index=source_trial_index if source_trial_index is not None else row_index,
        stimulus_modality="somatosensory",
        stimulus_value=None,
        stimulus_units=None,
        stimulus_side="none",
        evidence_strength=None,
        evidence_units=None,
        choice=choice,
        correct=correct,
        response_time=response_time,
        response_time_origin="seconds after response_window_open_time"
        if response_time is not None
        else None,
        feedback=rodgers_feedback(correct=correct),
        reward=None,
        reward_units=None,
        block_id=None,
        prior_context=task_rule,
        training_stage=task_rule if task_rule != "unknown" else None,
        task_variables=task_variables,
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def infer_task_rule(rows: list[dict[str, Any]]) -> str:
    explicit_rules = [
        normalize_task_rule(_row_alias(row, ["task_rule", "task", "task_type"]))
        for row in rows
        if _row_alias(row, ["task_rule", "task", "task_type"]) is not None
    ]
    explicit_rules = [rule for rule in explicit_rules if rule != "unknown"]
    if explicit_rules and len(set(explicit_rules)) == 1:
        return explicit_rules[0]

    stimuli = {normalize_stimulus(_row_alias(row, ["stimulus", "shape", "object"])) for row in rows}
    rewarded_by_stimulus: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        stimulus = normalize_stimulus(_row_alias(row, ["stimulus", "shape", "object"]))
        rewarded_side = normalize_side(_row_alias(row, ["rewarded_side", "correct_side"]))
        if stimulus != "unknown" and rewarded_side != "unknown":
            rewarded_by_stimulus[stimulus].add(rewarded_side)

    if "nothing" in stimuli:
        return "shape_detection"
    if "right" in rewarded_by_stimulus.get("concave", set()):
        return "shape_detection"
    if (
        rewarded_by_stimulus.get("convex") == {"right"}
        and rewarded_by_stimulus.get("concave") == {"left"}
    ):
        return "shape_discrimination"
    return "unknown"


def analyze_rodgers_whisker_object_recognition(
    trials: list[CanonicalTrial],
    *,
    analysis_id: str = "analysis.rodgers-whisker-object-recognition.behavior",
) -> dict[str, Any]:
    outcome_counts = _count_task_variable(trials, "source_outcome")
    analysis_trials = [trial for trial in trials if _analysis_eligible(trial)]
    ignored_trials = [trial for trial in trials if trial.task_variables.get("ignore_trial") is True]
    task_rule_rows = rodgers_task_rule_summary_rows(trials)
    condition_rows = rodgers_condition_summary_rows(trials)
    detection_rows = rodgers_detection_summary_rows(trials)
    contact_trials = [
        trial
        for trial in trials
        if _optional_int(trial.task_variables.get("n_contacts_total")) is not None
    ]
    return {
        "analysis_id": analysis_id,
        "analysis_type": "tactile_object_recognition_summary",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": RODGERS_PROTOCOL_ID,
        "dataset_id": RODGERS_DATASET_ID,
        "report_title": "Rodgers Whisker Object Recognition Report",
        "n_trials": len(trials),
        "n_analysis_trials": len(analysis_trials),
        "n_ignored_trials": len(ignored_trials),
        "n_subjects": len({trial.subject_id for trial in trials if trial.subject_id}),
        "n_sessions": len({trial.session_id for trial in trials if trial.session_id}),
        "n_task_rules": len(
            {
                str(trial.task_variables.get("task_rule"))
                for trial in trials
                if trial.task_variables.get("task_rule")
            }
        ),
        "n_contact_annotated_trials": len(contact_trials),
        "outcome_counts": outcome_counts,
        "task_rule_rows": task_rule_rows,
        "condition_rows": condition_rows,
        "detection_rows": detection_rows,
        "caveats": [
            (
                "Rows with ignore_trial=true are retained in canonical trials and "
                "excluded from analysis-trial accuracy rates."
            ),
            (
                "Shape discrimination and shape detection are kept as explicit "
                "task_rule values because the same object shapes have different "
                "choice mappings across rules."
            ),
            (
                "Whisker contact counts are optional. The adapter records them when "
                "present in NWB contact intervals or CSV exports but does not require "
                "video-derived annotations for the base behavior slice."
            ),
        ],
    }


def rodgers_task_rule_summary_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[str, list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        grouped[str(trial.task_variables.get("task_rule") or "unknown")].append(trial)
    rows = []
    for task_rule, group in sorted(grouped.items()):
        rows.append({"task_rule": task_rule, **_rodgers_group_summary(group)})
    return rows


def rodgers_condition_summary_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        task_rule = str(trial.task_variables.get("task_rule") or "unknown")
        stimulus = str(trial.task_variables.get("stimulus") or "unknown")
        servo_position = str(trial.task_variables.get("servo_position") or "unknown")
        grouped[(task_rule, stimulus, servo_position)].append(trial)
    rows = []
    for (task_rule, stimulus, servo_position), group in sorted(grouped.items()):
        rows.append(
            {
                "task_rule": task_rule,
                "stimulus": stimulus,
                "servo_position": servo_position,
                **_rodgers_group_summary(group),
            }
        )
    return rows


def rodgers_detection_summary_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    rows = []
    grouped: dict[str, list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        task_rule = str(trial.task_variables.get("task_rule") or "unknown")
        if task_rule == "shape_detection":
            grouped[task_rule].append(trial)
    for task_rule, group in sorted(grouped.items()):
        valid = [trial for trial in group if _analysis_eligible(trial)]
        signal = [
            trial
            for trial in valid
            if str(trial.task_variables.get("stimulus") or "unknown") != "nothing"
        ]
        catch = [
            trial
            for trial in valid
            if str(trial.task_variables.get("stimulus") or "unknown") == "nothing"
        ]
        hits = sum(1 for trial in signal if trial.choice == "right")
        misses = sum(1 for trial in signal if trial.choice == "left")
        false_alarms = sum(1 for trial in catch if trial.choice == "right")
        correct_rejects = sum(1 for trial in catch if trial.choice == "left")
        correct = sum(1 for trial in valid if trial.correct is True)
        rows.append(
            {
                "task_rule": task_rule,
                "n_signal_trials": len(signal),
                "n_catch_trials": len(catch),
                "n_hits": hits,
                "n_misses": misses,
                "n_false_alarms": false_alarms,
                "n_correct_rejects": correct_rejects,
                "hit_rate": _safe_ratio(hits, len(signal)),
                "false_alarm_rate": _safe_ratio(false_alarms, len(catch)),
                "p_correct": _safe_ratio(correct, len(valid)),
            }
        )
    return rows


def write_rodgers_task_rule_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_dict_rows(path, rows, RODGERS_TASK_RULE_FIELDS)


def write_rodgers_condition_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_dict_rows(path, rows, RODGERS_CONDITION_FIELDS)


def write_rodgers_detection_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_dict_rows(path, rows, RODGERS_DETECTION_FIELDS)


def write_rodgers_accuracy_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rodgers_accuracy_svg(rows) + "\n", encoding="utf-8")


def rodgers_accuracy_svg(rows: list[dict[str, Any]]) -> str:
    plotted = [row for row in rows if row.get("p_correct") is not None]
    width = 720
    height = 360
    margin_left = 70
    margin_right = 24
    margin_top = 44
    margin_bottom = 92
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    bar_gap = 6
    n = max(1, len(plotted))
    bar_w = max(8, (plot_w - bar_gap * (n - 1)) / n)
    bars = []
    labels = []
    for index, row in enumerate(plotted):
        p_correct = float(row["p_correct"])
        bar_h = max(0.0, min(1.0, p_correct)) * plot_h
        x = margin_left + index * (bar_w + bar_gap)
        y = margin_top + plot_h - bar_h
        task_rule = str(row.get("task_rule") or "unknown")
        stimulus = str(row.get("stimulus") or "unknown")
        position = str(row.get("servo_position") or "unknown")
        fill = "#4f7d70" if task_rule == "shape_discrimination" else "#8c5f8d"
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" '
            f'height="{bar_h:.2f}" fill="{fill}" />'
        )
        label = escape(f"{stimulus}/{position}")
        labels.append(
            f'<text x="{x + bar_w / 2:.2f}" y="{margin_top + plot_h + 14}" '
            f'text-anchor="end" font-size="9" fill="#333" '
            f'transform="rotate(-40 {x + bar_w / 2:.2f} {margin_top + plot_h + 14})">'
            f"{label}</text>"
        )
    y_ticks = []
    for value in (0.0, 0.5, 1.0):
        y = margin_top + plot_h - value * plot_h
        y_ticks.append(
            f'<line x1="{margin_left - 4}" y1="{y:.2f}" '
            f'x2="{margin_left + plot_w}" y2="{y:.2f}" stroke="#ddd" />'
            f'<text x="{margin_left - 8}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-size="10" fill="#333">{value:.1f}</text>'
        )
    if not plotted:
        bars.append(
            f'<text x="{width / 2:.2f}" y="{height / 2:.2f}" text-anchor="middle" '
            'font-size="13" fill="#555">No accuracy rows available</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" fill="white" />'
        f'<text x="{width / 2}" y="24" text-anchor="middle" font-size="15" fill="#111">'
        "Accuracy by stimulus and object position</text>"
        + "".join(y_ticks)
        + f'<line x1="{margin_left}" y1="{margin_top}" '
        f'x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#333" />'
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" '
        f'x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#333" />'
        + "".join(bars)
        + "".join(labels)
        + f'<text x="22" y="{margin_top + plot_h / 2}" text-anchor="middle" '
        f'font-size="11" fill="#333" transform="rotate(-90 22 {margin_top + plot_h / 2})">'
        "proportion correct</text>"
        "</svg>"
    )


def write_rodgers_report_html(
    path: Path,
    analysis: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    accuracy_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    title = str(analysis.get("report_title") or "Rodgers Whisker Object Recognition Report")
    body = [
        f"<h1>{escape(title)}</h1>",
        (
            "<p>Single-session or exported-session summary for the Rodgers DANDI "
            "mouse whisker object-recognition dataset. The adapter preserves the "
            "source task rule, shape stimulus, object position, lick choice, "
            "rewarded side, ignore-trial flag, and response-window timing.</p>"
        ),
        "<h2>Overview</h2>",
        _html_definition_list(
            [
                ("Trials", analysis.get("n_trials")),
                ("Analysis trials", analysis.get("n_analysis_trials")),
                ("Ignored trials", analysis.get("n_ignored_trials")),
                ("Subjects", analysis.get("n_subjects")),
                ("Sessions", analysis.get("n_sessions")),
                ("Task rules", analysis.get("n_task_rules")),
                ("Contact-annotated trials", analysis.get("n_contact_annotated_trials")),
            ]
        ),
        "<h2>Task Rules</h2>",
        _html_table(
            analysis.get("task_rule_rows", []),
            [
                ("task_rule", "Task rule"),
                ("n_analysis_trials", "Analysis trials"),
                ("n_ignored_trials", "Ignored"),
                ("n_correct", "Correct"),
                ("p_correct", "p(correct)"),
                ("median_response_time", "Median RT (s)"),
                ("mean_contacts_total", "Mean contacts"),
            ],
        ),
        "<h2>Conditions</h2>",
        _html_table(
            analysis.get("condition_rows", []),
            [
                ("task_rule", "Task rule"),
                ("stimulus", "Stimulus"),
                ("servo_position", "Position"),
                ("n_analysis_trials", "Analysis trials"),
                ("n_correct", "Correct"),
                ("p_correct", "p(correct)"),
                ("median_response_time", "Median RT (s)"),
                ("mean_contacts_total", "Mean contacts"),
            ],
        ),
    ]
    if analysis.get("detection_rows"):
        body.extend(
            [
                "<h2>Detection Summary</h2>",
                _html_table(
                    analysis["detection_rows"],
                    [
                        ("n_signal_trials", "Signal trials"),
                        ("n_catch_trials", "Catch trials"),
                        ("n_hits", "Hits"),
                        ("n_false_alarms", "False alarms"),
                        ("hit_rate", "Hit rate"),
                        ("false_alarm_rate", "False-alarm rate"),
                        ("p_correct", "p(correct)"),
                    ],
                ),
            ]
        )
    if accuracy_svg_text:
        body.extend(["<h2>Accuracy Plot</h2>", accuracy_svg_text])
    if analysis.get("caveats"):
        body.append("<h2>Caveats</h2>")
        body.append(
            "<ul>"
            + "".join(f"<li>{escape(str(item))}</li>" for item in analysis["caveats"])
            + "</ul>"
        )
    if provenance:
        source = provenance.get("source", {})
        body.extend(
            [
                "<h2>Provenance</h2>",
                _html_definition_list(
                    [
                        ("DANDI DOI", source.get("dandi_doi")),
                        ("Source file", source.get("source_file")),
                        ("Source SHA256", source.get("source_file_sha256")),
                        ("h5py version", provenance.get("h5py_version")),
                        ("behavtaskatlas commit", provenance.get("behavtaskatlas_commit")),
                        ("Working tree dirty", provenance.get("behavtaskatlas_git_dirty")),
                        ("Generated", provenance.get("generated_at")),
                    ]
                ),
            ]
        )
    if artifact_links:
        body.append("<h2>Artifacts</h2>")
        body.append(
            "<ul>"
            + "".join(
                f'<li><a href="{escape(href)}">{escape(label)}</a></li>'
                for label, href in artifact_links.items()
            )
            + "</ul>"
        )
    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{escape(title)}</title><style>{_report_css()}</style></head><body>"
        + "".join(body)
        + "</body></html>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html + "\n", encoding="utf-8")


def rodgers_provenance_payload(
    *,
    details: dict[str, Any],
    trials: list[CanonicalTrial],
    output_files: dict[str, str],
) -> dict[str, Any]:
    return {
        "protocol_id": RODGERS_PROTOCOL_ID,
        "dataset_id": RODGERS_DATASET_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "h5py_version": installed_package_version("h5py"),
        "source": {
            "dandi_url": RODGERS_DANDI_URL,
            "dandi_api_url": RODGERS_DANDI_API_URL,
            "dandi_assets_manifest_url": RODGERS_DANDI_ASSETS_MANIFEST_URL,
            "dandi_doi": RODGERS_DANDI_DOI,
            "paper_url": RODGERS_PAPER_URL,
            "paper_doi": RODGERS_PAPER_DOI,
            "companion_code_url": RODGERS_COMPANION_CODE_URL,
            "source_file": details.get("source_file"),
            "source_file_name": details.get("source_file_name"),
            "source_file_sha256": details.get("source_file_sha256"),
            "source_kind": details.get("source_kind"),
            "n_source_rows": details.get("n_source_rows"),
            "n_trials": details.get("n_trials"),
            "subjects": details.get("subjects"),
            "sessions": details.get("sessions"),
            "task_rules": details.get("task_rules"),
            "stimuli": details.get("stimuli"),
            "servo_positions": details.get("servo_positions"),
            "nwb_file_bytes": details.get("nwb_file_bytes"),
            "contact_whiskers": details.get("contact_whiskers"),
            "n_contacts_total": details.get("n_contacts_total"),
        },
        "source_fields": RODGERS_SOURCE_FIELDS,
        "output_files": output_files,
        "n_trials": len(trials),
        "n_analysis_trials": sum(1 for trial in trials if _analysis_eligible(trial)),
        "outcome_counts": _count_task_variable(trials, "source_outcome"),
        "task_rule_counts": _count_task_variable(trials, "task_rule"),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rodgers_choice_label(value: Any) -> str:
    label = _normalized_label(value)
    if label in {"left", "l"}:
        return "left"
    if label in {"right", "r"}:
        return "right"
    if label in {"nogo", "no_go", "no-go", "spoil", "none", "no_response", "no-response"}:
        return "no-response"
    return "unknown"


def rodgers_correct(outcome: str) -> bool | None:
    if outcome == "correct":
        return True
    if outcome == "error":
        return False
    return None


def rodgers_feedback(*, correct: bool | None) -> str:
    if correct is True:
        return "reward"
    if correct is False:
        return "error"
    return "none"


def rodgers_ignore_trial(*, source: dict[str, Any], outcome: str) -> bool:
    explicit = _optional_bool(_row_alias(source, ["ignore_trial", "ignored"]))
    if explicit is not None:
        return explicit
    if outcome == "spoil":
        return True
    direct_delivery = _optional_bool(_row_alias(source, ["direct_delivery"]))
    if direct_delivery is True:
        return True
    stim_is_random = _optional_bool(_row_alias(source, ["stim_is_random", "random_trial"]))
    if stim_is_random is False:
        return True
    optogenetic = _optional_bool(_row_alias(source, ["optogenetic", "laser", "opto"]))
    if optogenetic is True:
        return True
    return False


def rodgers_response_latency(
    *,
    choice: str,
    choice_time: float | None,
    response_window_open_time: float | None,
) -> float | None:
    if choice not in {"left", "right"}:
        return None
    if choice_time is None or response_window_open_time is None:
        return None
    latency = choice_time - response_window_open_time
    if not math.isfinite(latency) or latency < 0:
        return None
    return latency


def normalize_task_rule(value: Any) -> str:
    label = _normalized_label(value)
    if label in {"shape_detection", "detection", "detect"}:
        return "shape_detection"
    if label in {"shape_discrimination", "discrimination", "shape_discrim", "discrim"}:
        return "shape_discrimination"
    return "unknown"


def normalize_stimulus(value: Any) -> str:
    label = _normalized_label(value)
    if label in {"convex", "concave", "nothing"}:
        return label
    if label in {"catch", "none", "no_object", "no-object"}:
        return "nothing"
    return label or "unknown"


def normalize_servo_position(value: Any) -> str:
    label = _normalized_label(value)
    if label in {"close", "medium", "far"}:
        return label
    return label or "unknown"


def normalize_outcome(value: Any) -> str:
    label = _normalized_label(value)
    if label in {"correct", "error", "spoil"}:
        return label
    if label in {"incorrect", "wrong"}:
        return "error"
    if label in {"no_response", "no-response", "nogo", "no_go"}:
        return "spoil"
    return label or "unknown"


def normalize_side(value: Any) -> str:
    label = _normalized_label(value)
    if label in {"left", "right"}:
        return label
    if label in {"l"}:
        return "left"
    if label in {"r"}:
        return "right"
    return label or "unknown"


def _rodgers_group_summary(group: list[CanonicalTrial]) -> dict[str, Any]:
    analysis_trials = [trial for trial in group if _analysis_eligible(trial)]
    ignored_trials = [trial for trial in group if trial.task_variables.get("ignore_trial") is True]
    n_left = sum(1 for trial in analysis_trials if trial.choice == "left")
    n_right = sum(1 for trial in analysis_trials if trial.choice == "right")
    n_no_response = sum(1 for trial in analysis_trials if trial.choice == "no-response")
    n_correct = sum(1 for trial in analysis_trials if trial.correct is True)
    response_times = [
        trial.response_time
        for trial in analysis_trials
        if trial.response_time is not None and math.isfinite(trial.response_time)
    ]
    contact_counts = [
        value
        for trial in analysis_trials
        if (value := _optional_int(trial.task_variables.get("n_contacts_total"))) is not None
    ]
    return {
        "n_trials": len(group),
        "n_analysis_trials": len(analysis_trials),
        "n_ignored_trials": len(ignored_trials),
        "n_left": n_left,
        "n_right": n_right,
        "n_no_response": n_no_response,
        "n_correct": n_correct,
        "p_correct": _safe_ratio(n_correct, len(analysis_trials)),
        "median_response_time": statistics.median(response_times) if response_times else None,
        "mean_contacts_total": statistics.fmean(contact_counts) if contact_counts else None,
    }


def _analysis_eligible(trial: CanonicalTrial) -> bool:
    return trial.task_variables.get("analysis_eligible") is True


def _count_task_variable(trials: list[CanonicalTrial], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for trial in trials:
        counts[str(trial.task_variables.get(key) or "unknown")] += 1
    return dict(sorted(counts.items()))


def _write_dict_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _nwb_trials_to_rows(handle: Any) -> list[dict[str, Any]]:
    trials = None
    for path in ("intervals/trials", "trials"):
        if path in handle:
            trials = handle[path]
            break
    if trials is None:
        raise ValueError("Could not find an NWB trials table at /intervals/trials")
    if "start_time" not in trials:
        raise ValueError("NWB trials table is missing required start_time column")

    n_trials = len(trials["start_time"])
    columns: dict[str, list[Any]] = {}
    for name, node in trials.items():
        if not hasattr(node, "shape") or len(getattr(node, "shape", ())) == 0:
            continue
        if node.shape[0] != n_trials:
            continue
        columns[name] = [_decode_h5_value(value) for value in _h5_dataset_values(node)]

    rows: list[dict[str, Any]] = []
    for index in range(n_trials):
        row = {name: values[index] for name, values in columns.items()}
        if "id" in row and "trial" not in row:
            row["trial"] = row["id"]
        rows.append(row)
    return rows


def _nwb_session_metadata(handle: Any) -> dict[str, Any]:
    return {
        "subject_id": _read_h5_scalar(handle, "general/subject/subject_id"),
        "session_id": _read_h5_scalar(handle, "session_id"),
        "session_description": _read_h5_scalar(handle, "session_description"),
        "identifier": _read_h5_scalar(handle, "identifier"),
        "session_start_time": _read_h5_scalar(handle, "session_start_time"),
    }


def _nwb_contact_starts_by_whisker(handle: Any) -> dict[str, list[float]]:
    candidates = []
    for module_path in ("processing/identified_whisker_contacts", "processing/behavior"):
        if module_path in handle:
            candidates.extend(_contact_table_candidates(handle[module_path]))
    contact_starts: dict[str, list[float]] = {}
    for name, group in candidates:
        if "start_time" not in group:
            continue
        starts = [
            value
            for raw in _h5_dataset_values(group["start_time"])
            if (value := _optional_float(_decode_h5_value(raw))) is not None
        ]
        if starts:
            contact_starts[_whisker_label(name)] = sorted(starts)
    return contact_starts


def _contact_table_candidates(group: Any) -> list[tuple[str, Any]]:
    candidates = []
    for name, child in group.items():
        if hasattr(child, "items"):
            if "start_time" in child and (
                "contact" in name.lower() or "whisker" in name.lower()
            ):
                candidates.append((name, child))
            candidates.extend(_contact_table_candidates(child))
    return candidates


def _attach_contact_counts(
    rows: list[dict[str, Any]], contact_starts: dict[str, list[float]]
) -> None:
    for row in rows:
        start = _optional_float(row.get("start_time"))
        stop = _optional_float(row.get("choice_time")) or _optional_float(row.get("stop_time"))
        if start is None or stop is None:
            continue
        total = 0
        for whisker, starts in contact_starts.items():
            left = bisect.bisect_left(starts, start)
            right = bisect.bisect_right(starts, stop)
            count = max(0, right - left)
            row[f"n_contacts_{whisker}"] = count
            total += count
        row["n_contacts_total"] = total


def _whisker_label(name: str) -> str:
    lowered = name.lower()
    for label in ("c0", "c1", "c2", "c3"):
        if label in lowered:
            return label.upper()
    return name


def _h5_dataset_values(node: Any) -> list[Any]:
    try:
        values = node.asstr()[()]
    except (AttributeError, TypeError, ValueError):
        values = node[()]
    if hasattr(values, "tolist"):
        values = values.tolist()
    if isinstance(values, list):
        return values
    return [values]


def _read_h5_scalar(handle: Any, path: str) -> Any:
    if path not in handle:
        return None
    value = handle[path][()]
    return _decode_h5_value(value)


def _decode_h5_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "item"):
        try:
            return _decode_h5_value(value.item())
        except (TypeError, ValueError):
            pass
    return value


def _row_alias(source: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in source:
            return source[name]
    lowered = {key.lower(): key for key in source}
    for name in names:
        key = lowered.get(name.lower())
        if key is not None:
            return source[key]
    return None


def _normalized_label(value: Any) -> str:
    text = _string_or_none(value)
    if text is None:
        return ""
    return text.strip().lower().replace(" ", "_")


def _string_or_none(value: Any) -> str | None:
    value = _decode_h5_value(value)
    if value is None:
        return None
    if isinstance(value, float) and (not math.isfinite(value)):
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _optional_float(value: Any) -> float | None:
    value = _decode_h5_value(value)
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_int(value: Any) -> int | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _optional_bool(value: Any) -> bool | None:
    value = _decode_h5_value(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and math.isfinite(float(value)):
        return bool(int(value))
    text = _string_or_none(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"true", "t", "1", "yes", "y"}:
        return True
    if lowered in {"false", "f", "0", "no", "n"}:
        return False
    return None


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _json_safe_value(value: Any) -> Any:
    value = _decode_h5_value(value)
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


def _html_definition_list(rows: list[tuple[str, Any]]) -> str:
    parts = ["<dl>"]
    for label, value in rows:
        parts.append(f"<dt>{escape(str(label))}</dt><dd>{escape(_format_value(value))}</dd>")
    parts.append("</dl>")
    return "".join(parts)


def _html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "<p>No rows available.</p>"
    head = "<tr>" + "".join(f"<th>{escape(label)}</th>" for _, label in columns) + "</tr>"
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(
                f"<td>{escape(_format_value(row.get(key)))}</td>"
                for key, _label in columns
            )
            + "</tr>"
        )
    return "<table><thead>" + head + "</thead><tbody>" + "".join(body) + "</tbody></table>"


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _report_css() -> str:
    return """
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin: 2rem;
  color: #1f2933;
  line-height: 1.45;
}
h1, h2 { color: #102a43; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.92rem; }
th, td { border: 1px solid #d9e2ec; padding: 0.45rem 0.55rem; text-align: left; }
th { background: #f0f4f8; }
dt { font-weight: 700; float: left; clear: left; width: 14rem; }
dd { margin-left: 15rem; margin-bottom: 0.35rem; }
svg { max-width: 100%; height: auto; border: 1px solid #d9e2ec; }
""".strip()
