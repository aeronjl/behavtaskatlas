from datetime import date
from pathlib import Path

import yaml

from behavtaskatlas.cli import main
from behavtaskatlas.data_requests import (
    append_data_request_event,
    build_data_requests_index,
    data_request_action_state,
    write_data_request_markdown_exports,
)
from behavtaskatlas.models import (
    DataRequest,
    DataRequestDraft,
    DataRequestEvent,
    Dataset,
    Paper,
    Provenance,
    RequestedDataFile,
)
from behavtaskatlas.validation import _validate_data_request_status_events


def _demo_request_payload(status: str = "ready_to_send") -> dict:
    return {
        "object_type": "data_request",
        "schema_version": "0.1.0",
        "id": "data_request.demo",
        "title": "Demo request",
        "status": status,
        "priority": "high",
        "request_type": "author_request",
        "dataset_ids": ["dataset.demo"],
        "blocker_type": "author_request_raw_trials",
        "purpose": "Recover trial-level choice fields.",
        "blocker_detail": "Public archive lacks the behavioral table.",
        "next_action": "Send the request.",
        "requested_files": [
            {
                "name": "trials.mat",
                "description": "Trial-level MATLAB export.",
                "required": True,
            }
        ],
        "request_draft": {
            "subject": "Data request",
            "body": "Please share trials.mat.",
        },
        "events": [
            {
                "event_type": "drafted",
                "event_date": date(2026, 4, 29),
                "actor": "behavtaskatlas",
                "notes": "Drafted the request.",
            }
        ],
        "curation_status": "data-linked",
        "provenance": {
            "curators": ["behavtaskatlas"],
            "created": date(2026, 4, 29),
            "updated": date(2026, 4, 29),
        },
    }


def _write_demo_request(root: Path) -> Path:
    path = root / "data_requests" / "demo.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(_demo_request_payload(), sort_keys=False),
        encoding="utf-8",
    )
    return path


def test_build_data_requests_index_denormalizes_request_context(tmp_path: Path) -> None:
    request = DataRequest(
        object_type="data_request",
        schema_version="0.1.0",
        id="data_request.demo",
        title="Demo request",
        status="ready_to_send",
        priority="high",
        request_type="author_request",
        dataset_ids=["dataset.demo"],
        paper_ids=["paper.demo"],
        blocker_type="author_request_raw_trials",
        purpose="Recover trial-level choice fields.",
        blocker_detail="Public archive lacks the behavioral table.",
        next_action="Send the request.",
        requested_files=[
            RequestedDataFile(
                name="trials.mat",
                description="Trial-level MATLAB export.",
            )
        ],
        request_draft=DataRequestDraft(
            subject="Data request",
            body="Please share trials.mat.",
        ),
        events=[
            DataRequestEvent(
                event_type="drafted",
                event_date=date(2026, 4, 29),
                actor="behavtaskatlas",
                notes="Drafted the request.",
            )
        ],
        curation_status="data-linked",
        provenance=Provenance(
            curators=["behavtaskatlas"],
            created=date(2026, 4, 29),
            updated=date(2026, 4, 29),
        ),
    )
    dataset = Dataset(
        object_type="dataset",
        schema_version="0.1.0",
        id="dataset.demo",
        name="Demo dataset",
        description="Demo.",
        protocol_ids=["protocol.demo"],
        species=["mouse"],
        curation_status="data-linked",
        source_url="https://example.org/data",
        access_notes="Open.",
        source_data_level="raw-trial",
        provenance=Provenance(
            curators=["behavtaskatlas"],
            created=date(2026, 4, 29),
            updated=date(2026, 4, 29),
        ),
    )
    paper = Paper(
        object_type="paper",
        schema_version="0.1.0",
        id="paper.demo",
        citation="Doe J. Demo paper. Journal, 2026.",
        authors=["Doe, Jane"],
        year=2026,
        species=["mouse"],
        protocol_ids=["protocol.demo"],
        curation_status="literature-curated",
        provenance=Provenance(
            curators=["behavtaskatlas"],
            created=date(2026, 4, 29),
            updated=date(2026, 4, 29),
        ),
    )

    payload = build_data_requests_index(
        requests=[request],
        datasets=[dataset],
        papers=[paper],
        commit="abc123",
        git_dirty=False,
        today=date(2026, 4, 30),
    )

    assert payload["counts"] == {
        "events": 1,
        "linked_findings": 0,
        "requested_files": 1,
        "requests": 1,
    }
    assert payload["status_counts"] == {"ready_to_send": 1}
    assert payload["priority_counts"] == {"high": 1}
    assert payload["action_state_counts"] == {"ready_to_send": 1}
    row = payload["requests"][0]
    assert row["dataset_names"] == ["Demo dataset"]
    assert row["paper_labels"] == ["Doe J"]
    assert row["requested_files"][0]["name"] == "trials.mat"
    assert row["request_draft"]["subject"] == "Data request"
    assert row["events"][0]["event_type"] == "drafted"
    assert row["last_event_type"] == "drafted"
    assert row["last_event_date"] == "2026-04-29"
    assert row["request_export_path"] == "/data_requests/demo.md"
    assert row["action_state"] == "ready_to_send"
    assert row["days_since_last_event"] == 1
    assert row["days_until_follow_up"] is None
    assert "Send the ready-to-send request draft" in row["action_summary"]
    assert (
        "data-request-event data_request.demo --event-type sent"
        in row["suggested_command"]
    )
    assert "# Demo request" in row["request_export_markdown"]
    assert "Subject: Data request" in row["request_export_markdown"]
    assert "`trials.mat` (required)" in row["request_export_markdown"]
    assert "`paper.demo` - Doe J" in row["request_export_markdown"]
    assert "`event_type: sent`" in row["request_export_markdown"]

    written = write_data_request_markdown_exports(
        requests=[request],
        datasets=[dataset],
        papers=[paper],
        out_dir=tmp_path,
    )

    assert written == [tmp_path / "demo.md"]
    assert "Please share trials.mat." in written[0].read_text(encoding="utf-8")


