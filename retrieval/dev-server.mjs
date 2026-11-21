import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import series from "../api/series.mjs";

const root = fileURLToPath(new URL("../public", import.meta.url));
const port = Number(process.env.PORT || 4173);
const base = `http://127.0.0.1:${port}`;
const media = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".png": "image/png",
  ".webp": "image/webp",
};

createServer(async (request, response) => {
  try {
    const url = new URL(request.url, base);
    if (url.pathname === "/api/series") {
      const result = await series.fetch(new Request(url, { method: request.method }));
      response.writeHead(result.status, Object.fromEntries(result.headers));
      response.end(Buffer.from(await result.arrayBuffer()));
      return;
    }
    if (!["GET", "HEAD"].includes(request.method)) {
      response.writeHead(405, { Allow: "GET, HEAD" }).end("Method not allowed");
      return;
    }
    const path = resolve(root, `.${decodeURIComponent(url.pathname)}${url.pathname === "/" ? "index.html" : ""}`);
    const type = media[extname(path)];
    if (!path.startsWith(root + sep) || !type) {
      response.writeHead(404).end("Not found");
      return;
    }
    const file = await readFile(path);
    response.writeHead(200, { "Content-Type": type, "Content-Length": file.length });
    response.end(request.method === "HEAD" ? undefined : file);
  } catch (error) {
    if (error.code === "ENOENT") response.writeHead(404).end("Not found");
    else if (error instanceof URIError) response.writeHead(400).end("Invalid path");
    else {
      console.error(error.message);
      response.writeHead(500).end("Server error");
    }
  }
}).listen(port, "127.0.0.1", () => console.log(`Panel is serving at ${base}`));
