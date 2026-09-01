const assert = require("node:assert/strict");
const test = require("node:test");

const { validateCandidates, validateAnswer } = require("../evidence.cjs");

test("accepts only exact quotes from known local excerpts", () => {
  const sources = [{ source_id: "S1", text: "DeBERTa is a cautious second signal, not the only judge." }];
  const result = validateCandidates({ candidates: [
    { source_id: "S1", claim: "DeBERTa is not the sole judge.", quote: "not the only judge" },
    { source_id: "S1", claim: "Invented.", quote: "the final authority" },
    { source_id: "S9", claim: "Wrong source.", quote: "anything" },
  ] }, sources);
  assert.equal(result.accepted.length, 1);
  assert.equal(result.accepted[0].quote, "not the only judge");
  assert.deepEqual(result.rejected.map((item) => item.reason), ["quote is not exact", "unknown source"]);
});

test("final answer may cite only verified evidence labels", () => {
  const evidence = [{ candidate_id: "E1" }];
  assert.equal(validateAnswer("It is a second signal [E1].", evidence), true);
  assert.equal(validateAnswer("Unsupported [E2].", evidence), false);
  assert.equal(validateAnswer("No citation.", evidence), false);
});
