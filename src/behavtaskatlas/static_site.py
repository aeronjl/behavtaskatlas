from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from behavtaskatlas.models import (
    CatalogPayload,
    Dataset,
    Protocol,
    ReportManifest,
    TaskFamily,
    VerticalSlice,
    model_from_record,
)
from behavtaskatlas.validation import iter_record_paths, load_yaml


def build_static_index_payload(
    *,
    derived_dir: Path,
    index_path: Path,
    manifest_path: Path | None = None,
    catalog_path: Path | None = None,
    root: Path = Path("."),
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    manifest_path = manifest_path or index_path.with_name("manifest.json")
    catalog_path = catalog_path or index_path.with_name("catalog.html")
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
        "catalog_link": _relative_link(catalog_path, index_path),
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


def build_catalog_payload(
    *,
    root: Path,
    derived_dir: Path,
    catalog_path: Path,
    catalog_json_path: Path | None = None,
    report_index_path: Path | None = None,
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    catalog_json_path = catalog_json_path or catalog_path.with_suffix(".json")
    report_index_path = report_index_path or catalog_path.with_name("index.html")
    records = load_repository_records(root)
    task_families = sorted(
        [record for record in records if isinstance(record, TaskFamily)],
        key=lambda record: record.name,
    )
    protocols = sorted(
        [record for record in records if isinstance(record, Protocol)],
        key=lambda record: record.name,
    )
    datasets = sorted(
        [record for record in records if isinstance(record, Dataset)],
        key=lambda record: record.name,
    )
    vertical_slices = sorted(
        [record for record in records if isinstance(record, VerticalSlice)],
        key=lambda record: (record.display_order, record.title),
    )
    slice_payloads = {
        record.id: _vertical_slice_payload(
            record,
            derived_dir=derived_dir,
            index_path=catalog_path,
            root=root,
        )
        for record in vertical_slices
    }
    family_by_id = {record.id: record for record in task_families}
    datasets_by_protocol = _datasets_by_protocol(datasets)
    slices_by_family = _slices_by_field(vertical_slices, "family_id")
    slices_by_protocol = _slices_by_field(vertical_slices, "protocol_id")
    slices_by_dataset = _slices_by_field(vertical_slices, "dataset_id")
    detail_links_by_protocol = {
        protocol.id: _protocol_detail_link(protocol.id) for protocol in protocols
    }
    detail_links_by_dataset = {dataset.id: _dataset_detail_link(dataset.id) for dataset in datasets}

    return {
        "catalog_schema_version": "0.1.0",
        "title": "behavtaskatlas Catalog",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "derived_dir": str(derived_dir),
        "catalog_json_link": _relative_link(catalog_json_path, catalog_path),
        "report_index_link": _relative_link(report_index_path, catalog_path),
        "counts": {
            "task_families": len(task_families),
            "protocols": len(protocols),
            "datasets": len(datasets),
            "vertical_slices": len(vertical_slices),
            "report_available": sum(
                1
                for payload in slice_payloads.values()
                if payload.get("report_status") == "available"
            ),
        },
        "task_families": [
            _catalog_family_row(
                family,
                protocols=protocols,
                datasets_by_protocol=datasets_by_protocol,
                slices=slices_by_family.get(family.id, []),
            )
            for family in task_families
        ],
        "protocols": [
            _catalog_protocol_row(
                protocol,
                family=family_by_id.get(protocol.family_id),
                datasets=datasets_by_protocol.get(protocol.id, []),
                slices=slices_by_protocol.get(protocol.id, []),
                slice_payloads=slice_payloads,
                detail_link=detail_links_by_protocol[protocol.id],
            )
            for protocol in protocols
        ],
        "protocol_details": [
            _catalog_protocol_detail(
                protocol,
                family=family_by_id.get(protocol.family_id),
                datasets=datasets_by_protocol.get(protocol.id, []),
                slices=slices_by_protocol.get(protocol.id, []),
                slice_payloads=slice_payloads,
                detail_link=detail_links_by_protocol[protocol.id],
                dataset_detail_links=detail_links_by_dataset,
            )
            for protocol in protocols
        ],
        "datasets": [
            _catalog_dataset_row(
                dataset,
                slices=slices_by_dataset.get(dataset.id, []),
                detail_link=detail_links_by_dataset[dataset.id],
            )
            for dataset in datasets
        ],
        "dataset_details": [
            _catalog_dataset_detail(
                dataset,
                protocols=protocols,
                family_by_id=family_by_id,
                slices=slices_by_dataset.get(dataset.id, []),
                slices_by_protocol=slices_by_protocol,
                slice_payloads=slice_payloads,
                protocol_detail_links=detail_links_by_protocol,
                detail_link=detail_links_by_dataset[dataset.id],
            )
            for dataset in datasets
        ],
        "vertical_slices": [
            _catalog_slice_row(record, slice_payloads[record.id]) for record in vertical_slices
        ],
    }


def write_static_catalog_html(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(static_catalog_html(payload), encoding="utf-8")


def write_static_catalog_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    CatalogPayload.model_validate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_static_protocol_pages(catalog_path: Path, payload: dict[str, Any]) -> list[Path]:
    written = []
    for detail in payload.get("protocol_details", []):
        detail_link = detail.get("detail_link")
        if not detail_link:
            continue
        page_path = catalog_path.parent / str(detail_link)
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(
            static_protocol_detail_html(
                detail,
                payload,
                catalog_link=_relative_link(catalog_path, page_path),
            ),
            encoding="utf-8",
        )
        written.append(page_path)
    return written


def write_static_dataset_pages(catalog_path: Path, payload: dict[str, Any]) -> list[Path]:
    written = []
    for detail in payload.get("dataset_details", []):
        detail_link = detail.get("detail_link")
        if not detail_link:
            continue
        page_path = catalog_path.parent / str(detail_link)
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(
            static_dataset_detail_html(
                detail,
                payload,
                catalog_link=_relative_link(catalog_path, page_path),
            ),
            encoding="utf-8",
        )
        written.append(page_path)
    return written


def load_repository_records(root: Path = Path(".")) -> list[Any]:
    records = []
    for path in iter_record_paths(root):
        try:
            records.append(model_from_record(load_yaml(path)))
        except (OSError, ValueError, ValidationError) as exc:
            raise ValueError(f"Invalid repository record {path}: {exc}") from exc
    return records


def load_vertical_slice_records(root: Path = Path(".")) -> list[VerticalSlice]:
    records = []
    for path in sorted((root / "vertical_slices").glob("*/slice.yaml")):
        try:
            records.append(VerticalSlice.model_validate(load_yaml(path)))
        except (OSError, ValueError, ValidationError) as exc:
            raise ValueError(f"Invalid vertical slice record {path}: {exc}") from exc
    return sorted(records, key=lambda record: (record.display_order, record.id))


def _datasets_by_protocol(datasets: list[Dataset]) -> dict[str, list[Dataset]]:
    grouped: dict[str, list[Dataset]] = {}
    for dataset in datasets:
        for protocol_id in dataset.protocol_ids:
            grouped.setdefault(protocol_id, []).append(dataset)
    return {
        protocol_id: sorted(group, key=lambda dataset: dataset.name)
        for protocol_id, group in grouped.items()
    }


def _slices_by_field(
    slices: list[VerticalSlice],
    field_name: str,
) -> dict[str, list[VerticalSlice]]:
    grouped: dict[str, list[VerticalSlice]] = {}
    for slice_record in slices:
        grouped.setdefault(str(getattr(slice_record, field_name)), []).append(slice_record)
    return {
        key: sorted(group, key=lambda record: (record.display_order, record.title))
        for key, group in grouped.items()
    }


def _catalog_family_row(
    family: TaskFamily,
    *,
    protocols: list[Protocol],
    datasets_by_protocol: dict[str, list[Dataset]],
    slices: list[VerticalSlice],
) -> dict[str, Any]:
    family_protocols = [protocol for protocol in protocols if protocol.family_id == family.id]
    dataset_ids = {
        dataset.id
        for protocol in family_protocols
        for dataset in datasets_by_protocol.get(protocol.id, [])
    }
    return {
        "family_id": family.id,
        "name": family.name,
        "modalities": family.modalities,
        "choice_types": family.common_choice_types,
        "curation_status": family.curation_status,
        "protocol_count": len(family_protocols),
        "dataset_count": len(dataset_ids),
        "slice_count": len(slices),
    }


def _catalog_protocol_row(
    protocol: Protocol,
    *,
    family: TaskFamily | None,
    datasets: list[Dataset],
    slices: list[VerticalSlice],
    slice_payloads: dict[str, dict[str, Any]],
    detail_link: str,
) -> dict[str, Any]:
    dataset_ids = sorted(
        {
            *protocol.dataset_ids,
            *(dataset.id for dataset in datasets),
        }
    )
    slice_ids = [record.id for record in slices]
    return {
        "protocol_id": protocol.id,
        "detail_link": detail_link,
        "name": protocol.name,
        "family_id": protocol.family_id,
        "family_name": family.name if family else None,
        "species": protocol.species,
        "modalities": protocol.stimulus.modalities,
        "evidence_type": protocol.stimulus.evidence_type,
        "choice_type": protocol.choice.choice_type,
        "response_modalities": protocol.choice.response_modalities,
        "dataset_ids": dataset_ids,
        "slice_ids": slice_ids,
        "curation_status": protocol.curation_status,
        "report_status": _combined_report_status(
            [slice_payloads[record.id] for record in slices if record.id in slice_payloads]
        ),
    }


def _catalog_protocol_detail(
    protocol: Protocol,
    *,
    family: TaskFamily | None,
    datasets: list[Dataset],
    slices: list[VerticalSlice],
    slice_payloads: dict[str, dict[str, Any]],
    detail_link: str,
    dataset_detail_links: dict[str, str],
) -> dict[str, Any]:
    linked_slices = []
    for slice_record in slices:
        payload = slice_payloads.get(slice_record.id, {})
        linked_slices.append(
            {
                "slice_id": slice_record.id,
                "title": slice_record.title,
                "report_status": payload.get("report_status", "missing"),
                "artifact_status": payload.get("artifact_status", "missing"),
                "primary_link": payload.get("primary_link"),
            }
        )
    return {
        "protocol_id": protocol.id,
        "detail_link": detail_link,
        "name": protocol.name,
        "aliases": protocol.aliases,
        "description": protocol.description.strip(),
        "family_id": protocol.family_id,
        "family_name": family.name if family else None,
        "species": protocol.species,
        "curation_status": protocol.curation_status,
        "stimulus": protocol.stimulus.model_dump(mode="json"),
        "choice": protocol.choice.model_dump(mode="json"),
        "timing": [phase.model_dump(mode="json") for phase in protocol.timing],
        "feedback": protocol.feedback.model_dump(mode="json"),
        "training": protocol.training.model_dump(mode="json"),
        "apparatus": protocol.apparatus,
        "software": protocol.software,
        "expected_analyses": protocol.expected_analyses,
        "interpretive_claims": [
            claim.model_dump(mode="json") for claim in protocol.interpretive_claims
        ],
        "datasets": [
            {
                "dataset_id": dataset.id,
                "detail_link": dataset_detail_links[dataset.id],
                "name": dataset.name,
                "source_url": dataset.source_url,
                "license": dataset.license,
                "curation_status": dataset.curation_status,
            }
            for dataset in datasets
        ],
        "vertical_slices": linked_slices,
        "references": [reference.model_dump(mode="json") for reference in protocol.references],
        "provenance": protocol.provenance.model_dump(mode="json"),
        "open_questions": protocol.open_questions,
        "report_status": _combined_report_status(linked_slices),
    }


def _catalog_dataset_row(
    dataset: Dataset,
    *,
    slices: list[VerticalSlice],
    detail_link: str,
) -> dict[str, Any]:
    return {
        "dataset_id": dataset.id,
        "detail_link": detail_link,
        "name": dataset.name,
        "protocol_ids": dataset.protocol_ids,
        "species": dataset.species,
        "source_url": dataset.source_url,
        "license": dataset.license,
        "curation_status": dataset.curation_status,
        "slice_ids": [record.id for record in slices],
    }


def _catalog_dataset_detail(
    dataset: Dataset,
    *,
    protocols: list[Protocol],
    family_by_id: dict[str, TaskFamily],
    slices: list[VerticalSlice],
    slices_by_protocol: dict[str, list[VerticalSlice]],
    slice_payloads: dict[str, dict[str, Any]],
    protocol_detail_links: dict[str, str],
    detail_link: str,
) -> dict[str, Any]:
    linked_protocols = sorted(
        [
            protocol
            for protocol in protocols
            if protocol.id in dataset.protocol_ids or dataset.id in protocol.dataset_ids
        ],
        key=lambda protocol: protocol.name,
    )
    return {
        "dataset_id": dataset.id,
        "detail_link": detail_link,
        "name": dataset.name,
        "description": dataset.description.strip(),
        "protocol_ids": dataset.protocol_ids,
        "protocols": [
            {
                "protocol_id": protocol.id,
                "detail_link": protocol_detail_links[protocol.id],
                "name": protocol.name,
                "family_name": family_by_id[protocol.family_id].name
                if protocol.family_id in family_by_id
                else None,
                "species": protocol.species,
                "evidence_type": protocol.stimulus.evidence_type,
                "choice_type": protocol.choice.choice_type,
                "report_status": _combined_report_status(
                    [
                        slice_payloads[record.id]
                        for record in slices_by_protocol.get(protocol.id, [])
                        if record.id in slice_payloads
                    ]
                ),
            }
            for protocol in linked_protocols
        ],
        "species": dataset.species,
        "curation_status": dataset.curation_status,
        "source_url": dataset.source_url,
        "access_notes": dataset.access_notes,
        "license": dataset.license,
        "data_formats": dataset.data_formats,
        "expected_trial_table_mapping": dataset.expected_trial_table_mapping,
        "vertical_slices": [
            {
                "slice_id": slice_record.id,
                "title": slice_record.title,
                "report_status": slice_payloads.get(slice_record.id, {}).get(
                    "report_status", "missing"
                ),
                "artifact_status": slice_payloads.get(slice_record.id, {}).get(
                    "artifact_status", "missing"
                ),
                "primary_link": slice_payloads.get(slice_record.id, {}).get("primary_link"),
            }
            for slice_record in slices
        ],
        "references": [reference.model_dump(mode="json") for reference in dataset.references],
        "provenance": dataset.provenance.model_dump(mode="json"),
        "caveats": dataset.caveats,
    }


def _catalog_slice_row(record: VerticalSlice, payload: dict[str, Any]) -> dict[str, Any]:
    comparison = record.comparison
    return {
        "slice_id": record.id,
        "title": record.title,
        "family_id": record.family_id,
        "protocol_id": record.protocol_id,
        "dataset_id": record.dataset_id,
        "species": comparison.species,
        "modality": comparison.modality,
        "stimulus_metric": comparison.stimulus_metric,
        "evidence_type": comparison.evidence_type,
        "report_status": payload.get("report_status", "missing"),
        "artifact_status": payload.get("artifact_status", "missing"),
        "primary_link": payload.get("primary_link"),
    }


def _combined_report_status(slice_payloads: list[dict[str, Any]]) -> str:
    if not slice_payloads:
        return "no slice"
    if any(payload.get("report_status") == "available" for payload in slice_payloads):
        return "available"
    if any(payload.get("artifact_status") == "available" for payload in slice_payloads):
        return "report pending"
    return "analysis pending"


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
    catalog_link = payload.get("catalog_link")
    if catalog_link:
        html.append(
            f'<p class="manifest-link"><a href="{escape(str(catalog_link), quote=True)}">'
            "Task catalog</a></p>"
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


def static_catalog_html(payload: dict[str, Any]) -> str:
    counts = payload.get("counts", {})
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(str(payload.get('title', 'behavtaskatlas Catalog')))}</title>",
        "<style>",
        _index_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        '<p class="eyebrow">behavtaskatlas</p>',
        f"<h1>{escape(str(payload.get('title', 'Catalog')))}</h1>",
        "<p class=\"lede\">Generated catalog of committed task-family, protocol, "
        "dataset, and vertical-slice records. Report availability is read from local "
        "ignored artifacts under the derived directory.</p>",
    ]
    report_index_link = payload.get("report_index_link")
    if report_index_link:
        html.append(
            f'<p class="manifest-link"><a href="{escape(str(report_index_link), quote=True)}">'
            "Report index</a></p>"
        )
    catalog_json_link = payload.get("catalog_json_link")
    if catalog_json_link:
        html.append(
            f'<p class="manifest-link"><a href="{escape(str(catalog_json_link), quote=True)}">'
            "Machine-readable catalog JSON</a></p>"
        )
    html.extend(
        [
            "</header>",
            '<section class="summary" aria-label="Catalog summary">',
            _metric("Task families", counts.get("task_families")),
            _metric("Protocols", counts.get("protocols")),
            _metric("Datasets", counts.get("datasets")),
            _metric("Vertical slices", counts.get("vertical_slices")),
            _metric("Reports available", counts.get("report_available")),
            "</section>",
            "<section>",
            "<h2>Browse Protocols</h2>",
            _catalog_filter_controls(payload.get("protocols", [])),
            "</section>",
            "<section>",
            "<h2>Protocol Catalog</h2>",
            _catalog_protocol_table(
                payload.get("protocols", []),
            ),
            "</section>",
            "<section>",
            "<h2>Task Families</h2>",
            _html_table(
                payload.get("task_families", []),
                [
                    ("name", "Family"),
                    ("modalities", "Modalities"),
                    ("choice_types", "Choice types"),
                    ("protocol_count", "Protocols"),
                    ("dataset_count", "Datasets"),
                    ("slice_count", "Slices"),
                    ("curation_status", "Status"),
                ],
            ),
            "</section>",
            "<section>",
            "<h2>Datasets</h2>",
            _catalog_dataset_table(
                payload.get("datasets", []),
            ),
            "</section>",
            "<section>",
            "<h2>Report-Backed Slices</h2>",
            _html_table(
                payload.get("vertical_slices", []),
                [
                    ("title", "Slice"),
                    ("species", "Species"),
                    ("modality", "Modality"),
                    ("stimulus_metric", "Stimulus metric"),
                    ("evidence_type", "Evidence"),
                    ("report_status", "Report"),
                    ("artifact_status", "Artifacts"),
                    ("primary_link", "Primary link"),
                ],
            ),
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
            _catalog_filter_script(),
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(html) + "\n"


def static_protocol_detail_html(
    detail: dict[str, Any],
    payload: dict[str, Any],
    *,
    catalog_link: str = "catalog.html",
) -> str:
    title = str(detail.get("name", "Protocol"))
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)} | behavtaskatlas</title>",
        "<style>",
        _index_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        '<p class="eyebrow">behavtaskatlas protocol</p>',
        f"<h1>{escape(title)}</h1>",
        f"<p class=\"lede\">{escape(str(detail.get('description', '')))}</p>",
        f'<p class="manifest-link"><a href="{escape(catalog_link, quote=True)}">'
        "Back to catalog</a></p>",
    ]
    catalog_json_link = payload.get("catalog_json_link")
    if catalog_json_link:
        html.append(
            f'<p class="manifest-link"><a href="{escape(str(catalog_json_link), quote=True)}">'
            "Machine-readable catalog JSON</a></p>"
        )
    html.extend(
        [
            "</header>",
            '<section class="summary" aria-label="Protocol summary">',
            _metric("Family", detail.get("family_name") or detail.get("family_id")),
            _metric("Species", detail.get("species")),
            _metric("Evidence", detail.get("stimulus", {}).get("evidence_type")),
            _metric("Choice", detail.get("choice", {}).get("choice_type")),
            _metric("Report", detail.get("report_status")),
            "</section>",
            "<section>",
            "<h2>Task Structure</h2>",
            _protocol_structure(detail),
            "</section>",
            "<section>",
            "<h2>Timing</h2>",
            _protocol_timing_table(detail.get("timing", [])),
            "</section>",
            "<section>",
            "<h2>Linked Data and Reports</h2>",
            _protocol_connections(detail),
            "</section>",
            "<section>",
            "<h2>Curation Notes</h2>",
            _protocol_curation_notes(detail),
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(html) + "\n"


def static_dataset_detail_html(
    detail: dict[str, Any],
    payload: dict[str, Any],
    *,
    catalog_link: str = "catalog.html",
) -> str:
    title = str(detail.get("name", "Dataset"))
    html = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)} | behavtaskatlas</title>",
        "<style>",
        _index_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        '<p class="eyebrow">behavtaskatlas dataset</p>',
        f"<h1>{escape(title)}</h1>",
        f"<p class=\"lede\">{escape(str(detail.get('description', '')))}</p>",
        f'<p class="manifest-link"><a href="{escape(catalog_link, quote=True)}">'
        "Back to catalog</a></p>",
    ]
    catalog_json_link = payload.get("catalog_json_link")
    if catalog_json_link:
        html.append(
            f'<p class="manifest-link"><a href="{escape(str(catalog_json_link), quote=True)}">'
            "Machine-readable catalog JSON</a></p>"
        )
    source_url = detail.get("source_url")
    if source_url:
        html.append(
            f'<p class="manifest-link"><a href="{escape(str(source_url), quote=True)}">'
            "Open source dataset</a></p>"
        )
    html.extend(
        [
            "</header>",
            '<section class="summary" aria-label="Dataset summary">',
            _metric("Species", detail.get("species")),
            _metric("Protocols", len(detail.get("protocols", []))),
            _metric("Slices", len(detail.get("vertical_slices", []))),
            _metric("Formats", detail.get("data_formats")),
            _metric("Status", detail.get("curation_status")),
            "</section>",
            "<section>",
            "<h2>Dataset Record</h2>",
            _dataset_structure(detail),
            "</section>",
            "<section>",
            "<h2>Linked Protocols</h2>",
            _dataset_protocol_table(detail.get("protocols", [])),
            "</section>",
            "<section>",
            "<h2>Report-Backed Slices</h2>",
            _protocol_slice_table(detail.get("vertical_slices", [])),
            "</section>",
            "<section>",
            "<h2>Trial Table Mapping</h2>",
            _mapping_table(detail.get("expected_trial_table_mapping", {})),
            "</section>",
            "<section>",
            "<h2>Curation Notes</h2>",
            _dataset_curation_notes(detail),
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


def _protocol_structure(detail: dict[str, Any]) -> str:
    stimulus = detail.get("stimulus", {})
    choice = detail.get("choice", {})
    feedback = detail.get("feedback", {})
    training = detail.get("training", {})
    return _definition_list(
        _present_rows(
            [
                ("Protocol ID", detail.get("protocol_id")),
                ("Aliases", detail.get("aliases")),
                ("Family ID", detail.get("family_id")),
                ("Curation status", detail.get("curation_status")),
                ("Stimulus modalities", stimulus.get("modalities")),
                ("Stimulus variables", stimulus.get("variables")),
                ("Evidence type", stimulus.get("evidence_type")),
                ("Evidence schedule", stimulus.get("evidence_schedule")),
                ("Units", stimulus.get("units")),
                ("Stimulus notes", stimulus.get("notes")),
                ("Choice alternatives", choice.get("alternatives")),
                ("Response modalities", choice.get("response_modalities")),
                ("Action mapping", choice.get("action_mapping")),
                ("Choice notes", choice.get("notes")),
                ("Feedback", feedback.get("feedback_type")),
                ("Reward", feedback.get("reward")),
                ("Penalty", feedback.get("penalty")),
                ("Feedback notes", feedback.get("notes")),
                ("Training stages", training.get("stages")),
                ("Training notes", training.get("notes")),
                ("Apparatus", detail.get("apparatus")),
                ("Software", detail.get("software")),
            ]
        )
    )


def _protocol_timing_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="empty">No timing phases recorded.</p>'
    return _html_table(
        rows,
        [
            ("name", "Phase"),
            ("duration", "Duration"),
            ("description", "Description"),
            ("contingent_on", "Contingent on"),
        ],
    )


def _protocol_connections(detail: dict[str, Any]) -> str:
    parts = []
    datasets = detail.get("datasets", [])
    slices = detail.get("vertical_slices", [])
    if datasets:
        parts.extend(["<h3>Datasets</h3>", _protocol_dataset_table(datasets)])
    else:
        parts.append('<p class="empty">No linked dataset record yet.</p>')
    if slices:
        parts.extend(["<h3>Report-Backed Slices</h3>", _protocol_slice_table(slices)])
    else:
        parts.append('<p class="empty">No report-backed vertical slice yet.</p>')
    return "\n".join(parts)


def _dataset_structure(detail: dict[str, Any]) -> str:
    return _definition_list(
        _present_rows(
            [
                ("Dataset ID", detail.get("dataset_id")),
                ("Protocol IDs", detail.get("protocol_ids")),
                ("Curation status", detail.get("curation_status")),
                ("Species", detail.get("species")),
                ("Source URL", detail.get("source_url")),
                ("Access notes", detail.get("access_notes")),
                ("License", detail.get("license")),
                ("Data formats", detail.get("data_formats")),
            ]
        )
    )


def _dataset_protocol_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="empty">No linked protocol records yet.</p>'
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for label in ["Protocol", "Family", "Species", "Evidence", "Choice", "Report"]:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        name = str(row.get("name") or row.get("protocol_id") or "")
        detail_link = row.get("detail_link")
        parts.append("<tr>")
        if detail_link:
            parts.append(
                f'<td><a href="{escape(str(detail_link), quote=True)}">'
                f"{escape(name)}</a></td>"
            )
        else:
            parts.append(f"<td>{escape(name)}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('family_name')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('species')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('evidence_type')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('choice_type')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('report_status')))}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _mapping_table(mapping: dict[str, Any]) -> str:
    if not mapping:
        return '<p class="empty">No trial-table mapping recorded.</p>'
    rows = [
        {"canonical_field": key, "source_field": value}
        for key, value in sorted(mapping.items(), key=lambda item: item[0])
    ]
    return _html_table(
        rows,
        [
            ("canonical_field", "Canonical field"),
            ("source_field", "Source field"),
        ],
    )


def _dataset_curation_notes(detail: dict[str, Any]) -> str:
    sections = [
        "<h3>Caveats</h3>",
        _html_list(detail.get("caveats", []), "No caveats recorded."),
        "<h3>References</h3>",
        _reference_list(detail.get("references", [])),
        "<h3>Provenance</h3>",
        _definition_list(
            _present_rows(
                [
                    ("Curators", detail.get("provenance", {}).get("curators")),
                    ("Created", detail.get("provenance", {}).get("created")),
                    ("Updated", detail.get("provenance", {}).get("updated")),
                    ("Source notes", detail.get("provenance", {}).get("source_notes")),
                ]
            )
        ),
    ]
    return "\n".join(sections)


def _protocol_dataset_table(rows: list[dict[str, Any]]) -> str:
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for label in ["Dataset", "Dataset ID", "License", "Status"]:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        name = str(row.get("name") or row.get("dataset_id") or "")
        detail_link = row.get("detail_link")
        source_url = row.get("source_url")
        parts.append("<tr>")
        if detail_link:
            parts.append(
                f'<td><a href="{escape(str(detail_link), quote=True)}">'
                f"{escape(name)}</a></td>"
            )
        elif source_url:
            parts.append(
                f'<td><a href="{escape(str(source_url), quote=True)}">'
                f"{escape(name)}</a></td>"
            )
        else:
            parts.append(f"<td>{escape(name)}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('dataset_id')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('license')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('curation_status')))}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _protocol_slice_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="empty">No report-backed vertical slice yet.</p>'
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for label in ["Slice", "Slice ID", "Report", "Artifacts"]:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        title = str(row.get("title") or row.get("slice_id") or "")
        primary_link = row.get("primary_link")
        parts.append("<tr>")
        if primary_link:
            parts.append(
                f'<td><a href="{escape(str(primary_link), quote=True)}">'
                f"{escape(title)}</a></td>"
            )
        else:
            parts.append(f"<td>{escape(title)}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('slice_id')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('report_status')))}</td>")
        parts.append(f"<td>{escape(_format_cell(row.get('artifact_status')))}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _protocol_curation_notes(detail: dict[str, Any]) -> str:
    sections = [
        "<h3>Expected Analyses</h3>",
        _html_list(detail.get("expected_analyses", []), "No expected analyses recorded."),
        "<h3>Interpretive Claims</h3>",
        _interpretive_claims_table(detail.get("interpretive_claims", [])),
        "<h3>References</h3>",
        _reference_list(detail.get("references", [])),
        "<h3>Open Questions</h3>",
        _html_list(detail.get("open_questions", []), "No open questions recorded."),
        "<h3>Provenance</h3>",
        _definition_list(
            _present_rows(
                [
                    ("Curators", detail.get("provenance", {}).get("curators")),
                    ("Created", detail.get("provenance", {}).get("created")),
                    ("Updated", detail.get("provenance", {}).get("updated")),
                    ("Source notes", detail.get("provenance", {}).get("source_notes")),
                ]
            )
        ),
    ]
    return "\n".join(sections)


def _interpretive_claims_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="empty">No interpretive claims recorded.</p>'
    return _html_table(
        rows,
        [
            ("label", "Claim"),
            ("source", "Source"),
            ("confidence", "Confidence"),
            ("caveat", "Caveat"),
        ],
    )


def _reference_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="empty">No references recorded.</p>'
    parts = ["<ul>"]
    for row in rows:
        citation = str(row.get("citation") or row.get("id") or "")
        url = row.get("url") or (f"https://doi.org/{row['doi']}" if row.get("doi") else None)
        parts.append("<li>")
        if url:
            parts.append(
                f'<a href="{escape(str(url), quote=True)}">{escape(citation)}</a>'
            )
        else:
            parts.append(escape(citation))
        notes = row.get("notes")
        if notes:
            parts.append(f" - {escape(str(notes))}")
        parts.append("</li>")
    parts.append("</ul>")
    return "\n".join(parts)


def _html_list(items: list[Any], empty_text: str) -> str:
    if not items:
        return f'<p class="empty">{escape(empty_text)}</p>'
    parts = ["<ul>"]
    for item in items:
        parts.append(f"<li>{escape(_format_cell(item))}</li>")
    parts.append("</ul>")
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
section > h3 {
  margin: 18px 0 8px;
  font-size: 0.98rem;
}
section > h3:first-child {
  margin-top: 0;
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
.catalog-controls {
  display: grid;
  grid-template-columns: minmax(220px, 2fr) repeat(4, minmax(150px, 1fr));
  gap: 12px;
  align-items: end;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  padding: 14px;
}
.catalog-control label {
  display: block;
  margin-bottom: 5px;
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
  text-transform: uppercase;
}
.catalog-control input,
.catalog-control select {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: #ffffff;
  color: var(--ink);
  font: inherit;
  padding: 7px 9px;
}
.result-count {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 0.9rem;
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
  .catalog-controls {
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


def _catalog_filter_controls(protocols: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            '<div class="catalog-controls" data-catalog-controls>',
            _catalog_search_control(),
            _catalog_select_control(
                "species-filter",
                "Species",
                "All species",
                _unique_protocol_values(protocols, "species"),
            ),
            _catalog_select_control(
                "modality-filter",
                "Modality",
                "All modalities",
                _unique_protocol_values(protocols, "modalities"),
            ),
            _catalog_select_control(
                "evidence-filter",
                "Evidence",
                "All evidence",
                _unique_protocol_values(protocols, "evidence_type"),
            ),
            _catalog_select_control(
                "report-filter",
                "Report",
                "All reports",
                _unique_protocol_values(protocols, "report_status"),
            ),
            "</div>",
            '<p class="result-count" id="catalog-result-count">'
            f"{len(protocols)} protocols</p>",
        ]
    )


def _catalog_search_control() -> str:
    return (
        '<div class="catalog-control">'
        '<label for="catalog-search">Search</label>'
        '<input id="catalog-search" type="search" autocomplete="off" '
        'placeholder="Protocol, family, species, evidence">'
        "</div>"
    )


def _catalog_select_control(
    element_id: str,
    label: str,
    empty_label: str,
    values: list[str],
) -> str:
    parts = [
        '<div class="catalog-control">',
        f'<label for="{escape(element_id, quote=True)}">{escape(label)}</label>',
        f'<select id="{escape(element_id, quote=True)}">',
        f'<option value="">{escape(empty_label)}</option>',
    ]
    for value in values:
        parts.append(
            f'<option value="{escape(_filter_token(value), quote=True)}">'
            f"{escape(value)}</option>"
        )
    parts.extend(["</select>", "</div>"])
    return "\n".join(parts)


def _catalog_protocol_table(rows: list[dict[str, Any]]) -> str:
    columns = [
        ("name", "Protocol"),
        ("family_name", "Family"),
        ("species", "Species"),
        ("modalities", "Modality"),
        ("evidence_type", "Evidence"),
        ("choice_type", "Choice"),
        ("response_modalities", "Response"),
        ("dataset_ids", "Datasets"),
        ("slice_ids", "Slices"),
        ("report_status", "Report"),
    ]
    if not rows:
        return '<p class="empty">No protocol rows available.</p>'
    parts = [
        '<div class="table-wrap">',
        '<table data-catalog-table="protocols">',
        "<thead>",
        "<tr>",
    ]
    for _, label in columns:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        parts.append(_catalog_protocol_html_row(row, columns))
    parts.append(
        '<tr id="catalog-no-results" hidden>'
        '<td colspan="10">No protocols match the current filters.</td>'
        "</tr>"
    )
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _catalog_protocol_html_row(
    row: dict[str, Any],
    columns: list[tuple[str, str]],
) -> str:
    attrs = {
        "search": _catalog_search_text(row),
        "species": _filter_tokens(row.get("species")),
        "modality": _filter_tokens(row.get("modalities")),
        "evidence": _filter_tokens(row.get("evidence_type")),
        "report": _filter_tokens(row.get("report_status")),
    }
    attr_text = " ".join(
        f'data-{name}="{escape(value, quote=True)}"' for name, value in attrs.items()
    )
    parts = [f"<tr {attr_text}>"]
    for key, _ in columns:
        value = _format_cell(row.get(key))
        if key == "name" and row.get("detail_link"):
            parts.append(
                f'<td><a href="{escape(str(row["detail_link"]), quote=True)}">'
                f"{escape(value)}</a></td>"
            )
        else:
            parts.append(f"<td>{escape(value)}</td>")
    parts.append("</tr>")
    return "\n".join(parts)


def _catalog_dataset_table(rows: list[dict[str, Any]]) -> str:
    columns = [
        ("name", "Dataset"),
        ("protocol_ids", "Protocols"),
        ("species", "Species"),
        ("license", "License"),
        ("slice_ids", "Slices"),
        ("curation_status", "Status"),
    ]
    if not rows:
        return '<p class="empty">No dataset rows available.</p>'
    parts = ['<div class="table-wrap">', "<table>", "<thead>", "<tr>"]
    for _, label in columns:
        parts.append(f"<th>{escape(label)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        parts.append("<tr>")
        for key, _ in columns:
            value = _format_cell(row.get(key))
            if key == "name" and row.get("detail_link"):
                parts.append(
                    f'<td><a href="{escape(str(row["detail_link"]), quote=True)}">'
                    f"{escape(value)}</a></td>"
                )
            else:
                parts.append(f"<td>{escape(value)}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>", "</div>"])
    return "\n".join(parts)


def _catalog_filter_script() -> str:
    return """
<script>
(() => {
  const table = document.querySelector('[data-catalog-table="protocols"]');
  if (!table) return;
  const rows = Array.from(table.querySelectorAll('tbody tr[data-search]'));
  const controls = {
    search: document.getElementById('catalog-search'),
    species: document.getElementById('species-filter'),
    modality: document.getElementById('modality-filter'),
    evidence: document.getElementById('evidence-filter'),
    report: document.getElementById('report-filter'),
  };
  const counter = document.getElementById('catalog-result-count');
  const noResults = document.getElementById('catalog-no-results');
  const tokens = (value) => (value || '').split('|').filter(Boolean);
  const text = (value) => (value || '').trim().toLowerCase();
  function matches(row, key, value) {
    return !value || tokens(row.dataset[key]).includes(value);
  }
  function applyFilters() {
    const query = text(controls.search?.value);
    const values = {
      species: controls.species?.value || '',
      modality: controls.modality?.value || '',
      evidence: controls.evidence?.value || '',
      report: controls.report?.value || '',
    };
    let visible = 0;
    for (const row of rows) {
      const ok = (!query || (row.dataset.search || '').includes(query))
        && matches(row, 'species', values.species)
        && matches(row, 'modality', values.modality)
        && matches(row, 'evidence', values.evidence)
        && matches(row, 'report', values.report);
      row.hidden = !ok;
      if (ok) visible += 1;
    }
    if (counter) counter.textContent = `${visible} protocol${visible === 1 ? '' : 's'}`;
    if (noResults) noResults.hidden = visible !== 0;
  }
  Object.values(controls).forEach((control) => {
    if (!control) return;
    control.addEventListener(control.tagName === 'INPUT' ? 'input' : 'change', applyFilters);
  });
  applyFilters();
})();
</script>
""".strip()


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


def _present_rows(rows: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    return [(label, value) for label, value in rows if _has_value(value)]


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, list | tuple | dict | set):
        return len(value) > 0
    return True


def _link_if_exists(path: Path, index_path: Path) -> str | None:
    if not path.exists():
        return None
    return _relative_link(path, index_path)


def _relative_link(path: Path, index_path: Path) -> str:
    return os.path.relpath(path, index_path.parent).replace(os.sep, "/")


def _protocol_detail_link(protocol_id: str) -> str:
    slug_source = protocol_id.removeprefix("protocol.")
    slug_chars = [char.lower() if char.isalnum() else "-" for char in slug_source]
    slug = "-".join(part for part in "".join(slug_chars).split("-") if part)
    return f"protocol-{slug or 'detail'}.html"


def _dataset_detail_link(dataset_id: str) -> str:
    slug_source = dataset_id.removeprefix("dataset.")
    slug_chars = [char.lower() if char.isalnum() else "-" for char in slug_source]
    slug = "-".join(part for part in "".join(slug_chars).split("-") if part)
    return f"dataset-{slug or 'detail'}.html"


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


def _unique_protocol_values(protocols: list[dict[str, Any]], key: str) -> list[str]:
    values: set[str] = set()
    for row in protocols:
        value = row.get(key)
        if isinstance(value, list):
            values.update(str(item) for item in value if item is not None)
        elif value is not None and value != "":
            values.add(str(value))
    return sorted(values, key=str.lower)


def _catalog_search_text(row: dict[str, Any]) -> str:
    values = [
        row.get("protocol_id"),
        row.get("name"),
        row.get("family_name"),
        row.get("species"),
        row.get("modalities"),
        row.get("evidence_type"),
        row.get("choice_type"),
        row.get("response_modalities"),
        row.get("dataset_ids"),
        row.get("slice_ids"),
        row.get("curation_status"),
        row.get("report_status"),
    ]
    return " ".join(_flatten_for_search(value) for value in values).lower()


def _flatten_for_search(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list | tuple):
        return " ".join(_flatten_for_search(item) for item in value)
    return str(value)


def _filter_tokens(value: Any) -> str:
    if isinstance(value, list | tuple):
        return "|".join(_filter_token(str(item)) for item in value if item is not None)
    if value is None:
        return ""
    return _filter_token(str(value))


def _filter_token(value: str) -> str:
    return value.strip().lower()


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
    if isinstance(value, list | tuple):
        return ", ".join(_format_cell(item) for item in value)
    return str(value)
