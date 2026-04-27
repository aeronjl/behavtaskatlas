from __future__ import annotations

import csv
import json
import math
import statistics
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from html import escape
from pathlib import Path
from typing import Any

from behavtaskatlas.ibl import (
    current_git_commit,
    current_git_dirty,
    installed_package_version,
)
from behavtaskatlas.models import CanonicalTrial

ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID = "protocol.mouse-visual-change-detection-allen"
ALLEN_VISUAL_BEHAVIOR_DATASET_ID = "dataset.allen-brain-observatory-visual-behavior"
DEFAULT_ALLEN_VISUAL_BEHAVIOR_RAW_DIR = Path("data/raw/allen_visual_behavior")
DEFAULT_ALLEN_VISUAL_BEHAVIOR_DERIVED_DIR = Path("derived/allen_visual_behavior")
ALLEN_VISUAL_BEHAVIOR_PORTAL_URL = (
    "https://portal.brain-map.org/explore/circuits/visual-behavior-2p"
)
ALLEN_VISUAL_BEHAVIOR_S3_PREFIX = "s3://visual-behavior-ophys-data"

ALLEN_REQUIRED_TRIAL_FIELDS = (
    "go",
    "catch",
    "hit",
    "miss",
    "false_alarm",
    "correct_reject",
    "aborted",
    "auto_rewarded",
    "initial_image_name",
    "change_image_name",
    "response_latency",
    "reward_volume",
)

CANONICAL_TRIAL_CSV_FIELDS = [
    "protocol_id",
    "dataset_id",
    "subject_id",
    "session_id",
    "trial_index",
    "stimulus_modality",
    "stimulus_value",
    "stimulus_units",
    "stimulus_side",
    "evidence_strength",
    "evidence_units",
    "choice",
    "correct",
    "response_time",
    "response_time_origin",
    "feedback",
    "reward",
    "reward_units",
    "block_id",
    "prior_context",
    "training_stage",
    "task_variables_json",
    "source_json",
]

CHANGE_DETECTION_OUTCOME_FIELDS = [
    "outcome",
    "n_trials",
    "fraction",
]

CHANGE_DETECTION_IMAGE_PAIR_FIELDS = [
    "initial_image",
    "change_image",
    "n_trials",
    "n_hit",
    "n_miss",
    "hit_rate",
    "median_response_latency",
]


def harmonize_allen_change_detection_row(
    source: dict[str, Any],
    *,
    session_id: str,
    trial_index: int,
    subject_id: str | None = None,
    dataset_id: str = ALLEN_VISUAL_BEHAVIOR_DATASET_ID,
    protocol_id: str = ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID,
) -> CanonicalTrial:
    missing = sorted(
        field for field in ALLEN_REQUIRED_TRIAL_FIELDS if field not in source
    )
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required Allen Visual Behavior trial fields: {joined}")

    is_go = _truthy(source["go"])
    is_catch = _truthy(source["catch"])
    is_hit = _truthy(source["hit"])
    is_miss = _truthy(source["miss"])
    is_false_alarm = _truthy(source["false_alarm"])
    is_correct_reject = _truthy(source["correct_reject"])
    is_aborted = _truthy(source["aborted"])
    is_auto_rewarded = _truthy(source["auto_rewarded"])

    outcome = _change_detection_outcome(
        is_hit=is_hit,
        is_miss=is_miss,
        is_false_alarm=is_false_alarm,
        is_correct_reject=is_correct_reject,
        is_aborted=is_aborted,
        is_auto_rewarded=is_auto_rewarded,
    )

    choice = _outcome_choice(outcome)
    correct = _outcome_correct(outcome)
    feedback = _outcome_feedback(outcome, reward_volume=source["reward_volume"])
    response_time = _finite_or_none(source["response_latency"])
    reward = _finite_or_none(source["reward_volume"])
    initial_image = _string_or_none(source["initial_image_name"])
    change_image = _string_or_none(source["change_image_name"])

    return CanonicalTrial(
        protocol_id=protocol_id,
        dataset_id=dataset_id,
        subject_id=subject_id,
        session_id=session_id,
        trial_index=trial_index,
        stimulus_modality="visual",
        stimulus_value=None,
        stimulus_units=None,
        stimulus_side="none",
        evidence_strength=None,
        evidence_units=None,
        choice=choice,
        correct=correct,
        response_time=response_time,
        response_time_origin="response_latency seconds after change time",
        feedback=feedback,
        reward=reward,
        reward_units="mL" if reward is not None else None,
        training_stage=_string_or_none(source.get("session_type")),
        task_variables={
            "outcome": outcome,
            "is_change": is_go,
            "is_catch": is_catch,
            "is_aborted": is_aborted,
            "is_auto_rewarded": is_auto_rewarded,
            "initial_image_name": initial_image,
            "change_image_name": change_image,
            "image_pair": _image_pair_label(initial_image, change_image),
            "change_time_in_trial": _finite_or_none(source.get("change_time_no_display_delay")),
            "trial_length": _finite_or_none(source.get("trial_length")),
            "n_lick_times": _lick_count(source.get("lick_times")),
            "canonical_choice_convention": (
                "go=lick within response window; withhold=no lick on change or catch trial; "
                "no-response=aborted (lick before change window)"
            ),
        },
        source={key: _json_safe_value(value) for key, value in source.items()},
    )


