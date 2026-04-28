from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from behavtaskatlas.models import (
    CatalogPayload,
    CurationQueuePayload,
    Dataset,
    Protocol,
    RelationshipGraphPayload,
    ReportManifest,
    TaskFamily,
    VerticalSlice,
    model_from_record,
)
from behavtaskatlas.validation import iter_record_paths, load_yaml

SOURCE_DATA_LEVEL_LABELS = {
    "raw-trial": "Raw trial",
    "processed-trial": "Processed trial",
    "processed-session": "Processed session",
    "figure-source-data": "Figure source data",
    "aggregate-only": "Aggregate only",
}

SOURCE_DATA_LEVEL_CAVEATS = {
    "raw-trial": "Trial-level rows from a source that preserves raw behavioral trial structure.",
    "processed-trial": (
        "Trial-level rows after source-specific cleaning, recoding, or convenience export."
    ),
    "processed-session": (
        "Session-level processed data; trial-level rows may require additional reconstruction."
    ),
    "figure-source-data": (
        "Rows are source data for published figures and should not be treated as a complete "
        "raw behavioral export."
    ),
    "aggregate-only": "Only aggregate summaries are available; trial-level analyses are limited.",
}


def build_static_index_payload(
    *,
    derived_dir: Path,
    index_path: Path,
    manifest_path: Path | None = None,
    catalog_path: Path | None = None,
    graph_path: Path | None = None,
    curation_queue_path: Path | None = None,
    queue_counts: dict[str, int] | None = None,
    root: Path = Path("."),
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    manifest_path = manifest_path or index_path.with_name("manifest.json")
    catalog_path = catalog_path or index_path.with_name("catalog.html")
    graph_path = graph_path or index_path.with_name("graph.html")
    curation_queue_path = curation_queue_path or index_path.with_name("curation_queue.html")
    records = load_repository_records(root)
    vertical_slice_records = sorted(
        [record for record in records if isinstance(record, VerticalSlice)],
        key=lambda record: (record.display_order, record.id),
    )
    slices = [
        _vertical_slice_payload(
            record,
            derived_dir=derived_dir,
            index_path=index_path,
            root=root,
        )
        for record in vertical_slice_records
    ]
    counts = _repository_counts(records)
    health = _mvp_health_payload(
        counts=counts,
        slices=slices,
        git_dirty=current_git_dirty(),
        queue_counts=queue_counts,
    )
    return {
        "manifest_schema_version": "0.1.0",
        "title": "behavtaskatlas MVP Reports",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "derived_dir": str(derived_dir),
        "manifest_link": _relative_link(manifest_path, index_path),
        "catalog_link": _relative_link(catalog_path, index_path),
        "graph_link": _relative_link(graph_path, index_path),
        "curation_queue_link": _relative_link(curation_queue_path, index_path),
        "health": health,
        "comparison_rows": build_slice_comparison_rows(slices),
        "slices": slices,
    }


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
    graph_path: Path | None = None,
    graph_json_path: Path | None = None,
    curation_queue_path: Path | None = None,
) -> dict[str, Any]:
    from behavtaskatlas.ibl import current_git_commit, current_git_dirty

    catalog_json_path = catalog_json_path or catalog_path.with_suffix(".json")
    report_index_path = report_index_path or catalog_path.with_name("index.html")
    graph_path = graph_path or catalog_path.with_name("graph.html")
    graph_json_path = graph_json_path or graph_path.with_suffix(".json")
    curation_queue_path = curation_queue_path or catalog_path.with_name("curation_queue.html")
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
    protocol_by_id = {record.id: record for record in protocols}
    datasets_by_protocol = _datasets_by_protocol(datasets)
    slices_by_family = _slices_by_field(vertical_slices, "family_id")
    slices_by_protocol = _slices_by_field(vertical_slices, "protocol_id")
    slices_by_dataset = _slices_by_field(vertical_slices, "dataset_id")
    detail_links_by_protocol = {
        protocol.id: _protocol_detail_link(protocol.id) for protocol in protocols
    }
    detail_links_by_dataset = {dataset.id: _dataset_detail_link(dataset.id) for dataset in datasets}
    counts = {
        "task_families": len(task_families),
        "protocols": len(protocols),
        "datasets": len(datasets),
        "vertical_slices": len(vertical_slices),
        "report_available": sum(
            1
            for payload in slice_payloads.values()
            if payload.get("report_status") == "available"
        ),
    }
    health = _mvp_health_payload(
        counts=counts,
        slices=list(slice_payloads.values()),
        git_dirty=current_git_dirty(),
    )

    return {
        "catalog_schema_version": "0.1.0",
        "title": "behavtaskatlas Catalog",
        "generated_at": datetime.now(UTC).isoformat(),
        "behavtaskatlas_commit": current_git_commit(),
        "behavtaskatlas_git_dirty": current_git_dirty(),
        "derived_dir": str(derived_dir),
        "catalog_json_link": _relative_link(catalog_json_path, catalog_path),
        "report_index_link": _relative_link(report_index_path, catalog_path),
        "graph_link": _relative_link(graph_path, catalog_path),
        "graph_json_link": _relative_link(graph_json_path, catalog_path),
        "curation_queue_link": _relative_link(curation_queue_path, catalog_path),
        "health": health,
        "counts": counts,
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
                template_protocol=protocol_by_id.get(protocol.template_protocol_id)
                if protocol.template_protocol_id
                else None,
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


def write_static_catalog_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    CatalogPayload.model_validate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_relationship_graph_payload(
    catalog_payload: dict[str, Any],
    *,
    graph_path: Path,
    graph_json_path: Path | None = None,
    catalog_path: Path | None = None,
    curation_queue_path: Path | None = None,
) -> dict[str, Any]:
    graph_json_path = graph_json_path or graph_path.with_suffix(".json")
    catalog_path = catalog_path or graph_path.with_name("catalog.html")
    curation_queue_path = curation_queue_path or graph_path.with_name("curation_queue.html")
    nodes = _relationship_graph_nodes(
        catalog_payload,
        graph_path=graph_path,
        catalog_path=catalog_path,
    )
    edges = _relationship_graph_edges(catalog_payload)
    qa_issues = _relationship_graph_qa_issues(catalog_payload, nodes=nodes, edges=edges)
    return {
        "graph_schema_version": "0.1.0",
        "title": "behavtaskatlas Relationship Graph",
        "generated_at": catalog_payload.get("generated_at"),
        "behavtaskatlas_commit": catalog_payload.get("behavtaskatlas_commit"),
        "behavtaskatlas_git_dirty": catalog_payload.get("behavtaskatlas_git_dirty"),
        "catalog_link": _relative_link(catalog_path, graph_path),
        "graph_json_link": _relative_link(graph_json_path, graph_path),
        "curation_queue_link": _relative_link(curation_queue_path, graph_path),
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "task_families": len(catalog_payload.get("task_families", [])),
            "protocols": len(catalog_payload.get("protocols", [])),
            "datasets": len(catalog_payload.get("datasets", [])),
            "vertical_slices": len(catalog_payload.get("vertical_slices", [])),
            "qa_issues": len(qa_issues),
        },
        "qa_summary": _qa_summary(qa_issues),
        "qa_issues": qa_issues,
        "nodes": nodes,
        "edges": edges,
    }


