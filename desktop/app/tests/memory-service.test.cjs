const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const test = require("node:test");

const { MemoryService } = require("../memory-service.cjs");

function fakeProcess() {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.stdin = {
    write(line, callback) {
      const request = JSON.parse(line);
      setImmediate(() => child.stdout.emit("data", `${JSON.stringify({
        id: request.id,
        ok: true,
        result: { action: request.action, payload: request.payload },
      })}\n`));
      callback();
    },
  };
  child.killed = false;
  child.kill = () => { child.killed = true; };
  return child;
}

test("reuses one private process for multiple memory requests", async () => {
  let starts = 0;
  const child = fakeProcess();
  const service = new MemoryService({
    request: { command: "fixture", args: [], options: {} },
    spawnProcess: () => { starts += 1; return child; },
  });
  assert.deepEqual(await service.call("connect"), { action: "connect", payload: {} });
  assert.deepEqual(await service.call("route", { question: "Where?" }), {
    action: "route", payload: { question: "Where?" },
  });
  assert.equal(starts, 1);
  service.stop();
});

test("rejects a failed private response without leaking details", async () => {
  const child = fakeProcess();
  child.stdin.write = (line, callback) => {
    const request = JSON.parse(line);
    setImmediate(() => child.stdout.emit("data", `${JSON.stringify({
      id: request.id, ok: false, error: "Local memory failed.",
    })}\n`));
    callback();
  };
  const service = new MemoryService({
    request: { command: "fixture", args: [], options: {} },
    spawnProcess: () => child,
  });
  await assert.rejects(service.call("route"), /Local memory failed/);
  service.stop();
});
