// Per-case confidence scores from the independent confidence-reviewer agent, and the checks that keep them honest:
// the arithmetic and verdict follow the rubric, and every cited file:line exists in the repository under test.
// A score whose evidence cannot be found is a REJECT, so an invented review cannot pass a weak case (false positives).
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { isInside } from "./hook-common.ts";

export type Kind = "design" | "code";
export type Verdict = "APPROVED" | "REVISE" | "REJECT";

/** Dimension -> maximum points, per reviewed artifact (agents/confidence-reviewer.md). Each rubric sums to 100. */
export const RUBRIC: Record<Kind, Record<string, number>> = {
  design: { source_proven: 30, correct_target: 25, expected_derivable: 25, fixture_validity: 20 },
  code: { compilable: 30, assertion_integrity: 30, import_safety: 20, traceability_present: 20 }
};
/** Below this total a case is low confidence: a pass on it does not count as verified. */
export const THRESHOLD = 70;
/** A test whose assertions score under this proves little however good the rest is (it can pass with the code under test removed), so it is low confidence at any total. */
export const ASSERTION_FLOOR = 20;

export interface Component { file: string; line?: number; symbol?: string }
export interface Flaw { dimension: string; evidence: string; fix: string }
export interface ConfItem { tc_id: string; file?: string; component?: Component; scores: Record<string, number>; total: number; verdict: string; flaws?: Flaw[] }
export interface Checked extends ConfItem {
  /** what is wrong with the record itself (arithmetic, verdict rule, missing flaws) */
  problems: string[];
  /** verified: every cited file:line exists; not-checked: the source is not in this folder; missing: a citation does not exist */
  evidence: "verified" | "not-checked" | "missing";
  /** the verdict after the checks: recomputed from the scores, REJECT when evidence is missing */
  effective: Verdict;
  low: boolean;
  /** why it is low confidence; absent when it is not */
  lowReason?: string;
}

export const verdictFor = (total: number): Verdict => (total === 100 ? "APPROVED" : total >= THRESHOLD ? "REVISE" : "REJECT");
const RANK: Record<Verdict, number> = { APPROVED: 0, REVISE: 1, REJECT: 2 };
const worst = (a: Verdict, b: Verdict): Verdict => (RANK[a] >= RANK[b] ? a : b);

/** "path:line" or "path:line-line" relative to the source root; null when it is not that shape. */
export function parseCite(s: string): { file: string; line: number } | null {
  const m = /^([^:\s][^:]*):(\d+)(?:-\d+)?$/.exec(String(s ?? "").trim());
  return m ? { file: m[1], line: Number(m[2]) } : null;
}

const lineCount = new Map<string, number>();
/** Whether file:line exists inside source (and the file is a regular file of at most 5 MB). */
function citeExists(source: string, file: string, line?: number): boolean {
  const abs = resolve(source, file);
  if (!isInside(resolve(source), abs)) return false;
  try {
    const st = statSync(abs);
    if (!st.isFile() || st.size > 5 * 1024 * 1024) return false;
    if (line === undefined) return true;
    const key = `${abs}:${st.mtimeMs}:${st.size}`; // the dashboard runs for hours: a changed file is read again (AQE141-008)
    let n = lineCount.get(key);
    if (n === undefined) { n = readFileSync(abs, "utf-8").split("\n").length; lineCount.set(key, n); }
    return line >= 1 && line <= n;
  } catch { return false; }
}

/**
 * Checks one review record. `source` is the repository the citations point into; `strict` makes a missing citation a
 * REJECT (a real run), otherwise a folder without the source (an example) reports "not-checked".
 */
