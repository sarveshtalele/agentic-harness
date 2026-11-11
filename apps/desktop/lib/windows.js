// Windows: the first-run setup form and the main app window, both locked down.
const { BrowserWindow, ipcMain, shell } = require("electron");
const path = require("node:path");

const secure = (preload) => ({ contextIsolation: true, nodeIntegration: false, sandbox: true, ...(preload ? { preload } : {}) });

function openExternal(url) {
  if (/^https?:\/\//i.test(url)) shell.openExternal(url);
}

function lockNavigation(win, origin) {
  win.webContents.setWindowOpenHandler(({ url }) => { openExternal(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (event, url) => {
    if (new URL(url).origin === origin) return;
    event.preventDefault();
    openExternal(url);
  });
}

// Resolves with the admin credentials once the form passes validation, or null if the window is closed.
function askAdmin(validate) {
  return new Promise((resolve) => {
    const win = new BrowserWindow({ width: 460, height: 420, resizable: false, title: "Agentic QE Platform setup", webPreferences: secure(path.join(__dirname, "..", "preload.js")) });
    win.removeMenu();
    lockNavigation(win, "file://");
    let done = false;
    ipcMain.removeHandler("setup:submit");
    ipcMain.handle("setup:submit", (_event, creds) => {
      const error = validate(creds || {});
      if (error) return { error };
      done = true;
      resolve(creds);
      win.close();
      return {};
    });
    win.on("closed", () => { ipcMain.removeHandler("setup:submit"); if (!done) resolve(null); });
    win.loadFile(path.join(__dirname, "..", "setup.html"));
  });
}

function openMain(url) {
  const win = new BrowserWindow({ width: 1440, height: 900, title: "Agentic QE Platform", webPreferences: secure() });
  lockNavigation(win, new URL(url).origin);
  win.loadURL(url);
  return win;
}

module.exports = { askAdmin, openMain };
