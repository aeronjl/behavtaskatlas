from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from behavtaskatlas.models import ReportManifest, VerticalSlice
from behavtaskatlas.validation import load_yaml


def build_static_index_payload(
    *,
    derived_dir: Path,
    index_path: Path,
    manifest_path: Path | None = None,
    root: Path = Path("."),
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    manifest_path = manifest_path or index_path.with_name("manifest.json")
    records = load_vertical_slice_records(root)
    slices = [
        _vertical_slice_payload(
            record,
            derived_dir=derived_dir,
            index_path=index_path,
            root=root,
        )
        for record in records
    ]
    return {
        "manifest_schema_version": "0.1.0",
        "title": "behavtaskatlas MVP Reports",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "derived_dir": str(derived_dir),
        "manifest_link": _relative_link(manifest_path, index_path),
        "comparison_rows": build_slice_comparison_rows(slices),
        "slices": slices,
    }


def write_static_index_html(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(static_index_html(payload), encoding="utf-8")


def write_static_manifest_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ReportManifest.model_validate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_vertical_slice_records(root: Path = Path(".")) -> list[VerticalSlice]:
    records = []
    for path in sorted((root / "vertical_slices").glob("*/slice.yaml")):
        try:
            records.append(VerticalSlice.model_validate(load_yaml(path)))
        except (OSError, ValueError, ValidationError) as exc:
            raise ValueError(f"Invalid vertical slice record {path}: {exc}") from exc
    return sorted(records, key=lambda record: (record.display_order, record.id))


def build_slice_comparison_rows(slices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in slices:
        comparison = item.get("comparison", {})
        metrics = {metric["label"]: metric.get("value") for metric in item.get("metrics", [])}
        rows.append(
            {
                "slice_id": item.get("id"),
                "title": item.get("title"),
                "family_id": item.get("family_id"),
                "protocol_id": item.get("protocol_id"),
                "dataset_id": item.get("dataset_id"),
                "species": comparison.get("species"),
                "modality": comparison.get("modality"),
                "stimulus_metric": comparison.get("stimulus_metric"),
                "evidence_type": comparison.get("evidence_type"),
                "choice_type": comparison.get("choice_type"),
                "response_modality": comparison.get("response_modality"),
                "analysis_outputs": comparison.get("analysis_outputs"),
                "data_scope": comparison.get("data_scope"),
                "canonical_axis": comparison.get("canonical_axis"),
                "report_status": item.get("report_status"),
                "artifact_status": item.get("artifact_status"),
                "primary_link": item.get("primary_link"),
                "trial_count": _first_present_metric(
                    metrics,
                    ["Trials", "Parsed trials"],
                    fallback=comparison.get("trial_count"),
                ),
            }
        )
    return rows


def static_index_html(payload: dict[str, Any]) -> str:
    slices = payload.get("slices", [])
    comparison_rows = payload.get("comparison_rows") or build_slice_comparison_rows(slices)
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
    ]
    manifest_link = payload.get("manifest_link")
    if manifest_link:
        html.append(
            f'<p class="manifest-link"><a href="{escape(str(manifest_link), quote=True)}">'
            "Machine-readable manifest JSON</a></p>"
        )
    html.extend(
        [
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
            "<h2>Atlas Comparison</h2>",
            _comparison_table(comparison_rows),
            "</section>",
            "<section>",
            "<h2>Vertical Slices</h2>",
            '<div class="cards">',
        ]
    )
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


def _vertical_slice_payload(
    record: VerticalSlice,
    *,
    derived_dir: Path,
    index_path: Path,
    root: Path,
) -> dict[str, Any]:
    report_path = derived_dir / record.report_path
    analysis_path = derived_dir / record.analysis_result_path
    primary_artifact_path = (
        derived_dir / record.primary_artifact_path if record.primary_artifact_path else None
    )
    analysis = _read_json_object(analysis_path)
    primary_link = _link_if_exists(report_path, index_path)
    if primary_link is None and primary_artifact_path is not None:
        primary_link = _link_if_exists(primary_artifact_path, index_path)
    return {
        "id": record.id,
        "title": record.title,
        "family_id": record.family_id,
        "protocol_id": record.protocol_id,
        "dataset_id": record.dataset_id,
        "status_label": _report_status_label(
            report_path=report_path,
            artifact_path=analysis_path,
        ),
        "report_status": "available" if report_path.exists() else "missing",
        "artifact_status": "available" if analysis_path.exists() else "missing",
        "description": record.description.strip(),
        "primary_link": primary_link,
        "primary_link_label": "Open report"
        if report_path.exists()
        else record.primary_artifact_label or "Open artifact",
        "metrics": _slice_metrics(record.id, analysis),
        "links": _slice_links(record, derived_dir=derived_dir, index_path=index_path, root=root),
        "comparison": record.comparison.model_dump(),
    }


def _slice_metrics(slice_id: str, analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
    if analysis is None:
        return []
    if slice_id == "slice.auditory-clicks":
        return [
            _metric_payload("Rats", analysis.get("n_ok")),
            _metric_payload("Trials", analysis.get("n_trials_total")),
            _metric_payload(
                "Psychometric rows",
                len(analysis.get("psychometric_bias_rows", [])),
            ),
            _metric_payload("Kernel bins", len(analysis.get("kernel_summary_rows", []))),
        ]
    if slice_id == "slice.ibl-visual-decision":
        return [
            _metric_payload("Trials", analysis.get("n_trials")),
            _metric_payload("Response trials", analysis.get("n_response_trials")),
            _metric_payload("No-response trials", analysis.get("n_no_response_trials")),
            _metric_payload("Prior blocks", len(analysis.get("prior_results", []))),
        ]
    if slice_id == "slice.random-dot-motion":
        return [
            _metric_payload("Trials", analysis.get("n_trials")),
            _metric_payload("Response trials", analysis.get("n_response_trials")),
            _metric_payload("Coherence levels", len(analysis.get("chronometric_rows", []))),
            _metric_payload("Summary rows", len(analysis.get("summary_rows", []))),
        ]
    return []


def _metric_payload(label: str, value: Any) -> dict[str, Any]:
    return {"label": label, "value": value}


def _slice_links(
    record: VerticalSlice,
    *,
    derived_dir: Path,
    index_path: Path,
    root: Path,
) -> list[dict[str, str]]:
    links = []
    for link in record.artifact_links:
        base = derived_dir if link.path_type == "derived" else root
        path = base / link.path
        if path.exists():
            links.append({"label": link.label, "href": _relative_link(path, index_path)})
    return links


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
    for metric in item.get("metrics", []):
        parts.append(_small_metric(metric["label"], metric.get("value")))
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


def _report_status_label(*, report_path: Path, artifact_path: Path) -> str:
    if report_path.exists():
        return "Report available"
    if artifact_path.exists():
        return "Report pending"
    return "Analysis pending"


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
.manifest-link {
  margin: 14px 0 0;
}
.manifest-link a {
  font-weight: 800;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}
table {
  width: 100%;
  min-width: 980px;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th,
td {
  padding: 10px 11px;
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


def _comparison_table(rows: list[dict[str, Any]]) -> str:
    return _html_table(
        rows,
        [
            ("title", "Slice"),
            ("species", "Species"),
            ("modality", "Modality"),
            ("stimulus_metric", "Stimulus metric"),
            ("evidence_type", "Evidence"),
            ("choice_type", "Choice"),
            ("response_modality", "Response"),
            ("trial_count", "Trials"),
            ("analysis_outputs", "Outputs"),
            ("canonical_axis", "Canonical axis"),
            ("report_status", "Report"),
        ],
    )


def _html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="empty">No comparison rows available.</p>'
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


def _definition_list(rows: list[tuple[str, Any]]) -> str:
    parts = ["<dl>"]
    for label, value in rows:
        parts.append(f"<dt>{escape(label)}</dt>")
        parts.append(f"<dd>{escape(_format_cell(value))}</dd>")
    parts.append("</dl>")
    return "\n".join(parts)


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


def _first_present_metric(
    metrics: dict[str, Any],
    labels: list[str],
    *,
    fallback: Any = None,
) -> Any:
    for label in labels:
        value = metrics.get(label)
        if value is not None:
            return value
    return fallback


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
