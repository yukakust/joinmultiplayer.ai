const crypto = require("node:crypto");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const http = require("node:http");
const https = require("node:https");
const os = require("node:os");
const path = require("node:path");

const MINIMUM_MEMORY_BYTES = 12 * 1024 ** 3;

function requestClient(url) {
  return new URL(url).protocol === "http:" ? http : https;
}

async function sha256(filePath) {
  const hash = crypto.createHash("sha256");
  const stream = fs.createReadStream(filePath);
  for await (const chunk of stream) hash.update(chunk);
  return hash.digest("hex");
}

function openResponse(url, headers = {}, redirects = 0) {
  return new Promise((resolve, reject) => {
    if (redirects > 8) {
      reject(new Error("Too many download redirects."));
      return;
    }
    const request = requestClient(url).get(url, { headers }, (response) => {
      if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        response.resume();
        const redirected = new URL(response.headers.location, url).toString();
        resolve(openResponse(redirected, headers, redirects + 1));
        return;
      }
      resolve(response);
    });
    request.on("error", reject);
  });
}

async function downloadVerified({ item, destination, onProgress = () => {} }) {
  await fsp.mkdir(path.dirname(destination), { recursive: true, mode: 0o700 });
  const partial = `${destination}.part`;
  let existing = 0;
  try {
    existing = (await fsp.stat(partial)).size;
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  if (existing > item.bytes) {
    await fsp.unlink(partial);
    existing = 0;
  }

  const headers = existing ? { Range: `bytes=${existing}-` } : {};
  let response = await openResponse(item.url, headers);
  if (existing && response.statusCode === 200) {
    response.resume();
    await fsp.unlink(partial);
    existing = 0;
    response = await openResponse(item.url);
  }
  if (![200, 206].includes(response.statusCode)) {
    response.resume();
    throw new Error(`Download failed with HTTP ${response.statusCode}.`);
  }

  let received = existing;
  const output = fs.createWriteStream(partial, { flags: existing ? "a" : "w", mode: 0o600 });
  response.on("data", (chunk) => {
    received += chunk.length;
    onProgress({ received, total: item.bytes });
  });
  await new Promise((resolve, reject) => {
    response.pipe(output);
    response.on("error", reject);
    output.on("error", reject);
    output.on("finish", resolve);
  });

  const stat = await fsp.stat(partial);
  if (stat.size !== item.bytes) {
    throw new Error(`Downloaded ${stat.size} bytes; expected ${item.bytes}.`);
  }
  const actualHash = await sha256(partial);
  if (actualHash !== item.sha256) {
    await fsp.unlink(partial);
    throw new Error("The downloaded model failed its checksum.");
  }
  await fsp.rename(partial, destination);
  try { await fsp.chmod(destination, 0o600); } catch {}
  return destination;
}

class SetupManager {
  constructor({ userDataPath, manifest, runtimePath, onProgress = () => {} }) {
    this.userDataPath = userDataPath;
    this.manifest = manifest;
    this.runtimePath = runtimePath;
    this.onProgress = onProgress;
    this.active = null;
  }

  modelPath() {
    return path.join(this.userDataPath, "models", this.manifest.models.reader.file);
  }

  relevanceModelPath() {
    const model = this.manifest.models.relevance;
    return model ? path.join(this.userDataPath, "models", model.file) : null;
  }

  async installed(item, target) {
    if (!item || !target) return true;
    try {
      const stat = await fsp.stat(target);
      return stat.size === item.bytes;
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      return false;
    }
  }

  async status() {
    const model = this.manifest.models.reader;
    const installed = await this.installed(model, this.modelPath());
    const relevance = this.manifest.models.relevance;
    const relevanceInstalled = await this.installed(relevance, this.relevanceModelPath());
    const disk = await fsp.statfs(this.userDataPath);
    const freeBytes = disk.bavail * disk.bsize;
    const memoryBytes = os.totalmem();
    let runtimeInstalled = false;
    try {
      const runtimeStat = await fsp.stat(this.runtimePath);
      runtimeInstalled = runtimeStat.isFile();
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    const missingModelBytes = (installed ? 0 : model.bytes) + (relevanceInstalled ? 0 : (relevance?.bytes || 0));
    const diskOkay = freeBytes >= missingModelBytes + 2 * 1024 ** 3;
    return {
      version: "desktop-alpha-checkpoint-5a",
      model: {
        id: model.id,
        label: model.label,
        bytes: model.bytes,
        installed,
        downloading: Boolean(this.active),
      },
      relevance: relevance ? {
        id: relevance.id,
        label: relevance.label,
        bytes: relevance.bytes,
        installed: relevanceInstalled,
        downloading: Boolean(this.active),
      } : null,
      hardware: {
        memoryBytes,
        freeBytes,
        memoryOkay: memoryBytes >= MINIMUM_MEMORY_BYTES,
        diskOkay,
        requiredDownloadBytes: missingModelBytes,
      },
      runtime: { installed: runtimeInstalled, label: "llama.cpp" },
      readyToAsk: installed && relevanceInstalled && runtimeInstalled,
    };
  }

  async installModel() {
    if (this.active) return this.active;
    const current = await this.status();
    if (!current.hardware.memoryOkay) throw new Error("This preset needs at least 12 GB of memory.");
    if (!current.hardware.diskOkay) throw new Error("At least 8 GB of free disk space is required.");
    const pending = [];
    if (!current.model.installed) pending.push([this.manifest.models.reader, this.modelPath()]);
    if (current.relevance && !current.relevance.installed) {
      pending.push([this.manifest.models.relevance, this.relevanceModelPath()]);
    }
    if (!pending.length) return this.modelPath();
    this.active = (async () => {
      for (const [item, destination] of pending) {
        await downloadVerified({
          item,
          destination,
          onProgress: (progress) => this.onProgress({ ...progress, id: item.id, label: item.label }),
        });
      }
      return this.modelPath();
    })();
    try {
      return await this.active;
    } finally {
      this.active = null;
    }
  }
}

module.exports = { SetupManager, downloadVerified, sha256 };
