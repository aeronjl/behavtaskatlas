import searchJson from "../../../derived/search.json";

export type SearchEntry = (typeof searchJson)["entries"][number];
export type SearchPayload = typeof searchJson;
export const searchIndex = searchJson;
