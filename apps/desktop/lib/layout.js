// Where the backend and UI live: inside the installed app (packaged) or in the repository (dev).
const { app } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const API_PORT = Number(process.env.AQE_DESKTOP_API_PORT || 18765);
const UI_PORT = Number(process.env.AQE_DESKTOP_UI_PORT || 18766);
const repoRoot = path.resolve(__dirname, "..", "..", "..");
const uiRoot = app.isPackaged ? path.join(process.resourcesPath, "ui") : path.join(__dirname, "..", "build", "ui");

function backendCommand() {
  if (app.isPackaged) {
    const exe = path.join(process.resourcesPath, "backend", process.platform === "win32" ? "atlas-backend.exe" : "atlas-backend");
    return { command: exe, args: [], cwd: path.dirname(exe), extraEnv: {} };
  }
  const venv = path.join(repoRoot, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  const python = process.env.AQE_DESKTOP_PYTHON || (fs.existsSync(venv) ? venv : process.platform === "win32" ? "python" : "python3");
  return {
    command: python,
    args: ["-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", String(API_PORT)],
    cwd: repoRoot,
    extraEnv: { PYTHONPATH: ["src", "."].map((p) => path.join(repoRoot, p)).join(path.delimiter) },
  };
}

// The standalone build puts server.js at the top, or under src/frontend when Next traced from the repository root.
function uiServer() {
  for (const rel of ["server.js", path.join("src", "frontend", "server.js")]) {
    const script = path.join(uiRoot, rel);
    if (fs.existsSync(script)) return { script, cwd: path.dirname(script) };
  }
  throw new Error(`The UI build is missing at ${uiRoot}. Run: python scripts/desktop_build.py --ui`);
}

module.exports = { API_PORT, UI_PORT, backendCommand, uiServer };
