import type { APIRoute, GetStaticPaths } from "astro";
import { dataRequests } from "../../lib/data";

type DataRequestExportEntry = {
  request_id: string;
  request_export_path?: string | null;
  request_export_markdown?: string | null;
};

function slugFromExportPath(path: string | null | undefined): string | null {
  if (!path) return null;
  const match = path.match(/^\/data_requests\/(.+)\.md$/);
  return match?.[1] ?? null;
}

export const getStaticPaths = (() =>
  ((dataRequests.requests ?? []) as DataRequestExportEntry[])
    .map((request) => ({
      request,
      slug: slugFromExportPath(request.request_export_path),
    }))
    .filter((row): row is { request: DataRequestExportEntry; slug: string } =>
      Boolean(row.slug && row.request.request_export_markdown),
    )
    .map((row) => ({
      params: { slug: row.slug },
      props: { request: row.request },
    }))) satisfies GetStaticPaths;

export const GET: APIRoute = ({ props }) => {
  const request = props.request as DataRequestExportEntry;
  return new Response(`${request.request_export_markdown ?? ""}\n`, {
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      "Cache-Control": "public, max-age=300",
    },
  });
};
