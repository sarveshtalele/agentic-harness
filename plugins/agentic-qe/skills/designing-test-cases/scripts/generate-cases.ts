import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export interface TestCaseDesign {
  caseId: string;
  requirementId: string;
  scenario: string;
  type: "Positive" | "Negative" | "Exception" | "Boundary";
  precondition: string;
  testData: Record<string, any>;
  steps: string[];
  expectedResult: string;
  priority: "P0" | "P1" | "P2";
  automationCandidate: boolean;
  remarks: string;
  bdd: {
    given: string;
    when: string;
    then: string;
  };
  oracle: {
    kind: "specified" | "derived" | "metamorphic" | "golden";
    sourceQuote?: string;
  };
}

export function validateDesignCase(c: TestCaseDesign): boolean {
  if (!c.caseId || !c.scenario || !c.expectedResult) {
    throw new Error(`Invalid test case: missing caseId, scenario, or expectedResult.`);
  }
  if (!c.oracle || !c.oracle.kind) {
    throw new Error(`Test case ${c.caseId} missing deterministic oracle classification.`);
  }
  return true;
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

// CLI: node generate-cases.ts <cases.json>  (array of cases) -> JSON {count, errors}
if (isCli) {
  const file = process.argv[2];
  if (!file) { console.error("usage: node generate-cases.ts <cases.json>"); process.exit(2); }
  const cases: TestCaseDesign[] = JSON.parse(readFileSync(file, "utf-8"));
  const errors: string[] = [];
  for (const c of cases) { try { validateDesignCase(c); } catch (e) { errors.push((e as Error).message); } }
  console.log(JSON.stringify({ count: cases.length, errors }, null, 2));
  process.exit(errors.length ? 1 : 0);
}
