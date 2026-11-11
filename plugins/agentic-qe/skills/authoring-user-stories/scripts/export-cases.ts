import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { isMain, projectRoot, safeWrite } from "../../../hooks/src/hook-common.ts";
import { stampFile } from "../../../hooks/src/stamp-metadata.ts";

export interface Story { id: string; role: string; action: string; benefit: string; acceptance: string[]; priority: string }
export interface Case {
  tc_id: string; story_id: string; scenario: string; type: string; precondition: string; test_data: string;
  steps: string[]; expected: string; priority: string; automation: string; remarks: string;
  /** Optional test level; kept in JSON only (not a CSV/MD column). */
  level?: string;
}
export interface CasesFile { app: string; stories: Story[]; cases: Case[] }

export const TYPES = ["Positive", "Negative", "Negative (Boundary)", "Exception"];
export const LEVELS = ["Unit", "Integration", "E2E"];
export const COLUMNS = ["TC ID", "User Story ID", "Scenario", "Type", "Precondition", "Test Data", "Steps", "Expected Result", "Priority", "Automation Candidate", "Remarks"];
const PRIORITIES = ["P1", "P2", "P3"];
const STORY_FIELDS: (keyof Story)[] = ["id", "role", "action", "benefit", "acceptance", "priority"];
const CASE_FIELDS: (keyof Case)[] = ["tc_id", "story_id", "scenario", "type", "precondition", "test_data", "steps", "expected", "priority", "automation", "remarks"];
const OPTIONAL = new Set(["remarks", "precondition", "test_data"]);

const missing = (v: unknown) => v === undefined || v === null || (typeof v === "string" ? v.trim() === "" : Array.isArray(v) && v.length === 0);

/** Returns a list of specific error strings; empty means valid. */
export function validateCases(data: CasesFile): string[] {
  const errors: string[] = [];
  if (!data || missing(data.app)) errors.push("missing required field: app");
  if (!Array.isArray(data?.stories) || !data.stories.length) errors.push("stories must be a non-empty array");
  if (!Array.isArray(data?.cases) || !data.cases.length) errors.push("cases must be a non-empty array");
  if (errors.length) return errors;

  const ids = new Set<string>();
  data.stories.forEach((s, i) => {
    for (const f of STORY_FIELDS) if (missing(s[f])) errors.push(`story[${i}] (${s.id ?? "?"}): missing required field '${f}'`);
    if (s.priority && !PRIORITIES.includes(s.priority)) errors.push(`story ${s.id}: priority '${s.priority}' must be P1, P2 or P3`);
    ids.add(s.id);
  });
  data.cases.forEach((c, i) => {
    for (const f of CASE_FIELDS) if (!OPTIONAL.has(f) && missing(c[f])) errors.push(`case[${i}] (${c.tc_id ?? "?"}): missing required field '${f}'`);
    if (c.type && !TYPES.includes(c.type)) errors.push(`case ${c.tc_id}: type '${c.type}' must be one of ${TYPES.join(", ")}`);
    if (c.level !== undefined && !LEVELS.includes(c.level)) errors.push(`case ${c.tc_id}: level '${c.level}' must be one of ${LEVELS.join(", ")}`);
    if (c.priority && !PRIORITIES.includes(c.priority)) errors.push(`case ${c.tc_id}: priority '${c.priority}' must be P1, P2 or P3`);
    if (c.story_id && !ids.has(c.story_id)) errors.push(`case ${c.tc_id}: story_id '${c.story_id}' does not match any story`);
  });
  for (const s of data.stories) {
    const t = data.cases.filter((c) => c.story_id === s.id).map((c) => c.type);
    const pos = t.filter((x) => x === "Positive").length;
    const neg = t.filter((x) => x.startsWith("Negative")).length;
    const exc = t.filter((x) => x === "Exception").length;
    if (pos < 1) errors.push(`story ${s.id}: needs at least 1 Positive case (has ${pos})`);
    if (neg < 2) errors.push(`story ${s.id}: needs at least 2 Negative cases (has ${neg})`);
    if (exc < 1) errors.push(`story ${s.id}: needs at least 1 Exception case (has ${exc})`);
  }
  return errors;
}

/** Counts cases per level (cases without a level are ignored) and lists levels with zero cases. */
export function levelCoverage(cases: Pick<Case, "level">[]): { counts: Record<string, number>; missing: string[] } {
  const counts = Object.fromEntries(LEVELS.map((l) => [l, cases.filter((c) => c.level === l).length]));
  return { counts, missing: LEVELS.filter((l) => !counts[l]) };
}