def build_curation_queue_payload(
    graph_payload: dict[str, Any],
    *,
    queue_path: Path,
    queue_json_path: Path | None = None,
    graph_path: Path | None = None,
) -> dict[str, Any]:
    queue_json_path = queue_json_path or queue_path.with_suffix(".json")
    graph_path = graph_path or queue_path.with_name("graph.html")
    items = _curation_queue_items(
        graph_payload,
        queue_path=queue_path,
        graph_path=graph_path,
    )
    return {
        "queue_schema_version": "0.1.0",
        "title": "behavtaskatlas Curation Queue",
        "generated_at": graph_payload.get("generated_at"),
        "behavtaskatlas_commit": graph_payload.get("behavtaskatlas_commit"),
        "behavtaskatlas_git_dirty": graph_payload.get("behavtaskatlas_git_dirty"),
        "graph_link": _relative_link(graph_path, queue_path),
        "queue_json_link": _relative_link(queue_json_path, queue_path),
        "counts": {
            "items": len(items),
            "open": sum(1 for item in items if item["status"] == "open"),
        },
        "action_counts": _count_by(items, "action_type"),
        "priority_counts": _count_by(items, "priority"),
        "items": items,
    }


def write_static_graph_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    RelationshipGraphPayload.model_validate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_static_curation_queue_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    CurationQueuePayload.model_validate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _repository_counts(records: list[Any]) -> dict[str, int]:
    return {
        "task_families": sum(isinstance(record, TaskFamily) for record in records),
        "protocols": sum(isinstance(record, Protocol) for record in records),
        "datasets": sum(isinstance(record, Dataset) for record in records),
        "vertical_slices": sum(isinstance(record, VerticalSlice) for record in records),
    }


