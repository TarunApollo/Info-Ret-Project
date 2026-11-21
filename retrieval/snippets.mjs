export function highlightParams(query) {
  if (!query.trim()) return {};

  return {
    hl: "true",
    "hl.method": "unified",
    "hl.fl": "description",
    "hl.requireFieldMatch": "true",
    "hl.fragsize": "110",
    "hl.fragsizeIsMinimum": "false",
    "hl.fragAlignRatio": "0.2",
    "hl.bs.type": "WORD",
    "hl.defaultSummary": "true",
    "hl.encoder": "html",
    "hl.tag.pre": "<em>",
    "hl.tag.post": "</em>"
  };
}

const namedEntities = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };

function decodeText(text) {
  return text.replace(/&(amp|lt|gt|quot|apos|#x[\da-fA-F]+|#\d+);/g, (entity, name) => {
    if (name[0] !== "#") return namedEntities[name];
    const hex = name[1] === "x";
    const codePoint = Number.parseInt(name.slice(hex ? 2 : 1), hex ? 16 : 10);
    return codePoint <= 0x10ffff ? String.fromCodePoint(codePoint) : entity;
  });
}

export function resultSnippet(highlighting, id) {
  const excerpt = highlighting?.[id]?.description?.[0];
  if (!excerpt) return [];

  // Split the formatter's tags first. Literal markup from the description stays text.
  return excerpt.split(/<em>([\s\S]*?)<\/em>/)
    .map((text, index) => ({ text: decodeText(text), match: index % 2 === 1 }))
    .filter(segment => segment.text);
}