def test_data_request_action_state_tracks_active_follow_up_date() -> None:
    payload = _demo_request_payload(status="requested")
    payload["events"].append(
        {
            "event_type": "sent",
            "event_date": date(2026, 4, 30),
            "actor": "curator",
            "notes": "Sent the author request.",
            "next_follow_up_date": date(2026, 5, 14),
        }
    )
    request = DataRequest.model_validate(payload)

    assert data_request_action_state(request, today=date(2026, 5, 1)) == "waiting"
    assert (
        data_request_action_state(request, today=date(2026, 5, 14))
        == "follow_up_due"
    )
    assert data_request_action_state(request, today=date(2026, 5, 15)) == "overdue"

    payload["events"].append(
        {
            "event_type": "followed_up",
            "event_date": date(2026, 5, 15),
            "actor": "curator",
            "notes": "Sent a follow-up request.",
            "next_follow_up_date": date(2026, 5, 29),
        }
    )
    request = DataRequest.model_validate(payload)

    assert data_request_action_state(request, today=date(2026, 5, 16)) == "waiting"


def test_data_request_status_requires_matching_event() -> None:
    request = DataRequest(
        object_type="data_request",
        schema_version="0.1.0",
        id="data_request.demo",
        title="Demo request",
        status="requested",
        priority="high",
        request_type="author_request",
        dataset_ids=["dataset.demo"],
        blocker_type="author_request_raw_trials",
        purpose="Recover trial-level choice fields.",
        blocker_detail="Public archive lacks the behavioral table.",
        next_action="Send the request.",
        requested_files=[
            RequestedDataFile(
                name="trials.mat",
                description="Trial-level MATLAB export.",
            )
        ],
        events=[
            DataRequestEvent(
                event_type="drafted",
                event_date=date(2026, 4, 29),
                actor="behavtaskatlas",
                notes="Drafted the request.",
            )
        ],
        curation_status="data-linked",
        provenance=Provenance(
            curators=["behavtaskatlas"],
            created=date(2026, 4, 29),
            updated=date(2026, 4, 29),
        ),
    )

    issues = _validate_data_request_status_events(Path("demo.yaml"), request)

    assert len(issues) == 1
    assert "requires a 'sent' event" in issues[0].message


def test_append_data_request_event_updates_status_and_provenance(tmp_path: Path) -> None:
    path = _write_demo_request(tmp_path)

    result = append_data_request_event(
        root=tmp_path,
        request_id="demo",
        event_type="sent",
        event_date=date(2026, 4, 30),
        actor="curator",
        notes="Sent the author request.",
        status="requested",
        evidence_path=Path("data_requests/sent/demo-2026-04-30.md"),
        next_follow_up_date=date(2026, 5, 14),
    )

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert result["previous_status"] == "ready_to_send"
    assert result["status"] == "requested"
    assert payload["status"] == "requested"
    assert payload["provenance"]["updated"] == date(2026, 4, 30)
    assert payload["events"][-1] == {
        "event_type": "sent",
        "event_date": date(2026, 4, 30),
        "actor": "curator",
        "notes": "Sent the author request.",
        "evidence_path": "data_requests/sent/demo-2026-04-30.md",
        "next_follow_up_date": date(2026, 5, 14),
    }


def test_append_data_request_event_rejects_invalid_status_transition(
    tmp_path: Path,
) -> None:
    path = _write_demo_request(tmp_path)
    before = path.read_text(encoding="utf-8")

    try:
        append_data_request_event(
            root=tmp_path,
            request_id="data_request.demo",
            event_type="sent",
            event_date=date(2026, 4, 30),
            actor="curator",
            notes="Sent the author request.",
            status="fulfilled",
        )
    except ValueError as exc:
        assert "requires a 'received' event" in str(exc)
    else:
        raise AssertionError("Expected invalid status transition to be rejected")

    assert path.read_text(encoding="utf-8") == before


def test_data_request_event_cli_creates_evidence_stub(tmp_path: Path) -> None:
    path = _write_demo_request(tmp_path)

    code = main(
        [
            "data-request-event",
            "data_request.demo",
            "--root",
            str(tmp_path),
            "--event-type",
            "sent",
            "--event-date",
            "2026-04-30",
            "--actor",
            "curator",
            "--notes",
            "Sent the author request.",
            "--status",
            "requested",
            "--next-follow-up-date",
            "2026-05-14",
            "--create-evidence-stub",
        ]
    )

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    evidence_path = tmp_path / "data_requests" / "sent" / "demo-2026-04-30.md"
    assert code == 0
    assert payload["status"] == "requested"
    assert payload["events"][-1]["evidence_path"] == (
        "data_requests/sent/demo-2026-04-30.md"
    )
    assert evidence_path.exists()
    assert "Subject: Data request" in evidence_path.read_text(encoding="utf-8")


def test_data_request_queue_cli_prints_actionable_rows(
    tmp_path: Path,
    capsys,
) -> None:
    _write_demo_request(tmp_path)

    code = main(
        [
            "data-request-queue",
            "--root",
            str(tmp_path),
            "--today",
            "2026-04-30",
        ]
    )

    output = capsys.readouterr().out
    assert code == 0
    assert "Data request queue: 1 request(s)" in output
    assert "data_request.demo [ready_to_send]" in output
    assert "data-request-event data_request.demo --event-type sent" in output
