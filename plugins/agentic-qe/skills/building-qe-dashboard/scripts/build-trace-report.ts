// Run data for the live dashboard: reads every phase document of docs/qe/<app>/ (phase folders, or the flat names written
// before 1.4.0), the results/ folder and the ledger, and returns one normalized model: requirements, stories, cases with
// their generated files, RED and final results, healer diagnoses and traceability, plus executions and ledger events.
// Accepts both field-name schemas generators have written (tc_id/caseId, story_id/requirementId, …). Stdlib only.
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { localIso } from "../../../hooks/src/hook-common.ts";
import { userGateRecords, trustOf } from "../../../hooks/src/on-decision.ts";
import { PHASES, DOC_KEYS, findDoc, docRel, readJsonDoc, docItems, normalizeCase, normalizeRequirement, phaseOfPath, type Case, type Requirement } from "../../../hooks/src/layout.ts";
import { parseJUnitXml, caseIdOf } from "../../executing-tests/scripts/parse-junit.ts";
import { checkDoc, strictSourceFor, type Checked, type Summary } from "../../../hooks/src/confidence.ts";

export const MAX_INPUT_BYTES = 5 * 1024 * 1024;
const MAX_LEDGER_ROWS = 500;

export type TraceCase = Case;
export type { Requirement };
export interface Story { id: string; role?: string; action?: string; benefit?: string; acceptance: string[]; priority?: string; text: string }
export interface Run { status: "PASS" | "FAIL" | "SKIPPED"; file: string; message?: string; durationMs?: number }
export interface ExecRun { file: string; label?: string; total: number; passed: number; failed: number; skipped: number; durationMs: number; status: string; failures: { name: string; message: string }[] }
export interface Diagnosis { tc_id: string; classification: string; detail: string; evidence?: string; fix?: string; severity?: string; file?: string }
export interface Doc { name: string; stage: string; kind: "md" | "json" | "csv"; size: number }
export interface TraceInput {
  app: string; mode: string; generatedAt: string; qe: boolean; trust: { trusted: boolean; reason?: string };
  version: string; commit: string; scope: string; frameworks: string[];
  /** document key (layout.ts) -> exists */
  docs: Record<string, boolean>;
  gates: Record<number, { decision: string; timestamp: string }>;
  reports: { gate: number; file: string; created_at?: string }[];
  stories: Story[];
  requirements: Requirement[];
  levels: Record<string, string>;
  cases: TraceCase[];
  fixtures: Set<string>;
  generated: Map<string, string[]>;
  red: Map<string, Run>; runs: Map<string, Run>;
  healer: Map<string, Diagnosis>;
  covered: Map<string, boolean>;
  execRuns: ExecRun[];
  /** per case: the independent reviewer's design and code scores, after the arithmetic and evidence checks */
  confidence: Map<string, { design?: Checked; code?: Checked }>;
  confidenceSummary: { design?: Summary & { stamp?: string }; code?: Summary & { stamp?: string } };
  documents: Doc[];
  ledger: { time: string; kind: string; detail: string }[];
  ledgerTotal: number;
}

export { caseIdOf };

/** Control ID of the functional requirement behind a requirement or story ID: US-CALC-001 -> FR-CALC-001 (FR- kept). */
export const frId = (id: string): string => (/^FR-/i.test(id) ? id : id.replace(/^(US|REQ|R)-/i, "FR-").replace(/^(?!FR-)/, "FR-"));

