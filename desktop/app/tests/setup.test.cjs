const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { downloadVerified } = require("../setup.cjs");

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