export function checkItem(item: ConfItem, kind: Kind, source?: string, strict = true): Checked {
  const rubric = RUBRIC[kind], problems: string[] = [];
  const scores = item?.scores && typeof item.scores === "object" ? item.scores : {};
  let sum = 0;
  for (const [dim, max] of Object.entries(rubric)) {
    const v = scores[dim];
    if (!Number.isInteger(v) || v < 0 || v > max) problems.push(`${dim} must be a whole number from 0 to ${max} (got ${v ?? "nothing"})`);
    else sum += v;
  }
  for (const dim of Object.keys(scores)) if (!(dim in rubric)) problems.push(`unknown dimension ${dim}`);
  if (item.total !== sum) problems.push(`total ${item.total} does not equal the sum of the scores (${sum})`);
  const computed = verdictFor(sum);
  if (item.verdict !== computed) problems.push(`verdict ${item.verdict} does not follow the rule for ${sum} (${computed})`);
  const flaws = Array.isArray(item.flaws) ? item.flaws.filter((f) => f && typeof f === "object") : []; // repository-controlled: a null must not stop the reports (AQE141-005)
  if (computed !== "APPROVED" && !flaws.length) problems.push("a score below 100 must name each flaw with its evidence and fix");
  for (const f of flaws) if (!parseCite(f?.evidence) || !String(f?.fix ?? "").trim()) problems.push(`flaw "${f?.dimension ?? "?"}" needs evidence as path:line and a fix`);
  if (kind === "design" && !item.component?.file) problems.push("the component under test (file, line, symbol) is missing");
  if (kind === "code" && !item.file) problems.push("the test file is missing");

  let evidence: Checked["evidence"] = "not-checked";
  const missing: string[] = [];
  if (source) {
    const cites: { file: string; line?: number }[] = [];
    if (item.component?.file) cites.push({ file: item.component.file, line: Number.isInteger(item.component.line) ? item.component.line : undefined });
    if (kind === "code" && item.file) cites.push({ file: item.file });
    for (const f of flaws) { const c = parseCite(f?.evidence); if (c) cites.push(c); }
    for (const c of cites) if (!citeExists(source, c.file, c.line)) missing.push(c.line ? `${c.file}:${c.line}` : c.file);
    evidence = missing.length ? (strict ? "missing" : "not-checked") : "verified";
    if (missing.length && strict) problems.push(`cited evidence not found in the repository: ${missing.slice(0, 3).join(", ")}${missing.length > 3 ? ` (+${missing.length - 3})` : ""}`);
  }
  const effective = evidence === "missing" ? "REJECT" : worst(computed, problems.some((p) => /component|test file/.test(p)) ? "REJECT" : computed);
  const assertion = kind === "code" ? scores.assertion_integrity : undefined;
  // a record that breaks the rubric proves nothing: omitting a dimension must not skip the rules below (AQE141-004)
  const lowReason = effective === "REJECT" ? "verdict REJECT" : problems.length ? `the review record is invalid: ${problems[0]}` : sum < THRESHOLD ? `total ${sum} is under ${THRESHOLD}` : assertion !== undefined && Number.isInteger(assertion) && assertion < ASSERTION_FLOOR ? `assertion integrity ${assertion}/30 is under ${ASSERTION_FLOOR}: the test may pass without proving the behaviour` : undefined;
  return { ...item, flaws, problems, evidence, effective, low: !!lowReason, ...(lowReason ? { lowReason } : {}) };
}

export interface Summary { kind: Kind; count: number; approved: number; revise: number; reject: number; average: number; low: number; problems: number; evidence: Record<Checked["evidence"], number> }

/** Checks every record of a confidence document ({kind, items}). */
export function checkDoc(doc: unknown, kind: Kind, source?: string, strict = true): { items: Checked[]; summary: Summary } {
  const raw = doc && typeof doc === "object" && Array.isArray((doc as any).items) ? (doc as any).items as ConfItem[] : [];
  const items = raw.filter((x) => x && typeof x.tc_id === "string").map((x) => checkItem(x, kind, source, strict));
  const n = (v: Verdict) => items.filter((i) => i.effective === v).length;
  const ev = { verified: 0, "not-checked": 0, missing: 0 } as Record<Checked["evidence"], number>;
  for (const i of items) ev[i.evidence]++;
  return {
    items,
    summary: { kind, count: items.length, approved: n("APPROVED"), revise: n("REVISE"), reject: n("REJECT"), average: items.length ? Math.round(items.reduce((a, i) => a + (Number(i.total) || 0), 0) / items.length) : 0, low: items.filter((i) => i.low).length, problems: items.filter((i) => i.problems.length).length, evidence: ev }
  };
}

/** True when this folder holds a real run (citations must resolve here); an example or copied run holds only its outputs. */
export const strictSourceFor = (root: string): boolean => existsSync(join(root, ".qe", "run.json"));
