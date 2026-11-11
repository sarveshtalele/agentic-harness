// Child processes: argument lists only, never a shell. Logs go to <userData>/logs.
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");

function start(name, command, args, { env, cwd, logDir }) {
  fs.mkdirSync(logDir, { recursive: true });
  const log = fs.openSync(path.join(logDir, `${name}.log`), "a");
  const child = spawn(command, args, { env, cwd, stdio: ["ignore", log, log], windowsHide: true, shell: false });
  child.on("close", () => fs.closeSync(log));
  child.exited = new Promise((resolve) => child.on("exit", (code) => resolve(code)));
  return child;
}

function stop(child) {
  if (!child || child.exitCode !== null || !child.pid) return;
  if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true });
  else child.kill("SIGTERM");
}

function portFree(port) {
  return new Promise((resolve) => {
    const probe = net.createServer();
    probe.once("error", () => resolve(false));
    probe.listen(port, "127.0.0.1", () => probe.close(() => resolve(true)));
  });
}

function ok(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => { res.resume(); resolve(res.statusCode >= 200 && res.statusCode < 400); });
    req.on("error", () => resolve(false));
    req.setTimeout(2000, () => { req.destroy(); resolve(false); });
  });
}

async function waitFor(url, child, name, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`The ${name} stopped before it was ready (exit code ${child.exitCode}). See the ${name} log.`);
    if (await ok(url)) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`The ${name} did not answer at ${url} within ${Math.round(timeoutMs / 1000)} seconds. See the ${name} log.`);
}

module.exports = { start, stop, portFree, waitFor };