/** Neutralises spreadsheet formulas: a cell starting (after optional spaces) with = + - @ TAB or CR gets a leading single quote. */
export const defuse = (v: string): string => (/^ *[=+\-@\t\r]/.test(v) ? `'${v}` : v);

/** RFC 4180 field quoting, with formula-injection defence. */
export function csvField(raw: string): string {
  const v = defuse(raw);
  return /[",\r\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}
export const csvRow = (fields: string[]): string => fields.map(csvField).join(",");

export function jiraPriority(p: string): string {
  return ({ P1: "High", P2: "Medium", P3: "Low" } as Record<string, string>)[p] ?? "Medium";
}

const mdHtml = (v: string) => v.replace(/</g, "&lt;").replace(/>/g, "&gt;");
const mdCell = (v: string) => v.replace(/\|/g, "\\|").replace(/\r?\n/g, "<br>");
const stepsText = (steps: string[]) => steps.map((s, i) => `${i + 1}. ${s}`);

export function renderStoriesMd(d: CasesFile): string {
  const out = [`# User Stories: ${d.app}`, ""];
  for (const s of d.stories) {
    out.push(`**${s.id}**: As a ${s.role}, I want to ${s.action} so that ${s.benefit}.`, "", `Priority: ${s.priority}`, "", "Acceptance criteria:");
    s.acceptance.forEach((a, i) => out.push(`${i + 1}. ${a}`));
    out.push("");
  }
  out.push("## Test Cases", "", `| ${COLUMNS.join(" | ")} |`, `| ${COLUMNS.map(() => ":---").join(" | ")} |`);
  for (const c of d.cases) {
    const plain = [c.tc_id, c.story_id, c.scenario, c.type, c.precondition, c.test_data];
    const cells = [...plain.map((x) => mdHtml(x ?? "")), stepsText(c.steps).map(mdHtml).join("<br>"), ...[c.expected, c.priority, c.automation, c.remarks].map((x) => mdHtml(x ?? ""))];
    out.push(`| ${cells.map(mdCell).join(" | ")} |`);
  }
  return out.join("\n") + "\n";
}

export function renderCasesCsv(d: CasesFile): string {
  const rows = [COLUMNS, ...d.cases.map((c) => [c.tc_id, c.story_id, c.scenario, c.type, c.precondition, c.test_data, stepsText(c.steps).join("\n"), c.expected, c.priority, c.automation, c.remarks ?? ""])];
  return rows.map(csvRow).join("\r\n") + "\r\n";
}

export function renderJiraCsv(d: CasesFile): string {
  const rows: string[][] = [["Summary", "Issue Type", "Description", "Priority", "Labels", "Parent/Story ID"]];
  for (const s of d.stories) {
    rows.push([`${s.id}: As a ${s.role}, I want to ${s.action} so that ${s.benefit}`, "Story", s.acceptance.map((a, i) => `${i + 1}. ${a}`).join("\n"), jiraPriority(s.priority), "agentic-qe", ""]);
  }
  for (const c of d.cases) {
    const desc = [`Type: ${c.type}`, `Precondition: ${c.precondition ?? ""}`, `Test data: ${c.test_data ?? ""}`, "Steps:", ...stepsText(c.steps), `Expected: ${c.expected}`, `Automation: ${c.automation}`].join("\n");
    rows.push([`${c.tc_id}: ${c.scenario}`, "Test", desc, jiraPriority(c.priority), "agentic-qe", c.story_id]);
  }
  return rows.map(csvRow).join("\r\n") + "\r\n";
}

/** Validates, writes the three files into outDir and stamps each. Throws with all errors if invalid. */
export function exportCases(data: CasesFile, outDir: string, root = projectRoot({})): string[] {
  const errors = validateCases(data);
  if (errors.length) throw new Error(errors.join("\n"));
  const files: [string, string][] = [
    ["user_stories.md", renderStoriesMd(data)],
    ["test_cases.csv", renderCasesCsv(data)],
    ["jira_import.csv", renderJiraCsv(data)]
  ];
  return files.map(([name, text]) => {
    const p = resolve(join(outDir, name));
    safeWrite(p, text, root);
    stampFile(p, root);
    return p;
  });
}

if (isMain(import.meta.url)) {
  const [input, outDir] = process.argv.slice(2);
  if (!input || !outDir) {
    console.error("usage: node export-cases.ts <cases.json> <out-dir>");
    process.exit(2);
  }
  try {
    for (const p of exportCases(JSON.parse(readFileSync(input, "utf-8")), outDir)) console.log(`wrote ${p}`);
  } catch (e) {
    console.error(`export-cases: validation failed\n${(e as Error).message}`);
    process.exit(1);
  }
}
