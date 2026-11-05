// Install / update / uninstall / doctor / plan / gitignore for the agentic-qe plugin (Claude Code and Codex). Stdlib only.
// Usage: node scripts/agentic-qe.ts <install|update|uninstall|doctor|plan|gitignore> --host claude|codex|auto [--scope user|project|local]
//        [--project <dir>] [--yes] [--dry-run] [--json]
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { spawnSync } from "node:child_process";
import { createInterface } from "node:readline/promises";
import { parseArgs } from "node:util";
import { verifyLedger } from "../../../hooks/src/memory-logger.ts";
import { safeWrite } from "../../../hooks/src/hook-common.ts";
import { findPython, validatorHome, PINNED, SCRIPT, resetPython } from "../../../hooks/src/validate.ts";

export const PLUGIN_ROOT = resolve(import.meta.dirname, "..", "..", "..");
const REPO = "sarveshtalele/agentic-qe";
const NAME = "agentic-qe";
const PLUGIN_ID = "agentic-qe@agentic-qe";
const TOML_HEADER = `[plugins."${PLUGIN_ID}"]`;
const TOML_SNIPPET = `${TOML_HEADER}\nenabled = true\n`;

export type Host = "claude" | "codex";
export type Action = "install" | "update" | "uninstall";
export interface Opts {
  action: Action; host: Host; scope: "user" | "project" | "local";
  project?: string; yes?: boolean;
}
export type Step =
  | { kind: "exec"; argv: string[]; cwd?: string }
  | { kind: "append"; path: string; text: string }
  | { kind: "note"; text: string };

export function planActions(o: Opts): Step[] {
  const needsProject = o.scope !== "user";
  if (needsProject && !o.project) throw new Error(`--scope ${o.scope} requires --project <dir>`);
  const cwd = needsProject ? o.project : undefined;
  const cli = o.host;
  const steps: Step[] = [];
  const exec = (...argv: string[]) => steps.push({ kind: "exec", argv: [cli, ...argv], ...(cwd ? { cwd } : {}) });

  if (o.host === "claude") {
    const sc = ["--scope", o.scope];
    if (o.action === "install") { exec("plugin", "marketplace", "add", REPO, ...sc); exec("plugin", "install", PLUGIN_ID, ...sc); }
    // a marketplace refresh alone leaves the installed copy old, and a plugin uninstall leaves the marketplace registered
    else if (o.action === "update") { exec("plugin", "marketplace", "update", NAME); exec("plugin", "update", PLUGIN_ID, ...sc); }
    else { exec("plugin", "uninstall", PLUGIN_ID, ...sc); exec("plugin", "marketplace", "remove", NAME, ...sc); }
    return steps;
  }

  // codex plugin mode
  if (o.scope === "local") throw new Error("codex supports --scope user|project only");
  const cfg = o.project ? join(o.project, ".codex", "config.toml") : "";
  const has = o.scope === "project" && existsSync(cfg) && readFileSync(cfg, "utf-8").includes(TOML_HEADER);
  if (o.action === "install") {
    exec("plugin", "marketplace", "add", REPO);
    if (o.scope === "user") steps.push({ kind: "note", text: "Enable the plugin in the Codex UI: run /plugins and enable agentic-qe." });
    else if (has) steps.push({ kind: "note", text: `${cfg} already enables ${PLUGIN_ID}.` });
    else {
      steps.push({ kind: "note", text: `Add to ${cfg}:\n${TOML_SNIPPET}` });
      if (o.yes) steps.push({ kind: "append", path: cfg, text: (existsSync(cfg) && !readFileSync(cfg, "utf-8").endsWith("\n") && readFileSync(cfg, "utf-8") ? "\n" : "") + TOML_SNIPPET });
      else steps.push({ kind: "note", text: "Re-run with --yes to append this snippet automatically." });
    }
  } else if (o.action === "update") exec("plugin", "marketplace", "upgrade", NAME);
  else {
    exec("plugin", "marketplace", "remove", NAME);
    if (o.scope === "project" && has) steps.push({ kind: "note", text: `Remove the ${TOML_HEADER} section from ${cfg} manually.` });
  }
  return steps;
}

