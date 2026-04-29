import type { APIRoute } from "astro";
import { buildDataRequestsCsv } from "../lib/dataRequestExports";

export const GET: APIRoute = () =>
  new Response(buildDataRequestsCsv(), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
