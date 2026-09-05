const { app, BrowserWindow, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const manifest = require("./model-manifest.json");
const { SetupManager } = require("./setup.cjs");
const { ChatManager } = require("./chat.cjs");
const { MemoryService } = require("./memory-service.cjs");
const { RerankerManager } = require("./reranker.cjs");
const { beginPrivateAudit, privateAuditPaths } = require("./audit-store.cjs");

function loadRemoteAccessToken() {
  const fromEnvironment = String(process.env.POCKET_I_REMOTE_ACCESS_TOKEN || "").trim();
  if (fromEnvironment) return fromEnvironment;
  try {
    const access = require("./remote-access.json");
    return typeof access?.token === "string" ? access.token.trim() : "";
  } catch {
    return "";
  }
}

const remoteAccessToken = loadRemoteAccessToken();

let mainWindow = null;
let setupManager = null;
let chatManager = null;
let memoryService = null;
let rerankerManager = null;

async function configureRemoteBrain(enabled) {
  if (!setupManager || !manifest.remoteBrain?.enabled) return false;
  await setupManager.setBrainMode(enabled ? "remote" : "local");
  await setupManager.setRemoteConsent(Boolean(enabled));
  const remote = enabled ? manifest.remoteBrain : null;
  chatManager.remoteUrl = remote?.readerUrl || null;
  chatManager.remoteAccessToken = remote ? remoteAccessToken : null;
  rerankerManager.remoteUrl = remote?.relevanceUrl || null;
  rerankerManager.remoteAccessToken = remote ? remoteAccessToken : null;
  if (!enabled) rerankerManager.stop();
  return Boolean(enabled);
}

async function requireRemoteConsent() {
  if (manifest.remoteBrain?.enabled && !(await setupManager.remoteConsent())) {
    throw new Error("Yuka's server is off. Turn it on before sending selected memory excerpts.");
  }
}

function runtimePath() {
  const executable = process.platform === "win32" ? "llama-cli.exe" : "llama-cli";
  const root = app.isPackaged ? path.join(process.resourcesPath, "runtime") : path.join(__dirname, "runtime-current");
  return path.join(root, executable);
}

function rerankerRuntimePath() {
  const executable = process.platform === "win32" ? "llama-server.exe" : "llama-server";
  const root = app.isPackaged ? path.join(process.resourcesPath, "runtime") : path.join(__dirname, "runtime-current");
  return path.join(root, executable);
}

function bridgeCommand(action) {
  const nliRoot = app.isPackaged ? path.join(process.resourcesPath, "nli") : path.join(__dirname, "nli-current");
  const dataArgs = [
    "--data-dir", path.join(app.getPath("userData"), "memory"),
    "--nli-dir", nliRoot,
  ];
  if (app.isPackaged) {
    const executable = process.platform === "win32" ? "pocket-i-core.exe" : "pocket-i-core";
    return {
      command: path.join(process.resourcesPath, "sidecar", executable),
      args: ["--action", action, ...dataArgs],
      options: {},
    };
  }
  const desktopRoot = path.resolve(__dirname, "..");
  return {
    command: process.env.POCKET_I_PYTHON || "python3",
    args: ["-m", "pocket_i_app.bridge", "--action", action, ...dataArgs],
    options: {
      env: { ...process.env, PYTHONPATH: desktopRoot },
    },
  };
}

function memoryServiceCommand() {
  return bridgeCommand("serve");
}

function runBridge(action, timeoutMs = 120000, payload = null) {
  return new Promise((resolve, reject) => {
    const request = bridgeCommand(action);
    const child = spawn(request.command, request.args, {
      ...request.options,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error("Local library scan timed out."));
    }, timeoutMs);
    child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        reject(new Error(stderr.trim() || "Local core failed."));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch {
        reject(new Error("Local core returned an invalid response."));
      }
    });
    child.stdin.end(payload === null ? "" : JSON.stringify(payload));
  });
}

