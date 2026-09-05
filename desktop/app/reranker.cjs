const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { requestJson: requestRemoteJson } = require("./remote-inference.cjs");

const TAKE_AT = 0.92222771;
// Gate 7S.14: the frozen 30-question development sweep retained 58/58 useful
// fragments at this conservative cutoff while rejecting Helios-like weak hits.
const DROP_AT = 0.05;
const INSTRUCTION = "Given a peer question, decide whether this local conversation contains information that directly helps answer it.";
const PREFIX = '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n';
const SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";

function decisionForScore(score) {
  return score >= TAKE_AT ? "TAKE" : score < DROP_AT ? "DROP" : "NOT_SURE";
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close((error) => error ? reject(error) : resolve(port));
    });
  });
}

function requestJson({ port, method = "GET", route, payload = null, timeoutMs = 600000 }) {
  return new Promise((resolve, reject) => {
    const body = payload === null ? null : Buffer.from(JSON.stringify(payload));
    const request = http.request({
      hostname: "127.0.0.1",
      port,
      path: route,
      method,
      timeout: timeoutMs,
      headers: body ? { "Content-Type": "application/json", "Content-Length": body.length } : {},
    }, (response) => {
      let value = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => { value += chunk; });
      response.on("end", () => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error("The local relevance model failed."));
          return;
        }
        try { resolve(JSON.parse(value)); } catch { reject(new Error("The local relevance model returned invalid data.")); }
      });
    });
    request.on("timeout", () => request.destroy(new Error("The local relevance model timed out.")));
    request.on("error", reject);
    if (body) request.write(body);
    request.end();
  });
}

class RerankerManager {
  constructor({ executable, modelPath, remoteUrl = null, remoteAccessToken = null, timeoutMs = 180000 }) {
    this.executable = executable;
    this.modelPath = modelPath;
    this.remoteUrl = remoteUrl;
    this.remoteAccessToken = remoteAccessToken;
    this.timeoutMs = timeoutMs;
    this.child = null;
    this.port = null;
    this.starting = null;
  }

  async start() {
    if (this.child && this.port) return;
    if (this.starting) return this.starting;
    this.starting = this._start();
    try { await this.starting; } finally { this.starting = null; }
  }

  async _start() {
    this.port = await freePort();
    const runtimeDirectory = path.dirname(this.executable);
    const env = {
      ...process.env,
      LD_LIBRARY_PATH: [runtimeDirectory, process.env.LD_LIBRARY_PATH].filter(Boolean).join(path.delimiter),
      DYLD_LIBRARY_PATH: [runtimeDirectory, process.env.DYLD_LIBRARY_PATH].filter(Boolean).join(path.delimiter),
    };
    const child = spawn(this.executable, [
      "-m", this.modelPath,
      "--host", "127.0.0.1",
      "--port", String(this.port),
      "--reranking",
      "-c", "32768",
      "-b", "512",
      "-ub", "512",
      "-np", "1",
      "--log-disable",
    ], { env, windowsHide: true, stdio: ["ignore", "ignore", "ignore"] });
    this.child = child;
    let closed = null;
    child.once("error", (error) => { closed = error; });
    child.once("close", () => { closed = closed || new Error("The local relevance model stopped."); });
    const deadline = Date.now() + this.timeoutMs;
    while (Date.now() < deadline) {
      if (closed) throw closed;
      try {
        await requestJson({ port: this.port, route: "/health", timeoutMs: 1000 });
        return;
      } catch {}
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    this.stop();
    throw new Error("The local relevance model took too long to start.");
  }

  async score(question, document) {
    if (!this.remoteUrl) await this.start();
    const content = `${PREFIX}<Instruct>: ${INSTRUCTION}\n<Query>: ${question}\n<Document>: ${document}${SUFFIX}`;
    const payload = this.remoteUrl
      ? await requestRemoteJson(this.remoteUrl, "/embedding", {
        method: "POST",
        timeoutMs: this.timeoutMs,
        accessToken: this.remoteAccessToken,
        payload: { content, embd_normalize: -1 },
      })
      : await requestJson({
        port: this.port,
        method: "POST",
        route: "/embedding",
        payload: { content, embd_normalize: -1 },
      });
    let values = payload?.[0]?.embedding;
    if (Array.isArray(values?.[0])) values = values[0];
    if (!Array.isArray(values) || values.length < 2) throw new Error("The local relevance score was invalid.");
    const yes = Number(values[0]);
    const no = Number(values[1]);
    const score = yes / (yes + no);
    if (!Number.isFinite(score)) throw new Error("The local relevance score was invalid.");
    return {
      score,
      decision: decisionForScore(score),
    };
  }

  async filter(question, sources) {
    const rows = [];
    for (const source of sources) {
      const result = await this.score(question, source.text);
      rows.push({ source_id: source.source_id, ...result });
    }
    const byId = new Map(rows.map((row) => [row.source_id, row.decision]));
    return { rows, selected: sources.filter((source) => byId.get(source.source_id) !== "DROP") };
  }

  stop() {
    if (this.child && !this.child.killed) this.child.kill();
    this.child = null;
    this.port = null;
  }
}

module.exports = { DROP_AT, INSTRUCTION, RerankerManager, TAKE_AT, decisionForScore, requestJson };
