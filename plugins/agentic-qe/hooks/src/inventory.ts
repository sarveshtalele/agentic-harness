// Created 2026-11-03 15:30 IST by agentic-qe 1.6.0.
// Every test file in the project, read by code: framework, level, test and assertion counts, and its CASE_ID markers.
// Answers "how many tests are already in the repo, how many were generated, how many someone added by hand, and how many
// designed cases still have no test". Unchanged files are not read again (cache by size and modification time).
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
/** The `CASE_ID:` markers in the first 15 lines of a test file (comma or space separated). */
export function markersOf(text: string): string[] {
  const out: string[] = [];
  for (const line of text.split(/\r?\n/).slice(0, 15)) {
    const m = /CASE_ID:\s*([^\n]*)/.exec(line);
    if (m) out.push(...m[1].split(/[\s,()]+/).map((x) => x.trim()).filter(Boolean));
  }
  return out;
}

export type TestLevel = "Unit" | "Integration" | "E2E";
export interface TestFile { path: string; framework: string; level: TestLevel; tests: number; assertions: number; markers: string[]; mtimeMs: number; size: number }
export interface Inventory { files: TestFile[]; truncated: boolean }

const SKIP = /^(node_modules|\.git|\.venv|venv|env|\.qe|\.qe\.untrusted-.*|docs|dist|build|out|bin|obj|target|coverage|results|test-results|playwright-report|\.next|\.nuxt|__pycache__|\.pytest_cache|\.mypy_cache|\.idea|\.vscode)$/i;
/** A test file by name, across the stacks the plugin runs. */
export const TEST_FILE = /(\.(test|spec)\.[cm]?[jt]sx?$|^test_.*\.py$|_test\.py$|_test\.go$|Tests?\.cs$|Tests?\.java$|Test\.kt$|_spec\.rb$)/i;
const MAX_FILES = 5000, MAX_DEPTH = 12, MAX_BYTES = 512 * 1024;

const frameworkOf = (path: string, text: string): string => {
  if (/\.py$/.test(path)) return "pytest";
  if (/\.cs$/.test(path)) return /\[Fact\]|\[Theory\]/.test(text) ? "xunit" : /\[Test\]/.test(text) ? "nunit" : "dotnet";
  if (/\.(java|kt)$/.test(path)) return "junit";
  if (/\.go$/.test(path)) return "go test";
  if (/@playwright\/test/.test(text)) return "playwright";
  if (/from ["']vitest["']/.test(text)) return "vitest";
  if (/node:test/.test(text)) return "node:test";
  if (/cypress/.test(text)) return "cypress";
  return /\.[cm]?[jt]sx?$/.test(path) ? "jest" : "other";
};
const levelOf = (path: string, framework: string): TestLevel =>
  /(^|\/)(e2e|ui|browser|playwright|cypress|journeys?)(\/|$)|\.e2e\.|\.ui\./i.test(path) || framework === "playwright" || framework === "cypress" ? "E2E"
    : /(^|\/)(integration|api|contract|it)(\/|$)|\.int(egration)?\./i.test(path) ? "Integration" : "Unit";
const count = (text: string, re: RegExp) => (text.match(re) ?? []).length;
const TEST_RE = /^\s*(?:async\s+)?def test_|\b(?:it|test)(?:\.only|\.skip)?\s*\(|\[(?:Fact|Theory|Test|TestCase|TestMethod)\b|@Test\b|^func Test[A-Z]/gm;
const ASSERT_RE = /\bassert\b|\bexpect\s*\(|\bAssert\.|\bassert[A-Z][A-Za-z]*\s*\(|\.should\b|\bt\.(?:Error|Fatal|Fail)/g;

const cache = new Map<string, TestFile>();

/** Reads one test file (or returns the cached reading when it has not changed). */
export function readTestFile(root: string, abs: string): TestFile | null {
  try {
    const s = statSync(abs);
    if (!s.isFile()) return null;
    const path = relative(root, abs).replace(/\\/g, "/");
    const hit = cache.get(abs);
    if (hit && hit.mtimeMs === s.mtimeMs && hit.size === s.size) return hit;
    const text = s.size > MAX_BYTES ? readFileSync(abs, "utf-8").slice(0, MAX_BYTES) : readFileSync(abs, "utf-8");
    const framework = frameworkOf(path, text);
    const f: TestFile = { path, framework, level: levelOf(path, framework), tests: count(text, TEST_RE), assertions: count(text, ASSERT_RE), markers: markersOf(text).map((m) => m.toUpperCase().replace(/_/g, "-")), mtimeMs: s.mtimeMs, size: s.size };
    cache.set(abs, f);
    return f;
  } catch { return null; }
}

/** Every test file under the project root, skipping dependencies, build output and run state. */
export function scanTests(root: string): Inventory {
  const files: TestFile[] = [];
  let truncated = false;
  const walk = (dir: string, depth: number) => {
    if (depth > MAX_DEPTH || truncated) return;
    let entries: import("node:fs").Dirent[] = [];
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (files.length >= MAX_FILES) { truncated = true; return; }
      if (e.isSymbolicLink()) continue;
      const p = join(dir, e.name);
      if (e.isDirectory()) { if (!SKIP.test(e.name)) walk(p, depth + 1); }
      else if (e.isFile() && TEST_FILE.test(e.name)) { const f = readTestFile(root, p); if (f) files.push(f); }
    }
  };
  walk(root, 0);
  files.sort((a, b) => a.path.localeCompare(b.path));
  return { files, truncated };
}

export interface InventorySummary { files: number; tests: number; byLevel: Record<TestLevel, number>; existing: number; generated: number; manual: number; markedNotInManifest: string[]; truncated: boolean }

/**
 * Classifies the repo's test files: generated (listed in the manifest or marked with a designed case id), existing (no
 * marker and older than the run), and manual (no marker, added or changed since the run started, not in the manifest).
 */
export function summarize(inv: Inventory, opts: { caseIds: Set<string>; manifest: Set<string>; runStartedMs: number | null }): InventorySummary {
  const byLevel: Record<TestLevel, number> = { Unit: 0, Integration: 0, E2E: 0 };
  let existing = 0, generated = 0, manual = 0;
  const markedNotInManifest: string[] = [];
  for (const f of inv.files) {
    byLevel[f.level] += Math.max(1, f.tests);
    const ours = f.markers.some((m) => opts.caseIds.has(m));
    if (opts.manifest.has(f.path) || ours) { generated++; if (ours && !opts.manifest.has(f.path)) markedNotInManifest.push(f.path); }
    else if (opts.runStartedMs !== null && f.mtimeMs > opts.runStartedMs) manual++;
    else existing++;
  }
  return { files: inv.files.length, tests: inv.files.reduce((n, f) => n + Math.max(1, f.tests), 0), byLevel, existing, generated, manual, markedNotInManifest, truncated: inv.truncated };
}
