// Plain words for codes the server stores. Unknown codes fall back to a readable form, never a raw blob.
const words = (code: string) => {
  const t = String(code ?? "").replace(/[._-]+/g, " ").trim();
  return t ? t[0].toUpperCase() + t.slice(1) : "";
};

const ACTIONS: Record<string, string> = {
  "project.created": "Project created",
};
export const actionLabel = (code: string) => ACTIONS[code] || words(code);

const CLASSIFICATIONS: Record<string, string> = { application: "Application defect", drift: "Test drift", test_bug: "Test bug", environment: "Environment issue", flaky: "Flaky test" };
export const classificationLabel = (code: string) => CLASSIFICATIONS[code] || words(code);

const CHECKS: Record<string, string> = {
  V1: "Auditor: the test exercises its case", V2b: "No invented inputs or messages", V3: "File parses and collects", V4: "Imports and called names exist", V5: "Real assertion, no skip or tautology", V6: "Tied to its case by CASE_ID",
};
// Check codes are shown with a tooltip, so an unknown code keeps its own text
export const checkLabel = (code: string) => CHECKS[code] || code;

export const VERDICTS: Record<string, string> = {
  "NOT EXECUTED": "The platform did not run the tests, so there is no pass or fail.",
  INCONCLUSIVE: "No test was executed, so nothing can be claimed either way.",
  PASS: "Every executed test passed.",
  FAIL: "At least one executed test failed.",
  INCOMPLETE: "The run did not finish all its steps.",
  "NO NEW FAILURES": "Failures exist but none are new since the last run.",
};

// Truncated values keep the full text in the title attribute: spread this onto the element
export const full = (v: string | null | undefined) => ({ title: v || undefined });
