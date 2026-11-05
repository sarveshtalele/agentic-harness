// Live QE dashboard: a local server that shows, edits and exports one project's QE run. It never records approvals
// (those come only from the user's typed message) and never runs agents. Stdlib only.
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { spawn } from "node:child_process";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { existsSync, lstatSync, readFileSync, readdirSync, realpathSync, statSync, watch, type FSWatcher } from "node:fs";
import { dirname, extname, join, posix, relative, resolve } from "node:path";
import { parseArgs } from "node:util";
import { isMain, isInside, realRootOf, resolveReal, safeWrite, localIso, findSecret } from "../../../hooks/src/hook-common.ts";
import { appendLedger, readAnchor, anchorId } from "../../../hooks/src/memory-logger.ts";
import { stampFile } from "../../../hooks/src/stamp-metadata.ts";
import { GATE_NAMES, gateStatus } from "../../../hooks/src/on-decision.ts";
import { dashboardLink, dashboardTokenFile } from "../../../hooks/src/approval-hook.ts";
import { PHASES, GATE_PHASES, HOOK_OWNED, findDoc, phaseOfPath, readJsonDoc, docItems } from "../../../hooks/src/layout.ts";
import { buildCoverage, checkGate } from "../../../hooks/src/coverage.ts";
import { scanTests } from "../../../hooks/src/inventory.ts";

/** Paths in the project whose changes never matter to the dashboard. */
const PROJECT_IGNORE = /(^|\/)(node_modules|\.git|\.venv|venv|dist|build|out|bin|obj|target|coverage|\.next|__pycache__|\.pytest_cache|playwright-report|test-results)(\/|$)/;
import { collectTrace, frId, norm, overall, verdict, lowConfidencePasses } from "../../building-qe-dashboard/scripts/build-trace-report.ts";
import { esc, renderMarkdown, renderJsonDoc, parseCsv } from "../../building-qe-dashboard/scripts/html.ts";
import { gateReportMd, gateReportRel, checkReportImages, evidenceImages } from "../../building-qe-dashboard/scripts/gate-report-md.ts";
import { buildZip, type ZipEntry } from "./zip.ts";
import { PAGE_HTML, APP_CSS, APP_JS } from "./dashboard-ui.ts";

const APP = /^[A-Za-z0-9._-]{1,64}$/;
const MAX_READ = 5 * 1024 * 1024, MAX_WRITE = 2 * 1024 * 1024, MAX_ZIP_FILE = 50 * 1024 * 1024;
const PIPELINE = ["qe-start", "qe-discover", "qe-stories", "qe-requirements", "qe-plan", "qe-design", "qe-generate", "qe-execute", "qe-heal", "qe-trace", "qe-sign"];
const GATE_CMD = ["qe-start", "qe-requirements", "qe-plan", "qe-design", "qe-generate", "qe-sign"];
const DOC_EXT = /\.(md|json|csv|txt|ya?ml)$/i, SRC_EXT = /\.(tsx?|jsx?|mjs|py|cs|java|kt|go|rb|php)$/i;
const CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'";

export interface DashOpts { root: string; app?: string; port?: number; env?: NodeJS.ProcessEnv; record?: boolean }
export interface Dash { port: number; token: string; close(): Promise<void> }

const same = (a: string, b: string): boolean => { const x = Buffer.from(a), y = Buffer.from(b); return x.length === y.length && timingSafeEqual(x, y); };
const sha = (b: string | Uint8Array): string => createHash("sha256").update(b).digest("hex");
const kindOf = (p: string): string => {
  const e = extname(p).toLowerCase();
  return e === ".md" ? "md" : e === ".json" ? "json" : e === ".csv" ? "csv" : SRC_EXT.test(e) ? "code" : /^\.(png|jpe?g)$/.test(e) ? "image" : "other";
};
const pre = (s: string): string => `<pre><code>${esc(s)}</code></pre>`;

/** Project-relative path with forward slashes, or null when it is absolute, has "..", a backslash or NUL. */
export function cleanRel(p: unknown): string | null {
  if (typeof p !== "string" || !p || p.includes("\0") || p.includes("\\") || p.startsWith("/") || p.split("/").includes("..")) return null;
  const n = posix.normalize(p).replace(/\/$/, "");
  return n === "." || n.startsWith("../") ? null : n;
}

/** Same-origin URL for an image that a document at `rel` links to (relative to its folder): PNG/JPEG project paths only, never another host. */
export const imageUrl = (rel: string) => (src: string): string | null => {
  if (/^[a-z][a-z0-9+.-]*:|^[\\/]/i.test(src)) return null; // other hosts, schemes and absolute paths never load
  let p: string;
  try { p = posix.join(posix.dirname(rel), decodeURI(src)); } catch { return null; }
  const c = cleanRel(p);
  return c && /\.(png|jpe?g)$/i.test(c) ? `/api/file?path=${encodeURIComponent(c)}` : null;
};

