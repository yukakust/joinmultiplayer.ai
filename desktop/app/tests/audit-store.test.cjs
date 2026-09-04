const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { beginPrivateAudit, privateAuditPaths, recordPrivateAudit } = require("../audit-store.cjs");

test("ships the audit store inside the packaged application", () => {
  const packageDefinition = require("../package.json");
  assert.ok(packageDefinition.build.files.includes("audit-store.cjs"));
});

test("keeps every private answer audit and also updates the latest copy", async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-audits-"));
  const first = { stages: [{ stage: "sources_received", details: { question: "First?" } }], final: { answer: "one" } };
  const second = { stages: [{ stage: "sources_received", details: { question: "Second?" } }], final: { answer: "two" } };
  await recordPrivateAudit(root, first, new Date("2026-09-02T10:00:00.000Z"));
  await recordPrivateAudit(root, second, new Date("2026-09-02T10:00:01.000Z"));

  const targets = privateAuditPaths(root);
  const files = (await fs.readdir(targets.directory)).filter((name) => name.endsWith(".json"));
  assert.equal(files.length, 2);
  const saved = await Promise.all(files.map((name) => fs.readFile(path.join(targets.directory, name), "utf8").then(JSON.parse)));
  assert.deepEqual(saved.map((item) => item.final.answer).sort(), ["one", "two"]);
  assert.equal(JSON.parse(await fs.readFile(targets.latest, "utf8")).final.answer, "two");
  assert.equal((await fs.stat(targets.directory)).mode & 0o777, 0o700);
  assert.equal((await fs.stat(targets.latest)).mode & 0o777, 0o600);
});

test("creates one durable audit before the pipeline starts and updates the same file", async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-live-audit-"));
  const audit = {
    request: { question: "Why DeBERTa?", state: "started" },
    stages: [],
  };
  const recorder = await beginPrivateAudit(root, audit, new Date("2026-09-04T10:00:00Z"));
  const filesAtStart = await fs.readdir(recorder.directory);
  assert.equal(filesAtStart.length, 1);
  assert.match(filesAtStart[0], /T100000000Z-[0-9a-f]{12}-[0-9a-f]{8}\.json$/);
  assert.equal(JSON.parse(await fs.readFile(recorder.history, "utf8")).request.state, "started");

  audit.stages.push({ stage: "sources_received", details: { question: "Why DeBERTa?", sources: [] } });
  audit.request.state = "failed";
  audit.final = { error: "model stopped" };
  await recorder.checkpoint(audit);

  const filesAtEnd = await fs.readdir(recorder.directory);
  assert.deepEqual(filesAtEnd, filesAtStart);
  const saved = JSON.parse(await fs.readFile(recorder.history, "utf8"));
  assert.equal(saved.request.state, "failed");
  assert.equal(saved.stages[0].stage, "sources_received");
  assert.equal(saved.final.error, "model stopped");
});
