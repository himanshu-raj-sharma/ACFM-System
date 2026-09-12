const http = require("http");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "web");
const mime = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript" };

http.createServer((request, response) => {
  const requested = request.url === "/" ? "/index.html" : request.url;
  const file = path.join(root, path.normalize(requested));
  if (!file.startsWith(root)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }
  fs.readFile(file, (error, data) => {
    if (error) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": mime[path.extname(file)] || "text/plain" });
    response.end(data);
  });
}).listen(3000, "127.0.0.1", () => {
  console.log("ACFM-Net frontend: http://127.0.0.1:3000");
});
