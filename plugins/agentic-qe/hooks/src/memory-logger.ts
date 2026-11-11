import { existsSync, readFileSync, writeFileSync, mkdirSync, realpathSync, appendFileSync, openSync, closeSync, unlinkSync, statSync, lstatSync, readdirSync } from "node:fs";
import { join, dirname, basename, isAbsolute } from "node:path";
import { homedir, tmpdir } from "node:os";
import { createHash, createHmac, randomBytes } from "node:crypto";

export interface GateDecisionRecord {
  gate: string;
  stage: string;
  decision: "APPROVED" | "REJECTED" | "REVISED";
  approver?: string;
  notes?: string;
  timestamp: string;
}

const GENESIS = "0".repeat(64);
const hashOf = (prev: string, rec: object) => createHash("sha256").update(prev + JSON.stringify(rec)).digest("hex");
const hmacOf = (key: string, hash: string) => createHmac("sha256", key).update(hash).digest("hex");

/** Ledger lives at <root>/.qe/ledger.jsonl; for any other layout the project root is the ledger's own dir. */
function ledgerRoot(ledgerPath: string): string {
  const dir = dirname(ledgerPath);
  return basename(dir) === ".qe" ? dirname(dir) : dir;
}

/** The anchor lives outside the project so an agent that can edit the repo cannot rewrite it. */
export function anchorDir(env = process.env): string {
  return env.CLAUDE_PLUGIN_DATA || env.PLUGIN_DATA || join(homedir(), ".agentic-qe");
}

const sha16 = (s: string) => createHash("sha256").update(s).digest("hex").slice(0, 16);
/** Id of a project path. Windows paths are case-insensitive, and hooks and shells can spell the same folder differently (C:\x, c:\X). */
export const anchorId = (path: string, platform: string = process.platform): string => sha16(platform === "win32" ? path.toLowerCase() : path);
const realOf = (root: string): string => { try { return realpathSync(root); } catch { return root; } };

/** The folder that always exists for this user, whatever the host passes: pointers live here. */
export const homeAnchorDir = (env = process.env): string => join(env.HOME || env.USERPROFILE || homedir(), ".agentic-qe");
const pointerFile = (root: string, env = process.env) => join(homeAnchorDir(env), "pointers", `${anchorId(realOf(root))}.json`);

/**
 * Remembers where this project's anchor lives. Hosts pass CLAUDE_PLUGIN_DATA to hooks only, so a dashboard or panel
 * started from a shell would look in another folder, find no anchor, call the ledger untrusted and show every gate pending.
 */
export function writePointer(root: string, env = process.env): void {
  const dir = env.CLAUDE_PLUGIN_DATA || env.PLUGIN_DATA;
  if (!dir) return;
  const f = pointerFile(root, env), body = JSON.stringify({ dir });
  try {
    if (existsSync(f) && readFileSync(f, "utf-8") === body) return;
    mkdirSync(dirname(f), { recursive: true, mode: 0o700 });
    writeFileSync(f, body, { encoding: "utf-8", mode: 0o600 });
  } catch { /* best effort: without it a shell-started dashboard reports an untrusted ledger and says why */ }
}

/**
 * Claude Code's data folders for this plugin (~/.claude/plugins/data/<plugin>-<marketplace>), where hooks anchor a run.
 * Runs started by a release without pointers (1.4.0 and older) have their anchor only there.
 */
export function hostDataDirs(env = process.env): string[] {
  const base = join(env.CLAUDE_CONFIG_DIR || join(env.HOME || env.USERPROFILE || homedir(), ".claude"), "plugins", "data");
  try { return readdirSync(base).filter((n) => /^agentic-qe(?:[-_.]|$)/i.test(n)).sort().map((n) => join(base, n)); } catch { return []; }
}

/** This project's anchor folder: what the host passed, else what the hooks recorded, else a host data folder that anchors it, else the home folder. */
export function anchorDirFor(root: string, env = process.env): string {
  const fromHost = env.CLAUDE_PLUGIN_DATA || env.PLUGIN_DATA;
  if (fromHost) return fromHost;
  try {
    const dir = JSON.parse(readFileSync(pointerFile(root, env), "utf-8")).dir;
    if (typeof dir === "string" && isAbsolute(dir) && existsSync(join(dir, "anchors"))) return dir;
  } catch { /* no pointer yet */ }
  const r = realOf(root);
  const names = [`${anchorId(r)}.json`, `${sha16(r)}.json`];
  const home = homeAnchorDir(env);
  if (names.some((n) => existsSync(join(home, "anchors", n)))) return home;
  return hostDataDirs(env).find((d) => names.some((n) => existsSync(join(d, "anchors", n)))) ?? home;
}

