import findingsJson from "../../../derived/findings.json";
import comparisonsJson from "../../../derived/comparisons.json";

export type FindingsIndex = typeof findingsJson;
export type FindingsEntry = FindingsIndex["findings"][number];
export type FindingsCurvePoint = FindingsEntry["points"][number];

export type ComparisonsIndex = typeof comparisonsJson;
export type ComparisonEntry = ComparisonsIndex["comparisons"][number];

export const findings = findingsJson;
export const comparisons = comparisonsJson;

export function uniqueValues<T>(rows: T[], key: (row: T) => string | null | undefined): string[] {
  const out = new Set<string>();
  for (const row of rows) {
    const v = key(row);
    if (v !== null && v !== undefined && v !== "") out.add(v);
  }
  return Array.from(out).sort();
}
