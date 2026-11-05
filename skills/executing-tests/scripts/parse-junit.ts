import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export interface TestCaseFailure {
  testName: string;
  className?: string;
  failureMessage: string;
  stackTrace: string;
}

export interface ParsedJUnitReport {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  durationMs: number;
  status: "PASS" | "FAIL" | "INCONCLUSIVE";
  /** Set when INCONCLUSIVE because the input was refused (too large). */
  reason?: string;
  failures: TestCaseFailure[];
  /** Every testcase with its CASE_ID derived from tc_<app>_<nnn> / tc-<app>-<nnn> naming, for traceability. */
  cases: { testName: string; className: string; caseId: string | null; status: "PASS" | "FAIL" | "SKIPPED"; durationMs: number }[];
}

const MAX_BYTES = 5 * 1024 * 1024;

/** indexOf with a memo for non-decreasing `from`, so scanning many unclosed tags stays linear. */
const nextIndex = (hay: string, needle: string) => {
  let at = -2;
  return (from: number): number => (at === -1 ? -1 : at >= from ? at : (at = hay.indexOf(needle, from)));
};

/** First <failure>/<error> element in a testcase body. Linear: indexOf scanning, no regex backtracking. */
function findFailure(inner: string): { attrs: string; body?: string } | null {
  const start = /<(failure|error)\b/g;
  const close = { failure: nextIndex(inner, "</failure>"), error: nextIndex(inner, "</error>") };
  for (let m; (m = start.exec(inner)); ) {
    const gt = inner.indexOf(">", start.lastIndex);
    if (gt < 0) return null;
    const attrs = inner.slice(start.lastIndex, gt);
    if (attrs.endsWith("/")) return { attrs };
    const end = close[m[1] as "failure" | "error"](gt + 1);
    if (end >= 0) return { attrs, body: inner.slice(gt + 1, end) };
  }
  return null;
}

/**
 * Parses a standard JUnit XML report string into a structured summary.
 * Input over 5 MB is refused (INCONCLUSIVE with a reason).
 */
/** tc_<app>_<nnn>, tc-<app>-<nnn> and PascalCase TcApp001 (C#, Java) -> TC-APP-001. */
export const caseIdOf = (s: string): string | null =>
  s.match(/tc[_-]?([a-z][a-z0-9]*?)[_-]?(\d{3,})/i)?.slice(1, 3).map((x, i) => (i ? x : x.toUpperCase())).join("-").replace(/^/, "TC-") ?? null;

export function parseJUnitXml(xmlContent: string): ParsedJUnitReport {
  if (!xmlContent || xmlContent.trim().length === 0) {
    return {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      durationMs: 0,
      status: "INCONCLUSIVE",
      failures: [],
      cases: []
    };
  }

  if (xmlContent.length > MAX_BYTES) {
    return { total: 0, passed: 0, failed: 0, skipped: 0, durationMs: 0, status: "INCONCLUSIVE", reason: `JUnit XML is larger than ${MAX_BYTES / 1024 / 1024} MB; not parsed`, failures: [], cases: [] };
  }

  // dotnet test writes TRX (Visual Studio test results); every caller of this parser reads it the same way
  if (/<TestRun\b/.test(xmlContent.slice(0, 2000)) && xmlContent.includes("<UnitTestResult")) return parseTrx(xmlContent);

  // Extract totals from <testsuites> or <testsuite>
  const testsMatch = xmlContent.match(/tests="(\d+)"/);
  const failuresMatch = xmlContent.match(/failures="(\d+)"/);
  const errorsMatch = xmlContent.match(/errors="(\d+)"/);
  const skippedMatch = xmlContent.match(/skipped="(\d+)"/);
  const timeMatch = xmlContent.match(/time="([\d.]+)"/);

  const total = testsMatch ? parseInt(testsMatch[1], 10) : 0;
  const failuresCount = failuresMatch ? parseInt(failuresMatch[1], 10) : 0;
  const errorsCount = errorsMatch ? parseInt(errorsMatch[1], 10) : 0;
  const skipped = skippedMatch ? parseInt(skippedMatch[1], 10) : 0;
  const durationSec = timeMatch ? parseFloat(timeMatch[1]) : 0;
  const durationMs = Math.round(durationSec * 1000);

  const totalFailed = failuresCount + errorsCount;
  const passed = Math.max(0, total - totalFailed - skipped);

  // Extract failure details
  const failures: TestCaseFailure[] = [];
  // Attribute order differs between runners (pytest writes classname first), and
  // <failure .../> may be self-closing, so read attributes independently.
  const attr = (s: string, name: string) => s.match(new RegExp(`\\b${name}="([^"]*)"`))?.[1] ?? "";
  const cases: ParsedJUnitReport["cases"] = [];
  const closeTag = nextIndex(xmlContent, "</testcase>");
  const gtAt = nextIndex(xmlContent, ">");

  for (let pos = 0; ; ) {
    const s0 = xmlContent.indexOf("<testcase", pos);
    if (s0 < 0) break;
    const gt = gtAt(s0);
    if (gt < 0) break; // no ">" anywhere after this point
    if (!/[\s\/>]/.test(xmlContent[s0 + 9] ?? "x")) { pos = s0 + 9; continue; } // <testcases..., not a testcase
    const attrs = xmlContent.slice(s0 + 9, gt);
    let innerContent = "";
    pos = gt + 1;
    if (!attrs.endsWith("/")) {
      const end = closeTag(gt + 1);
      if (end < 0) continue; // unclosed: skipped, like the old pattern
      innerContent = xmlContent.slice(gt + 1, end);
      pos = end + "</testcase>".length;
    }
    const failureBlock = findFailure(innerContent);
    const testName = attr(attrs, "name");
    const className = attr(attrs, "classname");
    cases.push({ testName, className, caseId: caseIdOf(`${className} ${testName}`), durationMs: Math.round(parseFloat(attr(attrs, "time")) * 1000) || 0, status: failureBlock ? "FAIL" : /<skipped\b/.test(innerContent) ? "SKIPPED" : "PASS" });
    if (failureBlock) {
      failures.push({
        testName,
        className,
        failureMessage: attr(failureBlock.attrs, "message") || "Test execution assertion failed",
        stackTrace: failureBlock.body ? failureBlock.body.trim() : ""
      });
    }
  }

  let status: "PASS" | "FAIL" | "INCONCLUSIVE" = "PASS";
  if (total === 0) {
    status = "INCONCLUSIVE";
  } else if (totalFailed > 0) {
    status = "FAIL";
  }

  return {
    total,
    passed,
    failed: totalFailed,
    skipped,
    durationMs,
    status,
    failures,
    cases
  };
}

