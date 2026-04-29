"""Index machine-readable external data requests for the atlas UI."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from behavtaskatlas.ibl import current_git_commit, current_git_dirty
from behavtaskatlas.models import (
    DataRequest,
    DataRequestEvent,
    DataRequestsIndexEntry,
    DataRequestsIndexFile,
    DataRequestsIndexPayload,
    Dataset,
    Paper,
)

DATA_REQUEST_STATUS_EVENT_REQUIREMENTS = {
    "ready_to_send": "drafted",
    "requested": "sent",
    "fulfilled": "received",
    "declined": "declined",
    "closed": "closed",
}

DATA_REQUEST_EVENT_TYPES = (
    "drafted",
    "sent",
    "follow_up_due",
    "followed_up",
    "received",
    "declined",
    "license_confirmed",
    "closed",
    "note",
)

DATA_REQUEST_STATUSES = (
    "draft",
    "ready_to_send",
    "requested",
    "fulfilled",
    "declined",
    "blocked",
    "closed",
)

DATA_REQUEST_ACTION_STATES = (
    "ready_to_send",
    "waiting",
    "follow_up_due",
    "overdue",
    "fulfilled_pending_intake",
    "blocked",
    "draft",
    "closed",
)


def data_request_slug(request_id: str) -> str:
    """Return the stable URL/file slug for a data request id."""
    raw_slug = request_id.removeprefix("data_request.")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_slug).strip("-").lower()
    return slug or "data-request"


def data_request_export_path(request_id: str) -> str:
    """Return the site-relative Markdown export path for a data request."""
    return f"/data_requests/{data_request_slug(request_id)}.md"


def data_request_status_event_requirement(status: str) -> str | None:
    """Return the event type required by a data-request status."""
    return DATA_REQUEST_STATUS_EVENT_REQUIREMENTS.get(status)


def validate_data_request_status_event_state(record: DataRequest) -> list[str]:
    """Return status/event consistency messages for one data request."""
    required_event = data_request_status_event_requirement(record.status)
    if required_event is None:
        return []
    event_types = {event.event_type for event in record.events}
    if required_event in event_types:
        return []
    return [
        f"DataRequest status {record.status!r} requires a {required_event!r} event"
    ]


def _paper_label(paper: Paper) -> str:
    return paper.citation.strip().split(".")[0] or paper.id


def _names_for_ids(ids: list[str], lookup: dict[str, str]) -> list[str]:
    return [lookup.get(record_id, record_id) for record_id in ids]


def _sorted_events(events: list[DataRequestEvent]) -> list[DataRequestEvent]:
    return sorted(events, key=lambda event: (event.event_date, event.event_type))


def _next_follow_up(events: list[DataRequestEvent]) -> date | None:
    for event in reversed(_sorted_events(events)):
        if event.next_follow_up_date is not None:
            return event.next_follow_up_date
    return None


def data_request_action_state(
    request: DataRequest,
    *,
    today: date | None = None,
) -> str:
    """Return the operational queue state for a data request."""
    today = today or date.today()
    if request.status == "ready_to_send":
        return "ready_to_send"
    if request.status == "requested":
        next_follow_up = _next_follow_up(request.events)
        if next_follow_up is not None:
            days_until = (next_follow_up - today).days
            if days_until < 0:
                return "overdue"
            if days_until == 0:
                return "follow_up_due"
        return "waiting"
    if request.status == "fulfilled":
        return "fulfilled_pending_intake"
    if request.status == "blocked":
        return "blocked"
    if request.status == "draft":
        return "draft"
    if request.status in {"closed", "declined"}:
        return "closed"
    return "blocked"


def data_request_action_summary(
    request: DataRequest,
    *,
    today: date | None = None,
) -> str:
    state = data_request_action_state(request, today=today)
    if state == "ready_to_send":
        return "Send the ready-to-send request draft and record a sent event."
    if state == "waiting":
        next_follow_up = _next_follow_up(request.events)
        if next_follow_up is None:
            return "Await response; no follow-up date is recorded."
        days = (next_follow_up - (today or date.today())).days
        return f"Await response; follow up in {days} day(s)."
    if state == "follow_up_due":
        return "Follow up today and record the follow-up event."
    if state == "overdue":
        next_follow_up = _next_follow_up(request.events)
        if next_follow_up is None:
            return "Follow-up is overdue."
        days = ((today or date.today()) - next_follow_up).days
        return f"Follow-up is overdue by {days} day(s)."
    if state == "fulfilled_pending_intake":
        return "Run the intake check and confirm redistribution terms."
    if state == "draft":
        return "Complete the request draft before sending."
    if state == "blocked":
        return "Resolve the recorded blocker before continuing the request."
    return "No active external-data action is pending."


def data_request_suggested_command(
    request: DataRequest,
    *,
    today: date | None = None,
) -> str | None:
    """Return an exact next CLI command for the current queue state."""
    today = today or date.today()
    state = data_request_action_state(request, today=today)
    slug = data_request_slug(request.id)
    follow_up = (today + timedelta(days=14)).isoformat()
    if state == "ready_to_send":
        return (
            "uv run behavtaskatlas data-request-event "
            f"{request.id} --event-type sent --event-date {today.isoformat()} "
            '--actor "curator" --notes "Sent the author request." '
            f"--status requested --next-follow-up-date {follow_up} "
            "--create-evidence-stub"
        )
    if state in {"follow_up_due", "overdue"}:
        return (
            "uv run behavtaskatlas data-request-event "
            f"{request.id} --event-type followed_up "
            f"--event-date {today.isoformat()} "
            '--actor "curator" --notes "Sent follow-up request." '
            f"--status requested --next-follow-up-date {follow_up} "
            f"--evidence-path data_requests/sent/{slug}-{today.isoformat()}-follow-up.md "
            "--create-evidence-stub"
        )
    if state == "fulfilled_pending_intake":
        if (
            "dataset.khalvati-kiani-rao-rdm-confidence-source-data"
            in request.dataset_ids
        ):
            return "uv run behavtaskatlas macaque-rdm-confidence-intake-check"
        return (
            "uv run behavtaskatlas data-request-event <request_id> "
            "--event-type license_confirmed"
        )
    return None


def data_request_queue_row(
    request: DataRequest,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Return queue fields for one data request."""
    today = today or date.today()
    events = _sorted_events(request.events)
    last_event = events[-1] if events else None
    next_follow_up = _next_follow_up(events)
    return {
        "action_state": data_request_action_state(request, today=today),
        "action_summary": data_request_action_summary(request, today=today),
        "suggested_command": data_request_suggested_command(request, today=today),
        "days_since_last_event": (
            (today - last_event.event_date).days if last_event is not None else None
        ),
        "days_until_follow_up": (
            (next_follow_up - today).days if next_follow_up is not None else None
        ),
    }


