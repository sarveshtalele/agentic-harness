import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export interface PatchResult {
  patchedCode: string;
  success: boolean;
  assertionsIntact: boolean;
  replacementsCount: number;
  error?: string;
}

/**
 * Surgically replaces fragile/broken selectors in test source code
 * while verifying that assertion statements (expect, assert) remain 100% unaltered.
 */
export function applySelectorPatch(
  testSourceCode: string,
  brokenSelector: string,
  healedSelector: string
): PatchResult {
  if (!testSourceCode.includes(brokenSelector)) {
    return {
      patchedCode: testSourceCode,
      success: false,
      assertionsIntact: true,
      replacementsCount: 0,
      error: `Broken selector '${brokenSelector}' not found in source code.`
    };
  }

  // Count assertions before patch
  const assertionsBefore = countAssertions(testSourceCode);

  // Replace selector
  const patchedCode = testSourceCode.replaceAll(brokenSelector, healedSelector);

  // Count assertions after patch
  const assertionsAfter = countAssertions(patchedCode);

  const assertionsIntact = assertionsBefore === assertionsAfter;

  if (!assertionsIntact) {
    return {
      patchedCode: testSourceCode, // revert
      success: false,
      assertionsIntact: false,
      replacementsCount: 0,
      error: "Healing rejected: Assertions were mutated during selector replacement."
    };
  }

  const replacementsCount = (testSourceCode.split(brokenSelector).length - 1);

  return {
    patchedCode,
    success: true,
    assertionsIntact: true,
    replacementsCount
  };
}

function countAssertions(code: string): number {
  const matches = code.match(/\b(expect|assert|should)\s*\(|\bto(Be|Equal|Have|Contain)\b/g);
  return matches ? matches.length : 0;
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

// CLI: node apply-healing.ts <test-file> <broken-selector> <healed-selector> -> JSON result on stdout.
// Prints the patched source in `patchedCode`; it never writes the test file (the skill edits it after approval).
if (isCli) {
  const [file, broken, healed] = process.argv.slice(2);
  if (!file || !broken || !healed) { console.error("usage: node apply-healing.ts <test-file> <broken> <healed>"); process.exit(2); }
  const r = applySelectorPatch(readFileSync(file, "utf-8"), broken, healed);
  console.log(JSON.stringify(r, null, 2));
  process.exit(r.success ? 0 : 1);
}
