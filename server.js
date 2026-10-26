const http = require("http");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "web");
const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
};

http.createServer((request, response) => {
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
  if (file !== root && !file.startsWith(`${root}${path.sep}`)) {
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
    response.writeHead(200, {
      "Content-Type": mime[path.extname(file).toLowerCase()] || "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "Cache-Control": "no-store",
    });
    response.end(request.method === "HEAD" ? undefined : data);
  });
}).listen(3000, "127.0.0.1", () => {
  console.log("ACFM-Net frontend: http://127.0.0.1:3000");
});
