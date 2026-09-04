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
  questionRelevancePrompt,
  validateQuestionRelevance,
  wholeTurnExtractionPrompt,
  validateWholeTurnCandidates,
  handledMessages,
  messageSelectionPrompt,
  validateMessageSelection,
  selectedMessageExtractionPrompt,
  validateSelectedMessageClaims,
} = require("../evidence.cjs");

test("two-stage whole-message interface hides real IDs and restores exact lines", () => {
  const sources = [{
    source_id: "S1",
    messages: [{
      message_id: "codex:private-long-id:10313",
      role: "assistant",
      text: "Cause: alignment drift.\nAction: keep it offline.",
    }],
  }];
  const messages = handledMessages(sources);
  assert.equal(messages[0].handle, "M1");
  const selectionPrompt = messageSelectionPrompt("What happened and what next?", messages);
  assert.match(selectionPrompt, /\[M1\]/);
  assert.doesNotMatch(selectionPrompt, /private-long-id/);
  const selected = validateMessageSelection({ message_ids: ["M1"] }, messages);
  assert.equal(selected.selected.length, 1);
  const prompt = selectedMessageExtractionPrompt("What happened and what next?", messages[0]);
  assert.match(prompt, /M1-L1/);
  assert.match(prompt, /M1-L2/);
  const checked = validateSelectedMessageClaims({ status: "FOUND", claims: [{
    claim: "Keep it offline.",
    message_id: "M1",
    evidence_ids: ["M1-L2"],
  }] }, messages[0]);
  assert.equal(checked.accepted.length, 1);
  assert.equal(checked.accepted[0].quote, "Action: keep it offline.");
  assert.equal(checked.accepted[0].evidence_blocks[0].message_id, "codex:private-long-id:10313");
});

test("two-stage whole-message interface blocks prompt placeholders and invented handles", () => {
  const message = handledMessages([{ source_id: "S1", messages: [{
    message_id: "real-id", role: "assistant", text: "Exact evidence.",
  }] }])[0];
  const placeholder = validateSelectedMessageClaims({ status: "FOUND", claims: [{
    claim: "one atomic statement", message_id: "M1", evidence_ids: ["M1-L1"],
  }] }, message);
  assert.equal(placeholder.accepted.length, 0);
  assert.equal(placeholder.rejected[0].reason, "placeholder claim");
  const invented = validateMessageSelection({ message_ids: ["M9"] }, [message]);
  assert.equal(invented.selected.length, 0);
  assert.equal(invented.rejected[0].reason, "unknown message handle");
});

test("whole-turn evidence keeps punctuation and accepts only an exact quote from an existing message", () => {
  const sources = [{
    source_id: "S1",
    text: "[M1] ASSISTANT: Llama-3.3 was already on a free tier.",
    messages: [{ message_id: "M1", role: "assistant", text: "Llama-3.3 was already on a free tier." }],
  }];
  const prompt = wholeTurnExtractionPrompt("Why use Llama-3.3?", sources);
  assert.match(prompt, /Llama-3\.3/);
  const result = validateWholeTurnCandidates({ status: "FOUND", claims: [{
    claim: "It was already free.",
    message_id: "M1",
    exact_quote: "Llama-3.3 was already on a free tier.",
  }] }, sources);
  assert.equal(result.accepted.length, 1);
  assert.equal(result.accepted[0].quote, "Llama-3.3 was already on a free tier.");
  const broken = validateWholeTurnCandidates({ status: "FOUND", claims: [{
    claim: "It was already free.", message_id: "M1", exact_quote: "Llama 3.3 was free.",
  }] }, sources);
  assert.equal(broken.accepted.length, 0);
  assert.equal(broken.rejected[0].reason, "quote is not exact");
});

test("question relevance keeps direct and compositional answer parts but drops adjacent truth", () => {
  const candidates = [
    { candidate_id: "E1", claim: "DeBERTa was added as a fast cautious reject signal." },
    { candidate_id: "E2", claim: "It misses context, so it cannot be the only judge." },
    { candidate_id: "E3", claim: "The /x route was absent from a Caddy allowlist." },
  ];
  const prompt = questionRelevancePrompt("Why was DeBERTa added, and why not use it alone?", candidates);
  assert.match(prompt, /contributes/);
  assert.doesNotMatch(prompt, /EXACT SOURCE/);
  const result = validateQuestionRelevance({ decisions: [
    { candidate_id: "E1", relation: "answers" },
    { candidate_id: "E2", relation: "contributes" },
    { candidate_id: "E3", relation: "unrelated" },
  ] }, candidates);
  assert.equal(result.valid, true);
  assert.deepEqual(result.accepted.map((item) => item.candidate_id), ["E1", "E2"]);
  assert.deepEqual(result.rejected.map((item) => item.candidate_id), ["E3"]);
});

test("question relevance fails closed on missing, duplicate, or invented decisions", () => {
  const candidates = [{ candidate_id: "E1", claim: "One" }, { candidate_id: "E2", claim: "Two" }];
  assert.equal(validateQuestionRelevance({ decisions: [
    { candidate_id: "E1", relation: "answers" },
  ] }, candidates).valid, false);
  assert.equal(validateQuestionRelevance({ decisions: [
    { candidate_id: "E1", relation: "answers" },
    { candidate_id: "E1", relation: "unrelated" },
  ] }, candidates).valid, false);
  assert.equal(validateQuestionRelevance({ decisions: [
    { candidate_id: "E1", relation: "answers" },
    { candidate_id: "E9", relation: "unrelated" },
  ] }, candidates).valid, false);
});

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
  assert.deepEqual(result.accepted[0].source_contexts, [{
    source_id: "S1",
    text: "First fact. DeBERTa is a cautious second signal, not the only judge.",
    exact_quotes: ["DeBERTa is a cautious second signal, not the only judge."],
  }]);
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
