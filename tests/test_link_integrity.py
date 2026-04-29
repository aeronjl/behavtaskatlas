from behavtaskatlas.link_integrity import build_link_integrity_payload


def _payload(search_href: str = "/findings/demo") -> dict:
    return build_link_integrity_payload(
        papers_payload={"papers": [{"id": "paper.demo"}]},
        catalog_payload={
            "protocols": [{"protocol_id": "protocol.demo"}],
            "datasets": [{"dataset_id": "dataset.demo"}],
            "vertical_slices": [{"slice_id": "slice.demo"}],
        },
        findings_payload={
            "findings": [
                {
                    "finding_id": "finding.demo",
                    "paper_id": "paper.demo",
                    "protocol_id": "protocol.demo",
                    "dataset_id": "dataset.demo",
                    "slice_id": "slice.demo",
                }
            ]
        },
        models_payload={
            "fits": [{"id": "model_fit.demo"}],
            "model_selection_by_finding": [
                {
                    "finding_id": "finding.demo",
                    "candidate_fit_ids": ["model_fit.demo"],
                }
            ],
        },
        search_payload={"entries": [{"id": "finding.demo", "href": search_href}]},
        graph_payload={"nodes": [{"node_id": "finding.demo", "href": "/findings/demo"}]},
        curation_queue_payload={"items": []},
    )


def test_link_integrity_accepts_generated_routes() -> None:
    payload = _payload()

    assert payload["overall_status"] == "ok"
    assert payload["counts"]["issues"] == 0
    assert "/findings/demo" in payload["routes"]


def test_link_integrity_includes_data_request_export_routes() -> None:
    payload = build_link_integrity_payload(
        papers_payload={"papers": []},
        catalog_payload={"protocols": [], "datasets": [], "vertical_slices": []},
        findings_payload={"findings": []},
        models_payload={"fits": [], "model_selection_by_finding": []},
        search_payload={"entries": []},
        graph_payload={"nodes": []},
        curation_queue_payload={"items": []},
        data_requests_payload={
            "requests": [
                {
                    "request_id": "data_request.demo",
                    "request_export_path": "/data_requests/demo.md",
                }
            ]
        },
    )

    assert "/data_requests/demo.md" in payload["routes"]


def test_link_integrity_flags_missing_internal_href() -> None:
    payload = _payload(search_href="/findings/missing")

    assert payload["overall_status"] == "error"
    assert payload["counts"]["issues"] == 1
    assert payload["issues"][0]["href"] == "/findings/missing"
