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
    Comparison,
    ComparisonsIndexEntry,
    ComparisonsIndexPayload,
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


def extract_chronometric_findings_for_slice(
    slice_record: VerticalSlice,
    *,
    paper_id: str,
    derived_dir: Path,
    finding_id_prefix: str,
    x_label: str = "Absolute evidence strength",
    x_units: str = "",
    summary_filename: str = "chronometric_summary.csv",
) -> list[Finding]:
    """Build a chronometric Finding from the slice's chronometric_summary.csv.
    The CSV is expected to have one row per absolute-evidence level with
    n_trials, n_correct, and median_response_time columns; the resulting
    curve plots median RT (in seconds) against absolute evidence."""
    summary_path = _slice_derived_dir(slice_record, derived_dir) / summary_filename
    if not summary_path.exists():
        raise FileNotFoundError(f"summary CSV not found at {summary_path}")

    rows = _read_csv_rows(summary_path)
    points: list[CurvePoint] = []
    for row in rows:
        x = _to_float(row.get("evidence_strength", ""))
        y = _to_float(row.get("median_response_time", ""))
        n = _to_int(row.get("n_response", "")) or _to_int(row.get("n_trials", ""))
        if x is None or y is None or n is None:
            continue
        points.append(CurvePoint(x=x, n=n, y=y))
    if not points:
        return []
    points.sort(key=lambda p: p.x)
    n_trials_total = sum(int(p.n) for p in points)
    finding = Finding(
        object_type="finding",
        schema_version="0.1.0",
        id=finding_id_prefix,
        paper_id=paper_id,
        protocol_id=slice_record.protocol_id,
        dataset_id=slice_record.dataset_id,
        slice_id=slice_record.id,
        source_data_level=slice_record.comparison.source_data_level,
        n_trials=n_trials_total,
        stratification=StratificationKey(),
        curve=ResultCurve(
            curve_type="chronometric",
            x_label=x_label,
            x_units=x_units,
            y_label="median_rt_s",
            points=points,
        ),
        extraction_method="harmonized-pipeline",
        extraction_notes=(
            f"Aggregated from {summary_path.name}; median response time per "
            "absolute evidence level."
        ),
        provenance=_today_provenance(),
    )
    return [finding]


def extract_accuracy_findings_for_slice(
    slice_record: VerticalSlice,
    *,
    paper_id: str,
    derived_dir: Path,
    finding_id_prefix: str,
    x_label: str = "Absolute evidence strength",
    x_units: str = "",
    summary_filename: str = "accuracy_summary.csv",
    x_column: str = "motion_strength_percent",
    y_column: str = "p_correct",
    n_column: str = "n_source_rows",
    groupby_columns: tuple[str, ...] = ("source_measure", "monkey"),
) -> list[Finding]:
    """Build accuracy_by_strength Findings from a slice's accuracy summary.
    Groups rows by groupby_columns; emits one Finding per group with curve
    points sorted by x. Defaults are tuned for the macaque RDM confidence
    slice (one row per source_measure × monkey × motion_strength_percent).
    """
    summary_path = _slice_derived_dir(slice_record, derived_dir) / summary_filename
    if not summary_path.exists():
        raise FileNotFoundError(f"summary CSV not found at {summary_path}")

    rows = _read_csv_rows(summary_path)
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(col, "") or "" for col in groupby_columns)
        grouped[key].append(row)

    findings: list[Finding] = []
    for key, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
        points: list[CurvePoint] = []
        for row in group_rows:
            x = _to_float(row.get(x_column, ""))
            y = _to_float(row.get(y_column, ""))
            n = _to_int(row.get(n_column, ""))
            if x is None or y is None or n is None:
                continue
            points.append(CurvePoint(x=x, n=n, y=y))
        if not points:
            continue
        points.sort(key=lambda p: p.x)
        n_trials_total = sum(int(p.n) for p in points)
        slug_parts = [str(part).replace("_", "-").lower() for part in key if part]
        slug = ".".join(slug_parts) if slug_parts else "all"
        finding_id = f"{finding_id_prefix}.{slug}"
        # Map first groupby column into stratification.condition,
        # remaining into subject_id (best-effort fit for source_measure/monkey).
        condition = key[0] if len(key) >= 1 and key[0] else None
        subject_id = key[1] if len(key) >= 2 and key[1] else None
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
            stratification=StratificationKey(
                condition=condition,
                subject_id=subject_id,
            ),
            curve=ResultCurve(
                curve_type="accuracy_by_strength",
                x_label=x_label,
                x_units=x_units,
                y_label="p_correct",
                points=points,
            ),
            extraction_method="harmonized-pipeline",
            extraction_notes=(
                f"Aggregated from {summary_path.name} for groupby="
                f"{tuple(zip(groupby_columns, key, strict=False))}."
            ),
            provenance=_today_provenance(),
        )
        findings.append(finding)
    return findings


