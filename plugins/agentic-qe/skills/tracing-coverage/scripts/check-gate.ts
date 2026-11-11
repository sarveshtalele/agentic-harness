// Created 2026-11-03 14:10 IST by agentic-qe 1.5.0.
// Prints what a gate still needs before the approval hook will record it, and rewrites the coverage map.
// usage: node check-gate.ts --gate <1-5> --app <app> [--root <dir>] [--json]   (exit 1 while the gate check fails)
import { parseArgs } from "node:util";
import { resolve } from "node:path";
import { isMain } from "../../../hooks/src/hook-common.ts";
import { checkGate, writeCoverage } from "../../../hooks/src/coverage.ts";
import { recordValidation } from "../../../hooks/src/validate.ts";

export function report(root: string, app: string, gate: number): { text: string; ok: boolean } {
  const cov = writeCoverage(root, app, gate - 1);
  const c = checkGate(cov, gate);
  const v = recordValidation(root, app, gate, cov);
  const ok = c.ok && v.ok;
  const inv = cov.inventory;
  const lines = [
    `Gate ${gate} check for ${app}: ${ok ? "PASS" : "FAIL"}`,
    `requirements ${c.counts.requirements} · plan scenarios ${c.counts.scenarios} · designed cases ${c.counts.cases} · test files ${c.counts.tests} · results ${c.counts.results}`,
    `tests in the repo: ${inv.tests} in ${inv.files} files (existing ${inv.existing}, generated ${inv.generated}, added by hand ${inv.manual})`,
    ...(c.ok ? [] : ["Coverage gaps (the approval hook refuses the gate until each is done):", ...c.gaps.map((g) => `- ${g}`)]),
    v.verdict ? `pandas/numpy validator ${v.verdict.validator}: ${v.verdict.ok ? "PASS" : "FAIL"} (${v.verdict.errors.length} errors, ${v.verdict.warnings.length} warnings)` : `pandas/numpy validator: not run (${v.lines[0]})`,
    ...(v.verdict?.errors ?? []).map((e) => `- ${e.message}${e.ids.length ? `: ${e.ids.slice(0, 25).join(", ")}` : ""}`),
    ...(v.verdict?.warnings ?? []).slice(0, 8).map((w) => `- warning: ${w.message}${w.ids.length ? `: ${w.ids.slice(0, 12).join(", ")}` : ""}`),
    ...(v.verdict?.suspects.length ? [`Give the coverage-auditor these cases first: ${v.verdict.suspects.map((s) => s.case).join(", ")}`] : []),
    ok ? "Nothing missing. The user may now type the approval phrase." : "Do the missing work; do not ask for approval while this says FAIL.",
    `Full map: docs/qe/${app}/coverage-map.md · validator report: docs/qe/${app}/validation.json`
  ];
  return { text: lines.join("\n"), ok };
}

if (isMain(import.meta.url)) {
  const { values: v } = parseArgs({ options: { gate: { type: "string" }, app: { type: "string" }, root: { type: "string" }, json: { type: "boolean" } }, strict: false });
  const gate = Number(v.gate), app = String(v.app ?? "");
  if (!Number.isInteger(gate) || gate < 1 || gate > 5 || !/^[A-Za-z0-9._-]{1,64}$/.test(app)) { console.error("usage: check-gate.ts --gate <1-5> --app <app> [--root <dir>]"); process.exit(2); }
  const root = resolve(String(v.root ?? process.cwd()));
  if (v.json) {
    const cov = writeCoverage(root, app, gate - 1), c = checkGate(cov, gate), val = recordValidation(root, app, gate, cov);
    console.log(JSON.stringify({ ...c, ok: c.ok && val.ok, inventory: cov.inventory, validator: val.verdict ?? { error: val.lines[0] } }, null, 1));
    process.exit(c.ok && val.ok ? 0 : 1);
  }
  const r = report(root, app, gate);
  console.log(r.text);
  process.exit(r.ok ? 0 : 1);
}