def _label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ")


def _markdown_bullets(values: Iterable[str]) -> list[str]:
    return [f"- {value}" for value in values]


def render_data_request_markdown(
    request: DataRequest,
    *,
    datasets: Iterable[Dataset] = (),
    papers: Iterable[Paper] = (),
    generated_at: str | None = None,
) -> str:
    """Render a ready-to-send Markdown packet for an external data request."""
    generated_at = generated_at or datetime.now(UTC).isoformat()
    dataset_names = {dataset.id: dataset.name for dataset in datasets}
    paper_labels = {paper.id: _paper_label(paper) for paper in papers}

    lines = [
        "---",
        f"request_id: {request.id}",
        f"status: {request.status}",
        f"priority: {request.priority}",
        f"request_type: {request.request_type}",
        f"generated_at: {generated_at}",
        "---",
        "",
        f"# {request.title}",
        "",
        "## Email",
        "",
    ]
    if request.contact_instructions:
        lines.extend(["Contact path:", request.contact_instructions, ""])
    if request.request_draft is not None:
        lines.extend(
            [
                f"Subject: {request.request_draft.subject}",
                "",
                request.request_draft.body.strip(),
                "",
            ]
        )
    else:
        lines.extend(
            [
                "No request draft is recorded yet. Add `request_draft.subject` "
                "and `request_draft.body` before sending.",
                "",
            ]
        )

    lines.extend(
        [
            "## Requested Files",
            "",
            *_markdown_bullets(
                (
                    f"`{file.name}` ({'required' if file.required else 'optional'}): "
                    f"{file.description}"
                    + (f" Evidence: {file.evidence}" if file.evidence else "")
                )
                for file in request.requested_files
            ),
            "",
            "## Purpose",
            "",
            request.purpose,
            "",
            "## Blocker",
            "",
            request.blocker_detail,
            "",
            "## Affected Atlas Records",
            "",
        ]
    )
    affected_sections = [
        (
            "Datasets",
            _markdown_bullets(
                f"`{dataset_id}` - {dataset_names.get(dataset_id, dataset_id)}"
                for dataset_id in request.dataset_ids
            ),
        ),
        (
            "Papers",
            _markdown_bullets(
                f"`{paper_id}` - {paper_labels.get(paper_id, paper_id)}"
                for paper_id in request.paper_ids
            ),
        ),
        (
            "Protocols",
            _markdown_bullets(f"`{protocol_id}`" for protocol_id in request.protocol_ids),
        ),
        ("Slices", _markdown_bullets(f"`{slice_id}`" for slice_id in request.slice_ids)),
        (
            "Findings",
            _markdown_bullets(f"`{finding_id}`" for finding_id in request.finding_ids),
        ),
    ]
    for title, bullets in affected_sections:
        if not bullets:
            continue
        lines.extend([f"### {title}", "", *bullets, ""])

    lines.extend(["## Provenance Checks", ""])
    if request.evidence:
        for evidence in request.evidence:
            detail = f"- {_label(evidence.evidence_type)}: {evidence.description}"
            if evidence.url:
                detail += f" {evidence.url}"
            if evidence.path:
                detail += f" `{evidence.path}`"
            lines.append(detail)
    else:
        lines.append("- No source-evidence checks are recorded yet.")

    lines.extend(
        [
            "",
            "## License And Redistribution Question",
            "",
            "Please confirm whether behavtaskatlas may redistribute derived "
            "canonical trial tables and aggregate model-fit outputs produced "
            "from the shared files. If raw files cannot be redistributed, the "
            "atlas can keep them outside git and publish only provenance, field "
            "mapping, validation checks, and allowed aggregate summaries.",
            "",
            "## Status Handoff",
            "",
            "After sending this request, update the source `data_request` record "
            "from `ready_to_send` to `requested` and add an event with "
            "`event_type: sent`, the send date, actor, and evidence URL/path. "
            "Repository validation requires that event before accepting the "
            "`requested` status.",
            "",
        ]
    )
    return "\n".join(lines)


