"""Static route/link integrity checks for derived atlas payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any


def _slug(record_id: str) -> str:
    return record_id.split(".", 1)[-1] if "." in record_id else record_id


def _normalize_route(href: str) -> str | None:
    if not href.startswith("/") or href.startswith("//"):
        return None
    path = href.split("#", 1)[0].split("?", 1)[0]
    if path == "/":
        return path
    return path.rstrip("/")


def _route_for(record_type: str, record_id: str) -> str:
    slug = _slug(record_id)
    if record_type == "paper":
        return f"/papers/{slug}"
    if record_type == "protocol":
        return f"/protocols/{slug}"
    if record_type == "dataset":
        return f"/datasets/{slug}"
    if record_type == "vertical_slice":
        return f"/slices/{slug}"
    if record_type == "finding":
        return f"/findings/{slug}"
    raise ValueError(f"Unknown route record type: {record_type}")


def _base_routes() -> set[str]:
    return {
        "/",
        "/about",
        "/audit",
        "/catalog",
        "/compare",
        "/curation-queue",
        "/data-blockers",
        "/data_requests.csv",
        "/findings",
        "/fits_by_finding.csv",
        "/graph",
        "/model_roadmap.csv",
        "/model_selection.csv",
        "/model_selection_by_scope.csv",
        "/models",
        "/models/ddm",
        "/papers",
        "/search",
        "/slices",
        "/stories",
        "/stories/prior-shifts",
        "/stories/rdm",
    }


def _issue(
    *,
    issue_id: str,
    source: str,
    href: str,
    message: str,
    severity: str = "error",
) -> dict[str, Any]:
    return {
        "issue_id": issue_id,
        "severity": severity,
        "source": source,
        "href": href,
        "message": message,
    }


def _check_href(
    *,
    href: str | None,
    source: str,
    routes: set[str],
    issues: list[dict[str, Any]],
) -> int:
    if not href:
        return 0
    route = _normalize_route(href)
    if route is None:
        return 0
    if route not in routes:
        issues.append(
            _issue(
                issue_id=f"missing_route.{source}.{route.strip('/').replace('/', '.')}",
                source=source,
                href=href,
                message=f"Internal href {href!r} does not match a generated route.",
            )
        )
    return 1


def _add_record_routes(
    routes: set[str],
    *,
    record_type: str,
    records: Iterable[Mapping[str, Any]],
    id_key: str,
) -> None:
    for record in records:
        record_id = record.get(id_key)
        if isinstance(record_id, str):
            routes.add(_route_for(record_type, record_id))


def build_link_integrity_payload(
    *,
    papers_payload: Mapping[str, Any],
    catalog_payload: Mapping[str, Any],
    findings_payload: Mapping[str, Any],
    models_payload: Mapping[str, Any],
    search_payload: Mapping[str, Any],
    graph_payload: Mapping[str, Any],
    curation_queue_payload: Mapping[str, Any],
    data_requests_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check that derived internal links point at generated static routes."""
    routes = _base_routes()
    _add_record_routes(
        routes,
        record_type="paper",
        records=papers_payload.get("papers", []),
        id_key="id",
    )
    _add_record_routes(
        routes,
        record_type="protocol",
        records=catalog_payload.get("protocols", []),
        id_key="protocol_id",
    )
    _add_record_routes(
        routes,
        record_type="dataset",
        records=catalog_payload.get("datasets", []),
        id_key="dataset_id",
    )
    _add_record_routes(
        routes,
        record_type="vertical_slice",
        records=catalog_payload.get("vertical_slices", []),
        id_key="slice_id",
    )
    _add_record_routes(
        routes,
        record_type="finding",
        records=findings_payload.get("findings", []),
        id_key="finding_id",
    )
    for request in (data_requests_payload or {}).get("requests", []):
        export_path = request.get("request_export_path")
        if isinstance(export_path, str):
            route = _normalize_route(export_path)
            if route is not None:
                routes.add(route)

    issues: list[dict[str, Any]] = []
    checked_links = 0

    for entry in search_payload.get("entries", []):
        checked_links += _check_href(
            href=entry.get("href"),
            source=f"search.{entry.get('id', 'unknown')}",
            routes=routes,
            issues=issues,
        )

    for node in graph_payload.get("nodes", []):
        checked_links += _check_href(
            href=node.get("href"),
            source=f"graph.{node.get('node_id', 'unknown')}",
            routes=routes,
            issues=issues,
        )

    for item in curation_queue_payload.get("items", []):
        checked_links += _check_href(
            href=item.get("href"),
            source=f"curation_queue.{item.get('item_id', 'unknown')}",
            routes=routes,
            issues=issues,
        )

    finding_ids = {
        row.get("finding_id")
        for row in findings_payload.get("findings", [])
        if isinstance(row.get("finding_id"), str)
    }
    fit_ids = {
        row.get("id")
        for row in models_payload.get("fits", [])
        if isinstance(row.get("id"), str)
    }
    for selection in models_payload.get("model_selection_by_finding", []):
        finding_id = selection.get("finding_id")
        if finding_id not in finding_ids:
            issues.append(
                _issue(
                    issue_id=f"missing_finding.model_selection.{finding_id}",
                    source="model_selection",
                    href=str(finding_id),
                    message="Model-selection row references a missing finding.",
                )
            )
        for fit_id in selection.get("candidate_fit_ids", []):
            if fit_id not in fit_ids:
                issues.append(
                    _issue(
                        issue_id=f"missing_fit.model_selection.{fit_id}",
                        source="model_selection",
                        href=str(fit_id),
                        message="Model-selection row references a missing fit.",
                    )
                )

    paper_routes = routes
    for finding in findings_payload.get("findings", []):
        for key, record_type in (
            ("paper_id", "paper"),
            ("protocol_id", "protocol"),
            ("dataset_id", "dataset"),
            ("slice_id", "vertical_slice"),
        ):
            record_id = finding.get(key)
            if not isinstance(record_id, str):
                continue
            route = _route_for(record_type, record_id)
            checked_links += 1
            if route not in paper_routes:
                issues.append(
                    _issue(
                        issue_id=(
                            f"missing_route.finding.{finding.get('finding_id')}."
                            f"{key}"
                        ),
                        source=f"finding.{finding.get('finding_id', 'unknown')}",
                        href=route,
                        message=f"Finding {key} route does not exist.",
                    )
                )

    overall_status = "ok" if not issues else "error"
    return {
        "link_integrity_schema_version": "0.1.0",
        "title": "behavtaskatlas Link Integrity",
        "generated_at": datetime.now(UTC).isoformat(),
        "overall_status": overall_status,
        "counts": {
            "known_routes": len(routes),
            "checked_links": checked_links,
            "issues": len(issues),
        },
        "routes": sorted(routes),
        "issues": issues,
    }
