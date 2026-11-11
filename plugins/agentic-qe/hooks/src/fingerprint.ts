// Created 2026-11-03 13:35 IST by agentic-qe 1.5.0.
// What a gate approved, as a fingerprint of its files. An approval records it; when the files differ later, by any tool
// (Write, Edit, Bash, the dashboard), the gate reads as REOPENED until the user approves it again. Before 1.5.0 only a
// dashboard edit reopened a gate, so the model could change an approved manifest without anyone noticing.
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { GATE_PHASES, PHASES, HOOK_OWNED, findDoc, readJsonDoc, docItems } from "./layout.ts";

const cache = new Map<string, { key: string; sha: string }>();
/** Small files by content; large ones (screenshots) by size and modification time. Cached per process. */
function stamp(p: string): string | null {
  try {
    const s = statSync(p);
    if (!s.isFile()) return null;
    const key = `${s.size}:${s.mtimeMs}`;
    if (s.size > 256 * 1024) return `size:${key}`;
    const hit = cache.get(p);
    if (hit && hit.key === key) return hit.sha;
    const sha = createHash("sha256").update(readFileSync(p)).digest("hex").slice(0, 32);
    cache.set(p, { key, sha });
    return sha;
  } catch { return null; }
}

function walk(dir: string, out: string[], depth = 0): void {
  if (depth > 6) return;
  let entries: import("node:fs").Dirent[] = [];
  try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, out, depth + 1);
    else if (e.isFile()) out.push(p);
  }
}

/** Fingerprint of everything gate N approves for <app>: its phase folders, plus the generated tests for Gate 4. */
export function gateFingerprint(root: string, app: string, gate: number): Record<string, string> {
  const docs = join(root, "docs", "qe", app);
  const files: string[] = [];
  for (const id of GATE_PHASES[gate] ?? []) {
    const dir = PHASES.find((p) => p.id === id)?.dir;
    if (dir) walk(join(docs, dir), files);
  }
  if (gate === 4) {
    for (const f of docItems(readJsonDoc(findDoc(docs, "generation.manifest")) ?? {}, "files")) {
      const p = String(typeof f === "string" ? f : f?.path ?? "");
      if (p) files.push(resolve(root, p));
    }
  }
  const out: Record<string, string> = {};
  for (const f of files) {
    const rel = relative(root, f).replace(/\\/g, "/");
    if (rel.startsWith("..") || HOOK_OWNED.test(rel) || /\.meta\.json$/.test(rel) || /\/09-release\/dashboard\.html$/.test(rel)) continue;
    const s = stamp(f);
    if (s) out[rel] = s;
  }
  return out;
}

/** The files that differ from what was approved (changed, added or removed), or [] when it still matches. */
export function changedSince(approved: Record<string, string>, now: Record<string, string>): string[] {
  const keys = new Set([...Object.keys(approved), ...Object.keys(now)]);
  return [...keys].filter((k) => approved[k] !== now[k]).sort();
}
