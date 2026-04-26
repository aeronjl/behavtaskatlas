import json
from pathlib import Path

from behavtaskatlas.ibl import current_git_commit
from behavtaskatlas.release import (
    build_release_check_payload,
    release_check_html,
    write_release_check_html,
    write_release_check_json,
)
from behavtaskatlas.static_site import (
    build_catalog_payload,
    build_curation_queue_payload,
    build_relationship_graph_payload,
    build_static_index_payload,
    load_vertical_slice_records,
    write_static_catalog_json,
    write_static_curation_queue_json,
    write_static_graph_json,
    write_static_manifest_json,
)

ROOT = Path(__file__).resolve().parents[1]


def test_release_check_accepts_clean_generated_static_artifacts(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    _write_slice_artifacts(derived_dir)
    _write_static_artifacts(derived_dir)

    payload = build_release_check_payload(root=ROOT, derived_dir=derived_dir)
    status_json = derived_dir / "release_status.json"
    status_html = derived_dir / "release_status.html"
    write_release_check_json(status_json, payload)
    write_release_check_html(status_html, payload)

    loaded = json.loads(status_json.read_text(encoding="utf-8"))
    html = status_html.read_text(encoding="utf-8")
    statuses = {item["check_id"]: item["status"] for item in payload["items"]}

    assert not any(item["status"] == "error" for item in payload["items"])
    assert loaded["release_check_schema_version"] == "0.1.0"
    assert payload["counts"]["vertical_slices"] == 8
    assert payload["counts"]["reports_available"] == 8
    assert statuses["static.manifest"] == "ok"
    assert statuses["static.catalog"] == "ok"
    assert statuses["release.curation_queue"] == "ok"
    assert statuses["release.raw_path_links"] == "ok"
    assert "behavtaskatlas Release Check" in html
    assert "Slice report coverage" in html


def test_release_check_rejects_raw_data_links_in_static_payloads(tmp_path) -> None:
    derived_dir = tmp_path / "derived"
    _write_slice_artifacts(derived_dir)
    _write_static_artifacts(derived_dir)

    manifest_path = derived_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["slices"][0]["links"].append(
        {"label": "Raw local file", "href": "data/raw/private.csv"}
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    payload = build_release_check_payload(root=ROOT, derived_dir=derived_dir)
    raw_path_item = next(
        item for item in payload["items"] if item["check_id"] == "release.raw_path_links"
    )

    assert payload["overall_status"] == "error"
    assert raw_path_item["status"] == "error"
    assert raw_path_item["details"]["references"][0]["value"] == "data/raw/private.csv"
    assert "Raw data path exposure" in release_check_html(payload)


def _write_slice_artifacts(derived_dir: Path) -> None:
    commit = current_git_commit()
    for record in load_vertical_slice_records(ROOT):
        report_path = derived_dir / record.report_path
        analysis_path = derived_dir / record.analysis_result_path
        provenance_path = analysis_path.parent / "provenance.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("<html>report</html>", encoding="utf-8")
        analysis_path.write_text(
            json.dumps(
                {
                    "n_trials": 1,
                    "n_response_trials": 1,
                    "summary_rows": [{}],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        provenance_path.write_text(
            json.dumps(
                {
                    "behavtaskatlas_commit": commit,
                    "behavtaskatlas_git_dirty": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def _write_static_artifacts(derived_dir: Path) -> None:
    index_path = derived_dir / "index.html"
    manifest_path = derived_dir / "manifest.json"
    catalog_path = derived_dir / "catalog.html"
    catalog_json_path = derived_dir / "catalog.json"
    graph_path = derived_dir / "graph.html"
    graph_json_path = derived_dir / "graph.json"
    queue_path = derived_dir / "curation_queue.html"
    queue_json_path = derived_dir / "curation_queue.json"

    catalog_payload = build_catalog_payload(
        root=ROOT,
        derived_dir=derived_dir,
        catalog_path=catalog_path,
        catalog_json_path=catalog_json_path,
        report_index_path=index_path,
        graph_path=graph_path,
        graph_json_path=graph_json_path,
        curation_queue_path=queue_path,
    )
    graph_payload = build_relationship_graph_payload(
        catalog_payload,
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
    catalog_payload["health"]["curation_queue"] = queue_payload["counts"]
    manifest_payload = build_static_index_payload(
        root=ROOT,
        derived_dir=derived_dir,
        index_path=index_path,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        graph_path=graph_path,
        curation_queue_path=queue_path,
        queue_counts=queue_payload["counts"],
    )
    for payload in [manifest_payload, catalog_payload, graph_payload, queue_payload]:
        _mark_clean_at_head(payload)

    write_static_manifest_json(manifest_path, manifest_payload)
    write_static_catalog_json(catalog_json_path, catalog_payload)
    write_static_graph_json(graph_json_path, graph_payload)
    write_static_curation_queue_json(queue_json_path, queue_payload)


def _mark_clean_at_head(payload: dict) -> None:
    payload["behavtaskatlas_commit"] = current_git_commit()
    payload["behavtaskatlas_git_dirty"] = False
