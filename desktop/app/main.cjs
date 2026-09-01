const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");
const manifest = require("./model-manifest.json");
const { SetupManager } = require("./setup.cjs");
const { ChatManager } = require("./chat.cjs");
const { MemoryService } = require("./memory-service.cjs");

let mainWindow = null;
let setupManager = null;
let chatManager = null;
let memoryService = null;

function runtimePath() {
  const executable = process.platform === "win32" ? "llama-cli.exe" : "llama-cli";
  const root = app.isPackaged ? path.join(process.resourcesPath, "runtime") : path.join(__dirname, "runtime-current");
  return path.join(root, executable);
}

function bridgeCommand(action) {
  const dataArgs = ["--data-dir", path.join(app.getPath("userData"), "memory")];
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
  const context = await memoryService.call("context", { question }, 600000);
  return chatManager.answerFromMemory(question, context.items);
});
ipcMain.handle("pocket-i:setup-status", () => setupManager.status());
ipcMain.handle("pocket-i:install-model", async () => {
  await setupManager.installModel();
  return setupManager.status();
});
ipcMain.handle("pocket-i:ask", async (_event, question) => {
  const status = await setupManager.status();
  if (!status.readyToAsk) throw new Error("Finish setup before asking a question.");
  return chatManager.ask(question);
});

app.whenReady().then(() => {
  setupManager = new SetupManager({
    userDataPath: app.getPath("userData"),
    manifest,
    runtimePath: runtimePath(),
    onProgress: (progress) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("pocket-i:setup-progress", progress);
      }
    },
  });
  chatManager = new ChatManager({
    executable: runtimePath(),
    modelPath: setupManager.modelPath(),
    brainLabel: manifest.models.reader.label,
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
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
