import json
from pathlib import Path

from behavtaskatlas.ibl import DEFAULT_IBL_EID
from behavtaskatlas.static_site import (
    build_catalog_payload,
    build_relationship_graph_payload,
    build_static_index_payload,
    static_catalog_html,
    static_index_html,
    static_relationship_graph_html,
    write_static_catalog_json,
    write_static_dataset_pages,
    write_static_graph_json,
    write_static_manifest_json,
    write_static_protocol_pages,
)


def test_static_index_links_available_slice_reports(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    auditory_dir = derived_dir / "auditory_clicks"
    ibl_dir = derived_dir / "ibl_visual_decision" / DEFAULT_IBL_EID
    auditory_dir.mkdir(parents=True)
    ibl_dir.mkdir(parents=True)
    (auditory_dir / "report.html").write_text("<html>report</html>", encoding="utf-8")
    (auditory_dir / "aggregate_result.json").write_text(
        json.dumps(
            {
                "n_ok": 5,
                "n_trials_total": 61222,
                "psychometric_bias_rows": [{}, {}],
                "kernel_summary_rows": [{}],
            }
        ),
        encoding="utf-8",
    )
    (ibl_dir / "analysis_result.json").write_text(
        json.dumps(
            {
                "n_trials": 569,
                "n_response_trials": 537,
                "n_no_response_trials": 32,
                "prior_results": [{}, {}, {}],
            }
        ),
        encoding="utf-8",
    )
    (ibl_dir / "psychometric.svg").write_text("<svg></svg>", encoding="utf-8")

    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=derived_dir / "index.html",
    )
    html = static_index_html(payload)

    assert payload["slices"][0]["report_status"] == "available"
    assert payload["slices"][0]["primary_link"] == "auditory_clicks/report.html"
    assert payload["slices"][1]["artifact_status"] == "available"
    assert payload["slices"][1]["report_status"] == "missing"
    assert "Auditory Clicks Evidence Accumulation" in html
    assert "IBL Visual Decision" in html
    assert "Atlas Comparison" in html
    assert "Machine-readable manifest JSON" in html
    assert "Task catalog" in html
    assert "Relationship graph" in html
    assert "signed click-count difference" in html
    assert "auditory_clicks/report.html" in html
    assert "Open psychometric SVG" in html
    assert "61,222" in html


def test_static_index_promotes_ibl_report_when_available(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    ibl_dir = derived_dir / "ibl_visual_decision" / DEFAULT_IBL_EID
    ibl_dir.mkdir(parents=True)
    (ibl_dir / "analysis_result.json").write_text(
        json.dumps({"n_trials": 569, "prior_results": []}),
        encoding="utf-8",
    )
    (ibl_dir / "report.html").write_text("<html>ibl report</html>", encoding="utf-8")

    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=derived_dir / "index.html",
    )

    ibl_slice = payload["slices"][1]
    assert ibl_slice["report_status"] == "available"
    assert ibl_slice["primary_link"] == (
        f"ibl_visual_decision/{DEFAULT_IBL_EID}/report.html"
    )
    assert ibl_slice["primary_link_label"] == "Open report"


def test_static_index_links_random_dot_motion_report(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    rdm_dir = derived_dir / "random_dot_motion" / "roitman-shadlen-pyddm"
    rdm_dir.mkdir(parents=True)
    (rdm_dir / "analysis_result.json").write_text(
        json.dumps(
            {
                "n_trials": 6149,
                "n_response_trials": 6149,
                "chronometric_rows": [{}, {}, {}, {}, {}, {}],
                "summary_rows": [{}, {}],
            }
        ),
        encoding="utf-8",
    )
    (rdm_dir / "report.html").write_text("<html>rdm report</html>", encoding="utf-8")

    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=derived_dir / "index.html",
    )
    html = static_index_html(payload)

    rdm_slice = payload["slices"][2]
    rdm_row = payload["comparison_rows"][2]
    assert rdm_slice["report_status"] == "available"
    assert rdm_slice["primary_link"] == "random_dot_motion/roitman-shadlen-pyddm/report.html"
    assert rdm_row["protocol_id"] == "protocol.random-dot-motion-classic-macaque"
    assert rdm_row["stimulus_metric"] == "signed motion coherence"
    assert rdm_row["trial_count"] == 6149
    assert "Random-Dot Motion" in html
    assert "signed motion coherence" in html
    assert "6,149" in html