export function anchorFile(root: string, env = process.env): string {
  const dir = join(anchorDirFor(root, env), "anchors"), r = realOf(root);
  const now = join(dir, `${anchorId(r)}.json`), before = join(dir, `${sha16(r)}.json`); // runs started before ids ignored case on Windows
  return !existsSync(now) && existsSync(before) ? before : now;
}


/** The anchor says how many records this project's ledger had. null = no run was ever started here. */
export function readAnchor(root: string, env = process.env): { count: number; hash: string } | null {
  try { const a = JSON.parse(readFileSync(anchorFile(root, env), "utf-8")); return Number.isInteger(a.count) ? { count: a.count, hash: String(a.hash) } : null; } catch { return null; }
}

const keyFile = (root: string, env = process.env) => anchorFile(root, env).replace(/\.json$/, ".key");
const readKey = (root: string, env = process.env): string | null => { try { return readFileSync(keyFile(root, env), "utf-8").trim() || null; } catch { return null; } };

/** New random 32-byte approval key, stored only in the anchor dir (0600). Replacing it invalidates every earlier user_prompt mac.
 * ponytail limit: guards stop the agent's tool calls from naming the anchor dir, but a process that runs outside those calls (or a script that computes the path) can still read the key. */
export function newApprovalKey(root: string, env = process.env): string {
  const f = keyFile(root, env);
  mkdirSync(dirname(f), { recursive: true, mode: 0o700 });
  const k = randomBytes(32).toString("hex");
  writeFileSync(f, k, { encoding: "utf-8", mode: 0o600 });
  return k;
}
const macOf = (key: string, prev: string, rec: object) => createHmac("sha256", key).update(prev + JSON.stringify(rec)).digest("hex");

/** ponytail: .qe/ and the ledger must be real files; a symlink would redirect hook writes. */
function refuseSymlinks(ledgerPath: string): void {
  for (const p of [basename(dirname(ledgerPath)) === ".qe" ? dirname(ledgerPath) : "", ledgerPath]) {
    try { if (p && lstatSync(p).isSymbolicLink()) throw new Error(`refusing to write through symlink: ${p}`); } catch (e) { if ((e as NodeJS.ErrnoException).code !== "ENOENT") throw e; }
  }
}

/** Exclusive lock file so concurrent hook processes cannot interleave read-last-hash and append. ponytail: busy-wait with 20 ms sleeps; stale-lock cleanup can race, a crashed holder blocks for at most 5 s. */
function withLock<T>(lockPath: string, fn: () => T): T {
  const until = Date.now() + 3000;
  for (;;) {
    try { closeSync(openSync(lockPath, "wx", 0o600)); break; } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== "EEXIST") return fn(); // cannot lock (read-only dir, ...): best effort
      try { if (Date.now() - statSync(lockPath).mtimeMs > 5_000) unlinkSync(lockPath); } catch { /* released meanwhile */ }
      if (Date.now() > until) throw new Error(`ledger lock busy: ${lockPath}`);
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 20);
    }
  }
  try { return fn(); } finally { try { unlinkSync(lockPath); } catch { /* already gone */ } }
}

/** Appends a record to a hash-chained JSONL ledger: hash = sha256(prev_hash + JSON(record)); head is anchored outside the project. */
export function appendLedger(ledgerPath: string, record: Record<string, unknown>, root = ledgerRoot(ledgerPath), fresh = false): void {
  refuseSymlinks(ledgerPath);
  mkdirSync(dirname(ledgerPath), { recursive: true, mode: 0o700 });
  withLock(ledgerPath + ".lock", () => {
    // a missing ledger with a non-empty anchor means it was deleted: never quietly start a new chain (only a user-typed bootstrap may, fresh=true). Inside the lock so a concurrent first append is not mistaken for a deletion.
    if (!fresh && !existsSync(ledgerPath) && (readAnchor(root)?.count ?? 0) > 0) throw new Error("ledger is missing but anchored: refusing to recreate it");
    // a ledger with no anchor was not started here (a cloned repository's, say): appending would anchor it and launder it into "trusted" (AQE141-001)
    if (!fresh && existsSync(ledgerPath) && readAnchor(root) === null) throw new Error("ledger exists but was never anchored on this machine: refusing to adopt it");
    let prev = GENESIS;
    let count = 0;
    if (existsSync(ledgerPath)) {
      const lines = readFileSync(ledgerPath, "utf-8").split("\n").filter(Boolean);
      count = lines.length;
      try { if (lines.length) prev = JSON.parse(lines[lines.length - 1]).hash; } catch { prev = "corrupt"; } // verifyLedger reports it
    }
    const hash = hashOf(prev, record);
    const key = process.env.AGENTIC_QE_LEDGER_KEY;
    // user_prompt records carry a mac under a key only the hooks can read (anchor dir), so a script that rewrites ledger + anchor cannot forge approvals
    const mac = record.source === "user_prompt" ? macOf(readKey(root) ?? newApprovalKey(root), prev, record) : null;
    const full = { ...record, prev_hash: prev, hash, ...(key ? { hmac: hmacOf(key, hash) } : {}), ...(mac ? { mac } : {}) };
    appendFileSync(ledgerPath, JSON.stringify(full) + "\n", { encoding: "utf-8", mode: 0o600 });
    try {
      const f = anchorFile(root);
      mkdirSync(dirname(f), { recursive: true, mode: 0o700 });
      writeFileSync(f, JSON.stringify({ count: count + 1, hash }), { encoding: "utf-8", mode: 0o600 });
      // not for throwaway projects (test runs): a pointer outlives them
      if (![tmpdir(), "/tmp", "/private/tmp"].some((t) => realOf(root).startsWith(realOf(t)))) writePointer(root);
    } catch { /* ponytail: anchor is best effort; verifyLedger passes when no anchor exists, ledgerTrust does not */ }
  });
}

