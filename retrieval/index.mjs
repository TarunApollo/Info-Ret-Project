import { readFile } from "node:fs/promises";
import { seriesIdPattern, solrBase, solrRequest } from "./solr.mjs";

const fields = [
  { name: "title", type: "text_general" },
  { name: "title_sort", type: "string", stored: false, docValues: true },
  { name: "aliases", type: "text_general", multiValued: true },
  { name: "creator", type: "text_general" },
  { name: "description", type: "text_general" },
  { name: "genres", type: "string", multiValued: true, docValues: true },
  { name: "publisher", type: "string", docValues: true },
  { name: "debut_year", type: "pint", docValues: true },
  { name: "source_urls", type: "string", multiValued: true, indexed: false },
].map(field => ({ indexed: true, stored: true, multiValued: false, ...field }));

function cleanText(value, name) {
  if (value === undefined || value === null) return "";
  if (typeof value !== "string") throw new Error(`${name} must be text`);
  return value.trim();
}

function cleanList(value, name) {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value)) throw new Error(`${name} must be an array`);
  return [...new Set(value.map(item => cleanText(item, name)).filter(Boolean))];
}

function normalizeRecord(record) {
  if (!record || typeof record !== "object" || Array.isArray(record)) throw new Error("Expected an object");
  const id = cleanText(record.id, "id");
  if (!seriesIdPattern.test(id)) throw new Error("id must be a lowercase URL slug");
  const title = cleanText(record.title, "title");
  if (!title) throw new Error("title is required");
  const sourceUrls = cleanList(record.source_urls, "source_urls");
  if (!sourceUrls.length) throw new Error("At least one source URL is required");
  for (const source of sourceUrls) {
    const url = URL.parse(source);
    if (!url || !["https:", "http:"].includes(url.protocol) || url.username || url.password) {
      throw new Error("Sources must be HTTP(S) URLs without credentials");
    }
  }
  const year = record.debut_year;
  if (year != null && (!Number.isInteger(year) || year < 1000 || year > 9999)) {
    throw new Error("debut_year must be a four-digit integer");
  }
  return {
    id,
    title,
    title_sort: title.normalize("NFKC").toLowerCase(),
    aliases: cleanList(record.aliases, "aliases"),
    creator: cleanText(record.creator, "creator"),
    description: cleanText(record.description, "description"),
    publisher: cleanText(record.publisher, "publisher"),
    genres: cleanList(record.genres, "genres"),
    source_urls: sourceUrls,
    ...(year == null ? {} : { debut_year: year }),
  };
}

async function importCatalog(path) {
  if (!path) throw new Error("Usage: node retrieval/index.mjs <records.json>");
  const records = JSON.parse(await readFile(path, "utf8"));
  if (!Array.isArray(records) || records.length === 0) throw new Error("Expected a nonempty JSON array");
  const seen = new Set();
  const documents = records.map((record, offset) => {
    try {
      const doc = normalizeRecord(record);
      if (seen.has(doc.id)) throw new Error(`Duplicate ID ${doc.id}`);
      seen.add(doc.id);
      return doc;
    } catch (error) {
      throw new Error(`Record ${offset + 1}: ${error.message}`);
    }
  });

  const { fields: existing } = await solrRequest("schema/fields");
  const fieldByName = new Map(existing.map(field => [field.name, field]));
  for (const field of fields) {
    const current = fieldByName.get(field.name);
    if (!current) await solrRequest("schema", {}, { "add-field": field });
    else if (current.type !== field.type || Boolean(current.multiValued) !== field.multiValued) {
      throw new Error(`Solr field ${field.name} has an incompatible schema`);
    }
  }

  await solrRequest("update", { commit: "true" }, documents);
  console.log(`Indexed ${documents.length} records into ${solrBase}.`);
}

try {
  await importCatalog(process.argv[2]);
} catch (error) {
  console.error(`Import failed: ${error.message}`);
  process.exitCode = 1;
}