export const fmtStep = (s: Step): string =>
  s.kind === "exec" ? `$ ${s.cwd ? `(cd ${s.cwd}) ` : ""}${s.argv.join(" ")}`
    : s.kind === "append" ? `append to ${s.path}:\n${s.text}`
    : `note: ${s.text}`;

// On Windows `claude`/`codex` may be npm .cmd shims, which spawn only through a shell. Every argv here is a fixed word
// (paths go in cwd, never argv), so the shell sees no user text.
const WIN = process.platform === "win32";
// cmd.exe looks in the working directory before PATH, so a project could ship its own claude.cmd; this turns that off
const SPAWN_ENV = WIN ? { ...process.env, NoDefaultCurrentDirectoryInExePath: "1" } : process.env;
export const WIN_HINT = `hint (Windows): EPERM or "in use" means another process holds %USERPROFILE%\\.claude\\plugins\\marketplaces\\${NAME}. Close every Claude Code window and the Claude desktop app, then run the command again from a fresh terminal. If it still fails, delete that folder and run: claude plugin marketplace add ${REPO}`;

/** Runs one step. Returns false when an exec fails. */
export function runStep(s: Step, log: (m: string) => void = console.log): boolean {
  log(fmtStep(s));
  if (s.kind === "exec") {
    const r = spawnSync(s.argv[0], s.argv.slice(1), { cwd: s.cwd, stdio: "inherit", shell: WIN, env: SPAWN_ENV });
    if (r.status !== 0 && WIN) log(WIN_HINT);
    return r.status === 0;
  }
  // safeWrite refuses a symlinked target (a .gitignore -> ~/.zshrc must not receive our text); it writes the whole file via temp + rename
  if (s.kind === "append") {
    let root = dirname(s.path);
    while (!existsSync(root)) root = dirname(root);
    safeWrite(s.path, (existsSync(s.path) ? readFileSync(s.path, "utf-8") : "") + s.text, root);
  }
  return true;
}

// ---------- gitignore ----------
export const GITIGNORE_BLOCK = `# agentic-qe (local state and generated output)
.claude/settings.local.json
.qe/
.qe.untrusted-*/
results/
test-results/
playwright-report/
`;
const GI_MARK = GITIGNORE_BLOCK.split("\n")[0];

/** Plan for `gitignore --project <dir>`: always prints the block; appends it when --yes and not already present. */
export function planGitignore(project: string, yes = false): Step[] {
  const path = join(project, ".gitignore");
  const cur = existsSync(path) ? readFileSync(path, "utf-8") : "";
  if (cur.includes(GI_MARK)) return [{ kind: "note", text: `${path} already has the agentic-qe block.` }];
  const steps: Step[] = [{ kind: "note", text: `Add to ${path}:\n${GITIGNORE_BLOCK}` }];
  if (yes) steps.push({ kind: "append", path, text: (cur && !cur.endsWith("\n") ? "\n" : "") + (cur ? "\n" : "") + GITIGNORE_BLOCK });
  else steps.push({ kind: "note", text: "Re-run with --yes to append this block automatically." });
  return steps;
}

// ---------- doctor ----------
export type ExecFn = (argv: string[], o: { cwd?: string; timeout: number }) => { ok: boolean; stdout: string };
export const defaultExec: ExecFn = (argv, o) => {
  try {
    const r = spawnSync(argv[0], argv.slice(1), { cwd: o.cwd, timeout: o.timeout, encoding: "utf-8", shell: WIN, env: SPAWN_ENV });
    return { ok: r.status === 0, stdout: String(r.stdout ?? "").trim() };
  } catch { return { ok: false, stdout: "" }; }
};
export interface Check { name: string; ok: boolean; required: boolean; detail: string }

const EXPECTED_HOOKS = ["guard-write.ts", "guard-bash.ts", "stamp-metadata.ts", "ledger-hook.ts", "approval-hook.ts"];
const FOREIGN_DIRS = ["backend", "frontend", "gateway", "commands"];

