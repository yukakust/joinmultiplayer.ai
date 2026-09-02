const assert = require("node:assert/strict");
const test = require("node:test");

const { evidenceUnits, validateCandidates, validateAnswer } = require("../evidence.cjs");

test("ordinary code resolves selected evidence IDs to exact source text", () => {
  const sources = [{ source_id: "S1", text: "First fact. DeBERTa is a cautious second signal, not the only judge." }];
  assert.deepEqual(evidenceUnits(sources), [
    { evidence_id: "S1.1", source_id: "S1", text: "First fact." },
    { evidence_id: "S1.2", source_id: "S1", text: "DeBERTa is a cautious second signal, not the only judge." },
  ]);
  const result = validateCandidates({ candidates: [
    { claim: "DeBERTa is not the sole judge.", evidence_ids: ["S1.2"] },
    { claim: "Invented coordinate.", evidence_ids: ["S1.9"] },
    { claim: "No coordinate." },
  ] }, sources);
  assert.equal(result.accepted.length, 1);
  assert.equal(result.accepted[0].quote, "DeBERTa is a cautious second signal, not the only judge.");
  assert.deepEqual(result.rejected.map((item) => item.reason), ["unknown evidence id", "invalid evidence ids"]);
});

test("final answer may cite only verified evidence labels", () => {
  const evidence = [{ candidate_id: "E1" }];
  assert.equal(validateAnswer("It is a second signal [E1].", evidence), true);
  assert.equal(validateAnswer("Unsupported [E2].", evidence), false);
  assert.equal(validateAnswer("No citation.", evidence), false);
});
