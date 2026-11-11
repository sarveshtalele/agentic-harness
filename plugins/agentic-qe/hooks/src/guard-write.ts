import { relative, dirname } from "node:path";
import { statSync } from "node:fs";
import { anchorDir, homeAnchorDir } from "./memory-logger.ts";
import { HOOK_OWNED } from "./layout.ts";
import { windowDecision } from "./phase-lease.ts";
import { SECRETS, findSecret, type HookInput, type Decision, type Host, projectRoot, qeActive, isInside, emitDecision, isMain, readInput, detectHost, lexists, realRootOf, resolveReal, newFileDecision, tempRoots } from "./hook-common.ts";

export { SECRETS, findSecret };

const deny = (reason: string): Decision => ({ decision: "deny", reason: `agentic-qe: ${reason}` });

/** True if the target's real path is inside the ledger anchor directory (outside the project, hook-owned). */
/** Scratch space: real path inside the OS temp folder. A project that itself lives in the temp folder gets no such exemption (its siblings are not scratch). */
function inTemp(realRoot: string, real: string): boolean {
  const temps = tempRoots();
  return !temps.some((t) => isInside(t, realRoot)) && temps.some((t) => isInside(t, real));
}

export function inAnchorDir(root: string, file: string, env = process.env): boolean {
  const t = resolveReal(root, file);
  // the home folder too: its pointers decide where a shell-started dashboard looks for the anchor
  return t.bad || [anchorDir(env), homeAnchorDir(env)].some((d) => isInside(resolveReal(root, d).real, t.real));
}

/** Shared by guard-write and guard-bash: all checks for one write target. null = no opinion. */
export function checkTarget(root: string, file: string, content: string, active: boolean, host: Host): Decision | null {
  const { abs, real, bad } = resolveReal(root, file);
  const realRoot = realRootOf(root);
  const rel = relative(root, abs).replace(/\\/g, "/");
  if (inAnchorDir(root, file)) return deny("the ledger anchor directory is managed by hooks only");
  if (HOOK_OWNED.test(rel)) return deny(`${rel} is written by the plugin's hooks only (gate reports, coverage map, hand-off, and the reviews recorded from the confidence-reviewer and coverage-auditor agents). Run the agent or the phase again instead`);
  const secretScope = /^(docs\/qe\/|tests?\/)/.test(rel);
  if (!active && !secretScope) return null;
  if (active) {
    // the OS temp folder is scratch space; the anchor dir was refused above and the hook state folder below
    if ((bad || !isInside(realRoot, real)) && (bad || !inTemp(realRoot, real))) return deny(`${file} is outside the project root`);
    const rr = relative(realRoot, real).replace(/\\/g, "/").toLowerCase(); // .QE is .qe on macOS and Windows
    if (rr === ".qe" || rr.startsWith(".qe/")) return deny(".qe/ is managed by hooks only");
    // a hard link shares its content with another path, possibly outside the project
    let links = 1;
    try { const s = statSync(abs); if (s.isFile()) links = s.nlink; } catch { /* new file */ }
    if (links > 1) return host === "codex" ? deny(`${rel} has ${links} hard links; writing it changes the other paths too`) : { decision: "ask", reason: `agentic-qe: ${rel} has ${links} hard links, so writing it also changes the linked file(s), which may be outside the project. Approve?` };
    // the run's write window: QE documents, test files and new files only inside the phase command the user ran
    if (isInside(realRoot, real)) {
      const w = windowDecision(root, rel, !lexists(abs));
      if (w && !w.ok) return deny(w.reason);
    }
  }
  const secret = findSecret(content);
  if (secret) return deny(`content looks like it contains a secret (${secret})`);
  if (!active || lexists(abs)) return null;
  const dir = dirname(abs);
  return newFileDecision(root, rel, lexists(dir)
    ? `agentic-qe: approve creating ${rel}?`
    : `agentic-qe: approve creating folder ${relative(root, dir)} and file ${rel.split("/").pop()}?`, host);
}

/** Codex apply_patch: one entry per touched path; content = added lines only. */
export function parsePatch(text: string): { file: string; content: string }[] {
  const out: { file: string; content: string }[] = [];
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*\*\*\* (?:Add File|Update File|Delete File|Move to): (.+?)\s*$/);
    if (m) out.push({ file: m[1], content: "" });
    else if (line.trimStart().startsWith("+") && out.length) out[out.length - 1].content += line.trimStart().slice(1) + "\n";
  }
  return out;
}

function patchText(ti: Record<string, unknown>): string | null {
  for (const k of ["patch", "input", "command", "cmd"]) {
    const v = ti[k];
    const s = Array.isArray(v) ? v.join("\n") : typeof v === "string" ? v : "";
    if (s.includes("*** Begin Patch") || s.includes("*** Add File:") || s.includes("*** Update File:")) return s;
  }
  return null;
}

/** Pure decision. null = no opinion. */
export function decideWrite(input: HookInput, root: string, env = process.env): Decision | null {
  const ti = input.tool_input ?? {};
  const host = detectHost(input, env);
  const active = qeActive(root, env);
  const targets: { file: string; content: string }[] = [];
  const file = String(ti.file_path ?? ti.notebook_path ?? "");
  const patch = patchText(ti);
  if (patch) targets.push(...parsePatch(patch));
  if (file) {
    const strs = Array.isArray(ti.edits) ? ti.edits.map((e: { new_string?: unknown }) => e?.new_string).filter((v) => typeof v === "string") as string[] : [];
    const single = [ti.content, ti.new_string, ti.new_source].filter((v) => typeof v === "string") as string[];
    // each edit alone, plus all edits joined with no separator so a secret split across edits is still seen
    targets.push({ file, content: [...single, ...strs, strs.join(""), strs.join("\n")].join("\n") });
  }
  let ask: Decision | null = null;
  for (const t of targets) {
    const d = checkTarget(root, t.file, t.content, active, host);
    if (d?.decision === "deny") return d;
    ask ??= d;
  }
  return ask;
}

function main(): void {
  const input = readInput();
  emitDecision(decideWrite(input, projectRoot(input)));
}

if (isMain(import.meta.url)) main();
