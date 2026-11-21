import { renderSnippet } from "./snippets.mjs";

export function renderResults(container, seriesList, openSeries) {
  const list = document.createElement("ul");
  list.className = "results";
  for (const series of seriesList) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "result";
    button.textContent = series.title;
    if (series.creator) {
      const creator = document.createElement("span");
      creator.textContent = series.creator;
      button.append(creator);
    }
    button.addEventListener("click", () => openSeries(series.id));
    item.append(button);
    const snippet = renderSnippet(series.snippet ?? []);
    if (snippet) item.append(snippet);
    list.append(item);
  }
  container.replaceChildren(list);
}
