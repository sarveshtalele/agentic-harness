import { existsSync, readFileSync, readdirSync, watch, statSync, type FSWatcher } from "node:fs";
import { join, resolve } from "node:path";
import { isMain } from "../../../hooks/src/hook-common.ts";
import * as memoryLogger from "../../../hooks/src/memory-logger.ts";
import { userGateDecisions } from "../../../hooks/src/on-decision.ts";
import { parseJUnitXml } from "../../../scripts/parse-junit.ts";
import { findDoc } from "../../../hooks/src/layout.ts";
import { dashboardTokenFile } from "../../../hooks/src/approval-hook.ts";

export type Counts = { passed: number; failed: number; total: number };
export interface PhaseState { id: string; label: string; done: boolean; active: boolean; outOfOrder: boolean }
export interface PanelState {
  app: string | null;
  mode: string | null;
  startedAt: string | null;
  hasRun: boolean;
  phases: PhaseState[];
  active: string | null;
  gates: ("approved" | "rejected" | "pending")[];
  /** live dashboard URL, while its server runs */
  dashboard: string | null;
  levels: Record<"unit" | "integration" | "e2e" | "other", Counts>;
  blockers: string[];
  last: { type: string; ts: string | null } | null;
  ledger: { ok: boolean; reason?: string };
  next: string;
  now: number;
}

// req: always required; "greenfield" only for new projects; "data" optional (never blocks the chain); "heal" required only when tests fail.
const PHASES: { id: string; label: string; /** layout.ts document keys */ file: string[]; req: "yes" | "greenfield" | "optional" | "heal" }[] = [
  { id: "start", label: "Start", file: ["intake.scope"], req: "yes" },
  { id: "discover", label: "Discover", file: ["discovery.architecture"], req: "yes" },
  { id: "stories", label: "Stories", file: ["requirements.stories"], req: "greenfield" },
  { id: "requirements", label: "Requirements", file: ["requirements.requirements"], req: "yes" },
  { id: "plan", label: "Plan", file: ["plan.plan"], req: "yes" },
  { id: "design", label: "Design", file: ["design.cases"], req: "yes" },
  { id: "data", label: "Data", file: ["design.fixtures"], req: "optional" },
  { id: "generate", label: "Generate", file: ["generation.manifest"], req: "yes" },
  { id: "execute", label: "Execute", file: ["execution.summary"], req: "yes" },
  { id: "heal", label: "Heal", file: ["healing.log"], req: "heal" },
  { id: "trace", label: "Trace", file: ["traceability.matrix"], req: "yes" },
  { id: "sign", label: "Sign-off", file: ["release.signoff"], req: "yes" },
];
const GATE_NAMES = ["Intake", "Requirements", "Plan", "Design", "Generate", "Release"];
const NGATES = GATE_NAMES.length;

/** Strips ANSI/OSC sequences and control characters from untrusted text (terminal-injection defence). */
export function clean(v: unknown): string {
  return String(v ?? "")
    .replace(/\x1b\][^\x07\x1b]*(\x07|\x1b\\)?/g, "")
    .replace(/\x1b\[[0-9;?]*[ -/]*[@-~]/g, "")
    .replace(/[\x00-\x1f\x7f-\x9f]/g, "");
}

function readJson(p: string): any {
  try { return JSON.parse(readFileSync(p, "utf-8")); } catch { return null; }
}

