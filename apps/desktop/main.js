// Electron main: starts the local backend and UI on loopback, then opens the app. Both stop when the app quits.
const { app, dialog, Menu, session } = require("electron");
const path = require("node:path");
const central = require("./lib/central");
const layout = require("./lib/layout");
const procs = require("./lib/procs");
const secrets = require("./lib/secrets");
const terminal = require("./lib/terminal");
const windows = require("./lib/windows");

if (process.env.AQE_DESKTOP_USER_DATA) app.setPath("userData", process.env.AQE_DESKTOP_USER_DATA); // tests use a temporary folder

const children = [];
let mainOpened = false; // the setup window closing must not quit the app before the main window exists
const WAIT_MS = Number(process.env.AQE_DESKTOP_START_TIMEOUT_MS || 120000);

// The member's sign-in: the saved grant while it lasts, else the sign-in window (central sign-in, R6).
async function signIn(userData) {
  const saved = secrets.loadSignIn(userData);
  if (saved) return saved;
  const made = await windows.askSignIn(central.signIn, process.env.AQE_DESKTOP_SERVER || "");
  if (!made) return null;
  secrets.saveSignIn(userData, made);
  return secrets.loadSignIn(userData);
}

function menu(userData) {
  const signOut = { label: "Sign out", click: () => { secrets.clearSignIn(userData); app.relaunch(); app.quit(); } };
  const roles = [{ role: "editMenu" }, { role: "viewMenu" }, { role: "windowMenu" }];
  const template = process.platform === "darwin" ? [{ role: "appMenu" }, { label: "Account", submenu: [signOut] }, ...roles] : [{ label: "File", submenu: [signOut, { role: "quit" }] }, ...roles];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

async function boot() {
  const userData = app.getPath("userData");
  const logDir = path.join(userData, "logs");
  for (const port of [layout.API_PORT, layout.UI_PORT]) {
    if (!(await procs.portFree(port))) throw new Error(`Port ${port} is already in use. Close the program that uses it, or set AQE_DESKTOP_API_PORT (the backend port is fixed when the app is built).`);
  }
  const member = await signIn(userData);
  if (!member) return app.quit();
  const uiOrigin = `http://127.0.0.1:${layout.UI_PORT}`;

  const backend = layout.backendCommand();
  const backendEnv = { ...process.env, ...backend.extraEnv, ATLAS_PROFILE: "desktop", ATLAS_DATA_DIR: path.join(userData, "data"), ATLAS_ALLOWED_ORIGINS: uiOrigin, ATLAS_DESKTOP_GRANT: member.grant, ATLAS_DESKTOP_SERVER_KEY: member.public_key, ATLAS_SECRET_KEY: secrets.loadOrCreateKey(userData), ATLAS_BACKEND_PORT: String(layout.API_PORT) };
  delete backendEnv.ELECTRON_RUN_AS_NODE;
  for (const name of ["ATLAS_ADMIN_USERNAME", "ATLAS_ADMIN_PASSWORD", "ATLAS_ADMIN_PASSWORD_HASH"]) delete backendEnv[name]; // no local admin
  const api = procs.start("backend", backend.command, backend.args, { env: backendEnv, cwd: backend.cwd, logDir });
  children.push(api);

  const ui = layout.uiServer();
  const uiEnv = { ...process.env, ELECTRON_RUN_AS_NODE: "1", NODE_ENV: "production", HOSTNAME: "127.0.0.1", PORT: String(layout.UI_PORT) };
  const web = procs.start("ui", process.execPath, [ui.script], { env: uiEnv, cwd: ui.cwd, logDir });
  children.push(web);

  await procs.waitFor(`http://127.0.0.1:${layout.API_PORT}/api/health`, api, "backend", WAIT_MS);
  await procs.waitFor(`${uiOrigin}/login`, web, "UI", WAIT_MS);
  const token = await central.localSession(`http://127.0.0.1:${layout.API_PORT}`, member.grant, "aqe_session").catch((error) => {
    secrets.clearSignIn(userData); // a sign-in the backend refuses is dropped, so the next start asks again
    throw new Error(`${error.message} Start the app again to sign in.`);
  });
  // cookies are per host, not per port, so the UI's pages carry the backend's session
  await session.defaultSession.cookies.set({ url: uiOrigin, name: "aqe_session", value: token, httpOnly: true, sameSite: "strict", expirationDate: member.expires });
  terminal.register(`http://127.0.0.1:${layout.API_PORT}`, async () => `aqe_session=${token}`);
  menu(userData);
  windows.openMain(`${uiOrigin}/`);
  mainOpened = true;
}

function stopAll() {
  terminal.closeAll();
  while (children.length) procs.stop(children.pop());
}

app.whenReady().then(() => boot().catch((error) => {
  stopAll();
  dialog.showErrorBox("Agentic QE Platform could not start", String(error.message || error));
  app.quit();
}));
app.on("before-quit", stopAll);
app.on("window-all-closed", () => { if (mainOpened) app.quit(); });
