const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { privateAuditPaths, recordPrivateAudit } = require("../audit-store.cjs");

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
