const http = require("http");
const fs = require("fs");
const path = require("path");

// Deployment platforms inject PORT (Render, Fly.io, Cloud Run, ...);
// keep the historical 127.0.0.1:3000 default for local development.
const host = process.env.HOST || "127.0.0.1";
const port = Number(process.env.PORT || 3000);

const root = path.join(__dirname, "web");

// The development page runs on :3000 while the API defaults to :5000, so the
// page CSP must allow that origin explicitly. Override with ACFM_API_ORIGIN
// (space separated) when serving the frontend on another host or port.
const apiOrigins = (
  process.env.ACFM_API_ORIGIN || "http://127.0.0.1:5000 http://localhost:5000"
).trim();
const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'none'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data: blob:",
  `connect-src 'self' ${apiOrigins}`,
].join("; ");
const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

const server = http.createServer((request, response) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD" });
    response.end("Method not allowed");
    return;
  }
  let requested;
  try {
    requested = new URL(request.url, "http://localhost").pathname;
  } catch {
    response.writeHead(400);
    response.end("Bad request");
    return;
  }
  const relative = requested === "/" ? "index.html" : requested.replace(/^\/+/, "");
  const file = path.resolve(root, relative);
  // Containment check that is independent of path-separator and drive-letter
  // casing (unlike a case-sensitive startsWith comparison on Windows).
  const rel = path.relative(root, file);
  if (rel.startsWith("..") || path.isAbsolute(rel)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }
  fs.readFile(file, (error, data) => {
    if (error) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }
    const extension = path.extname(file).toLowerCase();
    const isHtml = extension === ".html" || extension === "";
    response.writeHead(200, {
      "Content-Type": mime[extension] || "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "X-Frame-Options": "DENY",
      "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
      "Content-Security-Policy": contentSecurityPolicy,
      // HTML must never be cached; assets revalidate so deploys are immediate.
      "Cache-Control": isHtml ? "no-store" : "no-cache",
    });
    response.end(request.method === "HEAD" ? undefined : data);
  });
});

server.on("error", (error) => {
  console.error(`ACFM-Net frontend server error: ${error.message}`);
  process.exitCode = 1;
});

server.listen(port, host, () => {
  console.log(`ACFM-Net frontend: http://${host}:${port}`);
});

for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
  });
}
