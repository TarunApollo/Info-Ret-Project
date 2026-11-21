import { renderResults } from "./results.mjs";
import { mountFilters } from "./filters.mjs";

const byId = id => document.getElementById(id);
const searchInput = byId("search-input");
const heading = byId("catalog-title");
const filterForm = byId("catalog-filters");
const status = byId("catalog-status");
const results = byId("results");
const pagination = byId("pagination");
const detail = byId("series-detail");

const locationInfo = new URL(location.href);
let query = (locationInfo.searchParams.get("q") ?? "").slice(0, 120);
let page = Number(locationInfo.searchParams.get("page") ?? 1);
if (!Number.isInteger(page) || page < 1 || page > 1000) page = 1;
searchInput.value = query;
mountFilters(filterForm, locationInfo.searchParams);
filterForm.hidden = filterForm.elements.length === 0;
let listRequest;
let detailRequest;

async function fetchSeries(params, signal) {
  const response = await fetch(`/api/series?${new URLSearchParams(params)}`, { signal });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error ?? "Request failed.");
  return payload;
}

async function loadResults({ focus = false } = {}) {
  listRequest?.abort();
  listRequest = new AbortController();
  const { signal } = listRequest;

  const params = new URLSearchParams([...new FormData(filterForm)].filter(([, value]) => value !== ""));
  if (query) params.set("q", query);
  if (page !== 1) params.set("page", page);
  const url = new URL(location.href);
  url.search = params;
  history.replaceState(null, "", url);

  heading.textContent = query ? `Results for “${query}”` : "Browse the catalog";
  if (focus) heading.focus();
  status.textContent = "Loading manga…";
  results.replaceChildren();
  pagination.hidden = true;

  try {
    const { items, total, page_size } = await fetchSeries(params, signal);
    if (signal.aborted) return;
    renderResults(results, items, showSeries);
    status.textContent = total ? `${total} series` : "No series found.";
    if (!items.length && total) status.textContent = "There are no series on this page.";
    byId("previous-page").disabled = page <= 1;
    byId("next-page").disabled = page * page_size >= total || page >= 1000;
    pagination.hidden = total <= page_size && page === 1;
  } catch (error) {
    if (!signal.aborted) status.textContent = error.message || "The catalog is unavailable.";
  }
}

async function showSeries(id) {
  detailRequest?.abort();
  detailRequest = new AbortController();
  const { signal } = detailRequest;
  const title = byId("detail-title");
  const creator = byId("detail-creator");
  const description = byId("detail-description");
  const sources = byId("detail-sources");

  title.textContent = "Series details";
  creator.textContent = "";
  description.textContent = "Loading series…";
  sources.replaceChildren();
  detail.showModal();
  title.focus();

  try {
    const { item } = await fetchSeries({ id }, signal);
    if (signal.aborted) return;
    title.textContent = item.title;
    creator.textContent = [item.creator, item.publisher, item.debut_year].filter(Boolean).join(" · ");
    description.textContent = item.description;
    for (const source of item.source_urls) {
      const url = URL.parse(source);
      if (!url || !["https:", "http:"].includes(url.protocol) || url.username || url.password) continue;
      const link = document.createElement("a");
      link.href = url.href;
      link.textContent = url.hostname;
      const row = document.createElement("li");
      row.append(link);
      sources.append(row);
    }
  } catch (error) {
    if (!signal.aborted) description.textContent = error.message || "Series details are unavailable.";
  }
}

byId("search-form").addEventListener("submit", event => {
  event.preventDefault();
  query = searchInput.value.trim();
  page = 1;
  loadResults({ focus: true });
});
function applyFilters(event) {
  event.preventDefault();
  page = 1;
  loadResults();
}
filterForm.addEventListener("change", applyFilters);
filterForm.addEventListener("submit", applyFilters);
byId("previous-page").addEventListener("click", () => {
  page -= 1;
  loadResults({ focus: true });
});
byId("next-page").addEventListener("click", () => {
  page += 1;
  loadResults({ focus: true });
});
detail.addEventListener("close", () => detailRequest?.abort());

loadResults();