def harmonize_allen_change_detection_rows(
    rows: Any,
    *,
    session_id: str,
    subject_id: str | None = None,
    limit: int | None = None,
) -> list[CanonicalTrial]:
    sequence = _row_sequence(rows)
    n_rows = len(sequence)
    if limit is not None:
        n_rows = min(n_rows, limit)
    return [
        harmonize_allen_change_detection_row(
            sequence[index],
            session_id=session_id,
            subject_id=subject_id,
            trial_index=index,
        )
        for index in range(n_rows)
    ]


def load_allen_visual_behavior_session(
    *,
    nwb_file: Path,
    limit: int | None = None,
) -> tuple[list[CanonicalTrial], dict[str, Any]]:
    rows, nwb_meta = read_visual_behavior_nwb(nwb_file)
    behavior_session_id = nwb_meta.get("behavior_session_id")
    subject_id = nwb_meta.get("subject_id")
    session_id = (
        str(behavior_session_id) if behavior_session_id is not None else nwb_file.stem
    )
    canonical = harmonize_allen_change_detection_rows(
        rows,
        session_id=session_id,
        subject_id=subject_id,
        limit=limit,
    )
    details = {
        "behavior_session_id": behavior_session_id,
        "behavior_session_uuid": nwb_meta.get("behavior_session_uuid"),
        "subject_id": subject_id,
        "session_type": nwb_meta.get("session_type"),
        "project_code": nwb_meta.get("project_code"),
        "equipment_name": nwb_meta.get("equipment_name"),
        "stimulus_frame_rate": nwb_meta.get("stimulus_frame_rate"),
        "n_source_rows": len(rows),
        "n_trials": len(canonical),
        "nwb_file": str(nwb_file),
        "nwb_file_sha256": nwb_meta.get("nwb_file_sha256"),
        "nwb_file_bytes": nwb_meta.get("nwb_file_bytes"),
    }
    return canonical, details


def download_allen_visual_behavior_session(
    *,
    nwb_url: str,
    out_file: Path,
) -> dict[str, Any]:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        nwb_url, headers={"User-Agent": "behavtaskatlas/0.1"}
    )
    with urllib.request.urlopen(request) as response, out_file.open("wb") as handle:
        digest = sha256()
        n_bytes = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            n_bytes += len(chunk)
    return {
        "nwb_url": nwb_url,
        "nwb_file": str(out_file),
        "nwb_file_bytes": n_bytes,
        "nwb_file_sha256": digest.hexdigest(),
    }


