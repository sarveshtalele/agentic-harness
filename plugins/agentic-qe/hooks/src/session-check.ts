import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { scanTests } from "./inventory.ts";
import { homedir } from "node:os";
import { projectRoot, qeActive, isMain, readInput, emitContext, pluginRoot } from "./hook-common.ts";
import { ledgerTrust } from "./memory-logger.ts";
import { findPython, SETUP_HINT } from "./validate.ts";

// Old Node cannot load this file (no type stripping); hooks.json registers session-check.mjs, which checks the version first.
/** Returns warnings to show the model/user at session start. */
export function sessionWarnings(root: string, nodeVersion = process.versions.node): string[] {
  const out: string[] = [];
  const [maj, min] = nodeVersion.split(".").map(Number);
  if (maj < 22 || (maj === 22 && min < 18)) out.push("agentic-qe hooks need Node 22.18+; guardrails are not active");
  if (qeActive(root)) {
    const t = ledgerTrust(root);
    if (!t.trusted) out.push(`agentic-qe ledger verification failed (${t.reason}); gate approvals are ignored until it is repaired`);
    if (!findPython()) out.push(`agentic-qe: ${SETUP_HINT}; until then every gate approval is refused`);
  }
  const stale = staleInstall();
  if (stale) out.push(stale);
  return out;
}

const semver = (v: string): number[] => v.split(".").map((x) => parseInt(x, 10) || 0);
const newer = (a: string, b: string): boolean => { const x = semver(a), y = semver(b); for (let i = 0; i < 3; i++) if ((x[i] ?? 0) !== (y[i] ?? 0)) return (x[i] ?? 0) > (y[i] ?? 0); return false; };

/**
 * The running copy is older than the marketplace's copy: the session runs old hooks and skills (seen on Windows, where
 * 1.4.5 kept running because updates were never applied). Says how to update.
 */
export function staleInstall(env = process.env): string | null {
  try {
    const mine = String(JSON.parse(readFileSync(join(pluginRoot(env) ?? "", ".claude-plugin", "plugin.json"), "utf-8")).version ?? "");
    const config = env.CLAUDE_CONFIG_DIR || join(env.HOME || env.USERPROFILE || homedir(), ".claude");
    const known = JSON.parse(readFileSync(join(config, "plugins", "known_marketplaces.json"), "utf-8"));
    const loc = String(known?.["agentic-qe"]?.installLocation ?? join(config, "plugins", "marketplaces", "agentic-qe"));
    const theirs = String(JSON.parse(readFileSync(join(loc, ".claude-plugin", "plugin.json"), "utf-8")).version ?? "");
    if (mine && theirs && newer(theirs, mine)) return `agentic-qe ${mine} is running but ${theirs} is available: run claude plugin update agentic-qe@agentic-qe (add --scope project if you installed it per project), then restart Claude Code`;
  } catch { /* no marketplace copy to compare with */ }
  return null;
}

/** Folders Claude Code should watch for this project, so edits made outside Claude (an editor, git) update the pane, map and dashboard. */
export function watchPathsFor(root: string): string[] {
  if (!qeActive(root)) return [];
  const dirs = new Set<string>([join(root, "docs", "qe"), join(root, "results")]);
  for (const f of scanTests(root).files) dirs.add(join(root, dirname(f.path)));
  return [...dirs].filter((d) => existsSync(d)).slice(0, 60);
}

export function run(): void {
  const root = projectRoot(readInput());
  const w = sessionWarnings(root);
  const watchPaths = watchPathsFor(root);
  if (!w.length && !watchPaths.length) return;
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: "SessionStart", ...(w.length ? { additionalContext: w.join(" | ") } : {}), ...(watchPaths.length ? { watchPaths } : {}) } }));
}

if (isMain(import.meta.url)) run();