def test_static_manifest_json_contains_comparison_rows(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    rdm_dir = derived_dir / "random_dot_motion" / "roitman-shadlen-pyddm"
    rdm_dir.mkdir(parents=True)
    (rdm_dir / "analysis_result.json").write_text(
        json.dumps(
            {
                "n_trials": 6149,
                "n_response_trials": 6149,
                "chronometric_rows": [{}],
                "summary_rows": [{}],
            }
        ),
        encoding="utf-8",
    )

    manifest_path = derived_dir / "manifest.json"
    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=derived_dir / "index.html",
        manifest_path=manifest_path,
    )
    write_static_manifest_json(manifest_path, payload)

    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    rdm_row = loaded["comparison_rows"][2]
    assert loaded["manifest_schema_version"] == "0.1.0"
    assert loaded["manifest_link"] == "manifest.json"
    assert loaded["catalog_link"] == "catalog.html"
    assert loaded["graph_link"] == "graph.html"
    assert len(loaded["comparison_rows"]) == 3
    assert rdm_row["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    assert rdm_row["trial_count"] == 6149


def test_catalog_payload_indexes_records_and_report_status(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    derived_dir = tmp_path / "derived"
    rdm_dir = derived_dir / "random_dot_motion" / "roitman-shadlen-pyddm"
    rdm_dir.mkdir(parents=True)
    (rdm_dir / "analysis_result.json").write_text(
        json.dumps(
            {
                "n_trials": 6149,
                "n_response_trials": 6149,
                "chronometric_rows": [{}],
                "summary_rows": [{}],
            }
        ),
        encoding="utf-8",
    )
    (rdm_dir / "report.html").write_text("<html>rdm report</html>", encoding="utf-8")

    catalog_path = derived_dir / "catalog.html"
    catalog_json_path = derived_dir / "catalog.json"
    graph_path = derived_dir / "graph.html"
    graph_json_path = derived_dir / "graph.json"
    payload = build_catalog_payload(
        root=root,
        derived_dir=derived_dir,
        catalog_path=catalog_path,
        catalog_json_path=catalog_json_path,
        report_index_path=derived_dir / "index.html",
        graph_path=graph_path,
        graph_json_path=graph_json_path,
    )
    html = static_catalog_html(payload)
    graph_payload = build_relationship_graph_payload(
        payload,
        graph_path=graph_path,
        graph_json_path=graph_json_path,
        catalog_path=catalog_path,
    )
    graph_html = static_relationship_graph_html(graph_payload)
    write_static_catalog_json(catalog_json_path, payload)
    write_static_graph_json(graph_json_path, graph_payload)
    protocol_pages = write_static_protocol_pages(catalog_path, payload)
    dataset_pages = write_static_dataset_pages(catalog_path, payload)

    loaded = json.loads(catalog_json_path.read_text(encoding="utf-8"))
    loaded_graph = json.loads(graph_json_path.read_text(encoding="utf-8"))
    rdm_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.random-dot-motion-classic-macaque"
    )
    human_rdm_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.human-rdm-button-reaction-time"
    )
    rdm_slice = next(
        row for row in payload["vertical_slices"] if row["slice_id"] == "slice.random-dot-motion"
    )
    rdm_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    )
    rdm_detail = next(
        row
        for row in payload["protocol_details"]
        if row["protocol_id"] == "protocol.random-dot-motion-classic-macaque"
    )
    rdm_dataset_detail = next(
        row
        for row in payload["dataset_details"]
        if row["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    )
    rdm_detail_path = derived_dir / rdm_protocol["detail_link"]
    rdm_dataset_path = derived_dir / rdm_dataset["detail_link"]

    assert payload["counts"]["task_families"] == 3
    assert payload["counts"]["protocols"] == 9
    assert payload["counts"]["datasets"] == 3
    assert payload["counts"]["vertical_slices"] == 3
    assert payload["counts"]["report_available"] == 1
    assert len(payload["protocol_details"]) == 9
    assert len(payload["dataset_details"]) == 3
    assert len(protocol_pages) == 9
    assert len(dataset_pages) == 3
    assert payload["graph_link"] == "graph.html"
    assert payload["graph_json_link"] == "graph.json"
    assert graph_payload["counts"]["nodes"] == 18
    assert graph_payload["counts"]["edges"] == 21
    assert graph_payload["counts"]["qa_issues"] == 13
    assert graph_payload["qa_summary"] == {"error": 0, "warning": 1, "info": 12, "total": 13}
    assert graph_payload["catalog_link"] == "catalog.html"
    assert graph_payload["graph_json_link"] == "graph.json"
    assert loaded_graph["graph_schema_version"] == "0.1.0"
    assert any(
        node["node_id"] == "protocol.random-dot-motion-classic-macaque"
        and node["href"] == "protocol-random-dot-motion-classic-macaque.html"
        for node in graph_payload["nodes"]
    )
    assert any(
        node["node_id"] == "dataset.roitman-shadlen-rdm-pyddm"
        and node["href"] == "dataset-roitman-shadlen-rdm-pyddm.html"
        for node in graph_payload["nodes"]
    )
    assert {
        "source": "protocol.random-dot-motion-classic-macaque",
        "target": "dataset.roitman-shadlen-rdm-pyddm",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
    assert {
        "source": "dataset.roitman-shadlen-rdm-pyddm",
        "target": "slice.random-dot-motion",
        "edge_type": "dataset_slice",
        "label": "dataset backs slice",
    } in graph_payload["edges"]
    assert {
        "issue_id": (
            "missing_protocol_reciprocal::dataset.roitman-shadlen-rdm-pyddm::"
            "protocol.random-dot-motion-classic-macaque"
        ),
        "severity": "warning",
        "issue_type": "missing_protocol_reciprocal",
        "node_id": "dataset.roitman-shadlen-rdm-pyddm",
        "related_node_id": "protocol.random-dot-motion-classic-macaque",
        "message": "Dataset lists protocol, but protocol does not declare dataset.",
    } in graph_payload["qa_issues"]
    assert {
        "issue_id": "protocol_without_slice::protocol.human-rdm-button-reaction-time",
        "severity": "info",
        "issue_type": "protocol_without_slice",
        "node_id": "protocol.human-rdm-button-reaction-time",
        "related_node_id": None,
        "message": "Protocol has no report-backed vertical slice yet.",
    } in graph_payload["qa_issues"]
    assert rdm_protocol["dataset_ids"] == ["dataset.roitman-shadlen-rdm-pyddm"]
    assert rdm_protocol["declared_dataset_ids"] == []
    assert rdm_protocol["slice_ids"] == ["slice.random-dot-motion"]
    assert rdm_protocol["detail_link"] == "protocol-random-dot-motion-classic-macaque.html"
    assert rdm_protocol["report_status"] == "available"
    assert rdm_detail["stimulus"]["evidence_type"] == "stochastic-motion"
    assert rdm_detail["choice"]["response_modalities"] == ["saccade"]
    assert rdm_detail["datasets"][0]["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    assert rdm_detail["datasets"][0]["detail_link"] == "dataset-roitman-shadlen-rdm-pyddm.html"
    assert rdm_detail["vertical_slices"][0]["primary_link"] == (
        "random_dot_motion/roitman-shadlen-pyddm/report.html"
    )
    assert rdm_dataset["detail_link"] == "dataset-roitman-shadlen-rdm-pyddm.html"
    assert rdm_dataset_detail["protocols"][0]["detail_link"] == (
        "protocol-random-dot-motion-classic-macaque.html"
    )
    assert rdm_dataset_detail["vertical_slices"][0]["primary_link"] == (
        "random_dot_motion/roitman-shadlen-pyddm/report.html"
    )
    assert rdm_detail_path.exists()
    rdm_detail_html = rdm_detail_path.read_text(encoding="utf-8")
    assert "Classic macaque random-dot motion discrimination" in rdm_detail_html
    assert "Back to catalog" in rdm_detail_html
    assert 'href="dataset-roitman-shadlen-rdm-pyddm.html"' in rdm_detail_html
    assert rdm_dataset_path.exists()
    rdm_dataset_html = rdm_dataset_path.read_text(encoding="utf-8")
    assert "Processed Roitman-Shadlen random-dot motion" in rdm_dataset_html
    assert "Linked Protocols" in rdm_dataset_html
    assert "Trial Table Mapping" in rdm_dataset_html
    assert 'href="protocol-random-dot-motion-classic-macaque.html"' in rdm_dataset_html
    assert human_rdm_protocol["dataset_ids"] == []
    assert human_rdm_protocol["slice_ids"] == []
    assert human_rdm_protocol["report_status"] == "no slice"
    assert rdm_slice["primary_link"] == "random_dot_motion/roitman-shadlen-pyddm/report.html"
    assert loaded["catalog_schema_version"] == "0.1.0"
    assert "Browse Protocols" in html
    assert "Protocol Catalog" in html
    assert 'href="protocol-random-dot-motion-classic-macaque.html"' in html
    assert 'href="dataset-roitman-shadlen-rdm-pyddm.html"' in html
    assert 'href="graph.html"' in html
    assert "Relationship Graph" in graph_html
    assert "Graph QA" in graph_html
    assert "missing_protocol_reciprocal" in graph_html
    assert "protocol uses dataset" in graph_html
    assert 'href="protocol-random-dot-motion-classic-macaque.html"' in graph_html
    assert 'href="dataset-roitman-shadlen-rdm-pyddm.html"' in graph_html
    assert 'id="catalog-search"' in html
    assert 'id="species-filter"' in html
    assert 'id="modality-filter"' in html
    assert 'id="evidence-filter"' in html
    assert 'id="report-filter"' in html
    assert 'data-catalog-table="protocols"' in html
    assert 'data-report="no slice"' in html
    assert "catalog-no-results" in html
    assert "applyFilters" in html
    assert "Random-Dot Motion" in html
    assert "Human random-dot motion button reaction-time task" in html
    assert "signed motion coherence" in html
