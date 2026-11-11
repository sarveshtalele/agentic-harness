import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export function calculatePlanConfidence(
  controlsCovered: number, // 0 - 40
  levelFit: number,        // 0 - 30
  scenariosDerivable: number // 0 - 30
): { score: number; verdict: "APPROVED" | "REVISE" | "REJECT" } {
  const score = Math.max(0, Math.min(100, controlsCovered + levelFit + scenariosDerivable));
  let verdict: "APPROVED" | "REVISE" | "REJECT" = "REJECT";
  if (score === 100) {
    verdict = "APPROVED";
  } else if (score >= 70) {
    verdict = "REVISE";
  }
  return { score, verdict };
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

// CLI: node calculate-risk.ts <scores.json>  ({controlsCovered, levelFit, scenariosDerivable}) -> JSON {score, verdict}
if (isCli) {
  const file = process.argv[2];
  if (!file) { console.error("usage: node calculate-risk.ts <scores.json>"); process.exit(2); }
  const s = JSON.parse(readFileSync(file, "utf-8"));
  console.log(JSON.stringify(calculatePlanConfidence(s.controlsCovered, s.levelFit, s.scenariosDerivable), null, 2));
}
