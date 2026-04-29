import { models } from "./data";
import { findings as findingsIndex } from "./findings";

const MODEL_SELECTION_FIELDS = [
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
];
const MODEL_SELECTION_SCOPE_FIELDS = MODEL_SELECTION_FIELDS;

const FITS_BY_FINDING_FIELDS = [
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
];

const MODEL_ROADMAP_FIELDS = [
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
];

function csvValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join("|");
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, entry]) => `${key}:${entry}`)
      .join("|");
  }
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "";
  const text = String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function toCsv(fields: string[], rows: Array<Record<string, unknown>>): string {
  const lines = [fields.join(",")];
  for (const row of rows) {
    lines.push(fields.map((field) => csvValue(row[field])).join(","));
  }
  return `${lines.join("\n")}\n`;
}

export function buildModelSelectionCsv(): string {
  const findingsById = new Map(
    ((findingsIndex.findings ?? []) as Array<Record<string, any>>).map((row) => [
      row.finding_id,
      row,
    ]),
  );
  const selections =
    ((models as unknown as { model_selection_by_finding?: Array<Record<string, any>> })
      .model_selection_by_finding ?? []);
  const rows = selections.map((selection) => {
    const finding = findingsById.get(selection.finding_id) ?? {};
    const strat = finding.stratification ?? {};
    return {
      finding_id: selection.finding_id,
      paper_id: finding.paper_id,
      curve_type: finding.curve_type,
      protocol_id: finding.protocol_id,
      species: finding.species,
      source_data_level: finding.source_data_level,
      condition: strat.condition,
      subject_id: strat.subject_id,
      selection_id: selection.selection_id,
      selection_level: selection.selection_level ?? "finding",
      best_fit_id: selection.best_fit_id,
      best_variant_id: selection.best_variant_id,
      best_aic: selection.best_aic,
      delta_aic_to_next: selection.delta_aic_to_next,
      confidence_label: selection.confidence_label,
      comparison_scope: selection.comparison_scope,
      n_candidate_fits: selection.n_candidate_fits,
      has_mixed_aic_scopes: selection.has_mixed_aic_scopes ?? false,
      scope_selection_ids: selection.scope_selection_ids ?? [],
      candidate_scope_counts: selection.candidate_scope_counts ?? {},
      candidate_fit_ids: selection.candidate_fit_ids ?? [],
      candidate_variant_ids: selection.candidate_variant_ids ?? [],
      candidate_comparison_scopes: selection.candidate_comparison_scopes ?? [],
      best_caveat_tags: selection.best_caveat_tags ?? [],
      candidate_caveat_tags: selection.candidate_caveat_tags ?? [],
      interpretation_warning_type: selection.interpretation_warning?.warning_type,
    };
  });
  return toCsv(MODEL_SELECTION_FIELDS, rows);
}

export function buildModelSelectionByScopeCsv(): string {
  const findingsById = new Map(
    ((findingsIndex.findings ?? []) as Array<Record<string, any>>).map((row) => [
      row.finding_id,
      row,
    ]),
  );
  const selections =
    ((models as unknown as {
      model_selection_by_finding_scope?: Array<Record<string, any>>;
    }).model_selection_by_finding_scope ?? []);
  const rows = selections.map((selection) => {
    const finding = findingsById.get(selection.finding_id) ?? {};
    const strat = finding.stratification ?? {};
    return {
      selection_id: selection.selection_id,
      selection_level: selection.selection_level ?? "comparison_scope",
      finding_id: selection.finding_id,
      paper_id: finding.paper_id,
      curve_type: finding.curve_type,
      protocol_id: finding.protocol_id,
      species: finding.species,
      source_data_level: finding.source_data_level,
      condition: strat.condition,
      subject_id: strat.subject_id,
      best_fit_id: selection.best_fit_id,
      best_variant_id: selection.best_variant_id,
      best_aic: selection.best_aic,
      delta_aic_to_next: selection.delta_aic_to_next,
      confidence_label: selection.confidence_label,
      comparison_scope: selection.comparison_scope,
      n_candidate_fits: selection.n_candidate_fits,
      has_mixed_aic_scopes: selection.has_mixed_aic_scopes ?? false,
      scope_selection_ids: selection.scope_selection_ids ?? [],
      candidate_scope_counts: selection.candidate_scope_counts ?? {},
      candidate_fit_ids: selection.candidate_fit_ids ?? [],
      candidate_variant_ids: selection.candidate_variant_ids ?? [],
      candidate_comparison_scopes: selection.candidate_comparison_scopes ?? [],
      best_caveat_tags: selection.best_caveat_tags ?? [],
      candidate_caveat_tags: selection.candidate_caveat_tags ?? [],
      interpretation_warning_type: selection.interpretation_warning?.warning_type,
    };
  });
  return toCsv(MODEL_SELECTION_SCOPE_FIELDS, rows);
}

export function buildFitsByFindingCsv(): string {
  const findingsById = new Map(
    ((findingsIndex.findings ?? []) as Array<Record<string, any>>).map((row) => [
      row.finding_id,
      row,
    ]),
  );
  const fitsById = new Map(
    ((models.fits ?? []) as Array<Record<string, any>>).map((fit) => [fit.id, fit]),
  );
  const fitsByFinding =
    (models as unknown as { fits_by_finding?: Record<string, string[]> })
      .fits_by_finding ?? {};
  const rows: Array<Record<string, unknown>> = [];
  for (const [findingId, fitIds] of Object.entries(fitsByFinding).sort()) {
    const finding = findingsById.get(findingId) ?? {};
    for (const fitId of fitIds) {
      const fit = fitsById.get(fitId);
      if (!fit) continue;
      const quality = fit.quality ?? {};
      rows.push({
        finding_id: findingId,
        paper_id: finding.paper_id,
        curve_type: finding.curve_type,
        fit_id: fit.id,
        variant_id: fit.variant_id,
        aic: quality.aic,
        bic: quality.bic,
        log_likelihood: quality.log_likelihood,
        n_trials: quality.n_trials,
        n_free_params: quality.n_free_params,
        comparison_scope: fit.comparison_scope,
        caveat_tags: fit.caveat_tags ?? [],
      });
    }
  }
  return toCsv(FITS_BY_FINDING_FIELDS, rows);
}

export function buildModelRoadmapCsv(): string {
  const roadmap =
    (models as unknown as {
      model_coverage_roadmap?: { items?: Array<Record<string, unknown>> };
    }).model_coverage_roadmap?.items ?? [];
  return toCsv(MODEL_ROADMAP_FIELDS, roadmap);
}
