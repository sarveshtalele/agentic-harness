// The main window's only bridge: the Terminal pane (lib/terminal.js). No other Node access reaches the page.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("aqeTerminal", {
  open: (threadId, cols, rows) => ipcRenderer.invoke("terminal:open", { threadId, cols, rows }),
  write: (id, data) => ipcRenderer.send("terminal:write", { id, data }),
  resize: (id, cols, rows) => ipcRenderer.send("terminal:resize", { id, cols, rows }),
  close: (id) => ipcRenderer.send("terminal:close", { id }),
  onData: (callback) => {
    const listener = (_event, message) => callback(message.id, message.data);
    ipcRenderer.on("terminal:data", listener);
    return () => ipcRenderer.removeListener("terminal:data", listener);
  },
  onExit: (callback) => {
    const listener = (_event, message) => callback(message.id, message.exitCode);
    ipcRenderer.on("terminal:exit", listener);
    return () => ipcRenderer.removeListener("terminal:exit", listener);
  },
});
