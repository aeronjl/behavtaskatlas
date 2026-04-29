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
from collections.abc import Iterable, Mapping
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
    "correct_outcome",
    "response_time",
    "prior_context",
    "click_times",
    "subject_id",
)

MODEL_FIT_CAVEAT_TAGS: dict[str, dict[str, str]] = {
    "figure_source_data": {
        "label": "figure/source data",
        "description": (
            "Fit is based on paper figure source data or summarized values, "
            "not a full public trial table."
        ),
    },
    "target_coded_choice_proxy": {
        "label": "target-coded choice proxy",
        "description": (
            "Choice side was reconstructed from accuracy or target-coded rows, "
            "so it should not be treated as an observed motor choice."
        ),
    },
    "motion_duration_rt_proxy": {
        "label": "motion-duration RT proxy",
        "description": (
            "Chronometric evidence comes from motion/stimulus duration summaries "
            "rather than observed reaction-time timestamps."
        ),
    },
    "ddm_rt_approximation": {
        "label": "aggregate DDM RT approximation",
        "description": (
            "DDM likelihood uses aggregate chronometric constraints rather than "
            "a full trial-level response-time likelihood."
        ),
    },
    "binary_yes_no_sdt": {
        "label": "yes/no SDT",
        "description": (
            "Signal-detection fit uses a go/no-go yes/no variant with one "
            "d-prime and one criterion, not a 2AFC choice rule."
        ),
    },
    "click_accumulator_summary_fit": {
        "label": "click-summary accumulator",
        "description": (
            "Click accumulator fit is tied to the curated click summary fields "
            "rather than a full behavioral model audit against raw event streams."
        ),
    },
    "click_summary_baseline": {
        "label": "click-summary baseline",
        "description": (
            "Same-scope baseline for the clicks task using per-subject "
            "choice-rate or signed click-count summaries."
        ),
    },
    "accuracy_summary_fit": {
        "label": "accuracy-summary fit",
        "description": (
            "Fit is a descriptive p(correct)-by-strength model over accuracy "
            "summaries, not a signed-choice or reaction-time model."
        ),
    },
    "condition_rate_null": {
        "label": "condition-rate null",
        "description": (
            "One-parameter Bernoulli baseline over condition levels; useful for "
            "categorical or ordinal hit-rate curves without a sensory evidence axis."
        ),
    },
    "condition_rate_saturated": {
        "label": "condition-rate saturated",
        "description": (
            "Per-condition Bernoulli baseline over categorical or ordinal "
            "hit-rate levels; descriptive upper-bound, not a sensory evidence model."
        ),
    },
    "chronometric_summary_fit": {
        "label": "chronometric-summary fit",
        "description": (
            "Descriptive median-RT-by-strength fit over summary chronometric points, "
            "not a full reaction-time likelihood or process model."
        ),
    },
}

MODEL_SELECTION_CONFIDENCE_DEFINITIONS: dict[str, dict[str, str]] = {
    "decisive": {
        "label": "decisive",
        "description": "Best candidate beats the next AIC candidate by at least 10.",
    },
    "supported": {
        "label": "supported",
        "description": "Best candidate beats the next AIC candidate by at least 2.",
    },
    "close": {
        "label": "close",
        "description": "Best candidate is within 2 AIC units of the next candidate.",
    },
    "single_candidate": {
        "label": "single candidate",
        "description": "Only one AIC-ranked candidate is available for this finding.",
    },
}

MODEL_COMPARISON_SCOPE_DEFINITIONS: dict[str, dict[str, str]] = {
    "direct_choice": {
        "label": "direct choice",
        "description": (
            "Choice-proportion likelihoods fit to the same finding-level "
            "response curve."
        ),
    },
    "joint_choice_rt": {
        "label": "joint choice + RT",
        "description": (
            "DDM fit whose AIC combines the psychometric likelihood with a "
            "paired aggregate chronometric term."
        ),
    },
    "chronometric_summary": {
        "label": "chronometric summary",
        "description": (
            "Descriptive median-RT-by-strength fit over chronometric summary "
            "points."
        ),
    },
    "accuracy_summary": {
        "label": "accuracy summary",
        "description": (
            "Descriptive p(correct)-by-strength fit over accuracy summary "
            "points."
        ),
    },
    "condition_rate": {
        "label": "condition-rate baseline",
        "description": (
            "Condition-invariant Bernoulli response-rate baseline for "
            "categorical hit-rate findings."
        ),
    },
    "click_summary": {
        "label": "click summary",
        "description": (
            "Click-accumulator fit over curated click summary fields rather "
            "than a full raw-event likelihood."
        ),
    },
}

SUMMARY_BASELINE_SCOPES = frozenset(
    {
        "chronometric_summary",
        "accuracy_summary",
        "condition_rate",
        "click_summary",
    }
)
PROCESS_COMPARISON_SCOPES = frozenset({"direct_choice", "joint_choice_rt"})
CHRONOMETRIC_SUMMARY_MODEL_VARIANT_IDS = frozenset(
    {
        "model_variant.chronometric-hyperbolic-rt",
        "model_variant.chronometric-constant-rt",
    }
)
ACCURACY_SUMMARY_MODEL_VARIANT_IDS = frozenset(
    {
        "model_variant.chance-floor-accuracy-logistic",
        "model_variant.accuracy-rate-null",
    }
)
CONDITION_RATE_MODEL_VARIANT_IDS = frozenset(
    {
        "model_variant.bernoulli-condition-rate",
        "model_variant.bernoulli-condition-saturated",
    }
)
CLICK_SUMMARY_MODEL_VARIANT_IDS = frozenset(
    {
        "model_variant.click-leaky-accumulator",
        "model_variant.click-count-logistic",
        "model_variant.click-choice-rate-null",
    }
)
CLICK_SUMMARY_BASELINE_VARIANT_IDS = CLICK_SUMMARY_MODEL_VARIANT_IDS - {
    "model_variant.click-leaky-accumulator"
}
AUDITORY_CLICK_SLICE_FAMILY_ID = "family.auditory-click-accumulation"
KHALVATI_RDM_CONFIDENCE_DATASET_ID = (
    "dataset.khalvati-kiani-rao-rdm-confidence-source-data"
)
ROADMAP_EXTERNAL_DATA_BLOCKERS_BY_DATASET: dict[str, dict[str, str]] = {
    KHALVATI_RDM_CONFIDENCE_DATASET_ID: {
        "status": "blocked_external_data",
        "blocker_type": "author_request_raw_trials",
        "blocker_detail": (
            "The Nature source-data ZIP and POMDP-Confidence code archive "
            "provide figure source tables and code, but not the behavioral "
            "MATLAB files referenced by the code (`beh_data.monkey1.mat` and "
            "`beh_data.monkey2.mat`). The article states that analyzed data "
            "are available from R.K. on reasonable request."
        ),
        "next_action": (
            "Request the raw behavioral MATLAB files from the Kiani lab/R.K.; "
            "keep figure-source and proxy caveats prominent until those files "
            "can be harmonized."
        ),
    }
}
INTENTIONALLY_UNAVAILABLE_SLICE_REQUIREMENTS: dict[str, dict[str, str]] = {
    "slice.auditory-clicks": {
        "response_time": (
            "Brody Lab parsed release exposes stimulus duration and click "
            "times, but not a response timestamp in the parsed schema."
        )
    }
}
VARIANT_APPLICABLE_CURVE_TYPES: dict[str, frozenset[str]] = {
    "model_variant.accuracy-rate-null": frozenset({"accuracy_by_strength"}),
    "model_variant.bernoulli-condition-rate": frozenset({"hit_rate_by_condition"}),
    "model_variant.bernoulli-condition-saturated": frozenset(
        {"hit_rate_by_condition"}
    ),
    "model_variant.chance-floor-accuracy-logistic": frozenset(
        {"accuracy_by_strength"}
    ),
    "model_variant.chronometric-constant-rt": frozenset({"chronometric"}),
    "model_variant.chronometric-hyperbolic-rt": frozenset({"chronometric"}),
    "model_variant.click-choice-rate-null": frozenset({"psychometric"}),
    "model_variant.click-count-logistic": frozenset({"psychometric"}),
    "model_variant.click-leaky-accumulator": frozenset({"psychometric"}),
    "model_variant.logistic-4param": frozenset({"psychometric"}),
    "model_variant.sdt-2afc": frozenset({"psychometric"}),
    "model_variant.sdt-yes-no": frozenset({"hit_rate_by_condition"}),
}

