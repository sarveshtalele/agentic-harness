// Created 2026-11-03 16:50 IST by agentic-qe 1.6.0.
// Exports the plugin's own record of a QE run (not the conversation): gate timeline with waivers, phase commands and tool
// activity from the ledger, files changed, coverage, test inventory, validator verdict and results.
// usage: node export-session.ts --root <dir> --app <app>   (writes docs/qe/<app>/sessions/session-<time>.md and .json)
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { isMain, safeWrite, localIso } from "../../../hooks/src/hook-common.ts";
import { gateStatus, GATE_NAMES } from "../../../hooks/src/on-decision.ts";
import { ledgerTrust } from "../../../hooks/src/memory-logger.ts";
import { buildCoverage, checkGate } from "../../../hooks/src/coverage.ts";
import { readJsonDoc } from "../../../hooks/src/layout.ts";

const pad = (n: number) => String(n).padStart(2, "0");
const stamp = (d = new Date()) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
const md = (s: unknown) => String(s ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");

export function exportSession(root: string, app: string, now = new Date()): { md: string; json: string } {
  if (!/^[A-Za-z0-9._-]{1,64}$/.test(app)) throw new Error("bad app name");
  const trust = ledgerTrust(root);
  let records: any[] = [];
  try { records = readFileSync(join(root, ".qe", "ledger.jsonl"), "utf-8").split("\n").filter(Boolean).map((l) => JSON.parse(l)); } catch { /* no ledger */ }
  const gates = gateStatus(join(root, ".qe"));
  const decisions = records.filter((r) => r.type === "gate_decision" && r.source === "user_prompt").map((r) => ({ at: r.timestamp, gate: r.gate, decision: r.decision, waiver: r.waiver?.reason ?? null, waivedGaps: Array.isArray(r.waiver?.gaps) ? r.waiver.gaps.length : 0 }));
  const tools: Record<string, number> = {};
  const files = new Set<string>();
  for (const r of records) {
    if (typeof r.tool === "string") tools[r.tool] = (tools[r.tool] ?? 0) + 1;
    if (typeof r.path === "string" && /^(Write|Edit|MultiEdit|NotebookEdit)$/.test(r.tool ?? "")) files.add(r.path);
  }
  const cov = buildCoverage(root, app);
  const check = checkGate(cov, 5);
  const validation = readJsonDoc(join(root, "docs", "qe", app, "validation.json"));
  const results = Object.values(cov.results);
  const data = {
    exported_at: now.toISOString(), app, ledger: trust, gates: Object.fromEntries(Object.entries(gates).map(([g, s]) => [g, s.status])), decisions,
    tools, files_changed: [...files].sort(), coverage: check.counts, inventory: cov.inventory,
    validator: validation ? { gate: validation.gate, ok: validation.ok, errors: (validation.errors ?? []).length, warnings: (validation.warnings ?? []).length } : null,
    results: { total: results.length, passed: results.filter((s) => s === "PASS").length, failed: results.filter((s) => s === "FAIL").length },
    open_gaps: check.gaps
  };
  const lines = [
    `---`, `doc_id: session-${stamp(now)}`, `created_at: ${localIso(now)}`, `created_by: agentic-qe`, `---`, "",
    `# QE session record: ${app}`, "",
    `Exported ${localIso(now)}. The plugin's own record of the run (ledger, coverage, inventory, validator, results); the conversation is not included.`, "",
    `Ledger: ${trust.trusted ? "trusted" : `NOT trusted (${trust.reason})`}`, "",
    "## Gates", "", "| Gate | Status |", "|---|---|", ...[0, 1, 2, 3, 4, 5].map((g) => `| ${g} ${GATE_NAMES[g]} | ${gates[g].status}${gates[g].waiver ? ` (accepted gaps: ${md(gates[g].waiver!.reason)})` : ""} |`), "",
    "## Decisions", "", "| When | Gate | Decision | Accepted gaps |", "|---|---|---|---|", ...decisions.map((d) => `| ${md(d.at)} | ${d.gate} | ${d.decision} | ${d.waiver ? `${d.waivedGaps}: ${md(d.waiver)}` : "-"} |`), "",
    "## Coverage", "", `requirements ${check.counts.requirements} · plan scenarios ${check.counts.scenarios} · designed cases ${check.counts.cases} · test files ${check.counts.tests} · results ${check.counts.results}`, "",
    `Tests in the repo: ${cov.inventory.tests} in ${cov.inventory.files} files (existing ${cov.inventory.existing}, generated ${cov.inventory.generated}, added by hand ${cov.inventory.manual}).`, "",
    `Validator: ${data.validator ? `gate ${data.validator.gate} ${data.validator.ok ? "PASS" : "FAIL"} (${data.validator.errors} errors, ${data.validator.warnings} warnings)` : "not run"}.`, "",
    `Results: ${data.results.passed} passed, ${data.results.failed} failed, ${data.results.total} in all.`, "",
    ...(check.gaps.length ? ["Open gaps:", "", ...check.gaps.map((g) => `- ${md(g)}`), ""] : ["No open gaps.", ""]),
    "## Activity", "", "| Tool | Calls |", "|---|---|", ...Object.entries(tools).sort((a, b) => b[1] - a[1]).map(([t, n]) => `| ${md(t)} | ${n} |`), "",
    `Files written through Claude's tools: ${files.size}`, ...[...files].sort().slice(0, 200).map((f) => `- \`${md(f)}\``), ""
  ];
  return { md: lines.join("\n"), json: JSON.stringify(data, null, 1) + "\n" };
}

if (isMain(import.meta.url)) {
  const { values: v } = parseArgs({ options: { root: { type: "string" }, app: { type: "string" } }, strict: false });
  const root = resolve(String(v.root ?? process.cwd())), app = String(v.app ?? "");
  try {
    const out = exportSession(root, app), name = `session-${stamp()}`;
    const dir = join(root, "docs", "qe", app, "sessions");
    safeWrite(join(dir, `${name}.md`), out.md, root);
    safeWrite(join(dir, `${name}.json`), out.json, root);
    console.log(`docs/qe/${app}/sessions/${name}.md`);
  } catch (e) { console.error(`export failed: ${(e as Error).message}`); process.exit(1); }
}
