import json

from behavtaskatlas.ibl import DEFAULT_IBL_EID
from behavtaskatlas.static_site import build_static_index_payload, static_index_html


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
