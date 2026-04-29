import type { APIRoute } from "astro";
import { buildModelSelectionCsv } from "../lib/modelExports";

export const GET: APIRoute = () =>
  new Response(buildModelSelectionCsv(), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
