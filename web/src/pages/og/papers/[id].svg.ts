import type { APIRoute } from "astro";
import { papers, slugForId, type PaperEntry } from "../../../lib/data";
import { renderOgCard } from "../../../lib/og";

export function getStaticPaths() {
  return (papers.papers as PaperEntry[]).map((paper) => ({
    params: { id: paper.slug ?? slugForId(paper.id) },
    props: { paper },
  }));
}

export const GET: APIRoute = async ({ props }) => {
  const paper = props.paper as PaperEntry;
  const findingsCount = paper.finding_count ?? 0;
  const trials = paper.total_n_trials > 0
    ? `${paper.total_n_trials.toLocaleString()} trials`
    : null;
  const subtitle = [
    paper.lab,
    paper.venue,
    paper.year ? String(paper.year) : "",
  ]
    .filter(Boolean)
    .join(" · ");

  const footer = [
    paper.id,
    findingsCount > 0
      ? `${findingsCount} finding${findingsCount === 1 ? "" : "s"}`
      : "no extracted findings",
    trials,
    paper.coverage_status,
  ]
    .filter(Boolean)
    .join(" · ");

  const svg = renderOgCard({
    kicker: "Paper",
    title: paper.citation ?? paper.id,
    subtitle,
    footer,
  });

  return new Response(svg, {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=86400, immutable",
    },
  });
};
