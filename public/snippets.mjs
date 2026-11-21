export function renderSnippet(segments) {
  if (!segments.length) return null;

  const excerpt = document.createElement("p");
  excerpt.className = "result-snippet";
  for (const { text, match } of segments) {
    if (match) {
      const mark = document.createElement("mark");
      mark.textContent = text;
      excerpt.append(mark);
    } else {
      excerpt.append(text);
    }
  }
  return excerpt;
}
