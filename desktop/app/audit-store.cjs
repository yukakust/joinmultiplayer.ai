const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");

function privateAuditPaths(userDataPath) {
  const memoryDirectory = path.join(userDataPath, "memory");
  return {
    directory: path.join(memoryDirectory, "answer-test-logs"),
    latest: path.join(memoryDirectory, "last-answer-test-log.json"),
  };
}

function auditFileName(now, audit) {
  const stamp = now.toISOString().replace(/[-:.]/g, "");
  const question = audit?.request?.question
    || audit?.stages?.find((item) => item?.stage === "sources_received")?.details?.question
    || "unknown";
  const digest = crypto.createHash("sha256").update(String(question)).digest("hex").slice(0, 12);
  const nonce = crypto.randomBytes(4).toString("hex");
  return `${stamp}-${digest}-${nonce}.json`;
}

async function atomicPrivateWrite(target, contents) {
  const temporary = `${target}.tmp-${process.pid}-${crypto.randomBytes(4).toString("hex")}`;
  await fs.writeFile(temporary, contents, { mode: 0o600, flag: "wx" });
  await fs.rename(temporary, target);
  await fs.chmod(target, 0o600);
}

async function recordPrivateAudit(userDataPath, audit, now = new Date()) {
  const targets = privateAuditPaths(userDataPath);
  await fs.mkdir(targets.directory, { recursive: true, mode: 0o700 });
  await fs.chmod(targets.directory, 0o700);
  const contents = `${JSON.stringify({ ...audit, recorded_at: now.toISOString() }, null, 2)}\n`;
  const history = path.join(targets.directory, auditFileName(now, audit));
  await atomicPrivateWrite(history, contents);
  await atomicPrivateWrite(targets.latest, contents);
  return { directory: targets.directory, history, latest: targets.latest };
}

async function beginPrivateAudit(userDataPath, audit, now = new Date()) {
  const targets = privateAuditPaths(userDataPath);
  await fs.mkdir(targets.directory, { recursive: true, mode: 0o700 });
  await fs.chmod(targets.directory, 0o700);
  const history = path.join(targets.directory, auditFileName(now, audit));

  async function checkpoint(nextAudit) {
    const contents = `${JSON.stringify({ ...nextAudit, recorded_at: new Date().toISOString() }, null, 2)}\n`;
    await atomicPrivateWrite(history, contents);
    await atomicPrivateWrite(targets.latest, contents);
    return { directory: targets.directory, history, latest: targets.latest };
  }

  await checkpoint(audit);
  return { directory: targets.directory, history, latest: targets.latest, checkpoint };
}

module.exports = { beginPrivateAudit, privateAuditPaths, recordPrivateAudit };
