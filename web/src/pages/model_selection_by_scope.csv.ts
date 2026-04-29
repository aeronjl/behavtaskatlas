import type { APIRoute } from "astro";
import { buildModelSelectionByScopeCsv } from "../lib/modelExports";

export const GET: APIRoute = () =>
  new Response(buildModelSelectionByScopeCsv(), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
