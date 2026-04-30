from __future__ import annotations

import csv
import hashlib
import math
import statistics
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

ODOEMENE_PROTOCOL_ID = "protocol.mouse-visual-flash-rate-accumulation"
ODOEMENE_DATASET_ID = "dataset.odoemene-visual-evidence-accumulation-cshl"
DEFAULT_ODOEMENE_SESSION_ID = "odoemene-visual-evidence-cshl"
DEFAULT_ODOEMENE_RAW_MAT = Path("data/raw/odoemene_visual_accumulation/Odoemene2020.mat")
DEFAULT_ODOEMENE_DERIVED_DIR = Path("derived/odoemene_visual_accumulation")
ODOEMENE_REPOSITORY_URL = "https://repository.cshl.edu/id/eprint/38944/"
ODOEMENE_DATASET_DOI = "10.14224/1.38944"
ODOEMENE_STORAGE_URL = "http://labshare.cshl.edu/shares/library/repository/38944/"
ODOEMENE_METADATA_PDF_URL = "https://repository.cshl.edu/38944/3/DataDescription_Odeomene2020.pdf"
ODOEMENE_CATEGORY_BOUNDARY_HZ = 12.0
ODOEMENE_EVENT_BIN_SECONDS = 0.04
ODOEMENE_N_EVENT_BINS = 25

ODOEMENE_RAW_FIELDS = [
    "stimEventList",
    "stimRate",
    "subjectResponse",
    "correctResponse",
    "validTrial",
    "success",
    "waitTime",
    "moveTime",
    "sessionID",
]

ODOEMENE_KERNEL_FIELDS = [
    "bin_index",
    "bin_start",
    "bin_end",
    "n_trials",
    "n_high_choice",
    "n_low_choice",
    "mean_event",
    "mean_event_high_choice",
    "mean_event_low_choice",
    "choice_difference",
    "point_biserial_r",
    "normalized_weight",
]


