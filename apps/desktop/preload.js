// Exposes one call to the setup page. No Node access reaches the page.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("setup", {
  submit: (username, password) => ipcRenderer.invoke("setup:submit", { username, password }),
});
