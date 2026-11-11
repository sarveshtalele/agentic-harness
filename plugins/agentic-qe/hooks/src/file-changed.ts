// Created 2026-11-03 16:40 IST by agentic-qe 1.6.0.
// FileChanged hook: a watched file changed outside Claude's tools (an editor, git pull). Rebuilds the coverage map and the
// test inventory so the pane, the dashboard and the next phase see it. Writes only the plugin's own files.
import { projectRoot, isMain, readInput } from "./hook-common.ts";
import { refreshCoverage } from "./ledger-hook.ts";

if (isMain(import.meta.url)) {
  try { refreshCoverage(projectRoot(readInput())); } catch { /* rebuilt again at the next change */ }
}
