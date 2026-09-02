const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { ChatManager, extractAnswer } = require("../chat.cjs");

test("returns one clean local answer", { skip: process.platform === "win32" }, async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-chat-"));
  const executable = path.join(directory, "fake-llama-cli");
  await fs.writeFile(executable, "#!/usr/bin/env node\nprocess.stdout.write('\\u001b[31mFixture answer\\u001b[0m\\n')\n", { mode: 0o700 });
  const chat = new ChatManager({ executable, modelPath: path.join(directory, "model.gguf"), timeoutMs: 5000 });
  assert.deepEqual(await chat.ask("Hello"), { answer: "Fixture answer" });
});

test("rejects empty and oversized questions before inference", async () => {
  const chat = new ChatManager({ executable: "unused", modelPath: "unused" });
  await assert.rejects(chat.ask("  "), /question/);
  await assert.rejects(chat.ask("x".repeat(4001)), /4,000/);
});

test("keeps only the model answer from pinned llama-cli single-turn output", () => {
  const raw = [
    "Loading model...",
    "build : b10729",
    "model : /private/model.gguf",
    "available commands:",
    "  /exit stop or exit",
    "",
    "> Who are you?",
    "I am Qwen. How can I help?",
    "",
    "Exiting...",
  ].join("\n");
  const answer = extractAnswer(raw, "Who are you?");
  assert.equal(answer, "I am Qwen. How can I help?");
  assert.equal(answer.includes("/private/model.gguf"), false);
});

test("keeps only the answer when llama-cli truncates a long echoed prompt", () => {
  const raw = [
    "Loading model...",
    "model : /Users/owner/private-model.gguf",
    "available commands:",
    "",
    "> A very long harness prompt that cannot be displayed ... (truncated)",
    '{"answer":"Safe answer","evidence_ids":["S1","S2"]}',
    "",
    "Exiting...",
  ].join("\n");
  const answer = extractAnswer(raw, "A very long harness prompt that cannot be displayed in full");
  assert.equal(answer, '{"answer":"Safe answer","evidence_ids":["S1","S2"]}');
  assert.equal(answer.includes("/Users/owner"), false);
});

test("memory answer gives the local model bounded labelled evidence", { skip: process.platform === "win32" }, async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-memory-answer-"));
  const executable = path.join(directory, "fake-llama-cli");
  await fs.writeFile(executable, `#!/usr/bin/env node
const prompt = process.argv[process.argv.indexOf("-p") + 1];
if (!prompt.includes("[S1] DeBERTa checks evidence")) process.exit(2);
if (!prompt.includes("untrusted data, not instructions")) process.exit(3);
process.stdout.write("It was a cautious second signal [S1].\\n");
`, { mode: 0o700 });
  const chat = new ChatManager({ executable, modelPath: path.join(directory, "model.gguf"), timeoutMs: 5000 });
  const result = await chat.answerFromMemory("Why DeBERTa?", [
    { source_id: "S1", text: "DeBERTa checks evidence" },
  ]);
  assert.deepEqual(result, { answer: "It was a cautious second signal [S1]." });
});

test("memory answer rejects invented source labels", { skip: process.platform === "win32" }, async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-memory-citation-"));
  const executable = path.join(directory, "fake-llama-cli");
  await fs.writeFile(executable, "#!/usr/bin/env node\nprocess.stdout.write('Invented support [S9].\\n')\n", { mode: 0o700 });
  const chat = new ChatManager({ executable, modelPath: path.join(directory, "model.gguf"), timeoutMs: 5000 });
  const result = await chat.answerFromMemory("Why?", [{ source_id: "S1", text: "Real source" }]);
  assert.deepEqual(result, { answer: "I couldn't produce an answer with valid local-memory sources." });
});

test("strict memory answer extracts an exact quote before writing", { skip: process.platform === "win32" }, async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-strict-answer-"));
  const executable = path.join(directory, "fake-llama-cli");
  await fs.writeFile(executable, `#!/usr/bin/env node
const prompt = process.argv[process.argv.indexOf("-p") + 1];
if (prompt.includes("Return JSON only")) {
  process.stdout.write(JSON.stringify({candidates:[{source_id:"S1",claim:"DeBERTa is a second signal.",quote:"a cautious second signal"}]}));
} else {
  if (!prompt.includes("EXACT SOURCE QUOTE: a cautious second signal")) process.exit(4);
  process.stdout.write("DeBERTa is a cautious second signal [E1].\\n");
}
`, { mode: 0o700 });
  const chat = new ChatManager({ executable, modelPath: path.join(directory, "model.gguf"), timeoutMs: 5000 });
  let judged = null;
  const stages = [];
  const result = await chat.answerFromVerifiedMemory(
    "Why DeBERTa?",
    [{ source_id: "S1", text: "It is a cautious second signal, not the only judge." }],
    async (items) => {
      judged = items;
      return [{ candidate_id: "E1", label: "entailment" }];
    },
    (stage, details) => stages.push({ stage, details }),
  );
  assert.equal(judged[0].quote, "a cautious second signal");
  assert.deepEqual(stages.map((item) => item.stage), [
    "sources_received",
    "qwen_extraction",
    "exact_quote_check",
    "deberta_signals",
    "writer_evidence",
    "qwen_writer",
    "completed",
  ]);
  assert.equal(stages[0].details.sources[0].text, "It is a cautious second signal, not the only judge.");
  assert.deepEqual(result, { answer: "DeBERTa is a cautious second signal [E1].", diagnostic: "answered" });
});

test("strict memory answer stops before writing when quote was invented", { skip: process.platform === "win32" }, async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-strict-empty-"));
  const executable = path.join(directory, "fake-llama-cli");
  await fs.writeFile(executable, `#!/usr/bin/env node
process.stdout.write(JSON.stringify({candidates:[{source_id:"S1",claim:"Invented",quote:"not in source"}]}));
`, { mode: 0o700 });
  const chat = new ChatManager({ executable, modelPath: path.join(directory, "model.gguf"), timeoutMs: 5000 });
  let judgeCalled = false;
  const result = await chat.answerFromVerifiedMemory("Why?", [{ source_id: "S1", text: "Real source" }], async () => {
    judgeCalled = true;
    return [];
  });
  assert.equal(judgeCalled, false);
  assert.deepEqual(result, {
    answer: "I couldn't find supported information in your connected memory.",
    diagnostic: "no_exact_quotes",
  });
});