def read_visual_behavior_nwb(nwb_file: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError(
            "Allen Visual Behavior ingestion requires the optional h5py "
            "dependency. Install it with `uv sync --extra allen`."
        ) from exc

    if not nwb_file.exists():
        raise FileNotFoundError(
            f"NWB file not found: {nwb_file}. "
            "Run `behavtaskatlas allen-visual-behavior-download --nwb-url <url>` "
            "or place a Visual Behavior NWB file at that path."
        )

    rows: list[dict[str, Any]] = []
    meta: dict[str, Any] = {
        "nwb_file_sha256": _file_sha256(nwb_file),
        "nwb_file_bytes": nwb_file.stat().st_size,
    }
    with h5py.File(nwb_file, "r") as handle:
        rows = _nwb_trials_to_rows(handle)
        meta.update(_nwb_session_metadata(handle))
    return rows, meta


def analyze_allen_change_detection(
    trials: list[CanonicalTrial],
    *,
    analysis_id: str = "analysis.allen-visual-behavior.change-detection",
    protocol_id: str = ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID,
    dataset_id: str = ALLEN_VISUAL_BEHAVIOR_DATASET_ID,
    report_title: str = "Allen Visual Behavior Change Detection Report",
) -> dict[str, Any]:
    outcome_counts = _count_outcomes(trials)
    n_trials = len(trials)
    n_hit = outcome_counts.get("hit", 0)
    n_miss = outcome_counts.get("miss", 0)
    n_false_alarm = outcome_counts.get("false_alarm", 0)
    n_correct_reject = outcome_counts.get("correct_reject", 0)
    n_go = n_hit + n_miss
    n_catch = n_false_alarm + n_correct_reject
    hit_rate = _safe_ratio(n_hit, n_go)
    false_alarm_rate = _safe_ratio(n_false_alarm, n_catch)
    d_prime = _d_prime(
        n_hit=n_hit,
        n_go=n_go,
        n_false_alarm=n_false_alarm,
        n_catch=n_catch,
    )
    response_latencies = [
        trial.response_time
        for trial in trials
        if trial.response_time is not None
        and trial.task_variables.get("outcome") == "hit"
    ]
    image_pair_rows = _image_pair_summary(trials)
    return {
        "analysis_id": analysis_id,
        "analysis_type": "change_detection",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "protocol_id": protocol_id,
        "dataset_id": dataset_id,
        "report_title": report_title,
        "n_trials": n_trials,
        "n_go_trials": n_go,
        "n_catch_trials": n_catch,
        "outcome_counts": outcome_counts,
        "hit_rate": hit_rate,
        "false_alarm_rate": false_alarm_rate,
        "d_prime": d_prime,
        "median_hit_response_latency": (
            statistics.median(response_latencies) if response_latencies else None
        ),
        "mean_hit_response_latency": (
            statistics.fmean(response_latencies) if response_latencies else None
        ),
        "n_hit_response_latencies": len(response_latencies),
        "image_pair_summary": image_pair_rows,
        "caveats": [
            (
                "Aborted trials (early licks before the change window) are filtered "
                "from rate calculations; they appear in outcome counts only."
            ),
            (
                "Auto-rewarded trials are tagged in task_variables but are kept in the "
                "canonical table; they are excluded from hit and false-alarm rates."
            ),
            (
                "Change-detection rates are reported per session without subject-level "
                "pooling; a multi-session aggregate is out of MVP scope."
            ),
        ],
    }


def write_canonical_trials_csv(path: Path, trials: list[CanonicalTrial]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_TRIAL_CSV_FIELDS)
        writer.writeheader()
        for trial in trials:
            row = trial.model_dump(mode="json")
            source = row.pop("source")
            task_variables = row.pop("task_variables")
            row["task_variables_json"] = json.dumps(task_variables, sort_keys=True)
            row["source_json"] = json.dumps(source, sort_keys=True)
            writer.writerow(row)


def write_outcome_summary_csv(path: Path, outcome_counts: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = sum(outcome_counts.values()) or 1
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHANGE_DETECTION_OUTCOME_FIELDS)
        writer.writeheader()
        for outcome in (
            "hit",
            "miss",
            "false_alarm",
            "correct_reject",
            "aborted",
            "auto_rewarded",
        ):
            n = outcome_counts.get(outcome, 0)
            writer.writerow(
                {
                    "outcome": outcome,
                    "n_trials": n,
                    "fraction": round(n / total, 6),
                }
            )


def write_image_pair_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHANGE_DETECTION_IMAGE_PAIR_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_lick_latency_svg(
    path: Path,
    trials: list[CanonicalTrial],
    *,
    title: str = "Hit lick latency (seconds after change)",
    bin_width: float = 0.05,
    max_latency: float = 0.75,
) -> None:
    latencies = [
        trial.response_time
        for trial in trials
        if trial.response_time is not None
        and 0.0 <= trial.response_time <= max_latency
        and trial.task_variables.get("outcome") == "hit"
    ]
    n_bins = max(1, int(round(max_latency / bin_width)))
    counts = [0] * n_bins
    for value in latencies:
        idx = min(n_bins - 1, int(value / bin_width))
        counts[idx] += 1
    peak = max(counts) if counts else 0
    width = 480
    height = 280
    margin_left = 60
    margin_right = 20
    margin_top = 36
    margin_bottom = 50
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    bar_width = plot_w / n_bins
    bars = []
    for i, count in enumerate(counts):
        bar_h = (count / peak * plot_h) if peak else 0
        x = margin_left + i * bar_width
        y = margin_top + plot_h - bar_h
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(0.0, bar_width - 1):.2f}" '
            f'height="{bar_h:.2f}" fill="#3a6ea5" />'
        )
    x_ticks = []
    for k in range(n_bins + 1):
        if k % max(1, n_bins // 5) != 0 and k != n_bins:
            continue
        tx = margin_left + k * bar_width
        label = f"{k * bin_width:.2f}"
        x_ticks.append(
            f'<line x1="{tx:.2f}" y1="{margin_top + plot_h}" '
            f'x2="{tx:.2f}" y2="{margin_top + plot_h + 4}" stroke="#333" />'
            f'<text x="{tx:.2f}" y="{margin_top + plot_h + 18}" '
            f'text-anchor="middle" font-size="10" fill="#333">{label}</text>'
        )
    y_label_max = peak if peak else 1
    y_ticks = [
        f'<text x="{margin_left - 8}" y="{margin_top + 4}" text-anchor="end" '
        f'font-size="10" fill="#333">{y_label_max}</text>',
        f'<text x="{margin_left - 8}" y="{margin_top + plot_h + 4}" '
        f'text-anchor="end" font-size="10" fill="#333">0</text>',
    ]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" fill="white" />'
        f'<text x="{width / 2}" y="20" text-anchor="middle" font-size="14" fill="#111">'
        f"{escape(title)}</text>"
        f'<line x1="{margin_left}" y1="{margin_top}" '
        f'x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#333" />'
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" '
        f'x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#333" />'
        + "".join(bars)
        + "".join(x_ticks)
        + "".join(y_ticks)
        + f'<text x="{margin_left + plot_w / 2}" y="{height - 10}" '
        f'text-anchor="middle" font-size="11" fill="#333">'
        "seconds after change</text>"
        f'<text x="20" y="{margin_top + plot_h / 2}" '
        f'text-anchor="middle" font-size="11" fill="#333" '
        f'transform="rotate(-90 20 {margin_top + plot_h / 2})">trial count</text>'
        "</svg>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg + "\n")


def write_analysis_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def write_change_detection_report_html(
    path: Path,
    *,
    analysis: dict[str, Any],
    provenance: dict[str, Any],
    image_pair_rows: list[dict[str, Any]],
) -> None:
    title = analysis.get("report_title", "Allen Visual Behavior Change Detection Report")
    body = []
    body.append(f"<h1>{escape(title)}</h1>")
    body.append(
        "<p>Single-session change-detection summary harmonized from the Allen "
        "Brain Observatory Visual Behavior open dataset. Hit and false-alarm "
        "rates are reported per session; aborted and auto-rewarded trials are "
        "excluded from rate calculations.</p>"
    )
    overview_rows = [
        ("Behavior session id", provenance.get("source", {}).get("behavior_session_id")),
        ("Subject id", provenance.get("source", {}).get("subject_id")),
        ("Session type", provenance.get("source", {}).get("session_type")),
        ("Trials", analysis.get("n_trials")),
        ("Go trials", analysis.get("n_go_trials")),
        ("Catch trials", analysis.get("n_catch_trials")),
        ("Hit rate", _format_rate(analysis.get("hit_rate"))),
        ("False-alarm rate", _format_rate(analysis.get("false_alarm_rate"))),
        ("d-prime", _format_number(analysis.get("d_prime"))),
        (
            "Median hit response latency (s)",
            _format_number(analysis.get("median_hit_response_latency")),
        ),
    ]
    body.append("<h2>Overview</h2>")
    body.append(_html_definition_list(overview_rows))

    body.append("<h2>Outcome counts</h2>")
    outcome_counts = analysis.get("outcome_counts", {})
    outcome_table_rows = [
        {"outcome": outcome, "count": outcome_counts.get(outcome, 0)}
        for outcome in (
            "hit",
            "miss",
            "false_alarm",
            "correct_reject",
            "aborted",
            "auto_rewarded",
        )
    ]
    body.append(
        _html_table(
            outcome_table_rows,
            columns=[("outcome", "Outcome"), ("count", "Trials")],
        )
    )

    body.append("<h2>Per image pair</h2>")
    if image_pair_rows:
        body.append(
            _html_table(
                image_pair_rows,
                columns=[
                    ("initial_image", "Initial"),
                    ("change_image", "Change"),
                    ("n_trials", "Trials"),
                    ("n_hit", "Hits"),
                    ("n_miss", "Misses"),
                    ("hit_rate", "Hit rate"),
                    ("median_response_latency", "Median latency (s)"),
                ],
            )
        )
    else:
        body.append("<p>No image-pair entries were available for this session.</p>")

    body.append("<h2>Lick latency</h2>")
    body.append('<p><img src="lick_latency.svg" alt="Hit lick latency histogram" /></p>')

    caveats = analysis.get("caveats") or []
    if caveats:
        body.append("<h2>Caveats</h2>")
        body.append(
            "<ul>" + "".join(f"<li>{escape(str(c))}</li>" for c in caveats) + "</ul>"
        )

    body.append("<h2>Provenance</h2>")
    provenance_rows = [
        ("Behavior session id", provenance.get("source", {}).get("behavior_session_id")),
        ("AllenSDK version", provenance.get("allensdk_version")),
        ("behavtaskatlas commit", provenance.get("behavtaskatlas_commit")),
        ("Working tree dirty", provenance.get("behavtaskatlas_git_dirty")),
        ("Generated", provenance.get("generated_at")),
    ]
    body.append(_html_definition_list(provenance_rows))

    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{escape(title)}</title>"
        "<style>" + _report_css() + "</style></head><body>"
        + "".join(body)
        + "</body></html>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html + "\n")


def allen_visual_behavior_provenance_payload(
    *,
    details: dict[str, Any],
    output_files: dict[str, str],
    trials: list[CanonicalTrial],
) -> dict[str, Any]:
    outcome_counts = _count_outcomes(trials)
    return {
        "protocol_id": ALLEN_VISUAL_BEHAVIOR_PROTOCOL_ID,
        "dataset_id": ALLEN_VISUAL_BEHAVIOR_DATASET_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "allensdk_version": installed_package_version("allensdk"),
        "source": {
            "portal_url": ALLEN_VISUAL_BEHAVIOR_PORTAL_URL,
            "s3_prefix": ALLEN_VISUAL_BEHAVIOR_S3_PREFIX,
            "behavior_session_id": details.get("behavior_session_id"),
            "behavior_session_uuid": details.get("behavior_session_uuid"),
            "subject_id": details.get("subject_id"),
            "session_type": details.get("session_type"),
            "project_code": details.get("project_code"),
            "equipment_name": details.get("equipment_name"),
            "stimulus_frame_rate": details.get("stimulus_frame_rate"),
            "nwb_file": details.get("nwb_file"),
            "nwb_file_sha256": details.get("nwb_file_sha256"),
            "nwb_file_bytes": details.get("nwb_file_bytes"),
        },
        "source_fields": list(ALLEN_REQUIRED_TRIAL_FIELDS),
        "response_time_origin": "response_latency seconds after change time",
        "n_trials": len(trials),
        "outcome_counts": outcome_counts,
        "outputs": output_files,
        "caveats": [
            (
                "Generated artifacts are ignored by git until dataset licensing and "
                "release policy are confirmed."
            ),
            (
                "The slice pins one BehaviorSession from the Visual Behavior 2P "
                "release; sister sessions in the same project are not bundled."
            ),
        ],
    }


# Helpers


def _row_sequence(rows: Any) -> list[dict[str, Any]]:
    if hasattr(rows, "to_dict"):
        records = rows.to_dict(orient="records")
        return [dict(record) for record in records]
    return [dict(row) for row in rows]


def _nwb_trials_to_rows(handle: Any) -> list[dict[str, Any]]:
    if "intervals/trials" not in handle:
        raise ValueError(
            "NWB file does not contain /intervals/trials; this does not look "
            "like a Visual Behavior behavior NWB file."
        )
    trials_group = handle["intervals/trials"]
    n_trials = _nwb_n_rows(trials_group)
    column_values: dict[str, list[Any]] = {}
    for name, dataset in trials_group.items():
        if name == "id":
            continue
        if name.endswith("_index"):
            continue
        if hasattr(dataset, "shape"):
            scalar_values = _nwb_scalar_column(trials_group, name, n_trials)
            if scalar_values is not None:
                column_values[name] = scalar_values
                continue
            ragged_values = _nwb_ragged_column(trials_group, name, n_trials)
            if ragged_values is not None:
                column_values[name] = ragged_values
    rows: list[dict[str, Any]] = []
    for index in range(n_trials):
        row = {name: column_values[name][index] for name in column_values}
        rows.append(row)
    return rows


def _nwb_n_rows(trials_group: Any) -> int:
    ids = trials_group.get("id")
    if ids is None or not hasattr(ids, "shape"):
        for value in trials_group.values():
            if hasattr(value, "shape") and len(value.shape) >= 1:
                return int(value.shape[0])
        return 0
    return int(ids.shape[0])


def _nwb_scalar_column(trials_group: Any, name: str, n_trials: int) -> list[Any] | None:
    index_name = f"{name}_index"
    if index_name in trials_group:
        return None
    dataset = trials_group[name]
    if not hasattr(dataset, "shape"):
        return None
    if len(dataset.shape) != 1 or int(dataset.shape[0]) != n_trials:
        return None
    raw = dataset[:]
    return [_decode_nwb_scalar(value) for value in raw]


def _nwb_ragged_column(trials_group: Any, name: str, n_trials: int) -> list[Any] | None:
    index_name = f"{name}_index"
    if index_name not in trials_group:
        return None
    index_dataset = trials_group[index_name]
    data_dataset = trials_group[name]
    if int(index_dataset.shape[0]) != n_trials:
        return None
    indices = list(int(value) for value in index_dataset[:])
    data = data_dataset[:]
    rows: list[Any] = []
    start = 0
    for end in indices:
        chunk = data[start:end]
        rows.append([_decode_nwb_scalar(item) for item in chunk])
        start = end
    return rows


def _decode_nwb_scalar(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _nwb_session_metadata(handle: Any) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    metadata_attrs: dict[str, Any] = {}
    if "general/metadata" in handle:
        attrs = handle["general/metadata"].attrs
        metadata_attrs = {key: attrs[key] for key in attrs}
    session_id = (
        metadata_attrs.get("behavior_session_id")
        or _nwb_attr_or_dataset(handle, "general/session_id")
        or _nwb_attr_or_dataset(handle, "identifier")
    )
    if session_id is not None:
        decoded = _decode_nwb_scalar(session_id)
        coerced = _coerce_int(decoded)
        meta["behavior_session_id"] = coerced if coerced is not None else decoded
    session_type = (
        metadata_attrs.get("session_type")
        or _nwb_attr_or_dataset(handle, "session_description")
    )
    if session_type is not None:
        meta["session_type"] = _decode_nwb_scalar(session_type)
    subject_id = _nwb_attr_or_dataset(handle, "general/subject/subject_id")
    if subject_id is not None:
        meta["subject_id"] = subject_id
    for attr in (
        "behavior_session_uuid",
        "equipment_name",
        "project_code",
        "stimulus_frame_rate",
    ):
        value = metadata_attrs.get(attr)
        if value is not None:
            meta[attr] = _decode_nwb_scalar(value)
    return meta


def _nwb_attr_or_dataset(handle: Any, path: str) -> Any:
    if path in handle:
        node = handle[path]
        if hasattr(node, "shape"):
            try:
                value = node[()]
            except Exception:
                return None
            return _decode_nwb_scalar(value)
    parts = path.rsplit("/", 1)
    if len(parts) == 2:
        parent_path, attr_name = parts
        parent_target = "/" if parent_path == "" else parent_path
        if parent_target in handle:
            parent = handle[parent_target]
            if attr_name in parent.attrs:
                return _decode_nwb_scalar(parent.attrs[attr_name])
    if path in handle.attrs:
        return _decode_nwb_scalar(handle.attrs[path])
    return None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _change_detection_outcome(
    *,
    is_hit: bool,
    is_miss: bool,
    is_false_alarm: bool,
    is_correct_reject: bool,
    is_aborted: bool,
    is_auto_rewarded: bool,
) -> str:
    if is_aborted:
        return "aborted"
    if is_auto_rewarded:
        return "auto_rewarded"
    if is_hit:
        return "hit"
    if is_miss:
        return "miss"
    if is_false_alarm:
        return "false_alarm"
    if is_correct_reject:
        return "correct_reject"
    return "unknown"


def _outcome_choice(outcome: str) -> str:
    if outcome in {"hit", "false_alarm"}:
        return "go"
    if outcome in {"miss", "correct_reject"}:
        return "withhold"
    if outcome == "auto_rewarded":
        return "go"
    if outcome == "aborted":
        return "no-response"
    return "unknown"


def _outcome_correct(outcome: str) -> bool | None:
    if outcome in {"hit", "correct_reject"}:
        return True
    if outcome in {"miss", "false_alarm"}:
        return False
    return None


def _outcome_feedback(outcome: str, *, reward_volume: Any) -> str:
    if outcome == "hit":
        return "reward"
    if outcome == "auto_rewarded":
        volume = _finite_or_none(reward_volume)
        return "reward" if volume and volume > 0 else "none"
    return "none"


def _count_outcomes(trials: list[CanonicalTrial]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for trial in trials:
        outcome = str(trial.task_variables.get("outcome", "unknown"))
        counts[outcome] += 1
    return dict(counts)


def _image_pair_summary(trials: list[CanonicalTrial]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str | None, str | None], list[CanonicalTrial]] = defaultdict(list)
    for trial in trials:
        if trial.task_variables.get("outcome") not in {"hit", "miss"}:
            continue
        initial = trial.task_variables.get("initial_image_name")
        change = trial.task_variables.get("change_image_name")
        grouped[(initial, change)].append(trial)
    rows: list[dict[str, Any]] = []
    for (initial, change), group in sorted(
        grouped.items(), key=lambda item: ((item[0][0] or ""), (item[0][1] or ""))
    ):
        n_hit = sum(1 for trial in group if trial.task_variables.get("outcome") == "hit")
        n_miss = sum(1 for trial in group if trial.task_variables.get("outcome") == "miss")
        latencies = [
            trial.response_time
            for trial in group
            if trial.response_time is not None
            and trial.task_variables.get("outcome") == "hit"
        ]
        rows.append(
            {
                "initial_image": initial,
                "change_image": change,
                "n_trials": len(group),
                "n_hit": n_hit,
                "n_miss": n_miss,
                "hit_rate": _safe_ratio(n_hit, n_hit + n_miss),
                "median_response_latency": (
                    statistics.median(latencies) if latencies else None
                ),
            }
        )
    return rows


def _d_prime(*, n_hit: int, n_go: int, n_false_alarm: int, n_catch: int) -> float | None:
    if n_go <= 0 or n_catch <= 0:
        return None
    hit_rate = (n_hit + 0.5) / (n_go + 1.0)
    false_alarm_rate = (n_false_alarm + 0.5) / (n_catch + 1.0)
    return _z_score(hit_rate) - _z_score(false_alarm_rate)


def _z_score(p: float) -> float:
    p = max(min(p, 1.0 - 1e-9), 1e-9)
    return math.sqrt(2.0) * _erfinv(2.0 * p - 1.0)


def _erfinv(x: float) -> float:
    a = 0.147
    sign = 1.0 if x >= 0 else -1.0
    ln = math.log(max(1.0 - x * x, 1e-30))
    first = 2.0 / (math.pi * a) + ln / 2.0
    inner = first * first - ln / a
    return sign * math.sqrt(math.sqrt(inner) - first)


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    return text


def _truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        if isinstance(value, float) and not math.isfinite(value):
            return False
        return value != 0
    text = str(value).strip().lower()
    return text in {"true", "1", "yes"}


def _lick_count(value: Any) -> int:
    if value is None:
        return 0
    if hasattr(value, "__len__"):
        try:
            return int(len(value))
        except TypeError:
            return 0
    return 0


def _image_pair_label(initial: str | None, change: str | None) -> str:
    if initial is None and change is None:
        return "unknown"
    return f"{initial or 'unknown'}->{change or 'unknown'}"


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | str):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            return str(value)
    if hasattr(value, "__iter__"):
        try:
            return [_json_safe_value(item) for item in value]
        except TypeError:
            return str(value)
    return str(value)


def _format_rate(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{numeric:.3f}"


def _format_number(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{numeric:.3f}"


def _html_definition_list(rows: list[tuple[str, Any]]) -> str:
    items = []
    for label, value in rows:
        if value is None:
            shown = "n/a"
        else:
            shown = escape(str(value))
        items.append(f"<dt>{escape(label)}</dt><dd>{shown}</dd>")
    return "<dl>" + "".join(items) + "</dl>"


def _html_table(rows: list[dict[str, Any]], *, columns: list[tuple[str, str]]) -> str:
    head = "".join(f"<th>{escape(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row.get(key)
            if value is None:
                cells.append("<td>n/a</td>")
            elif isinstance(value, float):
                cells.append(f"<td>{value:.3f}</td>")
            else:
                cells.append(f"<td>{escape(str(value))}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def _report_css() -> str:
    return (
        "body{font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif;"
        "max-width:920px;margin:24px auto;padding:0 16px;color:#111;line-height:1.5}"
        "h1{margin-top:0}"
        "h2{margin-top:32px;border-bottom:1px solid #ccc;padding-bottom:4px}"
        "table{border-collapse:collapse;margin:8px 0}"
        "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;font-size:13px}"
        "dl{display:grid;grid-template-columns:max-content 1fr;column-gap:12px;row-gap:2px}"
        "dt{font-weight:600}"
        "img{max-width:100%}"
    )
