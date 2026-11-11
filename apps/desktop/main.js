// Electron main: starts the local backend and UI on loopback, then opens the app. Both stop when the app quits.
const { app, dialog } = require("electron");
const path = require("node:path");
const layout = require("./lib/layout");
const procs = require("./lib/procs");
const secrets = require("./lib/secrets");
const windows = require("./lib/windows");

if (process.env.AQE_DESKTOP_USER_DATA) app.setPath("userData", process.env.AQE_DESKTOP_USER_DATA); // tests use a temporary folder

const children = [];
let mainOpened = false; // the setup window closing must not quit the app before the main window exists
const WAIT_MS = Number(process.env.AQE_DESKTOP_START_TIMEOUT_MS || 120000);

async function credentials(userData) {
  const saved = secrets.loadAdmin(userData);
  if (saved) return saved;
  const entered = await windows.askAdmin(secrets.validate);
  if (!entered) return null;
  secrets.saveAdmin(userData, entered);
  return secrets.loadAdmin(userData);
}

async function boot() {
  const userData = app.getPath("userData");
  const logDir = path.join(userData, "logs");
  for (const port of [layout.API_PORT, layout.UI_PORT]) {
    if (!(await procs.portFree(port))) throw new Error(`Port ${port} is already in use. Close the program that uses it, or set AQE_DESKTOP_API_PORT (the backend port is fixed when the app is built).`);
  }
  const admin = await credentials(userData);
  if (!admin) return app.quit();
  const uiOrigin = `http://127.0.0.1:${layout.UI_PORT}`;

  const backend = layout.backendCommand();
  const backendEnv = { ...process.env, ...backend.extraEnv, ATLAS_PROFILE: "desktop", ATLAS_DATA_DIR: path.join(userData, "data"), ATLAS_ALLOWED_ORIGINS: uiOrigin, ATLAS_ADMIN_USERNAME: admin.username, ATLAS_ADMIN_PASSWORD: admin.password, ATLAS_SECRET_KEY: secrets.loadOrCreateKey(userData), ATLAS_BACKEND_PORT: String(layout.API_PORT) };
  delete backendEnv.ELECTRON_RUN_AS_NODE;
  const api = procs.start("backend", backend.command, backend.args, { env: backendEnv, cwd: backend.cwd, logDir });
  children.push(api);

  const ui = layout.uiServer();
  const uiEnv = { ...process.env, ELECTRON_RUN_AS_NODE: "1", NODE_ENV: "production", HOSTNAME: "127.0.0.1", PORT: String(layout.UI_PORT) };
  const web = procs.start("ui", process.execPath, [ui.script], { env: uiEnv, cwd: ui.cwd, logDir });
  children.push(web);

  await procs.waitFor(`http://127.0.0.1:${layout.API_PORT}/api/health`, api, "backend", WAIT_MS);
  await procs.waitFor(`${uiOrigin}/login`, web, "UI", WAIT_MS);
  windows.openMain(`${uiOrigin}/login`);
  mainOpened = true;
}

function stopAll() {
  while (children.length) procs.stop(children.pop());
}

app.whenReady().then(() => boot().catch((error) => {
  stopAll();
  dialog.showErrorBox("Agentic QE Platform could not start", String(error.message || error));
  app.quit();
}));
app.on("before-quit", stopAll);
app.on("window-all-closed", () => { if (mainOpened) app.quit(); });
