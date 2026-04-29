import type { APIRoute } from "astro";
import { buildFitsByFindingCsv } from "../lib/modelExports";

export const GET: APIRoute = () =>
  new Response(buildFitsByFindingCsv(), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
