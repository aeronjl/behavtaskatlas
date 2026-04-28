"""Findings extraction and indexing for the cross-paper meta-analysis route.

This module turns slice-level summary CSVs into Finding records (one
per stratification group), and walks every Paper + Finding YAML in the
repository into a denormalized FindingsIndexPayload that the Astro
build consumes statically.

Slice extraction is intentionally narrow: it currently understands the
psychometric_summary.csv format (signed-evidence axis, p_right by
prior_context group). Other curve types — chronometric, accuracy by
strength, hit-rate by image pair — get their own helpers as we add
findings that need them rather than upfront.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from behavtaskatlas.models import (
    CurvePoint,
    Finding,
    FindingsIndexCurvePoint,
    FindingsIndexEntry,
    FindingsIndexPayload,
    Paper,
    Protocol,
    Provenance,
    ResultCurve,
    StratificationKey,
    TaskFamily,
    VerticalSlice,
)

# ---------------------------------------------------------------------------
# Slice extraction
# ---------------------------------------------------------------------------


def _slice_derived_dir(slice_record: VerticalSlice, derived_dir: Path) -> Path:
    return (derived_dir / slice_record.report_path).parent


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _to_float(value: str) -> float | None:
    if value == "" or value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str) -> int | None:
    if value == "" or value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _today_provenance(curators: list[str] | None = None) -> Provenance:
    today = date.today()
    return Provenance(
        curators=curators or ["behavtaskatlas"],
        created=today,
        updated=today,
        source_notes=(
            "Extracted from a vertical-slice psychometric summary by "
            "behavtaskatlas.findings.extract_psychometric_findings_for_slice."
        ),
    )


def extract_psychometric_findings_for_slice(
    slice_record: VerticalSlice,
    *,
    paper_id: str,
    derived_dir: Path,
    finding_id_prefix: str,
    x_label: str,
    x_units: str,
    summary_filename: str = "psychometric_summary.csv",
) -> list[Finding]:
    """Build one Finding per prior_context group from the slice's
    psychometric_summary.csv. If the prior_context column is empty
    everywhere, return a single ungrouped Finding.

    The slice must point at one dataset and one protocol; the resulting
    findings inherit those plus the slice's source_data_level so the
    cross-ref validator passes.
    """
    summary_path = _slice_derived_dir(slice_record, derived_dir) / summary_filename
    if not summary_path.exists():
        raise FileNotFoundError(f"summary CSV not found at {summary_path}")

    rows = _read_csv_rows(summary_path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        ctx = (row.get("prior_context") or "").strip()
        grouped[ctx].append(row)

    findings: list[Finding] = []
    for ctx, ctx_rows in sorted(grouped.items(), key=lambda item: item[0]):
        points: list[CurvePoint] = []
        for row in ctx_rows:
            x = _to_float(row.get("stimulus_value", ""))
            y = _to_float(row.get("p_right", ""))
            n = _to_int(row.get("n_response", "")) or _to_int(row.get("n_trials", ""))
            if x is None or y is None or n is None:
                continue
            points.append(CurvePoint(x=x, n=n, y=y))
        if not points:
            continue
        points.sort(key=lambda p: p.x)
        n_trials_total = sum(int(p.n) for p in points)
        if ctx:
            condition = ctx
            slug = ctx.replace("=", "-").replace(" ", "-").lower()
            finding_id = f"{finding_id_prefix}.{slug}"
        else:
            condition = None
            finding_id = finding_id_prefix
        finding = Finding(
            object_type="finding",
            schema_version="0.1.0",
            id=finding_id,
            paper_id=paper_id,
            protocol_id=slice_record.protocol_id,
            dataset_id=slice_record.dataset_id,
            slice_id=slice_record.id,
            source_data_level=slice_record.comparison.source_data_level,
            n_trials=n_trials_total,
            n_subjects=None,
            stratification=StratificationKey(condition=condition),
            curve=ResultCurve(
                curve_type="psychometric",
                x_label=x_label,
                x_units=x_units,
                y_label="p_right",
                points=points,
            ),
            extraction_method="harmonized-pipeline",
            extraction_notes=(
                f"Aggregated from {summary_path.name} for "
                f"prior_context={ctx or 'all'!r}."
            ),
            provenance=_today_provenance(),
        )
        findings.append(finding)
    return findings


def write_finding_yaml(finding: Finding, papers_root: Path | None = None) -> Path:
    """Serialize a Finding to findings/<slug>.yaml. Returns the written
    path. The slug derives from the finding id: drop the "finding."
    prefix, replace dots with slashes? No — keep dots so the filename
    mirrors the id."""
    slug = finding.id.removeprefix("finding.")
    findings_dir = (papers_root or Path(".")) / "findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    path = findings_dir / f"{slug}.yaml"
    payload = finding.model_dump(mode="json", exclude_none=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------


def build_findings_index(
    *,
    papers: Iterable[Paper],
    findings: Iterable[Finding],
    protocols: Iterable[Protocol],
    families: Iterable[TaskFamily],
    title: str = "behavtaskatlas Findings Index",
    commit: str | None = None,
    git_dirty: bool | None = None,
) -> dict[str, Any]:
    """Walk every Paper + Finding into a denormalized FindingsIndexPayload
    suitable for the Astro overlay route to consume statically.

    Each entry inlines paper citation, protocol/family names, and the
    curve points so the front-end never has to follow id references.
    """
    paper_by_id = {p.id: p for p in papers}
    protocol_by_id = {p.id: p for p in protocols}
    family_by_id = {f.id: f for f in families}

    entries: list[FindingsIndexEntry] = []
    for finding in findings:
        paper = paper_by_id.get(finding.paper_id)
        if paper is None:
            continue
        protocol = protocol_by_id.get(finding.protocol_id)
        family = (
            family_by_id.get(protocol.family_id) if protocol is not None else None
        )
        if protocol is None:
            continue
        species = paper.species[0] if paper.species else None
        evidence_type = protocol.stimulus.evidence_type if protocol else None
        response_modality = (
            protocol.choice.response_modalities[0]
            if protocol and protocol.choice.response_modalities
            else None
        )
        index_points = [
            FindingsIndexCurvePoint(
                x=p.x,
                n=p.n,
                y=p.y,
                y_lower=p.y_lower,
                y_upper=p.y_upper,
            )
            for p in finding.curve.points
        ]
        entries.append(
            FindingsIndexEntry(
                finding_id=finding.id,
                paper_id=paper.id,
                paper_citation=paper.citation,
                paper_year=paper.year,
                paper_lab=paper.lab,
                paper_doi=paper.doi,
                protocol_id=finding.protocol_id,
                protocol_name=protocol.name if protocol else finding.protocol_id,
                family_id=protocol.family_id if protocol else "",
                family_name=family.name if family else None,
                dataset_id=finding.dataset_id,
                slice_id=finding.slice_id,
                species=finding.stratification.species or species,
                modalities=list(protocol.stimulus.modalities) if protocol else [],
                evidence_type=evidence_type,
                response_modality=(
                    finding.stratification.response_modality or response_modality
                ),
                source_data_level=finding.source_data_level,
                extraction_method=finding.extraction_method,
                n_trials=finding.n_trials,
                n_subjects=finding.n_subjects or paper.n_subjects,
                stratification=finding.stratification,
                curve_type=finding.curve.curve_type,
                x_label=finding.curve.x_label,
                x_units=finding.curve.x_units,
                y_label=finding.curve.y_label,
                points=index_points,
            )
        )

    counts = {
        "papers": len(paper_by_id),
        "findings": len(entries),
        "psychometric": sum(1 for e in entries if e.curve_type == "psychometric"),
        "chronometric": sum(1 for e in entries if e.curve_type == "chronometric"),
    }

    payload = FindingsIndexPayload(
        findings_schema_version="0.1.0",
        title=title,
        generated_at=datetime.now(UTC).isoformat(),
        behavtaskatlas_commit=commit,
        behavtaskatlas_git_dirty=git_dirty,
        counts=counts,
        findings=entries,
    )
    return payload.model_dump(mode="json")
