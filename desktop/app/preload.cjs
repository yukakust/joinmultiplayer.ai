const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("pocketI", {
  health: () => ipcRenderer.invoke("pocket-i:health"),
  scan: () => ipcRenderer.invoke("pocket-i:scan"),
  memoryStatus: () => ipcRenderer.invoke("pocket-i:memory-status"),
  connectMemory: () => ipcRenderer.invoke("pocket-i:connect-memory"),
  routeMemory: (question) => ipcRenderer.invoke("pocket-i:route-memory", question),
  onMemoryProgress: (callback) => {
    const listener = (_event, progress) => callback(progress);
    ipcRenderer.on("pocket-i:memory-progress", listener);
    return () => ipcRenderer.removeListener("pocket-i:memory-progress", listener);
  },
  setupStatus: () => ipcRenderer.invoke("pocket-i:setup-status"),
  installModel: () => ipcRenderer.invoke("pocket-i:install-model"),
  ask: (question) => ipcRenderer.invoke("pocket-i:ask", question),
  onSetupProgress: (callback) => {
    const listener = (_event, progress) => callback(progress);
    ipcRenderer.on("pocket-i:setup-progress", listener);
    return () => ipcRenderer.removeListener("pocket-i:setup-progress", listener);
  },
});