export function collectState(root: string, appArg?: string): PanelState {
  const now = Date.now();
  const qe = join(root, ".qe");
  const run = readJson(join(qe, "run.json"));
  const app: string | null = clean(appArg || run?.app || "").trim() || null;
  const safeApp = app && /^[A-Za-z0-9._-]{1,64}$/.test(app) ? app : null;
  const docs = safeApp ? join(root, "docs", "qe", safeApp) : null;
  const has = (key: string) => !!docs && existsSync(findDoc(docs, key));
  const mode = run?.mode ? clean(run.mode) : null;

  // test counts per level from results/*.xml
  const levels: PanelState["levels"] = { unit: z(), integration: z(), e2e: z(), other: z() };
  const failedNames: string[] = [];
  const rdir = join(root, "results");
  if (existsSync(rdir)) {
    for (const f of readdirSync(rdir).filter((x) => x.endsWith(".xml")).sort()) {
      try {
        const r = parseJUnitXml(readFileSync(join(rdir, f), "utf-8"));
        const k = f.startsWith("unit-") ? "unit" : f.startsWith("integration-") ? "integration" : f.startsWith("e2e-") ? "e2e" : "other";
        levels[k].passed += r.passed; levels[k].failed += r.failed; levels[k].total += r.total;
        if (k !== "other") for (const x of r.failures.slice(0, 3)) failedNames.push(clean(x.testName));
      } catch { /* unreadable xml */ }
    }
  }
  // ponytail: "other" (e.g. red-/green- TDD runs) is informational, never a blocker
  const totalFailed = levels.unit.failed + levels.integration.failed + levels.e2e.failed;

  // phases: derived strictly in order; a phase is done only if its artifact exists AND every earlier required phase is done
  const greenfield = mode !== "brownfield";
  const executed = has("execution.summary") || levels.unit.total + levels.integration.total + levels.e2e.total > 0 ||
    (existsSync(rdir) && readdirSync(rdir).some((f) => /^(unit|integration|e2e)-.*\.xml$/.test(f)));
  const list = PHASES.filter((p) =>
    p.req === "greenfield" ? greenfield :
    p.req === "optional" ? has(p.file[0]) :
    p.req === "heal" ? totalFailed > 0 || has(p.file[0]) : true);
  let chainOk = true;
  let activeSet = false;
  const phases: PhaseState[] = list.map((p) => {
    const exists = p.id === "execute" ? executed : p.file.some(has);
    const required = p.req !== "optional";
    const done = exists && (!required || chainOk);
    const outOfOrder = exists && !done;
    const active = required && !done && !activeSet;
    if (active) activeSet = true;
    if (required && !done) chainOk = false;
    return { id: p.id, label: p.label, done, active, outOfOrder };
  });
  const active = phases.find((p) => p.active)?.id ?? null;

  // ledger + gates: an untrusted ledger (tampered, truncated, or no local anchor) leaves every gate pending
  const ledgerPath = join(qe, "ledger.jsonl");
  let ledger: PanelState["ledger"] = { ok: true };
  let gates: PanelState["gates"] = Array(NGATES).fill("pending");
  let last: PanelState["last"] = null;
  if (existsSync(ledgerPath)) {
    try {
      // ledgerTrust is exported by the hooks; fall back to verifyLedger if running against an older hooks tree
      const t = (memoryLogger as any).ledgerTrust ? (memoryLogger as any).ledgerTrust(root) : (() => { const v = memoryLogger.verifyLedger(ledgerPath); return { trusted: v.ok, reason: v.ok ? "verified" : v.reason ?? `broken at record ${v.brokenAt ?? "?"}` }; })();
      ledger = { ok: !!t.trusted, reason: clean(t.reason) };
    } catch { ledger = { ok: false, reason: "unreadable" }; }
    try {
      if (ledger.ok) {
        const d = userGateDecisions(qe);
        gates = gates.map((_, i) => (d[i] === "APPROVED" ? "approved" : d[i] === "REJECTED" ? "rejected" : "pending"));
      }
      const lines = readFileSync(ledgerPath, "utf-8").split("\n").filter(Boolean);
      const r = JSON.parse(lines[lines.length - 1]);
      last = { type: clean(r.type ?? "?"), ts: r.timestamp ? clean(r.timestamp) : null };
    } catch { /* partial ledger */ }
  }
  else { // .qe/ or its ledger gone: trust says "run state missing" when a run was started here
    try { const t = memoryLogger.ledgerTrust(root); if (!t.trusted) ledger = { ok: false, reason: clean(t.reason) }; } catch { /* leave ok */ }
  }

  // live dashboard: the server's record (one per user, so a dashboard started before the run is found too), else
  // .qe/dashboard.json from older servers; shown only while that process is alive, never with its token
  let dashboard: string | null = null;
  for (const dj of [readJson(dashboardTokenFile(root)), readJson(join(qe, "dashboard.json"))]) {
    if (dashboard || !Number.isInteger(dj?.port) || !Number.isInteger(dj?.pid)) continue;
    try { process.kill(dj.pid, 0); dashboard = `http://127.0.0.1:${dj.port}/`; } catch { /* server gone */ }
  }

  // blockers
  const blockers: string[] = [];
  if (!ledger.ok) blockers.push(`Ledger UNTRUSTED (${ledger.reason ?? "unknown"}): gates treated as pending`);
  if (totalFailed) blockers.push(`${totalFailed} failing test(s)${failedNames.length ? `: ${failedNames.join(", ")}` : ""}`);
  gates.forEach((g, i) => { if (g === "rejected") blockers.push(`Gate ${i} (${GATE_NAMES[i]}) rejected`); });
  const done = (id: string) => phases.find((p) => p.id === id)?.done;
  const pend = (g: number, ph: string) => { if (done(ph) && gates[g] === "pending") blockers.push(`Gate ${g} (${GATE_NAMES[g]}) pending approval`); };
  pend(0, "start"); pend(1, "requirements"); pend(2, "plan"); pend(3, "design"); pend(4, "generate"); pend(5, "sign");
  phases.filter((p) => p.outOfOrder).forEach((p) => blockers.push(`${p.label} exists but an earlier phase is not done (out of order)`));
  if (done("execute")) for (const k of ["unit", "integration", "e2e"] as const) if (!levels[k].total) blockers.push(`No ${k === "e2e" ? "E2E" : k[0].toUpperCase() + k.slice(1)} results`);

  // Claude Code lists plugin commands namespaced, so print exactly what the user types
  const next = !run && !docs ? "/agentic-qe:qe-start <app>" : active ? `/agentic-qe:qe-${active} ${safeApp ?? "<app>"}` : "all phases complete";
  return { app, mode, startedAt: run?.started_at ? clean(run.started_at) : null, hasRun: !!run || (!!docs && existsSync(docs)), phases, active, gates, dashboard, levels, blockers, last, ledger, next, now };
}
function z(): Counts { return { passed: 0, failed: 0, total: 0 }; }