/** Page markup for a document: Markdown with its images and metadata table, JSON as a readable document (never raw), CSV as a table, code as code. Always escaped. */
export function renderDoc(rel: string, text: string): string {
  const ext = extname(rel).toLowerCase();
  if (ext === ".md") {
    const { meta, html } = renderMarkdown(text, { img: imageUrl(rel) });
    const rows = Object.entries(meta).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join("");
    return (rows ? `<table class="meta">${rows}</table>` : "") + html;
  }
  if (ext === ".json") { try { return renderJsonDoc(JSON.parse(text)); } catch (e) { return `<p class="notice bad">Invalid JSON: ${esc((e as Error).message)}</p>` + pre(text); } }
  if (ext === ".csv") {
    const [h = [], ...r] = parseCsv(text).slice(0, 2001);
    return `<div class="scroll"><table><thead><tr>${h.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${r.map((row) => `<tr>${row.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }
  return pre(text);
}

/**
 * First symlink (or Windows junction) on the way to `p`, or null. The root check looks for links rather than comparing
 * spellings, because on Windows the real path can differ only in letter case or 8.3 short names (C:\Users\SARVES~1).
 */
export function symlinkIn(p: string): string | null {
  for (let d = resolve(p); ; d = dirname(d)) {
    try { if (lstatSync(d).isSymbolicLink()) return d; } catch { /* missing: realpath reports it */ }
    if (dirname(d) === d) return null;
  }
}

/** The port every dashboard asks for first: option dashboard_port, else 4173. The next free one is used only when another project holds it. */
export function defaultPort(env: NodeJS.ProcessEnv = process.env): number {
  const n = Number(env.CLAUDE_PLUGIN_OPTION_DASHBOARD_PORT);
  return Number.isInteger(n) && n >= 1024 && n <= 4190 ? n : 4173;
}
export const ALREADY_RUNNING = "this project's dashboard is already running";
/** The project a dashboard on this port serves, or null when nothing or something else answers. */
async function pingProject(port: number): Promise<string | null> {
  try {
    const r = await fetch(`http://127.0.0.1:${port}/api/ping`, { signal: AbortSignal.timeout(800) });
    const j = await r.json() as { service?: string; project?: string };
    return j.service === "agentic-qe-dashboard" && typeof j.project === "string" ? j.project : null;
  } catch { return null; }
}

export async function startDashboard(opts: DashOpts): Promise<Dash> {
  const given = resolve(opts.root), link = symlinkIn(given);
  if (link) throw new Error(`--root must be the real folder, not a symlink: ${link} is a link (use ${realpathSync(given)})`);
  const root = realpathSync(given);
  const env = opts.env ?? process.env;
  const token = randomBytes(32).toString("hex");
  let port = 0;

  const appName = (): string => {
    if (opts.app && APP.test(opts.app)) return opts.app;
    try { const a = String(JSON.parse(readFileSync(join(root, ".qe", "run.json"), "utf-8")).app ?? ""); if (APP.test(a)) return a; } catch { /* no run state */ }
    try { const d = readdirSync(join(root, "docs", "qe"), { withFileTypes: true }).filter((e) => e.isDirectory() && APP.test(e.name)); if (d.length === 1) return d[0].name; } catch { /* no docs */ }
    return "";
  };
  const docsRel = (app: string) => `docs/qe/${app}`;
  const manifestFiles = (app: string): Set<string> => new Set(docItems(readJsonDoc(findDoc(join(root, "docs", "qe", app), "generation.manifest")), "files")
    .map((f: any) => cleanRel(String(typeof f === "string" ? f : f?.path ?? "").replace(/^\.\//, ""))).filter((x): x is string => !!x));

  /** Why this project file may not be edited, or null when it may. */
  const editError = (rel: string, app: string, gates = gateStatus(join(root, ".qe"))): string | null => {
    if (!app) return "no app";
    if (rel === ".qe" || rel.startsWith(".qe/") || rel.startsWith("results/")) return "run state and results are read-only";
    if (/\/gate-\d-report\.md$/.test(rel)) return "gate reports are generated at each approval";
    if (HOOK_OWNED.test(rel)) return "written by the plugin (coverage map, hand-off, reviews recorded from the agents)";
    if (DOC_EXT.test(rel)) return rel.startsWith(docsRel(app) + "/") && !/\.meta\.json$/.test(rel) ? null : "only documents under docs/qe/<app>/ are editable";
    if (SRC_EXT.test(rel)) return !manifestFiles(app).has(rel) ? "not listed in the generation manifest" : ["APPROVED", "REOPENED"].includes(gates[4].status) ? null : "Gate 4 must be approved before test sources can be edited";
    return "file type is not editable";
  };

  /** Real path of a readable project file: inside docs/qe/<app>/, results/, test-results/ or the generation manifest. */
  const locate = (p: unknown, app: string): { real: string; rel: string } | { err: string; status: number } => {
    const rel = cleanRel(p);
    if (!rel || !app) return { err: "bad path", status: 400 };
    const bases = [docsRel(app), "results", "test-results"];
    const base = bases.find((b) => rel === b || rel.startsWith(b + "/")) ?? (SRC_EXT.test(rel) && !/(^|\/)\./.test(rel) && manifestFiles(app).has(rel) ? "." : null); // a manifest may name test sources, never .env or .git/config (AQE141-002)
    if (base === null) return { err: "path is outside docs/qe/<app>/ and results/", status: 403 };
    const r = resolveReal(root, rel), b = resolveReal(root, base);
    if (r.bad || b.bad || !isInside(b.real, r.real) || !isInside(root, r.real)) return { err: "path escapes the project", status: 403 };
    try { if (!statSync(r.real).isFile()) return { err: "not a file", status: 404 }; } catch { return { err: "not found", status: 404 }; }
    return { real: r.real, rel };
  };

  const walk = (dirRel: string, out: { path: string; size: number; mtime: number }[] = [], depth = 0) => {
    let es: import("node:fs").Dirent[] = [];
    try { es = readdirSync(join(root, dirRel), { withFileTypes: true }); } catch { return out; }
    for (const e of es.sort((a, b) => a.name.localeCompare(b.name))) {
      const rel = `${dirRel}/${e.name}`;
      if (e.isSymbolicLink() || e.name === "node_modules" || e.name.endsWith(".tmp")) continue;
      if (e.isDirectory()) { if (depth < 8) walk(rel, out, depth + 1); } else if (e.isFile() && out.length < 3000) { const s = statSync(join(root, rel)); out.push({ path: rel, size: s.size, mtime: s.mtimeMs }); }
    }
    return out;
  };
  const projectFiles = (app: string) => [...(app ? walk(docsRel(app)) : []), ...walk("results")];

  function state() {
    const app = appName();
    const t = collectTrace(root, app);
    const docsDir = join(root, "docs", "qe", app);
    const gates: Record<number, { status: string; timestamp?: string; recorded?: boolean }> = gateStatus(join(root, ".qe"));
    // No run in this folder (an example or a copied run): show the decisions recorded in the saved gate reports,
    // marked as recorded. Display only; approvals and the in-order rule still use the ledger alone.
    // Never where a run started on this machine: deleting run.json must not turn a report's claim into a shown approval.
    const startedHere = Object.keys(t.gates).length > 0 || ((readAnchor(root, env)?.count ?? 0) > 0 && !t.trust.trusted);
    if (app && !startedHere && !existsSync(join(root, ".qe", "run.json"))) {
      for (const g of [0, 1, 2, 3, 4, 5]) {
        let md = "";
        try { md = readFileSync(join(docsDir, gateReportRel(g)), "utf-8"); } catch { continue; }
        const st = /^\| Status \| \S*\s*(APPROVED|REJECTED) \|$/m.exec(md)?.[1], at = /^\| Decided at \| ([0-9T:+.Z-]{10,40}) \|$/m.exec(md)?.[1];
        if (st && gates[g].status === "PENDING") gates[g] = { status: st, timestamp: at, recorded: true };
      }
    }
    const caseReq = (c: { story_id?: string }) => (c.story_id ? norm(frId(c.story_id)) : "");
    const cases = t.cases.map((c) => {
      const id = norm(c.tc_id);
      return { ...c, requirement: c.story_id ? frId(c.story_id) : undefined, result: t.runs.get(id) ?? null, red: t.red.get(id) ?? null, healer: t.healer.get(id) ?? null, files: t.generated.get(id) ?? [], covered: t.covered.get(id) ?? null, fixture: t.fixtures.has(id), confidence: t.confidence.get(id) ?? {} };
    });
    const requirements = t.requirements.map((r) => {
      const mine = t.cases.filter((c) => caseReq(c) === norm(frId(r.id)));
      return { ...r, control: frId(r.id), cases: mine.map((c) => c.tc_id), verdict: verdict(t, mine) };
    });
    const defects = [...t.healer.values()].filter((d) => d.classification.toUpperCase() === "APPLICATION_DEFECT").map((d) => {
      const c = t.cases.find((x) => norm(x.tc_id) === norm(d.tc_id));
      return { tc_id: d.tc_id, scenario: c?.scenario, requirement: c?.story_id ? frId(c.story_id) : undefined, root_cause: d.detail, evidence: d.evidence, fix: d.fix, severity: d.severity, test_file: d.file, message: t.runs.get(norm(d.tc_id))?.message };
    });
    const phases = PHASES.map((p) => ({
      id: p.id, dir: p.dir, title: p.title, gate: p.gate,
      docs: Object.entries(p.docs).map(([k, file]) => {
        const abs = findDoc(docsDir, `${p.id}.${k}`);
        let s: import("node:fs").Stats | null = null;
        try { s = statSync(abs); } catch { /* missing */ }
        const rel = relative(docsDir, abs).replace(/\\/g, "/");
        return { key: `${p.id}.${k}`, name: file, file, rel, path: `${docsRel(app)}/${rel}`, exists: !!s?.isFile(), size: s?.size ?? 0, mtime: s?.mtimeMs ?? 0 };
      })
    }));
    return {
      app, mode: t.mode, generatedAt: localIso(), verdict: overall(t), trust: t.trust, meta: { version: t.version, commit: t.commit, scope: t.scope, frameworks: t.frameworks, levels: t.levels },
      pipeline: PIPELINE,
      coverage: (() => {
        try {
          const cov = buildCoverage(root, app);
          const validation = readJsonDoc(join(docsDir, "validation.json"));
          return { inventory: cov.inventory, validation: validation && typeof validation === "object" ? { gate: validation.gate, ok: validation.ok, errors: (validation.errors ?? []).slice(0, 6), warnings: (validation.warnings ?? []).length, error: validation.error } : null, counts: checkGate(cov, 5).counts, checks: [1, 2, 3, 4, 5].map((g) => { const c = checkGate(cov, g); return { gate: g, ok: c.ok, gaps: c.gaps.slice(0, 8), more: Math.max(0, c.gaps.length - 8) }; }) };
        } catch { return null; }
      })(),
      gates: [0, 1, 2, 3, 4, 5].map((g) => ({ gate: g, name: GATE_NAMES[g], ...gates[g], cmd: GATE_CMD[g], phrase: g === 0 ? `approve gate 0 for ${app || "<app>"}` : `approve gate ${g}`, covers: (GATE_PHASES[g] ?? []).map((id) => PHASES.find((p) => p.id === id)?.title) })),
      // guardrail: every evidence image must appear in the saved Gate 5 report (and no report links a missing image)
      reports: [0, 1, 2, 3, 4, 5].map((g) => {
        const rel = gateReportRel(g);
        let saved: string | null = null;
        try { saved = readFileSync(join(docsDir, rel), "utf-8"); } catch { /* not written yet */ }
        const chk = saved === null ? { missing: [] as string[], broken: [] as string[] } : checkReportImages(docsDir, rel, saved);
        return { gate: g, rel, path: `${docsRel(app)}/${rel}`, exists: saved !== null, missing: g === 5 ? chk.missing : [], broken: chk.broken };
      }),
      evidence: app ? evidenceImages(docsDir) : { valid: [], invalid: [] },
      confidence: t.confidenceSummary, lowPasses: lowConfidencePasses(t),
      phases, requirements, stories: t.stories, cases, executions: t.execRuns, defects, documents: t.documents,
      ledger: t.ledger.slice(-300), ledgerTotal: t.ledgerTotal
    };
  }

  const tree = () => {
    const app = appName(), gates = gateStatus(join(root, ".qe"));
    return projectFiles(app).map((f) => ({ ...f, kind: kindOf(f.path), editable: editError(f.path, app, gates) === null }));
  };

  // ---- responses
  const head = (extra: Record<string, string | string[]> = {}) => ({
    "Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store", "X-Frame-Options": "DENY", ...extra
  });
  const send = (res: ServerResponse, status: number, body: string | Uint8Array, type: string, extra: Record<string, string | string[]> = {}) => { res.writeHead(status, head({ "Content-Type": type, ...extra })); res.end(body); };
  const json = (res: ServerResponse, status: number, v: unknown) => send(res, status, JSON.stringify(v), "application/json; charset=utf-8");
  const fail = (res: ServerResponse, status: number, error: string, extra: object = {}) => json(res, status, { error, ...extra });

  const readBody = (req: IncomingMessage): Promise<string> => new Promise((ok, no) => {
    const parts: Buffer[] = []; let n = 0;
    req.on("data", (c: Buffer) => { n += c.length; if (n > MAX_WRITE + 4096) { no(new Error("body too large")); req.destroy(); } else parts.push(c); });
    req.on("end", () => ok(Buffer.concat(parts).toString("utf-8")));
    req.on("error", no);
  });

  function putFile(res: ServerResponse, raw: string) {
    let b: any;
    try { b = JSON.parse(raw); } catch { return fail(res, 400, "body must be JSON"); }
    const app = appName();
    if (typeof b?.content !== "string" || typeof b?.baseSha !== "string") return fail(res, 400, "path, content and baseSha are required");
    if (Buffer.byteLength(b.content) > MAX_WRITE) return fail(res, 413, "file is larger than 2 MB");
    const rel = cleanRel(b.path);
    if (!rel) return fail(res, 400, "bad path");
    const gates = gateStatus(join(root, ".qe"));
    const why = editError(rel, app, gates);
    if (why) return fail(res, 403, why);
    const loc = locate(rel, app);
    if ("err" in loc) return fail(res, loc.status === 404 ? 404 : 403, loc.err === "not found" ? "only existing files can be edited" : loc.err);
    // the rules above judged the name; write only when the name is the file (no symlinked component), AQE140-007
    if (loc.real !== join(root, rel)) return fail(res, 403, "symlinked paths cannot be edited");
    const secret = findSecret(b.content);
    if (secret) return fail(res, 422, `not saved: the content looks like it contains a secret (${secret})`);
    const cur = sha(readFileSync(loc.real));
    if (cur !== b.baseSha) return fail(res, 409, "the file changed on disk since you opened it", { sha: cur });
    if (extname(rel).toLowerCase() === ".json") { try { JSON.parse(b.content); } catch (e) { return fail(res, 422, `invalid JSON: ${(e as Error).message}`); } }
    const isDoc = rel.startsWith(docsRel(app) + "/");
    safeWrite(loc.real, b.content, root);
    if (isDoc) stampFile(loc.real, root, env);
    const sum = sha(readFileSync(loc.real));
    const phase = isDoc ? phaseOfPath(rel.slice(docsRel(app).length + 1)) : null;
    const gate = phase ? Number(Object.keys(GATE_PHASES).find((g) => GATE_PHASES[Number(g)].includes(phase))) : isDoc ? NaN : 4;
    // no run here (an example, a copied folder): save the file but create no run state
    if (!existsSync(join(root, ".qe"))) return json(res, 200, { sha: sum, reopened: [] });
    appendLedger(join(root, ".qe", "ledger.jsonl"), { type: "doc_edit", source: "dashboard", file: rel, sha256: sum, phase, ...(Number.isInteger(gate) ? { gate } : {}), timestamp: new Date().toISOString() }, root);
    const after = gateStatus(join(root, ".qe"));
    json(res, 200, { sha: sum, reopened: [0, 1, 2, 3, 4, 5].filter((g) => after[g].status === "REOPENED" && gates[g].status !== "REOPENED") });
  }

  function getFile(res: ServerResponse, p: string | null, asRender: boolean) {
    const app = appName(), loc = locate(p, app);
    if ("err" in loc) return fail(res, loc.status, loc.err);
    const { real, rel } = loc;
    const size = statSync(real).size;
    if (size > MAX_READ) return fail(res, 413, "file is larger than 5 MB");
    const data = readFileSync(real);
    if (kindOf(rel) === "image") {
      const png = data.subarray(0, 4).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47])), jpg = data.subarray(0, 3).equals(Buffer.from([0xff, 0xd8, 0xff]));
      const ok = rel.startsWith(`${docsRel(app)}/06-execution/evidence/`) || rel.startsWith("test-results/");
      if (asRender || !ok || !(png && /\.png$/i.test(rel) || jpg && /\.jpe?g$/i.test(rel))) return fail(res, 415, "only PNG or JPEG evidence images can be shown");
      return send(res, 200, data, png ? "image/png" : "image/jpeg");
    }
    if (data.includes(0)) return fail(res, 415, "binary file");
    const text = data.toString("utf-8");
    if (asRender) return json(res, 200, { path: rel, kind: kindOf(rel), sha: sha(data), html: renderDoc(rel, text) });
    json(res, 200, { path: rel, kind: kindOf(rel), content: text, sha: sha(data), size, mtime: statSync(real).mtimeMs, editable: editError(rel, app) === null, reason: editError(rel, app) });
  }

  function zip(res: ServerResponse) {
    const app = appName(), entries: ZipEntry[] = [];
    for (const f of projectFiles(app)) {
      if (f.size > MAX_ZIP_FILE) continue;
      const loc = locate(f.path, app);
      if ("real" in loc) entries.push({ name: f.path, data: readFileSync(loc.real), mtime: new Date(f.mtime) });
    }
    send(res, 200, buildZip(entries), "application/zip", { "Content-Disposition": `attachment; filename="${app || "qe"}-qe-run.zip"` });
  }

  // ---- change stream
  const clients = new Set<ServerResponse>();
  const watchers: FSWatcher[] = [], watched = new Set<string>();
  let pending = new Set<string>(), debounce: NodeJS.Timeout | undefined, lastSig = "";
  const poke = (paths: string[]) => {
    paths.forEach((p) => pending.size < 50 && pending.add(p));
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      const msg = `event: change\ndata: ${JSON.stringify({ paths: [...pending] })}\n\n`;
      pending = new Set();
      for (const c of clients) c.write(msg);
    }, 300);
  };
  const watchDirs = () => [`docs/qe/${appName()}`, "results", ".qe"].filter((d) => d !== "docs/qe/");
  const signature = () => watchDirs().map((d) => walk(d).map((f) => `${f.path}:${f.size}:${f.mtime}`).join("|")).join("#");
  let fellBack = false;
  const attach = () => {
    for (const d of watchDirs()) {
      if (watched.has(d) || !existsSync(join(root, d))) continue;
      try {
        const w = watch(join(root, d), { recursive: true }, (_e, f) => { if (f && !String(f).endsWith(".tmp")) poke([`${d}/${f}`.replace(/\\/g, "/")]); });
        w.on("error", () => { fellBack = true; });
        watchers.push(w); watched.add(d);
      } catch { fellBack = true; }
    }
  };
  attach();
  // the whole project too, so a changed test or source file updates the page (dependencies and build output are ignored)
  try {
    const w = watch(root, { recursive: true }, (_e, f) => {
      const p = String(f ?? "").replace(/\\/g, "/");
      if (!p || p.endsWith(".tmp") || PROJECT_IGNORE.test(p) || watchDirs().some((d) => p.startsWith(d + "/"))) return;
      poke([p]);
    });
    w.on("error", () => { fellBack = true; });
    watchers.push(w);
  } catch { fellBack = true; }
  // test files, by size and time, in case the project watcher misses an event (Windows, network folders)
  const testSig = () => scanTests(root).files.map((f) => `${f.path}:${f.size}:${f.mtimeMs}`).join("|");
  lastSig = signature();
  let lastTests = testSig(), tick = 0;
  const poller = setInterval(() => {
    attach();
    // always compare: file watchers miss events on some systems (Windows, network folders), and approvals must still show
    const s = signature();
    if (s !== lastSig) { lastSig = s; poke(["*"]); }
    if (++tick % 3 === 0) { const t = testSig(); if (t !== lastTests) { lastTests = t; poke(["tests"]); } }
  }, 1500);
  const beat = setInterval(() => { for (const c of clients) c.write(": ping\n\n"); }, 20000);
  poller.unref(); beat.unref();

  // ---- routing
  // Browsers keep cookies per host, not per port: each dashboard has its own cookie name, so one never signs another out.
  const cookieOk = (req: IncomingMessage): boolean => {
    for (const m of (req.headers.cookie ?? "").matchAll(/(?:^|;\s*)qe_dash(?:_(\d+))?=([0-9a-f]+)/g)) {
      if ((m[1] === undefined || Number(m[1]) === port) && same(m[2], token)) return true;
    }
    return false;
  };
  const deny = (res: ServerResponse) => send(res, 401, "<!doctype html><meta charset=utf-8><title>QE dashboard</title><h1>Not signed in</h1><p>Open the link the plugin opened in your browser at the run start, or run <code>/agentic-qe:qe-panel --serve --link</code> to print it again.</p>", "text/html; charset=utf-8");

  async function route(req: IncomingMessage, res: ServerResponse) {
    const host = req.headers.host ?? "";
    if (host !== `127.0.0.1:${port}` && host !== `localhost:${port}`) return fail(res, 403, "bad host");
    if (req.headers.origin !== undefined && req.headers.origin !== `http://${host}`) return fail(res, 403, "bad origin");
    const url = new URL(req.url ?? "/", `http://${host}`);
    const method = req.method ?? "GET";
    if (method !== "GET" && method !== "PUT") return fail(res, 405, "method not allowed");
    const t = url.searchParams.get("token");
    if (method === "GET" && url.pathname === "/" && t !== null) {
      if (!same(t, token)) return deny(res);
      return send(res, 302, "", "text/plain", { Location: "/", "Set-Cookie": `qe_dash_${port}=${token}; HttpOnly; SameSite=Strict; Path=/` });
    }
    // which project this dashboard serves (a hash of its folder), so a second start finds it instead of taking the next port
    if (method === "GET" && url.pathname === "/api/ping") return send(res, 200, JSON.stringify({ service: "agentic-qe-dashboard", project: anchorId(root) }), "application/json");
    if (!cookieOk(req)) return deny(res);
    if (method === "PUT" && !same(String(req.headers["x-qe-token"] ?? ""), token)) return fail(res, 403, "missing X-QE-Token");
    const path = url.pathname, q = url.searchParams.get("path");
    if (method === "PUT") {
      if (path !== "/api/file") return fail(res, 404, "not found");
      const body = await readBody(req).catch(() => null);
      return body === null ? fail(res, 413, "request body is larger than 2 MB") : putFile(res, body);
    }
    switch (path) {
      case "/": return send(res, 200, PAGE_HTML.replace("__TOKEN__", token), "text/html; charset=utf-8");
      case "/app.js": return send(res, 200, APP_JS, "text/javascript; charset=utf-8");
      case "/app.css": return send(res, 200, APP_CSS, "text/css; charset=utf-8");
      case "/api/state": return json(res, 200, state());
      case "/api/tree": return json(res, 200, { app: appName(), files: tree() });
      case "/api/file": return getFile(res, q, false);
      case "/api/render": return getFile(res, q, true);
      case "/api/gate-report": {
        // always current: built from the documents and ledger now; the saved file is the snapshot at approval
        const g = Number(url.searchParams.get("gate")), app = appName();
        if (!Number.isInteger(g) || g < 0 || g > 5 || !app) return fail(res, 400, "gate must be 0-5");
        const rel = `${docsRel(app)}/${gateReportRel(g)}`;
        return json(res, 200, { gate: g, path: rel, html: renderDoc(rel, gateReportMd(root, app, g, { gates: gateStatus(join(root, ".qe")) })) });
      }
      case "/api/download.zip": return zip(res);
      case "/api/events":
        res.writeHead(200, head({ "Content-Type": "text/event-stream", Connection: "keep-alive" }));
        res.write("retry: 3000\n: connected\n\n");
        clients.add(res); req.on("close", () => clients.delete(res));
        return;
      default: return fail(res, 404, "not found");
    }
  }

  const server = createServer((req, res) => { route(req, res).catch((e) => { if (!res.headersSent) fail(res, 500, (e as Error).message); else res.end(); }); });
  const first = opts.port ?? defaultPort(env);
  const candidates = first === 0 ? [0] : Array.from({ length: Math.max(1, 4190 - first + 1) }, (_, i) => first + i);
  let bound = false;
  for (const p of candidates) {
    // the usual port is taken: when this project's own dashboard holds it, reuse that one rather than start a second
    if (p !== first && first !== 0 && (await pingProject(first)) === anchorId(root)) {
      // stand down for the running one, and leave nothing open that keeps this process alive
      clearInterval(poller); clearInterval(beat); clearTimeout(debounce);
      for (const w of watchers) w.close();
      throw new Error(ALREADY_RUNNING);
    }
    bound = await new Promise<boolean>((done, no) => {
      const onErr = (e: NodeJS.ErrnoException) => { server.off("listening", onOk); e.code === "EADDRINUSE" ? done(false) : no(e); };
      const onOk = () => { server.off("error", onErr); done(true); };
      server.once("error", onErr); server.once("listening", onOk); server.listen(p, "127.0.0.1");
    });
    if (bound) break;
  }
  if (!bound) throw new Error("no free port between 4173 and 4190");
  port = (server.address() as import("node:net").AddressInfo).port;

  // a private, short-lived server (the HTML export) leaves the running dashboard's record and link alone
  if (opts.record !== false) {
    if (existsSync(join(root, ".qe"))) safeWrite(join(root, ".qe", "dashboard.json"), JSON.stringify({ port, pid: process.pid, started_at: new Date().toISOString(), app: appName() }, null, 2) + "\n", root, { mode: 0o600 });
    const tf = dashboardTokenFile(root, env);
    safeWrite(tf, JSON.stringify({ port, token, pid: process.pid }) + "\n", resolve(tf, "..", ".."), { mode: 0o600 });
  }

  return {
    port, token,
    close: () => new Promise<void>((done) => {
      clearInterval(poller); clearInterval(beat); clearTimeout(debounce);
      for (const w of watchers) w.close();
      for (const c of clients) c.end();
      server.close(() => done());
      server.closeAllConnections();
    })
  };
}

