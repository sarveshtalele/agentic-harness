import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { spawn, type ChildProcess } from "node:child_process";
import { isMain, projectRoot, safeWrite } from "../../../hooks/src/hook-common.ts";

export interface PlanEntry { caseId: string; url: string; title?: string }
export interface EvidenceRow { caseId: string; url: string; screenshot?: string; snapshot?: string; ok: boolean; error?: string }

const DEFAULT_CMD = "npx -y @playwright/mcp@0.0.83 --headless --isolated";
const TIMEOUT_MS = 60_000;
const REQUIRED = ["browser_navigate", "browser_snapshot", "browser_take_screenshot"];

/** One JSON-RPC message per line (MCP stdio transport). */
export const frame = (msg: unknown): string => JSON.stringify(msg) + "\n";

/** Splits a stream buffer into complete messages; returns the unfinished tail. Non-JSON lines are ignored. */
export function parseLines(buf: string): { messages: any[]; rest: string } {
  const parts = buf.split("\n");
  const rest = parts.pop() ?? "";
  const messages: any[] = [];
  for (const l of parts) {
    if (!l.trim()) continue;
    try { messages.push(JSON.parse(l)); } catch { /* server log noise */ }
  }
  return { messages, rest };
}

const LOCAL_HOSTS = ["localhost", "127.0.0.1", "::1"];
const hostOf = (u: string): string | null => { try { return new URL(u).hostname.replace(/^\[|\]$/g, "").toLowerCase(); } catch { return null; } };
const portOf = (u: URL): number => Number(u.port || (u.protocol === "https:" ? 443 : 80));
// ponytail: well-known service ports stay blocked even when a plan names them; a deny list is a ceiling, `--port` / BASE_URL are the real policy.
const SENSITIVE_PORTS = new Set([22, 2375, 2376, 2379, 3306, 5432, 6379, 9200, 10250, 11211, 27017]);

/**
 * Hosts a plan may navigate to. BASE_URL set: only its host (and, in urlError, only its exact host+port).
 * Not set: loopback only. There is no host override; the CLI has none either.
 */
export function allowedHosts(_extra: string[] = [], env = process.env): string[] {
  const base = env.BASE_URL ? hostOf(env.BASE_URL) : null;
  return base ? [base] : LOCAL_HOSTS;
}

/** Loopback ports named by the plan's own localhost URLs: the only ports a no-BASE_URL run (and its redirects) may use unless `--port` says otherwise. */
export const planPorts = (plan: unknown): number[] =>
  [...new Set((Array.isArray(plan) ? plan : []).flatMap((e: any) => { try { const u = new URL(String(e?.url)); return LOCAL_HOSTS.includes(u.hostname.replace(/^\[|\]$/g, "").toLowerCase()) ? [portOf(u)] : []; } catch { return []; } }))];

/**
 * Error for one URL, or null. With BASE_URL: exactly its host and port. Without: loopback, port 1024-65535, not a well-known service port,
 * and one of `ports` (from `--port`, else the plan's own localhost URLs).
 */
export function urlError(url: unknown, hosts: string[], env = process.env, ports: number[] = []): string | null {
  if (typeof url !== "string") return "url must be a string";
  let u: URL;
  try { u = new URL(url); } catch { return "url is not a valid URL"; }
  if (u.protocol !== "http:" && u.protocol !== "https:") return `url scheme '${u.protocol}' is not allowed (http/https only)`;
  const h = u.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  if (!hosts.includes(h)) return `host '${h}' is not allowed (only ${env.BASE_URL ? "the origin of BASE_URL" : "localhost"})`;
  const port = portOf(u);
  let base: URL | null = null;
  try { base = env.BASE_URL ? new URL(env.BASE_URL) : null; } catch { /* invalid BASE_URL: treated as unset */ }
  if (base) return port === portOf(base) ? null : `port ${port} is not allowed (BASE_URL's port is ${portOf(base)})`;
  if (port < 1024 || port > 65535 || SENSITIVE_PORTS.has(port) || !ports.includes(port)) return `loopback port ${port} is not allowed (use BASE_URL, or --port)`;
  return null;
}

