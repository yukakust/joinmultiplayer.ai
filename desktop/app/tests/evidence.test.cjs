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

test("one supported claim may keep exact blocks from multiple sources", () => {
  const sources = [
    { source_id: "S1", text: "DeBERTa is a fast reject signal." },
    { source_id: "S7", text: "It lowers false alarms but misses attacks, so it is not the only judge." },
  ];
  const result = validateCandidates({ candidates: [{
    claim: "DeBERTa is useful but cannot be the only judge.",
    evidence_ids: ["S1.1", "S7.1"],
  }] }, sources);
  assert.equal(result.accepted.length, 1);
  assert.deepEqual(result.accepted[0].source_ids, ["S1", "S7"]);
  assert.deepEqual(result.accepted[0].evidence_blocks.map((item) => item.evidence_id), ["S1.1", "S7.1"]);
  assert.equal(result.accepted[0].quote, "DeBERTa is a fast reject signal.\nIt lowers false alarms but misses attacks, so it is not the only judge.");
});

test("final answer may cite only verified evidence labels", () => {
  const evidence = [{ candidate_id: "E1" }];
  assert.equal(validateAnswer("It is a second signal [E1].", evidence), true);
  assert.equal(validateAnswer("Unsupported [E2].", evidence), false);
  assert.equal(validateAnswer("No citation.", evidence), false);
});
