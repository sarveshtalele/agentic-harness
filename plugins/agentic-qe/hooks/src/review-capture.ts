// Created 2026-11-03 13:20 IST by agentic-qe 1.5.0.
// SubagentStop hook: records the confidence-reviewer's and coverage-auditor's own answer as the run's review record.
// The model used to write confidence.json itself and raise scores until they passed; now only this hook writes the
// review files (the write guard refuses everyone else), each stamped with the agent and a hash of its message.
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { type HookInput, projectRoot, qeActive, isMain, readInput, safeWrite, emitContext } from "./hook-common.ts";
import { readJsonDoc, docItems } from "./layout.ts";
import { CAPTURED } from "./coverage.ts";

type StopInput = HookInput & { agent_type?: string; agent_id?: string; last_assistant_message?: string; agent_transcript_path?: string };

/** The first JSON object in a message: a ```json fence, or the outermost {...}. */
export function jsonIn(text: string): any {
  const fence = /```(?:json)?\s*\n([\s\S]*?)```/.exec(text);
  for (const s of [fence?.[1], text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1)]) {
    if (!s) continue;
    try { const v = JSON.parse(s); if (v && typeof v === "object") return v; } catch { /* next */ }
  }
  return null;
}

/** The agent's last text message, from the hook input or its transcript. */
function lastMessage(input: StopInput): string {
  if (typeof input.last_assistant_message === "string" && input.last_assistant_message.trim()) return input.last_assistant_message;
  try {
    const p = String(input.agent_transcript_path ?? "");
    if (!p || statSync(p).size > 50 * 1024 * 1024) return "";
    const lines = readFileSync(p, "utf-8").trim().split("\n").reverse();
    for (const l of lines) {
      const r = JSON.parse(l);
      const content = r?.message?.role === "assistant" ? r.message.content : null;
      const t = Array.isArray(content) ? content.filter((c: any) => c?.type === "text").map((c: any) => c.text).join("\n") : typeof content === "string" ? content : "";
      if (t.trim()) return t;
    }
  } catch { /* unreadable transcript */ }
  return "";
}

function runApp(root: string): string | null {
  try { const a = String(JSON.parse(readFileSync(join(root, ".qe", "run.json"), "utf-8")).app ?? ""); if (/^[A-Za-z0-9._-]{1,64}$/.test(a)) return a; } catch { /* no run */ }
  try { const d = readdirSync(join(root, "docs", "qe")).filter((n) => statSync(join(root, "docs", "qe", n)).isDirectory()); return d.length === 1 ? d[0] : null; } catch { return null; }
}

/** Records one agent answer. Returns the file written (relative to the project), or why nothing was. */
export function capture(input: StopInput, root: string): { file?: string; note?: string } {
  const agent = String(input.agent_type ?? "").replace(/^[^:]*:/, ""); // "agentic-qe:confidence-reviewer" -> "confidence-reviewer"
  const which = agent === CAPTURED.confidence ? "confidence" : agent === CAPTURED.audit ? "audit" : null;
  if (!which || !qeActive(root)) return {};
  const app = runApp(root);
  if (!app) return { note: `agentic-qe: ${agent} finished, but no run or app was found; nothing recorded` };
  const msg = lastMessage(input);
  const answer = jsonIn(msg);
  const kind = String(answer?.kind ?? "").toLowerCase();
  const list = which === "confidence" ? "items" : "verdicts";
  if (!answer || !(kind === "design" || kind === "code") || !Array.isArray(answer[list])) {
    return { note: `agentic-qe: ${agent}'s answer was not one JSON object with "kind" ("design" or "code") and "${list}"; nothing recorded. Run it again.` };
  }
  const rel = `docs/qe/${app}/${kind === "design" ? "04-design" : "05-generation"}/${which}.json`;
  const abs = join(root, rel);
  // several runs of the agent (one per area) add up: a later answer for the same case replaces the earlier one
  const before = existsSync(abs) ? readJsonDoc(abs) : null;
  const key = (x: any) => String(x?.tc_id ?? x?.caseId ?? x?.id ?? "").toUpperCase();
  const merged = new Map<string, any>(docItems(before, list).map((x: any) => [key(x), x]));
  for (const x of answer[list]) if (key(x)) merged.set(key(x), x);
  const sha256 = createHash("sha256").update(msg).digest("hex");
  const doc = {
    _capture: { agent_type: agent, agent_id: String(input.agent_id ?? ""), at: new Date().toISOString(), sha256, note: "Recorded by the agentic-qe SubagentStop hook from the agent's own answer. Do not edit." },
    kind, [list]: [...merged.values()]
  };
  safeWrite(abs, JSON.stringify(doc, null, 1) + "\n", root);
  return { file: rel, note: `agentic-qe recorded ${answer[list].length} ${which === "confidence" ? "reviews" : "verdicts"} from ${agent} in ${rel}. Do not write that file yourself.` };
}

if (isMain(import.meta.url)) {
  const input = readInput() as StopInput;
  try { const r = capture(input, projectRoot(input)); if (r.note) emitContext("SubagentStop", r.note); } catch (e) { emitContext("SubagentStop", `agentic-qe could not record the review: ${(e as Error).message}`); }
}
