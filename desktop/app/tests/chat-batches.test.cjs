const assert = require("node:assert/strict");
const test = require("node:test");

const { wholeTurnBatches } = require("../chat.cjs");

test("whole conversations are batched by UTF-8 bytes without cutting their text", () => {
  const sources = [
    { source_id: "S1", text: "a".repeat(60) },
    { source_id: "S2", text: "b".repeat(60) },
    { source_id: "S3", text: "c".repeat(20) },
  ];
  const batches = wholeTurnBatches(sources, 100);
  assert.deepEqual(batches.map((batch) => batch.map((item) => item.source_id)), [["S1"], ["S2", "S3"]]);
  assert.equal(batches.flat()[0].text.length, 60);
});

test("multibyte text starts a new batch before its character count reaches the byte budget", () => {
  const sources = [
    { source_id: "S1", text: "я".repeat(30) },
    { source_id: "S2", text: "б".repeat(30) },
  ];
  const batches = wholeTurnBatches(sources, 100);
  assert.deepEqual(batches.map((batch) => batch.map((item) => item.source_id)), [["S1"], ["S2"]]);
});