/** Steps that create the validator's own Python environment and install pinned pandas and numpy into it. */
export function planValidator(platform = process.platform, env = process.env): Step[] {
  const home = validatorHome(env);
  const py = platform === "win32" ? ["py", "-3"] : ["python3"];
  const venvPy = platform === "win32" ? join(home, "Scripts", "python.exe") : join(home, "bin", "python");
  return [
    { kind: "note", text: `Creates ${home} (outside the project) and installs ${PINNED.join(" ")} from PyPI. Needs Python 3.10 or newer.` },
    { kind: "exec", argv: [...py, "-m", "venv", home] },
    { kind: "exec", argv: [venvPy, "-m", "pip", "install", "--disable-pip-version-check", "--quiet", ...PINNED] },
    { kind: "exec", argv: [venvPy, SCRIPT, "--probe"] }
  ];
}

export function runDoctor(o: { host: Host; project?: string; root?: string; nodeVersion?: string; findPython?: () => { python: string; probe: string } | null }, exec: ExecFn = defaultExec): { ok: boolean; checks: Check[] } {
  const root = o.root ?? PLUGIN_ROOT;
  const checks: Check[] = [];
  const add = (name: string, ok: boolean, required: boolean, detail: string) => checks.push({ name, ok, required, detail });

  const nv = o.nodeVersion ?? process.versions.node;
  const [maj, min] = nv.split(".").map(Number);
  add("node >= 22.18", maj > 22 || (maj === 22 && min >= 18), true, nv);

  for (const h of ["claude", "codex"] as Host[]) {
    const r = exec([h, "--version"], { timeout: 5000 });
    add(`${h} CLI`, r.ok, h === o.host, r.ok ? r.stdout : "not found");
  }

  let version = "?";
  try { version = JSON.parse(readFileSync(join(root, ".claude-plugin", "plugin.json"), "utf-8")).version; add("plugin.json version", true, true, version); }
  catch (e) { add("plugin.json version", false, true, String(e)); }

  if (o.host === "claude") {
    const r = exec(["claude", "plugin", "list", "--json"], { cwd: o.project, timeout: 5000 });
    let detail = "unavailable";
    let current = true;
    if (r.ok) try {
      const list = JSON.parse(r.stdout);
      const hits = (Array.isArray(list) ? list : []).filter((p: any) => String(p.id ?? p.name ?? "").startsWith(NAME));
      detail = hits.length ? hits.map((p: any) => `${p.scope ?? "?"}@${p.version ?? "?"}`).join(", ") : "not installed";
      // An installed copy that differs from this repo means the user runs stale hooks and skills.
      const stale = hits.filter((p: any) => version && p.version && p.version !== version);
      if (stale.length) {
        current = false;
        detail += ` — differs from repo ${version}; fix: claude plugin marketplace update agentic-qe && claude plugin update agentic-qe@agentic-qe --scope ${stale[0].scope ?? "user"}`;
      }
      for (const p of hits) {
        const dir = String(p.installPath ?? p.path ?? "");
        const foreign = dir && existsSync(dir) ? FOREIGN_DIRS.filter((d) => existsSync(join(dir, d))) : [];
        if (foreign.length) add("installed copy contents", false, true, `${dir} has foreign folders: ${foreign.join(", ")}; reinstall the plugin`);
      }
    } catch { detail = "unparseable output"; }
    add("installed scope/version", current, true, detail);
  }

  try {
    const hooks = readFileSync(join(root, "hooks", "hooks.json"), "utf-8");
    const missing = EXPECTED_HOOKS.filter((h) => !hooks.includes(h));
    if (!/session-check\.(ts|mjs)/.test(hooks)) missing.push("session-check (.ts or .mjs)");
    add("hooks.json hooks", !missing.length, true, missing.length ? `missing ${missing.join(", ")}` : `${EXPECTED_HOOKS.length + 1} hooks listed`);
  } catch (e) { add("hooks.json hooks", false, true, String(e)); }

  // the repository is private: without a GitHub login for git, updates fail and an old cached copy keeps running
  const git = exec(["git", "ls-remote", `https://github.com/${REPO}.git`, "HEAD"], { timeout: 20000 });
  add("GitHub access for updates", git.ok, false, git.ok ? "ok" : `git cannot read github.com/${REPO}; sign git in once: gh auth login, then gh auth setup-git (or run git clone https://github.com/${REPO}.git once and sign in); then: claude plugin marketplace update ${NAME} && claude plugin update ${PLUGIN_ID}`);

  // gates run the pandas/numpy validator; without it every gate approval is refused
  const py = o.findPython ? o.findPython() : findPython();
  add("pandas/numpy validator", !!py, true, py ? `${py.python} ${py.probe}` : `not set up; run: node "${join(root, "skills", "qe-doctor", "scripts", "agentic-qe.ts")}" validator --yes`);

  if (o.project) {
    if (existsSync(join(o.project, ".qe"))) {
      try { const v = verifyLedger(join(o.project, ".qe", "ledger.jsonl"), o.project); add("ledger integrity", v.ok, true, v.ok ? "ok" : `broken at ${v.brokenAt ?? "?"}: ${v.reason ?? ""}`); }
      catch (e) { add("ledger integrity", false, true, String(e)); }
    }
    // never execute project binaries (node_modules/.bin is repo-controlled): read the version from package.json instead
    let pw = "";
    try { pw = String(JSON.parse(readFileSync(join(o.project, "node_modules", "@playwright", "test", "package.json"), "utf-8")).version ?? ""); } catch { /* not installed */ }
    add("playwright", !!pw, false, pw ? `Version ${pw}` : "not installed in project");
  }
  return { ok: checks.every((c) => c.ok || !c.required), checks };
}

