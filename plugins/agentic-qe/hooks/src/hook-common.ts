import { existsSync, readFileSync, realpathSync, lstatSync, statSync, mkdirSync, writeFileSync, renameSync, unlinkSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { tmpdir } from "node:os";
import { join, resolve, relative, isAbsolute, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { readAnchor, ledgerTrust } from "./memory-logger.ts";

export interface HookInput {
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  cwd?: string;
  turn_id?: string;
  session_id?: string;
  prompt?: string;
}

export type Decision = { decision: "allow" | "deny" | "ask"; reason: string };

/** Plugin install dir: Claude Code sets CLAUDE_PLUGIN_ROOT, Codex sets PLUGIN_ROOT. */
export const pluginRoot = (env = process.env): string | undefined => env.CLAUDE_PLUGIN_ROOT || env.PLUGIN_ROOT || undefined;

export function projectRoot(input: HookInput, env = process.env): string {
  const proj = env.CLAUDE_PROJECT_DIR ? resolve(env.CLAUDE_PROJECT_DIR) : "";
  // a session that moved to another folder keeps the old CLAUDE_PROJECT_DIR; its cwd then names the real project.
  // Only while no run is active there: otherwise `cd` out of an active project would switch its guards off.
  // ponytail: a moved session can still cd out of the new project; fix needs the harness to refresh CLAUDE_PROJECT_DIR
  if (proj && input.cwd && !isInside(proj, resolve(input.cwd)) && !qeActive(proj, env)) {
    // from a subfolder, the project is the nearest folder above with an active run (AQE140-002)
    for (let d = resolve(input.cwd); ; d = dirname(d)) { if (qeActive(d, env)) return d; if (dirname(d) === d) break; }
    return resolve(input.cwd);
  }
  return proj || resolve(input.cwd || process.cwd());
}

/** Real paths of the OS temp folder (macOS tmpdir is a symlink into /private/var), plus /tmp. */
export function tempRoots(): string[] {
  return [...new Set([tmpdir(), "/tmp", "/private/tmp"].map((p) => { try { return realpathSync(p); } catch { return resolve(p); } }))];
}

/** A QE run was started here iff <root>/.qe exists OR a ledger anchor does (so deleting .qe/ does not switch the guards off). */
export function qeActive(root: string, env = process.env): boolean {
  return lexists(join(root, ".qe")) || (readAnchor(root, env)?.count ?? 0) > 0;
}

/** Claude Code on Windows runs Bash through Git Bash, which writes C:\x as /c/x; Node needs the drive form. */
export function shellPath(p: string, platform = process.platform): string {
  const m = platform === "win32" ? /^\/([a-zA-Z])(\/.*)?$/.exec(p) : null;
  return m ? `${m[1].toUpperCase()}:${m[2] ?? "/"}` : p;
}

export function isInside(root: string, abs: string): boolean {
  const rel = relative(root, abs);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

export function emitDecision(d: Decision | null): void {
  if (!d) return;
  console.log(JSON.stringify({
    hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: d.decision, permissionDecisionReason: d.reason }
  }));
}

export function isMain(metaUrl: string): boolean {
  return !!process.argv[1] && resolve(process.argv[1]) === fileURLToPath(metaUrl);
}

export function readInput(): HookInput {
  try {
    return JSON.parse(readFileSync(0, "utf-8")) as HookInput;
  } catch {
    return {};
  }
}

export type Host = "claude" | "codex";

/** Codex sends turn_id and sets PLUGIN_ROOT; Claude Code sets CLAUDE_CODE_ENTRYPOINT / CLAUDECODE. */
export function detectHost(input: HookInput, env = process.env): Host {
  if (input.turn_id !== undefined) return "codex";
  return pluginRoot(env) && !env.CLAUDE_CODE_ENTRYPOINT && !env.CLAUDECODE ? "codex" : "claude";
}

export function lexists(p: string): boolean {
  try { lstatSync(p); return true; } catch { return false; }
}

export function realRootOf(root: string): string {
  try { return realpathSync(root); } catch { return root; }
}

/**
 * Real path of p: realpath of the nearest existing ancestor plus the missing tail.
 * bad = a dangling symlink sits on the path (its target is unknowable, treat as escape).
 */
export function resolveReal(root: string, p: string): { abs: string; real: string; bad: boolean } {
  const abs = resolve(root, p);
  const tail: string[] = [];
  let cur = abs;
  for (;;) {
    try {
      return { abs, real: join(realpathSync(cur), ...tail), bad: false };
    } catch {
      if (lexists(cur)) return { abs, real: abs, bad: true };
      const up = dirname(cur);
      if (up === cur) return { abs, real: abs, bad: true };
      tail.unshift(basename(cur));
      cur = up;
    }
  }
}

/** Codex path approvals; honoured only while the run's ledger is trusted (a shipped approvals.json is not). */
export function approvedPaths(root: string): string[] {
  try {
    const t = ledgerTrust(root);
    if (!t.trusted || t.reason !== "ok") return []; // "ok" = a real, anchored, verified ledger; a bare shipped .qe/ is not enough
    const p = JSON.parse(readFileSync(join(root, ".qe", "approvals.json"), "utf-8")).paths;
    return Array.isArray(p) ? p.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** Decision for creating a new file. Codex has no "ask", so it needs a prior user approval recorded by approval-hook. */
export function newFileDecision(root: string, rel: string, askReason: string, host: Host): Decision | null {
  if (host !== "codex") return { decision: "ask", reason: askReason };
  const ok = approvedPaths(root);
  const dir = dirname(rel);
  if (ok.includes(rel) || (dir !== "." && ok.includes(dir + "/"))) return null;
  return { decision: "deny", reason: `agentic-qe: creating ${rel} needs your approval. Reply exactly: approve create ${rel}` };
}

export function emitContext(event: string, text: string): void {
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: event, additionalContext: text } }));
}

