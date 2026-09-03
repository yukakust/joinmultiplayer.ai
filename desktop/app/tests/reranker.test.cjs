const assert = require("node:assert/strict");
const test = require("node:test");

const { RerankerManager } = require("../reranker.cjs");

test("reranker removes DROP but preserves TAKE and NOT_SURE", async () => {
  const manager = new RerankerManager({ executable: "unused", modelPath: "unused" });
  const scores = new Map([
    ["take", { score: 0.99, decision: "TAKE" }],
    ["unsure", { score: 0.4, decision: "NOT_SURE" }],
    ["drop", { score: 0.0001, decision: "DROP" }],
  ]);
  manager.score = async (_question, document) => scores.get(document);
  const result = await manager.filter("question", [
    { source_id: "S1", text: "take" },
    { source_id: "S2", text: "unsure" },
    { source_id: "S3", text: "drop" },
  ]);
  assert.deepEqual(result.rows.map((item) => item.decision), ["TAKE", "NOT_SURE", "DROP"]);
  assert.deepEqual(result.selected.map((item) => item.source_id), ["S1", "S2"]);
});