/** brokenAt is the 1-based line of the first bad record; reason explains anchor/HMAC failures. */
export function verifyLedger(ledgerPath: string, root = ledgerRoot(ledgerPath)): { ok: boolean; brokenAt?: number; reason?: string } {
  if (!existsSync(ledgerPath)) return { ok: true };
  const lines = readFileSync(ledgerPath, "utf-8").split("\n").filter(Boolean);
  const key = process.env.AGENTIC_QE_LEDGER_KEY;
  let prev = GENESIS;
  for (let i = 0; i < lines.length; i++) {
    try {
      const { prev_hash, hash, hmac, mac, ...rec } = JSON.parse(lines[i]);
      if (prev_hash !== prev || hash !== hashOf(prev, rec)) return { ok: false, brokenAt: i + 1 };
      if (key && hmac !== hmacOf(key, hash)) return { ok: false, brokenAt: i + 1, reason: "bad or missing HMAC" };
      prev = hash;
    } catch {
      return { ok: false, brokenAt: i + 1 };
    }
  }
  try {
    const a = JSON.parse(readFileSync(anchorFile(root), "utf-8"));
    if (a.count !== lines.length || a.hash !== prev) return { ok: false, reason: `ledger does not match its external anchor (expected ${a.count} records, found ${lines.length}): truncated or rewritten` };
  } catch { /* no anchor yet */ }
  return { ok: true };
}

/** First user_prompt record whose mac is missing or wrong (1-based line), 0 = all fine. */
function badMac(lines: string[], key: string | null): number {
  for (let i = 0; i < lines.length; i++) {
    try {
      const { prev_hash, hash, hmac, mac, ...rec } = JSON.parse(lines[i]);
      if (rec.source === "user_prompt" && (!key || mac !== macOf(key, prev_hash, rec))) return i + 1;
    } catch { return i + 1; }
  }
  return 0;
}

/**
 * Gate for readers (approvals, panel, session check). A ledger is trusted only if it was created here:
 * it verifies, a local anchor exists for this project, .qe/run.json carries the hook's bootstrap marker
 * and every user_prompt record has a valid mac. A deleted .qe/ or ledger is untrusted once a run has started here.
 * No run, no ledger and no anchor = nothing to distrust.
 */
export function ledgerTrust(root: string, env = process.env): { trusted: boolean; reason: string } {
  const qe = join(root, ".qe");
  const lp = join(qe, "ledger.jsonl");
  const no = (reason: string) => ({ trusted: false, reason });
  const anchor = readAnchor(root, env);
  let isLink = false;
  try { isLink = lstatSync(qe).isSymbolicLink(); } catch { /* absent */ }
  if (isLink) return no(".qe is a symlink");
  if (!existsSync(qe)) return anchor && anchor.count > 0 ? no("run state missing: .qe/ was deleted after a run started here") : { trusted: true, reason: "no run" };
  let marker = false;
  const hasRun = existsSync(join(qe, "run.json"));
  try { marker = JSON.parse(readFileSync(join(qe, "run.json"), "utf-8")).bootstrap === "hook"; } catch { /* missing or invalid */ }
  if (hasRun && !marker) return no('.qe/run.json lacks the "bootstrap":"hook" marker: this run was not started on this machine');
  if (!existsSync(lp)) return anchor && anchor.count > 0 ? no("ledger missing: .qe/ledger.jsonl was deleted after a run started here") : { trusted: true, reason: "no ledger yet" };
  if (!anchor) return no("no local anchor: this ledger was not created on this machine");
  const v = verifyLedger(lp, root);
  if (!v.ok) return no(v.reason ?? `broken at line ${v.brokenAt}`);
  const bad = badMac(readFileSync(lp, "utf-8").split("\n").filter(Boolean), readKey(root, env));
  if (bad) return no(`approval record at line ${bad} lacks a valid mac: the ledger was not written by the approval hook`);
  return { trusted: true, reason: "ok" };
}
