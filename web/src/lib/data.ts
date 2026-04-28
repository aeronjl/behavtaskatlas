import manifestJson from "../../../derived/manifest.json";
import catalogJson from "../../../derived/catalog.json";
import graphJson from "../../../derived/graph.json";
import curationQueueJson from "../../../derived/curation_queue.json";
import papersJson from "../../../derived/papers.json";

export type Manifest = typeof manifestJson;
export type Catalog = typeof catalogJson;
export type Graph = typeof graphJson;
export type CurationQueue = typeof curationQueueJson;

export type ManifestSlice = Manifest["slices"][number];
export type ComparisonRow = Manifest["comparison_rows"][number];

export type CatalogTaskFamily = Catalog["task_families"][number];
export type CatalogProtocolRow = Catalog["protocols"][number];
export type CatalogDatasetRow = Catalog["datasets"][number];
export type CatalogVerticalSlice = Catalog["vertical_slices"][number];
export type CatalogProtocolDetail = Catalog["protocol_details"][number];
export type CatalogDatasetDetail = Catalog["dataset_details"][number];

export type GraphNode = Graph["nodes"][number];
export type GraphEdge = Graph["edges"][number];

export const manifest = manifestJson;
export const catalog = catalogJson;
export const graph = graphJson;
export const curationQueue = curationQueueJson;

export type PapersIndex = typeof papersJson;
export type PaperEntry = PapersIndex["papers"][number];
export const papers = papersJson;

export function getPaper(id: string): PaperEntry | undefined {
  return papers.papers.find((p) => p.id === id || p.slug === id);
}

export function bibtexHref(text: string): string {
  return `data:application/x-bibtex;charset=utf-8,${encodeURIComponent(text)}`;
}

export function risHref(text: string): string {
  return `data:application/x-research-info-systems;charset=utf-8,${encodeURIComponent(text)}`;
}

export function getProtocolDetail(
  id: string,
): CatalogProtocolDetail | undefined {
  return catalog.protocol_details.find((row) => row.protocol_id === id);
}

export function getDatasetDetail(
  id: string,
): CatalogDatasetDetail | undefined {
  return catalog.dataset_details.find((row) => row.dataset_id === id);
}

export function getSlice(id: string): ManifestSlice | undefined {
  return manifest.slices.find((slice) => slice.id === id);
}

export function slugForId(id: string): string {
  return id.replace(/^[^.]+\./, "");
}

export function hrefForNode(node: GraphNode): string | null {
  const slug = slugForId(node.node_id);
  switch (node.node_type) {
    case "protocol":
      return `/protocols/${slug}`;
    case "dataset":
      return `/datasets/${slug}`;
    case "vertical_slice":
      return `/slices/${slug}`;
    case "task_family":
    default:
      return null;
  }
}