def _fit_logistic_4p(
    points: list[CurvePoint],
    *,
    force_lower: float | None = None,
    target_y: float = 0.75,
) -> dict[str, float] | None:
    """4-parameter logistic fit (μ, σ, γ, λ) via scipy.curve_fit.
    Mirrors the JS-side fitter on /findings so build-time fits and
    interactive bootstrap fits agree. Returns None when the fit fails or
    has too few points.

    For accuracy_by_strength curves the lower asymptote is pinned at the
    chance floor (e.g. 0.5) so the fit doesn't slide γ below chance.
    Returns the threshold (x at target_y) numerically.
    """
    if len(points) < 4:
        return None
    try:
        import numpy as np
        from scipy import optimize
    except ImportError:
        return None

    xs = np.array([p.x for p in points], dtype=float)
    ys = np.array([p.y for p in points], dtype=float)
    ns = np.array([max(p.n, 1) for p in points], dtype=float)
    sigma_w = 1.0 / np.sqrt(ns)
    mu0 = float(np.mean(xs))
    span = float(np.max(xs) - np.min(xs)) or 1.0
    sigma0 = max(span / 4.0, 1e-3)

    def _logistic4(x, mu, sigma, gamma, lapse):
        sig = max(float(sigma), 1e-6)
        return gamma + (1.0 - gamma - lapse) / (1.0 + np.exp(-(x - mu) / sig))

    try:
        if force_lower is not None:
            def _model(x, mu, sigma, lapse):
                return _logistic4(x, mu, sigma, force_lower, lapse)
            popt, _ = optimize.curve_fit(
                _model, xs, ys,
                p0=[mu0, sigma0, 0.05],
                sigma=sigma_w, absolute_sigma=False,
                bounds=([-np.inf, 1e-3, 0.0], [np.inf, np.inf, 0.49]),
                maxfev=4000,
            )
            mu, sigma, lapse = popt
            gamma = float(force_lower)
        else:
            popt, _ = optimize.curve_fit(
                _logistic4, xs, ys,
                p0=[mu0, sigma0, 0.05, 0.05],
                sigma=sigma_w, absolute_sigma=False,
                bounds=([-np.inf, 1e-3, 0.0, 0.0], [np.inf, np.inf, 0.49, 0.49]),
                maxfev=4000,
            )
            mu, sigma, gamma, lapse = popt
            gamma = float(gamma)
    except Exception:
        return None

    span = 1.0 - gamma - float(lapse)
    threshold: float | None = None
    if span > 0:
        z = (target_y - gamma) / span
        if 0.0 < z < 1.0:
            threshold = float(mu - max(float(sigma), 1e-6) * np.log((1.0 - z) / z))

    payload: dict[str, float] = {
        "mu": float(mu),
        "sigma": float(sigma),
        "gamma": gamma,
        "lapse": float(lapse),
        "threshold_target_y": float(target_y),
    }
    if threshold is not None:
        payload["threshold"] = threshold
    return payload


def _fit_target_y(curve_type: str) -> float:
    if curve_type == "accuracy_by_strength":
        return 0.84
    return 0.75


def _fit_force_lower(curve_type: str) -> float | None:
    if curve_type == "accuracy_by_strength":
        return 0.5
    return None