async function recordAnswerDiagnostic(result) {
  const directory = path.join(app.getPath("userData"), "memory");
  const target = path.join(directory, "last-answer-diagnostic.json");
  const temporary = `${target}.tmp`;
  const payload = {
    schema_version: "pocket-i-answer-diagnostic-v0.1",
    stage: typeof result?.diagnostic === "string" ? result.diagnostic : "unknown",
  };
  try {
    await fs.mkdir(directory, { recursive: true, mode: 0o700 });
    await fs.writeFile(temporary, `${JSON.stringify(payload, null, 2)}\n`, { mode: 0o600 });
    await fs.rename(temporary, target);
  } catch {
    // Diagnostics must never block or weaken the owner's answer path.
  }
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1240,
    height: 820,
    minWidth: 820,
    minHeight: 620,
    backgroundColor: "#10100f",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.removeMenu();
  window.loadFile(path.join(__dirname, "renderer", "index.html"));
  window.once("ready-to-show", () => window.show());
  mainWindow = window;
}

ipcMain.handle("pocket-i:health", () => runBridge("health"));
ipcMain.handle("pocket-i:scan", () => memoryService.call("scan"));
ipcMain.handle("pocket-i:memory-status", () => memoryService.call("memory-status"));
ipcMain.handle("pocket-i:connect-memory", () => memoryService.call("connect", {}, null));
ipcMain.handle("pocket-i:route-memory", (_event, question) =>
  memoryService.call("route", { question }, 600000),
);
ipcMain.handle("pocket-i:answer-memory", async (_event, question) => {
  await requireRemoteConsent();
  const cleanQuestion = typeof question === "string" ? question.trim() : "";
  const audit = {
    schema_version: "pocket-i-private-answer-test-log-v0.1",
    warning: "PRIVATE: contains the owner's question, local memory excerpts and model output. Never upload this file.",
    stage_guide: {
      sources_received: "The exact local excerpts given to Qwen.",
      pre_reranker_sources: "The exact local whole conversations or complete turns about to be sent to the remote reranker. This stage is private and makes remote failures inspectable.",
      remote_reranker_finished: "The remote reranker returned a decision for every sent item.",
      whole_turn_relevance: "Qwen3-Reranker-4B sees the unchanged question and each whole conversation or complete turn before Qwen reads it. DROP is removed; TAKE and NOT_SURE continue.",
      qwen_extraction: "The raw claims and evidence IDs returned by Qwen.",
      evidence_id_check: "Ordinary code resolves Qwen's selected IDs back to exact source text.",
      grounding_signals: "DeBERTa checks one atomic claim against its exact quote plus bounded neighbouring text from the same source. The user's question stays outside this check.",
      grounded_evidence: "Only source-grounded claims continue.",
      question_relevance: "Qwen checks whether each grounded claim answers the owner's question, contributes one needed part, or is unrelated. Truth and source support are not judged here.",
      primary_piles: "Bidirectional DeBERTa groups mutually entailing claims without deleting alternatives.",
      qwen_canonicals: "Qwen rewrites each pile into one readable claim.",
      canonical_validation: "Bidirectional DeBERTa checks every rewrite against every original claim.",
      final_piles: "Validated claims are compared again; supported alternatives stay separate.",
      writer_evidence: "The complete evidence bundle given to the final Qwen writer.",
      qwen_writer: "The raw final text returned by Qwen.",
      stopped: "The exact stage and reason where the harness stopped.",
      completed: "The strict answer path completed.",
    },
    request: {
      question: cleanQuestion,
      state: "started",
      started_at: new Date().toISOString(),
    },
    stages: [],
  };
  let recorder;
  try {
    recorder = await beginPrivateAudit(app.getPath("userData"), audit);
  } catch {
    throw new Error("Pocket i could not start the private test log, so the test was not run.");
  }
  const recordStage = async (stage, details) => {
    audit.stages.push({ stage, details });
    await recorder.checkpoint(audit);
  };
  try {
    const context = await memoryService.call("context", { question }, 600000);
    await recordStage("pre_reranker_sources", {
      transport: manifest.remoteBrain?.transport || "local",
      items: context.items,
    });
    const relevance = await rerankerManager.filter(question, context.items);
    await recordStage("remote_reranker_finished", { item_count: relevance.rows.length });
    await recordStage("whole_turn_relevance", {
      items: relevance.rows.map((item) => ({
        source_id: item.source_id,
        score: Number(item.score.toFixed(8)),
        decision: item.decision,
      })),
    });
    const result = await chatManager.answerFromVerifiedMemory(
      question,
      relevance.selected,
      async (candidates) => {
        const items = [];
        for (let index = 0; index < candidates.length; index += 10) {
          const judged = await memoryService.call("nli", { candidates: candidates.slice(index, index + 10) }, 600000);
          items.push(...judged.items);
        }
        return items;
      },
      recordStage,
    );
    audit.final = { answer: result.answer, diagnostic: result.diagnostic };
    audit.request.state = "completed";
    audit.request.finished_at = new Date().toISOString();
    await recordAnswerDiagnostic(result);
    await recorder.checkpoint(audit);
    return { ...result, test_log_ready: true };
  } catch (error) {
    audit.final = { error: error instanceof Error ? error.message : "Unknown local error" };
    audit.request.state = "failed";
    audit.request.finished_at = new Date().toISOString();
    try {
      await recorder.checkpoint(audit);
    } catch {
      // Preserve the original pipeline error if the final audit checkpoint also fails.
    }
    throw error;
  }
});
ipcMain.handle("pocket-i:open-test-log", async () => {
  const target = privateAuditPaths(app.getPath("userData")).directory;
  try {
    await fs.access(target);
  } catch {
    throw new Error("Run one memory question first.");
  }
  const error = await shell.openPath(target);
  if (error) throw new Error("The private test log folder could not be opened.");
  return { opened: true };
});
ipcMain.handle("pocket-i:setup-status", () => setupManager.status());
ipcMain.handle("pocket-i:set-remote-brain", async (_event, enabled) => {
  await configureRemoteBrain(enabled);
  return setupManager.status();
});
ipcMain.handle("pocket-i:install-model", async () => {
  await setupManager.installModel();
  return setupManager.status();
});
ipcMain.handle("pocket-i:ask", async (_event, question) => {
  await requireRemoteConsent();
  const status = await setupManager.status();
  if (!status.readyToAsk) throw new Error("Finish setup before asking a question.");
  return chatManager.ask(question);
});