export function relTime(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
  return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`;
}

const cut = (s: string, n: number) => (s.length <= n ? s : n <= 1 ? "…".slice(0, n) : s.slice(0, n - 1) + "…");

export function renderPanel(st: PanelState, opts: { width?: number; color?: boolean } = {}): string {
  const width = Math.min(120, Math.max(40, Math.floor(opts.width ?? 80)));
  const inner = width - 4;
  const paint = (code: string, s: string) => (opts.color ? `\x1b[${code}m${s}\x1b[0m` : s);
  const out: string[] = [];
  const row = (plain: string, code = "") => {
    const t = cut(clean(plain), inner);
    out.push("│ " + (code ? paint(code, t) : t) + " ".repeat(inner - t.length) + " │");
  };
  const rule = (l: string, r: string, title = "") => {
    const t = title ? ` ${cut(title, inner - 2)} ` : "";
    out.push(l + t + "─".repeat(width - 2 - t.length) + r);
  };
  rule("┌", "┐");
  row("AGENTIC QE — LIVE PANEL", "1;36");
  if (!st.hasRun) {
    rule("├", "┤");
    row("No QE run yet — start with /agentic-qe:qe-start <app>", "33");
    rule("└", "┘");
    return out.join("\n");
  }
  const el = st.startedAt && !isNaN(Date.parse(st.startedAt)) ? relTime(st.now - Date.parse(st.startedAt)) : "n/a";
  row(`App: ${st.app ?? "?"}   Mode: ${st.mode ?? "?"}   Elapsed: ${el}`);
  rule("├", "┤", "Phases");
  const cells = st.phases.map((p) => (p.done ? "✔ " : p.outOfOrder ? "◐ " : p.active ? "▶ " : "○ ") + p.label);
  const colW = Math.max(...cells.map((c) => c.length)) + 2;
  const perRow = Math.max(1, Math.floor(inner / colW));
  for (let i = 0; i < cells.length; i += perRow) {
    const chunk = st.phases.slice(i, i + perRow);
    // colour per cell: build plain line, colour the whole row by its dominant state
    const line = cells.slice(i, i + perRow).map((c) => c.padEnd(colW)).join("");
    row(line, chunk.some((p) => p.active) ? "33" : chunk.every((p) => p.done) ? "32" : "2");
  }
  row("✔ done  ▶ next  ◐ out of order  ○ pending", "2");
  rule("├", "┤", "Gates");
  row(st.gates.map((g, i) => `${i}${g === "approved" ? "✔" : g === "rejected" ? "✘" : "○"}`).join("  ") + "   (✔ approved ○ pending ✘ rejected)", "");
  rule("├", "┤", "Tests");
  const names: [keyof PanelState["levels"], string][] = [["unit", "Unit"], ["integration", "Integration"], ["e2e", "E2E"]];
  if (st.levels.other.total) names.push(["other", "Other"]);
  const barW = Math.max(6, Math.min(24, inner - 36));
  for (const [k, n] of names) {
    const c = st.levels[k];
    const fill = c.total ? Math.round((c.passed / c.total) * barW) : 0;
    const bar = "█".repeat(fill) + "░".repeat(barW - fill);
    row(`${n.padEnd(12)} ${bar} ${c.passed}/${c.failed}/${c.total}`.replace(/$/, c.total ? "" : " –"), c.failed ? "31" : c.total ? "32" : "2");
  }
  row("(passed/failed/total)", "2");
  rule("├", "┤", "Blockers");
  if (!st.blockers.length) row("none", "32");
  for (const b of st.blockers.slice(0, 6)) row("• " + b, "31");
  rule("├", "┤");
  row("Last: " + (st.last ? `${st.last.type}${st.last.ts && !isNaN(Date.parse(st.last.ts)) ? ` (${relTime(st.now - Date.parse(st.last.ts))} ago)` : ""}` : "no ledger activity") );
  row(`Ledger: ${st.ledger.ok ? "trusted" : `UNTRUSTED (${st.ledger.reason ?? "unknown"})`}`, st.ledger.ok ? "" : "31");
  row("Dashboard: " + (st.dashboard ?? "not running (/agentic-qe:qe-panel --serve)"), "");
  row(`Next: ${st.next}`, "1");
  if (st.active) row(`Codex: $qe-${st.active} ${st.app ?? "<app>"}`, "2");
  rule("└", "┘");
  return out.join("\n");
}

/** Auto-detect the single app under docs/qe when nothing else names it. */
function detectApp(root: string): string | undefined {
  try {
    const d = join(root, "docs", "qe");
    const apps = readdirSync(d).filter((n) => statSync(join(d, n)).isDirectory());
    return apps.length === 1 ? apps[0] : undefined;
  } catch { return undefined; }
}

function parseArgs(argv: string[]) {
  const a: { app?: string; root?: string; watch: boolean; width?: number; color: boolean; json?: boolean } = { watch: false, color: true };
  for (let i = 0; i < argv.length; i++) {
    const v = argv[i];
    if (v === "--app") a.app = argv[++i];
    else if (v === "--root") a.root = argv[++i];
    else if (v === "--width") a.width = Number(argv[++i]);
    else if (v === "--json") a.json = true;
    else if (v === "--watch") a.watch = true;
    else if (v === "--once") a.watch = false;
    else if (v === "--no-color") a.color = false;
  }
  return a;
}

/** What the pane beside the transcript draws: the panel state plus one tile per case. Facts from disk only; missing facts stay missing. */
/** Apps that have a docs/qe/<app> folder, for the pane's app switcher. */
function listApps(root: string): string[] {
  try { const d = join(root, "docs", "qe"); return readdirSync(d).filter((n) => /^[A-Za-z0-9._-]{1,64}$/.test(n) && statSync(join(d, n)).isDirectory()).sort(); } catch { return []; }
}

/** What the pane beside the transcript draws: the panel state plus one tile per case. Facts from disk only; missing facts stay missing. */
export async function paneData(root: string, appArg?: string) {
  let st = collectState(root, appArg);
  if (!st.app) { const d = detectApp(root); if (d) st = collectState(root, d); }
  const app = st.app && /^[A-Za-z0-9._-]{1,64}$/.test(st.app) ? st.app : null;
  const apps = listApps(root);
  // first gate whose phase is done and that still waits for the typed phrase
  const GATE_PHASE = ["start", "requirements", "plan", "design", "generate", "sign"];
  const g = st.gates.findIndex((x, i) => x !== "approved" && st.phases.some((p) => p.id === GATE_PHASE[i] && p.done));
  const approval = g < 0 ? null : g === 0 ? `approve gate 0 for ${app ?? "<app>"}` : `approve gate ${g}`;
  const reject = g < 0 ? null : `reject gate ${g}`;
  if (!app) return { ...st, apps, approval, reject, pendingGate: g < 0 ? null : g, gateReport: null, cases: [], low: 0, confidence: null };
  const { gateReportRel } = await import("../../building-qe-dashboard/scripts/gate-report-md.ts");
  const report = g < 0 ? null : `docs/qe/${app}/${gateReportRel(g)}`;
  const { collectTrace, norm } = await import("../../building-qe-dashboard/scripts/build-trace-report.ts");
  const t = collectTrace(root, app);
  const cases = t.cases.map((c) => { const id = norm(c.tc_id), k = t.confidence.get(id); return { id: c.tc_id, level: c.level ?? "Other", status: t.runs.get(id)?.status ?? "NOT RUN", low: !!(k?.design?.low || k?.code?.low) }; });
  // coverage of the next gate, from the same check the approval hook runs
  let coverage: { gate: number; ok: boolean; gaps: string[]; more: number; counts: Record<string, number> } | null = null;
  let inventory: { files: number; tests: number; existing: number; generated: number; manual: number; byLevel: Record<string, number> } | null = null;
  let toGenerate = 0;
  try {
    const { buildCoverage, checkGate } = await import("../../../hooks/src/coverage.ts");
    const cov = buildCoverage(root, app);
    inventory = cov.inventory;
    const marked = new Set(cov.tests.flatMap((x) => x.markers));
    toGenerate = cov.cases.filter((c) => !marked.has(c.id)).length;
    const next = st.gates.findIndex((x) => x !== "approved");
    if (next >= 1) { const c = checkGate(cov, next); coverage = { gate: next, ok: c.ok, gaps: c.gaps.slice(0, 4), more: Math.max(0, c.gaps.length - 4), counts: c.counts }; }
  } catch { /* no coverage yet */ }
  // the validator's last verdict (written by the approval hook and check-gate.ts)
  let validation: { gate: number; ok: boolean; errors: number; warnings: number; first?: string; error?: string } | null = null;
  try {
    const v = JSON.parse(readFileSync(join(root, "docs", "qe", app, "validation.json"), "utf-8"));
    validation = { gate: Number(v.gate), ok: !!v.ok, errors: (v.errors ?? []).length, warnings: (v.warnings ?? []).length, first: v.errors?.[0]?.message, error: v.error };
  } catch { /* not run yet */ }
  let version = "";
  try { version = String(JSON.parse(readFileSync(join(import.meta.dirname, "..", "..", "..", ".claude-plugin", "plugin.json"), "utf-8")).version ?? ""); } catch { /* unknown */ }
  return { ...st, apps, approval, reject, pendingGate: g < 0 ? null : g, gateReport: report && existsSync(join(root, report)) ? report : null, cases, low: cases.filter((c) => c.low).length, confidence: t.confidenceSummary.design?.average ?? t.confidenceSummary.code?.average ?? null, coverage, inventory, toGenerate, validation, version };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = resolve(args.root || process.env.CLAUDE_PROJECT_DIR || process.cwd());
  const color = args.color && !process.env.NO_COLOR && (args.watch || !!process.stdout.isTTY);
  const frame = () => {
    const app = args.app || undefined;
    let st = collectState(root, app);
    if (!st.app) { const d = detectApp(root); if (d) st = collectState(root, d); }
    return renderPanel(st, { width: args.width || process.stdout.columns || 80, color });
  };
  if (args.json) { console.log(JSON.stringify(await paneData(root, args.app || undefined))); return; }
  if (!args.watch) { console.log(frame()); return; }

  const out = process.stdout;
  let timer: NodeJS.Timeout | undefined;
  const draw = () => out.write("\x1b[H\x1b[J" + frame() + "\n");
  const restore = () => { out.write("\x1b[?25h\x1b[?1049l"); };
  out.write("\x1b[?1049h\x1b[?25l");
  let done = false;
  const quit = () => { if (done) return; done = true; restore(); process.exit(0); };
  process.on("SIGINT", quit); process.on("SIGTERM", quit); process.on("exit", () => { if (!done) restore(); });
  const kick = () => { clearTimeout(timer); timer = setTimeout(draw, 250); };
  const watchers: FSWatcher[] = [];
  const app = args.app || collectState(root).app || detectApp(root);
  for (const d of [join(root, ".qe"), app ? join(root, "docs", "qe", app) : "", join(root, "results")]) {
    if (!d || !existsSync(d)) continue;
    try { watchers.push(watch(d, { recursive: true }, kick)); } catch { try { watchers.push(watch(d, kick)); } catch { /* poll covers it */ } }
  }
  out.on("resize", draw);
  setInterval(draw, 2000);
  draw();
}

if (isMain(import.meta.url)) main();
