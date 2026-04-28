"""Reproducibility audit: check pooled vs by-subject findings reconcile."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from behavtaskatlas.models import Finding


def _group_key(finding: Finding) -> tuple[str, str, str, str, str]:
    """Group findings that should sit on the same x-axis. The condition
    field is included so per-cue pooled curves don't get matched against
    aggregates spanning different conditions."""
    return (
        finding.paper_id,
        finding.curve.curve_type,
        finding.curve.x_label,
        finding.curve.x_units,
        finding.stratification.condition or "",
    )


def _is_pooled(finding: Finding) -> bool:
    return not finding.stratification.subject_id


def audit_pooled_vs_by_subject(
    findings: Iterable[Finding],
    *,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """For each (paper × curve_type × axis) group that contains both a
    pooled curve and at least two per-subject curves, recompute the
    n-weighted aggregate of the subject curves at each x value and
    compare to the pooled curve's y value at the same x. Returns a
    structured report summarizing each group plus an overall status.

    Reconciliation tolerance defaults to 0.01 (1 percentage point on a
    [0, 1] axis); set tighter for harmonized-pipeline curves that
    should match exactly.
    """
    by_group: dict[tuple[str, str, str, str], list[Finding]] = defaultdict(list)
    for f in findings:
        by_group[_group_key(f)].append(f)

    reports: list[dict[str, Any]] = []
    overall_max_diff = 0.0
    overall_status = "ok"
    for key, group in sorted(by_group.items()):
        pooled_findings = [f for f in group if _is_pooled(f)]
        subject_findings = [f for f in group if not _is_pooled(f)]
        if not pooled_findings or len(subject_findings) < 2:
            continue
        if len(pooled_findings) > 1:
            reports.append(
                {
                    "paper_id": key[0],
                    "curve_type": key[1],
                    "x_label": key[2],
                    "x_units": key[3],
                    "condition": key[4],
                    "status": "ambiguous",
                    "reason": (
                        f"Found {len(pooled_findings)} pooled curves with the same "
                        "axis; expected exactly one."
                    ),
                    "pooled_finding_ids": [f.id for f in pooled_findings],
                    "subject_finding_ids": [f.id for f in subject_findings],
                }
            )
            overall_status = "warning"
            continue
        pooled = pooled_findings[0]
        agg_n: dict[float, int] = defaultdict(int)
        agg_weighted_y: dict[float, float] = defaultdict(float)
        for f in subject_findings:
            for p in f.curve.points:
                agg_n[p.x] += p.n
                agg_weighted_y[p.x] += p.n * p.y

        per_point: list[dict[str, Any]] = []
        max_diff = 0.0
        n_overlap = 0
        for p in pooled.curve.points:
            n = agg_n.get(p.x, 0)
            if n == 0:
                per_point.append(
                    {"x": p.x, "pooled_y": p.y, "agg_y": None, "abs_diff": None}
                )
                continue
            agg_y = agg_weighted_y[p.x] / n
            diff = abs(p.y - agg_y)
            if diff > max_diff:
                max_diff = diff
            n_overlap += 1
            per_point.append(
                {"x": p.x, "pooled_y": p.y, "agg_y": agg_y, "abs_diff": diff}
            )
        if max_diff > overall_max_diff:
            overall_max_diff = max_diff

        status = "ok" if max_diff <= tolerance else "drift"
        if status == "drift":
            overall_status = "drift"
        elif status == "ok" and overall_status == "ok":
            pass

        reports.append(
            {
                "paper_id": key[0],
                "curve_type": key[1],
                "x_label": key[2],
                "x_units": key[3],
                "condition": key[4],
                "status": status,
                "tolerance": tolerance,
                "max_abs_diff": max_diff,
                "n_pooled_points": len(pooled.curve.points),
                "n_subjects": len(subject_findings),
                "n_x_overlap": n_overlap,
                "pooled_finding_id": pooled.id,
                "subject_finding_ids": sorted(f.id for f in subject_findings),
                "per_point": per_point,
            }
        )

    return {
        "tolerance": tolerance,
        "overall_status": overall_status,
        "overall_max_abs_diff": overall_max_diff,
        "n_groups_audited": len(reports),
        "reports": reports,
    }


def format_audit_report(report: dict[str, Any]) -> str:
    """Render a one-line-per-group human summary of an audit report."""
    lines: list[str] = []
    overall = report["overall_status"]
    lines.append(
        f"Audit: {overall.upper()} — {report['n_groups_audited']} group(s), "
        f"max |diff|={report['overall_max_abs_diff']:.6f} "
        f"(tolerance {report['tolerance']:.4f})."
    )
    for r in report["reports"]:
        condition_suffix = f" [{r['condition']}]" if r.get("condition") else ""
        label = f"{r['paper_id']} / {r['curve_type']}{condition_suffix}"
        if r["status"] == "ambiguous":
            lines.append(f"  ✗ {label}: ambiguous — {r['reason']}")
            continue
        flag = "✓" if r["status"] == "ok" else "✗"
        lines.append(
            f"  {flag} {label}: "
            f"n_subjects={r['n_subjects']}, n_x_overlap={r['n_x_overlap']}, "
            f"max |diff|={r['max_abs_diff']:.6f}"
        )
    return "\n".join(lines)
