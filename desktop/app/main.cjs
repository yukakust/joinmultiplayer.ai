const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");

function bridgeCommand(action) {
  if (app.isPackaged) {
    const executable = process.platform === "win32" ? "pocket-i-core.exe" : "pocket-i-core";
    return {
      command: path.join(process.resourcesPath, "sidecar", executable),
      args: ["--action", action],
      options: {},
    };
  }
  const desktopRoot = path.resolve(__dirname, "..");
  return {
    command: process.env.POCKET_I_PYTHON || "python3",
    args: ["-m", "pocket_i_app.bridge", "--action", action],
    options: {
      env: { ...process.env, PYTHONPATH: desktopRoot },
    },
  };
}

function runBridge(action) {
  return new Promise((resolve, reject) => {
    const request = bridgeCommand(action);
    const child = spawn(request.command, request.args, {
      ...request.options,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error("Local library scan timed out."));
    }, 120000);
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
}

ipcMain.handle("pocket-i:health", () => runBridge("health"));
ipcMain.handle("pocket-i:scan", () => runBridge("scan"));

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

