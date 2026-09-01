const { spawn } = require("node:child_process");

class MemoryService {
  constructor({ request, spawnProcess = spawn, onProgress = () => {} }) {
    this.request = request;
    this.spawnProcess = spawnProcess;
    this.child = null;
    this.buffer = "";
    this.nextId = 1;
    this.pending = new Map();
    this.onProgress = onProgress;
  }

  start() {
    if (this.child) return;
    this.child = this.spawnProcess(this.request.command, this.request.args, {
      ...this.request.options,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.child.stdout.on("data", (chunk) => this.consume(chunk.toString()));
    // Drain local model progress without forwarding paths or private diagnostics.
    this.child.stderr.on("data", () => {});
    this.child.on("error", (error) => this.stop(error));
    this.child.on("close", () => this.stop(new Error("Local memory stopped.")));
  }

  consume(chunk) {
    this.buffer += chunk;
    while (this.buffer.includes("\n")) {
      const boundary = this.buffer.indexOf("\n");
      const line = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 1);
      if (!line) continue;
      let response;
      try { response = JSON.parse(line); } catch { continue; }
      if (response.event === "progress") {
        this.onProgress(response.payload || {});
        continue;
      }
      const waiting = this.pending.get(response.id);
      if (!waiting) continue;
      this.pending.delete(response.id);
      clearTimeout(waiting.timer);
      if (response.ok) waiting.resolve(response.result);
      else waiting.reject(new Error(response.error || "Local memory failed."));
    }
  }

  call(action, payload = {}, timeoutMs = 120000) {
    this.start();
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = timeoutMs === null ? null : setTimeout(() => {
          this.pending.delete(id);
          reject(new Error("Local memory timed out."));
        }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(`${JSON.stringify({ id, action, payload })}\n`, (error) => {
        if (!error) return;
        clearTimeout(timer);
        this.pending.delete(id);
        reject(error);
      });
    });
  }

  stop(error = new Error("Local memory stopped.")) {
    const child = this.child;
    this.child = null;
    for (const waiting of this.pending.values()) {
      clearTimeout(waiting.timer);
      waiting.reject(error);
    }
    this.pending.clear();
    if (child && !child.killed) child.kill();
  }
}

module.exports = { MemoryService };
