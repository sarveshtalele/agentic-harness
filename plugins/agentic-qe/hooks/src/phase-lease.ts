// Created 2026-11-03 17:10 IST by agentic-qe 1.6.0.
// The write window of a QE run. Only a phase command the user sends opens it, and only for that phase's documents (and,
// for generate, heal and sync, the test files). Any other prompt closes it. With no window open, nothing under docs/qe/
// and no test file may be written, and no new file may be created: the plugin never produces output on its own.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { safeWrite } from "./hook-common.ts";
import { PHASES } from "./layout.ts";
import { TEST_FILE } from "./inventory.ts";

/** Phase command -> the phase folders it may write, and whether it may write test files. */
export const SCOPE: Record<string, { dirs: string[]; tests: boolean; extra?: RegExp }> = {
  start: { dirs: ["00-intake"], tests: false },
  discover: { dirs: ["01-discovery"], tests: false },
  stories: { dirs: ["02-requirements"], tests: false },
  requirements: { dirs: ["02-requirements"], tests: false },
  plan: { dirs: ["03-plan"], tests: false },
  design: { dirs: ["04-design"], tests: false },
  data: { dirs: ["04-design"], tests: false },
  generate: { dirs: ["05-generation"], tests: true },
  execute: { dirs: ["06-execution"], tests: false, extra: /^(results|test-results|playwright-report)\// },
  heal: { dirs: ["07-healing", "06-execution"], tests: true, extra: /^(results|test-results)\// },
  trace: { dirs: ["08-traceability"], tests: false },
  sign: { dirs: ["09-release"], tests: false },
  sync: { dirs: ["04-design", "05-generation", "08-traceability"], tests: false }
};

export interface Lease { phase: string; app: string; at: string }
const MAX_AGE_MS = 12 * 60 * 60 * 1000;
const leaseFile = (root: string) => join(root, ".qe", "phase.json");

export function openLease(root: string, phase: string, app: string): void {
  if (!SCOPE[phase] || !/^[A-Za-z0-9._-]{1,64}$/.test(app)) return;
  safeWrite(leaseFile(root), JSON.stringify({ phase, app, at: new Date().toISOString() }) + "\n", root, { mode: 0o600 });
}
export function closeLease(root: string): void {
  try { safeWrite(leaseFile(root), "{}\n", root, { mode: 0o600 }); } catch { /* no run */ }
}
export function currentLease(root: string, now = Date.now()): Lease | null {
  try {
    const l = JSON.parse(readFileSync(leaseFile(root), "utf-8"));
    if (!l || !SCOPE[l.phase] || typeof l.app !== "string" || now - Date.parse(l.at) > MAX_AGE_MS) return null;
    return l as Lease;
  } catch { return null; }
}

const DOC_NAMES = new Set(PHASES.flatMap((p) => Object.values(p.docs).map((f) => `${p.dir}/${f}`)));
/** Files the layout allows inside a phase folder: its documents, evidence, and results copied there. */
const allowedDoc = (inApp: string): boolean => DOC_NAMES.has(inApp) || /^06-execution\/(evidence|results)\//.test(inApp) || /^04-design\/fixtures\//.test(inApp);
export const isTestPath = (rel: string): boolean => TEST_FILE.test(rel.split("/").pop() ?? "") || /(^|\/)(tests?|__tests__|e2e|specs?|playwright)\//.test(rel) || /(^|\/)(playwright|vitest|jest|pytest)\.config\.[a-z]+$|(^|\/)conftest\.py$/.test(rel);

/**
 * Whether the run's write window lets this project-relative path be written. null = the window has no opinion (an
 * existing file outside docs/qe/ and the test folders: ordinary work on the project).
 */
export function windowDecision(root: string, rel: string, isNew: boolean, lease = currentLease(root)): { ok: boolean; reason: string } | null {
  const r = rel.replace(/\\/g, "/");
  const doc = /^docs\/qe\/([^/]+)\/(.+)$/.exec(r);
  const test = isTestPath(r);
  // other project files keep the guard's usual rule: a new one needs the user's yes, file by file
  if (!doc && !test) return null;
  // the window belongs to a live run (.qe/ present; the guards refuse deleting it). A run whose state is gone has no
  // phase commands left to open a window, and its documents can no longer be approved anyway.
  if (!existsSync(join(root, ".qe"))) return null;
  const how = "Only a phase command opens the QE write window (for example /agentic-qe:qe-design <app>); run the command for the phase whose files you need to change, or /agentic-qe:qe-sync <app> to bring the documents in line with the tests.";
  if (!lease) return { ok: false, reason: `no QE phase command is running, so ${r} may not be ${isNew ? "created" : "changed"}. ${how}` };
  const scope = SCOPE[lease.phase];
  if (doc) {
    if (doc[1] !== lease.app) return { ok: false, reason: `${r} belongs to app ${doc[1]}, but the running phase command is for ${lease.app}` };
    const dir = doc[2].split("/")[0];
    if (!scope.dirs.includes(dir)) return { ok: false, reason: `/agentic-qe:qe-${lease.phase} may write ${scope.dirs.map((d) => `docs/qe/${lease.app}/${d}/`).join(", ")} only, not ${r}. ${how}` };
    if (!allowedDoc(doc[2])) return { ok: false, reason: `${doc[2]} is not a document of the QE layout; the plugin does not create extra files in docs/qe/${lease.app}/` };
    return { ok: true, reason: "" };
  }
  return scope.tests || scope.extra?.test(r) ? { ok: true, reason: "" } : { ok: false, reason: `/agentic-qe:qe-${lease.phase} does not write test files (${r}); test files change only in /agentic-qe:qe-generate or /agentic-qe:qe-heal` };
}