MODEL_ROADMAP_ISSUE_DEFINITIONS: dict[str, dict[str, str]] = {
    "no_fit": {
        "label": "no fit",
        "description": "Finding has no AIC-ranked model candidate.",
    },
    "single_candidate": {
        "label": "single candidate",
        "description": "Finding has only one AIC-ranked candidate.",
    },
    "proxy_source_data": {
        "label": "proxy/source data",
        "description": "Model evidence is based on proxy-coded or figure-source data.",
    },
    "summary_baseline_winner": {
        "label": "summary baseline winner",
        "description": (
            "A descriptive summary or baseline model is winning against process "
            "or direct-choice candidates."
        ),
    },
    "mixed_choice_rt_aic": {
        "label": "mixed AIC scope",
        "description": "Choice-only and joint choice+RT AIC candidates share one row.",
    },
    "near_miss_slice": {
        "label": "near-miss slice",
        "description": "A slice is one capability away from a model variant.",
    },
}

PROXY_BACKED_CAVEAT_TAGS = frozenset(
    {
        "figure_source_data",
        "target_coded_choice_proxy",
        "motion_duration_rt_proxy",
    }
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
    capabilities["correct_outcome"] = has_any("correct")
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


def _record_value(record: Any, field: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(field, default)
    return getattr(record, field, default)


def _finding_curve_type(finding: Any) -> str | None:
    curve = _record_value(finding, "curve")
    if curve is None:
        return None
    return _record_value(curve, "curve_type")


def infer_model_fit_caveat_tags(
    fit: ModelFit,
    findings_by_id: Mapping[str, Any] | None = None,
) -> list[str]:
    """Infer stable, machine-readable caveat tags for a fit.

    Fit YAML may carry explicit `caveat_tags`, but most historical records
    predate that field. This helper centralizes inference from variant ids and
    linked findings so the static indexes and CSV exports stay consistent
    without a large YAML migration.
    """
    tags = set(fit.caveat_tags)
    findings = [
        findings_by_id[fid]
        for fid in fit.finding_ids
        if findings_by_id is not None and fid in findings_by_id
    ]
    finding_ids = " ".join(fit.finding_ids)

    if any(_record_value(f, "source_data_level") == "figure-source-data" for f in findings):
        tags.add("figure_source_data")

    if "direction-choice-proxy" in finding_ids:
        tags.add("target_coded_choice_proxy")

    if "khalvati-kiani-rao-2021.chronometric.direction-choice-proxy" in finding_ids:
        tags.add("motion_duration_rt_proxy")

    if fit.variant_id.startswith("model_variant.ddm"):
        if any(_finding_curve_type(f) == "chronometric" for f in findings):
            tags.add("ddm_rt_approximation")

    if fit.variant_id == "model_variant.sdt-yes-no":
        tags.add("binary_yes_no_sdt")

    if fit.variant_id == "model_variant.click-leaky-accumulator":
        tags.add("click_accumulator_summary_fit")

    if fit.variant_id in CLICK_SUMMARY_BASELINE_VARIANT_IDS:
        tags.add("click_summary_baseline")

    if fit.variant_id in ACCURACY_SUMMARY_MODEL_VARIANT_IDS:
        tags.add("accuracy_summary_fit")

    if fit.variant_id == "model_variant.bernoulli-condition-rate":
        tags.add("condition_rate_null")

    if fit.variant_id == "model_variant.bernoulli-condition-saturated":
        tags.add("condition_rate_saturated")

    if fit.variant_id in CHRONOMETRIC_SUMMARY_MODEL_VARIANT_IDS:
        tags.add("chronometric_summary_fit")

    return sorted(tags)


def model_fit_comparison_scope(
    fit: ModelFit,
    findings_by_id: Mapping[str, Any] | None = None,
) -> str:
    """Return the AIC interpretation scope for a fit.

    Scopes separate direct likelihood comparisons from useful baselines whose
    likelihoods are built over different summaries. The optional findings map
    is accepted for future refinements and to match the caveat-inference API.
    """
    del findings_by_id
    if fit.variant_id.startswith("model_variant.ddm"):
        return "joint_choice_rt"
    if fit.variant_id in CHRONOMETRIC_SUMMARY_MODEL_VARIANT_IDS:
        return "chronometric_summary"
    if fit.variant_id in ACCURACY_SUMMARY_MODEL_VARIANT_IDS:
        return "accuracy_summary"
    if fit.variant_id in CONDITION_RATE_MODEL_VARIANT_IDS:
        return "condition_rate"
    if fit.variant_id in CLICK_SUMMARY_MODEL_VARIANT_IDS:
        return "click_summary"
    return "direct_choice"


def _ordered_comparison_scopes(scopes: Iterable[str]) -> list[str]:
    scope_set = set(scopes)
    ordered = [
        scope
        for scope in MODEL_COMPARISON_SCOPE_DEFINITIONS
        if scope in scope_set
    ]
    return ordered + sorted(scope_set - set(ordered))


def _model_selection_interpretation_warning(
    *,
    finding_id: str,
    best_fit: ModelFit,
    best_scope: str,
    confidence_label: str,
    delta_aic_to_next: float | None,
    candidate_scopes: list[str],
    candidate_scope_counts: Mapping[str, int],
    mixed_scope_resolved: bool = False,
) -> dict[str, Any] | None:
    competitor_scopes = set(candidate_scopes) - {best_scope}
    if (
        best_scope in SUMMARY_BASELINE_SCOPES
        and competitor_scopes & PROCESS_COMPARISON_SCOPES
        and candidate_scope_counts.get(best_scope, 0) <= 1
    ):
        return {
            "finding_id": finding_id,
            "best_fit_id": best_fit.id,
            "best_variant_id": best_fit.variant_id,
            "comparison_scope": best_scope,
            "candidate_comparison_scopes": candidate_scopes,
            "confidence_label": confidence_label,
            "delta_aic_to_next": delta_aic_to_next,
            "severity": "high",
            "warning_type": "summary_baseline_winner",
            "message": (
                "A descriptive summary or baseline model is the AIC winner "
                "against process/direct-choice candidates; treat this as a "
                "fit-quality baseline, not stronger cognitive evidence."
            ),
        }
    if (
        "direct_choice" in candidate_scopes
        and "joint_choice_rt" in candidate_scopes
        and not mixed_scope_resolved
    ):
        return {
            "finding_id": finding_id,
            "best_fit_id": best_fit.id,
            "best_variant_id": best_fit.variant_id,
            "comparison_scope": best_scope,
            "candidate_comparison_scopes": candidate_scopes,
            "confidence_label": confidence_label,
            "delta_aic_to_next": delta_aic_to_next,
            "severity": "medium",
            "warning_type": "mixed_choice_rt_aic",
            "message": (
                "Candidate set mixes choice-only AIC with joint choice+RT AIC; "
                "use the winner as model-selection triage rather than a direct "
                "likelihood-ratio claim."
            ),
        }
    return None


def _roadmap_token(value: Any) -> str:
    text = str(value or "none").lower()
    token = "".join(ch if ch.isalnum() else "-" for ch in text).strip("-")
    return token or "none"


def _roadmap_priority_label(score: int) -> str:
    if score >= 85:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def _roadmap_item(
    *,
    issue_type: str,
    priority_score: int,
    target_type: str,
    target_id: str,
    recommended_action: str,
    impact: str,
    rationale: str,
    finding: Mapping[str, Any] | None = None,
    slice_id: str | None = None,
    best_variant_id: str | None = None,
    comparison_scope: str | None = None,
    confidence_label: str | None = None,
    n_candidate_fits: int | None = None,
    related_variant_id: str | None = None,
    missing_requirements: Iterable[str] = (),
    caveat_tags: Iterable[str] = (),
    warning_type: str | None = None,
    status: str = "ready",
    blocker_type: str = "",
    blocker_detail: str = "",
    next_action: str = "",
) -> dict[str, Any]:
    finding = finding or {}
    item = {
        "roadmap_id": (
            "model_roadmap."
            f"{_roadmap_token(issue_type)}."
            f"{_roadmap_token(target_type)}."
            f"{_roadmap_token(target_id)}."
            f"{_roadmap_token(related_variant_id or warning_type or best_variant_id)}"
        ),
        "rank": 0,
        "priority_score": int(priority_score),
        "priority_label": _roadmap_priority_label(priority_score),
        "issue_type": issue_type,
        "target_type": target_type,
        "target_id": target_id,
        "finding_id": finding.get("finding_id", "") if target_type == "finding" else "",
        "slice_id": slice_id or "",
        "paper_id": finding.get("paper_id", ""),
        "curve_type": finding.get("curve_type", ""),
        "species": finding.get("species", ""),
        "source_data_level": finding.get("source_data_level", ""),
        "best_variant_id": best_variant_id or "",
        "comparison_scope": comparison_scope or "",
        "confidence_label": confidence_label or "",
        "n_candidate_fits": "" if n_candidate_fits is None else int(n_candidate_fits),
        "related_variant_id": related_variant_id or "",
        "missing_requirements": sorted(str(req) for req in missing_requirements),
        "caveat_tags": sorted(str(tag) for tag in caveat_tags),
        "warning_type": warning_type or "",
        "status": status,
        "blocker_type": blocker_type,
        "blocker_detail": blocker_detail,
        "next_action": next_action,
        "recommended_action": recommended_action,
        "impact": impact,
        "rationale": rationale,
    }
    return item


def _single_candidate_action(scope: str, curve_type: str) -> str:
    if scope == "accuracy_summary":
        return (
            "Add an accuracy-rate null or second accuracy-by-strength baseline "
            "so accuracy summaries are not single-candidate winners."
        )
    if scope == "condition_rate":
        return (
            "Add a condition-structured categorical baseline or mark the row as "
            "descriptive if no sensory evidence axis is available."
        )
    if scope == "chronometric_summary":
        return (
            "Add a second same-scope chronometric baseline or a trial-level RT "
            "likelihood before treating the winner as model selection."
        )
    if scope == "click_summary":
        return (
            "Add a click-summary null or direct-choice comparator with the same "
            "summary-data likelihood."
        )
    if curve_type == "psychometric":
        return "Add a second direct-choice candidate, such as SDT or logistic."
    return "Add a second same-scope candidate for this finding."


def _warning_action(warning: Mapping[str, Any]) -> tuple[str, str]:
    warning_type = str(warning.get("warning_type") or "")
    scope = str(warning.get("comparison_scope") or "")
    if warning_type == "summary_baseline_winner":
        if scope == "chronometric_summary":
            return (
                "Add a matched trial-level RT likelihood or chronometric process "
                "baseline before reading this as evidence against DDM.",
                "Prevents descriptive median-RT fits from being overread as "
                "process-model wins or losses.",
            )
        if scope == "click_summary":
            return (
                "Add a same-scope click-summary null/direct baseline or a "
                "raw-event accumulator likelihood.",
                "Separates click-summary fit quality from direct choice-model "
                "evidence.",
            )
        return (
            "Add a same-scope comparator or explicitly classify this winner as "
            "descriptive in the model-selection view.",
            "Keeps summary/baseline AIC winners from being treated as direct "
            "cognitive model evidence.",
        )
    return (
        "Split the row into matched AIC scopes, or add paired direct-only and "
        "joint choice+RT comparisons for the same model class.",
        "Makes AIC gaps interpretable within matched likelihood definitions.",
    )


def _external_data_blocker(finding: Mapping[str, Any]) -> Mapping[str, str] | None:
    dataset_id = str(finding.get("dataset_id") or "")
    return ROADMAP_EXTERNAL_DATA_BLOCKERS_BY_DATASET.get(dataset_id)


def build_model_coverage_roadmap(
    *,
    findings_by_id: Mapping[str, Any],
    model_selection_by_finding: Iterable[Mapping[str, Any]],
    model_coverage_gaps: Mapping[str, Any],
    interpretation_warnings: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build prioritized model-layer work items from the derived matrix."""
    selections = {
        str(selection.get("finding_id")): selection
        for selection in model_selection_by_finding
        if selection.get("finding_id")
    }
    items: list[dict[str, Any]] = []

    def finding_summary(finding_id: str) -> dict[str, Any]:
        return _finding_summary(finding_id, findings_by_id)

    for gap in model_coverage_gaps.get("findings_with_no_fits", []):
        finding_id = str(gap.get("finding_id", ""))
        items.append(
            _roadmap_item(
                issue_type="no_fit",
                priority_score=100,
                target_type="finding",
                target_id=finding_id,
                finding=gap,
                recommended_action=(
                    "Add the first model candidate for this finding, or harmonize "
                    "the required trial fields so an existing variant applies."
                ),
                impact="Converts an unmodelled finding into an AIC-ranked row.",
                rationale="No committed AIC-ranked fit currently references this finding.",
            )
        )

    for gap in model_coverage_gaps.get("findings_with_single_candidate", []):
        finding_id = str(gap.get("finding_id", ""))
        selection = selections.get(finding_id, {})
        scope = str(selection.get("comparison_scope") or "")
        curve_type = str(gap.get("curve_type") or "")
        items.append(
            _roadmap_item(
                issue_type="single_candidate",
                priority_score=82,
                target_type="finding",
                target_id=finding_id,
                finding=gap,
                best_variant_id=str(selection.get("best_variant_id") or ""),
                comparison_scope=scope,
                confidence_label=str(selection.get("confidence_label") or ""),
                n_candidate_fits=selection.get("n_candidate_fits"),
                caveat_tags=selection.get("candidate_caveat_tags", []),
                recommended_action=_single_candidate_action(scope, curve_type),
                impact=(
                    "Turns an unsupported winner into a comparable "
                    "model-selection row."
                ),
                rationale="Only one AIC-ranked candidate is available.",
            )
        )

    for warning in interpretation_warnings:
        finding_id = str(warning.get("finding_id", ""))
        selection = selections.get(finding_id, {})
        action, impact = _warning_action(warning)
        warning_type = str(warning.get("warning_type") or "")
        items.append(
            _roadmap_item(
                issue_type=warning_type,
                priority_score=92 if warning.get("severity") == "high" else 70,
                target_type="finding",
                target_id=finding_id,
                finding=finding_summary(finding_id),
                best_variant_id=str(warning.get("best_variant_id") or ""),
                comparison_scope=str(warning.get("comparison_scope") or ""),
                confidence_label=str(warning.get("confidence_label") or ""),
                n_candidate_fits=selection.get("n_candidate_fits"),
                caveat_tags=selection.get("candidate_caveat_tags", []),
                warning_type=warning_type,
                recommended_action=action,
                impact=impact,
                rationale=str(warning.get("message") or ""),
            )
        )

    for gap in model_coverage_gaps.get("proxy_backed_findings", []):
        finding_id = str(gap.get("finding_id", ""))
        selection = selections.get(finding_id, {})
        caveat_tags = gap.get("proxy_caveat_tags", [])
        blocker = _external_data_blocker(gap)
        recommended_action = (
            blocker.get("next_action", "") if blocker is not None else ""
        ) or (
            "Replace proxy or figure-source evidence with raw-trial "
            "harmonization, or keep the caveat prominent if raw data are "
            "not available."
        )
        rationale_parts = [
            "Candidate fits include proxy-backed caveats: "
            f"{', '.join(str(tag) for tag in caveat_tags)}."
        ]
        if blocker is not None:
            rationale_parts.append(blocker.get("blocker_detail", ""))
        items.append(
            _roadmap_item(
                issue_type="proxy_source_data",
                priority_score=88,
                target_type="finding",
                target_id=finding_id,
                finding=gap,
                best_variant_id=str(gap.get("best_variant_id") or ""),
                comparison_scope=str(selection.get("comparison_scope") or ""),
                confidence_label=str(selection.get("confidence_label") or ""),
                n_candidate_fits=gap.get("n_candidate_fits"),
                caveat_tags=caveat_tags,
                status=blocker.get("status", "ready") if blocker else "ready",
                blocker_type=blocker.get("blocker_type", "") if blocker else "",
                blocker_detail=blocker.get("blocker_detail", "") if blocker else "",
                next_action=blocker.get("next_action", "") if blocker else "",
                recommended_action=recommended_action,
                impact=(
                    "Improves cross-paper model comparisons by reducing source "
                    "and proxy caveats."
                ),
                rationale=" ".join(part for part in rationale_parts if part),
            )
        )

    for row in model_coverage_gaps.get("near_miss_slices", []):
        slice_id = str(row.get("slice_id") or "")
        variant_id = str(row.get("variant_id") or "")
        missing = row.get("missing_requirements", [])
        items.append(
            _roadmap_item(
                issue_type="near_miss_slice",
                priority_score=45,
                target_type="slice",
                target_id=slice_id,
                slice_id=slice_id,
                related_variant_id=variant_id,
                missing_requirements=missing,
                recommended_action=(
                    "Add the missing harmonized capability "
                    f"({', '.join(str(req) for req in missing)}) or mark the "
                    "variant as intentionally inapplicable for this slice."
                ),
                impact=(
                    "Expands the fittable model set for an existing vertical "
                    "slice."
                ),
                rationale=(
                    f"{variant_id} is one requirement away from being fittable "
                    f"on {slice_id}."
                ),
            )
        )

    items.sort(
        key=lambda item: (
            -int(item["priority_score"]),
            str(item["issue_type"]),
            str(item["target_id"]),
            str(item["roadmap_id"]),
        )
    )
    for rank, item in enumerate(items, start=1):
        item["rank"] = rank

    counts_by_issue = {
        key: 0 for key in MODEL_ROADMAP_ISSUE_DEFINITIONS
    }
    counts_by_priority = {"high": 0, "medium": 0, "low": 0}
    counts_by_status = {"ready": 0, "blocked_external_data": 0}
    for item in items:
        issue_type = str(item["issue_type"])
        priority = str(item["priority_label"])
        status = str(item.get("status") or "ready")
        counts_by_issue[issue_type] = counts_by_issue.get(issue_type, 0) + 1
        counts_by_priority[priority] = counts_by_priority.get(priority, 0) + 1
        counts_by_status[status] = counts_by_status.get(status, 0) + 1

    return {
        "counts": {
            "items": len(items),
            "by_issue_type": counts_by_issue,
            "by_priority": counts_by_priority,
            "by_status": counts_by_status,
        },
        "issue_definitions": MODEL_ROADMAP_ISSUE_DEFINITIONS,
        "items": items,
    }


def model_selection_confidence(
    delta_aic_to_next: float | None,
    n_candidate_fits: int,
) -> str:
    """Map an AIC gap to a stable confidence label for model selection."""
    if n_candidate_fits <= 1 or delta_aic_to_next is None:
        return "single_candidate"
    if delta_aic_to_next >= 10:
        return "decisive"
    if delta_aic_to_next >= 2:
        return "supported"
    return "close"


def fit_provenance_summary(fits: Iterable[ModelFit]) -> dict[str, int]:
    """Small reproducibility fingerprint for the model index."""
    summary = {
        "fit_dirty_true": 0,
        "fit_dirty_false": 0,
        "fit_dirty_unknown": 0,
        "missing_fit_commit": 0,
    }
    for fit in fits:
        dirty = fit.provenance.fit_dirty
        if dirty is True:
            summary["fit_dirty_true"] += 1
        elif dirty is False:
            summary["fit_dirty_false"] += 1
        else:
            summary["fit_dirty_unknown"] += 1
        if not fit.provenance.fit_commit:
            summary["missing_fit_commit"] += 1
    return summary


def _stratification_summary(finding: Any) -> dict[str, Any]:
    strat = _record_value(finding, "stratification")
    if strat is None:
        return {}
    if isinstance(strat, Mapping):
        return {
            key: value
            for key, value in strat.items()
            if value not in ("", None)
        }
    keys = ("condition", "subject_id", "session_id", "group")
    return {
        key: _record_value(strat, key)
        for key in keys
        if _record_value(strat, key) not in ("", None)
    }


def _finding_summary(
    finding_id: str,
    findings_by_id: Mapping[str, Any],
) -> dict[str, Any]:
    finding = findings_by_id.get(finding_id)
    if finding is None:
        return {"finding_id": finding_id}
    strat = _record_value(finding, "stratification")
    species = _record_value(finding, "species")
    if species is None and strat is not None:
        species = _record_value(strat, "species")
    return {
        "finding_id": finding_id,
        "paper_id": _record_value(finding, "paper_id"),
        "protocol_id": _record_value(finding, "protocol_id"),
        "dataset_id": _record_value(finding, "dataset_id"),
        "species": species,
        "curve_type": _finding_curve_type(finding),
        "source_data_level": _record_value(finding, "source_data_level"),
        "stratification": _stratification_summary(finding),
    }


def _findings_curve_types_by_slice(
    findings_by_id: Mapping[str, Any],
    slice_coverage: Iterable[Mapping[str, Any]],
) -> dict[str, frozenset[str]]:
    coverage_rows = list(slice_coverage)
    curve_types_by_slice: dict[str, set[str]] = {}
    for finding in findings_by_id.values():
        curve_type = _finding_curve_type(finding)
        if curve_type in ("", None):
            continue
        explicit_slice_id = _record_value(finding, "slice_id")
        if explicit_slice_id not in ("", None):
            curve_types_by_slice.setdefault(str(explicit_slice_id), set()).add(
                str(curve_type)
            )
            continue
        for coverage in coverage_rows:
            slice_id = coverage.get("slice_id")
            if slice_id in ("", None):
                continue
            if _finding_matches_slice_coverage(finding, coverage):
                curve_types_by_slice.setdefault(str(slice_id), set()).add(
                    str(curve_type)
                )
    return {
        slice_id: frozenset(curve_types)
        for slice_id, curve_types in curve_types_by_slice.items()
    }


def _finding_matches_slice_coverage(
    finding: Any,
    coverage: Mapping[str, Any],
) -> bool:
    finding_dataset_id = _record_value(finding, "dataset_id")
    coverage_dataset_id = coverage.get("dataset_id")
    finding_protocol_id = _record_value(finding, "protocol_id")
    coverage_protocol_id = coverage.get("protocol_id")
    if finding_dataset_id not in ("", None) and coverage_dataset_id not in ("", None):
        if str(finding_dataset_id) != str(coverage_dataset_id):
            return False
        if finding_protocol_id in ("", None) or coverage_protocol_id in ("", None):
            return True
        return str(finding_protocol_id) == str(coverage_protocol_id)
    if finding_protocol_id in ("", None) or coverage_protocol_id in ("", None):
        return False
    return str(finding_protocol_id) == str(coverage_protocol_id)


def _family_applicable_curve_types(
    families: Iterable[ModelFamily],
) -> dict[str, frozenset[str]]:
    return {
        family.id: frozenset(
            str(curve_type) for curve_type in family.applicable_curve_types
        )
        for family in families
    }


def _variant_applicable_curve_types(
    variant: ModelVariant,
    family_curve_types: Mapping[str, frozenset[str]],
) -> frozenset[str]:
    return VARIANT_APPLICABLE_CURVE_TYPES.get(
        variant.id,
        family_curve_types.get(variant.family_id, frozenset()),
    )


def _variant_matches_slice_context(
    *,
    variant: ModelVariant,
    slice_family_id: str,
    slice_choice_type: str,
    slice_curve_types: frozenset[str],
    variant_curve_types: frozenset[str],
) -> bool:
    if slice_curve_types and variant_curve_types:
        if not slice_curve_types & variant_curve_types:
            return False
    if "choice_go_withhold" in variant.requires:
        return slice_choice_type in ("", "go-no-go")
    if "click_times" in variant.requires:
        return slice_family_id == AUDITORY_CLICK_SLICE_FAMILY_ID
    return True


def _intentionally_unavailable_requirement(
    *,
    slice_id: str,
    missing_requirements: list[str],
) -> str | None:
    if len(missing_requirements) != 1:
        return None
    unavailable = INTENTIONALLY_UNAVAILABLE_SLICE_REQUIREMENTS.get(slice_id, {})
    return unavailable.get(missing_requirements[0])


def _model_coverage_gaps(
    *,
    findings_by_id: Mapping[str, Any],
    fits_by_finding: Mapping[str, list[str]],
    selections: list[dict[str, Any]],
    slice_coverage: list[dict[str, Any]],
    families: Iterable[ModelFamily],
    variants: Iterable[ModelVariant],
) -> dict[str, Any]:
    no_fit_ids = sorted(set(findings_by_id) - set(fits_by_finding))
    findings_with_no_fits = [
        _finding_summary(finding_id, findings_by_id) for finding_id in no_fit_ids
    ]

    findings_with_single_candidate = [
        {
            **_finding_summary(selection["finding_id"], findings_by_id),
            "best_fit_id": selection.get("best_fit_id"),
            "best_variant_id": selection.get("best_variant_id"),
            "best_aic": selection.get("best_aic"),
            "best_caveat_tags": selection.get("best_caveat_tags", []),
        }
        for selection in selections
        if selection.get("n_candidate_fits", 0) <= 1
    ]

    proxy_backed_findings = []
    for selection in selections:
        tags = sorted(
            set(selection.get("candidate_caveat_tags", []))
            & PROXY_BACKED_CAVEAT_TAGS
        )
        if not tags:
            continue
        proxy_backed_findings.append(
            {
                **_finding_summary(selection["finding_id"], findings_by_id),
                "best_fit_id": selection.get("best_fit_id"),
                "best_variant_id": selection.get("best_variant_id"),
                "proxy_caveat_tags": tags,
                "n_candidate_fits": selection.get("n_candidate_fits"),
            }
        )

    curve_types_by_slice = _findings_curve_types_by_slice(
        findings_by_id,
        slice_coverage,
    )
    family_curve_types = _family_applicable_curve_types(families)
    variant_rows = sorted(variants, key=lambda variant: variant.id)
    near_miss_slices: list[dict[str, Any]] = []
    intentionally_inapplicable_near_misses: list[dict[str, Any]] = []
    for coverage in slice_coverage:
        caps = coverage.get("capabilities")
        if caps is None:
            continue
        slice_id = str(coverage.get("slice_id") or "")
        slice_family_id = str(coverage.get("family_id") or "")
        slice_choice_type = str(coverage.get("choice_type") or "")
        slice_curve_types = curve_types_by_slice.get(slice_id, frozenset())
        for variant in variant_rows:
            variant_curve_types = _variant_applicable_curve_types(
                variant,
                family_curve_types,
            )
            if not _variant_matches_slice_context(
                variant=variant,
                slice_family_id=slice_family_id,
                slice_choice_type=slice_choice_type,
                slice_curve_types=slice_curve_types,
                variant_curve_types=variant_curve_types,
            ):
                continue
            missing = [
                req
                for req in variant.requires
                if req not in KNOWN_REQUIREMENTS or not caps.get(req, False)
            ]
            if len(missing) != 1:
                continue
            unavailable_reason = _intentionally_unavailable_requirement(
                slice_id=slice_id,
                missing_requirements=missing,
            )
            if unavailable_reason is not None:
                intentionally_inapplicable_near_misses.append(
                    {
                        "slice_id": slice_id,
                        "slice_family_id": slice_family_id,
                        "slice_choice_type": slice_choice_type,
                        "variant_id": variant.id,
                        "variant_name": variant.name,
                        "family_id": variant.family_id,
                        "missing_requirements": missing,
                        "inapplicable_reason": unavailable_reason,
                    }
                )
                continue
            near_miss_slices.append(
                {
                    "slice_id": slice_id,
                    "slice_family_id": slice_family_id,
                    "slice_choice_type": slice_choice_type,
                    "variant_id": variant.id,
                    "variant_name": variant.name,
                    "family_id": variant.family_id,
                    "slice_curve_types": sorted(slice_curve_types),
                    "variant_applicable_curve_types": sorted(variant_curve_types),
                    "missing_requirements": missing,
                    "satisfied_requirements": [
                        req for req in variant.requires if req not in missing
                    ],
                    "n_trials": coverage.get("n_trials", 0),
                    "n_subjects": coverage.get("n_subjects", 0),
                }
            )

    return {
        "counts": {
            "findings_with_no_fits": len(findings_with_no_fits),
            "findings_with_single_candidate": len(findings_with_single_candidate),
            "proxy_backed_findings": len(proxy_backed_findings),
            "near_miss_slices": len(near_miss_slices),
            "intentionally_inapplicable_near_misses": len(
                intentionally_inapplicable_near_misses
            ),
        },
        "findings_with_no_fits": findings_with_no_fits,
        "findings_with_single_candidate": findings_with_single_candidate,
        "proxy_backed_findings": proxy_backed_findings,
        "near_miss_slices": near_miss_slices,
        "intentionally_inapplicable_near_misses": (
            intentionally_inapplicable_near_misses
        ),
    }


def _model_selection_id(finding_id: str, scope: str | None = None) -> str:
    base = f"model_selection.{_roadmap_token(finding_id)}"
    if scope is None:
        return base
    return f"{base}.{_roadmap_token(scope)}"


def _ranked_model_selection_row(
    *,
    finding_id: str,
    candidates: list[ModelFit],
    caveat_tags_by_fit: Mapping[str, list[str]],
    comparison_scope_by_fit: Mapping[str, str],
    selection_id: str,
    selection_level: str,
    extra_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = sorted(
        candidates,
        key=lambda fit: (float(fit.quality.get("aic", float("inf"))), fit.id),
    )
    best = candidates[0]
    best_aic = float(best.quality["aic"])
    next_aic = float(candidates[1].quality["aic"]) if len(candidates) > 1 else None
    delta_aic_to_next = (
        None if next_aic is None else max(0.0, next_aic - best_aic)
    )
    confidence_label = model_selection_confidence(
        delta_aic_to_next,
        len(candidates),
    )
    candidate_scope_values = [
        comparison_scope_by_fit.get(fit.id, model_fit_comparison_scope(fit))
        for fit in candidates
    ]
    candidate_scopes = _ordered_comparison_scopes(candidate_scope_values)
    candidate_scope_counts = {
        scope: candidate_scope_values.count(scope)
        for scope in set(candidate_scope_values)
    }
    best_scope = comparison_scope_by_fit.get(
        best.id,
        model_fit_comparison_scope(best),
    )
    interpretation_warning = _model_selection_interpretation_warning(
        finding_id=finding_id,
        best_fit=best,
        best_scope=best_scope,
        confidence_label=confidence_label,
        delta_aic_to_next=delta_aic_to_next,
        candidate_scopes=candidate_scopes,
        candidate_scope_counts=candidate_scope_counts,
        mixed_scope_resolved=True,
    )
    row = {
        "selection_id": selection_id,
        "selection_level": selection_level,
        "finding_id": finding_id,
        "best_fit_id": best.id,
        "best_variant_id": best.variant_id,
        "best_aic": best_aic,
        "delta_aic_to_next": delta_aic_to_next,
        "confidence_label": confidence_label,
        "comparison_scope": best_scope,
        "n_candidate_fits": len(candidates),
        "candidate_fit_ids": [fit.id for fit in candidates],
        "candidate_variant_ids": [fit.variant_id for fit in candidates],
        "candidate_comparison_scopes": candidate_scopes,
        "candidate_scope_counts": {
            scope: candidate_scope_counts[scope]
            for scope in _ordered_comparison_scopes(candidate_scope_counts)
        },
        "best_caveat_tags": caveat_tags_by_fit.get(best.id, []),
        "candidate_caveat_tags": sorted(
            {
                tag
                for fit in candidates
                for tag in caveat_tags_by_fit.get(fit.id, [])
            }
        ),
        "interpretation_warning": interpretation_warning,
    }
    if extra_fields:
        row.update(extra_fields)
    return row


def build_models_index(
    *,
    families: list[ModelFamily],
    variants: list[ModelVariant],
    fits: list[ModelFit],
    slices: list[VerticalSlice],
    derived_dir: Path,
    findings: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Compose the derived/models.json payload."""
    findings_by_id = {
        _record_value(f, "id"): f
        for f in (findings or [])
        if _record_value(f, "id") is not None
    }
    family_payload: list[dict[str, Any]] = [
        json.loads(f.model_dump_json()) for f in sorted(families, key=lambda r: r.id)
    ]
    variant_payload: list[dict[str, Any]] = [
        json.loads(v.model_dump_json()) for v in sorted(variants, key=lambda r: r.id)
    ]
    fit_payload: list[dict[str, Any]] = []
    caveat_tags_by_fit: dict[str, list[str]] = {}
    comparison_scope_by_fit: dict[str, str] = {}
    for fit in sorted(fits, key=lambda r: r.id):
        tags = infer_model_fit_caveat_tags(fit, findings_by_id)
        caveat_tags_by_fit[fit.id] = tags
        comparison_scope = model_fit_comparison_scope(fit, findings_by_id)
        comparison_scope_by_fit[fit.id] = comparison_scope
        payload = json.loads(fit.model_dump_json())
        payload["caveat_tags"] = tags
        payload["comparison_scope"] = comparison_scope
        fit_payload.append(payload)

    fits_by_variant: dict[str, list[str]] = {}
    fits_by_finding: dict[str, list[str]] = {}
    fit_by_id = {fit.id: fit for fit in fits}
    for fit in fits:
        fits_by_variant.setdefault(fit.variant_id, []).append(fit.id)
        for fid in fit.finding_ids:
            fits_by_finding.setdefault(fid, []).append(fit.id)

    model_selection_by_finding: list[dict[str, Any]] = []
    model_selection_by_finding_scope: list[dict[str, Any]] = []
    for finding_id, fit_ids in sorted(fits_by_finding.items()):
        candidates = [
            fit_by_id[fit_id]
            for fit_id in fit_ids
            if "aic" in fit_by_id[fit_id].quality
        ]
        candidates.sort(
            key=lambda fit: (float(fit.quality.get("aic", float("inf"))), fit.id)
        )
        if not candidates:
            continue
        candidate_scope_values = [
            comparison_scope_by_fit.get(fit.id, model_fit_comparison_scope(fit))
            for fit in candidates
        ]
        candidate_scopes = _ordered_comparison_scopes(candidate_scope_values)
        scope_selection_ids: list[str] = []
        for scope in candidate_scopes:
            scope_candidates = [
                fit
                for fit in candidates
                if comparison_scope_by_fit.get(
                    fit.id,
                    model_fit_comparison_scope(fit),
                )
                == scope
            ]
            scope_row = _ranked_model_selection_row(
                finding_id=finding_id,
                candidates=scope_candidates,
                caveat_tags_by_fit=caveat_tags_by_fit,
                comparison_scope_by_fit=comparison_scope_by_fit,
                selection_id=_model_selection_id(finding_id, scope),
                selection_level="comparison_scope",
                extra_fields={"scope_stratified": True},
            )
            model_selection_by_finding_scope.append(scope_row)
            scope_selection_ids.append(str(scope_row["selection_id"]))

        model_selection_by_finding.append(
            _ranked_model_selection_row(
                finding_id=finding_id,
                candidates=candidates,
                caveat_tags_by_fit=caveat_tags_by_fit,
                comparison_scope_by_fit=comparison_scope_by_fit,
                selection_id=_model_selection_id(finding_id),
                selection_level="finding",
                extra_fields={
                    "has_mixed_aic_scopes": len(candidate_scopes) > 1,
                    "scope_selection_ids": scope_selection_ids,
                },
            )
        )

    slice_coverage: list[dict[str, Any]] = []
    for slice_record in sorted(slices, key=lambda r: r.id):
        coverage = compute_slice_data_coverage(slice_record, derived_dir)
        coverage["slice_id"] = slice_record.id
        coverage["family_id"] = slice_record.family_id
        coverage["protocol_id"] = slice_record.protocol_id
        coverage["dataset_id"] = slice_record.dataset_id
        coverage["choice_type"] = slice_record.comparison.choice_type
        coverage["fittable_variant_ids"] = fittable_variants_for_slice(
            coverage, variants
        )
        slice_coverage.append(coverage)

    confidence_counts = {
        key: 0 for key in MODEL_SELECTION_CONFIDENCE_DEFINITIONS
    }
    for selection in model_selection_by_finding:
        confidence = selection["confidence_label"]
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
    scope_confidence_counts = {
        key: 0 for key in MODEL_SELECTION_CONFIDENCE_DEFINITIONS
    }
    for selection in model_selection_by_finding_scope:
        confidence = selection["confidence_label"]
        scope_confidence_counts[confidence] = (
            scope_confidence_counts.get(confidence, 0) + 1
        )

    comparison_scope_counts = {
        key: 0 for key in MODEL_COMPARISON_SCOPE_DEFINITIONS
    }
    scope_row_counts = {
        key: 0 for key in MODEL_COMPARISON_SCOPE_DEFINITIONS
    }
    for selection in model_selection_by_finding_scope:
        scope = selection["comparison_scope"]
        scope_row_counts[scope] = scope_row_counts.get(scope, 0) + 1
    interpretation_warnings: list[dict[str, Any]] = []
    interpretation_warning_counts: dict[str, int] = {}
    for selection in model_selection_by_finding:
        scope = selection["comparison_scope"]
        comparison_scope_counts[scope] = comparison_scope_counts.get(scope, 0) + 1
        warning = selection.get("interpretation_warning")
        if warning is None:
            continue
        interpretation_warnings.append(warning)
        warning_type = warning["warning_type"]
        interpretation_warning_counts[warning_type] = (
            interpretation_warning_counts.get(warning_type, 0) + 1
        )

    model_coverage_gaps = _model_coverage_gaps(
        findings_by_id=findings_by_id,
        fits_by_finding=fits_by_finding,
        selections=model_selection_by_finding,
        slice_coverage=slice_coverage,
        families=families,
        variants=variants,
    )
    model_coverage_roadmap = build_model_coverage_roadmap(
        findings_by_id=findings_by_id,
        model_selection_by_finding=model_selection_by_finding,
        model_coverage_gaps=model_coverage_gaps,
        interpretation_warnings=interpretation_warnings,
    )

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
        "fit_provenance_summary": fit_provenance_summary(fits),
        "caveat_tag_definitions": MODEL_FIT_CAVEAT_TAGS,
        "model_selection_confidence_definitions": (
            MODEL_SELECTION_CONFIDENCE_DEFINITIONS
        ),
        "model_comparison_scope_definitions": MODEL_COMPARISON_SCOPE_DEFINITIONS,
        "model_selection_confidence_counts": confidence_counts,
        "model_selection_scope_confidence_counts": scope_confidence_counts,
        "model_comparison_scope_counts": comparison_scope_counts,
        "model_selection_scope_counts": scope_row_counts,
        "model_selection_interpretation_warnings": interpretation_warnings,
        "model_selection_interpretation_warning_counts": (
            interpretation_warning_counts
        ),
        "model_coverage_gaps": model_coverage_gaps,
        "model_coverage_roadmap": model_coverage_roadmap,
        "families": family_payload,
        "variants": variant_payload,
        "fits": fit_payload,
        "fits_by_variant": fits_by_variant,
        "fits_by_finding": fits_by_finding,
        "model_selection_by_finding": model_selection_by_finding,
        "model_selection_by_finding_scope": model_selection_by_finding_scope,
        "slice_coverage": slice_coverage,
        "known_requirements": list(KNOWN_REQUIREMENTS),
    }


MODEL_SELECTION_CSV_FIELDS: tuple[str, ...] = (
    "selection_id",
    "selection_level",
    "finding_id",
    "paper_id",
    "curve_type",
    "protocol_id",
    "species",
    "source_data_level",
    "condition",
    "subject_id",
    "best_fit_id",
    "best_variant_id",
    "best_aic",
    "delta_aic_to_next",
    "confidence_label",
    "comparison_scope",
    "n_candidate_fits",
    "has_mixed_aic_scopes",
    "scope_selection_ids",
    "candidate_scope_counts",
    "candidate_fit_ids",
    "candidate_variant_ids",
    "candidate_comparison_scopes",
    "best_caveat_tags",
    "candidate_caveat_tags",
    "interpretation_warning_type",
)
MODEL_SELECTION_SCOPE_CSV_FIELDS = MODEL_SELECTION_CSV_FIELDS

FITS_BY_FINDING_CSV_FIELDS: tuple[str, ...] = (
    "finding_id",
    "paper_id",
    "curve_type",
    "fit_id",
    "variant_id",
    "aic",
    "bic",
    "log_likelihood",
    "n_trials",
    "n_free_params",
    "comparison_scope",
    "caveat_tags",
)

MODEL_ROADMAP_CSV_FIELDS: tuple[str, ...] = (
    "rank",
    "roadmap_id",
    "priority_score",
    "priority_label",
    "issue_type",
    "target_type",
    "target_id",
    "finding_id",
    "slice_id",
    "paper_id",
    "curve_type",
    "species",
    "source_data_level",
    "best_variant_id",
    "comparison_scope",
    "confidence_label",
    "n_candidate_fits",
    "related_variant_id",
    "missing_requirements",
    "caveat_tags",
    "warning_type",
    "status",
    "blocker_type",
    "blocker_detail",
    "next_action",
    "recommended_action",
    "impact",
    "rationale",
)


def _csv_list(values: Iterable[Any]) -> str:
    return "|".join(str(value) for value in values if value is not None)


def _csv_mapping(values: Mapping[str, Any]) -> str:
    return "|".join(
        f"{key}:{values[key]}"
        for key in sorted(values)
        if values[key] is not None
    )


def _csv_float(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.10g}"
    return "" if value is None else value


def _csv_bool(value: Any) -> str:
    return "true" if bool(value) else "false"


def model_selection_csv_rows(
    *,
    models_payload: Mapping[str, Any],
    findings_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    findings_by_id = {
        row["finding_id"]: row for row in findings_payload.get("findings", [])
    }
    rows: list[dict[str, Any]] = []
    for selection in models_payload.get("model_selection_by_finding", []):
        finding = findings_by_id.get(selection.get("finding_id"), {})
        strat = finding.get("stratification") or {}
        rows.append(
            {
                "selection_id": selection.get("selection_id", ""),
                "selection_level": selection.get("selection_level", "finding"),
                "finding_id": selection.get("finding_id", ""),
                "paper_id": finding.get("paper_id", ""),
                "curve_type": finding.get("curve_type", ""),
                "protocol_id": finding.get("protocol_id", ""),
                "species": finding.get("species", ""),
                "source_data_level": finding.get("source_data_level", ""),
                "condition": strat.get("condition", ""),
                "subject_id": strat.get("subject_id", ""),
                "best_fit_id": selection.get("best_fit_id", ""),
                "best_variant_id": selection.get("best_variant_id", ""),
                "best_aic": _csv_float(selection.get("best_aic")),
                "delta_aic_to_next": _csv_float(
                    selection.get("delta_aic_to_next")
                ),
                "confidence_label": selection.get("confidence_label", ""),
                "comparison_scope": selection.get("comparison_scope", ""),
                "n_candidate_fits": selection.get("n_candidate_fits", ""),
                "has_mixed_aic_scopes": _csv_bool(
                    selection.get("has_mixed_aic_scopes", False)
                ),
                "scope_selection_ids": _csv_list(
                    selection.get("scope_selection_ids", [])
                ),
                "candidate_scope_counts": _csv_mapping(
                    selection.get("candidate_scope_counts", {})
                ),
                "candidate_fit_ids": _csv_list(
                    selection.get("candidate_fit_ids", [])
                ),
                "candidate_variant_ids": _csv_list(
                    selection.get("candidate_variant_ids", [])
                ),
                "candidate_comparison_scopes": _csv_list(
                    selection.get("candidate_comparison_scopes", [])
                ),
                "best_caveat_tags": _csv_list(
                    selection.get("best_caveat_tags", [])
                ),
                "candidate_caveat_tags": _csv_list(
                    selection.get("candidate_caveat_tags", [])
                ),
                "interpretation_warning_type": (
                    (selection.get("interpretation_warning") or {}).get(
                        "warning_type",
                        "",
                    )
                ),
            }
        )
    return rows


def model_selection_scope_csv_rows(
    *,
    models_payload: Mapping[str, Any],
    findings_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return model_selection_csv_rows(
        models_payload={
            "model_selection_by_finding": models_payload.get(
                "model_selection_by_finding_scope",
                [],
            )
        },
        findings_payload=findings_payload,
    )


def fits_by_finding_csv_rows(
    *,
    models_payload: Mapping[str, Any],
    findings_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    findings_by_id = {
        row["finding_id"]: row for row in findings_payload.get("findings", [])
    }
    fits_by_id = {fit["id"]: fit for fit in models_payload.get("fits", [])}
    rows: list[dict[str, Any]] = []
    for finding_id, fit_ids in sorted(
        (models_payload.get("fits_by_finding") or {}).items()
    ):
        finding = findings_by_id.get(finding_id, {})
        for fit_id in fit_ids:
            fit = fits_by_id.get(fit_id)
            if fit is None:
                continue
            quality = fit.get("quality") or {}
            rows.append(
                {
                    "finding_id": finding_id,
                    "paper_id": finding.get("paper_id", ""),
                    "curve_type": finding.get("curve_type", ""),
                    "fit_id": fit.get("id", ""),
                    "variant_id": fit.get("variant_id", ""),
                    "aic": _csv_float(quality.get("aic")),
                    "bic": _csv_float(quality.get("bic")),
                    "log_likelihood": _csv_float(quality.get("log_likelihood")),
                    "n_trials": _csv_float(quality.get("n_trials")),
                    "n_free_params": _csv_float(quality.get("n_free_params")),
                    "comparison_scope": fit.get("comparison_scope", ""),
                    "caveat_tags": _csv_list(fit.get("caveat_tags", [])),
                }
            )
    return rows


def model_coverage_roadmap_csv_rows(
    *,
    models_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    roadmap = models_payload.get("model_coverage_roadmap") or {}
    for item in roadmap.get("items", []):
        rows.append(
            {
                **item,
                "missing_requirements": _csv_list(
                    item.get("missing_requirements", [])
                ),
                "caveat_tags": _csv_list(item.get("caveat_tags", [])),
            }
        )
    return rows


def _write_dict_csv(
    path: Path,
    *,
    fieldnames: tuple[str, ...],
    rows: Iterable[Mapping[str, Any]],
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
            count += 1
    return count


def write_model_selection_exports(
    *,
    derived_dir: Path,
    models_payload: Mapping[str, Any],
    findings_payload: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Write model-selection CSV artifacts beside derived/models.json."""
    selection_path = derived_dir / "model_selection.csv"
    scope_selection_path = derived_dir / "model_selection_by_scope.csv"
    fits_path = derived_dir / "fits_by_finding.csv"
    roadmap_path = derived_dir / "model_roadmap.csv"
    selection_rows = model_selection_csv_rows(
        models_payload=models_payload,
        findings_payload=findings_payload,
    )
    scope_selection_rows = model_selection_scope_csv_rows(
        models_payload=models_payload,
        findings_payload=findings_payload,
    )
    fit_rows = fits_by_finding_csv_rows(
        models_payload=models_payload,
        findings_payload=findings_payload,
    )
    roadmap_rows = model_coverage_roadmap_csv_rows(models_payload=models_payload)
    return {
        "model_selection": {
            "path": str(selection_path),
            "rows": _write_dict_csv(
                selection_path,
                fieldnames=MODEL_SELECTION_CSV_FIELDS,
                rows=selection_rows,
            ),
        },
        "model_selection_by_scope": {
            "path": str(scope_selection_path),
            "rows": _write_dict_csv(
                scope_selection_path,
                fieldnames=MODEL_SELECTION_SCOPE_CSV_FIELDS,
                rows=scope_selection_rows,
            ),
        },
        "fits_by_finding": {
            "path": str(fits_path),
            "rows": _write_dict_csv(
                fits_path,
                fieldnames=FITS_BY_FINDING_CSV_FIELDS,
                rows=fit_rows,
            ),
        },
        "model_roadmap": {
            "path": str(roadmap_path),
            "rows": _write_dict_csv(
                roadmap_path,
                fieldnames=MODEL_ROADMAP_CSV_FIELDS,
                rows=roadmap_rows,
            ),
        },
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
    _ensure_forwards_registered()
    return variant_id in _FORWARD_REGISTRY


def get_forward(variant_id: str) -> Any | None:
    _ensure_forwards_registered()
    return _FORWARD_REGISTRY.get(variant_id)


_FORWARDS_REGISTERED = False


def _ensure_forwards_registered() -> None:
    """Lazy import of the model_fits subpackage so each variant's
    `register_forward` call runs exactly once. Avoids a hard import
    cycle at module load: model_fits modules import model_layer, so
    we defer the back-import until the first registry lookup."""
    global _FORWARDS_REGISTERED
    if _FORWARDS_REGISTERED:
        return
    _FORWARDS_REGISTERED = True
    from behavtaskatlas import model_fits  # noqa: F401


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
        max_observed_residual = 0.0
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

            # Drift = forward(recorded_params) vs the recorded predictions
            # curve (if any). This is the staleness check: does running
            # the forward function with the recorded parameters still
            # produce the curve that was committed? It only fires if the
            # variant's forward implementation, the parameters, or the
            # finding's x grid have changed since the fit was recorded.
            # ModelFit.predictions holds at most one curve, so only the
            # finding whose curve_type matches that curve participates in
            # the consistency check; secondary findings (e.g. the
            # chronometric paired with a DDM fit) report GoF only.
            consistency_diffs: list[float] = []
            if (
                fit.predictions is not None
                and fit.predictions.curve_type == finding.curve.curve_type
            ):
                recorded = {p.x: p.y for p in fit.predictions.points}
                for pred in predicted:
                    if pred.x in recorded:
                        diff = abs(pred.y - recorded[pred.x])
                        consistency_diffs.append(diff)
                        if diff > max_diff_for_fit:
                            max_diff_for_fit = diff

            # Goodness-of-fit (informational only): forward(params) vs
            # the observed finding points.
            observed = {p.x: p.y for p in finding.curve.points}
            observed_diffs: list[float] = []
            for pred in predicted:
                if pred.x in observed:
                    obs_diff = abs(pred.y - observed[pred.x])
                    observed_diffs.append(obs_diff)
                    if obs_diff > max_observed_residual:
                        max_observed_residual = obs_diff

            per_finding.append(
                {
                    "finding_id": fid,
                    "status": "ok",
                    "n_points": len(consistency_diffs),
                    "max_consistency_diff": (
                        max(consistency_diffs) if consistency_diffs else 0.0
                    ),
                    "max_observed_residual": (
                        max(observed_diffs) if observed_diffs else 0.0
                    ),
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
                "max_consistency_diff": max_diff_for_fit,
                "max_observed_residual": max_observed_residual,
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
        f"max consistency |diff|={report['overall_max_abs_diff']:.6f} "
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
        if "max_consistency_diff" in r and r["status"] != "forward_unimplemented":
            line += (
                f" consistency |diff|={r['max_consistency_diff']:.6f},"
                f" GoF |residual|={r.get('max_observed_residual', 0.0):.4f}"
            )
        lines.append(line)
    return "\n".join(lines)