def import_csv_findings(
    *,
    csv_path: Path,
    paper_id: str,
    protocol_id: str,
    finding_id_prefix: str,
    source_data_level: str,
    extraction_method: str,
    curve_type: str,
    x_label: str,
    x_units: str,
    y_label: str,
    x_column: str,
    y_column: str,
    n_column: str,
    groupby_columns: tuple[str, ...] = (),
    dataset_id: str | None = None,
    extraction_notes: str | None = None,
) -> list[Finding]:
    """Generic CSV → Finding importer for the supplement-csv,
    figure-trace, and table-transcription paths. Group rows by
    groupby_columns, emit one Finding per group with curve points
    sorted by x.

    Unlike the slice extractors, this does not assume a slice
    record exists; the caller supplies paper_id, protocol_id,
    optional dataset_id, source_data_level, and extraction_method
    directly. The CSV's column names for x, y, n (and the groupby
    columns) are configurable per paper.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    if extraction_method not in {"supplement-csv", "figure-trace", "table-transcription"}:
        raise ValueError(
            f"extraction_method must be supplement-csv, figure-trace, or "
            f"table-transcription; got {extraction_method!r}"
        )

    rows = _read_csv_rows(csv_path)
    if groupby_columns:
        grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            key = tuple(row.get(col, "") or "" for col in groupby_columns)
            grouped[key].append(row)
    else:
        grouped = {(): rows}

    findings: list[Finding] = []
    for key, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
        points: list[CurvePoint] = []
        for row in group_rows:
            x = _to_float(row.get(x_column, ""))
            y = _to_float(row.get(y_column, ""))
            n = _to_int(row.get(n_column, ""))
            if x is None or y is None or n is None:
                continue
            points.append(CurvePoint(x=x, n=n, y=y))
        if not points:
            continue
        points.sort(key=lambda p: p.x)
        n_trials_total = sum(int(p.n) for p in points)
        slug_parts = [str(part).replace("_", "-").lower() for part in key if part]
        slug = ".".join(slug_parts) if slug_parts else "all"
        finding_id = f"{finding_id_prefix}.{slug}" if slug != "all" else finding_id_prefix
        condition = key[0] if len(key) >= 1 and key[0] else None
        subject_id = key[1] if len(key) >= 2 and key[1] else None
        finding = Finding(
            object_type="finding",
            schema_version="0.1.0",
            id=finding_id,
            paper_id=paper_id,
            protocol_id=protocol_id,
            dataset_id=dataset_id,
            source_data_level=source_data_level,
            n_trials=n_trials_total,
            stratification=StratificationKey(
                condition=condition,
                subject_id=subject_id,
            ),
            curve=ResultCurve(
                curve_type=curve_type,  # type: ignore[arg-type]
                x_label=x_label,
                x_units=x_units,
                y_label=y_label,
                points=points,
            ),
            extraction_method=extraction_method,  # type: ignore[arg-type]
            extraction_notes=extraction_notes
            or (
                f"Imported from {csv_path.name} via "
                f"behavtaskatlas.findings.import_csv_findings."
            ),
            provenance=_today_provenance(),
        )
        findings.append(finding)
    return findings


def load_import_mapping(mapping_path: Path) -> dict[str, Any]:
    """Load a YAML import-mapping file describing how a CSV maps to
    Finding fields. Schema:

        paper_id: paper.foo
        protocol_id: protocol.bar
        dataset_id: dataset.baz             # optional
        source_data_level: figure-source-data
        extraction_method: supplement-csv   # or figure-trace / table-transcription
        curve_type: psychometric
        x_label: Signed coherence
        x_units: percent
        y_label: p_right
        x_column: coherence
        y_column: p_right
        n_column: n
        groupby_columns: [monkey]            # optional
        finding_id_prefix: finding.foo.psychometric
        extraction_notes: ...                 # optional
    """
    return yaml.safe_load(mapping_path.read_text(encoding="utf-8"))


def extract_subject_psychometric_findings_for_slice(
    slice_record: VerticalSlice,
    *,
    paper_id: str,
    derived_dir: Path,
    finding_id_prefix: str,
    x_label: str = "Signed evidence",
    x_units: str = "",
    trials_filename: str = "trials.csv",
    min_points: int = 4,
) -> list[Finding]:
    """Build one psychometric Finding per subject_id from the slice's
    canonical trials.csv. Used for slices whose summary CSV is pooled
    across subjects but whose trial-level data carries subject_id —
    e.g. Roitman (2 macaques), Palmer-Huk-Shadlen (6 observers).

    Subjects with fewer than `min_points` distinct stimulus values are
    skipped; that filter prevents the index from filling up with sparse
    near-no-response curves from training-stage subjects.
    """
    trials_path = _slice_derived_dir(slice_record, derived_dir) / trials_filename
    if not trials_path.exists():
        raise FileNotFoundError(f"trials CSV not found at {trials_path}")

    rows = _read_csv_rows(trials_path)
    by_subject: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        subject = (row.get("subject_id") or "").strip()
        if not subject:
            continue
        choice = (row.get("choice") or "").strip()
        if choice not in {"left", "right"}:
            continue
        by_subject[subject].append(row)

    findings: list[Finding] = []
    for subject in sorted(by_subject.keys()):
        subject_rows = by_subject[subject]
        agg: dict[float, list[int]] = defaultdict(lambda: [0, 0])  # [n, n_right]
        for row in subject_rows:
            x = _to_float(row.get("stimulus_value", ""))
            if x is None:
                continue
            agg[x][0] += 1
            if row.get("choice") == "right":
                agg[x][1] += 1
        points: list[CurvePoint] = []
        for x in sorted(agg.keys()):
            n, n_right = agg[x]
            if n == 0:
                continue
            points.append(CurvePoint(x=x, n=n, y=n_right / n))
        if len(points) < min_points:
            continue
        slug = (
            subject.replace("/", "-")
            .replace(".", "-")
            .replace("_", "-")
            .lower()
        )
        n_trials_total = sum(int(p.n) for p in points)
        finding = Finding(
            object_type="finding",
            schema_version="0.1.0",
            id=f"{finding_id_prefix}.{slug}",
            paper_id=paper_id,
            protocol_id=slice_record.protocol_id,
            dataset_id=slice_record.dataset_id,
            slice_id=slice_record.id,
            source_data_level=slice_record.comparison.source_data_level,
            n_trials=n_trials_total,
            n_subjects=1,
            stratification=StratificationKey(subject_id=subject),
            curve=ResultCurve(
                curve_type="psychometric",
                x_label=x_label,
                x_units=x_units,
                y_label="p_right",
                points=points,
            ),
            extraction_method="harmonized-pipeline",
            extraction_notes=(
                f"Aggregated per trial from {trials_path.name} for "
                f"subject_id={subject!r}; per-subject psychometric."
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
        fit_payload: dict[str, float] | None = None
        if finding.curve.curve_type in ("psychometric", "accuracy_by_strength"):
            fit_payload = _fit_logistic_4p(
                finding.curve.points,
                force_lower=_fit_force_lower(finding.curve.curve_type),
                target_y=_fit_target_y(finding.curve.curve_type),
            )
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
                fit=fit_payload,
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


def build_comparisons_index(
    *,
    comparisons: Iterable[Comparison],
    title: str = "behavtaskatlas Comparisons Index",
    commit: str | None = None,
    git_dirty: bool | None = None,
) -> dict[str, Any]:
    """Walk every Comparison record into a denormalized
    ComparisonsIndexPayload sorted by display_order. Astro reads this from
    derived/comparisons.json and renders one section per entry on /compare.
    """
    items = sorted(
        comparisons,
        key=lambda c: (c.display_order, c.id),
    )
    entries = [
        ComparisonsIndexEntry(
            id=c.id,
            title=c.title,
            question=c.question,
            framing=c.framing,
            finding_ids=list(c.finding_ids),
            color_by=c.color_by,
            hint=c.hint,
            display_order=c.display_order,
        )
        for c in items
    ]
    payload = ComparisonsIndexPayload(
        comparisons_schema_version="0.1.0",
        title=title,
        generated_at=datetime.now(UTC).isoformat(),
        behavtaskatlas_commit=commit,
        behavtaskatlas_git_dirty=git_dirty,
        counts={"comparisons": len(entries)},
        comparisons=entries,
    )
    return payload.model_dump(mode="json")