export const SECRETS: [string, RegExp][] = [
  ["AWS access key", /AKIA[0-9A-Z]{16}/],
  ["private key block", /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
  ["GitHub token", /(ghp_|gho_|github_pat_)[A-Za-z0-9_]{10,}/],
  ["Anthropic API key", /sk-ant-/],
  ["Slack token", /xox[baprs]-/],
  ["hard-coded credential", /(api[_-]?key|secret|password)\s*[:=]\s*['"][^'"]{8,}/i]
];

export function findSecret(content: string): string | null {
  return SECRETS.find(([, re]) => re.test(content))?.[0] ?? null;
}

/** Masks secrets (and the rest of the token that follows a known prefix) so command text can be logged. */
export function redact(text: string): string {
  let out = text.replace(/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*/, "[REDACTED]");
  for (const [, re] of SECRETS) out = out.replace(new RegExp(re.source + "[A-Za-z0-9_-]*", re.flags + "g"), "[REDACTED]");
  // ponytail: generic credential shapes only (bearer tokens, user:pass@ URLs, --password/--token flags)
  return out
    .replace(/(bearer\s+)[A-Za-z0-9._~+\/=-]{8,}/gi, "$1[REDACTED]")
    .replace(/((?:authorization|x-api-key):\s*)[^'"\s]+(?:\s+[^'"\s]+)?/gi, "$1[REDACTED]")
    .replace(/(\s(?:-u|--user)[= ]\s*['"]?[^:\s'"]+:)[^\s'"]+/g, "$1[REDACTED]")
    .replace(/(:\/\/[^\/\s:@]+:)[^@\s]+@/g, "$1[REDACTED]@")
    .replace(/\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|ACCESS_KEY)[A-Z0-9_]*)=\S+/g, "$1=[REDACTED]")
    .replace(/(--?(?:password|passwd|token|api-?key|secret)[= ])\S+/gi, "$1[REDACTED]");
}

/**
 * Writes a file only if neither the target nor any ancestor below root is a symlink and the real path stays inside root.
 * Temp file + rename, so a reader never sees a partial file. ponytail: check-then-write has a tiny TOCTOU window; fine against planted repo symlinks.
 */
export function safeWrite(path: string, data: string | Uint8Array, root: string, opts: { mode?: number } = {}): void {
  const base = resolve(root);
  const abs = resolve(base, path);
  if (!isInside(base, abs) || abs === base) throw new Error(`refusing to write outside ${root}: ${path}`);
  for (let p = abs; p !== base && p !== dirname(p); p = dirname(p)) {
    if (lexists(p) && lstatSync(p).isSymbolicLink()) throw new Error(`refusing to write through symlink: ${p}`);
  }
  const { real, bad } = resolveReal(base, abs);
  if (bad || !isInside(realRootOf(base), real)) throw new Error(`refusing to write outside ${root}: ${path}`);
  mkdirSync(dirname(abs), { recursive: true });
  const mode = opts.mode ?? (lexists(abs) ? statSync(abs).mode & 0o777 : 0o644);
  const tmp = join(dirname(abs), `.${basename(abs)}.${process.pid}.${randomBytes(4).toString("hex")}.tmp`);
  try {
    writeFileSync(tmp, data, { mode, flag: "wx" });
    renameSync(tmp, abs);
  } catch (e) {
    try { unlinkSync(tmp); } catch { /* nothing to clean */ }
    throw e;
  }
}

/** Local time with a numeric UTC offset, e.g. 2026-10-26T18:00:11+05:30 (used by every generated document). */
export function localIso(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? "+" : "-";
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}${sign}${p(Math.floor(Math.abs(off) / 60))}:${p(Math.abs(off) % 60)}`;
}
