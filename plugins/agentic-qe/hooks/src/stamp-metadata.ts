import { existsSync, readFileSync, lstatSync, realpathSync } from "node:fs";
import { join, resolve, relative, basename, extname, dirname } from "node:path";
import { execFileSync } from "node:child_process";
import { type HookInput, projectRoot, qeActive, isInside, isMain, readInput, lexists, realRootOf, safeWrite, pluginRoot, localIso } from "./hook-common.ts";


/** Strips anything that could break out of a YAML/JSON/HTML-comment context. */
function clean(v: unknown): string {
  return String(v).replace(/[\r\n]+/g, " ").replace(/[<>&`'"]/g, "").replace(/-{2,}/g, "-").slice(0, 120);
}

/** No symlink on the path below root, and the real path stays inside root. */
function safeTarget(abs: string, root: string): boolean {
  try {
    for (let p = abs; p !== root && p !== dirname(p); p = dirname(p)) if (lstatSync(p).isSymbolicLink()) return false;
    return isInside(realRootOf(root), realpathSync(abs));
  } catch {
    return false;
  }
}

function metaFor(file: string, root: string, env = process.env): Record<string, string> {
  let version = "";
  try {
    version = JSON.parse(readFileSync(join(pluginRoot(env) ?? "", ".claude-plugin/plugin.json"), "utf-8")).version ?? "";
  } catch { /* fallback below */ }
  let mode = "unknown";
  try { mode = String(JSON.parse(readFileSync(join(root, ".qe/run.json"), "utf-8")).mode ?? "unknown"); } catch { /* default */ }
  if (!/^[a-z-]{1,20}$/.test(mode)) mode = "unknown";
  let commit = "none";
  try {
    commit = execFileSync("git", ["rev-parse", "--short", "HEAD"], { cwd: root, encoding: "utf-8", stdio: ["ignore", "pipe", "ignore"] }).trim() || "none";
  } catch { /* not a repo */ }
  const meta = {
    // path inside docs/qe/<app>/ without extension, e.g. 04-design/test_cases (phase folders share file names)
    doc_id: (relative(root, file).replace(/\\/g, "/").match(/^docs\/qe\/[^/]+\/(.+)$/)?.[1] ?? basename(file)).replace(/\.[^./]+$/, ""),
    created_at: localIso(),
    created_by: version ? `agentic-qe v${version}` : "agentic-qe",
    mode,
    source_commit: commit
  };
  return Object.fromEntries(Object.entries(meta).map(([k, v]) => [k, clean(v)]));
}

/** Stamps a file under docs/qe/ or examples/ when a QE run is active. Returns true if the file changed. */
export function stampFile(file: string, root: string, env = process.env): boolean {
  const abs = resolve(root, file);
  const rel = relative(root, abs).replace(/\\/g, "/"); // Windows separators
  if (!qeActive(root) || !isInside(root, abs) || !/^(docs\/qe|examples)\//.test(rel) || !existsSync(abs) || !safeTarget(abs, root)) return false;
  const ext = extname(abs).toLowerCase();
  const text = readFileSync(abs, "utf-8");
  const meta = metaFor(abs, root, env);
  const lines = Object.entries(meta).map(([k, v]) => `${k}: ${v}`);
  let out: string | null = null;
  let sidecarOnly = ext === ".csv";

  if (ext === ".md") {
    if (text.startsWith("---\n")) {
      const end = text.indexOf("\n---", 4);
      if (end > 0 && !/^created_at:/m.test(text.slice(0, end))) out = `---\n${lines.join("\n")}\n${text.slice(4)}`;
    } else {
      out = `---\n${lines.join("\n")}\n---\n\n${text}`;
    }
  } else if (ext === ".json") {
    try {
      const obj = JSON.parse(text);
      // a bare array cannot hold _meta without changing its shape, so it gets a sidecar like CSV; scalars are left alone
      if (Array.isArray(obj)) sidecarOnly = true;
      else if (obj && typeof obj === "object" && !("_meta" in obj)) out = JSON.stringify({ _meta: meta, ...obj }, null, 2) + "\n";
    } catch { /* invalid json: leave */ }
  } else if (ext === ".html") {
    if (!text.includes("<!-- agentic-qe metadata")) {
      const block = `<!-- agentic-qe metadata\n${lines.join("\n")}\n-->\n`;
      const m = text.match(/^<!doctype html>\s*\n?/i);
      out = m ? m[0] + block + text.slice(m[0].length) : block + text;
    }
  }
  if (sidecarOnly) {
    // Comment lines break Jira and spreadsheet CSV import, so metadata goes to a sidecar file.
    const sidecar = `${abs}.meta.json`;
    if (lexists(sidecar)) return false;
    try { safeWrite(sidecar, JSON.stringify({ _meta: meta, describes: rel.split("/").pop() }, null, 2) + "\n", root); } catch { return false; }
    return true;
  }
  if (out === null) return false;
  try { safeWrite(abs, out, root); } catch { return false; }
  return true;
}

function main(): void {
  const cli = process.argv[2];
  if (cli) {
    stampFile(cli, projectRoot({}));
    return;
  }
  const input: HookInput = readInput();
  const file = input.tool_input?.file_path;
  if (typeof file === "string") stampFile(file, projectRoot(input));
}

if (isMain(import.meta.url)) main();
