const test = require("node:test");
const assert = require("node:assert/strict");

const { apiBaseUrl } = require("./app.js");

function documentWithMeta(value) {
  return {
    querySelector() {
      return value === undefined
        ? null
        : { getAttribute: () => value };
    },
  };
}

test("uses the configured API base URL", () => {
  assert.equal(
    apiBaseUrl(
      { protocol: "http:", hostname: "example.test", port: "3000" },
      documentWithMeta("https://api.example.test/"),
    ),
    "https://api.example.test",
  );
});

test("defaults to the backend beside the development frontend", () => {
  assert.equal(
    apiBaseUrl(
      { protocol: "http:", hostname: "localhost", port: "3000" },
      documentWithMeta(),
    ),
    "http://localhost:5000",
  );
});

test("uses same-origin requests in the production container", () => {
  assert.equal(
    apiBaseUrl(
      { protocol: "https:", hostname: "monitor.example.test", port: "443" },
      documentWithMeta(),
    ),
    "",
  );
});
