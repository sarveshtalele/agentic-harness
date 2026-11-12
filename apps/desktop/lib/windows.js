// Windows: the sign-in form and the main app window, both locked down.
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

// Resolves with what `attempt(form)` returns once it has no error (the sign-in), or null if the window is closed.
function askSignIn(attempt, server) {
  return new Promise((resolve) => {
    const win = new BrowserWindow({ width: 480, height: 470, resizable: false, title: "Agentic QE Platform sign-in", webPreferences: secure(path.join(__dirname, "..", "preload.js")) });
    win.removeMenu();
    lockNavigation(win, "file://");
    let done = false;
    ipcMain.removeHandler("setup:submit");
    ipcMain.handle("setup:submit", async (_event, form) => {
      let result;
      try {
        result = await attempt(form || {});
      } catch (error) {
        result = { error: String(error.message || error) };
      }
      if (result.error) return { error: result.error };
      done = true;
      resolve(result);
      win.close();
      return {};
    });
    win.on("closed", () => { ipcMain.removeHandler("setup:submit"); if (!done) resolve(null); });
    win.loadFile(path.join(__dirname, "..", "setup.html"), { query: server ? { server } : {} });
  });
}

function openMain(url) {
  const win = new BrowserWindow({ width: 1440, height: 900, title: "Agentic QE Platform", webPreferences: secure(path.join(__dirname, "..", "preload-main.js")) });
  lockNavigation(win, new URL(url).origin);
  win.loadURL(url);
  return win;
}

module.exports = { askSignIn, openMain };