app.whenReady().then(async () => {
  setupManager = new SetupManager({
    userDataPath: app.getPath("userData"),
    manifest,
    runtimePath: runtimePath(),
    remoteAccessToken,
    onProgress: (progress) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("pocket-i:setup-progress", progress);
      }
    },
  });
  const remoteConsented = await setupManager.remoteConsent();
  chatManager = new ChatManager({
    executable: runtimePath(),
    modelPath: setupManager.modelPath(),
    remoteUrl: remoteConsented ? manifest.remoteBrain.readerUrl : null,
    remoteAccessToken: remoteConsented ? remoteAccessToken : null,
    brainLabel: manifest.models.reader.label,
  });
  rerankerManager = new RerankerManager({
    executable: rerankerRuntimePath(),
    modelPath: setupManager.relevanceModelPath(),
    remoteUrl: remoteConsented ? manifest.remoteBrain.relevanceUrl : null,
    remoteAccessToken: remoteConsented ? remoteAccessToken : null,
  });
  memoryService = new MemoryService({
    request: memoryServiceCommand(),
    onProgress: (progress) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("pocket-i:memory-progress", progress);
      }
    },
  });
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("before-quit", () => {
  if (memoryService) memoryService.stop();
  if (rerankerManager) rerankerManager.stop();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
