const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("pocketI", {
  health: () => ipcRenderer.invoke("pocket-i:health"),
  scan: () => ipcRenderer.invoke("pocket-i:scan"),
});

