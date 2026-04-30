import json
from pathlib import Path

from behavtaskatlas.ibl import DEFAULT_IBL_EID
from behavtaskatlas.static_site import (
    build_catalog_payload,
    build_curation_queue_payload,
    build_relationship_graph_payload,
    build_static_index_payload,
    write_static_catalog_json,
    write_static_curation_queue_json,
    write_static_graph_json,
    write_static_manifest_json,
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

    auditory_slice = next(
        item for item in payload["slices"] if item["id"] == "slice.auditory-clicks"
    )
    assert auditory_slice["report_status"] == "available"
    assert auditory_slice["primary_link"] == "auditory_clicks/report.html"
    ibl_slice = next(
        item for item in payload["slices"] if item["id"] == "slice.ibl-visual-decision"
    )
    assert ibl_slice["artifact_status"] == "available"
    assert ibl_slice["report_status"] == "missing"


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

    rdm_slice = next(item for item in payload["slices"] if item["id"] == "slice.random-dot-motion")
    rdm_row = next(
        item for item in payload["comparison_rows"] if item["slice_id"] == "slice.random-dot-motion"
    )
    assert rdm_slice["report_status"] == "available"
    assert rdm_slice["primary_link"] == "random_dot_motion/roitman-shadlen-pyddm/report.html"
    assert rdm_row["protocol_id"] == "protocol.random-dot-motion-classic-macaque"
    assert rdm_row["stimulus_metric"] == "signed motion coherence"
    assert rdm_row["trial_count"] == 6149


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
    assert len(loaded["comparison_rows"]) == 17
    assert rdm_row["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    assert rdm_row["source_data_level"] == "processed-trial"
    assert rdm_row["trial_count"] == 6149
    assert loaded["health"]["source_data_level_counts"] == {
        "figure-source-data": 1,
        "processed-trial": 12,
        "raw-trial": 4,
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
    graph_payload = build_relationship_graph_payload(
        payload,
        graph_path=graph_path,
        graph_json_path=graph_json_path,
        catalog_path=catalog_path,
        curation_queue_path=queue_path,
    )
    queue_payload = build_curation_queue_payload(
        graph_payload,
        queue_path=queue_path,
        queue_json_path=queue_json_path,
        graph_path=graph_path,
    )
    write_static_catalog_json(catalog_json_path, payload)
    write_static_graph_json(graph_json_path, graph_payload)
    write_static_curation_queue_json(queue_json_path, queue_payload)

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
    port_contrast_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-visual-contrast-port-2afc"
    )
    value_block_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-visual-contrast-wheel-value-blocks"
    )
    temporal_regularities_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-visual-contrast-wheel-temporal-regularities"
    )
    lick_gonogo_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-visual-contrast-lick-gonogo"
    )
    steinmetz_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-unforced-visual-contrast-wheel"
    )
    odoemene_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-visual-flash-rate-accumulation"
    )
    coen_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-audiovisual-spatial-wheel"
    )
    rodgers_protocol = next(
        row
        for row in payload["protocols"]
        if row["protocol_id"] == "protocol.mouse-whisker-object-recognition-lick"
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
    temporal_regularities_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.fritsche-temporal-regularities"
    )
    steinmetz_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.steinmetz-visual-decision"
    )
    zatka_haas_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.zatka-haas-visual-decision"
    )
    odoemene_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.odoemene-visual-accumulation"
    )
    coen_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.coen-audiovisual-spatial-wheel"
    )
    rodgers_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.rodgers-whisker-object-recognition"
    )
    brainwide_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.ibl-brainwide-map-behavior"
    )
    allen_vbn_slice = next(
        row
        for row in payload["vertical_slices"]
        if row["slice_id"] == "slice.allen-visual-behavior-neuropixels"
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
    steinmetz_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.steinmetz-visual-decision-figshare"
    )
    zatka_haas_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.zatka-haas-visual-decision-figshare"
    )
    odoemene_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.odoemene-visual-evidence-accumulation-cshl"
    )
    coen_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.coen-audiovisual-decisions-ucl"
    )
    rodgers_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.rodgers-whisker-object-recognition-dandi"
    )
    brainwide_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.ibl-brainwide-map-2025"
    )
    temporal_regularities_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.fritsche-temporal-regularities-figshare"
    )
    allen_vbn_dataset = next(
        row
        for row in payload["datasets"]
        if row["dataset_id"] == "dataset.allen-visual-behavior-neuropixels"
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

    assert payload["counts"]["task_families"] == 7
    assert payload["counts"]["protocols"] == 18
    assert payload["counts"]["datasets"] == 16
    assert payload["counts"]["vertical_slices"] == 17
    assert payload["counts"]["report_available"] == 1
    assert len(payload["protocol_details"]) == 18
    assert len(payload["dataset_details"]) == 16
    assert graph_payload["counts"]["nodes"] == 58
    assert graph_payload["counts"]["edges"] == 88
    assert graph_payload["counts"]["qa_issues"] == 6
    assert graph_payload["qa_summary"] == {"error": 0, "warning": 0, "info": 6, "total": 6}
    assert loaded_graph["graph_schema_version"] == "0.1.0"
    assert queue_payload["counts"] == {"items": 6, "open": 6}
    assert queue_payload["priority_counts"] == {"normal": 6}
    assert queue_payload["action_counts"] == {
        "needs dataset": 3,
        "needs vertical slice": 3,
    }
    assert loaded_queue["queue_schema_version"] == "0.1.0"
    assert any(
        node["node_id"] == "protocol.random-dot-motion-classic-macaque"
        for node in graph_payload["nodes"]
    )
    assert any(
        node["node_id"] == "dataset.roitman-shadlen-rdm-pyddm"
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
        "source": "protocol.poisson-clicks-evidence-accumulation",
        "target": "protocol.rat-auditory-clicks-nose-poke",
        "edge_type": "protocol_variant",
        "label": "template has variant",
    } in graph_payload["edges"]
    assert {
        "source": "dataset.allen-visual-behavior-neuropixels",
        "target": "slice.allen-visual-behavior-neuropixels",
        "edge_type": "dataset_slice",
        "label": "dataset backs slice",
    } in graph_payload["edges"]
    assert {
        "source": "protocol.mouse-visual-contrast-wheel-temporal-regularities",
        "target": "dataset.fritsche-temporal-regularities-figshare",
        "edge_type": "protocol_dataset",
        "label": "protocol uses dataset",
    } in graph_payload["edges"]
    assert not any(issue["severity"] == "warning" for issue in graph_payload["qa_issues"])
    assert rdm_protocol["dataset_ids"] == ["dataset.roitman-shadlen-rdm-pyddm"]
    assert rdm_protocol["declared_dataset_ids"] == ["dataset.roitman-shadlen-rdm-pyddm"]
    assert rdm_protocol["slice_ids"] == ["slice.random-dot-motion"]
    assert rdm_protocol["report_status"] == "available"
    assert poisson_clicks_protocol["protocol_scope"] == "template"
    assert poisson_clicks_protocol["report_status"] == "no slice"
    assert rat_clicks_protocol["dataset_ids"] == ["dataset.brody-lab-poisson-clicks-2009-2024"]
    assert rat_clicks_protocol["protocol_scope"] == "concrete"
    assert rat_clicks_protocol["template_protocol_id"] == (
        "protocol.poisson-clicks-evidence-accumulation"
    )
    assert rat_clicks_protocol["slice_ids"] == ["slice.auditory-clicks"]
    assert rat_clicks_protocol["report_status"] == "analysis pending"
    assert auditory_slice["protocol_id"] == "protocol.rat-auditory-clicks-nose-poke"
    assert human_clicks_protocol["dataset_ids"] == [
        "dataset.london-human-poisson-clicks-dbs-mendeley"
    ]
    assert human_clicks_protocol["slice_ids"] == ["slice.human-auditory-clicks-dbs"]
    assert human_clicks_protocol["report_status"] == "analysis pending"
    assert human_clicks_slice["protocol_id"] == "protocol.human-auditory-clicks-button"
    assert human_clicks_slice["report_status"] == "missing"
    assert mouse_unbiased_protocol["dataset_ids"] == ["dataset.ibl-public-behavior"]
    assert mouse_unbiased_protocol["slice_ids"] == ["slice.mouse-visual-contrast-unbiased"]
    assert mouse_unbiased_protocol["report_status"] == "analysis pending"
    assert port_contrast_protocol["dataset_ids"] == []
    assert port_contrast_protocol["slice_ids"] == []
    assert port_contrast_protocol["report_status"] == "no slice"
    assert value_block_protocol["dataset_ids"] == []
    assert value_block_protocol["slice_ids"] == []
    assert value_block_protocol["report_status"] == "no slice"
    assert temporal_regularities_protocol["dataset_ids"] == [
        "dataset.fritsche-temporal-regularities-figshare"
    ]
    assert temporal_regularities_protocol["declared_dataset_ids"] == [
        "dataset.fritsche-temporal-regularities-figshare"
    ]
    assert temporal_regularities_protocol["slice_ids"] == [
        "slice.fritsche-temporal-regularities"
    ]
    assert temporal_regularities_protocol["report_status"] == "analysis pending"
    assert lick_gonogo_protocol["dataset_ids"] == []
    assert lick_gonogo_protocol["slice_ids"] == []
    assert lick_gonogo_protocol["report_status"] == "no slice"
    assert mouse_unbiased_slice["protocol_id"] == "protocol.mouse-visual-contrast-wheel-unbiased"
    assert mouse_unbiased_slice["report_status"] == "missing"
    assert temporal_regularities_slice["protocol_id"] == (
        "protocol.mouse-visual-contrast-wheel-temporal-regularities"
    )
    assert temporal_regularities_slice["dataset_id"] == (
        "dataset.fritsche-temporal-regularities-figshare"
    )
    assert temporal_regularities_slice["source_data_level"] == "processed-trial"
    assert temporal_regularities_slice["report_status"] == "missing"
    assert steinmetz_protocol["dataset_ids"] == [
        "dataset.steinmetz-visual-decision-figshare",
        "dataset.zatka-haas-visual-decision-figshare",
    ]
    assert steinmetz_protocol["slice_ids"] == [
        "slice.steinmetz-visual-decision",
        "slice.zatka-haas-visual-decision",
    ]
    assert steinmetz_protocol["report_status"] == "analysis pending"
    assert steinmetz_slice["protocol_id"] == "protocol.mouse-unforced-visual-contrast-wheel"
    assert steinmetz_slice["source_data_level"] == "processed-trial"
    assert steinmetz_slice["report_status"] == "missing"
    assert zatka_haas_slice["protocol_id"] == "protocol.mouse-unforced-visual-contrast-wheel"
    assert zatka_haas_slice["dataset_id"] == "dataset.zatka-haas-visual-decision-figshare"
    assert zatka_haas_slice["source_data_level"] == "processed-trial"
    assert zatka_haas_slice["report_status"] == "missing"
    assert odoemene_protocol["dataset_ids"] == [
        "dataset.odoemene-visual-evidence-accumulation-cshl"
    ]
    assert odoemene_protocol["slice_ids"] == ["slice.odoemene-visual-accumulation"]
    assert odoemene_protocol["report_status"] == "analysis pending"
    assert odoemene_slice["protocol_id"] == "protocol.mouse-visual-flash-rate-accumulation"
    assert odoemene_slice["source_data_level"] == "raw-trial"
    assert odoemene_slice["report_status"] == "missing"
    assert coen_protocol["dataset_ids"] == ["dataset.coen-audiovisual-decisions-ucl"]
    assert coen_protocol["slice_ids"] == ["slice.coen-audiovisual-spatial-wheel"]
    assert coen_protocol["report_status"] == "analysis pending"
    assert coen_slice["protocol_id"] == "protocol.mouse-audiovisual-spatial-wheel"
    assert coen_slice["source_data_level"] == "processed-trial"
    assert coen_slice["report_status"] == "missing"
    assert rodgers_protocol["dataset_ids"] == [
        "dataset.rodgers-whisker-object-recognition-dandi"
    ]
    assert rodgers_protocol["slice_ids"] == ["slice.rodgers-whisker-object-recognition"]
    assert rodgers_protocol["report_status"] == "analysis pending"
    assert rodgers_slice["protocol_id"] == "protocol.mouse-whisker-object-recognition-lick"
    assert rodgers_slice["source_data_level"] == "processed-trial"
    assert rodgers_slice["report_status"] == "missing"
    assert brainwide_slice["protocol_id"] == "protocol.ibl-visual-decision-v1"
    assert brainwide_slice["dataset_id"] == "dataset.ibl-brainwide-map-2025"
    assert brainwide_slice["source_data_level"] == "processed-trial"
    assert brainwide_slice["report_status"] == "missing"
    assert allen_vbn_slice["protocol_id"] == "protocol.mouse-visual-change-detection-allen"
    assert allen_vbn_slice["dataset_id"] == "dataset.allen-visual-behavior-neuropixels"
    assert allen_vbn_slice["source_data_level"] == "raw-trial"
    assert allen_vbn_slice["report_status"] == "missing"
    assert human_visual_protocol["dataset_ids"] == [
        "dataset.walsh-prior-cue-human-contrast-osf"
    ]
    assert human_visual_protocol["slice_ids"] == ["slice.human-visual-contrast-prior-cue"]
    assert human_visual_slice["protocol_id"] == "protocol.human-visual-contrast-2afc-keyboard"
    assert human_visual_slice["report_status"] == "missing"
    assert rdm_detail["stimulus"]["evidence_type"] == "stochastic-motion"
    assert rdm_detail["choice"]["response_modalities"] == ["saccade"]
    assert rdm_detail["datasets"][0]["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    assert rdm_detail["vertical_slices"][0]["primary_link"] == (
        "random_dot_motion/roitman-shadlen-pyddm/report.html"
    )
    assert rdm_dataset_detail["protocols"][0]["protocol_id"] == (
        "protocol.random-dot-motion-classic-macaque"
    )
    assert rdm_dataset_detail["vertical_slices"][0]["primary_link"] == (
        "random_dot_motion/roitman-shadlen-pyddm/report.html"
    )
    assert human_rdm_protocol["dataset_ids"] == [
        "dataset.palmer-huk-shadlen-human-rdm-cosmo2017"
    ]
    assert human_rdm_protocol["slice_ids"] == ["slice.human-random-dot-motion"]
    assert human_rdm_protocol["report_status"] == "analysis pending"
    assert human_rdm_slice["protocol_id"] == "protocol.human-rdm-button-reaction-time"
    assert human_rdm_slice["report_status"] == "missing"
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
    assert macaque_confidence_dataset["source_data_level"] == "figure-source-data"
    assert rdm_slice["primary_link"] == "random_dot_motion/roitman-shadlen-pyddm/report.html"
    assert rdm_slice["source_data_level"] == "processed-trial"
    assert rdm_dataset["dataset_id"] == "dataset.roitman-shadlen-rdm-pyddm"
    assert human_clicks_dataset["dataset_id"] == "dataset.london-human-poisson-clicks-dbs-mendeley"
    assert human_visual_dataset["dataset_id"] == "dataset.walsh-prior-cue-human-contrast-osf"
    assert steinmetz_dataset["slice_ids"] == ["slice.steinmetz-visual-decision"]
    assert zatka_haas_dataset["slice_ids"] == ["slice.zatka-haas-visual-decision"]
    assert odoemene_dataset["slice_ids"] == ["slice.odoemene-visual-accumulation"]
    assert coen_dataset["slice_ids"] == ["slice.coen-audiovisual-spatial-wheel"]
    assert rodgers_dataset["slice_ids"] == ["slice.rodgers-whisker-object-recognition"]
    assert brainwide_dataset["slice_ids"] == ["slice.ibl-brainwide-map-behavior"]
    assert temporal_regularities_dataset["slice_ids"] == [
        "slice.fritsche-temporal-regularities"
    ]
    assert allen_vbn_dataset["slice_ids"] == ["slice.allen-visual-behavior-neuropixels"]
    assert loaded["catalog_schema_version"] == "0.1.0"
    assert loaded["health"]["source_data_level_counts"]["figure-source-data"] == 1
