const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("first light separates selection from wake and keeps private logs visible", () => {
  const renderer = path.join(__dirname, "..", "renderer");
  const html = fs.readFileSync(path.join(renderer, "index.html"), "utf8");
  const js = fs.readFileSync(path.join(renderer, "app.js"), "utf8");
  assert.match(html, /id="choose-yukabox"/);
  assert.match(html, /id="choose-local"/);
  assert.match(html, /id="install"[^>]*>WAKE POCKET i/);
  assert.match(html, /id="open-test-log"/);
  assert.match(js, /chooseYukabox\.addEventListener/);
  assert.match(js, /chooseLocal\.addEventListener/);
  assert.match(js, /install\.addEventListener/);
});