def _mvp_health_payload(
    *,
    counts: dict[str, int],
    slices: list[dict[str, Any]],
    git_dirty: bool | None,
    queue_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    source_level_counts = _source_data_level_counts(slices)
    report_available = sum(1 for item in slices if item.get("report_status") == "available")
    artifact_available = sum(1 for item in slices if item.get("artifact_status") == "available")
    return {
        "counts": counts,
        "reports": {
            "available": report_available,
            "total": len(slices),
            "missing": len(slices) - report_available,
        },
        "artifacts": {
            "available": artifact_available,
            "total": len(slices),
            "missing": len(slices) - artifact_available,
        },
        "curation_queue": queue_counts or {"items": None, "open": None},
        "provenance_clean": git_dirty is False,
        "source_data_level_counts": source_level_counts,
        "source_data_rows": _source_data_level_rows(slices),
        "analysis_support_rows": _analysis_support_rows(slices),
    }


def _source_data_level_counts(slices: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in slices:
        comparison = item.get("comparison", {})
        level = str(comparison.get("source_data_level") or "unknown")
        counts[level] = counts.get(level, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[0]))


def _source_data_level_rows(slices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in slices:
        comparison = item.get("comparison", {})
        level = str(comparison.get("source_data_level") or "unknown")
        rows.append(
            {
                "slice": item.get("title"),
                "source_data_level": level,
                "source_data_label": _source_data_level_label(level),
                "data_scope": comparison.get("data_scope"),
                "caveat": _source_data_level_caveat(level),
            }
        )
    return sorted(rows, key=lambda row: (str(row["source_data_level"]), str(row["slice"])))


def _analysis_support_rows(slices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in slices:
        comparison = item.get("comparison", {})
        rows.append(
            {
                "slice": item.get("title"),
                "source_data_level": comparison.get("source_data_level"),
                "analysis_outputs": comparison.get("analysis_outputs"),
                "report_status": item.get("report_status"),
                "artifact_status": item.get("artifact_status"),
            }
        )
    return sorted(rows, key=lambda row: str(row["slice"]))


def _source_data_level_label(level: str | None) -> str:
    if not level:
        return ""
    return SOURCE_DATA_LEVEL_LABELS.get(level, level)


def _source_data_level_caveat(level: str | None) -> str:
    if not level:
        return ""
    return SOURCE_DATA_LEVEL_CAVEATS.get(level, "")


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
        "protocol_scope": protocol.protocol_scope,
        "template_protocol_id": protocol.template_protocol_id,
        "species": protocol.species,
        "modalities": protocol.stimulus.modalities,
        "evidence_type": protocol.stimulus.evidence_type,
        "choice_type": protocol.choice.choice_type,
        "response_modalities": protocol.choice.response_modalities,
        "declared_dataset_ids": sorted(protocol.dataset_ids),
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
    template_protocol: Protocol | None = None,
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
                "source_data_level": slice_record.comparison.source_data_level,
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
        "protocol_scope": protocol.protocol_scope,
        "template_protocol_id": protocol.template_protocol_id,
        "template_protocol_name": template_protocol.name if template_protocol else None,
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
                "source_data_level": dataset.source_data_level,
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
        "source_data_level": dataset.source_data_level,
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
                "protocol_scope": protocol.protocol_scope,
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
        "source_data_level": dataset.source_data_level,
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
                "source_data_level": slice_record.comparison.source_data_level,
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
        "source_data_level": comparison.source_data_level,
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


def _relationship_graph_nodes(
    catalog_payload: dict[str, Any],
    *,
    graph_path: Path,
    catalog_path: Path,
) -> list[dict[str, Any]]:
    nodes = []
    for family in catalog_payload.get("task_families", []):
        nodes.append(
            {
                "node_id": family["family_id"],
                "node_type": "task_family",
                "label": family["name"],
                "href": None,
                "status": family.get("curation_status"),
                "metadata": {
                    "protocol_count": family.get("protocol_count"),
                    "dataset_count": family.get("dataset_count"),
                    "slice_count": family.get("slice_count"),
                    "modalities": family.get("modalities", []),
                    "choice_types": family.get("choice_types", []),
                },
            }
        )
    for protocol in catalog_payload.get("protocols", []):
        nodes.append(
            {
                "node_id": protocol["protocol_id"],
                "node_type": "protocol",
                "label": protocol["name"],
                "href": _catalog_relative_href(
                    protocol.get("detail_link"),
                    catalog_path=catalog_path,
                    target_path=graph_path,
                ),
                "status": protocol.get("report_status"),
                "metadata": {
                    "family_id": protocol.get("family_id"),
                    "family_name": protocol.get("family_name"),
                    "protocol_scope": protocol.get("protocol_scope"),
                    "template_protocol_id": protocol.get("template_protocol_id"),
                    "species": protocol.get("species", []),
                    "modalities": protocol.get("modalities", []),
                    "evidence_type": protocol.get("evidence_type"),
                    "choice_type": protocol.get("choice_type"),
                    "curation_status": protocol.get("curation_status"),
                },
            }
        )
    for dataset in catalog_payload.get("datasets", []):
        nodes.append(
            {
                "node_id": dataset["dataset_id"],
                "node_type": "dataset",
                "label": dataset["name"],
                "href": _catalog_relative_href(
                    dataset.get("detail_link"),
                    catalog_path=catalog_path,
                    target_path=graph_path,
                ),
                "status": dataset.get("curation_status"),
                "metadata": {
                    "species": dataset.get("species", []),
                    "source_data_level": dataset.get("source_data_level"),
                    "license": dataset.get("license"),
                    "protocol_ids": dataset.get("protocol_ids", []),
                    "slice_ids": dataset.get("slice_ids", []),
                },
            }
        )
    for slice_row in catalog_payload.get("vertical_slices", []):
        nodes.append(
            {
                "node_id": slice_row["slice_id"],
                "node_type": "vertical_slice",
                "label": slice_row["title"],
                "href": _catalog_relative_href(
                    slice_row.get("primary_link"),
                    catalog_path=catalog_path,
                    target_path=graph_path,
                ),
                "status": slice_row.get("report_status"),
                "metadata": {
                    "family_id": slice_row.get("family_id"),
                    "protocol_id": slice_row.get("protocol_id"),
                    "dataset_id": slice_row.get("dataset_id"),
                    "species": slice_row.get("species"),
                    "modality": slice_row.get("modality"),
                    "stimulus_metric": slice_row.get("stimulus_metric"),
                    "evidence_type": slice_row.get("evidence_type"),
                    "source_data_level": slice_row.get("source_data_level"),
                    "artifact_status": slice_row.get("artifact_status"),
                },
            }
        )
    return sorted(nodes, key=lambda node: (node["node_type"], node["label"]))


def _relationship_graph_edges(catalog_payload: dict[str, Any]) -> list[dict[str, str]]:
    known_ids = {
        *[row["family_id"] for row in catalog_payload.get("task_families", [])],
        *[row["protocol_id"] for row in catalog_payload.get("protocols", [])],
        *[row["dataset_id"] for row in catalog_payload.get("datasets", [])],
        *[row["slice_id"] for row in catalog_payload.get("vertical_slices", [])],
    }
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(source: str | None, target: str | None, edge_type: str, label: str) -> None:
        if not source or not target or source not in known_ids or target not in known_ids:
            return
        key = (source, target, edge_type)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": source, "target": target, "edge_type": edge_type, "label": label})

    for protocol in catalog_payload.get("protocols", []):
        add(
            protocol.get("family_id"),
            protocol.get("protocol_id"),
            "family_protocol",
            "family has protocol",
        )
        for dataset_id in protocol.get("dataset_ids", []):
            add(
                protocol.get("protocol_id"),
                dataset_id,
                "protocol_dataset",
                "protocol uses dataset",
            )
        add(
            protocol.get("template_protocol_id"),
            protocol.get("protocol_id"),
            "protocol_variant",
            "template has variant",
        )
        for slice_id in protocol.get("slice_ids", []):
            add(
                protocol.get("protocol_id"),
                slice_id,
                "protocol_slice",
                "protocol has slice",
            )
    for slice_row in catalog_payload.get("vertical_slices", []):
        add(
            slice_row.get("family_id"),
            slice_row.get("slice_id"),
            "family_slice",
            "family has slice",
        )
        add(
            slice_row.get("protocol_id"),
            slice_row.get("slice_id"),
            "protocol_slice",
            "protocol has slice",
        )
        add(
            slice_row.get("dataset_id"),
            slice_row.get("slice_id"),
            "dataset_slice",
            "dataset backs slice",
        )
    return sorted(edges, key=lambda edge: (edge["edge_type"], edge["source"], edge["target"]))


def _relationship_graph_qa_issues(
    catalog_payload: dict[str, Any],
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, str]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    node_ids = {node["node_id"] for node in nodes}
    degrees = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        if edge["source"] in degrees:
            degrees[edge["source"]] += 1
        if edge["target"] in degrees:
            degrees[edge["target"]] += 1

    protocols = {row["protocol_id"]: row for row in catalog_payload.get("protocols", [])}
    datasets = {row["dataset_id"]: row for row in catalog_payload.get("datasets", [])}

    for node in nodes:
        if degrees.get(node["node_id"], 0) == 0:
            issues.append(
                _graph_issue(
                    "orphan_record",
                    "warning",
                    node["node_id"],
                    None,
                    f"{node['node_type']} record has no graph relationships.",
                )
            )

    for family in catalog_payload.get("task_families", []):
        if (
            not family.get("protocol_count")
            and not family.get("dataset_count")
            and not family.get("slice_count")
        ):
            issues.append(
                _graph_issue(
                    "family_without_members",
                    "warning",
                    family["family_id"],
                    None,
                    "Task family has no linked protocols, datasets, or slices.",
                )
            )

    for protocol in protocols.values():
        protocol_id = protocol["protocol_id"]
        is_template = protocol.get("protocol_scope") == "template"
        declared_dataset_ids = set(protocol.get("declared_dataset_ids", []))
        displayed_dataset_ids = set(protocol.get("dataset_ids", []))
        slice_ids = set(protocol.get("slice_ids", []))
        if not displayed_dataset_ids and not is_template:
            issues.append(
                _graph_issue(
                    "protocol_without_dataset",
                    "info",
                    protocol_id,
                    None,
                    "Protocol has no linked dataset record yet.",
                )
            )
        if not slice_ids and not is_template:
            issues.append(
                _graph_issue(
                    "protocol_without_slice",
                    "info",
                    protocol_id,
                    None,
                    "Protocol has no report-backed vertical slice yet.",
                )
            )
        for dataset_id in declared_dataset_ids:
            dataset = datasets.get(dataset_id)
            if dataset and protocol_id not in set(dataset.get("protocol_ids", [])):
                issues.append(
                    _graph_issue(
                        "missing_dataset_reciprocal",
                        "warning",
                        protocol_id,
                        dataset_id,
                        "Protocol declares dataset, but dataset does not list protocol.",
                    )
                )

    for dataset in datasets.values():
        dataset_id = dataset["dataset_id"]
        protocol_ids = set(dataset.get("protocol_ids", []))
        if not protocol_ids:
            issues.append(
                _graph_issue(
                    "dataset_without_protocol",
                    "warning",
                    dataset_id,
                    None,
                    "Dataset has no linked protocol records.",
                )
            )
        if not dataset.get("slice_ids", []):
            issues.append(
                _graph_issue(
                    "dataset_without_slice",
                    "info",
                    dataset_id,
                    None,
                    "Dataset has no report-backed vertical slice yet.",
                )
            )
        for protocol_id in protocol_ids:
            protocol = protocols.get(protocol_id)
            if protocol and dataset_id not in set(protocol.get("declared_dataset_ids", [])):
                issues.append(
                    _graph_issue(
                        "missing_protocol_reciprocal",
                        "warning",
                        dataset_id,
                        protocol_id,
                        "Dataset lists protocol, but protocol does not declare dataset.",
                    )
                )

    return sorted(
        issues,
        key=lambda issue: (
            {"error": 0, "warning": 1, "info": 2}[issue["severity"]],
            issue["issue_type"],
            issue.get("node_id") or "",
            issue.get("related_node_id") or "",
        ),
    )


def _graph_issue(
    issue_type: str,
    severity: str,
    node_id: str,
    related_node_id: str | None,
    message: str,
) -> dict[str, Any]:
    issue_id_parts = [issue_type, node_id]
    if related_node_id:
        issue_id_parts.append(related_node_id)
    issue_id = "::".join(issue_id_parts)
    return {
        "issue_id": issue_id,
        "severity": severity,
        "issue_type": issue_type,
        "node_id": node_id,
        "related_node_id": related_node_id,
        "message": message,
    }


def _qa_summary(issues: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"error": 0, "warning": 0, "info": 0, "total": len(issues)}
    for issue in issues:
        severity = issue.get("severity")
        if severity in summary:
            summary[severity] += 1
    return summary


def _curation_queue_items(
    graph_payload: dict[str, Any],
    *,
    queue_path: Path,
    graph_path: Path,
) -> list[dict[str, Any]]:
    node_by_id = {node["node_id"]: node for node in graph_payload.get("nodes", [])}
    items = []
    for issue in graph_payload.get("qa_issues", []):
        node = node_by_id.get(str(issue.get("node_id")))
        action_type = _curation_action_type(str(issue.get("issue_type", "")))
        priority = _curation_priority(str(issue.get("severity", "info")))
        href = _queue_item_href(node.get("href") if node else None, queue_path, graph_path)
        items.append(
            {
                "item_id": f"queue::{issue['issue_id']}",
                "action_type": action_type,
                "priority": priority,
                "status": "open",
                "source_issue_id": issue["issue_id"],
                "source_issue_type": issue["issue_type"],
                "source_severity": issue["severity"],
                "node_id": issue.get("node_id"),
                "node_label": node.get("label") if node else issue.get("node_id"),
                "node_type": node.get("node_type") if node else None,
                "related_node_id": issue.get("related_node_id"),
                "message": issue["message"],
                "suggested_next_step": _curation_next_step(str(issue.get("issue_type", ""))),
                "href": href,
            }
        )
    return sorted(
        items,
        key=lambda item: (
            {"high": 0, "normal": 1, "low": 2}[item["priority"]],
            item["action_type"],
            item.get("node_label") or "",
        ),
    )


def _curation_action_type(issue_type: str) -> str:
    return {
        "protocol_without_dataset": "needs dataset",
        "protocol_without_slice": "needs vertical slice",
        "dataset_without_slice": "needs vertical slice",
        "missing_protocol_reciprocal": "fix reciprocal metadata",
        "missing_dataset_reciprocal": "fix reciprocal metadata",
        "orphan_record": "connect orphan record",
        "family_without_members": "add family members",
        "dataset_without_protocol": "needs protocol link",
    }.get(issue_type, "review graph issue")


def _curation_priority(severity: str) -> str:
    if severity == "error":
        return "high"
    if severity == "warning":
        return "high"
    if severity == "info":
        return "normal"
    return "low"


def _curation_next_step(issue_type: str) -> str:
    return {
        "protocol_without_dataset": (
            "Find or curate an open dataset for this protocol, then add reciprocal "
            "protocol/dataset metadata."
        ),
        "protocol_without_slice": (
            "Choose a dataset-backed instance and add a vertical slice with analysis artifacts."
        ),
        "dataset_without_slice": (
            "Add a vertical slice that turns this dataset into an analysis-backed atlas page."
        ),
        "missing_protocol_reciprocal": (
            "Add the dataset id to the protocol record so both sides declare the link."
        ),
        "missing_dataset_reciprocal": (
            "Add the protocol id to the dataset record so both sides declare the link."
        ),
        "orphan_record": "Connect this record to at least one family, protocol, dataset, or slice.",
        "family_without_members": "Add at least one protocol or slice for this task family.",
        "dataset_without_protocol": "Link this dataset to at least one protocol record.",
    }.get(issue_type, "Review the record and decide the next curation action.")


def _queue_item_href(href: Any, queue_path: Path, graph_path: Path) -> str | None:
    if not href:
        return None
    href_text = str(href)
    if "://" in href_text or href_text.startswith("#"):
        return href_text
    return _relative_link(graph_path.parent / href_text, queue_path)


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[0]))


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
                "source_data_level": comparison.get("source_data_level"),
                "analysis_outputs": comparison.get("analysis_outputs"),
                "data_scope": comparison.get("data_scope"),
                "canonical_axis": comparison.get("canonical_axis"),
                "report_status": item.get("report_status"),
                "artifact_status": item.get("artifact_status"),
                "primary_link": item.get("primary_link"),
                "trial_count": _first_present_metric(
                    metrics,
                    ["Trials", "Parsed trials", "Source rows"],
                    fallback=comparison.get("trial_count"),
                ),
            }
        )
    return rows


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
    if slice_id == "slice.macaque-rdm-confidence-wager":
        return [
            _metric_payload("Source rows", analysis.get("n_source_rows")),
            _metric_payload("Accuracy rows", analysis.get("n_accuracy_rows")),
            _metric_payload("Sure-target rows", analysis.get("n_sure_target_choice_rows")),
            _metric_payload("Confidence rows", len(analysis.get("confidence_rows", []))),
        ]
    if "n_trials" in analysis:
        metrics = [
            _metric_payload("Trials", analysis.get("n_trials")),
            _metric_payload("Response trials", analysis.get("n_response_trials")),
        ]
        if "n_no_response_trials" in analysis:
            metrics.append(
                _metric_payload("No-response trials", analysis.get("n_no_response_trials"))
            )
        if "prior_results" in analysis:
            metrics.append(
                _metric_payload("Prior contexts", len(analysis.get("prior_results", [])))
            )
        if "summary_rows" in analysis:
            metrics.append(_metric_payload("Summary rows", len(analysis.get("summary_rows", []))))
        return metrics
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



def _report_status_label(*, report_path: Path, artifact_path: Path) -> str:
    if report_path.exists():
        return "Report available"
    if artifact_path.exists():
        return "Report pending"
    return "Analysis pending"


def _link_if_exists(path: Path, index_path: Path) -> str | None:
    if not path.exists():
        return None
    return _relative_link(path, index_path)


def _relative_link(path: Path, index_path: Path) -> str:
    return os.path.relpath(path, index_path.parent).replace(os.sep, "/")


def _catalog_relative_href(
    href: Any,
    *,
    catalog_path: Path,
    target_path: Path,
) -> str | None:
    if not href:
        return None
    href_text = str(href)
    if "://" in href_text or href_text.startswith("#"):
        return href_text
    return _relative_link(catalog_path.parent / href_text, target_path)


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
        row.get("protocol_scope"),
        row.get("template_protocol_id"),
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
