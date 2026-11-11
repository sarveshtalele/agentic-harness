// Created 2026-11-03 16:10 IST by agentic-qe 1.6.0.
// Runs the pandas/numpy validator (validators/qe_validate.py) on a run's coverage and returns its verdict. The approval
// hook refuses a gate the validator fails, the same way it refuses a gate the coverage check fails.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { homeAnchorDir } from "./memory-logger.ts";
import { safeWrite } from "./hook-common.ts";
import type { Coverage } from "./coverage.ts";

export const PINNED = ["pandas==2.3.3", "numpy==2.3.4"];
const PLUGIN = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const SCRIPT = join(PLUGIN, "validators", "qe_validate.py");

export interface Finding { check: string; message: string; ids: string[] }
export interface Verdict { validator: string; gate: number; ok: boolean; errors: Finding[]; warnings: Finding[]; metrics: Record<string, unknown>; suspects: { case: string; scenario: string; similarity: number; audit?: string }[]; brief: string }

/** The validator's own environment: <home>/.agentic-qe/py, created by `agentic-qe.ts validator` (qe-doctor). */
export const validatorHome = (env = process.env): string => join(homeAnchorDir(env), "py");
const venvPython = (dir: string): string => (process.platform === "win32" ? join(dir, "Scripts", "python.exe") : join(dir, "bin", "python"));

let resolved: { python: string; probe: string } | null | undefined;
/** The first Python that imports pandas and numpy: the validator's own environment, a development .venv, then PATH. */
export function findPython(env = process.env): { python: string; probe: string } | null {
  if (resolved !== undefined) return resolved;
  const candidates = [venvPython(validatorHome(env)), venvPython(join(PLUGIN, ".venv"))].filter(existsSync)
    .concat(process.platform === "win32" ? ["python", "py"] : ["python3", "python"]);
  for (const py of candidates) {
    try {
      const args = py === "py" ? ["-3", SCRIPT, "--probe"] : [SCRIPT, "--probe"];
      const r = spawnSync(py, args, { encoding: "utf-8", timeout: 15000, windowsHide: true });
      if (r.status === 0 && /"pandas"/.test(r.stdout)) return (resolved = { python: py === "py" ? "py -3" : py, probe: r.stdout.trim() });
    } catch { /* next */ }
  }
  return (resolved = null);
}
/** Forget the cached interpreter (tests, and after qe-doctor set one up). */
export const resetPython = () => { resolved = undefined; };

export const SETUP_HINT = "the pandas/numpy validator is not set up: run /agentic-qe:qe-doctor (it creates the validator's Python environment with pandas and numpy)";

/** Runs the validator for one gate. null with a reason when no usable Python is found or it fails. */
export function runValidator(cov: Coverage, gate: number, env = process.env): { verdict: Verdict | null; error?: string } {
  const py = findPython(env);
  if (!py) return { verdict: null, error: SETUP_HINT };
  const [cmd, ...pre] = py.python.split(" ");
  const r = spawnSync(cmd, [...pre, SCRIPT], { input: JSON.stringify({ gate, coverage: cov }), encoding: "utf-8", timeout: 20000, windowsHide: true, maxBuffer: 32 * 1024 * 1024 });
  if (r.status !== 0) return { verdict: null, error: `the validator failed: ${(r.stderr || r.error?.message || "no output").trim().split("\n").slice(-1)[0]}` };
  try { return { verdict: JSON.parse(r.stdout) as Verdict }; } catch { return { verdict: null, error: "the validator printed no verdict" }; }
}

/** Writes docs/qe/<app>/validation.json (hook-owned) and returns the verdict text for a refusal or a check. */
export function recordValidation(root: string, app: string, gate: number, cov: Coverage, env = process.env): { ok: boolean; lines: string[]; verdict: Verdict | null } {
  const { verdict, error } = runValidator(cov, gate, env);
  const docs = join(root, "docs", "qe", app);
  if (existsSync(docs)) safeWrite(join(docs, "validation.json"), JSON.stringify(verdict ?? { gate, ok: false, error }, null, 1) + "\n", root);
  if (!verdict) return { ok: false, lines: [error ?? SETUP_HINT], verdict: null };
  const lines = verdict.errors.map((e) => `${e.message}${e.ids.length ? `: ${e.ids.slice(0, 25).join(", ")}${e.ids.length > 25 ? " …" : ""}` : ""}`);
  return { ok: verdict.ok, lines, verdict };
}