const readText = (f: string): string | null => {
  try { return statSync(f).isFile() && statSync(f).size <= MAX_INPUT_BYTES ? readFileSync(f, "utf-8") : null; } catch { return null; }
};
export const norm = (id: unknown): string => String(id ?? "").replace(/_/g, "-").toUpperCase();
/** JUnit messages arrive XML-encoded; decode for display (escaped again on output). */
const unxml = (s: unknown): string => String(s ?? "").replace(/&#10;/g, "\n").replace(/&#13;/g, "").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, "&");
const text = (v: unknown): string => (v === undefined || v === null ? "" : typeof v === "string" ? v : typeof v === "object" ? Object.values(v as object).filter((x) => typeof x !== "object").join(" · ") || JSON.stringify(v) : String(v));
const fileOf = (p: string) => p.replace(/^results[\\/]/, "");

/** Reads every phase's output for <app> under <root>. Missing or malformed files are simply absent. */
export function collectTrace(root: string, app: string): TraceInput {
  const docs = join(root, "docs", "qe", app);
  const j = (key: string) => readJsonDoc(findDoc(docs, key));
  const confidence: TraceInput["confidence"] = new Map(), confidenceSummary: TraceInput["confidenceSummary"] = {};
  const strict = strictSourceFor(root);
  for (const [kind, key] of [["design", "design.confidence"], ["code", "generation.confidence"]] as const) {
    const doc = j(key);
    if (!doc) continue;
    const { items, summary } = checkDoc(doc, kind, root, strict);
    confidenceSummary[kind] = { ...summary, stamp: typeof doc.evidence_checked === "string" ? doc.evidence_checked : undefined };
    for (const it of items) { const id = norm(it.tc_id); confidence.set(id, { ...confidence.get(id), [kind]: it }); }
  }
  const design = j("design.cases") ?? {};
  const cases = docItems(design, "cases").map(normalizeCase).filter((c): c is Case => !!c);
  const ids = new Set(cases.map((c) => norm(c.tc_id)));
  const sentence = (s: any) => `As a ${s.role ?? s.actor ?? "?"}, I want to ${s.action ?? "?"}${s.benefit ? ` so that ${s.benefit}` : ""}`;
  const stories: Story[] = docItems(design, "stories").filter((s: any) => s?.id).map((s: any) => ({
    id: String(s.id), role: s.role ?? s.actor, action: s.action, benefit: s.benefit, priority: s.priority,
    acceptance: (Array.isArray(s.acceptance) ? s.acceptance : Array.isArray(s.acceptanceCriteria) ? s.acceptanceCriteria : []).map(text), text: sentence(s)
  }));
  const requirements = docItems(j("requirements.requirements"), "requirements").map(normalizeRequirement).filter((r): r is Requirement => !!r);

  const fixtures = new Set<string>();
  const fx = readText(findDoc(docs, "design.fixtures"));
  if (fx) for (const m of fx.matchAll(/tc[_-][a-z0-9]+[_-]\d{3,}/gi)) fixtures.add(norm(m[0]));

  const generated = new Map<string, string[]>();
  for (const f of docItems(j("generation.manifest"), "files")) {
    const p = typeof f === "string" ? f : String(f?.path ?? "");
    const id = norm((typeof f === "object" && (f?.caseId ?? f?.tc_id)) || caseIdOf(p));
    if (p && ids.has(id)) generated.set(id, [...(generated.get(id) ?? []), p]);
  }

  // results/ at the project root is where qe-execute writes; red-*.xml is the greenfield RED baseline
  const red = new Map<string, Run>(), runs = new Map<string, Run>();
  for (const dir of [join(root, "results"), join(docs, "06-execution", "results"), join(docs, "results")]) {
    let files: string[] = [];
    try { files = readdirSync(dir).filter((f) => f.endsWith(".xml")).sort(); } catch { continue; }
    for (const f of files) {
      const t = readText(join(dir, f));
      if (!t) continue;
      const parsed = parseJUnitXml(t);
      for (const c of parsed.cases) {
        const id = norm(c.caseId);
        if (!ids.has(id)) continue;
        const fail = parsed.failures.find((x) => x.testName === c.testName && x.className === c.className);
        (/^red-/i.test(f) ? red : runs).set(id, { status: c.status, file: f, message: fail ? unxml(fail.failureMessage) : undefined, durationMs: (c as { durationMs?: number }).durationMs });
      }
    }
  }

  const healer = new Map<string, Diagnosis>();
  for (const d of docItems(j("healing.log"), "diagnoses")) {
    const tc = d?.tc_id ?? d?.caseId;
    if (tc) healer.set(norm(tc), { tc_id: String(tc), classification: String(d.classification ?? ""), detail: text(d.root_cause ?? d.rootCause), evidence: text(d.evidence) || undefined, fix: text(d.suggested_app_fix ?? d.suggestedFix ?? d.fix) || undefined, severity: d.severity, file: d.test_file ?? d.testFile });
  }

  const covered = new Map<string, boolean>();
  for (const e of docItems(j("traceability.matrix"), "entries")) for (const id of Array.isArray(e?.testCaseIds) ? e.testCaseIds : []) covered.set(norm(id), !!e.covered);

  const ex = j("execution.summary");
  const execRuns: ExecRun[] = Object.entries(ex?.runs && typeof ex.runs === "object" ? ex.runs : {}).map(([file, r]: [string, any]) => ({
    file: fileOf(file), label: r?.label, total: Number(r?.total ?? 0), passed: Number(r?.passed ?? 0), failed: Number(r?.failed ?? 0), skipped: Number(r?.skipped ?? 0),
    durationMs: Number(r?.durationMs ?? 0), status: String(r?.status ?? ""),
    failures: (Array.isArray(r?.failures) ? r.failures : []).map((x: any) => ({ name: String(x?.testName ?? x?.name ?? ""), message: unxml(x?.failureMessage ?? x?.message ?? "") }))
  }));

  // every phase document that exists, in workflow order
  const documents: Doc[] = [];
  const walk = (dir: string) => {
    let entries: import("node:fs").Dirent[] = [];
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      const p = join(dir, e.name);
      if (e.isDirectory()) { if (!/^(evidence|results|node_modules)$/.test(e.name)) walk(p); continue; }
      if (!/\.(md|json|csv)$/.test(e.name) || /\.meta\.json$/.test(e.name)) continue;
      const rel = relative(docs, p).replace(/\\/g, "/");
      const phase = PHASES.find((x) => x.id === phaseOfPath(rel));
      let size = 0;
      try { size = statSync(p).size; } catch { continue; }
      documents.push({ name: rel, stage: phase?.title ?? "Other", kind: e.name.slice(e.name.lastIndexOf(".") + 1) as Doc["kind"], size });
    }
  };
  walk(docs);

  const ledger: TraceInput["ledger"] = [];
  let ledgerTotal = 0;
  const lt = readText(join(root, ".qe", "ledger.jsonl"));
  if (lt) for (const line of lt.split("\n")) {
    let r: any;
    try { r = JSON.parse(line); } catch { continue; }
    ledgerTotal++;
    const kind = String(r.type ?? r.tool ?? "event");
    const detail = r.type === "gate_decision" ? `Gate ${r.gate} ${r.decision}${r.approver ? ` by ${r.approver}` : ""}`
      : r.type === "run_start" ? `run started for ${r.app} (${r.mode})`
      : r.type === "path_approval" ? `approved create: ${[].concat(r.paths ?? []).join(", ")}`
      : r.type === "doc_edit" ? `edited ${r.file} in the dashboard`
      : String(r.command ?? r.path ?? "");
    ledger.push({ time: String(r.timestamp ?? ""), kind, detail });
  }

  let run: any = {};
  try { run = JSON.parse(readFileSync(join(root, ".qe", "run.json"), "utf-8")); } catch { /* no run state */ }
  const lv = j("plan.plan")?.levels;
  const intake = j("intake.manifest") ?? {};
  const meta = design._meta ?? intake._meta ?? intake.metadata ?? {};
  const fw = intake.frameworks;
  const qe = existsSync(join(root, ".qe"));
  return {
    app, mode: String(run.mode ?? intake.mode ?? meta.mode ?? "unknown"), generatedAt: localIso(),
    qe, trust: qe ? trustOf(root) : { trusted: false, reason: "no .qe/ run state" },
    version: String(meta.created_by ?? "agentic-qe"), commit: String(meta.source_commit ?? intake.sourceCommit ?? "none"),
    scope: text(intake.scope_note ?? intake.scope), frameworks: Array.isArray(fw) ? fw.map(String) : fw && typeof fw === "object" ? Object.values(fw).filter((x) => typeof x === "string") as string[] : [],
    docs: Object.fromEntries(DOC_KEYS.map((k) => [k, existsSync(findDoc(docs, k))])),
    gates: qe ? userGateRecords(join(root, ".qe")) : {}, reports: [], stories, requirements,
    levels: lv && typeof lv === "object" && !Array.isArray(lv) ? Object.fromEntries(Object.entries(lv).map(([k, v]: [string, any]) => [k, v && typeof v === "object" && !Array.isArray(v) && (v.note || v.description || v.scope) ? `${v.skipped === true ? "Skipped: " : ""}${text(v.note ?? v.description ?? v.scope)}` : text(v)])) : {},
    cases, fixtures, generated, red, runs, healer, covered, execRuns, confidence, confidenceSummary, documents,
    ledger: ledger.slice(-MAX_LEDGER_ROWS), ledgerTotal
  };
}

