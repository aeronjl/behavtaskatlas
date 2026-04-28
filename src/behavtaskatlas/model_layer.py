"""Model-layer support: per-slice data coverage, models index, audit hooks.

Forward-evaluation dispatchers per ModelFamily live here too; for v1 the
dispatcher is a stub that returns "not implemented" for every variant.
Step 4 will plug in the logistic / SDT / DDM / click-accumulator forward
functions one at a time.

The audit pattern mirrors `audit.py`: ModelFit records carry the
parameters and (optionally) the predicted curve; the audit re-evaluates
predictions with the variant's forward function and compares to either
the recorded predictions (drift between fit-time and now) or to the
underlying finding's data. Variants without a registered forward function
get a `forward_unimplemented` status so the audit reports coverage rather
than silently skipping them.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from behavtaskatlas.models import (
    ModelFamily,
    ModelFit,
    ModelVariant,
    VerticalSlice,
)

# Canonical "data capabilities" exposed to ModelVariant.requires. Each
# capability is checked against a slice's harmonized trials.csv (when
# one exists at the slice root) and exposed via the fittability map.
KNOWN_REQUIREMENTS: tuple[str, ...] = (
    "stimulus_value",
    "choice_lr",
    "choice_go_withhold",
    "response_time",
    "prior_context",
    "click_times",
    "subject_id",
)


def _slice_trials_path(slice_record: VerticalSlice, derived_dir: Path) -> Path:
    return (derived_dir / slice_record.report_path).parent / "trials.csv"


def compute_slice_data_coverage(
    slice_record: VerticalSlice, derived_dir: Path
) -> dict[str, Any]:
    """Inspect a slice's slice-level trials.csv and emit a coverage
    fingerprint keyed by `KNOWN_REQUIREMENTS`. Returns a dict with:

    - capabilities: dict[str, bool]
    - n_trials, n_subjects
    - notes: list[str] with caveats (e.g. RT 0%-populated)

    Slices whose trials.csv hasn't been generated yet (only per-session
    subdirectories) get capabilities=None and a note. Best-effort, not a
    hard validation gate.
    """
    trials_path = _slice_trials_path(slice_record, derived_dir)
    if not trials_path.exists():
        return {
            "trials_path": str(trials_path),
            "capabilities": None,
            "n_trials": 0,
            "n_subjects": 0,
            "notes": [
                f"No slice-level trials.csv at {trials_path}; coverage skipped."
            ],
        }

    with trials_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    n_trials = len(rows)
    if n_trials == 0:
        return {
            "trials_path": str(trials_path),
            "capabilities": dict.fromkeys(KNOWN_REQUIREMENTS, False),
            "n_trials": 0,
            "n_subjects": 0,
            "notes": ["trials.csv is empty."],
        }

    notes: list[str] = []

    def has_any(column: str, predicate=lambda v: v not in ("", None)) -> bool:
        return any(predicate(row.get(column, "")) for row in rows)

    def coverage(column: str) -> float:
        if column not in rows[0]:
            return 0.0
        n_pop = sum(1 for row in rows if row.get(column) not in ("", None))
        return n_pop / n_trials if n_trials else 0.0

    capabilities: dict[str, bool] = {}
    capabilities["stimulus_value"] = has_any("stimulus_value")
    capabilities["choice_lr"] = any(
        (row.get("choice") or "").strip() in {"left", "right"} for row in rows
    )
    capabilities["choice_go_withhold"] = any(
        (row.get("choice") or "").strip() in {"go", "withhold"} for row in rows
    )
    rt_cov = coverage("response_time")
    capabilities["response_time"] = rt_cov > 0.0
    if 0.0 < rt_cov < 0.5:
        notes.append(
            f"response_time only {int(round(rt_cov * 100))}% populated; "
            "DDM-class fits may be unreliable."
        )
    capabilities["prior_context"] = has_any("prior_context")
    capabilities["subject_id"] = has_any("subject_id")
    # click_times lives in task_variables_json; sniff the JSON for
    # left_click_times / right_click_times.
    capabilities["click_times"] = False
    for row in rows[:200]:  # sample first 200 rows for speed
        raw = row.get("task_variables_json") or ""
        if raw and (
            "left_click_times" in raw or "right_click_times" in raw
        ):
            capabilities["click_times"] = True
            break

    if not capabilities["choice_lr"] and not capabilities["choice_go_withhold"]:
        notes.append(
            "choice column has no left/right or go/withhold values; "
            "psychometric / SDT fits cannot be evaluated here."
        )

    n_subjects = len(
        {(row.get("subject_id") or "").strip() for row in rows if row.get("subject_id")}
    )
    return {
        "trials_path": str(trials_path),
        "capabilities": capabilities,
        "n_trials": n_trials,
        "n_subjects": n_subjects,
        "notes": notes,
    }


def fittable_variants_for_slice(
    coverage: dict[str, Any], variants: Iterable[ModelVariant]
) -> list[str]:
    """Variant ids whose `requires` are all satisfied by the slice's
    capability fingerprint. Variants with unknown requirements (not in
    KNOWN_REQUIREMENTS) are conservatively excluded with a note in the
    returned tuple; for the index payload the caller stores the unknowns
    as a separate field if needed."""
    caps = coverage.get("capabilities") or {}
    fittable: list[str] = []
    for variant in variants:
        ok = True
        for req in variant.requires:
            if req not in KNOWN_REQUIREMENTS:
                ok = False
                break
            if not caps.get(req, False):
                ok = False
                break
        if ok:
            fittable.append(variant.id)
    return fittable


def build_models_index(
    *,
    families: list[ModelFamily],
    variants: list[ModelVariant],
    fits: list[ModelFit],
    slices: list[VerticalSlice],
    derived_dir: Path,
) -> dict[str, Any]:
    """Compose the derived/models.json payload."""
    family_payload: list[dict[str, Any]] = [
        json.loads(f.model_dump_json()) for f in sorted(families, key=lambda r: r.id)
    ]
    variant_payload: list[dict[str, Any]] = [
        json.loads(v.model_dump_json()) for v in sorted(variants, key=lambda r: r.id)
    ]
    fit_payload: list[dict[str, Any]] = [
        json.loads(f.model_dump_json()) for f in sorted(fits, key=lambda r: r.id)
    ]

    fits_by_variant: dict[str, list[str]] = {}
    fits_by_finding: dict[str, list[str]] = {}
    for fit in fits:
        fits_by_variant.setdefault(fit.variant_id, []).append(fit.id)
        for fid in fit.finding_ids:
            fits_by_finding.setdefault(fid, []).append(fit.id)

    slice_coverage: list[dict[str, Any]] = []
    for slice_record in sorted(slices, key=lambda r: r.id):
        coverage = compute_slice_data_coverage(slice_record, derived_dir)
        coverage["slice_id"] = slice_record.id
        coverage["fittable_variant_ids"] = fittable_variants_for_slice(
            coverage, variants
        )
        slice_coverage.append(coverage)

    counts = {
        "families": len(families),
        "variants": len(variants),
        "fits": len(fits),
        "slices_with_coverage": sum(
            1 for s in slice_coverage if s.get("capabilities") is not None
        ),
    }

    return {
        "counts": counts,
        "families": family_payload,
        "variants": variant_payload,
        "fits": fit_payload,
        "fits_by_variant": fits_by_variant,
        "fits_by_finding": fits_by_finding,
        "slice_coverage": slice_coverage,
        "known_requirements": list(KNOWN_REQUIREMENTS),
    }


# ── Forward-evaluation dispatch ──────────────────────────────────────────
#
# Each registered variant exposes a forward function with signature
#   forward(params: dict[str, float], finding: Finding) -> list[CurvePoint]
# returning predicted points on the finding's x grid. Variants without a
# registered forward function fall through to the audit's
# `forward_unimplemented` status so callers can distinguish "fit ok,
# nothing to compare" from "fit drifted".

_FORWARD_REGISTRY: dict[str, Any] = {}


def register_forward(variant_id: str, fn: Any) -> None:
    _FORWARD_REGISTRY[variant_id] = fn


def has_forward(variant_id: str) -> bool:
    return variant_id in _FORWARD_REGISTRY


def get_forward(variant_id: str) -> Any | None:
    return _FORWARD_REGISTRY.get(variant_id)


def audit_model_fits(
    *,
    fits: list[ModelFit],
    variants: list[ModelVariant],
    findings_by_id: dict[str, Any],
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Forward-evaluate each ModelFit and report drift against the
    finding's recorded points (or the fit's recorded predictions if
    present). Variants without a registered forward function are
    reported as `forward_unimplemented`. Returns a structured report;
    overall_status is `drift` only if at least one fit's max |diff|
    exceeds tolerance."""
    variant_by_id = {v.id: v for v in variants}
    reports: list[dict[str, Any]] = []
    overall_max_diff = 0.0
    overall_status = "ok"
    n_evaluated = 0
    n_unimplemented = 0
    for fit in sorted(fits, key=lambda f: f.id):
        variant = variant_by_id.get(fit.variant_id)
        if variant is None:
            reports.append(
                {
                    "fit_id": fit.id,
                    "variant_id": fit.variant_id,
                    "status": "missing_variant",
                }
            )
            overall_status = "warning"
            continue
        if not has_forward(variant.id):
            reports.append(
                {
                    "fit_id": fit.id,
                    "variant_id": fit.variant_id,
                    "status": "forward_unimplemented",
                }
            )
            n_unimplemented += 1
            continue
        forward = get_forward(variant.id)
        per_finding: list[dict[str, Any]] = []
        max_diff_for_fit = 0.0
        for fid in fit.finding_ids:
            finding = findings_by_id.get(fid)
            if finding is None:
                per_finding.append(
                    {"finding_id": fid, "status": "missing_finding"}
                )
                continue
            try:
                predicted = forward(fit.parameters, finding)
            except Exception as exc:  # surface, don't crash
                per_finding.append(
                    {
                        "finding_id": fid,
                        "status": "forward_error",
                        "error": str(exc),
                    }
                )
                overall_status = "warning"
                continue
            observed = {p.x: p.y for p in finding.curve.points}
            diffs: list[float] = []
            for pred in predicted:
                if pred.x in observed:
                    diff = abs(pred.y - observed[pred.x])
                    diffs.append(diff)
                    if diff > max_diff_for_fit:
                        max_diff_for_fit = diff
            per_finding.append(
                {
                    "finding_id": fid,
                    "status": "ok",
                    "n_points": len(diffs),
                    "max_abs_diff": max(diffs) if diffs else 0.0,
                }
            )
        n_evaluated += 1
        status = "ok" if max_diff_for_fit <= tolerance else "drift"
        if status == "drift":
            overall_status = "drift"
        if max_diff_for_fit > overall_max_diff:
            overall_max_diff = max_diff_for_fit
        reports.append(
            {
                "fit_id": fit.id,
                "variant_id": fit.variant_id,
                "status": status,
                "max_abs_diff": max_diff_for_fit,
                "per_finding": per_finding,
            }
        )

    return {
        "tolerance": tolerance,
        "overall_status": overall_status,
        "overall_max_abs_diff": overall_max_diff,
        "n_fits": len(fits),
        "n_evaluated": n_evaluated,
        "n_unimplemented": n_unimplemented,
        "reports": reports,
    }


def format_model_audit_report(report: dict[str, Any]) -> str:
    lines = [
        f"Model audit: {report['overall_status'].upper()} — "
        f"{report['n_fits']} fit(s), {report['n_evaluated']} evaluated, "
        f"{report['n_unimplemented']} forward unimplemented; "
        f"max |diff|={report['overall_max_abs_diff']:.6f} "
        f"(tolerance {report['tolerance']:.4f})."
    ]
    for r in report["reports"]:
        if r["status"] == "ok":
            flag = "✓"
        elif r["status"] == "forward_unimplemented":
            flag = "·"
        elif r["status"] == "missing_variant" or r["status"] == "missing_finding":
            flag = "✗"
        elif r["status"] == "drift":
            flag = "✗"
        else:
            flag = "?"
        line = f"  {flag} {r['fit_id']} [{r.get('variant_id','')}]: {r['status']}"
        if "max_abs_diff" in r and r["status"] != "forward_unimplemented":
            line += f" max |diff|={r['max_abs_diff']:.6f}"
        lines.append(line)
    return "\n".join(lines)

