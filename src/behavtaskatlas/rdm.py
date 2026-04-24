from __future__ import annotations

import csv
import hashlib
import math
import statistics
import urllib.request
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
RDM_CHRONOMETRIC_FIELDS = [
    "evidence_strength",
    "n_trials",
    "n_response",
    "n_correct",
    "p_correct",
    "median_response_time",
    "mean_response_time",
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
    title = "Random-Dot Motion Report"
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
        "<p class=\"lede\">Roitman-Shadlen random-dot motion slice generated from "
        "the processed PyDDM trial table, with target-coded psychometric and "
        "chronometric summaries.</p>",
        "</header>",
        '<section class="metrics" aria-label="Report metrics">',
        _metric("Trials", analysis_result.get("n_trials")),
        _metric("Response trials", analysis_result.get("n_response_trials")),
        _metric("Subjects", len(source.get("monkeys", []))),
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
                ("PyDDM commit", source.get("source_repository_commit")),
                ("Source file hash", source.get("source_file_sha256")),
                ("Subjects", ", ".join(source.get("monkeys", []))),
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
                ("Response time", "saccade time minus stimulus onset"),
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
