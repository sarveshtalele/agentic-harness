import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export interface DiagnosticResult {
  category: "SELECTOR_DRIFT" | "FIXTURE_DRIFT" | "APPLICATION_DEFECT" | "ENVIRONMENT_ERROR";
  canHeal: boolean;
  recommendedAction: string;
}

const ENV_EVIDENCE = /ECONNREFUSED|ECONNRESET|connection refused|actively refused|ENOENT|EADDRINUSE|\bport\b.*(in use|bound|unavailable)|database.*(unavailable|unreachable|down)|cannot open database|executable doesn't exist|browser.*(not (found|installed)|missing)|unable to resolve service|no service for type|unable to find a? ?constructor/i;
const ASSERTION = /\bExpected\b.*\bbut\b|\bassert(ion)?\b|AssertionError|Should\(\)\.|expect\(.*\)\.to|Assert\.(That|AreEqual|IsTrue)/i;

export function classifyFailure(errorMessage: string, stackTrace: string): DiagnosticResult {
  if (/locator\.click|waiting for locator|selector|no such element|NoSuchElement|element not found/i.test(errorMessage)) {
    return {
      category: "SELECTOR_DRIFT",
      canHeal: true,
      recommendedAction: "Inspect updated DOM snapshot and update selector to stable getByRole/getByTestId."
    };
  }
  if (ENV_EVIDENCE.test(errorMessage + "\n" + stackTrace)) {
    return {
      category: "ENVIRONMENT_ERROR",
      canHeal: false,
      recommendedAction: "Check environment, port bindings, and external services."
    };
  }
  if (errorMessage.includes("500 Internal Server Error") || stackTrace.includes("NullPointerException") || ASSERTION.test(errorMessage)) {
    return {
      category: "APPLICATION_DEFECT",
      canHeal: false,
      recommendedAction: "Real application defect detected. Log defect report and do not modify test code."
    };
  }
  return {
    category: "ENVIRONMENT_ERROR",
    canHeal: false,
    recommendedAction: "Check environment, port bindings, and external services."
  };
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

// CLI: node diagnose-failure.ts <failure.json> ({errorMessage, stackTrace}) -> JSON classification
if (isCli) {
  const file = process.argv[2];
  if (!file) { console.error("usage: node diagnose-failure.ts <failure.json>"); process.exit(2); }
  const f = JSON.parse(readFileSync(file, "utf-8"));
  console.log(JSON.stringify(classifyFailure(f.errorMessage ?? "", f.stackTrace ?? ""), null, 2));
}
