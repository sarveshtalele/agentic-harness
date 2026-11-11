// Created 2026-11-03 13:00 IST by agentic-qe 1.5.0.
// Coverage map of a QE run: requirement -> plan scenario -> designed case -> generated test -> result, built from the
// documents on disk by code, never by the model, and the check each gate must pass before the hook records an approval.
// Field report (mcp-skills-registry): the plan listed 109 scenarios, 26 cases were designed, test files were marked with
// requirement ids, the manifest used an invented schema, and gates 3 and 4 were approved anyway. Nothing compared them.
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { findDoc, readJsonDoc, docItems, normalizeCase, normalizeRequirement, PHASES, GATE_PHASES } from "./layout.ts";
import { isInside, safeWrite } from "./hook-common.ts";
import { collectTrace, norm } from "../../skills/building-qe-dashboard/scripts/build-trace-report.ts";
import { markersOf, readTestFile, scanTests, summarize, type InventorySummary } from "./inventory.ts";

export const LEVELS = ["Unit", "Integration", "E2E"] as const;
export type Level = (typeof LEVELS)[number];
/** Plan scenario ids: SC-<AREA>-<NNN>, e.g. SC-API-001. */
export const SCENARIO_ID = /^SC-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3,}$/;
/** Agents whose final message the SubagentStop hook records (review-capture.ts). The model never writes these files. */
export const CAPTURED = { confidence: "confidence-reviewer", audit: "coverage-auditor" } as const;