// ---------- cli ----------
export function detectHost(env = process.env, which: (c: string) => boolean = (c) => defaultExec([c, "--version"], { timeout: 5000 }).ok): Host {
  const codexEnv = Object.keys(env).some((k) => k.startsWith("CODEX_")) || (!!env.PLUGIN_ROOT && !env.CLAUDE_CODE_ENTRYPOINT);
  if (env.CLAUDECODE || env.CLAUDE_CODE_ENTRYPOINT) return "claude";
  if (codexEnv) return "codex";
  if (which("claude")) return "claude";
  if (which("codex")) return "codex";
  throw new Error("cannot detect host; pass --host claude|codex");
}

const HELP = `agentic-qe lifecycle CLI

Usage: node scripts/agentic-qe.ts <command> [options]

The plugin is the only supported installation method.

Commands:
  install    Install the plugin
  update     Refresh the marketplace, then update the installed plugin in the chosen scope
  uninstall  Remove the plugin, then its marketplace, from the chosen scope
  doctor     Check Node, CLIs, versions, GitHub access, the pandas/numpy validator, hooks, ledger and Playwright
  validator  Create the validator's Python environment (outside the project) with pinned pandas and numpy (asks first)
  plan       Show what install would run, without running it
  gitignore  Print (with --yes, append) the recommended .gitignore block for --project <dir>

Options:
  --host claude|codex|auto      Target host (default: auto)
  --scope user|project|local    user: ~/.claude/settings.json (global); project: <repo>/.claude/settings.json
                                (commit it); local: <repo>/.claude/settings.local.json (gitignored).
                                Codex supports user and project only. Default: user
  --project <dir>               Project folder for project/local scope and gitignore
  --yes                         Run without the confirmation prompt
  --dry-run                     Print the commands and file changes only
  --json                        Machine-readable output
  -h, --help                    Show this help
`;

