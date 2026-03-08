import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { existsSync } from "node:fs";

const PORT = process.env.PORT || 8080;
const DIST = import.meta.dirname;

const MIME = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

const server = createServer(async (req, res) => {
  let filePath = join(DIST, req.url === "/" ? "index.html" : req.url);

  // SPA fallback: if the file doesn't exist and it's not a file extension, serve index.html
  if (!existsSync(filePath) || (!extname(filePath) && !existsSync(filePath))) {
    filePath = join(DIST, "index.html");
  }

  try {
    const data = await readFile(filePath);
    const ext = extname(filePath);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  } catch {
    // Final fallback to index.html for SPA routing
    try {
      const data = await readFile(join(DIST, "index.html"));
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end("Not Found");
    }
  }
});

server.listen(PORT, () => console.log(`Serving on port ${PORT}`));
