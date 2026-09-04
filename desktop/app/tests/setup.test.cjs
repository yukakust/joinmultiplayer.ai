const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { SetupManager, downloadVerified } = require("../setup.cjs");

async function fixtureServer(content) {
  const requests = [];
  const server = http.createServer((request, response) => {
    requests.push(request.headers.range || null);
    const match = /^bytes=(\d+)-$/.exec(request.headers.range || "");
    const start = match ? Number(match[1]) : 0;
    response.writeHead(start ? 206 : 200, {
      "Content-Length": content.length - start,
      ...(start ? { "Content-Range": `bytes ${start}-${content.length - 1}/${content.length}` } : {}),
    });
    response.end(content.subarray(start));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    requests,
    url: `http://127.0.0.1:${server.address().port}/model.gguf`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

test("downloads and verifies a model before atomic promotion", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-setup-"));
  const content = Buffer.from("a tiny model fixture");
  const server = await fixtureServer(content);
  const destination = path.join(directory, "model.gguf");
  const progress = [];
  try {
    await downloadVerified({
      item: {
        url: server.url,
        bytes: content.length,
        sha256: crypto.createHash("sha256").update(content).digest("hex"),
      },
      destination,
      onProgress: (item) => progress.push(item),
    });
    assert.deepEqual(await fs.readFile(destination), content);
    assert.equal(progress.at(-1).received, content.length);
    await assert.rejects(fs.stat(`${destination}.part`), { code: "ENOENT" });
  } finally {
    await server.close();
  }
});

test("continues an interrupted partial download", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-resume-"));
  const content = Buffer.from("resume-this-download");
  const server = await fixtureServer(content);
  const destination = path.join(directory, "model.gguf");
  await fs.writeFile(`${destination}.part`, content.subarray(0, 7));
  try {
    await downloadVerified({
      item: {
        url: server.url,
        bytes: content.length,
        sha256: crypto.createHash("sha256").update(content).digest("hex"),
      },
      destination,
    });
    assert.equal(server.requests[0], "bytes=7-");
    assert.deepEqual(await fs.readFile(destination), content);
  } finally {
    await server.close();
  }
});

test("rejects and removes a model with a wrong checksum", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-hash-"));
  const content = Buffer.from("corrupt fixture");
  const server = await fixtureServer(content);
  const destination = path.join(directory, "model.gguf");
  try {
    await assert.rejects(
      downloadVerified({
        item: { url: server.url, bytes: content.length, sha256: "0".repeat(64) },
        destination,
      }),
      /checksum/,
    );
    await assert.rejects(fs.stat(destination), { code: "ENOENT" });
    await assert.rejects(fs.stat(`${destination}.part`), { code: "ENOENT" });
  } finally {
    await server.close();
  }
});

test("becomes ready to ask only when model and runtime both exist", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-ready-"));
  const runtime = path.join(directory, "runtime", "llama-cli");
  const setup = new SetupManager({
    userDataPath: directory,
    runtimePath: runtime,
    manifest: { models: { reader: { file: "model.gguf", bytes: 4 } } },
  });
  assert.equal((await setup.status()).readyToAsk, false);
  await fs.mkdir(path.dirname(setup.modelPath()), { recursive: true });
  await fs.writeFile(setup.modelPath(), "1234");
  assert.equal((await setup.status()).readyToAsk, false);
  await fs.mkdir(path.dirname(runtime), { recursive: true });
  await fs.writeFile(runtime, "runtime");
  assert.equal((await setup.status()).readyToAsk, true);
});

test("a configured relevance model is required before the accepted pipeline is ready", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-relevance-ready-"));
  const runtime = path.join(directory, "runtime", "llama-cli");
  const setup = new SetupManager({
    userDataPath: directory,
    runtimePath: runtime,
    manifest: { models: {
      reader: { file: "reader.gguf", bytes: 4 },
      relevance: { file: "reranker.gguf", bytes: 3 },
    } },
  });
  await fs.mkdir(path.dirname(setup.modelPath()), { recursive: true });
  await fs.writeFile(setup.modelPath(), "1234");
  await fs.mkdir(path.dirname(runtime), { recursive: true });
  await fs.writeFile(runtime, "runtime");
  assert.equal((await setup.status()).readyToAsk, false);
  await fs.writeFile(setup.relevanceModelPath(), "123");
  assert.equal((await setup.status()).readyToAsk, true);
});

test("remote mode needs no local model files when both yukabox services are healthy", async () => {
  const servers = [];
  async function healthServer() {
    const server = http.createServer((_request, response) => {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end('{"status":"ok"}');
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    servers.push(server);
    return `http://127.0.0.1:${server.address().port}`;
  }
  const readerUrl = await healthServer();
  const relevanceUrl = await healthServer();
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-remote-ready-"));
  try {
    const setup = new SetupManager({
      userDataPath: directory,
      runtimePath: path.join(directory, "missing-runtime"),
      manifest: {
        remoteBrain: { enabled: true, readerUrl, relevanceUrl },
        models: { reader: { id: "reader", label: "Reader" }, relevance: { id: "reranker", label: "Reranker" } },
      },
    });
    const status = await setup.status();
    assert.equal(status.mode, "remote");
    assert.equal(status.readyToAsk, true);
    assert.equal(status.hardware.requiredDownloadBytes, 0);
  } finally {
    await Promise.all(servers.map((server) => new Promise((resolve) => server.close(resolve))));
  }
});
