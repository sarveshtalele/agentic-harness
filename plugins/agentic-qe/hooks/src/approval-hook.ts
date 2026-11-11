import { basename, dirname, isAbsolute, join, normalize, resolve } from "node:path";
import { chmodSync, existsSync, lstatSync, mkdirSync, readFileSync, realpathSync, renameSync } from "node:fs";
import { spawn, type SpawnOptions } from "node:child_process";
import { connect } from "node:net";
import { fileURLToPath } from "node:url";
import { type HookInput, projectRoot, isMain, readInput, approvedPaths, emitContext, isInside, detectHost } from "./hook-common.ts";
import { anchorDir, anchorDirFor, anchorFile, anchorId, appendLedger, homeAnchorDir, newApprovalKey } from "./memory-logger.ts";
import { trustOf, gateStatus } from "./on-decision.ts";
import { buildCoverage, checkGate, writeCoverage, handoff } from "./coverage.ts";
import { gateFingerprint } from "./fingerprint.ts";
import { recordValidation } from "./validate.ts";
import { openLease, closeLease } from "./phase-lease.ts";

/** Validator checks the coverage map already reports in its own words (shown once, not twice). */
const COVERED_BY_MAP = new Set(["requirements.present", "requirements.evidence", "plan.scenarios", "plan.ids", "plan.unique", "plan.level", "plan.total", "plan.levels", "plan.requirements", "design.coverage", "design.links", "generate.coverage", "generate.markers", "generate.files", "results.coverage"]);
import { safeWrite, realRootOf } from "./hook-common.ts";

/** Relative, normalized, inside root, no "..". Returns null if unacceptable. Trailing / marks a folder. */
export function cleanPath(root: string, p: string): string | null {
  const dir = p.endsWith("/");
  if (!p || isAbsolute(p) || p.includes("\0") || p.split(/[\\/]/).includes("..")) return null;
  const n = normalize(p).replace(/\\/g, "/").replace(/\/$/, "");
  if (!n || n === "." || !isInside(root, resolve(root, n))) return null;
  return dir ? n + "/" : n;
}

/** Writes a user-authored gate decision. Only the prompt hook calls this. */
export function recordUserGate(workspaceDir: string, gate: number, decision: "APPROVED" | "REJECTED", session = "", app?: string, extra: { docs?: Record<string, string>; waiver?: { reason: string; gaps: string[] } } = {}): void {
  appendLedger(join(workspaceDir, "ledger.jsonl"), {
    type: "gate_decision", gate, decision, ...(app ? { app } : {}), ...extra, source: "user_prompt", session_id: session, timestamp: new Date().toISOString()
  });
}

export const GRAMMAR = "approve gate <0-5> [for <app>] [with gaps: <reason>] | reject gate <0-5> [for <app>] | approve create <path>[, <path>...] | reset qe for <app> (the whole message, nothing else; gate 0 also accepts: approve gate 0 for <app> mode greenfield|brownfield)";
const APP = /^[A-Za-z0-9._-]{1,64}$/;

export type Parsed =
  | { kind: "gate"; decision: "APPROVED" | "REJECTED"; gate: number; app?: string; mode?: string; waiver?: string }
  | { kind: "create"; paths: string[] }
  | { kind: "reset"; app: string }
  | { kind: "bad"; why: string }
  | null;

