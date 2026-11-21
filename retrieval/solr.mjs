export const solrBase = (process.env.SOLR_URL || "http://127.0.0.1:8983/solr/panel").replace(/\/+$/, "");
export const recordFields = "id,title,aliases,creator,description,genres,publisher,debut_year,source_urls";
export const seriesIdPattern = /^[a-z0-9][a-z0-9-]{0,127}$/;

export async function solrRequest(path, params = {}, body) {
  const url = new URL(`${solrBase}/${path}`);
  url.searchParams.set("wt", "json");
  for (const [key, value] of Object.entries(params)) {
    for (const entry of Array.isArray(value) ? value : [value]) url.searchParams.append(key, entry);
  }
  const headers = { Accept: "application/json" };
  if (process.env.SOLR_AUTHORIZATION) headers.Authorization = process.env.SOLR_AUTHORIZATION;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(url, {
    method: body === undefined ? "GET" : "POST",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(5000)
  });
  const payload = await response.json();
  if (!response.ok || payload.error || payload.errors?.length) {
    throw new Error(payload.error?.msg || `Solr ${path} returned HTTP ${response.status}`);
  }
  return payload;
}

export function publicRecord(doc) {
  return {
    id: doc.id,
    title: doc.title,
    aliases: doc.aliases ?? [],
    creator: doc.creator ?? "",
    description: doc.description ?? "",
    genres: doc.genres ?? [],
    publisher: doc.publisher ?? "",
    debut_year: doc.debut_year ?? null,
    source_urls: doc.source_urls ?? []
  };
}
