import { join } from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { type HookInput, projectRoot, qeActive, isMain, readInput, redact } from "./hook-common.ts";
import { appendLedger, readAnchor } from "./memory-logger.ts";
import { gateStatus } from "./on-decision.ts";
import { writeCoverage } from "./coverage.ts";

export function recordToolUse(input: HookInput, root: string): boolean {
  if (!qeActive(root) || !existsSync(join(root, ".qe"))) return false; // never recreate a deleted .qe/
  if (existsSync(join(root, ".qe", "ledger.jsonl")) && readAnchor(root) === null) return false; // not this machine's ledger: leave it untrusted (AQE141-001)
  const ti = input.tool_input ?? {};
  const target = String(ti.file_path ?? ti.notebook_path ?? ti.command ?? ti.cmd ?? ti.patch ?? ti.input ?? "");
  const shown = redact(target).slice(0, 160); // redact first so a secret cut by the limit is not half-logged
  appendLedger(join(root, ".qe", "ledger.jsonl"), {
    tool: input.tool_name ?? "unknown",
    [ti.file_path === undefined && ti.notebook_path === undefined ? "command" : "path"]: shown,
    timestamp: new Date().toISOString()
  });
  return true;
}

/** After a change, rebuild the coverage map so the dashboard, the pane and the next phase see what is still missing. */
export function refreshCoverage(root: string): boolean {
  let app = "";
  try { app = String(JSON.parse(readFileSync(join(root, ".qe", "run.json"), "utf-8")).app ?? ""); } catch { return false; }
  if (!/^[A-Za-z0-9._-]{1,64}$/.test(app) || !existsSync(join(root, "docs", "qe", app))) return false;
  const st = gateStatus(join(root, ".qe"));
  let upTo = -1;
  while (upTo < 5 && st[upTo + 1].status === "APPROVED") upTo++;
  writeCoverage(root, app, upTo);
  return true;
}

function main(): void {
  const input = readInput();
  const root = projectRoot(input);
  let logged = false;
  try { logged = recordToolUse(input, root); } catch (e) { console.error(`agentic-qe: not logged: ${(e as Error).message}`); }
  if (logged) { try { refreshCoverage(root); } catch { /* the map is rebuilt again at the next change or gate */ } }
}

if (isMain(import.meta.url)) main();