/** The WHOLE message must be exactly one phrase. null = not ours (nothing recorded, no reply). */
export function parseMessage(prompt: string): Parsed {
  const t = prompt.trim().replace(/\.$/, "");
  let m = t.match(/^(approve|reject) gate (\d+)(?: for (\S+)(?: mode (\S+))?)?(?: with gaps: (.+))?$/i);
  if (m) {
    const [, verb, g, app, mode, waiver] = m;
    if (waiver !== undefined && (verb.toLowerCase() !== "approve" || waiver.trim().length < 10)) return { kind: "bad", why: "with gaps: needs a reason of at least 10 characters, and only follows approve" };
    if (!/^[0-5]$/.test(g)) return { kind: "bad", why: `gate must be 0 to 5, got "${g}"` };
    if (app !== undefined && !APP.test(app)) return { kind: "bad", why: `app "${app.slice(0, 40)}" must match [A-Za-z0-9._-]{1,64}` };
    if (mode !== undefined && !(Number(g) === 0 && verb.toLowerCase() === "approve" && /^(greenfield|brownfield)$/i.test(mode))) return { kind: "bad", why: "mode is only accepted as: approve gate 0 for <app> mode greenfield|brownfield" };
    return { kind: "gate", decision: verb.toLowerCase() === "approve" ? "APPROVED" : "REJECTED", gate: Number(g), app, mode: mode?.toLowerCase(), ...(waiver ? { waiver: waiver.trim() } : {}) };
  }
  m = t.match(/^approve create (\S.*)$/i);
  if (m) return { kind: "create", paths: m[1].split(/\s*,\s*/).map((p) => p.trim()) };
  m = t.match(/^reset qe for (\S+)$/i);
  if (m) return APP.test(m[1]) ? { kind: "reset", app: m[1] } : { kind: "bad", why: `app "${m[1].slice(0, 40)}" must match [A-Za-z0-9._-]{1,64}` };
  if (/^(approve|reject)\b/i.test(t)) return { kind: "bad", why: "the message is not exactly one approval phrase (extra text, a second line or an unknown form)" };
  return null;
}