/** Where the HTML snapshot of the dashboard goes, relative to the project root. */
export const exportRel = (app: string): string => `docs/qe/${app}/09-release/dashboard.html`;

/**
 * Writes one self-contained, read-only HTML snapshot of the dashboard (same page, documents pre-rendered, evidence
 * images embedded as data URIs; no network, opens from disk or GitHub). It drives a private loopback server through
 * the same API, so the snapshot shows exactly what the live dashboard shows. Returns the path relative to root.
 */
export async function exportDashboard(root: string, app?: string): Promise<string> {
  const d = await startDashboard({ root, app, port: 0, record: false });
  try {
    const get = async (p: string): Promise<Response> => {
      const r = await fetch(`http://127.0.0.1:${d.port}${p}`, { headers: { Cookie: `qe_dash=${d.token}` } });
      if (!r.ok) throw new Error(`${p}: ${r.status}`);
      return r;
    };
    const state = await (await get("/api/state")).json() as any;
    if (!state.app) throw new Error("no app to export: pass --app or run in a project with docs/qe/<app>/");
    const images: Record<string, string> = {};
    for (const p of state.evidence.valid as string[]) {
      const rel = `docs/qe/${state.app}/${p}`;
      try { const r = await get(`/api/file?path=${encodeURIComponent(rel)}`); images[rel] = `data:${r.headers.get("content-type")};base64,${Buffer.from(await r.arrayBuffer()).toString("base64")}`; } catch { /* listed as invalid in state */ }
    }
    // every image the server would load is swapped for its embedded copy
    const inline = (html: string) => html.replace(/src="\/api\/file\?path=([^"]+)"/g, (m, enc) => { const k = decodeURIComponent(enc.replace(/&amp;/g, "&")); return images[k] ? `src="${images[k]}"` : m; });
    const renders: Record<string, string> = {}, reports: Record<number, string> = {};
    const paths = new Set<string>();
    for (const p of state.phases) for (const doc of p.docs) if (doc.exists) paths.add(doc.path);
    for (const r of state.reports) if (r.exists) paths.add(r.path);
    for (const c of state.cases) for (const f of c.files) paths.add(f);
    // this file gets shared and committed: nothing secret-shaped goes in, and activity keeps its kind and time only, no commands or paths (AQE141-002, -003)
    for (const p of paths) { try { const html = (await (await get(`/api/render?path=${encodeURIComponent(p)}`)).json() as any).html; if (!findSecret(html)) renders[p] = inline(html); } catch { /* not readable: shown as not included */ } }
    state.ledger = state.ledger.map((e: any) => ({ time: e.time, kind: e.kind, detail: "" }));
    for (const g of [0, 1, 2, 3, 4, 5]) reports[g] = inline((await (await get(`/api/gate-report?gate=${g}`)).json() as any).html);
    const data = JSON.stringify({ state, renders, reports, images, exportedAt: localIso() }).replace(/</g, "\\u003c");
    const h = (s: string) => `'sha256-${createHash("sha256").update(s).digest("base64")}'`;
    const page = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src ${h(APP_CSS)}; script-src ${h(APP_JS)}; base-uri 'none'; form-action 'none'">
<!-- agentic-qe metadata
doc_id: ${exportRel(state.app).replace(/^docs\/qe\/[^/]+\//, "").replace(/\.html$/, "")}
created_at: ${localIso()}
created_by: agentic-qe dashboard export
-->
<title>Agentic QE · ${esc(state.app)} (snapshot)</title>
<style>${APP_CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header id="top" class="shell-header"></header>
<div class="shell">
<nav id="nav" class="side-nav" aria-label="Sections"></nav>
<main id="main" tabindex="-1"></main>
</div>
<div id="toast" class="toast" role="status" aria-live="polite"></div>
<script type="application/json" id="qe-static">${data}</script>
<script>${APP_JS}</script>
</body>
</html>
`;
    const rel = exportRel(state.app);
    safeWrite(join(root, rel), page, root);
    return rel;
  } finally { await d.close(); }
}

/**
 * How to open a link in the user's browser on this system, or null where there is no browser to open (CI, a remote shell
 * without a display, the open_browser option set to false). The link is passed as one argument, never through a shell.
 */
export function browserCommand(url: string, platform: string = process.platform, env: NodeJS.ProcessEnv = process.env): string[] | null {
  if (!/^http:\/\/127\.0\.0\.1:\d{2,5}\/(\?token=[0-9a-f]{64})?$/.test(url)) return null;
  if (/^(false|0|no|off)$/i.test(env.CLAUDE_PLUGIN_OPTION_OPEN_BROWSER ?? "") || env.CI || env.AGENTIC_QE_DASHBOARD === "off") return null;
  if (platform === "darwin") return env.SSH_CONNECTION ? null : ["open", url];
  if (platform === "win32") return ["rundll32", "url.dll,FileProtocolHandler", url];
  return env.DISPLAY || env.WAYLAND_DISPLAY ? ["xdg-open", url] : null;
}

/** Opens the dashboard in the browser; best effort, never throws. */
export function openBrowser(url: string): boolean {
  const argv = browserCommand(url);
  if (!argv) return false;
  try { spawn(argv[0], argv.slice(1), { detached: true, stdio: "ignore", windowsHide: true }).on("error", () => undefined).unref(); return true; } catch { return false; }
}

if (isMain(import.meta.url)) {
  const { values: v } = parseArgs({ options: { root: { type: "string" }, app: { type: "string" }, port: { type: "string" }, link: { type: "boolean" }, export: { type: "boolean" }, open: { type: "boolean" } }, strict: false });
  const given = resolve(String(v.root ?? process.cwd()));
  let root = "";
  try { root = realpathSync(given); } catch { /* reported below */ }
  const link = root ? symlinkIn(given) : null;
  if (!root || link) { console.error(root ? `--root must be a real path, not a symlink: ${link} is a link (use ${root})` : `--root not found: ${given}`); process.exit(2); }
  if (v.export) {
    try { console.log(`Dashboard snapshot written: ${await exportDashboard(root, typeof v.app === "string" ? v.app : undefined)}`); process.exit(0); }
    catch (e) { console.error(`export failed: ${(e as Error).message}`); process.exit(1); }
  }
  const live = await dashboardLink(root);
  if (live || v.link) {
    console.log(live ?? "no dashboard is running for this project; run /agentic-qe:qe-panel --serve");
    if (live && v.open && openBrowser(live)) console.log("opened in your browser");
    process.exit(live ? 0 : 1);
  }
  try {
    const d = await startDashboard({ root, app: typeof v.app === "string" ? v.app : undefined, port: v.port ? Number(v.port) : undefined });
    const url = `http://127.0.0.1:${d.port}/?token=${d.token}`;
    console.log(url);
    if (v.open && openBrowser(url)) console.log("opened in your browser");
    for (const s of ["SIGINT", "SIGTERM"] as const) process.on(s, () => d.close().then(() => process.exit(0)));
    // the project folder was deleted (or moved): nothing left to serve
    setInterval(() => { if (!existsSync(root)) void d.close().then(() => process.exit(0)); }, 5000).unref();
  } catch (e) {
    if ((e as Error).message === ALREADY_RUNNING) {
      // started a moment ago by another process (the hook): wait for its record, then hand back its link
      let again: string | null = null;
      for (let i = 0; i < 20 && !again; i++) { await new Promise((r) => setTimeout(r, 150)); again = await dashboardLink(root); }
      console.log(again ?? `${ALREADY_RUNNING} on port ${defaultPort()}`);
      if (again && v.open && openBrowser(again)) console.log("opened in your browser");
      process.exit(0);
    }
    console.error((e as Error).message); process.exit(1);
  }
}
