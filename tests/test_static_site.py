import json
from pathlib import Path

from behavtaskatlas.ibl import DEFAULT_IBL_EID
from behavtaskatlas.static_site import (
    build_catalog_payload,
    build_curation_queue_payload,
    build_relationship_graph_payload,
    build_static_index_payload,
    static_catalog_html,
    static_curation_queue_html,
    static_index_html,
    static_relationship_graph_html,
    write_static_catalog_json,
    write_static_curation_queue_json,
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
    ibl_slice = next(
        item for item in payload["slices"] if item["id"] == "slice.ibl-visual-decision"
    )
    assert ibl_slice["artifact_status"] == "available"
    assert ibl_slice["report_status"] == "missing"
    assert "Auditory Clicks Evidence Accumulation" in html
    assert "IBL Visual Decision" in html
    assert "Atlas Comparison" in html
    assert "MVP Health" in html
    assert "Source Data Levels" in html
    assert "Machine-readable manifest JSON" in html
    assert "Task catalog" in html
    assert "Relationship graph" in html
    assert "Curation queue" in html
    assert "signed click-count difference" in html
    assert "processed-trial" in html
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

    ibl_slice = next(
        item for item in payload["slices"] if item["id"] == "slice.ibl-visual-decision"
    )
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

    rdm_slice = next(item for item in payload["slices"] if item["id"] == "slice.random-dot-motion")
    rdm_row = next(
        item for item in payload["comparison_rows"] if item["slice_id"] == "slice.random-dot-motion"
    )
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
    rdm_row = next(
        item for item in loaded["comparison_rows"] if item["slice_id"] == "slice.random-dot-motion"
    )
    assert loaded["manifest_schema_version"] == "0.1.0"
    assert loaded["manifest_link"] == "manifest.json"
    assert loaded["catalog_link"] == "catalog.html"
    assert loaded["graph_link"] == "graph.html"
    assert loaded["curation_queue_link"] == "curation_queue.html"
    assert len(loaded["comparison_rows"]) == 8
    assert rdm_row["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    assert rdm_row["source_data_level"] == "processed-trial"
    assert rdm_row["trial_count"] == 6149
    assert loaded["health"]["source_data_level_counts"] == {
        "figure-source-data": 1,
        "processed-trial": 6,
        "raw-trial": 1,
    }


def test_static_manifest_reads_generic_psychometric_metrics(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    visual_dir = derived_dir / "human_visual_contrast" / "walsh-prior-cue-human-contrast-osf"
    visual_dir.mkdir(parents=True)
    (visual_dir / "analysis_result.json").write_text(
        json.dumps(
            {
                "n_trials": 66200,
                "n_response_trials": 66200,
                "n_no_response_trials": 0,
                "prior_results": [{}, {}, {}],
                "summary_rows": [{}, {}],
            }
        ),
        encoding="utf-8",
    )

    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=derived_dir / "index.html",
    )

    visual_row = next(
        item
        for item in payload["comparison_rows"]
        if item["slice_id"] == "slice.human-visual-contrast-prior-cue"
    )
    visual_slice = next(
        item for item in payload["slices"] if item["id"] == "slice.human-visual-contrast-prior-cue"
    )
    assert visual_row["trial_count"] == 66200
    assert {"label": "Prior contexts", "value": 3} in visual_slice["metrics"]
    assert {"label": "Summary rows", "value": 2} in visual_slice["metrics"]


def test_static_manifest_reads_source_row_metrics(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    confidence_dir = (
        derived_dir / "macaque_rdm_confidence" / "khalvati-kiani-rao-natcomm2021-source-data"
    )
    confidence_dir.mkdir(parents=True)
    (confidence_dir / "analysis_result.json").write_text(
        json.dumps(
            {
                "n_source_rows": 174160,
                "n_accuracy_rows": 100694,
                "n_sure_target_choice_rows": 73466,
                "confidence_rows": [{}],
            }
        ),
        encoding="utf-8",
    )

    payload = build_static_index_payload(
        derived_dir=derived_dir,
        index_path=derived_dir / "index.html",
    )

    confidence_row = next(
        item
        for item in payload["comparison_rows"]
        if item["slice_id"] == "slice.macaque-rdm-confidence-wager"
    )
    confidence_slice = next(
        item for item in payload["slices"] if item["id"] == "slice.macaque-rdm-confidence-wager"
    )
    assert confidence_row["trial_count"] == 174160
    assert confidence_row["source_data_level"] == "figure-source-data"
    assert {"label": "Source rows", "value": 174160} in confidence_slice["metrics"]
    assert {"label": "Sure-target rows", "value": 73466} in confidence_slice["metrics"]


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
    queue_path = derived_dir / "curation_queue.html"
    queue_json_path = derived_dir / "curation_queue.json"
    payload = build_catalog_payload(
        root=root,
        derived_dir=derived_dir,
        catalog_path=catalog_path,
        catalog_json_path=catalog_json_path,
        report_index_path=derived_dir / "index.html",
        graph_path=graph_path,
        graph_json_path=graph_json_path,
        curation_queue_path=queue_path,
    )
    html = static_catalog_html(payload)
    graph_payload = build_relationship_graph_payload(
        payload,
        graph_path=graph_path,
        graph_json_path=graph_json_path,
        catalog_path=catalog_path,
        curation_queue_path=queue_path,
    )
    graph_html = static_relationship_graph_html(graph_payload)
    queue_payload = build_curation_queue_payload(
        graph_payload,
        queue_path=queue_path,
        queue_json_path=queue_json_path,
        graph_path=graph_path,
    )
    queue_html = static_curation_queue_html(queue_payload)
    write_static_catalog_json(catalog_json_path, payload)
    write_static_graph_json(graph_json_path, graph_payload)
    write_static_curation_queue_json(queue_json_path, queue_payload)
    protocol_pages = write_static_protocol_pages(catalog_path, payload)
    dataset_pages = write_static_dataset_pages(catalog_path, payload)

    loaded = json.loads(catalog_json_path.read_text(encoding="utf-8"))
    loaded_graph = json.loads(graph_json_path.read_text(encoding="utf-8"))
    loaded_queue = json.loads(queue_json_path.read_text(encoding="utf-8"))
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
    macaque_confidence_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.macaque-rdm-confidence-wager"
    )
    mouse_unbiased_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-visual-contrast-wheel-unbiased"
    )
    human_visual_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.human-visual-contrast-2afc-keyboard"
    )
    rat_clicks_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.rat-auditory-clicks-nose-poke"
    )
    human_clicks_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.human-auditory-clicks-button"
    )
    poisson_clicks_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.poisson-clicks-evidence-accumulation"
    )
    rdm_slice = next(
        row for row in payload["vertical_slices"] if row["slice_id"] == "slice.random-dot-motion"
    )
    auditory_slice = next(
        row for row in payload["vertical_slices"] if row["slice_id"] == "slice.auditory-clicks"
    )
    human_clicks_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.human-auditory-clicks-dbs"
    )
    mouse_unbiased_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.mouse-visual-contrast-unbiased"
    )
    human_visual_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.human-visual-contrast-prior-cue"
    )
    human_rdm_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.human-random-dot-motion"
    )
    macaque_confidence_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.macaque-rdm-confidence-wager"
    )
    rdm_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    )
    human_rdm_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.palmer-huk-shadlen-human-rdm-cosmo2017"
    )
    macaque_confidence_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.khalvati-kiani-rao-rdm-confidence-source-data"
    )
    human_clicks_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.london-human-poisson-clicks-dbs-mendeley"
    )
    human_visual_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.walsh-prior-cue-human-contrast-osf"
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
    assert payload["counts"]["datasets"] == 7
    assert payload["counts"]["vertical_slices"] == 8
    assert payload["counts"]["report_available"] == 1
    assert len(payload["protocol_details"]) == 9
    assert len(payload["dataset_details"]) == 7
    assert len(protocol_pages) == 9
    assert len(dataset_pages) == 7
    assert payload["graph_link"] == "graph.html"
    assert payload["graph_json_link"] == "graph.json"
    assert payload["curation_queue_link"] == "curation_queue.html"
    assert graph_payload["counts"]["nodes"] == 27
    assert graph_payload["counts"]["edges"] == 43
    assert graph_payload["counts"]["qa_issues"] == 0
    assert graph_payload["qa_summary"] == {"error": 0, "warning": 0, "info": 0, "total": 0}
    assert graph_payload["catalog_link"] == "catalog.html"
    assert graph_payload["graph_json_link"] == "graph.json"
    assert graph_payload["curation_queue_link"] == "curation_queue.html"
    assert loaded_graph["graph_schema_version"] == "0.1.0"
    assert queue_payload["counts"] == {"items": 0, "open": 0}
    assert queue_payload["priority_counts"] == {}
    assert queue_payload["action_counts"] == {}
    assert loaded_queue["queue_schema_version"] == "0.1.0"
    assert not any(
        item["source_issue_id"] == "protocol_without_slice::protocol.human-rdm-button-reaction-time"
        for item in queue_payload["items"]
    )
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
        "source": "protocol.mouse-visual-contrast-wheel-unbiased",
        "target": "slice.mouse-visual-contrast-unbiased",
        "edge_type": "protocol_slice",
        "label": "protocol has slice",
    } in graph_payload["edges"]
    assert {
        "source": "dataset.ibl-public-behavior",
        "target": "slice.mouse-visual-contrast-unbiased",
        "edge_type": "dataset_slice",
        "label": "dataset backs slice",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.human-visual-contrast-2afc-keyboard",
        "target": "dataset.walsh-prior-cue-human-contrast-osf",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.human-visual-contrast-2afc-keyboard",
        "target": "slice.human-visual-contrast-prior-cue",
        "edge_type": "protocol_slice",
        "label": "protocol has slice",
    } in graph_payload["edges"]
    assert {
        "source": "dataset.walsh-prior-cue-human-contrast-osf",
        "target": "slice.human-visual-contrast-prior-cue",
        "edge_type": "dataset_slice",
        "label": "dataset backs slice",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.human-rdm-button-reaction-time",
        "target": "dataset.palmer-huk-shadlen-human-rdm-cosmo2017",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.human-auditory-clicks-button",
        "target": "dataset.london-human-poisson-clicks-dbs-mendeley",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.human-auditory-clicks-button",
        "target": "slice.human-auditory-clicks-dbs",
        "edge_type": "protocol_slice",
        "label": "protocol has slice",
    } in graph_payload["edges"]
    assert {
        "source": "dataset.london-human-poisson-clicks-dbs-mendeley",
        "target": "slice.human-auditory-clicks-dbs",
        "edge_type": "dataset_slice",
        "label": "dataset backs slice",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.human-rdm-button-reaction-time",
        "target": "slice.human-random-dot-motion",
        "edge_type": "protocol_slice",
        "label": "protocol has slice",
    } in graph_payload["edges"]
    assert {
        "source": "dataset.palmer-huk-shadlen-human-rdm-cosmo2017",
        "target": "slice.human-random-dot-motion",
        "edge_type": "dataset_slice",
        "label": "dataset backs slice",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.mouse-visual-contrast-wheel-unbiased",
        "target": "dataset.ibl-public-behavior",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.poisson-clicks-evidence-accumulation",
        "target": "protocol.rat-auditory-clicks-nose-poke",
        "edge_type": "protocol_variant",
        "label": "template has variant",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.rat-auditory-clicks-nose-poke",
        "target": "dataset.brody-lab-poisson-clicks-2009-2024",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
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
        "source": "protocol.macaque-rdm-confidence-wager",
        "target": "dataset.khalvati-kiani-rao-rdm-confidence-source-data",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.macaque-rdm-confidence-wager",
        "target": "slice.macaque-rdm-confidence-wager",
        "edge_type": "protocol_slice",
        "label": "protocol has slice",
    } in graph_payload["edges"]
    assert {
        "source": "dataset.khalvati-kiani-rao-rdm-confidence-source-data",
        "target": "slice.macaque-rdm-confidence-wager",
        "edge_type": "dataset_slice",
        "label": "dataset backs slice",
    } in graph_payload["edges"]
    assert not any(issue["severity"] == "warning" for issue in graph_payload["qa_issues"])
    assert not any(
        issue["issue_id"] == "protocol_without_slice::protocol.human-rdm-button-reaction-time"
        for issue in graph_payload["qa_issues"]
    )
    assert not any(
        issue["issue_id"] == "protocol_without_slice::protocol.human-auditory-clicks-button"
        for issue in graph_payload["qa_issues"]
    )
    assert not any(
        issue["issue_id"] == "protocol_without_dataset::protocol.human-auditory-clicks-button"
        for issue in graph_payload["qa_issues"]
    )
    assert not any(
        issue["issue_id"]
        == "protocol_without_dataset::protocol.human-visual-contrast-2afc-keyboard"
        for issue in graph_payload["qa_issues"]
    )
    assert not any(
        issue["issue_id"]
        == "protocol_without_slice::protocol.human-visual-contrast-2afc-keyboard"
        for issue in graph_payload["qa_issues"]
    )
    assert not any(
        issue["issue_id"]
        == "protocol_without_dataset::protocol.macaque-rdm-confidence-wager"
        for issue in graph_payload["qa_issues"]
    )
    assert not any(
        issue["issue_id"] == "protocol_without_slice::protocol.macaque-rdm-confidence-wager"
        for issue in graph_payload["qa_issues"]
    )
    assert rdm_protocol["dataset_ids"] == ["dataset.roitman-shadlen-rdm-pyddm"]
    assert rdm_protocol["declared_dataset_ids"] == ["dataset.roitman-shadlen-rdm-pyddm"]
    assert rdm_protocol["slice_ids"] == ["slice.random-dot-motion"]
    assert rdm_protocol["detail_link"] == "protocol-random-dot-motion-classic-macaque.html"
    assert rdm_protocol["report_status"] == "available"
    assert poisson_clicks_protocol["protocol_scope"] == "template"
    assert poisson_clicks_protocol["report_status"] == "no slice"
    assert not any(
        item["source_issue_id"]
        == "protocol_without_slice::protocol.poisson-clicks-evidence-accumulation"
        for item in queue_payload["items"]
    )
    assert rat_clicks_protocol["dataset_ids"] == ["dataset.brody-lab-poisson-clicks-2009-2024"]
    assert rat_clicks_protocol["protocol_scope"] == "concrete"
    assert rat_clicks_protocol["template_protocol_id"] == (
        "protocol.poisson-clicks-evidence-accumulation"
    )
    assert rat_clicks_protocol["declared_dataset_ids"] == [
        "dataset.brody-lab-poisson-clicks-2009-2024"
    ]
    assert rat_clicks_protocol["slice_ids"] == ["slice.auditory-clicks"]
    assert rat_clicks_protocol["report_status"] == "analysis pending"
    assert auditory_slice["protocol_id"] == "protocol.rat-auditory-clicks-nose-poke"
    assert not any(
        item["source_issue_id"]
        == "protocol_without_dataset::protocol.rat-auditory-clicks-nose-poke"
        for item in queue_payload["items"]
    )
    assert not any(
        item["source_issue_id"]
        == "protocol_without_slice::protocol.rat-auditory-clicks-nose-poke"
        for item in queue_payload["items"]
    )
    assert human_clicks_protocol["dataset_ids"] == [
        "dataset.london-human-poisson-clicks-dbs-mendeley"
    ]
    assert human_clicks_protocol["declared_dataset_ids"] == [
        "dataset.london-human-poisson-clicks-dbs-mendeley"
    ]
    assert human_clicks_protocol["slice_ids"] == ["slice.human-auditory-clicks-dbs"]
    assert human_clicks_protocol["report_status"] == "analysis pending"
    assert human_clicks_slice["protocol_id"] == "protocol.human-auditory-clicks-button"
    assert human_clicks_slice["report_status"] == "missing"
    assert human_clicks_dataset["detail_link"] == (
        "dataset-london-human-poisson-clicks-dbs-mendeley.html"
    )
    assert not any(
        item["source_issue_id"]
        == "protocol_without_dataset::protocol.human-auditory-clicks-button"
        for item in queue_payload["items"]
    )
    assert not any(
        item["source_issue_id"]
        == "protocol_without_slice::protocol.human-auditory-clicks-button"
        for item in queue_payload["items"]
    )
    assert mouse_unbiased_protocol["dataset_ids"] == ["dataset.ibl-public-behavior"]
    assert mouse_unbiased_protocol["declared_dataset_ids"] == ["dataset.ibl-public-behavior"]
    assert mouse_unbiased_protocol["slice_ids"] == ["slice.mouse-visual-contrast-unbiased"]
    assert mouse_unbiased_protocol["report_status"] == "analysis pending"
    assert mouse_unbiased_slice["protocol_id"] == "protocol.mouse-visual-contrast-wheel-unbiased"
    assert mouse_unbiased_slice["report_status"] == "missing"
    assert not any(
        item["source_issue_id"]
        == "protocol_without_dataset::protocol.mouse-visual-contrast-wheel-unbiased"
        for item in queue_payload["items"]
    )
    assert not any(
        item["source_issue_id"]
        == "protocol_without_slice::protocol.mouse-visual-contrast-wheel-unbiased"
        for item in queue_payload["items"]
    )
    assert human_visual_protocol["dataset_ids"] == [
        "dataset.walsh-prior-cue-human-contrast-osf"
    ]
    assert human_visual_protocol["declared_dataset_ids"] == [
        "dataset.walsh-prior-cue-human-contrast-osf"
    ]
    assert human_visual_protocol["slice_ids"] == ["slice.human-visual-contrast-prior-cue"]
    assert human_visual_protocol["report_status"] == "analysis pending"
    assert human_visual_slice["protocol_id"] == "protocol.human-visual-contrast-2afc-keyboard"
    assert human_visual_slice["report_status"] == "missing"
    assert human_visual_dataset["detail_link"] == (
        "dataset-walsh-prior-cue-human-contrast-osf.html"
    )
    assert not any(
        item["source_issue_id"]
        == "protocol_without_dataset::protocol.human-visual-contrast-2afc-keyboard"
        for item in queue_payload["items"]
    )
    assert not any(
        item["source_issue_id"]
        == "protocol_without_slice::protocol.human-visual-contrast-2afc-keyboard"
        for item in queue_payload["items"]
    )
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
    assert human_rdm_protocol["dataset_ids"] == [
        "dataset.palmer-huk-shadlen-human-rdm-cosmo2017"
    ]
    assert human_rdm_protocol["slice_ids"] == ["slice.human-random-dot-motion"]
    assert human_rdm_protocol["report_status"] == "analysis pending"
    assert human_rdm_slice["protocol_id"] == "protocol.human-rdm-button-reaction-time"
    assert human_rdm_slice["report_status"] == "missing"
    assert human_rdm_dataset["detail_link"] == (
        "dataset-palmer-huk-shadlen-human-rdm-cosmo2017.html"
    )
    assert human_rdm_dataset["source_data_level"] == "processed-trial"
    assert macaque_confidence_protocol["dataset_ids"] == [
        "dataset.khalvati-kiani-rao-rdm-confidence-source-data"
    ]
    assert macaque_confidence_protocol["slice_ids"] == [
        "slice.macaque-rdm-confidence-wager"
    ]
    assert macaque_confidence_protocol["report_status"] == "analysis pending"
    assert macaque_confidence_slice["protocol_id"] == "protocol.macaque-rdm-confidence-wager"
    assert macaque_confidence_slice["source_data_level"] == "figure-source-data"
    assert macaque_confidence_slice["report_status"] == "missing"
    assert macaque_confidence_dataset["detail_link"] == (
        "dataset-khalvati-kiani-rao-rdm-confidence-source-data.html"
    )
    assert macaque_confidence_dataset["source_data_level"] == "figure-source-data"
    assert rdm_slice["primary_link"] == "random_dot_motion/roitman-shadlen-pyddm/report.html"
    assert rdm_slice["source_data_level"] == "processed-trial"
    assert loaded["catalog_schema_version"] == "0.1.0"
    assert loaded["health"]["source_data_level_counts"]["figure-source-data"] == 1
    assert "Browse Protocols" in html
    assert "Protocol Catalog" in html
    assert "MVP Health" in html
    assert "Source level" in html
    assert 'href="protocol-random-dot-motion-classic-macaque.html"' in html
    assert 'href="dataset-roitman-shadlen-rdm-pyddm.html"' in html
    assert 'href="graph.html"' in html
    assert 'href="curation_queue.html"' in html
    assert "Relationship Graph" in graph_html
    assert "Graph QA" in graph_html
    assert 'href="curation_queue.html"' in graph_html
    assert "missing_protocol_reciprocal" not in graph_html
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
    assert "Human Random-Dot Motion" in html
    assert "Human Visual Contrast Prior Cue" in html
    assert "figure-source-data" in html
    assert "signed motion coherence" in html
    assert "signed contrast difference" in html
    assert "Curation Queue" in queue_html
    assert "No curation queue items available." in queue_html
    assert 'href="protocol-human-rdm-button-reaction-time.html"' not in queue_html
