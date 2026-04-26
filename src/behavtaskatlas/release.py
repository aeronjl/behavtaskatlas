from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from behavtaskatlas.ibl import current_git_commit, current_git_dirty
from behavtaskatlas.models import (
    CatalogPayload,
    CurationQueuePayload,
    Dataset,
    Protocol,
    RelationshipGraphPayload,
    ReleaseCheckPayload,
    ReportManifest,
    TaskFamily,
    VerticalSlice,
)
from behavtaskatlas.static_site import load_vertical_slice_records
from behavtaskatlas.validation import validate_repository

STATUS_ORDER = {"ok": 0, "warning": 1, "error": 2}


def build_release_check_payload(
    *,
    root: Path = Path("."),
    derived_dir: Path = Path("derived"),
) -> dict[str, Any]:
    root = root.resolve()
    derived_root = _resolve_under_root(root, derived_dir)
    commit = current_git_commit()
    git_dirty = current_git_dirty()
    items: list[dict[str, Any]] = []

    validation_report = validate_repository(root)
    if validation_report.ok:
        items.append(
            _item(
                "repository.validation",
                "Repository validation",
                "ok",
                f"Validated {len(validation_report.records)} committed records.",
            )
        )
    else:
        items.append(
            _item(
                "repository.validation",
                "Repository validation",
                "error",
                f"{len(validation_report.issues)} validation issue(s) found.",
                details={
                    "issues": [
                        {
                            "path": _display_path(issue.path, root),
                            "message": issue.message,
                        }
                        for issue in validation_report.issues
                    ]
                },
            )
        )

    items.append(_worktree_item(git_dirty))
    items.append(_source_data_level_item(validation_report.records, root))

    loaded_artifacts: dict[str, BaseModel] = {}
    for artifact_id, file_name, model in _static_artifact_specs():
        path = derived_root / file_name
        item, payload = _static_artifact_item(
            artifact_id=artifact_id,
            path=path,
            root=root,
            model=model,
            expected_commit=commit,
        )
        items.append(item)
        if payload is not None:
            loaded_artifacts[artifact_id] = payload

    manifest = loaded_artifacts.get("manifest")
    if isinstance(manifest, ReportManifest):
        items.append(_slice_coverage_item(manifest))
        items.append(_health_source_level_item(manifest))

    queue = loaded_artifacts.get("curation_queue")
    if isinstance(queue, CurationQueuePayload):
        items.append(_queue_item(queue))

    if loaded_artifacts:
        items.append(_raw_path_item(loaded_artifacts, root))
        items.append(
            _slice_provenance_item(
                root=root,
                derived_root=derived_root,
                expected_commit=commit,
            )
        )

    overall_status = _overall_status(items)
    counts = _release_counts(
        records=validation_report.records,
        manifest=manifest if isinstance(manifest, ReportManifest) else None,
        items=items,
    )
    payload = {
        "release_check_schema_version": "0.1.0",
        "title": "behavtaskatlas Release Check",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": commit,
        "behavtaskatlas_git_dirty": git_dirty,
        "root": str(root),
        "derived_dir": _display_path(derived_root, root),
        "overall_status": overall_status,
        "counts": counts,
        "items": items,
    }
    ReleaseCheckPayload.model_validate(payload)
    return payload


def write_release_check_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ReleaseCheckPayload.model_validate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_release_check_html(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(release_check_html(payload), encoding="utf-8")


def release_check_html(payload: dict[str, Any]) -> str:
    items = payload.get("items", [])
    counts = payload.get("counts", {})
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(str(payload.get('title', 'Release Check')))}</title>",
        "<style>",
        _release_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        '<p class="eyebrow">behavtaskatlas release</p>',
        f"<h1>{escape(str(payload.get('title', 'Release Check')))}</h1>",
        "<p class=\"lede\">Static release-readiness checks for committed catalog "
        "records and generated publishable artifacts.</p>",
        "</header>",
        '<section class="summary" aria-label="Release summary">',
        _metric("Overall", payload.get("overall_status")),
        _metric("Errors", counts.get("errors", 0)),
        _metric("Warnings", counts.get("warnings", 0)),
        _metric("Slices", counts.get("vertical_slices", 0)),
        _metric("Reports", counts.get("reports_available", 0)),
        _metric("Commit", payload.get("behavtaskatlas_commit") or ""),
        "</section>",
        "<section>",
        "<h2>Checks</h2>",
        _check_table(items),
        "</section>",
        "<section>",
        "<h2>Build Provenance</h2>",
        _definition_list(
            [
                ("Generated", payload.get("generated_at")),
                ("Commit", payload.get("behavtaskatlas_commit")),
                ("Git dirty", payload.get("behavtaskatlas_git_dirty")),
                ("Root", payload.get("root")),
                ("Derived root", payload.get("derived_dir")),
            ]
        ),
        "</section>",
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html) + "\n"