/** The "Page URL:" the Playwright MCP server reports after navigating or snapshotting; null when absent. */
export const pageUrlOf = (text: string): string | null => text.match(/Page URL:\s*(\S+)/i)?.[1] ?? null;

/**
 * Error when the page ended on a URL (after redirects) that the policy does not allow.
 * ponytail: checked AFTER navigation (the Playwright MCP server has no pre-navigation origin filter, so a redirect target gets one blind GET),
 * and a response without "Page URL:" passes. Upgrade: run the server with its own --allowed-origins option.
 */
export function finalUrlError(text: string, hosts: string[], env = process.env, ports: number[] = []): string | null {
  const final = pageUrlOf(text);
  if (!final || /^about:/i.test(final)) return null;
  const bad = urlError(final, hosts, env, ports);
  return bad ? `redirected to ${final}: ${bad}` : null;
}

const CASE_ID = /^[A-Za-z0-9._-]{1,64}$/;

/** Returns error strings; empty means the plan is valid. Host policy is checked per entry at capture time. */
export function validatePlan(plan: unknown): string[] {
  if (!Array.isArray(plan) || !plan.length) return ["plan must be a non-empty array"];
  return plan.flatMap((e, i) => {
    const bad: string[] = [];
    if (!e || typeof e.caseId !== "string" || !CASE_ID.test(e.caseId) || e.caseId === "." || e.caseId === "..") bad.push(`plan[${i}]: caseId must match ${CASE_ID}`);
    if (!e || typeof e.url !== "string" || !/^https?:\/\//i.test(e.url)) bad.push(`plan[${i}]: url must be http(s)`);
    return bad;
  });
}

/** Pulls text / first image out of a tools/call result; throws on isError. */
export function extractResult(result: any): { text: string; image?: Buffer } {
  const content: any[] = Array.isArray(result?.content) ? result.content : [];
  const text = content.filter((c) => c.type === "text").map((c) => c.text).join("\n");
  if (result?.isError) throw new Error(text || "tool returned isError");
  const img = content.find((c) => c.type === "image" && typeof c.data === "string");
  return { text, image: img ? Buffer.from(img.data, "base64") : undefined };
}

class Client {
  private id = 0;
  private buf = "";
  private pending = new Map<number, { ok: (r: any) => void; fail: (e: Error) => void }>();
  private child: ChildProcess;
  constructor(child: ChildProcess) {
    this.child = child;
    child.stdout!.on("data", (d) => {
      const { messages, rest } = parseLines(this.buf + d.toString());
      this.buf = rest;
      for (const m of messages) {
        const p = this.pending.get(m.id);
        if (!p) continue;
        this.pending.delete(m.id);
        m.error ? p.fail(new Error(m.error.message ?? "rpc error")) : p.ok(m.result);
      }
    });
    child.on("exit", (c) => this.pending.forEach((p) => p.fail(new Error(`MCP server exited (code ${c})`))));
    child.on("error", (e) => this.pending.forEach((p) => p.fail(e)));
  }
  request(method: string, params: unknown, timeoutMs = TIMEOUT_MS): Promise<any> {
    const id = ++this.id;
    return new Promise((ok, fail) => {
      const t = setTimeout(() => { this.pending.delete(id); fail(new Error(`timeout after ${timeoutMs / 1000}s waiting for ${method}`)); }, timeoutMs);
      this.pending.set(id, { ok: (r) => { clearTimeout(t); ok(r); }, fail: (e) => { clearTimeout(t); fail(e); } });
      this.child.stdin!.write(frame({ jsonrpc: "2.0", id, method, params }));
    });
  }
  notify(method: string) { this.child.stdin!.write(frame({ jsonrpc: "2.0", method })); }
  call(name: string, args: unknown) { return this.request("tools/call", { name, arguments: args }); }
}

/**
 * AGENTIC_QE_MCP_CMD is a trusted local override for developers (e.g. a fake server in tests).
 * It runs via spawn WITHOUT a shell, and is refused if it contains shell metacharacters.
 */
export function checkCmd(cmd: string): string {
  if (/[;&|`$<>(){}\\"'\n\r*?~!#]/.test(cmd)) throw new Error("AGENTIC_QE_MCP_CMD contains shell metacharacters; refusing to run it");
  return cmd;
}

export async function captureEvidence(plan: PlanEntry[], outDir: string, cmd = process.env.AGENTIC_QE_MCP_CMD || DEFAULT_CMD, timeoutMs = TIMEOUT_MS, ports: number[] = [], root = projectRoot({})): Promise<EvidenceRow[]> {
  const errors = validatePlan(plan);
  if (errors.length) throw new Error(errors.join("\n"));
  checkCmd(cmd);
  const hosts = allowedHosts();
  if (!ports.length) ports = planPorts(plan);
  const put = (name: string, data: string | Uint8Array) => safeWrite(resolve(outDir, name), data, root);
  const [bin, ...args] = cmd.split(/\s+/).filter(Boolean);
  const child = spawn(bin, args, { stdio: ["pipe", "pipe", "ignore"] });
  const c = new Client(child);
  const rows: EvidenceRow[] = [];
  try {
    await c.request("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "agentic-qe", version: "1.3.0" } }, timeoutMs);
    c.notify("notifications/initialized");
    const names: string[] = ((await c.request("tools/list", {}, timeoutMs))?.tools ?? []).map((t: any) => t.name);
    const lacking = REQUIRED.filter((t) => !names.includes(t));
    if (lacking.length) throw new Error(`MCP server is missing required tools: ${lacking.join(", ")}`);
    for (const e of plan) {
      const row: EvidenceRow = { caseId: e.caseId, url: e.url, ok: false };
      const bad = urlError(e.url, hosts, process.env, ports);
      if (bad) { row.error = bad; rows.push(row); continue; }
      try {
        const nav = extractResult(await c.request("tools/call", { name: "browser_navigate", arguments: { url: e.url } }, timeoutMs));
        const navBad = finalUrlError(nav.text, hosts, process.env, ports);
        if (navBad) throw new Error(navBad);
        const snap = extractResult(await c.request("tools/call", { name: "browser_snapshot", arguments: {} }, timeoutMs));
        const snapBad = finalUrlError(snap.text, hosts, process.env, ports);
        if (snapBad) throw new Error(snapBad);
        put(`${e.caseId}.snapshot.md`, snap.text);
        row.snapshot = `${e.caseId}.snapshot.md`;
        const shot = extractResult(await c.request("tools/call", { name: "browser_take_screenshot", arguments: {} }, timeoutMs));
        if (!shot.image) throw new Error("screenshot call returned no image content");
        put(`${e.caseId}.png`, shot.image);
        row.screenshot = `${e.caseId}.png`;
        row.ok = true;
      } catch (err) { row.error = (err as Error).message; }
      rows.push(row);
    }
    await c.request("tools/call", { name: "browser_close", arguments: {} }, 5000).catch(() => {});
  } finally {
    child.kill();
    put("mcp-evidence.json", JSON.stringify(rows, null, 2) + "\n");
  }
  return rows;
}

if (isMain(import.meta.url)) {
  const { positionals: [planFile, outDir], values: { port } } = parseArgs({ allowPositionals: true, options: { port: { type: "string", multiple: true } } });
  if (!planFile || !outDir) {
    console.error("usage: node mcp-evidence.ts <plan.json> <out-dir> [--port <n>]...   (BASE_URL set: only its origin; else localhost on --port, default the plan's own localhost ports)");
    process.exit(2);
  }
  try {
    const rows = await captureEvidence(JSON.parse(readFileSync(planFile, "utf-8")), outDir, undefined, undefined, (port ?? []).map(Number).filter((n) => Number.isInteger(n)));
    for (const r of rows) console.log(`${r.ok ? "ok  " : "FAIL"} ${r.caseId} ${r.url}${r.error ? ` (${r.error})` : ""}`);
    process.exit(rows.every((r) => r.ok) ? 0 : 1);
  } catch (e) {
    console.error(`mcp-evidence: ${(e as Error).message}`);
    process.exit(1);
  }
}
