import type { APIRoute } from "astro";
import { stories } from "../../../lib/stories";
import { renderOgCard } from "../../../lib/og";

export function getStaticPaths() {
  return stories.map((story) => ({
    params: { slug: story.slug },
    props: { story },
  }));
}

export const GET: APIRoute = async ({ props }) => {
  const story = props.story as (typeof stories)[number];
  const subtitle = story.surface;
  const footer = [
    `${story.readMinutes} min read`,
    story.speciesCount ? `${story.speciesCount} species` : null,
    story.publishedAt,
  ]
    .filter(Boolean)
    .join(" · ");
  const svg = renderOgCard({
    kicker: "Story",
    title: story.title,
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