const unesc = (s: string) => s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&#xD;|&#13;/g, "").replace(/&#xA;|&#10;/g, "\n").replace(/&amp;/g, "&");
/** Text of the first <tag>…</tag> inside s, unescaped. */
const inner = (s: string, tag: string): string => { const a = s.indexOf(`<${tag}>`); if (a < 0) return ""; const b = s.indexOf(`</${tag}>`, a); return b < 0 ? "" : unesc(s.slice(a + tag.length + 2, b)).trim(); };

/**
 * TRX (dotnet test --logger trx): one <UnitTestResult testName outcome duration> per test, the class name in
 * <TestDefinitions>. Outcome Passed is PASS; Failed, Error, Timeout and Aborted are FAIL; anything else is SKIPPED.
 * Linear indexOf scanning, like the JUnit path.
 */
export function parseTrx(xml: string): ParsedJUnitReport {
  const attr = (s: string, name: string) => s.match(new RegExp(`\\b${name}="([^"]*)"`))?.[1] ?? "";
  const classOf = new Map<string, string>();
  for (let pos = 0; ; ) {
    const s0 = xml.indexOf("<UnitTest ", pos);
    if (s0 < 0) break;
    const end = xml.indexOf("</UnitTest>", s0);
    const block = xml.slice(s0, end < 0 ? xml.indexOf(">", s0) + 1 : end);
    const tm = block.indexOf("<TestMethod");
    if (tm >= 0) classOf.set(attr(block.slice(0, block.indexOf(">") + 1), "id"), attr(block.slice(tm, block.indexOf(">", tm) + 1), "className"));
    pos = end < 0 ? s0 + 10 : end + 11;
  }
  const cases: ParsedJUnitReport["cases"] = [];
  const failures: TestCaseFailure[] = [];
  let durationMs = 0;
  for (let pos = 0; ; ) {
    const s0 = xml.indexOf("<UnitTestResult", pos);
    if (s0 < 0) break;
    const gt = xml.indexOf(">", s0);
    if (gt < 0) break;
    const attrs = xml.slice(s0, gt + 1);
    let body = "";
    pos = gt + 1;
    if (!attrs.endsWith("/>")) {
      const end = xml.indexOf("</UnitTestResult>", gt);
      if (end >= 0) { body = xml.slice(gt + 1, end); pos = end + 17; }
    }
    const testName = unesc(attr(attrs, "testName"));
    const className = classOf.get(attr(attrs, "testId")) ?? "";
    const outcome = attr(attrs, "outcome");
    const status = outcome === "Passed" ? "PASS" : /^(Failed|Error|Timeout|Aborted)$/.test(outcome) ? "FAIL" : "SKIPPED";
    const d = /^(\d+):(\d+):([\d.]+)$/.exec(attr(attrs, "duration"));
    const ms = d ? Math.round((Number(d[1]) * 3600 + Number(d[2]) * 60 + Number(d[3])) * 1000) : 0;
    durationMs += ms;
    cases.push({ testName, className, caseId: caseIdOf(`${className} ${testName}`), durationMs: ms, status });
    if (status === "FAIL") failures.push({ testName, className, failureMessage: inner(body, "Message") || `Test outcome ${outcome}`, stackTrace: inner(body, "StackTrace") });
  }
  const passed = cases.filter((c) => c.status === "PASS").length, failed = failures.length, skipped = cases.length - passed - failed;
  return { total: cases.length, passed, failed, skipped, durationMs, status: failed ? "FAIL" : passed ? "PASS" : "INCONCLUSIVE", failures, cases }; // PASS needs at least one passing test
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const file = process.argv[2];
  if (!file) {
    console.error("usage: node parse-junit.ts <junit.xml>");
    process.exit(2);
  }
  console.log(JSON.stringify(parseJUnitXml(readFileSync(file, "utf-8")), null, 2));
}
