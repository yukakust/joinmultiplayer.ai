const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("pocketI", {
  health: () => ipcRenderer.invoke("pocket-i:health"),
  scan: () => ipcRenderer.invoke("pocket-i:scan"),
  setupStatus: () => ipcRenderer.invoke("pocket-i:setup-status"),
  installModel: () => ipcRenderer.invoke("pocket-i:install-model"),
  ask: (question) => ipcRenderer.invoke("pocket-i:ask", question),
  onSetupProgress: (callback) => {
    const listener = (_event, progress) => callback(progress);
    ipcRenderer.on("pocket-i:setup-progress", listener);
    return () => ipcRenderer.removeListener("pocket-i:setup-progress", listener);
  },
});