async function main(): Promise<number> {
  const { values: v, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      host: { type: "string", default: "auto" }, scope: { type: "string", default: "user" },
      project: { type: "string" }, yes: { type: "boolean", default: false }, "dry-run": { type: "boolean", default: false }, json: { type: "boolean", default: false },
      help: { type: "boolean", short: "h", default: false },
    },
  });
  const cmd = positionals[0];
  if (v.help || !cmd) { console.log(HELP); return 0; }
  const out = (m: string) => (v.json ? console.error(m) : console.log(m));
  try {
    if (!["install", "update", "uninstall", "doctor", "plan", "gitignore", "validator"].includes(cmd)) throw new Error("usage: agentic-qe.ts <install|update|uninstall|doctor|plan|gitignore|validator> --host claude|codex|auto [--scope user|project|local] [--project <dir>] [--yes] [--dry-run] [--json]");
    if (cmd === "validator") {
      const steps = planValidator();
      for (const s of steps) out(fmtStep(s));
      if (v["dry-run"]) return 0;
      if (!v.yes) {
        if (!process.stdin.isTTY) { console.error("refusing to download pandas and numpy without --yes on a non-interactive stdin"); return 2; }
        const rl = createInterface({ input: process.stdin, output: process.stderr });
        const a = (await rl.question("Create the validator environment and download pandas and numpy? [y/N] ")).trim().toLowerCase();
        rl.close();
        if (a !== "y" && a !== "yes") { out("aborted"); return 1; }
      }
      for (const s of steps) if (s.kind === "exec" && !runStep(s, out)) { console.error("command failed: " + fmtStep(s)); return 1; }
      resetPython();
      out(findPython() ? "validator: ready" : "validator: installed, but no working Python with pandas was found");
      return findPython() ? 0 : 1;
    }
    if (!["user", "project", "local"].includes(v.scope!)) throw new Error("--scope must be user|project|local");
    if (!["auto", "claude", "codex"].includes(v.host!)) throw new Error("--host must be claude|codex|auto");
    if (cmd === "gitignore") {
      if (!v.project) throw new Error("gitignore requires --project <dir>");
      const dir = resolve(v.project);
      if (!existsSync(dir) || !statSync(dir).isDirectory()) throw new Error(`--project is not an existing directory: ${dir}`);
      const steps = planGitignore(dir, v.yes);
      for (const s of steps) { if (s.kind === "append") { if (!v["dry-run"]) runStep(s, out); else out(fmtStep(s)); } else out(fmtStep(s)); }
      return 0;
    }
    const host = v.host === "auto" ? detectHost() : (v.host as Host);
    let project: string | undefined;
    if (v.project !== undefined || v.scope !== "user" || cmd === "doctor") {
      project = resolve(v.project ?? process.cwd());
      if (!existsSync(project) || !statSync(project).isDirectory()) throw new Error(`--project is not an existing directory: ${project}`);
    }
    if (cmd === "doctor") {
      const r = runDoctor({ host, project });
      if (v.json) console.log(JSON.stringify(r, null, 2));
      else { for (const c of r.checks) console.log(`${c.ok ? "PASS" : c.required ? "FAIL" : "WARN"}  ${c.name}: ${c.detail}`); console.log(r.ok ? "doctor: ok" : "doctor: required checks failed"); }
      return r.ok ? 0 : 1;
    }
    const action: Action = cmd === "plan" ? "install" : (cmd as Action);
    const steps = planActions({ action, host, scope: v.scope as Opts["scope"], project, yes: v.yes });
    out(`Plan: ${action} agentic-qe (host=${host}, scope=${v.scope})`);
    for (const s of steps) out("  " + fmtStep(s));
    if (cmd === "plan" || v["dry-run"]) {
      if (v.json) console.log(JSON.stringify({ steps }, null, 2));
      return 0;
    }
    if (!v.yes) {
      if (!process.stdin.isTTY) { console.error("refusing to run without --yes on a non-interactive stdin"); return 2; }
      const rl = createInterface({ input: process.stdin, output: process.stderr });
      const a = (await rl.question("Proceed? [y/N] ")).trim().toLowerCase();
      rl.close();
      if (a !== "y" && a !== "yes") { out("aborted"); return 1; }
    }
    for (const s of steps) if (!runStep(s, out)) { console.error("command failed: " + fmtStep(s)); return 1; }
    if (v.json) console.log(JSON.stringify({ ok: true, steps }, null, 2));
    return 0;
  } catch (e) {
    console.error(`error: ${(e as Error).message}`);
    return 2;
  }
}

if (import.meta.main) process.exitCode = await main();
