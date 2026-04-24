from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any


def build_static_index_payload(*, derived_dir: Path, index_path: Path) -> dict[str, Any]:
    from behavtaskatlas.ibl import DEFAULT_IBL_EID, current_git_commit, current_git_dirty

    return {
        "title": "behavtaskatlas MVP Reports",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "derived_dir": str(derived_dir),
        "slices": [
            _auditory_clicks_slice_payload(derived_dir=derived_dir, index_path=index_path),
            _ibl_visual_slice_payload(
                derived_dir=derived_dir,
                index_path=index_path,
                default_eid=DEFAULT_IBL_EID,
            ),
        ],
    }


def write_static_index_html(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(static_index_html(payload), encoding="utf-8")


def static_index_html(payload: dict[str, Any]) -> str:
    slices = payload.get("slices", [])
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(str(payload.get('title', 'behavtaskatlas')))}</title>",
        "<style>",
        _index_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        '<p class="eyebrow">behavtaskatlas</p>',
        f"<h1>{escape(str(payload.get('title', 'MVP Reports')))}</h1>",
        "<p class=\"lede\">Static entry point for locally generated vertical-slice "
        "reports and analysis artifacts. Raw data and derived outputs remain outside git; "
        "this page is regenerated from reproducible local artifacts.</p>",
        "</header>",
        '<section class="summary" aria-label="Index summary">',
        _metric("Slices", len(slices)),
        _metric(
            "Reports available",
            sum(1 for item in slices if item.get("report_status") == "available"),
        ),
        _metric(
            "Analysis artifacts",
            sum(1 for item in slices if item.get("artifact_status") == "available"),
        ),
        _metric("Commit", payload.get("behavtaskatlas_commit") or ""),
        "</section>",
        "<section>",
        "<h2>Vertical Slices</h2>",
        '<div class="cards">',
    ]
    for item in slices:
        html.append(_slice_card(item))
    html.extend(
        [
            "</div>",
            "</section>",
            "<section>",
            "<h2>Build Provenance</h2>",
            _definition_list(
                [
                    ("Generated", payload.get("generated_at")),
                    ("Commit", payload.get("behavtaskatlas_commit")),
                    ("Git dirty", payload.get("behavtaskatlas_git_dirty")),
                    ("Derived root", payload.get("derived_dir")),
                ]
            ),
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(html) + "\n"


def _auditory_clicks_slice_payload(*, derived_dir: Path, index_path: Path) -> dict[str, Any]:
    slice_dir = derived_dir / "auditory_clicks"
    aggregate_result_path = slice_dir / "aggregate_result.json"
    report_path = slice_dir / "report.html"
    aggregate = _read_json_object(aggregate_result_path)
    metrics = []
    if aggregate:
        metrics = [
            ("Rats", aggregate.get("n_ok")),
            ("Trials", aggregate.get("n_trials_total")),
            ("Psychometric rows", len(aggregate.get("psychometric_bias_rows", []))),
            ("Kernel bins", len(aggregate.get("kernel_summary_rows", []))),
        ]
    return {
        "id": "slice.auditory-clicks",
        "title": "Auditory Clicks Evidence Accumulation",
        "status_label": "Report available" if report_path.exists() else "Report pending",
        "report_status": "available" if report_path.exists() else "missing",
        "artifact_status": "available" if aggregate_result_path.exists() else "missing",
        "description": (
            "Brody Lab Poisson clicks slice with real local batch processing, per-rat "
            "psychometrics, and aggregate click-time evidence kernel."
        ),
        "primary_link": _link_if_exists(report_path, index_path),
        "primary_link_label": "Open report",
        "metrics": metrics,
        "links": _existing_links(
            [
                ("Report HTML", report_path),
                ("Aggregate result JSON", aggregate_result_path),
                ("Aggregate kernel SVG", slice_dir / "aggregate_kernel.svg"),
                ("Batch summary CSV", slice_dir / "batch_summary.csv"),
                ("Slice notes", Path("vertical_slices/auditory_clicks/README.md")),
                ("Analysis record", Path("analyses/auditory_clicks.yaml")),
            ],
            index_path=index_path,
        ),
    }


def _ibl_visual_slice_payload(
    *,
    derived_dir: Path,
    index_path: Path,
    default_eid: str,
) -> dict[str, Any]:
    slice_dir = derived_dir / "ibl_visual_decision"
    session_dir = slice_dir / default_eid
    if not session_dir.exists():
        session_dirs = sorted(path for path in slice_dir.glob("*") if path.is_dir())
        if session_dirs:
            session_dir = session_dirs[0]
    analysis_path = session_dir / "analysis_result.json"
    analysis = _read_json_object(analysis_path)
    metrics = []
    if analysis:
        metrics = [
            ("Trials", analysis.get("n_trials")),
            ("Response trials", analysis.get("n_response_trials")),
            ("No-response trials", analysis.get("n_no_response_trials")),
            ("Prior blocks", len(analysis.get("prior_results", []))),
        ]
    return {
        "id": "slice.ibl-visual-decision",
        "title": "IBL Visual Decision",
        "status_label": "Report pending" if analysis_path.exists() else "Analysis pending",
        "report_status": "missing",
        "artifact_status": "available" if analysis_path.exists() else "missing",
        "description": (
            "First visual 2AFC slice with OpenAlyx provenance, canonical trials, "
            "and fitted descriptive psychometrics for one public IBL session."
        ),
        "primary_link": _link_if_exists(session_dir / "psychometric.svg", index_path),
        "primary_link_label": "Open psychometric SVG",
        "metrics": metrics,
        "links": _existing_links(
            [
                ("Analysis result JSON", analysis_path),
                ("Psychometric SVG", session_dir / "psychometric.svg"),
                ("Canonical trials CSV", session_dir / "trials.csv"),
                ("Slice notes", Path("vertical_slices/ibl_visual_decision/README.md")),
                ("Analysis record", Path("analyses/ibl_visual_decision.yaml")),
            ],
            index_path=index_path,
        ),
    }


def _slice_card(item: dict[str, Any]) -> str:
    classes = ["card"]
    if item.get("report_status") == "available":
        classes.append("available")
    primary_link = item.get("primary_link")
    parts = [
        f'<article class="{" ".join(classes)}">',
        '<div class="card-header">',
        f"<h3>{escape(str(item.get('title', 'Untitled slice')))}</h3>",
        f"<span>{escape(str(item.get('status_label', 'Unknown')))}</span>",
        "</div>",
        f"<p>{escape(str(item.get('description', '')))}</p>",
        '<div class="metric-grid">',
    ]
    for label, value in item.get("metrics", []):
        parts.append(_small_metric(label, value))
    parts.append("</div>")
    if primary_link:
        parts.append(
            f'<p><a class="primary" href="{escape(primary_link, quote=True)}">'
            f"{escape(str(item.get('primary_link_label', 'Open')))}</a></p>"
        )
    links = item.get("links", [])
    if links:
        parts.extend(["<ul>"])
        for link in links:
            parts.append(
                f'<li><a href="{escape(link["href"], quote=True)}">'
                f'{escape(link["label"])}</a></li>'
            )
        parts.append("</ul>")
    parts.append("</article>")
    return "\n".join(parts)


def _index_css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #16202a;
  --muted: #63717d;
  --line: #d8dee4;
  --panel: #f6f8fa;
  --accent: #145f91;
  --good: #237a57;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  color: var(--ink);
  background: #ffffff;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  line-height: 1.45;
}
main {
  width: min(1160px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 34px 0 52px;
}
header {
  padding-bottom: 24px;
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
  font-size: clamp(2.1rem, 5vw, 3.5rem);
  line-height: 1.03;
}
h2 {
  margin: 0 0 14px;
  font-size: 1.18rem;
}
h3 {
  margin: 0;
  font-size: 1.08rem;
}
.lede {
  max-width: 780px;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 1.05rem;
}
section {
  margin-top: 28px;
}
.summary,
.cards {
  display: grid;
  gap: 12px;
}
.summary {
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}
.cards {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}
.metric,
.card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
}
.metric {
  padding: 14px;
}
.metric span,
.small-metric span {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
  text-transform: uppercase;
}
.metric strong {
  display: block;
  margin-top: 4px;
  font-size: 1.42rem;
}
.card {
  padding: 18px;
}
.card.available {
  border-color: #b9d7c9;
}
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.card-header span {
  flex: 0 0 auto;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 8px;
  background: #ffffff;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
}
.available .card-header span {
  border-color: #b9d7c9;
  color: var(--good);
}
.card p {
  margin: 12px 0;
  color: var(--muted);
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 8px;
  margin-top: 14px;
}
.small-metric {
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 9px;
  background: #ffffff;
}
.small-metric strong {
  display: block;
  margin-top: 3px;
  font-size: 1.08rem;
}
a {
  color: var(--accent);
}
a.primary {
  font-weight: 800;
}
ul {
  margin: 12px 0 0;
  padding-left: 18px;
}
dl {
  display: grid;
  grid-template-columns: minmax(120px, 0.25fr) 1fr;
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
@media (max-width: 700px) {
  main {
    width: min(100vw - 20px, 1160px);
    padding-top: 22px;
  }
  .cards {
    grid-template-columns: 1fr;
  }
  .card-header {
    display: block;
  }
  .card-header span {
    display: inline-block;
    margin-top: 8px;
  }
  dl {
    grid-template-columns: 1fr;
  }
}
""".strip()


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(_format_cell(value))}</strong>"
        "</div>"
    )


def _small_metric(label: str, value: Any) -> str:
    return (
        '<div class="small-metric">'
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


def _existing_links(
    links: list[tuple[str, Path]],
    *,
    index_path: Path,
) -> list[dict[str, str]]:
    return [
        {
            "label": label,
            "href": _relative_link(path, index_path),
        }
        for label, path in links
        if path.exists()
    ]


def _link_if_exists(path: Path, index_path: Path) -> str | None:
    if not path.exists():
        return None
    return _relative_link(path, index_path)


def _relative_link(path: Path, index_path: Path) -> str:
    return os.path.relpath(path, index_path.parent).replace(os.sep, "/")


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:.4g}"
    return str(value)
