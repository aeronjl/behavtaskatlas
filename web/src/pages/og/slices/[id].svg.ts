import type { APIRoute } from "astro";
import { manifest, slugForId, type ManifestSlice } from "../../../lib/data";
import { renderOgCard } from "../../../lib/og";

export function getStaticPaths() {
  return manifest.slices.map((slice) => ({
    params: { id: slugForId(slice.id) },
    props: { slice },
  }));
}

export const GET: APIRoute = async ({ props }) => {
  const slice = props.slice as ManifestSlice;
  const subtitle = [
    slice.comparison.species,
    slice.comparison.modality,
    slice.comparison.choice_type,
  ]
    .filter(Boolean)
    .join(" · ");
  const footer = [
    slice.id,
    slice.comparison.source_data_level,
    slice.report_status === "available" ? "report available" : "no report",
  ]
    .filter(Boolean)
    .join(" · ");

  const svg = renderOgCard({
    kicker: "Vertical slice",
    title: slice.title,
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
