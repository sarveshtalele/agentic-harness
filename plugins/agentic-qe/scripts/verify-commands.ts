import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

interface Problem {
  file: string;
  line: number;
  token: string;
  status: string;
  inSkills: boolean;
}

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SKILLS_DIR = path.join(ROOT, "skills");
// Claude Code shows plugin commands namespaced (/agentic-qe:qe-start); Codex uses $qe-start.
const FULL_RE = /\/agentic-qe:(qe-[a-z-]+)/g;
const CODEX_RE = /(?<![\w:])\$(qe-[a-z-]+)/g;
// a bare /qe-start is not how Claude Code lists the command, so docs must not use it
const BARE_RE = /(?<![\w:$/.-])\/(qe-[a-z-]+)/g;
const EMPTY_HINT_OK = new Set(["qe-doctor"]);
// Commands the pane mod registers with $.command.register (hooks/pane.tsx). Mod commands are typed bare, not namespaced.
const MOD_COMMANDS = new Set(["qe-pane"]);
const strict = process.argv.includes("--strict");

const problems: Problem[] = [];

function rel(p: string): string {
  return path.relative(ROOT, p).split(path.sep).join("/");
}

function report(file: string, line: number, token: string, status: string, inSkills: boolean): void {
  problems.push({ file, line, token, status, inSkills });
}

function walk(dir: string, match: (f: string, full: string) => boolean, out: string[] = []): string[] {
  if (!existsSync(dir)) return out;
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.name === "node_modules" || e.name === ".git") continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, match, out);
    else if (match(e.name, p)) out.push(p);
  }
  return out;
}

const skillNames = readdirSync(SKILLS_DIR, { withFileTypes: true })
  .filter((d) => d.isDirectory() && d.name.startsWith("qe-"))
  .map((d) => d.name)
  .sort();
const known = new Set(skillNames);

function scan(file: string, inSkills: boolean): void {
  const relFile = rel(file);
  readFileSync(file, "utf8")
    .split(/\r?\n/)
    .forEach((line, i, all) => {
      // recorded command output inside ```text blocks is kept verbatim, so it is not checked
      const fences = all.slice(0, i).filter((l) => l.startsWith("```"));
      if (fences.length % 2 === 1 && fences[fences.length - 1].trim() === "```text") return;
      for (const re of [FULL_RE, CODEX_RE]) {
        for (const m of line.matchAll(re)) {
          if (!known.has(m[1])) report(relFile, i + 1, m[0], "not a qe-* skill (typo or stale name)", inSkills);
        }
      }
      for (const m of line.matchAll(BARE_RE)) {
        if (MOD_COMMANDS.has(m[1])) continue;
        report(relFile, i + 1, m[0], `bare form; Claude Code lists it as /agentic-qe:${m[1]}`, inSkills);
      }
    });
}

for (const name of skillNames) {
  const filePath = path.join(SKILLS_DIR, name, "SKILL.md");
  const relFile = rel(filePath);
  if (!existsSync(filePath)) {
    report(relFile, 1, "(file)", "SKILL.md missing", true);
    continue;
  }
  const lines = readFileSync(filePath, "utf8").split(/\r?\n/);
  const end = lines[0]?.trim() === "---" ? lines.indexOf("---", 1) : -1;
  if (end === -1) {
    report(relFile, 1, "(frontmatter)", "missing or unterminated frontmatter block", true);
    continue;
  }
  const keys = new Map<string, string>();
  for (let i = 1; i < end; i++) {
    const m = /^([A-Za-z][A-Za-z-]*):\s*(.*)$/.exec(lines[i]);
    if (m) keys.set(m[1], m[2].trim());
  }
  if (keys.get("name") !== name) report(relFile, 1, "(frontmatter)", `name is "${keys.get("name") ?? ""}", expected "${name}"`, true);
  if (!keys.get("description")) report(relFile, 1, "(frontmatter)", "missing or empty description", true);
  else if (keys.get("description")!.length > 1024) report(relFile, 1, "(frontmatter)", "description over 1024 chars", true);
  if (!keys.has("argument-hint")) { if (!EMPTY_HINT_OK.has(name)) report(relFile, 1, "(frontmatter)", "missing argument-hint key", true); }
  else if (!keys.get("argument-hint") && !EMPTY_HINT_OK.has(name)) report(relFile, 1, "(frontmatter)", "empty argument-hint", true);
  if (keys.get("disable-model-invocation") !== "true") report(relFile, 1, "(frontmatter)", "disable-model-invocation must be true", true);
  if (!lines.some((l) => l.startsWith(`Invoke: \`/agentic-qe:${name}\``))) {
    report(relFile, 1, "(invoke)", `missing "Invoke: \`/agentic-qe:${name}\`" line`, true);
  }
}

const skillMds = walk(SKILLS_DIR, (f) => f === "SKILL.md");
for (const f of skillMds) scan(f, true);
const others = [
  path.join(ROOT, "README.md"),
  // docs/security/raw holds archived audit evidence that quotes old command names verbatim
  ...walk(path.join(ROOT, "docs"), (f, full) => f.endsWith(".md") && !full.includes(`${path.sep}security${path.sep}raw${path.sep}`)),
  ...walk(path.join(ROOT, "examples"), (f) => f === "RUN_LOG.md"),
].filter(existsSync);
for (const f of others) scan(f, false);

const skillProblems = problems.filter((p) => p.inSkills);
const otherProblems = problems.filter((p) => !p.inSkills);

if (problems.length > 0) {
  const rows = problems.map((p) => [`${p.file}:${p.line}`, p.token, p.status]);
  const header = ["file:line", "token", "status"];
  const widths = header.map((h, c) => Math.max(h.length, ...rows.map((r) => r[c].length)));
  const fmt = (cells: string[]) => cells.map((c, i) => (i < 2 ? c.padEnd(widths[i]) : c)).join("  ");
  console.log(fmt(header));
  for (const r of rows) console.log(fmt(r));
  console.log("");
}

const failed = skillProblems.length > 0 || (strict && otherProblems.length > 0);
console.log(
  `verify-commands: ${skillNames.length} qe-* skills, ${skillProblems.length} mismatch(es) in skills/, ` +
    `${otherProblems.length} in README/docs/examples (${strict ? "strict: counted" : "reported only; use --strict to fail"}) ` +
    `=> ${failed ? "FAIL" : "PASS"}`,
);
process.exit(failed ? 1 : 0);