const pad = (n: number) => String(n).padStart(2, "0");
/** YYYYMMDDTHHMMSS in local time, used in report and backup names. */
export const stampNow = (d = new Date()) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}T${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;

/** Creates .qe/ (0700), run.json (0600) and the ledger's first record. Only the hook may do this. */
export function bootstrap(root: string, app: string, mode: string | undefined, session = "", env = process.env): void {
  const ws = join(root, ".qe");
  try { if (lstatSync(ws).isSymbolicLink()) throw new Error(".qe is a symlink; refusing to start a run through it"); } catch (e) { if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e; }
  mkdirSync(ws, { recursive: true, mode: 0o700 });
  chmodSync(ws, 0o700);
  safeWrite(join(ws, ".gitignore"), "*\n", root, { mode: 0o600 });
  newApprovalKey(root); // fresh key: approvals of any earlier run no longer verify
  const cfg = env.CLAUDE_PLUGIN_OPTION_DEFAULT_MODE ?? env.CLAUDE_PLUGIN_OPTION_default_mode;
  const m = mode ?? (cfg && /^(greenfield|brownfield|auto)$/.test(cfg) ? cfg : "auto");
  const startedAt = new Date().toISOString();
  safeWrite(join(ws, "run.json"), JSON.stringify({ app, mode: m, started_at: startedAt, bootstrap: "hook" }, null, 2) + "\n", root, { mode: 0o600 });
  appendLedger(join(ws, "ledger.jsonl"), { type: "run_start", app, mode: m, source: "approval_hook", session_id: session, timestamp: startedAt }, root, true);
  try { chmodSync(join(ws, "ledger.jsonl"), 0o600); } catch { /* best effort */ }
}

export interface Outcome { done: string[]; notes: string[]; approved: { gate: number; app?: string }[] }

function runApp(root: string): string | undefined {
  try { const a = String(JSON.parse(readFileSync(join(root, ".qe", "run.json"), "utf-8")).app ?? ""); return APP.test(a) ? a : undefined; } catch { return undefined; }
}

/** Handles one user message. Whole-message grammar only; see GRAMMAR. */
export function processPrompt(prompt: string, root: string, session = "", env = process.env): Outcome {
  const out: Outcome = { done: [], notes: [], approved: [] };
  const p = parseMessage(prompt);
  if (!p) return out;
  if (p.kind === "bad") { out.notes.push(`agentic-qe did not record this message: ${p.why}. Accepted forms: ${GRAMMAR}`); return out; }
  const ws = join(root, ".qe");
  const exists = existsSync(ws);

  if (p.kind === "reset") {
    if (exists) renameSync(ws, join(root, `.qe.untrusted-${stampNow()}`));
    bootstrap(root, p.app, undefined, session, env);
    out.done.push(`run state reset for ${p.app}; old .qe/ kept as .qe.untrusted-*`);
    out.notes.push(`Fresh .qe/ created. Next: approve gate 0 for ${p.app}`);
    return out;
  }
  if (!exists) {
    if (p.kind === "gate" && p.decision === "APPROVED" && p.gate === 0) {
      if (!p.app) { out.notes.push("No QE run exists yet. Reply exactly: approve gate 0 for <app>"); return out; }
      bootstrap(root, p.app, p.mode, session, env);
      out.done.push(`run started for ${p.app}`);
    } else {
      out.notes.push("No QE run exists yet. Start one with: approve gate 0 for <app>");
      return out;
    }
  } else {
    const t = trustOf(root);
    if (!t.trusted) {
      out.notes.push(`Nothing recorded: the run state in .qe/ is untrusted (${t.reason ?? "ledger not verified on this machine"}). If you want a fresh run, reply exactly: reset qe for <app>`);
      return out;
    }
  }
  if (p.kind === "gate") {
    // Gates are sequential: approving N needs N-1 approved first (rejecting is always allowed).
    if (p.decision === "APPROVED" && p.gate > 0 && gateStatus(ws)[p.gate - 1].status !== "APPROVED") {
      out.notes.push(`Nothing recorded: Gate ${p.gate - 1} is not approved yet${gateStatus(ws)[p.gate - 1].status === "REOPENED" ? " (reopened by a dashboard edit)" : ""}. Approve gates in order (0 to 5).`);
      return out;
    }
    const app = p.app ?? runApp(root);
    // coverage: a gate is approved only when what it approves is complete, or the user names the gaps they accept
    const extra: { docs?: Record<string, string>; waiver?: { reason: string; gaps: string[] } } = {};
    if (p.decision === "APPROVED" && app) {
      if (p.gate >= 1) {
        const cov = buildCoverage(root, app);
        const check = checkGate(cov, p.gate, { host: detectHost({}, env) });
        // the pandas/numpy validator: the checks the coverage map cannot make (types per area, similarity, score inflation, assertions)
        const v = recordValidation(root, app, p.gate, cov, env);
        const extraLines = v.verdict ? v.verdict.errors.filter((e) => !COVERED_BY_MAP.has(e.check)).map((e) => `${e.message}${e.ids.length ? `: ${e.ids.slice(0, 25).join(", ")}` : ""}`) : v.lines;
        const gaps = [...check.gaps, ...extraLines.map((l) => `validator: ${l}`)];
        if (gaps.length && !p.waiver) {
          out.notes.push(`Nothing recorded: Gate ${p.gate} is not complete. ${gaps.length} gap(s):\n- ${gaps.join("\n- ")}\nFix them and approve again, or accept them by name: approve gate ${p.gate} with gaps: <reason>. docs/qe/${app}/coverage-map.md and validation.json list every row.`);
          try { writeCoverage(root, app, p.gate - 1); } catch { /* best effort */ }
          return out;
        }
        if (gaps.length) extra.waiver = { reason: p.waiver!, gaps: [...new Set([...check.missing, ...(v.verdict?.errors.flatMap((e) => e.ids) ?? [])])].concat(check.missing.length ? [] : gaps) };
      }
      // Gate 0 starts the run and its intake documents are written after it, so it has no fingerprint
      if (p.gate >= 1) extra.docs = gateFingerprint(root, app, p.gate);
    }
    recordUserGate(ws, p.gate, p.decision, session, app ?? p.app, extra);
    out.done.push(`Gate ${p.gate} ${p.decision}${extra.waiver ? ` with ${extra.waiver.gaps.length} accepted gap(s): ${extra.waiver.reason}` : ""}`);
    if (app) { try { writeCoverage(root, app, p.decision === "APPROVED" ? p.gate : p.gate - 1); } catch { /* best effort */ } }
    if (p.decision === "APPROVED") out.approved.push({ gate: p.gate, app });
    return out;
  }
  const paths = p.paths.map((x) => cleanPath(root, x));
  if (paths.some((x) => x === null)) { out.notes.push("approve create: every path must be relative, inside the project and without \"..\"."); return out; }
  const ok = paths as string[];
  appendLedger(join(ws, "ledger.jsonl"), { type: "path_approval", paths: ok, decision: "APPROVED", source: "user_prompt", session_id: session, timestamp: new Date().toISOString() });
  safeWrite(join(ws, "approvals.json"), JSON.stringify({ paths: [...new Set([...approvedPaths(root), ...ok])] }, null, 2) + "\n", root, { mode: 0o600 });
  out.done.push(`create ${ok.join(", ")} approved`);
  return out;
}

/** Confirmations only (kept for callers that just want what was recorded). */
export const applyPrompt = (prompt: string, root: string, session = ""): string[] => processPrompt(prompt, root, session).done;

type Spawner = (cmd: string, args: string[], opts: SpawnOptions) => { unref(): void };

const alive = (pid: number): boolean => { try { process.kill(pid, 0); return true; } catch { return false; } };
const answers = (port: number): Promise<boolean> => new Promise((res) => {
  const s = connect({ port, host: "127.0.0.1" });
  const done = (v: boolean) => { s.destroy(); res(v); };
  s.once("connect", () => done(true)); s.once("error", () => done(false)); s.setTimeout(500, () => done(false));
});

/** True when the project's dashboard record names a live pid whose port answers. */
export async function dashboardRunning(root: string): Promise<boolean> {
  try {
    const d = JSON.parse(readFileSync(join(root, ".qe", "dashboard.json"), "utf-8"));
    if (Number.isInteger(d.pid) && Number.isInteger(d.port) && alive(d.pid) && await answers(d.port)) return true;
  } catch { /* no .qe yet: a dashboard started by the start command has only its token record */ }
  return (await dashboardLink(root)) !== null;
}

const realOr = (p: string): string => { try { return realpathSync(p); } catch { return p; } };

/**
 * Where the server keeps its port, pid and access token: one fixed folder per user (the write guard protects it), so the
 * hook, a shell-started --serve and the panel all find the same dashboard, before a run exists as well as after.
 */
export const dashboardTokenFile = (root: string, env = process.env): string => join(homeAnchorDir(env), "dashboards", `${anchorId(realOr(root))}.json`);
/** Where 1.4.2 and older kept it (next to the anchors); still read so a dashboard they started is reused. */
const oldTokenFile = (root: string, env = process.env): string => join(anchorDirFor(root, env), "dashboards", basename(anchorFile(root, env)));

/** The running dashboard's port, pid and token, or null when none answers. */
export async function dashboardRecord(root: string, env = process.env): Promise<{ port: number; pid: number; token: string } | null> {
  for (const f of [dashboardTokenFile(root, env), oldTokenFile(root, env)]) {
    try {
      const d = JSON.parse(readFileSync(f, "utf-8"));
      if (/^[0-9a-f]{64}$/.test(d.token) && Number.isInteger(d.port) && Number.isInteger(d.pid) && alive(d.pid) && await answers(d.port)) return d;
    } catch { /* no record there */ }
  }
  return null;
}

/** Access URL of the running dashboard (token included), or null. Shown to the user only, never to the model. */
export async function dashboardLink(root: string, env = process.env): Promise<string | null> {
  const d = await dashboardRecord(root, env);
  return d ? `http://127.0.0.1:${d.port}/?token=${d.token}` : null;
}

/** Starts the live dashboard in a detached child unless one already runs for this project (it updates itself). Returns true if started. */
export async function ensureDashboard(root: string, app: string | undefined, opts: { spawn?: Spawner; env?: NodeJS.ProcessEnv; open?: boolean } = {}): Promise<boolean> {
  const env = opts.env ?? process.env;
  if (env.AGENTIC_QE_DASHBOARD === "off") return false; // opt-out for CI and test runs
  if (await dashboardRunning(root)) return false;
  const plugin = env.CLAUDE_PLUGIN_ROOT ?? env.PLUGIN_ROOT ?? join(dirname(fileURLToPath(import.meta.url)), "..", "..");
  const script = join(plugin, "skills", "qe-panel", "scripts", "dashboard-server.ts");
  (opts.spawn ?? spawn)(process.execPath, [script, "--root", realRootOf(root), ...(app ? ["--app", app] : []), ...(opts.open ? ["--open"] : [])], { detached: true, stdio: "ignore", cwd: root, windowsHide: true }).unref(); // windowsHide: no console window on Windows
  return true;
}

/** At run completion (Gate 5) writes the read-only HTML snapshot docs/qe/<app>/09-release/dashboard.html in a detached child, so the prompt never waits. */
export function exportSnapshot(root: string, app: string, opts: { spawn?: Spawner; env?: NodeJS.ProcessEnv } = {}): boolean {
  const env = opts.env ?? process.env;
  if (env.AGENTIC_QE_DASHBOARD === "off") return false;
  const plugin = env.CLAUDE_PLUGIN_ROOT ?? env.PLUGIN_ROOT ?? join(dirname(fileURLToPath(import.meta.url)), "..", "..");
  const script = join(plugin, "skills", "qe-panel", "scripts", "dashboard-server.ts");
  (opts.spawn ?? spawn)(process.execPath, [script, "--root", realRootOf(root), "--app", app, "--export"], { detached: true, stdio: "ignore", cwd: root, windowsHide: true }).unref();
  return true;
}

/** `/agentic-qe:qe-start <app> …` (Claude Code) or `$qe-start <app> …` (Codex): the app named, or "" when none is. */
export function startCommandApp(prompt: string): string | null {
  const m = /^\s*(?:\/(?:agentic-qe:)?|\$)qe-start(?:\s+([A-Za-z0-9._-]{1,64}))?(?:\s|$)/.exec(prompt);
  return m ? m[1] ?? "" : null;
}

/** `/agentic-qe:qe-<phase> [app]` or `$qe-<phase> [app]` for a phase after the start, or null. */
export function phaseCommand(prompt: string): { name: string; app: string } | null {
  const m = /^\s*(?:\/(?:agentic-qe:)?|\$)qe-(discover|stories|requirements|plan|design|data|generate|execute|heal|trace|sign|sync)(?:\s+([A-Za-z0-9._-]{1,64}))?(?:\s|$)/.exec(prompt);
  return m ? { name: m[1], app: m[2] ?? "" } : null;
}

/** What the coverage map says the next gate still needs, plus the rule for asking for approval. */
export function phaseBrief(root: string, app: string): string {
  const st = gateStatus(join(root, ".qe"));
  let upTo = -1;
  while (upTo < 5 && st[upTo + 1].status === "APPROVED") upTo++;
  const cov = writeCoverage(root, app, upTo);
  const next = Math.min(5, upTo + 1);
  const inv = cov.inventory;
  let validator = "";
  try { const v = JSON.parse(readFileSync(join(root, "docs", "qe", app, "validation.json"), "utf-8")); if (typeof v.brief === "string") validator = `\n${v.brief}`; } catch { /* not run yet */ }
  return `${handoff(cov, upTo)}\nTests in the repo: ${inv.tests} in ${inv.files} files (existing ${inv.existing}, generated ${inv.generated}, added by hand ${inv.manual}).${validator}\nBefore you ask the user to approve Gate ${next}, run node "<plugin>/skills/tracing-coverage/scripts/check-gate.ts" --gate ${next} --app ${app} and show its output. While it says FAIL, do the missing work; do not ask for approval. Report counts only as that script or panel.ts --json prints them; never state numbers of your own. This command may write only its own phase's documents; the plugin refuses the rest. Never write gate reports, coverage-map, handoff, validation.json, confidence.json or audit.json yourself.`;
}

async function main(): Promise<void> {
  const input: HookInput = readInput();
  if (typeof input.prompt !== "string") return;
  const root = projectRoot(input);
  // the user's start command: start the live dashboard from here and open it in the browser, so nobody runs --serve by hand
  const starting = startCommandApp(input.prompt);
  const phase = phaseCommand(input.prompt);
  // the write window: a phase command opens it for that phase; every other prompt closes it (approve gate 0 opens intake)
  if (existsSync(join(root, ".qe"))) {
    if (starting !== null) openLease(root, "start", starting || runApp(root) || "");
    else if (phase) openLease(root, phase.name, phase.app || runApp(root) || "");
    else if (!/^\s*approve gate 0\b/i.test(input.prompt)) closeLease(root);
  }
  if (starting !== null) {
    let started = false;
    try { started = await ensureDashboard(root, starting || undefined, { open: true }); } catch { /* best effort */ }
    if (process.env.AGENTIC_QE_DASHBOARD === "off") return;
    emitContext("UserPromptSubmit", started
      ? "agentic-qe: the live dashboard is starting and opens in the user's browser; it updates itself. Do not run --serve or --watch."
      : "agentic-qe: the live dashboard already runs for this project and updates itself. Do not run --serve or --watch.");
    return;
  }
  // a phase command: hand the phase the exact open list from the coverage map, so it starts from what is still missing
  if (phase) {
    const app = phase.app || runApp(root);
    if (!app || !existsSync(join(root, ".qe"))) return;
    try { emitContext("UserPromptSubmit", phaseBrief(root, app)); } catch { /* best effort */ }
    return;
  }
  let r: Outcome;
  try { r = processPrompt(input.prompt, root, input.session_id ?? ""); } catch (e) {
    const busy = /lock busy/.test((e as Error).message);
    emitContext("UserPromptSubmit", `agentic-qe could not record the approval (${busy ? "ledger busy" : (e as Error).message}); send the same message again`);
    return;
  }
  const lines: string[] = [];
  if (r.done.length) lines.push(`agentic-qe recorded: ${r.done.join("; ")}`);
  let link: string | null = null;
  if (r.approved.length) {
    let started = false;
    try { started = await ensureDashboard(root, r.approved.find((a) => a.app)?.app, { open: r.approved.some((a) => a.gate === 0) }); } catch { /* the dashboard is best effort */ }
    let app = r.approved.find((a) => a.app)?.app;
    try { app ??= String(JSON.parse(readFileSync(join(root, ".qe", "run.json"), "utf-8")).app ?? ""); } catch { /* no run state */ }
    for (const a of r.approved) {
      let report = "";
      // Markdown gate report next to the gate's documents; loaded only on an approval to keep every other prompt fast
      if (app && /^[A-Za-z0-9._-]{1,64}$/.test(app)) {
        try { report = ` Report: docs/qe/${app}/${(await import("../../skills/building-qe-dashboard/scripts/gate-report-md.ts")).writeGateReport(root, app, a.gate)}`; } catch { /* the report is best effort */ }
      }
      lines.push(`Gate ${a.gate} approved.${report}`);
      if (a.gate === 5 && app && /^[A-Za-z0-9._-]{1,64}$/.test(app)) {
        try { if (exportSnapshot(root, app)) lines.push(`Dashboard snapshot: docs/qe/${app}/09-release/dashboard.html (being written; open it in any browser)`); } catch { /* best effort */ }
      }
    }
    if (r.approved.some((a) => a.gate === 0)) {
      // the intake documents are written after Gate 0: this approval opens the intake window
      if (app) { try { openLease(root, "start", app); } catch { /* best effort */ } }
      lines.push(`Live dashboard ${started ? "starting and opening in the user's browser" : "already running"}; it updates itself and the user has its link. Do not run --serve, and do not repeat the link.`);
      link = await dashboardLink(root); // only if the server already wrote its token; never wait for it
    }
  }
  lines.push(...r.notes);
  if (!lines.length) return;
  if (!link) return emitContext("UserPromptSubmit", lines.join("\n"));
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: lines.join("\n") }, systemMessage: `QE dashboard: ${link}` }));
}

if (isMain(import.meta.url)) await main();
