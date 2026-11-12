// Output layout of a QE run: one folder per phase under docs/qe/<app>/, plus readers that accept every document shape
// the plugin has written (bare arrays, {_meta, …} objects, old flat file names, and both field-name schemas).
import { existsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

/** A phase: its folder, the gate that approves it (if any), and its documents (key -> file name in the folder). */
export interface Phase { id: string; dir: string; title: string; gate?: number; docs: Record<string, string> }

export const PHASES: Phase[] = [
  { id: "intake", dir: "00-intake", title: "Intake", gate: 0, docs: { scope: "scope.md", manifest: "manifest.json" } },
  { id: "discovery", dir: "01-discovery", title: "Discovery", docs: { architecture: "architecture.json", summary: "summary.md" } },
  { id: "requirements", dir: "02-requirements", title: "Requirements and stories", gate: 1, docs: { requirements: "requirements.json", requirementsMd: "requirements.md", stories: "user_stories.md", casesCsv: "test_cases.csv", jiraCsv: "jira_import.csv" } },
  { id: "plan", dir: "03-plan", title: "Plan", gate: 2, docs: { strategy: "strategy.md", plan: "plan.json" } },
  { id: "design", dir: "04-design", title: "Design", gate: 3, docs: { cases: "test_cases.json", casesMd: "test_cases.md", fixtures: "fixtures.json", confidence: "confidence.json" } },
  { id: "generation", dir: "05-generation", title: "Generation", gate: 4, docs: { manifest: "manifest.json", contract: "app_contract.md", confidence: "confidence.json" } },
  { id: "execution", dir: "06-execution", title: "Execution", docs: { summary: "summary.json" } },
  { id: "healing", dir: "07-healing", title: "Healing", docs: { log: "audit_log.json" } },
  { id: "traceability", dir: "08-traceability", title: "Traceability", docs: { matrix: "matrix.json" } },
  { id: "release", dir: "09-release", title: "Release sign-off", gate: 5, docs: { signoff: "signoff.md" } }
];

/** Gate -> the phases it approves (an edit to any of their documents reopens that gate). */
export const GATE_PHASES: Record<number, string[]> = { 0: ["intake"], 1: ["discovery", "requirements"], 2: ["plan"], 3: ["design"], 4: ["generation"], 5: ["execution", "healing", "traceability", "release"] };

/** Flat names written before 1.4.0, read when the phase file does not exist. */
const LEGACY: Record<string, string> = {
  "intake.scope": "00_intake_scope.md", "intake.manifest": "00_intake_manifest.json",
  "discovery.architecture": "01_discovery_architecture.json", "discovery.summary": "01_discovery_summary.md",
  "requirements.requirements": "01_discovery_requirements.json", "requirements.requirementsMd": "01_discovery_requirements.md",
  "requirements.stories": "01_user_stories.md", "requirements.casesCsv": "01_test_cases.csv", "requirements.jiraCsv": "01_jira_import.csv",
  "plan.strategy": "02_planning_test_strategy.md", "plan.plan": "02_planning_test_plan.json",
  "design.cases": "03_design_test_cases.json", "design.casesMd": "03_design_test_cases.md", "design.fixtures": "03_design_test_data_fixtures.json",
  "generation.manifest": "04_generation_manifest.json", "generation.contract": "04_app_contract.md",
  "execution.summary": "05_execution_summary.json", "healing.log": "06_healer_audit_log.json",
  "traceability.matrix": "07_traceability_matrix.json", "release.signoff": "08_release_signoff.md"
};

/**
 * Paths under docs/qe/<app>/ that only the plugin's hooks write: gate reports, the coverage map and hand-off, and the
 * review records captured from the confidence-reviewer and coverage-auditor agents. The write guards refuse the model.
 */
export const HOOK_OWNED = /(^|\/)docs\/qe\/[^/]+\/(coverage-map\.(json|md)|handoff\.md|validation\.json|sessions\/[^/]+|0[0-9]-[a-z-]+\/gate-[0-5]-report\.md|0[45]-(design|generation)\/(confidence|audit)\.json)$/i;

/** Evidence (screenshots, MCP snapshots) and E2E reports of a run live here. */
export const EVIDENCE_DIR = "06-execution/evidence";

const phaseOf = (key: string): { phase: Phase; file: string } => {
  const [pid, doc] = key.split(".");
  const phase = PHASES.find((p) => p.id === pid);
  const file = phase?.docs[doc];
  if (!phase || !file) throw new Error(`unknown document key ${key}`);
  return { phase, file };
};

/** Path of a document relative to docs/qe/<app>/, e.g. docRel("design.cases") = "04-design/test_cases.json". */
export const docRel = (key: string): string => { const { phase, file } = phaseOf(key); return `${phase.dir}/${file}`; };

/** Where to write a document: always the phase folder. */
export const docPath = (appDir: string, key: string): string => join(appDir, docRel(key));

/** Where to read a document: the phase folder, else the pre-1.4.0 flat name, else the phase folder (missing). */
export function findDoc(appDir: string, key: string): string {
  const p = docPath(appDir, key);
  if (existsSync(p)) return p;
  const old = LEGACY[key] && join(appDir, LEGACY[key]);
  return old && existsSync(old) ? old : p;
}

/** Every document key, in workflow order. */
export const DOC_KEYS: string[] = PHASES.flatMap((p) => Object.keys(p.docs).map((d) => `${p.id}.${d}`));

/** Phase id of a path relative to docs/qe/<app>/ ("04-design/x.md" or the old "03_design_test_cases.json"), or null. */
export function phaseOfPath(rel: string): string | null {
  const r = rel.replace(/\\/g, "/");
  const byDir = PHASES.find((p) => r.startsWith(p.dir + "/"));
  if (byDir) return byDir.id;
  const key = Object.entries(LEGACY).find(([, f]) => f === r)?.[0];
  return key ? key.split(".")[0] : null;
}

const MAX_DOC_BYTES = 5 * 1024 * 1024;

/** Parsed JSON document, or null when missing, too large or malformed. */
export function readJsonDoc(file: string): any {
  try {
    if (!statSync(file).isFile() || statSync(file).size > MAX_DOC_BYTES) return null;
    return JSON.parse(readFileSync(file, "utf-8"));
  } catch { return null; }
}

/** The list inside a document: a bare array, obj[key], obj.items or obj.data (the stamp hook wraps arrays in {_meta, items}). */
export function docItems(doc: any, key: string): any[] {
  if (Array.isArray(doc)) return doc;
  if (!doc || typeof doc !== "object") return [];
  for (const k of [key, "items", "data"]) if (Array.isArray(doc[k])) return doc[k];
  return [];
}

const str = (v: unknown): string | undefined => (v === undefined || v === null || v === "" ? undefined : typeof v === "string" ? v : typeof v === "object" ? JSON.stringify(v) : String(v));

/** A test case in one schema, whichever names the generator used (tc_id or caseId, story_id or requirementId, …). */
export interface Case { tc_id: string; story_id?: string; scenario?: string; type?: string; level?: string; priority?: string; steps?: string[]; expected?: string; test_data?: string; precondition?: string; automation?: string; remarks?: string }

export function normalizeCase(c: any): Case | null {
  const tc = str(c?.tc_id ?? c?.caseId ?? c?.case_id ?? c?.id);
  if (!tc) return null;
  const steps = Array.isArray(c.steps) ? c.steps.map(String) : typeof c.steps === "string" ? c.steps.split(/\r?\n|<br\s*\/?>/i).map((s: string) => s.trim()).filter(Boolean) : undefined;
  const auto = c.automation ?? (c.automationCandidate === true ? "Yes" : c.automationCandidate === false ? "No" : c.automationCandidate);
  return {
    tc_id: tc, story_id: str(c.story_id ?? c.requirementId ?? c.storyId ?? c.requirement_id), scenario: str(c.scenario ?? c.title ?? c.name),
    type: str(c.type), level: str(c.level), priority: str(c.priority), steps, expected: str(c.expected ?? c.expectedResult ?? c.expected_result),
    test_data: str(c.test_data ?? c.testData), precondition: str(c.precondition), automation: str(auto), remarks: str(c.remarks)
  };
}

/** A requirement in one schema: id, a readable statement, actor and action when known, evidence as text. */
export interface Requirement { id: string; text: string; title?: string; role?: string; action?: string; evidence?: string; priority?: string; sourceFile?: string; quote?: string }

export function normalizeRequirement(r: any): Requirement | null {
  const id = str(r?.id ?? r?.requirementId);
  if (!id) return null;
  const role = str(r.role ?? r.actor), action = str(r.action);
  // REQUIREMENT_RULES.md names source_file, line_number and quote; extract-contracts.ts uses the camelCase forms
  const sourceFile = str(r.sourceFile ?? r.source_file), line = r.lineNumber ?? r.line_number, quote = str(r.evidenceQuote ?? r.quote);
  const ev = r.evidence ?? (sourceFile ? `${sourceFile}${line ? `:${line}` : ""}${quote ? ` "${quote}"` : ""}` : undefined);
  const text = str(r.text ?? r.statement ?? r.behavior ?? r.description) ?? (role && action ? `As a ${role}, I want to ${action}` : str(r.title) ?? "");
  return { id, text, title: str(r.title), role, action, evidence: typeof ev === "object" && ev ? Object.values(ev).filter(Boolean).join(" · ") : str(ev), priority: str(r.priority), sourceFile, quote };
}
