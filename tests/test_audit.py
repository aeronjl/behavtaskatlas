"""Tests for the pooled vs by-subject reproducibility audit."""

from __future__ import annotations

from datetime import date

from behavtaskatlas.audit import audit_pooled_vs_by_subject, format_audit_report
from behavtaskatlas.models import (
    CurvePoint,
    Finding,
    Provenance,
    ResultCurve,
    StratificationKey,
)


def _provenance() -> Provenance:
    return Provenance(
        curators=["test"],
        created=date(2026, 4, 28),
        updated=date(2026, 4, 28),
    )


def _make_finding(
    *,
    fid: str,
    paper_id: str,
    points: list[tuple[float, int, float]],
    subject_id: str | None = None,
    curve_type: str = "psychometric",
) -> Finding:
    return Finding(
        object_type="finding",
        schema_version="0.1.0",
        id=fid,
        paper_id=paper_id,
        protocol_id="protocol.demo",
        dataset_id="dataset.demo",
        source_data_level="processed-trial",
        stratification=StratificationKey(subject_id=subject_id),
        curve=ResultCurve(
            curve_type=curve_type,
            x_label="Signed evidence",
            x_units="",
            y_label="p_right",
            points=[CurvePoint(x=x, n=n, y=y) for x, n, y in points],
        ),
        extraction_method="harmonized-pipeline",
        provenance=_provenance(),
    )


def test_audit_passes_when_subject_aggregate_matches_pooled() -> None:
    pooled = _make_finding(
        fid="finding.demo.pooled",
        paper_id="paper.demo",
        points=[(-1.0, 200, 0.10), (0.0, 200, 0.50), (1.0, 200, 0.90)],
    )
    s1 = _make_finding(
        fid="finding.demo.subject.s1",
        paper_id="paper.demo",
        subject_id="s1",
        points=[(-1.0, 100, 0.06), (0.0, 100, 0.42), (1.0, 100, 0.94)],
    )
    s2 = _make_finding(
        fid="finding.demo.subject.s2",
        paper_id="paper.demo",
        subject_id="s2",
        points=[(-1.0, 100, 0.14), (0.0, 100, 0.58), (1.0, 100, 0.86)],
    )
    report = audit_pooled_vs_by_subject([pooled, s1, s2])
    assert report["overall_status"] == "ok"
    assert report["overall_max_abs_diff"] == 0.0
    assert len(report["reports"]) == 1
    g = report["reports"][0]
    assert g["status"] == "ok"
    assert g["n_subjects"] == 2
    assert g["n_x_overlap"] == 3
    assert "✓" in format_audit_report(report)


def test_audit_flags_drift_above_tolerance() -> None:
    pooled = _make_finding(
        fid="finding.demo.pooled",
        paper_id="paper.demo",
        points=[(0.0, 200, 0.50)],
    )
    s1 = _make_finding(
        fid="finding.demo.subject.s1",
        paper_id="paper.demo",
        subject_id="s1",
        points=[(0.0, 100, 0.10)],
    )
    s2 = _make_finding(
        fid="finding.demo.subject.s2",
        paper_id="paper.demo",
        subject_id="s2",
        points=[(0.0, 100, 0.20)],
    )
    # Aggregate y = 0.15, pooled = 0.50 -> diff = 0.35.
    report = audit_pooled_vs_by_subject([pooled, s1, s2], tolerance=0.01)
    assert report["overall_status"] == "drift"
    assert report["overall_max_abs_diff"] == 0.35
    assert report["reports"][0]["status"] == "drift"


def test_audit_skips_groups_lacking_pooled_or_subjects() -> None:
    only_subject = _make_finding(
        fid="finding.x.subject.s1",
        paper_id="paper.x",
        subject_id="s1",
        points=[(0.0, 50, 0.5)],
    )
    only_pooled = _make_finding(
        fid="finding.y.pooled",
        paper_id="paper.y",
        points=[(0.0, 50, 0.5)],
    )
    one_subject = _make_finding(
        fid="finding.z.subject.s1",
        paper_id="paper.z",
        subject_id="s1",
        points=[(0.0, 50, 0.5)],
    )
    pooled_z = _make_finding(
        fid="finding.z.pooled",
        paper_id="paper.z",
        points=[(0.0, 50, 0.5)],
    )
    report = audit_pooled_vs_by_subject(
        [only_subject, only_pooled, one_subject, pooled_z]
    )
    # paper.z has 1 pooled + 1 subject -> below the 2-subject minimum.
    assert report["n_groups_audited"] == 0
    assert report["overall_status"] == "ok"


def test_audit_flags_ambiguous_when_multiple_pooled_curves_share_axis() -> None:
    pooled_a = _make_finding(
        fid="finding.dup.pooled.a",
        paper_id="paper.dup",
        points=[(0.0, 100, 0.5)],
    )
    pooled_b = _make_finding(
        fid="finding.dup.pooled.b",
        paper_id="paper.dup",
        points=[(0.0, 100, 0.6)],
    )
    s1 = _make_finding(
        fid="finding.dup.subject.s1",
        paper_id="paper.dup",
        subject_id="s1",
        points=[(0.0, 50, 0.5)],
    )
    s2 = _make_finding(
        fid="finding.dup.subject.s2",
        paper_id="paper.dup",
        subject_id="s2",
        points=[(0.0, 50, 0.5)],
    )
    report = audit_pooled_vs_by_subject([pooled_a, pooled_b, s1, s2])
    assert report["overall_status"] == "warning"
    assert report["reports"][0]["status"] == "ambiguous"