def write_data_request_markdown_exports(
    *,
    requests: Iterable[DataRequest],
    datasets: Iterable[Dataset] = (),
    papers: Iterable[Paper] = (),
    out_dir: Path,
    generated_at: str | None = None,
) -> list[Path]:
    """Write Markdown outbox packets for data requests and return written paths."""
    dataset_rows = list(datasets)
    paper_rows = list(papers)
    written: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for request in sorted(requests, key=lambda row: row.id):
        path = out_dir / f"{data_request_slug(request.id)}.md"
        markdown = render_data_request_markdown(
            request,
            datasets=dataset_rows,
            papers=paper_rows,
            generated_at=generated_at,
        )
        path.write_text(markdown + "\n", encoding="utf-8")
        written.append(path)
    return written


def append_data_request_event(
    *,
    root: Path,
    request_id: str,
    event_type: str,
    actor: str,
    notes: str,
    event_date: date,
    status: str | None = None,
    evidence_url: str | None = None,
    evidence_path: Path | None = None,
    next_follow_up_date: date | None = None,
    create_evidence_stub: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Append a validated workflow event to a data_request YAML record."""
    record_path = find_data_request_record_path(root=root, request_id=request_id)
    payload = _load_data_request_yaml(record_path)
    original_payload = dict(payload)
    current_record = DataRequest.model_validate(payload)

    evidence_file_path = _rooted_path(root, evidence_path) if evidence_path else None
    stored_evidence_path = (
        _stored_path(root, evidence_file_path) if evidence_file_path else None
    )
    evidence_stub_path = None
    if create_evidence_stub:
        evidence_stub_path = evidence_file_path or (
            root
            / "data_requests"
            / "sent"
            / f"{data_request_slug(current_record.id)}-{event_date.isoformat()}.md"
        )
        stored_evidence_path = _stored_path(root, evidence_stub_path)

    event_payload = {
        "event_type": event_type,
        "event_date": event_date,
        "actor": actor,
        "notes": notes,
    }
    if evidence_url:
        event_payload["evidence_url"] = evidence_url
    if stored_evidence_path:
        event_payload["evidence_path"] = stored_evidence_path
    if next_follow_up_date is not None:
        event_payload["next_follow_up_date"] = next_follow_up_date

    events = list(payload.get("events") or [])
    events.append(event_payload)
    payload["events"] = events
    if status is not None:
        payload["status"] = status
    provenance = dict(payload.get("provenance") or {})
    provenance["updated"] = event_date
    payload["provenance"] = provenance

    updated_record = DataRequest.model_validate(payload)
    state_messages = validate_data_request_status_event_state(updated_record)
    if state_messages:
        raise ValueError("; ".join(state_messages))

    if create_evidence_stub and evidence_stub_path is not None:
        _write_data_request_evidence_stub(
            path=evidence_stub_path,
            request=current_record,
            event_payload=event_payload,
            force=force,
        )

    _write_data_request_yaml(record_path, payload)
    return {
        "path": record_path,
        "request_id": updated_record.id,
        "previous_status": original_payload.get("status"),
        "status": updated_record.status,
        "event": event_payload,
        "evidence_stub_path": evidence_stub_path,
    }


def find_data_request_record_path(*, root: Path, request_id: str) -> Path:
    """Find a data_request YAML by full id or stable slug."""
    data_requests_dir = root / "data_requests"
    if not data_requests_dir.exists():
        raise FileNotFoundError(f"Data requests directory not found: {data_requests_dir}")
    for path in sorted(data_requests_dir.glob("*.yaml")):
        payload = _load_data_request_yaml(path)
        record_id = payload.get("id")
        if not isinstance(record_id, str):
            continue
        if record_id == request_id or data_request_slug(record_id) == request_id:
            return path
    raise FileNotFoundError(f"No data_request record matched {request_id!r}")


def _load_data_request_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Data request YAML must be a mapping: {path}")
    if loaded.get("object_type") != "data_request":
        raise ValueError(f"YAML record is not a data_request: {path}")
    return loaded


def _write_data_request_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def _stored_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _rooted_path(root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    if path.is_absolute():
        return path
    return root / path


def _write_data_request_evidence_stub(
    *,
    path: Path,
    request: DataRequest,
    event_payload: dict[str, Any],
    force: bool,
) -> None:
    if path.exists() and not force:
        raise FileExistsError(
            f"Evidence stub already exists: {path}. Pass --force to overwrite."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"request_id: {request.id}",
        f"event_type: {event_payload['event_type']}",
        f"event_date: {event_payload['event_date']}",
        f"actor: {event_payload['actor']}",
        "---",
        "",
        f"# {request.title}",
        "",
        "## Event Notes",
        "",
        str(event_payload["notes"]),
        "",
        "## Request Draft",
        "",
    ]
    if request.request_draft is not None:
        lines.extend(
            [
                f"Subject: {request.request_draft.subject}",
                "",
                request.request_draft.body.strip(),
                "",
            ]
        )
    else:
        lines.extend(["No request draft was recorded when this stub was created.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def build_data_requests_index(
    *,
    requests: Iterable[DataRequest],
    datasets: Iterable[Dataset] = (),
    papers: Iterable[Paper] = (),
    title: str = "behavtaskatlas Data Requests",
    commit: str | None = None,
    git_dirty: bool | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Build the derived/data_requests.json payload."""
    generated_at = datetime.now(UTC).isoformat()
    today = today or date.today()
    dataset_rows = list(datasets)
    paper_rows = list(papers)
    request_rows = sorted(requests, key=lambda request: (request.priority, request.id))
    dataset_names = {dataset.id: dataset.name for dataset in dataset_rows}
    paper_labels = {paper.id: _paper_label(paper) for paper in paper_rows}

    entries: list[DataRequestsIndexEntry] = []
    for request in request_rows:
        events = _sorted_events(request.events)
        last_event = events[-1] if events else None
        queue = data_request_queue_row(request, today=today)
        entries.append(
            DataRequestsIndexEntry(
                request_id=request.id,
                title=request.title,
                status=request.status,
                priority=request.priority,
                request_type=request.request_type,
                blocker_type=request.blocker_type,
                dataset_ids=request.dataset_ids,
                dataset_names=_names_for_ids(request.dataset_ids, dataset_names),
                paper_ids=request.paper_ids,
                paper_labels=_names_for_ids(request.paper_ids, paper_labels),
                protocol_ids=request.protocol_ids,
                slice_ids=request.slice_ids,
                finding_ids=request.finding_ids,
                model_roadmap_issue_types=request.model_roadmap_issue_types,
                purpose=request.purpose,
                blocker_detail=request.blocker_detail,
                next_action=request.next_action,
                requested_files=[
                    DataRequestsIndexFile(
                        name=file.name,
                        description=file.description,
                        required=file.required,
                    )
                    for file in request.requested_files
                ],
                contact_instructions=request.contact_instructions,
                evidence=[
                    evidence.model_dump(mode="json") for evidence in request.evidence
                ],
                request_draft=(
                    request.request_draft.model_dump(mode="json")
                    if request.request_draft is not None
                    else None
                ),
                events=[event.model_dump(mode="json") for event in events],
                last_event_type=last_event.event_type if last_event else None,
                last_event_date=last_event.event_date if last_event else None,
                next_follow_up_date=_next_follow_up(events),
                request_export_path=data_request_export_path(request.id),
                request_export_markdown=render_data_request_markdown(
                    request,
                    datasets=dataset_rows,
                    papers=paper_rows,
                    generated_at=generated_at,
                ),
                action_state=queue["action_state"],
                action_summary=queue["action_summary"],
                suggested_command=queue["suggested_command"],
                days_since_last_event=queue["days_since_last_event"],
                days_until_follow_up=queue["days_until_follow_up"],
                curation_status=request.curation_status,
                notes=request.notes,
            )
        )

    status_counts = Counter(entry.status for entry in entries)
    priority_counts = Counter(entry.priority for entry in entries)
    action_state_counts = Counter(entry.action_state for entry in entries)
    requested_file_count = sum(len(entry.requested_files) for entry in entries)
    event_count = sum(len(entry.events) for entry in entries)
    linked_finding_count = len(
        {
            finding_id
            for entry in entries
            for finding_id in entry.finding_ids
        }
    )
    payload = DataRequestsIndexPayload(
        data_requests_schema_version="0.1.0",
        title=title,
        generated_at=generated_at,
        behavtaskatlas_commit=commit if commit is not None else current_git_commit(),
        behavtaskatlas_git_dirty=(
            git_dirty if git_dirty is not None else current_git_dirty()
        ),
        counts={
            "requests": len(entries),
            "requested_files": requested_file_count,
            "events": event_count,
            "linked_findings": linked_finding_count,
        },
        status_counts=dict(sorted(status_counts.items())),
        priority_counts=dict(sorted(priority_counts.items())),
        action_state_counts=dict(sorted(action_state_counts.items())),
        requests=entries,
    )
    return payload.model_dump(mode="json")
