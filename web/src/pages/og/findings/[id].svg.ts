import type { APIRoute } from "astro";
import { findings, type FindingsEntry } from "../../../lib/findings";
import { slugForId } from "../../../lib/data";
import { renderOgCard } from "../../../lib/og";

export function getStaticPaths() {
  return (findings.findings as FindingsEntry[]).map((entry) => ({
    params: { id: slugForId(entry.finding_id) },
    props: { entry },
  }));
}

export const GET: APIRoute = async ({ props }) => {
  const entry = props.entry as FindingsEntry;
  const curveType = entry.curve_type.replace(/_/g, " ");
  const condition = entry.stratification?.condition;
  const subject = entry.stratification?.subject_id;
  const stratification = condition ?? subject ?? "pooled";
  const subtitle = [
    entry.paper_citation,
    entry.species ? `· ${entry.species}` : "",
  ]
    .filter(Boolean)
    .join(" ");
  const trials =
    typeof entry.n_trials === "number" && entry.n_trials > 0
      ? `${entry.n_trials.toLocaleString()} trials`
      : null;
  const footer = [
    entry.finding_id,
    entry.source_data_level,
    stratification,
    trials,
  ]
    .filter(Boolean)
    .join(" · ");

  // Sparkline shows the observed curve. Psychometric/accuracy curves
  // share a 0–1 y axis; chronometric leaves the domain auto-derived.
  const yDomain: [number, number] | undefined =
    entry.curve_type === "psychometric" ||
    entry.curve_type === "accuracy_by_strength"
      ? [0, 1]
      : undefined;

  const points = (entry.points ?? []).map((p) => ({ x: p.x, y: p.y }));

  const svg = renderOgCard({
    kicker: `Finding · ${curveType}`,
    title: entry.protocol_name ?? entry.finding_id,
    subtitle,
    footer,
    points,
    yDomain,
  });

  return new Response(svg, {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=86400, immutable",
    },
  });
};