def _static_artifact_specs() -> tuple[tuple[str, str, type[BaseModel]], ...]:
    return (
        ("manifest", "manifest.json", ReportManifest),
        ("catalog", "catalog.json", CatalogPayload),
        ("relationship_graph", "graph.json", RelationshipGraphPayload),
        ("curation_queue", "curation_queue.json", CurationQueuePayload),
    )


def _static_artifact_item(
    *,
    artifact_id: str,
    path: Path,
    root: Path,
    model: type[BaseModel],
    expected_commit: str | None,
) -> tuple[dict[str, Any], BaseModel | None]:
    if not path.exists():
        return (
            _item(
                f"static.{artifact_id}",
                f"{artifact_id.replace('_', ' ').title()} JSON",
                "error",
                "Generated static JSON is missing.",
                path=_display_path(path, root),
            ),
            None,
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        payload = model.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        return (
            _item(
                f"static.{artifact_id}",
                f"{artifact_id.replace('_', ' ').title()} JSON",
                "error",
                f"Generated static JSON is not valid: {exc}",
                path=_display_path(path, root),
            ),
            None,
        )

    artifact_commit = getattr(payload, "behavtaskatlas_commit", None)
    artifact_dirty = getattr(payload, "behavtaskatlas_git_dirty", None)
    details = {
        "commit": artifact_commit,
        "git_dirty": artifact_dirty,
        "expected_commit": expected_commit,
    }
    if expected_commit and artifact_commit != expected_commit:
        return (
            _item(
                f"static.{artifact_id}",
                f"{artifact_id.replace('_', ' ').title()} JSON",
                "error",
                "Generated static JSON does not match the current commit.",
                path=_display_path(path, root),
                details=details,
            ),
            payload,
        )
    if artifact_dirty is not False:
        return (
            _item(
                f"static.{artifact_id}",
                f"{artifact_id.replace('_', ' ').title()} JSON",
                "error",
                "Generated static JSON was not produced from a clean worktree.",
                path=_display_path(path, root),
                details=details,
            ),
            payload,
        )
    return (
        _item(
            f"static.{artifact_id}",
            f"{artifact_id.replace('_', ' ').title()} JSON",
            "ok",
            "Generated static JSON validates and matches the clean current commit.",
            path=_display_path(path, root),
            details=details,
        ),
        payload,
    )


def _worktree_item(git_dirty: bool | None) -> dict[str, Any]:
    if git_dirty is False:
        return _item("repository.worktree", "Current worktree", "ok", "Worktree is clean.")
    if git_dirty is True:
        return _item(
            "repository.worktree",
            "Current worktree",
            "warning",
            "Worktree has uncommitted source changes; static artifact provenance "
            "is checked separately.",
        )
    return _item(
        "repository.worktree",
        "Current worktree",
        "warning",
        "Git worktree state could not be determined.",
    )


def _source_data_level_item(records: list[BaseModel], root: Path) -> dict[str, Any]:
    datasets = [record for record in records if isinstance(record, Dataset)]
    slices = [record for record in records if isinstance(record, VerticalSlice)]
    missing_datasets = [record.id for record in datasets if not record.source_data_level]
    missing_slices = [
        record.id for record in slices if not record.comparison.source_data_level
    ]
    details = {
        "datasets": len(datasets),
        "vertical_slices": len(slices),
        "missing_datasets": missing_datasets,
        "missing_vertical_slices": missing_slices,
    }
    if missing_datasets or missing_slices:
        return _item(
            "metadata.source_data_level",
            "Source data level metadata",
            "error",
            "Some datasets or vertical slices are missing source_data_level metadata.",
            path=_display_path(root / "vocabularies" / "core.yaml", root),
            details=details,
        )
    return _item(
        "metadata.source_data_level",
        "Source data level metadata",
        "ok",
        "All datasets and vertical slices expose source_data_level metadata.",
        path=_display_path(root / "vocabularies" / "core.yaml", root),
        details=details,
    )


def _slice_coverage_item(manifest: ReportManifest) -> dict[str, Any]:
    slices = manifest.slices
    missing_reports = [item.id for item in slices if item.report_status != "available"]
    missing_artifacts = [item.id for item in slices if item.artifact_status != "available"]
    details = {
        "slices": len(slices),
        "missing_reports": missing_reports,
        "missing_artifacts": missing_artifacts,
    }
    if missing_reports or missing_artifacts:
        return _item(
            "release.slice_coverage",
            "Slice report coverage",
            "error",
            "One or more vertical slices lack a generated report or analysis artifact.",
            details=details,
        )
    return _item(
        "release.slice_coverage",
        "Slice report coverage",
        "ok",
        f"All {len(slices)} vertical slices have generated reports and analysis artifacts.",
        details=details,
    )


def _health_source_level_item(manifest: ReportManifest) -> dict[str, Any]:
    counts = manifest.health.get("source_data_level_counts", {})
    if not counts:
        return _item(
            "release.health_source_levels",
            "Health source-level summary",
            "warning",
            "Manifest health payload does not include source data level counts.",
        )
    return _item(
        "release.health_source_levels",
        "Health source-level summary",
        "ok",
        "Manifest health payload includes source data level counts.",
        details={"source_data_level_counts": counts},
    )


def _queue_item(queue: CurationQueuePayload) -> dict[str, Any]:
    open_count = int(queue.counts.get("open", 0))
    details = {
        "items": int(queue.counts.get("items", len(queue.items))),
        "open": open_count,
        "action_counts": queue.action_counts,
        "priority_counts": queue.priority_counts,
    }
    if open_count:
        return _item(
            "release.curation_queue",
            "Curation queue",
            "error",
            f"Curation queue has {open_count} open item(s).",
            details=details,
        )
    return _item(
        "release.curation_queue",
        "Curation queue",
        "ok",
        "Curation queue has no open items.",
        details=details,
    )


def _raw_path_item(loaded_artifacts: dict[str, BaseModel], root: Path) -> dict[str, Any]:
    references: list[dict[str, str]] = []
    for artifact_id, payload in loaded_artifacts.items():
        data = payload.model_dump(mode="json")
        for pointer, value in _iter_string_values(data):
            if _looks_like_raw_path(value):
                references.append(
                    {
                        "artifact": artifact_id,
                        "pointer": pointer,
                        "value": value,
                    }
                )
    if references:
        return _item(
            "release.raw_path_links",
            "Raw data path exposure",
            "error",
            "Generated static payloads expose raw-data paths.",
            path=_display_path(root / "data" / "raw", root),
            details={"references": references},
        )
    return _item(
        "release.raw_path_links",
        "Raw data path exposure",
        "ok",
        "Generated static payloads do not expose local data/raw paths.",
        path=_display_path(root / "data" / "raw", root),
    )


def _slice_provenance_item(
    *,
    root: Path,
    derived_root: Path,
    expected_commit: str | None,
) -> dict[str, Any]:
    try:
        slices = load_vertical_slice_records(root)
    except ValueError as exc:
        return _item(
            "release.slice_provenance",
            "Slice artifact provenance",
            "warning",
            f"Could not inspect slice provenance: {exc}",
        )

    warnings: list[dict[str, str | None]] = []
    checked = 0
    for record in slices:
        analysis_path = derived_root / record.analysis_result_path
        provenance_path = analysis_path.parent / "provenance.json"
        if not provenance_path.exists():
            warnings.append(
                {
                    "slice_id": record.id,
                    "path": _display_path(provenance_path, root),
                    "reason": "missing provenance.json",
                }
            )
            continue
        checked += 1
        warning = _provenance_warning(
            slice_id=record.id,
            path=provenance_path,
            root=root,
            expected_commit=expected_commit,
        )
        if warning:
            warnings.append(warning)

    details = {
        "checked": checked,
        "warnings": warnings,
    }
    if warnings:
        return _item(
            "release.slice_provenance",
            "Slice artifact provenance",
            "warning",
            "Some per-slice provenance files are missing, dirty, stale, or unreadable.",
            details=details,
        )
    return _item(
        "release.slice_provenance",
        "Slice artifact provenance",
        "ok",
        f"Checked {checked} per-slice provenance file(s).",
        details=details,
    )


def _provenance_warning(
    *,
    slice_id: str,
    path: Path,
    root: Path,
    expected_commit: str | None,
) -> dict[str, str | None] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "slice_id": slice_id,
            "path": _display_path(path, root),
            "reason": f"unreadable provenance JSON: {exc}",
        }
    commit = data.get("behavtaskatlas_commit")
    dirty = data.get("behavtaskatlas_git_dirty")
    if expected_commit and commit != expected_commit:
        return {
            "slice_id": slice_id,
            "path": _display_path(path, root),
            "reason": "commit mismatch",
            "commit": str(commit) if commit is not None else None,
            "expected_commit": expected_commit,
        }
    if dirty is not False:
        return {
            "slice_id": slice_id,
            "path": _display_path(path, root),
            "reason": "dirty or missing git status",
            "git_dirty": str(dirty),
        }
    return None