export const levelOf = (v: unknown): Level | null => {
  const s = String(v ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");
  if (/^(unit|component)/.test(s)) return "Unit";
  if (/^(integration|api|service|contract)/.test(s)) return "Integration";
  if (/^(e2e|endtoend|ui|browser|system)/.test(s)) return "E2E";
  return null;
};
const ids = (v: unknown): string[] => (Array.isArray(v) ? v : typeof v === "string" ? v.split(/[\s,]+/) : []).map((x) => String(x).trim()).filter(Boolean);

export interface Scenario { id: string; area: string; level: Level | null; priority?: string; requirementIds: string[]; text: string }
export interface CaseRow { id: string; scenarioIds: string[]; level: Level | null; confidence: boolean; audit?: string; codeConfidence?: boolean; codeAudit?: string; type?: string; text: string }
export interface TestRow { path: string; caseIds: string[]; exists: boolean; markers: string[]; tests: number; assertions: number; level?: string }
export interface Review { id: string; total: number; scores: Record<string, number> }
export interface Coverage {
  app: string;
  requirements: { id: string; priority?: string; evidence: boolean; text: string }[];
  reviews: { design: Review[]; code: Review[] };
  inventory: InventorySummary;
  scenarios: Scenario[];
  skippedLevels: { level: string; reason: string }[];
  declaredScenarios: number | null;
  cases: CaseRow[];
  tests: TestRow[];
  results: Record<string, string>;
  provenance: { design: string | null; code: string | null; designAudit: string | null; codeAudit: string | null };
  problems: string[];
}

/** Who wrote a reviewer or auditor record: the agent type the capture hook stamped, or null (written some other way). */
function capturedBy(doc: any, agent: string): string | null {
  const c = doc && typeof doc === "object" ? doc._capture : null;
  return c && c.agent_type === agent && typeof c.agent_id === "string" && typeof c.sha256 === "string" ? `${agent} ${c.agent_id}` : null;
}

export { markersOf };

export function buildCoverage(root: string, app: string): Coverage {
  const docs = join(root, "docs", "qe", app);
  const j = (key: string) => readJsonDoc(findDoc(docs, key));
  const problems: string[] = [];

  const requirements = docItems(j("requirements.requirements"), "requirements").map((r: any) => {
    const n = normalizeRequirement(r);
    return n ? { id: n.id, priority: n.priority, evidence: !!n.evidence, text: [n.title, n.text, n.action].filter(Boolean).join(" ") } : null;
  }).filter((r): r is NonNullable<typeof r> => !!r);

  const plan = j("plan.plan");
  const rawScenarios = docItems(plan, "scenarios");
  const scenarios: Scenario[] = rawScenarios.map((s: any) => ({
    id: String(s?.id ?? s?.scenarioId ?? ""), area: String(s?.area ?? s?.testArea ?? s?.areaId ?? ""), level: levelOf(s?.level),
    priority: s?.priority ? String(s.priority) : undefined, requirementIds: ids(s?.requirementIds ?? s?.requirements ?? s?.requirementId),
    text: [s?.title, s?.scenario, s?.description, s?.name].filter((x) => typeof x === "string").join(" ")
  }));
  const skippedLevels = (Array.isArray(plan?.skippedLevels) ? plan.skippedLevels : []).map((x: any) => ({ level: String(x?.level ?? ""), reason: String(x?.reason ?? "") }));
  const declared = Number(plan?.totalScenarios ?? plan?.summary?.totalScenarios ?? plan?.summary?.total_scenarios ?? plan?.total_scenarios);
  const declaredScenarios = Number.isFinite(declared) && declared > 0 ? declared : null;

  const design = j("design.cases");
  const rawCases = docItems(design ?? {}, "cases");
  const designConf = j("design.confidence"), codeConf = j("generation.confidence");
  const designAudit = readJsonDoc(join(docs, "04-design", "audit.json")), codeAudit = readJsonDoc(join(docs, "05-generation", "audit.json"));
  // the same reading of the review records the dashboard and the reports use
  let trace: ReturnType<typeof collectTrace> | null = null;
  try { trace = collectTrace(root, app); } catch { /* unreadable documents: no reviews, no results */ }
  const designConfIds = new Set([...(trace?.confidence ?? new Map())].filter(([, k]) => k.design).map(([id]) => id));
  const codeConfIds = new Set([...(trace?.confidence ?? new Map())].filter(([, k]) => k.code).map(([id]) => id));
  const verdicts = (doc: any) => new Map(docItems(doc, "verdicts").map((v: any) => [norm(v?.id ?? v?.tc_id), String(v?.verdict ?? "")]));
  const designVerdicts = verdicts(designAudit), codeVerdicts = verdicts(codeAudit);
  const cases: CaseRow[] = rawCases.map((c: any): CaseRow | null => {
    const n = normalizeCase(c);
    if (!n) return null;
    return {
      id: norm(n.tc_id), scenarioIds: ids(c?.planScenarioIds ?? c?.scenarioIds ?? c?.planScenarioId), level: levelOf(n.level), confidence: designConfIds.has(norm(n.tc_id)), audit: designVerdicts.get(norm(n.tc_id)),
      type: n.type, text: [n.scenario, ...(n.steps ?? []), n.expected, n.precondition].filter(Boolean).join(" ")
    };
  }).filter((c): c is CaseRow => !!c);

  const manifest = j("generation.manifest");
  const tests: TestRow[] = [];
  for (const f of docItems(manifest ?? {}, "files")) {
    const path = String(typeof f === "string" ? f : f?.path ?? "");
    if (!path) continue;
    const abs = resolve(root, path);
    const tf = isInside(root, abs) ? readTestFile(root, abs) : null;
    tests.push({ path: relative(root, abs).replace(/\\/g, "/"), caseIds: ids(typeof f === "object" ? f?.caseIds ?? f?.caseId ?? f?.tc_id : []).map(norm), exists: !!tf, markers: (tf?.markers ?? []).map(norm), tests: tf?.tests ?? 0, assertions: tf?.assertions ?? 0, level: tf?.level });
  }
  if (manifest && !Array.isArray(manifest?.files) && !Array.isArray(manifest?.items) && !Array.isArray(manifest)) problems.push(`05-generation/manifest.json has no "files" list (keys: ${Object.keys(manifest).filter((k) => k !== "_meta").slice(0, 6).join(", ")})`);

  const results: Record<string, string> = Object.fromEntries([...(trace?.runs ?? new Map())].map(([id, r]) => [id, r.status]));

  const provenance = {
    design: capturedBy(designConf, CAPTURED.confidence), code: capturedBy(codeConf, CAPTURED.confidence),
    designAudit: capturedBy(designAudit, CAPTURED.audit), codeAudit: capturedBy(codeAudit, CAPTURED.audit)
  };
  for (const c of cases) { c.codeConfidence = codeConfIds.has(c.id); c.codeAudit = codeVerdicts.get(c.id); }

  // the scores as the reviewer gave them, for the statistical checks (inflation, zero variance)
  const reviewsOf = (doc: any): Review[] => docItems(doc, "items").map((i: any) => ({
    id: norm(i?.tc_id ?? i?.caseId), total: Number(i?.total ?? NaN),
    scores: Object.fromEntries(Object.entries(i?.scores && typeof i.scores === "object" ? i.scores : {}).map(([k, v]) => [k, Number(v)]))
  })).filter((r: Review) => r.id);

  let runStartedMs: number | null = null;
  try { const t = Date.parse(String(JSON.parse(readFileSync(join(root, ".qe", "run.json"), "utf-8")).started_at ?? "")); if (Number.isFinite(t)) runStartedMs = t; } catch { /* no run */ }
  const inventory = summarize(scanTests(root), { caseIds: new Set(cases.map((c) => c.id)), manifest: new Set(tests.map((t) => t.path)), runStartedMs });
  return { app, requirements, reviews: { design: reviewsOf(designConf), code: reviewsOf(codeConf) }, inventory, scenarios, skippedLevels, declaredScenarios, cases, tests, results, provenance, problems };
}

export interface GateCheck { gate: number; ok: boolean; gaps: string[]; missing: string[]; counts: Record<string, number> }

const high = (p?: string) => !p || /^(p0|p1|critical|high)$/i.test(p.trim());

/** What gate N needs before it can be approved. Gate 0 has no coverage rule. */
export function checkGate(cov: Coverage, gate: number, opts: { host?: "claude" | "codex" } = {}): GateCheck {
  const gaps: string[] = [], missing: string[] = [];
  const counts: Record<string, number> = { requirements: cov.requirements.length, scenarios: cov.scenarios.length, cases: cov.cases.length, tests: cov.tests.length, results: Object.keys(cov.results).length };
  const gap = (msg: string, list: string[] = []) => { gaps.push(list.length ? `${msg}: ${list.slice(0, 25).join(", ")}${list.length > 25 ? ` and ${list.length - 25} more` : ""}` : msg); missing.push(...list); };
  // Codex has no subagent stop event to capture a reviewer's output from; there, a record written by the run is accepted
  const needCapture = opts.host !== "codex";

  if (gate >= 1) {
    if (!cov.requirements.length) gap("02-requirements/requirements.json lists no requirements");
    const noEv = cov.requirements.filter((r) => !r.evidence).map((r) => r.id);
    if (noEv.length) gap("requirements without source evidence", noEv);
  }
  if (gate >= 2) {
    if (!cov.scenarios.length) gap('03-plan/plan.json has no "scenarios" list with ids (SC-<AREA>-NNN), so nothing later can be checked against the plan');
    const badId = cov.scenarios.filter((s) => !SCENARIO_ID.test(s.id)).map((s) => s.id || "(no id)");
    if (badId.length) gap("scenario ids not in the form SC-<AREA>-NNN", badId);
    const seen = new Set<string>(), dup = cov.scenarios.map((s) => s.id).filter((id) => (seen.has(id) ? true : (seen.add(id), false)));
    if (dup.length) gap("duplicate scenario ids", [...new Set(dup)]);
    const noLevel = cov.scenarios.filter((s) => !s.level).map((s) => s.id);
    if (noLevel.length) gap("scenarios without a level (Unit, Integration or E2E)", noLevel);
    if (cov.declaredScenarios !== null && cov.declaredScenarios !== cov.scenarios.length) gap(`the plan says ${cov.declaredScenarios} scenarios but lists ${cov.scenarios.length}`);
    for (const l of LEVELS) {
      if (cov.scenarios.length && !cov.scenarios.some((s) => s.level === l) && !cov.skippedLevels.some((x) => levelOf(x.level) === l && x.reason.trim().length >= 10)) gap(`no ${l} scenarios and no written reason in plan.skippedLevels`);
    }
    const covered = new Set(cov.scenarios.flatMap((s) => s.requirementIds));
    const unplanned = cov.requirements.filter((r) => high(r.priority) && !covered.has(r.id)).map((r) => r.id);
    if (cov.scenarios.length && unplanned.length) gap("P0/P1 requirements with no plan scenario", unplanned);
  }
  if (gate >= 3) {
    const designed = new Set(cov.cases.flatMap((c) => c.scenarioIds));
    const undesigned = cov.scenarios.filter((s) => !designed.has(s.id)).map((s) => s.id);
    if (undesigned.length) gap(`plan scenarios with no designed case (${cov.scenarios.length - undesigned.length} of ${cov.scenarios.length} designed)`, undesigned);
    const known = new Set(cov.scenarios.map((s) => s.id));
    const unlinked = cov.cases.filter((c) => !c.scenarioIds.length || c.scenarioIds.some((id) => !known.has(id))).map((c) => c.id);
    if (unlinked.length) gap("cases whose planScenarioIds are missing or not in the plan", unlinked);
    const noConf = cov.cases.filter((c) => !c.confidence).map((c) => c.id);
    if (noConf.length) gap("cases with no confidence review", noConf);
    if (needCapture && cov.cases.length && !cov.provenance.design) gap("04-design/confidence.json was not recorded from the confidence-reviewer agent (run it; the hook records its answer, nobody else may write the file)");
    if (needCapture && cov.cases.length && !cov.provenance.designAudit) gap("04-design/audit.json missing: run the coverage-auditor agent on the design");
    const notCovering = cov.cases.filter((c) => c.audit !== undefined && c.audit !== "COVERS").map((c) => `${c.id} (${c.audit})`);
    if (notCovering.length) gap("cases the coverage auditor says do not cover their scenario", notCovering);
  }
  if (gate >= 4) {
    for (const p of cov.problems) gap(p);
    const markerOf = new Map<string, string[]>();
    for (const t of cov.tests) {
      if (!t.exists) gap(`manifest lists ${t.path}, which does not exist`);
      if (/^docs\//.test(t.path)) gap(`${t.path} is under docs/; generated tests belong in the project's test folders`);
      for (const id of t.markers) markerOf.set(id, [...(markerOf.get(id) ?? []), t.path]);
    }
    const caseIds = new Set(cov.cases.map((c) => c.id));
    const ungenerated = cov.cases.filter((c) => !markerOf.has(c.id)).map((c) => c.id);
    if (ungenerated.length) gap(`designed cases with no test file carrying "CASE_ID: <id>" (${cov.cases.length - ungenerated.length} of ${cov.cases.length} generated)`, ungenerated);
    const foreign = [...markerOf.keys()].filter((id) => !caseIds.has(id));
    if (foreign.length) gap("CASE_ID markers that are not designed case ids (a requirement id is not a case id)", foreign);
    const noCodeConf = cov.cases.filter((c) => markerOf.has(c.id) && !c.codeConfidence).map((c) => c.id);
    if (noCodeConf.length) gap("generated tests with no code confidence review", noCodeConf);
    const codeNotCovering = cov.cases.filter((c) => c.codeAudit !== undefined && c.codeAudit !== "COVERS").map((c) => `${c.id} (${c.codeAudit})`);
    if (codeNotCovering.length) gap("tests the coverage auditor says do not exercise their case", codeNotCovering);
    if (needCapture && cov.tests.length && !cov.provenance.code) gap("05-generation/confidence.json was not recorded from the confidence-reviewer agent");
    if (needCapture && cov.tests.length && !cov.provenance.codeAudit) gap("05-generation/audit.json missing: run the coverage-auditor agent on the generated tests");
  }
  if (gate >= 5) {
    const unrun = cov.cases.filter((c) => !cov.results[c.id]).map((c) => c.id);
    if (unrun.length) gap(`designed cases with no test result (${cov.cases.length - unrun.length} of ${cov.cases.length} executed)`, unrun);
  }
  return { gate, ok: gaps.length === 0, gaps, missing: [...new Set(missing)], counts };
}

/** SC-API-004, SC-API-005, SC-API-006 -> SC-API-004..006: long id lists become short, for Claude's context. */
export function idRanges(list: string[]): string[] {
  const groups = new Map<string, { n: number; w: number }[]>(), plain: string[] = [];
  for (const id of [...new Set(list)].sort()) {
    const m = /^(.*?)(\d+)$/.exec(id);
    if (!m) { plain.push(id); continue; }
    groups.set(m[1], [...(groups.get(m[1]) ?? []), { n: Number(m[2]), w: m[2].length }]);
  }
  const out = [...plain];
  for (const [prefix, nums] of groups) {
    nums.sort((a, b) => a.n - b.n);
    const fmt = (x: { n: number; w: number }) => `${prefix}${String(x.n).padStart(x.w, "0")}`;
    let start = nums[0], prev = nums[0];
    for (const x of [...nums.slice(1), null]) {
      if (x && x.n === prev.n + 1) { prev = x; continue; }
      out.push(start === prev ? fmt(start) : `${fmt(start)}..${String(prev.n).padStart(prev.w, "0")}`);
      if (x) start = prev = x;
    }
  }
  return out.sort();
}

/** The work the next phase must do, in one short paragraph the hooks put in Claude's context. */
export function handoff(cov: Coverage, approvedUpTo: number): string {
  const next = Math.min(5, approvedUpTo + 1);
  const c = checkGate(cov, next);
  const head = `agentic-qe coverage for ${cov.app}: ${cov.requirements.length} requirements, ${cov.scenarios.length} plan scenarios, ${cov.cases.length} designed cases, ${cov.tests.length} test files, ${Object.keys(cov.results).length} results.`;
  if (c.ok) return `${head} Gate ${next} check passes.`;
  // the full open list, not the 25-item summary, as ranges (SC-API-004..025) so it stays short
  const all = c.missing.length ? `\nEvery open id (${c.missing.length}): ${idRanges(c.missing).join(", ")}` : "";
  return `${head} Gate ${next} will refuse approval until these are done (docs/qe/${cov.app}/coverage-map.md lists them all):\n- ${c.gaps.join("\n- ")}${all}`.slice(0, 12000);
}

/** Writes docs/qe/<app>/coverage-map.json and coverage-map.md (hook-owned: the model may not edit them). */
export function writeCoverage(root: string, app: string, approvedUpTo: number): Coverage {
  const cov = buildCoverage(root, app);
  const checks = [1, 2, 3, 4, 5].map((g) => checkGate(cov, g));
  const docs = join(root, "docs", "qe", app);
  if (!existsSync(docs)) return cov;
  const rows = cov.scenarios.map((s) => {
    const cs = cov.cases.filter((c) => c.scenarioIds.includes(s.id));
    const tests = cs.filter((c) => cov.tests.some((t) => t.markers.includes(c.id)));
    return `| ${s.id} | ${s.area} | ${s.level ?? "?"} | ${s.requirementIds.join(", ")} | ${cs.map((c) => c.id).join(", ") || "**none**"} | ${tests.length}/${cs.length} | ${cs.map((c) => cov.results[c.id] ?? "-").join(", ") || "-"} |`;
  });
  const md = [
    `# Coverage map: ${app}`, "",
    "Written by the plugin's hooks from the documents on disk. Do not edit it: it is rebuilt after every change and checked at every gate.", "",
    "| Gate | Check | Gaps |", "|---|---|---|",
    ...checks.map((c) => `| ${c.gate} | ${c.ok ? "PASS" : "FAIL"} | ${c.gaps.length ? c.gaps.map((g) => g.replace(/\|/g, "\\|")).join("<br>") : "-"} |`), "",
    `Requirements ${cov.requirements.length} · plan scenarios ${cov.scenarios.length}${cov.declaredScenarios !== null ? ` (plan says ${cov.declaredScenarios})` : ""} · designed cases ${cov.cases.length} · test files ${cov.tests.length} · results ${Object.keys(cov.results).length}`, "",
    "| Scenario | Area | Level | Requirements | Cases | Tests | Results |", "|---|---|---|---|---|---|---|", ...rows, ""
  ].join("\n");
  // written only when the content changes, so a watching dashboard is not woken by every tool call
  const same = (p: string, body: string) => { try { return readFileSync(p, "utf-8") === body; } catch { return false; } };
  for (const [name, body] of [["coverage-map.md", md], ["coverage-map.json", JSON.stringify({ app, approvedUpTo, checks, coverage: cov }, null, 1) + "\n"], ["handoff.md", `# Next phase: ${app}\n\n${handoff(cov, approvedUpTo)}\n`]] as const) {
    if (!same(join(docs, name), body)) safeWrite(join(docs, name), body, root);
  }
  return cov;
}

export { HOOK_OWNED } from "./layout.ts";

/** Phase folders a gate approves, for the edit-after-approval fingerprint. */
export const gateDirs = (gate: number): string[] => (GATE_PHASES[gate] ?? []).map((id) => PHASES.find((p) => p.id === id)?.dir).filter((d): d is string => !!d);
