// The desktop Terminal pane (docs/PHASE2_PLAN.md 11.2): real PTYs (node-pty; ConPTY on Windows) where the person runs
// their own commands. The page names only a chat; the folder comes from the local backend, so a page cannot pick one.
const { ipcMain } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const terminals = new Map(); // id -> { pty, owner }
let next = 1;

function shell() {
  if (process.platform === "win32") {
    for (const dir of (process.env.PATH || "").split(path.delimiter)) {
      for (const exe of ["pwsh.exe", "powershell.exe"]) if (fs.existsSync(path.join(dir, exe))) return { file: path.join(dir, exe), args: ["-NoLogo"] };
    }
    return { file: process.env.ComSpec || "cmd.exe", args: [] };
  }
  return { file: process.env.SHELL || (fs.existsSync("/bin/zsh") ? "/bin/zsh" : "/bin/bash"), args: ["-l"] };
}

async function folderOf(apiOrigin, cookie, threadId) {
  const response = await fetch(`${apiOrigin}/api/chats/${encodeURIComponent(threadId)}/terminal`, { headers: { cookie }, signal: AbortSignal.timeout(15000) });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || body.detail || `HTTP ${response.status}`);
  if (!body.cwd) throw new Error("This project has no workspace yet. Connect a repository first.");
  return body.cwd;
}

// `cookie()` gives the window's session cookie for the local backend.
function register(apiOrigin, cookie) {
  const pty = require("node-pty");
  ipcMain.handle("terminal:open", async (event, { threadId, cols, rows }) => {
    try {
      const cwd = await folderOf(apiOrigin, await cookie(), String(threadId || ""));
      const { file, args } = shell();
      const term = pty.spawn(file, args, { name: "xterm-256color", cols: cols || 100, rows: rows || 24, cwd, env: { ...process.env, AQH_PROJECT_DIR: cwd } });
      const id = next++;
      terminals.set(id, { pty: term, owner: event.sender });
      term.onData((data) => { if (!event.sender.isDestroyed()) event.sender.send("terminal:data", { id, data }); });
      term.onExit(({ exitCode }) => {
        terminals.delete(id);
        if (!event.sender.isDestroyed()) event.sender.send("terminal:exit", { id, exitCode });
      });
      return { id, cwd, shell: path.basename(file) };
    } catch (error) {
      return { error: String(error.message || error) };
    }
  });
  const mine = (event, id) => { const t = terminals.get(id); return t && t.owner === event.sender ? t.pty : null; };
  ipcMain.on("terminal:write", (event, { id, data }) => mine(event, id)?.write(String(data)));
  ipcMain.on("terminal:resize", (event, { id, cols, rows }) => { if (cols > 0 && rows > 0) mine(event, id)?.resize(cols, rows); });
  ipcMain.on("terminal:close", (event, { id }) => mine(event, id)?.kill());
}

function closeAll() {
  for (const { pty } of terminals.values()) {
    try { pty.kill(); } catch { /* already ended */ }
  }
  terminals.clear();
}

module.exports = { register, closeAll };