def _release_counts(
    *,
    records: list[BaseModel],
    manifest: ReportManifest | None,
    items: list[dict[str, Any]],
) -> dict[str, int]:
    counts = {
        "records": len(records),
        "task_families": sum(isinstance(record, TaskFamily) for record in records),
        "protocols": sum(isinstance(record, Protocol) for record in records),
        "datasets": sum(isinstance(record, Dataset) for record in records),
        "vertical_slices": sum(isinstance(record, VerticalSlice) for record in records),
        "checks": len(items),
        "errors": sum(item["status"] == "error" for item in items),
        "warnings": sum(item["status"] == "warning" for item in items),
    }
    if manifest is not None:
        counts["vertical_slices"] = len(manifest.slices)
        counts["reports_available"] = sum(
            item.report_status == "available" for item in manifest.slices
        )
        counts["artifacts_available"] = sum(
            item.artifact_status == "available" for item in manifest.slices
        )
    return counts


def _overall_status(items: list[dict[str, Any]]) -> str:
    if any(item["status"] == "error" for item in items):
        return "error"
    if any(item["status"] == "warning" for item in items):
        return "warning"
    return "ok"


def _item(
    check_id: str,
    label: str,
    status: str,
    message: str,
    *,
    path: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "label": label,
        "status": status,
        "message": message,
        "path": path,
        "details": details or {},
    }


