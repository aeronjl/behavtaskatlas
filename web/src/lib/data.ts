import manifestJson from "../../../derived/manifest.json";
import catalogJson from "../../../derived/catalog.json";

export type Manifest = typeof manifestJson;
export type Catalog = typeof catalogJson;

export type ManifestSlice = Manifest["slices"][number];
export type ComparisonRow = Manifest["comparison_rows"][number];

export type CatalogTaskFamily = Catalog["task_families"][number];
export type CatalogProtocolRow = Catalog["protocols"][number];
export type CatalogDatasetRow = Catalog["datasets"][number];
export type CatalogVerticalSlice = Catalog["vertical_slices"][number];
export type CatalogProtocolDetail = Catalog["protocol_details"][number];
export type CatalogDatasetDetail = Catalog["dataset_details"][number];

export const manifest = manifestJson;
export const catalog = catalogJson;

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

export function slugForId(id: string): string {
  return id.replace(/^[^.]+\./, "");
}
