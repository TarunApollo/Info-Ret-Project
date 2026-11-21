import { publicRecord, recordFields, seriesIdPattern, solrRequest } from "../retrieval/solr.mjs";
import { buildFilterQueries } from "../retrieval/filters.mjs";
import { highlightParams, resultSnippet } from "../retrieval/snippets.mjs";

const pageSize = 12;

function reply(body, status = 200, headers = {}) {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store", ...headers } });
}

export default {
  async fetch(request) {
    if (request.method !== "GET") return reply({ error: "Use GET." }, 405, { Allow: "GET" });

    const params = new URL(request.url).searchParams;
    const id = params.get("id");
    const query = (params.get("q") ?? "").trim();
    const page = Number(params.get("page") ?? 1);

    if (id !== null && !seriesIdPattern.test(id)) return reply({ error: "Invalid series ID." }, 400);
    if (query.length > 120) return reply({ error: "Search queries can have up to 120 characters." }, 400);
    if (!Number.isInteger(page) || page < 1 || page > 1000) return reply({ error: "Invalid page." }, 400);

    try {
      if (id !== null) {
        const { doc } = await solrRequest("get", { id, fl: recordFields });
        return doc ? reply({ item: publicRecord(doc) }) : reply({ error: "Series not found." }, 404);
      }

      // Match the user's words as plain text and reserve Solr query syntax for the server.
      const words = query.toLowerCase().match(/[\p{L}\p{M}\p{N}]+/gu)?.join(" ") ?? "";
      if (query && !words) return reply({ items: [], total: 0, page, page_size: pageSize });
      const { response, highlighting } = await solrRequest("select", {
        q: words || "*:*",
        ...(words && {
          defType: "edismax",
          qf: "title^5 aliases^3 creator^2 description",
          pf: "title^8 aliases^4",
          uf: "-*",
          mm: "1"
        }),
        fq: buildFilterQueries(params),
        ...highlightParams(words),
        fl: recordFields,
        sort: words ? "score desc,title_sort asc,id asc" : "title_sort asc,id asc",
        start: (page - 1) * pageSize,
        rows: pageSize
      });
      return reply({
        items: response.docs.map(doc => ({
          ...publicRecord(doc),
          snippet: resultSnippet(highlighting, doc.id)
        })),
        total: response.numFound,
        page,
        page_size: pageSize
      });
    } catch (error) {
      console.error(`Solr read failed: ${error.message}`);
      return reply({ error: "The catalog is unavailable. Try again shortly." }, 503);
    }
  }
};