def _iter_string_values(value: Any, pointer: str = "$") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(pointer, value)]
    if isinstance(value, list):
        results = []
        for index, item in enumerate(value):
            results.extend(_iter_string_values(item, f"{pointer}[{index}]"))
        return results
    if isinstance(value, dict):
        results = []
        for key, item in value.items():
            results.extend(_iter_string_values(item, f"{pointer}.{key}"))
        return results
    return []


def _looks_like_raw_path(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return (
        normalized == "data/raw"
        or normalized.startswith("data/raw/")
        or "/data/raw/" in normalized
        or normalized.startswith("../data/raw/")
    )


def _resolve_under_root(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _check_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">No release checks were run.</p>'
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for label in ["Status", "Check", "Message", "Path"]:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for item in sorted(items, key=lambda row: (-STATUS_ORDER[row["status"]], row["check_id"])):
        status = str(item.get("status", ""))
        parts.append(f'<tr class="{escape(status, quote=True)}">')
        parts.append(f"<td>{escape(status)}</td>")
        parts.append(f"<td>{escape(str(item.get('label') or item.get('check_id') or ''))}</td>")
        parts.append(f"<td>{escape(str(item.get('message') or ''))}</td>")
        parts.append(f"<td>{escape(str(item.get('path') or ''))}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(_format_value(value))}</strong>"
        "</div>"
    )


def _definition_list(rows: list[tuple[str, Any]]) -> str:
    parts = ["<dl>"]
    for label, value in rows:
        parts.append(f"<dt>{escape(label)}</dt>")
        parts.append(f"<dd>{escape(_format_value(value))}</dd>")
    parts.append("</dl>")
    return "\n".join(parts)


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _release_css() -> str:
    return """
:root {
  color-scheme: light;
  --ink: #16202a;
  --muted: #63717d;
  --line: #d8dee4;
  --panel: #f6f8fa;
  --accent: #145f91;
  --good: #237a57;
  --warn: #91640b;
  --bad: #a83232;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  color: var(--ink);
  background: #fff;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  line-height: 1.45;
}
main {
  width: min(1120px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 48px 0 64px;
}
header {
  margin-bottom: 28px;
}
h1,
h2 {
  margin: 0 0 12px;
  line-height: 1.12;
}
h1 {
  font-size: 42px;
}
h2 {
  font-size: 24px;
}
.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 13px;
}
.lede {
  max-width: 760px;
  color: var(--muted);
  font-size: 18px;
}
section {
  margin-top: 32px;
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
.metric {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 8px;
  padding: 14px;
}
.metric span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.metric strong {
  display: block;
  margin-top: 6px;
  font-size: 22px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  border-bottom: 1px solid var(--line);
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
tr.ok td:first-child {
  color: var(--good);
  font-weight: 700;
}
tr.warning td:first-child {
  color: var(--warn);
  font-weight: 700;
}
tr.error td:first-child {
  color: var(--bad);
  font-weight: 700;
}
dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 8px 16px;
}
dt {
  color: var(--muted);
  font-weight: 700;
}
dd {
  margin: 0;
}
@media (max-width: 640px) {
  h1 {
    font-size: 32px;
  }
  dl {
    grid-template-columns: 1fr;
  }
}
"""
