import { readFileSync } from "node:fs";
import { isMain } from "../../../hooks/src/hook-common.ts";

export interface TraceabilityEntry {
  requirementId: string;
  testCaseIds: string[];
  covered: boolean;
}

export function buildTraceabilityMatrix(
  requirementIds: string[],
  testCases: { caseId: string; requirementId: string }[]
): { entries: TraceabilityEntry[]; coveragePercent: number; uncoveredCount: number } {
  const entries: TraceabilityEntry[] = requirementIds.map((reqId) => {
    const matchingCases = testCases.filter((tc) => tc.requirementId === reqId).map((tc) => tc.caseId);
    return {
      requirementId: reqId,
      testCaseIds: matchingCases,
      covered: matchingCases.length > 0
    };
  });

  const coveredCount = entries.filter((e) => e.covered).length;
  const coveragePercent = entries.length > 0 ? (coveredCount / entries.length) * 100 : 100;
  const uncoveredCount = entries.length - coveredCount;

  return { entries, coveragePercent, uncoveredCount };
}

// CLI: <requirements.json> <cases.json> <results.json> -> JSON on stdout
// requirements: [{id}|string] ; cases: [{caseId|tc_id, requirementId|story_id}] ; results: [{caseId|tc_id, status}]
if (isMain(import.meta.url)) {
  const [reqFile, caseFile, resFile] = process.argv.slice(2);
  if (!reqFile || !caseFile || !resFile) {
    console.error("usage: node build-matrix.ts <requirements.json> <cases.json> <results.json>");
    process.exit(2);
  }
  type Row = Record<string, string>;
  // Prefer the named key so a combined {stories, cases} file (export-cases input) is read correctly.
  const load = (f: string, key: string): Row[] => {
    const j = JSON.parse(readFileSync(f, "utf-8"));
    if (Array.isArray(j)) return j;
    return Array.isArray(j[key]) ? j[key] : (Object.values(j).find(Array.isArray) as Row[]) ?? [];
  };
  const reqs = load(reqFile, "stories").map((r) => (typeof r === "string" ? r : r.id ?? r.requirementId));
  const cases = load(caseFile, "cases").map((c) => ({ caseId: c.caseId ?? c.tc_id, requirementId: c.requirementId ?? c.story_id }));
  const status = new Map(load(resFile, "results").map((r) => [r.caseId ?? r.tc_id, r.status]));
  const matrix = buildTraceabilityMatrix(reqs, cases);
  const orphanCases = cases.filter((c) => !reqs.includes(c.requirementId)).map((c) => c.caseId);
  const entries = matrix.entries.map((e) => ({ ...e, results: Object.fromEntries(e.testCaseIds.map((id) => [id, status.get(id) ?? "NOT_RUN"])) }));
  console.log(JSON.stringify({ ...matrix, entries, orphanCases }, null, 2));
}
