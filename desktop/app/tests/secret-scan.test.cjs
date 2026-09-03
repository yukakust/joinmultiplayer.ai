const assert = require("node:assert/strict");
const test = require("node:test");

const { secretCategories } = require("../secret-scan.cjs");

test("outbound scan catches credentials but leaves ordinary evidence alone", () => {
  assert.deepEqual(secretCategories("The route was absent from Caddy."), []);
  assert.deepEqual(secretCategories("Authorization: Bearer private-value-123456"), ["bearer_token"]);
  assert.deepEqual(secretCategories("api_key=private-value-123456"), ["named_secret"]);
});