/** Requirement verdict: PASSED only when every linked case ran and passed. */
export type Verdict = "PASSED" | "FAILED" | "PARTLY RUN" | "NOT RUN" | "NO TESTS";
export function verdict(t: TraceInput, cs: TraceCase[]): Verdict {
  if (!cs.length) return "NO TESTS";
  const st = cs.map((c) => t.runs.get(norm(c.tc_id))?.status);
  if (st.includes("FAIL")) return "FAILED";
  if (st.every((s) => s === "PASS")) return "PASSED";
  return st.some((s) => s) ? "PARTLY RUN" : "NOT RUN";
}

/** Case IDs that passed but whose review is low confidence (REJECT or under 70): a pass that proves little, so not counted as verified. */
export function lowConfidencePasses(t: TraceInput): string[] {
  return [...t.runs.entries()].filter(([id, r]) => { const c = t.confidence.get(id); return r.status === "PASS" && (c?.design?.low || c?.code?.low); }).map(([id]) => id);
}

/** Overall run verdict, same rule as the plugin's sign-off: PASS needs at least one executed test, no failures and no low-confidence passes. */
export function overall(t: TraceInput): { verdict: "PASS" | "FAIL" | "INCONCLUSIVE"; reason: string } {
  const st = [...t.runs.values()].map((r) => r.status);
  const failed = st.filter((s) => s === "FAIL").length;
  if (!st.length) return { verdict: "INCONCLUSIVE", reason: "no executed test results yet" };
  if (failed) { const low = lowConfidencePasses(t).length; return { verdict: "FAIL", reason: `${failed} of ${st.length} executed test cases failed${low ? `; ${low} passing case${low === 1 ? "" : "s"} low confidence` : ""}` }; }
  const low = lowConfidencePasses(t).length;
  if (low) return { verdict: "INCONCLUSIVE", reason: `${low} passing test case${low === 1 ? "" : "s"} ha${low === 1 ? "s" : "ve"} low confidence from the independent review, so the pass is not verified` };
  const notRun = t.cases.length - st.length;
  return { verdict: "PASS", reason: `${st.filter((s) => s === "PASS").length} of ${st.length} executed test cases passed${notRun ? `; ${notRun} not run` : ""}` };
}

/** Phase document path relative to docs/qe/<app>/ (re-exported for the dashboard). */
export { docRel };
