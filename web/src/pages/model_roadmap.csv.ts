import type { APIRoute } from "astro";
import { buildModelRoadmapCsv } from "../lib/modelExports";

export const GET: APIRoute = () =>
  new Response(buildModelRoadmapCsv(), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
