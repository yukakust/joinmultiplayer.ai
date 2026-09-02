const assert = require("node:assert/strict");
const test = require("node:test");

const {
  evidenceUnits,
  validateCandidates,
  validateAnswer,
  directionalNliJobs,
  mutualEntailmentPiles,
  validateCanonicals,
  canonicalValidationJobs,
  canonicalUnits,
  writerEvidenceFromPiles,
} = require("../evidence.cjs");

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

test("full sandwich groups mutual paraphrases but preserves a conflicting version", () => {
  const items = [
    { candidate_id: "C1", claim: "Restart only after power is isolated.", source_ids: ["S1"], evidence_blocks: [{ evidence_id: "S1.1", text: "Isolate power before restart." }] },
    { candidate_id: "C2", claim: "Power must be isolated before restart.", source_ids: ["S2"], evidence_blocks: [{ evidence_id: "S2.1", text: "Do not restart until power is isolated." }] },
    { candidate_id: "C3", claim: "Restart immediately.", source_ids: ["S3"], evidence_blocks: [{ evidence_id: "S3.1", text: "Restart immediately." }] },
  ];
  const primaryJobs = directionalNliJobs(items, "P");
  const primarySignals = primaryJobs.map((job) => ({
    candidate_id: job.candidate_id,
    label: new Set(["C1", "C2"]).has(job.left_id) && new Set(["C1", "C2"]).has(job.right_id)
      ? "entailment" : "contradiction",
  }));
  const primary = mutualEntailmentPiles(items, primaryJobs, primarySignals);
  assert.deepEqual(primary.map((pile) => pile.map((item) => item.candidate_id)), [["C1", "C2"], ["C3"]]);

  const canonicals = validateCanonicals({ piles: [
    { pile_id: "P1", claim: "Isolate power before restarting." },
    { pile_id: "P2", claim: "Restart immediately." },
  ] }, primary);
  const validationJobs = canonicalValidationJobs(canonicals);
  const units = canonicalUnits(canonicals, validationJobs, validationJobs.map((job) => ({
    candidate_id: job.candidate_id,
    label: "entailment",
  })));
  assert.deepEqual(units.map((item) => item.claim), ["Isolate power before restarting.", "Restart immediately."]);

  const finalJobs = directionalNliJobs(units, "F");
  const final = mutualEntailmentPiles(units, finalJobs, finalJobs.map((job) => ({
    candidate_id: job.candidate_id,
    label: "contradiction",
  })));
  const writer = writerEvidenceFromPiles(final);
  assert.equal(writer.length, 2);
  assert.deepEqual(writer[0].original_candidate_ids, ["C1", "C2"]);
  assert.deepEqual(writer[1].original_candidate_ids, ["C3"]);
});

test("a bad canonical rewrite is discarded without losing its exact originals", () => {
  const original = { candidate_id: "C1", claim: "Use remote controls only.", evidence_blocks: [] };
  const canonicals = [{ pile_id: "P1", claim: "Open the device by hand.", members: [original] }];
  const jobs = canonicalValidationJobs(canonicals);
  const units = canonicalUnits(canonicals, jobs, jobs.map((job) => ({
    candidate_id: job.candidate_id,
    label: "contradiction",
  })));
  assert.deepEqual(units, [{
    unit_id: "O-C1",
    claim: "Use remote controls only.",
    members: [original],
    canonical: false,
  }]);
});
