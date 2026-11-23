import { renderSnippet } from "./snippets.mjs";

const columns = ["Title", "Creator", "Genres", "Publisher", "Year"];

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

export function renderResults(container, seriesList, openSeries) {
  if (!seriesList.length) {
    container.replaceChildren();
    return;
  }

  const table = document.createElement("table");
  table.className = "results";
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = "Manga series. Select a title to see its details and sources.";
  const headRow = document.createElement("tr");
  for (const name of columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = name;
    headRow.append(th);
  }
  table.createTHead().append(headRow);

  const body = table.createTBody();
  for (const series of seriesList) {
    const row = body.insertRow();
    const titleCell = document.createElement("th");
    titleCell.scope = "row";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "result-title";
    button.textContent = series.title;
    button.addEventListener("click", () => openSeries(series.id));
    titleCell.append(button);
    const snippet = renderSnippet(series.snippet ?? []);
    if (snippet) titleCell.append(snippet);

    row.append(
      titleCell,
      cell(series.creator),
      cell(series.genres.join(", ")),
      cell(series.publisher),
      cell(series.debut_year ?? "")
    );
  }

  const scroller = document.createElement("div");
  scroller.className = "results-scroll";
  scroller.append(table);
  container.replaceChildren(scroller);
}