def load_odoemene_visual_accumulation_mat(
    mat_file: Path = DEFAULT_ODOEMENE_RAW_MAT,
    *,
    session_id: str = DEFAULT_ODOEMENE_SESSION_ID,
    limit: int | None = None,
    max_subjects: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    try:
        import scipy.io
    except ImportError as exc:
        raise RuntimeError(
            "Odoemene visual accumulation ingestion requires scipy. "
            "Install it with `uv sync --extra visual`."
        ) from exc

    loaded = scipy.io.loadmat(mat_file, squeeze_me=True, simplify_cells=True)
    subject_records, matlab_variable = _odoemene_subject_records(loaded)
    if max_subjects is not None:
        subject_records = subject_records[:max_subjects]

    trials = harmonize_odoemene_subjects(
        subject_records,
        base_session_id=session_id,
        limit=limit,
    )
    details = {
        "source_file": str(mat_file),
        "source_file_name": mat_file.name,
        "source_file_sha256": file_sha256(mat_file),
        "source_url": ODOEMENE_REPOSITORY_URL,
        "dataset_doi": ODOEMENE_DATASET_DOI,
        "storage_url": ODOEMENE_STORAGE_URL,
        "metadata_pdf_url": ODOEMENE_METADATA_PDF_URL,
        "matlab_variable": matlab_variable,
        "n_subjects_source": len(subject_records),
        "n_trials": len(trials),
        "subjects": sorted({trial.subject_id for trial in trials if trial.subject_id}),
        "source_sessions": sorted({trial.block_id for trial in trials if trial.block_id}),
        "stimulus_rates": sorted(
            {
                trial.task_variables["stim_rate"]
                for trial in trials
                if "stim_rate" in trial.task_variables
            }
        ),
    }
    return trials, details


def harmonize_odoemene_subjects(
    subject_records: list[dict[str, Any]],
    *,
    base_session_id: str = DEFAULT_ODOEMENE_SESSION_ID,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    trials: list[CanonicalTrial] = []
    for subject_index, subject in enumerate(subject_records):
        for trial in harmonize_odoemene_subject_trials(
            subject,
            subject_index=subject_index,
            base_session_id=base_session_id,
        ):
            trials.append(trial)
            if limit is not None and len(trials) >= limit:
                return trials
    return trials


def harmonize_odoemene_subject_trials(
    subject_record: dict[str, Any],
    *,
    subject_index: int = 0,
    base_session_id: str = DEFAULT_ODOEMENE_SESSION_ID,
) -> list[CanonicalTrial]:
    raw = _subject_raw_choice_data(subject_record)
    n_trials = _validate_raw_choice_data(raw)
    subject_id = _subject_id(subject_record, subject_index)
    species = _optional_text(_field_alias(subject_record, ["species"]))
    contingency = _optional_text(
        _field_alias(
            subject_record,
            [
                "trainingContingency",
                "training_contingency",
                "contingency",
                "trainContingency",
            ],
        )
    )
    num_sessions = _optional_int(_field_alias(raw, ["numSessions", "num_sessions"]))

    return [
        harmonize_odoemene_trial(
            _raw_choice_row(raw, index),
            subject_id=subject_id,
            subject_index=subject_index,
            species=species,
            training_contingency=contingency,
            num_sessions=num_sessions,
            base_session_id=base_session_id,
            trial_index=index,
        )
        for index in range(n_trials)
    ]


def harmonize_odoemene_trial(
    source: dict[str, Any],
    *,
    subject_id: str,
    subject_index: int,
    species: str | None,
    training_contingency: str | None,
    num_sessions: int | None,
    base_session_id: str,
    trial_index: int,
) -> CanonicalTrial:
    missing = sorted(field for field in ODOEMENE_RAW_FIELDS if field not in source)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Odoemene raw choice fields: {joined}")

    stim_rate = _required_float(source["stimRate"], field="stimRate")
    signed_rate = stim_rate - ODOEMENE_CATEGORY_BOUNDARY_HZ
    valid_trial = _required_bool(source["validTrial"], field="validTrial")
    subject_response = _optional_int(source["subjectResponse"])
    correct_response = _optional_int(source["correctResponse"])
    success = _optional_bool(source["success"])
    source_session = _optional_text(source["sessionID"]) or "unknown"
    event_bins = _event_bin_list(source["stimEventList"])
    move_time = _optional_float(source["moveTime"])
    wait_time = _optional_float(source["waitTime"])

    choice = _category_choice_label(subject_response) if valid_trial else "no-response"
    correct = success if valid_trial else None
    response_time = move_time if valid_trial else None
    feedback = "none"
    if valid_trial and success is True:
        feedback = "reward"
    elif valid_trial and success is False:
        feedback = "error"

    session_id = f"{base_session_id}.{subject_id}.session-{_session_token(source_session)}"
    prior_context = (
        f"contingency={training_contingency}" if training_contingency else None
    )
    return CanonicalTrial(
        protocol_id=ODOEMENE_PROTOCOL_ID,
        dataset_id=ODOEMENE_DATASET_ID,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=signed_rate,
        stimulus_units="flashes per second minus 12 Hz category boundary",
        stimulus_side=_category_side(correct_response),
        evidence_strength=abs(signed_rate),
        evidence_units="absolute distance from 12 Hz category boundary",
        choice=choice,
        correct=correct,
        response_time=response_time,
        response_time_origin="moveTime: center-port withdrawal to side-port response",
        feedback=feedback,
        block_id=f"{subject_id}:session-{source_session}",
        prior_context=prior_context,
        task_variables={
            "subject_index": subject_index,
            "species": species,
            "training_contingency": training_contingency,
            "source_session_id": source_session,
            "num_sessions": num_sessions,
            "source_trial_index": trial_index,
            "stim_rate": stim_rate,
            "category_boundary_hz": ODOEMENE_CATEGORY_BOUNDARY_HZ,
            "signed_rate_from_boundary": signed_rate,
            "stim_event_bins": event_bins,
            "stim_event_count": sum(event_bins),
            "event_bin_seconds": ODOEMENE_EVENT_BIN_SECONDS,
            "subject_response_code": subject_response,
            "correct_response_code": correct_response,
            "subject_response_category": _category_label(subject_response),
            "correct_response_category": _category_label(correct_response),
            "valid_trial": valid_trial,
            "success": success,
            "wait_time": wait_time,
            "move_time": move_time,
            "canonical_choice_convention": "right=high-rate response; left=low-rate response",
            "canonical_stimulus_convention": "right=high-rate category; left=low-rate category",
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def analyze_odoemene_visual_accumulation(trials: list[CanonicalTrial]) -> dict[str, Any]:
    result = analyze_canonical_psychometric(
        trials,
        analysis_id="analysis.odoemene-visual-accumulation.descriptive-psychometric-kernel",
        protocol_id=ODOEMENE_PROTOCOL_ID,
        dataset_id=ODOEMENE_DATASET_ID,
        report_title="Odoemene Visual Evidence Accumulation Report",
        stimulus_label="Signed flash rate",
        stimulus_units="flashes/s minus 12 Hz category boundary",
        stimulus_metric_name="flash_rate",
        caveats=[
            (
                "Canonical right means high-rate response and canonical left means "
                "low-rate response; physical port side is preserved separately through "
                "the training contingency where available."
            ),
            (
                "Invalid source trials are retained as no-response trials and excluded "
                "from the p(high-rate choice) denominator."
            ),
            (
                "The event-bin kernel is descriptive: it compares event presence in "
                "40 ms bins between high-rate and low-rate choices, not a full GLM."
            ),
        ],
    )
    kernel_rows = odoemene_event_kernel_rows(trials)
    result["analysis_type"] = "descriptive_psychometric_kernel"
    result["event_kernel_rows"] = kernel_rows
    result["event_kernel_bin_seconds"] = ODOEMENE_EVENT_BIN_SECONDS
    result["event_kernel_analyzed_trials"] = _event_kernel_analyzed_trials(trials)
    result["event_kernel_excluded_trials"] = len(trials) - result["event_kernel_analyzed_trials"]
    result["n_subjects"] = len({trial.subject_id for trial in trials if trial.subject_id})
    result["n_source_sessions"] = len({trial.block_id for trial in trials if trial.block_id})
    return result


def odoemene_event_kernel_rows(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    analyzed = [
        trial
        for trial in trials
        if trial.choice in {"left", "right"}
        and isinstance(trial.task_variables.get("stim_event_bins"), list)
    ]
    rows = []
    for bin_index in range(ODOEMENE_N_EVENT_BINS):
        values = []
        choices = []
        for trial in analyzed:
            bins = trial.task_variables.get("stim_event_bins", [])
            if not isinstance(bins, list) or len(bins) <= bin_index:
                continue
            values.append(float(bins[bin_index]))
            choices.append(1.0 if trial.choice == "right" else 0.0)
        high_values = [
            value for value, choice in zip(values, choices, strict=True) if choice == 1.0
        ]
        low_values = [
            value for value, choice in zip(values, choices, strict=True) if choice == 0.0
        ]
        mean_high = statistics.mean(high_values) if high_values else None
        mean_low = statistics.mean(low_values) if low_values else None
        choice_difference = (
            mean_high - mean_low if mean_high is not None and mean_low is not None else None
        )
        rows.append(
            {
                "bin_index": bin_index,
                "bin_start": bin_index * ODOEMENE_EVENT_BIN_SECONDS,
                "bin_end": (bin_index + 1) * ODOEMENE_EVENT_BIN_SECONDS,
                "n_trials": len(values),
                "n_high_choice": len(high_values),
                "n_low_choice": len(low_values),
                "mean_event": statistics.mean(values) if values else None,
                "mean_event_high_choice": mean_high,
                "mean_event_low_choice": mean_low,
                "choice_difference": choice_difference,
                "point_biserial_r": _point_biserial(values, choices),
                "normalized_weight": None,
            }
        )
    differences = [
        abs(float(row["choice_difference"]))
        for row in rows
        if row["choice_difference"] is not None
    ]
    max_abs = max(differences, default=0.0)
    if max_abs > 0.0:
        for row in rows:
            if row["choice_difference"] is not None:
                row["normalized_weight"] = float(row["choice_difference"]) / max_abs
    return rows


def write_odoemene_kernel_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ODOEMENE_KERNEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_odoemene_kernel_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(odoemene_kernel_svg(rows), encoding="utf-8")


def write_odoemene_report_html(
    path: Path,
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    kernel_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        odoemene_report_html(
            analysis_result,
            provenance=provenance,
            psychometric_svg_text=psychometric_svg_text,
            kernel_svg_text=kernel_svg_text,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def odoemene_provenance_payload(
    *,
    details: dict[str, Any],
    trials: list[CanonicalTrial],
    output_files: dict[str, str],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": ODOEMENE_PROTOCOL_ID,
        "dataset_id": ODOEMENE_DATASET_ID,
        "source": details,
        "source_fields": ODOEMENE_RAW_FIELDS,
        "response_time_origin": "moveTime: center-port withdrawal to side-port response",
        "n_trials": len(trials),
        "exclusions": {
            "invalid_trials": sum(1 for trial in trials if trial.choice == "no-response"),
            "missing_event_bins": sum(
                1 for trial in trials if not trial.task_variables.get("stim_event_bins")
            ),
            "missing_response_time": sum(1 for trial in trials if trial.response_time is None),
        },
        "outputs": output_files,
        "caveats": [
            (
                "The public storage pointer is indirect through the CSHL repository; "
                "download the MATLAB file into ignored local raw-data storage before "
                "running this adapter."
            ),
            (
                "Generated trial tables and reports remain under ignored derived paths "
                "until source-file redistribution policy is reviewed."
            ),
        ],
    }


def odoemene_kernel_svg(rows: list[dict[str, Any]]) -> str:
    width = 720
    height = 360
    left = 72
    right = 28
    top = 28
    bottom = 56
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [
        float(row["normalized_weight"])
        for row in rows
        if row.get("normalized_weight") is not None
    ]
    if not values:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
            '<text x="20" y="60">No Odoemene event-kernel data available</text></svg>\n'
        )
    y_min = min(-1.0, min(values))
    y_max = max(1.0, max(values))

    def x_scale(index: int) -> float:
        if len(rows) <= 1:
            return left + plot_width / 2
        return left + (index / (len(rows) - 1)) * plot_width

    def y_scale(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * plot_height

    zero_y = y_scale(0.0)
    points = [
        (x_scale(int(row["bin_index"])), y_scale(float(row["normalized_weight"])))
        for row in rows
        if row.get("normalized_weight") is not None
    ]
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#222"/>',
        f'<line x1="{left}" y1="{zero_y:.1f}" x2="{left + plot_width}" y2="{zero_y:.1f}" '
        'stroke="#aaa" stroke-dasharray="4 4"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 16}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14">Stimulus time (s)</text>',
        f'<text x="18" y="{top + plot_height / 2}" text-anchor="middle" '
        'font-family="sans-serif" font-size="14" transform="rotate(-90 18 '
        f'{top + plot_height / 2})">Normalized event-choice weight</text>',
    ]
    for y_value in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        y = y_scale(y_value)
        elements.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="11">{y_value:.1g}</text>'
        )
    for x_value in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = left + x_value * plot_width
        elements.append(
            f'<line x1="{x:.1f}" y1="{top + plot_height}" x2="{x:.1f}" '
            f'y2="{top + plot_height + 4}" stroke="#222"/>'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 20}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="10">{x_value:.2g}</text>'
        )
    point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    elements.append(
        f'<polyline points="{point_attr}" fill="none" stroke="#145f91" stroke-width="2"/>'
    )
    for x, y in points:
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="#145f91"/>')
    elements.append("</svg>")
    return "\n".join(elements) + "\n"


def odoemene_report_html(
    analysis_result: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
    psychometric_svg_text: str | None = None,
    kernel_svg_text: str | None = None,
    artifact_links: dict[str, str] | None = None,
) -> str:
    provenance = provenance or {}
    source = provenance.get("source", {}) if isinstance(provenance.get("source"), dict) else {}
    artifact_links = artifact_links or {}
    psychometric_svg_text = psychometric_svg_text or (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        '<text x="20" y="60">Psychometric plot not available</text></svg>'
    )
    kernel_svg_text = kernel_svg_text or (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="120">'
        '<text x="20" y="60">Event-kernel plot not available</text></svg>'
    )
    title = str(analysis_result.get("report_title") or "Odoemene Visual Evidence Report")
    metrics = [
        ("Trials", analysis_result.get("n_trials")),
        ("Response trials", analysis_result.get("n_response_trials")),
        ("No-response trials", analysis_result.get("n_no_response_trials")),
        ("Subjects", analysis_result.get("n_subjects")),
        ("Source sessions", analysis_result.get("n_source_sessions")),
        ("Kernel bins", len(analysis_result.get("event_kernel_rows", []))),
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
        "<p class=\"lede\">Visual flash-rate accumulation report with a category "
        "psychometric and a descriptive 25-bin event-choice kernel.</p>",
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
                    ("CSHL repository", source.get("source_url")),
                    ("Dataset DOI", source.get("dataset_doi")),
                    ("MATLAB file", source.get("source_file_name")),
                    ("MATLAB variable", source.get("matlab_variable")),
                    ("Subjects", source.get("n_subjects_source")),
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
            "<h2>Psychometric Summary</h2>",
            '<div class="figure-wrap">',
            psychometric_svg_text,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Event Kernel</h2>",
            '<div class="figure-wrap">',
            kernel_svg_text,
            "</div>",
            "</section>",
            "<section>",
            "<h2>Psychometric Points</h2>",
            _html_table(
                analysis_result.get("summary_rows", []),
                [
                    ("prior_context", "Contingency"),
                    ("stimulus_value", "Rate from boundary"),
                    ("n_trials", "Trials"),
                    ("n_response", "Responses"),
                    ("n_right", "High choices"),
                    ("p_right", "P(high)"),
                    ("p_correct", "P(correct)"),
                    ("median_response_time", "Median move time"),
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


def _odoemene_subject_records(loaded: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    candidates = [
        "data",
        "dataset",
        "mouseData",
        "mice",
        "subjectData",
        "allData",
        "Odoemene2020",
    ]
    for name in candidates:
        if name in loaded:
            records = _as_subject_record_list(loaded[name])
            if records:
                return records, name
    for name, value in loaded.items():
        if name.startswith("__"):
            continue
        records = _as_subject_record_list(value)
        if records:
            return records, name
    raise ValueError(
        "Could not find Odoemene subject structure array in MATLAB file. "
        "Expected a 1x29 structure array with raw choice data."
    )


def _as_subject_record_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and _looks_like_subject_record(value):
        return [value]
    if isinstance(value, list | tuple):
        records = [
            item
            for item in value
            if isinstance(item, dict) and _looks_like_subject_record(item)
        ]
        return records
    if isinstance(value, np.ndarray):
        records = []
        for item in value.flat:
            if isinstance(item, dict) and _looks_like_subject_record(item):
                records.append(item)
        return records
    return []


def _looks_like_subject_record(value: dict[str, Any]) -> bool:
    try:
        _subject_raw_choice_data(value)
    except ValueError:
        return False
    return True


def _subject_raw_choice_data(subject_record: dict[str, Any]) -> dict[str, Any]:
    raw = _field_alias(
        subject_record,
        ["rawChoiceData", "raw_choice_data", "choiceData", "choice_data", "rawData", "raw"],
    )
    if isinstance(raw, dict):
        return raw
    if all(field in subject_record for field in ODOEMENE_RAW_FIELDS):
        return subject_record
    raise ValueError("Expected subject record to contain Odoemene raw choice data")


def _validate_raw_choice_data(raw: dict[str, Any]) -> int:
    missing = sorted(field for field in ODOEMENE_RAW_FIELDS if field not in raw)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Odoemene raw choice fields: {joined}")
    n_trials = len(_as_vector(raw["stimRate"]))
    for field in ODOEMENE_RAW_FIELDS:
        actual = len(_as_vector(raw[field]))
        if actual != n_trials:
            raise ValueError(f"Field {field!r} has length {actual}, expected {n_trials}")
    return n_trials


def _raw_choice_row(raw: dict[str, Any], index: int) -> dict[str, Any]:
    return {field: _index_value(raw[field], index) for field in ODOEMENE_RAW_FIELDS}


def _index_value(values: Any, index: int) -> Any:
    vector = _as_vector(values)
    value = vector[index]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value.tolist()
    return value


def _as_vector(values: Any) -> list[Any]:
    if isinstance(values, np.ndarray):
        if values.ndim == 0:
            return [values.item()]
        return list(values.tolist())
    if isinstance(values, list | tuple):
        return list(values)
    return [values]


def _field_alias(mapping: dict[str, Any], names: list[str]) -> Any:
    lowered = {key.lower(): key for key in mapping}
    for name in names:
        key = lowered.get(name.lower())
        if key is not None:
            return mapping[key]
    return None


def _subject_id(subject_record: dict[str, Any], subject_index: int) -> str:
    value = _field_alias(
        subject_record,
        ["subjectID", "subjectId", "subject_id", "subject", "mouseID", "mouseId", "mouse"],
    )
    text = _optional_text(value)
    if text:
        return _session_token(text)
    return f"subject-{subject_index + 1:02d}"


def _event_bin_list(value: Any) -> list[int]:
    vector = _as_vector(value)
    if len(vector) == 1 and isinstance(vector[0], list | tuple | np.ndarray):
        vector = _as_vector(vector[0])
    bins = []
    for item in vector:
        numeric = _optional_float(item)
        bins.append(1 if numeric and numeric > 0.0 else 0)
    return bins


def _category_choice_label(value: int | None) -> str:
    if value == 1:
        return "left"
    if value == 2:
        return "right"
    return "unknown"


def _category_side(value: int | None) -> str:
    if value == 1:
        return "left"
    if value == 2:
        return "right"
    return "unknown"


def _category_label(value: int | None) -> str | None:
    if value == 1:
        return "low-rate"
    if value == 2:
        return "high-rate"
    return None


def _event_kernel_analyzed_trials(trials: list[CanonicalTrial]) -> int:
    return sum(
        1
        for trial in trials
        if trial.choice in {"left", "right"}
        and isinstance(trial.task_variables.get("stim_event_bins"), list)
    )


def _point_biserial(values: list[float], choices: list[float]) -> float | None:
    if len(values) < 2 or len(values) != len(choices):
        return None
    mean_x = statistics.mean(values)
    mean_y = statistics.mean(choices)
    variance_x = sum((value - mean_x) ** 2 for value in values)
    variance_y = sum((choice - mean_y) ** 2 for choice in choices)
    if variance_x == 0.0 or variance_y == 0.0:
        return None
    covariance = sum(
        (value - mean_x) * (choice - mean_y)
        for value, choice in zip(values, choices, strict=True)
    )
    return covariance / math.sqrt(variance_x * variance_y)


def _required_float(value: Any, *, field: str) -> float:
    numeric = _optional_float(value)
    if numeric is None:
        raise ValueError(f"Field {field!r} is required to be finite")
    return numeric


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _optional_int(value: Any) -> int | None:
    numeric = _optional_float(value)
    return int(numeric) if numeric is not None else None


def _required_bool(value: Any, *, field: str) -> bool:
    parsed = _optional_bool(value)
    if parsed is None:
        raise ValueError(f"Field {field!r} is required to be boolean-like")
    return parsed


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool | np.bool_):
        return bool(value)
    numeric = _optional_float(value)
    if numeric == 1.0:
        return True
    if numeric == 0.0:
        return False
    return None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, list | tuple) and len(value) == 1:
        value = value[0]
    text = str(value).strip()
    return text or None


def _session_token(value: Any) -> str:
    text = _optional_text(value) or "unknown"
    chars = [char.lower() if char.isalnum() else "-" for char in text]
    return "-".join(part for part in "".join(chars).split("-") if part) or "unknown"


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
    numeric = _optional_float(value)
    if numeric is not None:
        return numeric
    return str(value)


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
    numeric = _optional_float(value)
    if numeric is not None:
        if numeric.is_integer():
            return f"{int(numeric):,}"
        return f"{numeric:.4g}"
    return str(value)


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
