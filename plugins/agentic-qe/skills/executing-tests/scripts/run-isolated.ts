import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export interface ExecutionSummary {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  durationMs: number;
  status: "PASS" | "FAIL" | "INCONCLUSIVE" | "TIMEOUT";
}

export function parseTestRunResult(total: number, passed: number, failed: number, durationMs: number): ExecutionSummary {
  if (total === 0) {
    return {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      durationMs,
      status: "INCONCLUSIVE"
    };
  }
  return {
    total,
    passed,
    failed,
    skipped: Math.max(0, total - passed - failed),
    durationMs,
    status: failed === 0 && passed > 0 ? "PASS" : "FAIL"
  };
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

// CLI: node run-isolated.ts <total> <passed> <failed> <durationMs> -> JSON verdict (INCONCLUSIVE when total is 0)
if (isCli) {
  const [t, p, f, d] = process.argv.slice(2).map(Number);
  if ([t, p, f, d].some((n) => !Number.isFinite(n))) { console.error("usage: node run-isolated.ts <total> <passed> <failed> <durationMs>"); process.exit(2); }
  console.log(JSON.stringify(parseTestRunResult(t, p, f, d), null, 2));
}
