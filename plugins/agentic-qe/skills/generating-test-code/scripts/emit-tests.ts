import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const CASE_ID = /^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$/; // ponytail: looser than TC-APP-001 so TC-01 and TC-AUTO-01-POS work; still no quotes, spaces or punctuation
const BAD_ROUTE = /[`'"\n\r\\]|\$\{/;

/** Emits a Playwright test. caseId and route are validated; scenario is emitted as a JSON string literal. */
export function generatePlaywrightTestTemplate(
  caseId: string,
  scenario: string,
  targetRoute: string,
  assertionCode: string
): string {
  if (!CASE_ID.test(caseId)) throw new Error(`invalid caseId '${caseId}': must match ${CASE_ID}`);
  if (BAD_ROUTE.test(targetRoute)) throw new Error("invalid path: must not contain backtick, ${, quotes, backslash or newlines");
  // ponytail: assertionCode is trusted generator output, emitted as-is.
  return `// CASE_ID: ${caseId}
import { test, expect } from '@playwright/test';

test.describe(${JSON.stringify(`${caseId}: ${scenario}`)}, () => {
  test('should execute scenario successfully', async ({ page }) => {
    const baseUrl = process.env.BASE_URL || 'http://localhost:3000';
    await page.goto(\`\${baseUrl}${targetRoute}\`);
    ${assertionCode}
  });
});
`;
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

// CLI: node emit-tests.ts <spec.json> ({caseId, scenario, route, assertion}) -> test source on stdout (writes nothing)
if (isCli) {
  const file = process.argv[2];
  if (!file) { console.error("usage: node emit-tests.ts <spec.json>"); process.exit(2); }
  const s = JSON.parse(readFileSync(file, "utf-8"));
  try { process.stdout.write(generatePlaywrightTestTemplate(s.caseId, s.scenario, s.route, s.assertion ?? "")); }
  catch (e) { console.error((e as Error).message); process.exit(1); }
}
