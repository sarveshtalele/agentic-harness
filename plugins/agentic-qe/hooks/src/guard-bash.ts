import { basename, resolve, isAbsolute, join, relative } from "node:path";
import { type HookInput, type Decision, projectRoot, qeActive, isInside, emitDecision, isMain, readInput, detectHost, realRootOf, resolveReal, shellPath, tempRoots } from "./hook-common.ts";
import { anchorDir } from "./memory-logger.ts";
import { checkTarget, findSecret, inAnchorDir, parsePatch } from "./guard-write.ts";

interface Word { t: string; dyn: boolean; dl: boolean }
interface Cmd { words: Word[]; redirs: { op: string; target: Word }[]; pipe: number; body?: string }

const DOWNLOAD = new Set(["curl", "wget", "fetch", "invoke-webrequest", "iwr", "invoke-restmethod", "irm"]);
const SHELLS = new Set(["sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "yash", "csh", "tcsh", "fish"]);
/** Shell keywords and grouping words that start a command but are not the command (if x; then rm ...; fi). */
const RESERVED = new Set(["!", "{", "}", "if", "then", "else", "elif", "fi", "do", "done", "while", "until", "function", "coproc"]);
const INTERP = new Set([...SHELLS, "python", "python3", "pypy", "pypy3", "node", "deno", "bun", "perl", "ruby", "php", "lua", "luajit", "tclsh", "wish", "rscript", "osascript", "gdb", "pwsh", "powershell", "source", ".", "eval", "iex", "invoke-expression"]);
const ONELINER = new Set(["python", "python3", "node", "perl", "ruby", "php", "deno", "bun"]);
const WRAPPERS = new Set(["sudo", "doas", "env", "command", "exec", "nohup", "time", "nice", "builtin", "timeout", "setsid", "stdbuf", "ionice", "chrt", "taskset", "flock", "unbuffer", "strace", "ltrace", "caffeinate",
  "chroot", "nsenter", "unshare", "ssh-agent", "systemd-run", "entr", "screen", "parallel"]);
/** Wrappers whose first non-option word is not the command (timeout DURATION, chrt PRIO, taskset MASK, flock FILE, chroot DIR). */
const POSITIONAL: Record<string, number> = { timeout: 1, chrt: 1, taskset: 1, flock: 1, chroot: 1 };
/** Commands that run a command string given after an option (su -c 'cmd', pwsh -Command 'cmd'). */
const STRING_RUNNERS: Record<string, RegExp> = { su: /^(-c|--command|-[a-zA-Z]*c)$/, pwsh: /^-(c|command)$/i, powershell: /^-(c|command)$/i };
const DELETERS = new Set(["rm", "unlink", "rmdir", "shred", "rename"]);
const NESTED_AGENT_APPROVAL = /\b(approve|reject)\s+gate\b|\bapprove\s+create\b|\breset\s+qe\b/i;
const OPT_ARG: Record<string, Set<string>> = {
  sudo: new Set(["-u", "-g", "-h", "-p", "-C", "-D", "-R", "-r", "-t", "-U", "-T"]), doas: new Set(["-u", "-C"]),
  env: new Set(["-u", "-C", "--unset", "--chdir"]), nice: new Set(["-n", "--adjustment"]), exec: new Set(["-a"]),
  timeout: new Set(["-s", "-k", "--signal", "--kill-after"]),
  stdbuf: new Set(["-i", "-o", "-e"]), ionice: new Set(["-c", "-n", "-p", "-P", "-u"]), taskset: new Set(["-c"]), flock: new Set(["-w", "-E", "--timeout", "--conflict-exit-code"]),
  strace: new Set(["-e", "-o", "-p", "-s", "-u", "-E", "-a", "-b", "-P", "-I", "-O", "-S"]), ltrace: new Set(["-e", "-o", "-p", "-s", "-u", "-a", "-n", "-w", "-l", "-F", "-A"]),
  xargs: new Set(["-a", "-d", "-E", "-I", "-L", "-n", "-P", "-s", "-R", "-S", "--arg-file", "--delimiter", "--max-args", "--max-procs", "--max-chars", "--max-lines", "--replace", "--eof"])
};
const nonFlags = (a: Word[]) => a.filter((x) => !x.t.startsWith("-") || x.t === "-");
const hasFlag = (a: Word[], re: RegExp) => a.some((x) => re.test(x.t));
const DOT: Word = { t: ".", dyn: false, dl: false }; // implicit target: the current directory

/** Values of an option: "-X val", "-Xval" (also inside a flag cluster), "--long val", "--long=val". */
function optVal(a: Word[], short: string, long: string): Word[] {
  const re = short ? new RegExp(`^-[a-zA-Z]*${short}(.*)$`) : null;
  const out: Word[] = [];
  a.forEach((x, i) => {
    const m = re?.exec(x.t);
    if (m) out.push(m[1] ? { ...x, t: m[1] } : a[i + 1]);
    else if (x.t === long) out.push(a[i + 1]);
    else if (x.t.startsWith(long + "=")) out.push({ ...x, t: x.t.slice(long.length + 1) });
  });
  return out.filter((x) => x && x.t !== "-");
}
const tdir = (a: Word[]) => optVal(a, "t", "--target-directory");
const last = (a: Word[]) => (tdir(a).length ? tdir(a) : nonFlags(a).slice(-1));
const tarExtract = (a: Word[]) => a.some((x, i) => x.t === "--extract" || x.t === "--get" || (i === 0 ? /^-?[a-zA-Z]*x[a-zA-Z]*$/ : /^-[a-zA-Z]*x[a-zA-Z]*$/).test(x.t));
const tarCreate = (a: Word[]) => a.some((x, i) => x.t === "--create" || (i === 0 ? /^-?[a-zA-Z]*c[a-zA-Z]*$/ : /^-[a-zA-Z]*c[a-zA-Z]*$/).test(x.t));
/** Write targets of file-modifying commands. ponytail: no per-tool option parsing beyond these rules (sed -f, perl -n -e combos, rsync/tar create modes, curl --config). */
const WRITERS: Record<string, (a: Word[]) => Word[]> = {
  cp: last, mv: last, install: last, ln: last, rsync: (a) => nonFlags(a).slice(-1),
  dd: (a) => a.filter((x) => x.t.startsWith("of=")).map((x) => ({ ...x, t: x.t.slice(3) })),
  // BSD/macOS `sed -i '' script file`: the empty word after -i is the backup suffix, not the script
  // A script given by option (-e…, -f…, --expression[=], --file[=], attached or not) leaves every operand a file.
  // An in-place edit whose file cannot be found is an unverifiable target, never "no target" (AQE140-004).
  sed: (a) => {
    if (!hasFlag(a, /^(-[a-zA-Z]*i|--in-place)/)) return [];
    const ops = nonFlags(a).filter((x, i) => !(i === 0 && x.t === "" && a[a.indexOf(x) - 1]?.t === "-i"));
    const files = ops.slice(hasFlag(a, /^(-[a-zA-Z]*[ef]|--expression|--file)/) ? 0 : 1);
    return files.length ? files : [{ t: "(sed -i target)", dyn: true, dl: false }];
  },
  perl: (a) => (hasFlag(a, /^-[a-zA-Z]*i/) ? nonFlags(a).slice(1) : []),
  truncate: (a) => nonFlags(a).slice(hasFlag(a, /^(-s|--size)$/) ? 1 : 0),
  chmod: (a) => nonFlags(a).slice(1), chown: (a) => nonFlags(a).slice(1),
  curl: (a) => [...optVal(a, "o", "--output"), ...optVal(a, "", "--output-dir")],
  wget: (a) => [...optVal(a, "O", "--output-document"), ...optVal(a, "P", "--directory-prefix"), ...optVal(a, "o", "--output-file")],
  tar: (a) => [
    ...(tarExtract(a) ? (optVal(a, "C", "--directory").length ? optVal(a, "C", "--directory") : [DOT]) : []),
    ...(tarCreate(a) ? (/^[a-zA-Z]*f[a-zA-Z]*$/.test(a[0]?.t ?? "") && a[1] ? [a[1]] : optVal(a, "f", "--file")) : [])
  ],
  zip: (a) => nonFlags(a).slice(0, 1),
  unzip: (a) => (hasFlag(a, /^-[a-zA-Z]*[lptvZ]/) ? [] : optVal(a, "d", "").length ? optVal(a, "d", "") : [DOT]),
  // 7z x|e: -o<dir> or the current folder; cpio -i: the current folder; gzip -d and friends write next to the source
  "7z": (a) => {
    if (!/^[xe]$/.test(nonFlags(a)[0]?.t ?? "")) return [];
    const out = a.filter((x) => /^-o./.test(x.t)).map((x) => ({ ...x, t: x.t.slice(2) }));
    return out.length ? out : [DOT];
  },
  cpio: (a) => (hasFlag(a, /^-[a-zA-Z]*i|^--extract$/) ? [DOT] : []),
  gzip: (a) => (hasFlag(a, /^-[a-zA-Z]*d|^--decompress$/) ? nonFlags(a) : []),
  gunzip: (a) => nonFlags(a), bunzip2: (a) => nonFlags(a), unxz: (a) => nonFlags(a), unzstd: (a) => nonFlags(a)
};

WRITERS.bsdtar = WRITERS.tar;
WRITERS["7za"] = WRITERS["7zz"] = WRITERS["7z"];

/** Script languages that can write files or run commands from their own program text (checked while a run is active). */
const SCRIPT_WRITES: Record<string, (prog: string, a: Word[]) => string | null> = {
  sed: (p) => (/(^|[;{}\s])[wWe](\s|$)|(^|[;{}\s])[wW]\s*\S|\/[a-zA-Z0-9]*[we](\s|$|;)/.test(p) ? "a sed script with a w or e command writes files or runs commands" : null),
  awk: (p, a) => (/\bsystem\s*\(|print[f]?\b[^;}]*>|\|\s*["&]|getline/.test(p) || hasFlag(a, /^-i$|^--include$/) ? "an awk program that writes files or runs commands" : null)
};
SCRIPT_WRITES.gawk = SCRIPT_WRITES.mawk = SCRIPT_WRITES.nawk = SCRIPT_WRITES.awk;
const EDITORS = new Set(["ed", "ex", "vi", "vim", "nvim", "view", "red"]);
/** Inline programs (python -c, node -e, perl -e, ...) that call file-writing or process APIs. */
/** Extra Python/Node write calls: inline code naming the hook state folder is denied only together with one of these (or DESTRUCTIVE_API). */
const QE_WRITE_API = /\b(write|write_text|write_bytes|unlink|rmtree|rename|replace|symlink|link|writeFile|writeFileSync|appendFile|appendFileSync|rmSync|cpSync|symlinkSync|linkSync|createWriteStream)\b|\bopen(Sync)?\s*\([^)]*['"][wax+]/;
const DESTRUCTIVE_API = /\b(rm|unlink|rmdir|rmtree|rmSync|rmdirSync|unlinkSync|removeSync|remove|rename|renameSync|writeFile|writeFileSync|appendFile|appendFileSync|copyFile|copyFileSync|truncate|chmod|chown|system|popen|subprocess|child_process|execSync|execFile|exec|spawn|spawnSync|shutil|execute)\b|do shell script|open\s*\([^)]*,\s*['"][wax+]/;
const INLINE_FLAG: Record<string, RegExp> = { node: /^(-e|-p|--eval|--print)$/, deno: /^eval$/, bun: /^(-e|--eval)$/, perl: /^-[a-zA-Z]*[eE]$/, ruby: /^-[a-zA-Z]*e$/, php: /^-r$/, lua: /^-e$/, luajit: /^-e$/, osascript: /^-e$/, rscript: /^-e$/ };

const GIT_OPT_ARG = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env", "--exec-path"]);

/** Index of the char after the ")" matching an already-consumed "(" at depth 1. */
function closeParen(s: string, i: number): number {
  let d = 1;
  for (; i < s.length; i++) {
    const c = s[i];
    if (c === "\\") i++;
    else if (c === "'") i = s.indexOf("'", i + 1) < 0 ? s.length : s.indexOf("'", i + 1);
    else if (c === '"') { for (i++; i < s.length && s[i] !== '"'; i++) if (s[i] === "\\") i++; }
    else if (c === "(") d++;
    else if (c === ")" && --d === 0) return i + 1;
  }
  return s.length;
}

/**
 * Small shell tokenizer: quotes, backslashes, $(...), `...`, <(...), operators and redirections.
 * Nested command substitutions are parsed recursively and appended to the same flat command list.
 * ponytail: no variable expansion, aliases, functions, brace expansion, or heredoc-body parsing beyond skipping it.
 */
export function parseShell(src: string, out: Cmd[] = [], ctr = { n: 0 }): Cmd[] {
  let cur: Cmd = { words: [], redirs: [], pipe: ctr.n };
  let w: Word | null = null;
  let redir: string | null = null;
  const heredocs: { d: string; c: Cmd }[] = [];
  const word = (): Word => (w ??= { t: "", dyn: false, dl: false });
  const endWord = () => {
    if (!w) return;
    if (redir) {
      cur.redirs.push({ op: redir, target: w });
      if (redir.startsWith("<<") && redir !== "<<<") heredocs.push({ d: w.t, c: cur });
      redir = null;
    } else cur.words.push(w);
    w = null;
  };
  const endCmd = (pipe: boolean) => {
    endWord();
    if (cur.words.length || cur.redirs.length) out.push(cur);
    if (!pipe) ctr.n++;
    cur = { words: [], redirs: [], pipe: ctr.n };
  };
  const sub = (inner: string) => {
    const at = out.length;
    const n = ctr.n;
    parseShell(inner, out, ctr);
    ctr.n = n; // keep the enclosing pipeline id stable
    const x = word();
    x.dyn = true;
    x.t += "$(...)";
    if (out.slice(at).some((c) => DOWNLOAD.has(cmdName(c)))) x.dl = true;
  };

  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    const two = src.slice(i, i + 2);
    if (c === " " || c === "\t") endWord();
    else if (c === "\n") {
      endCmd(false);
      if (heredocs.length) {
        let pos = i + 1;
        for (const { d, c: owner } of heredocs.splice(0)) {
          // a body without its terminator is not a heredoc we understand: keep parsing those lines as commands
          const lines = src.slice(pos).split("\n");
          const end = lines.findIndex((l) => l.replace(/^\t+/, "") === d);
          if (end < 0) break;
          owner.body = lines.slice(0, end).map((l) => l + "\n").join("");
          pos += lines.slice(0, end + 1).join("\n").length + 1;
        }
        i = Math.min(pos, src.length) - 1;
      }
    } else if (c === "#" && !w) { while (i < src.length && src[i] !== "\n") i++; i--; }
    else if (c === ";") endCmd(false);
    else if (two === "&&" || two === "||") { endCmd(false); i++; }
    else if (two === "|&") { endCmd(true); i++; }
    else if (c === "|" && src[i + 1] !== "|") endCmd(true);
    else if (two === "&>") { endWord(); redir = src[i + 2] === ">" ? "&>>" : "&>"; i += redir.length - 1; }
    else if (c === "&") endCmd(false);
    else if (c === "\\") { if (src[i + 1] !== "\n") word().t += src[i + 1] ?? ""; else word(); i++; }
    else if (two === "$'") { // ANSI-C quoting: \' does not end it
      let j = i + 2;
      for (; j < src.length && src[j] !== "'"; j++) if (src[j] === "\\") j++;
      word().t += src.slice(i + 2, j);
      i = j;
    }
    else if (two === "((" && !w) { const e = closeParen(src, i + 2); word().t += src.slice(i, e); i = e - 1; } // arithmetic: << inside is a shift
    // subshell or function body: its commands are checked like any other, and a pipe into ( ) still counts as a pipe
    else if (c === "(" && !w) { if (cur.words.length || cur.redirs.length) endCmd(false); }
    else if (c === ")") endCmd(true);
    else if (c === "'") { const e = src.indexOf("'", i + 1) < 0 ? src.length : src.indexOf("'", i + 1); word().t += src.slice(i + 1, e); i = e; }
    else if (c === '"') {
      word();
      for (i++; i < src.length && src[i] !== '"'; i++) {
        if (src[i] === "\\") { if ("\\$\"`\n".includes(src[i + 1] ?? "x")) i++; w!.t += src[i]; }
        else if (src.startsWith("$(", i)) { const e = closeParen(src, i + 2); sub(src.slice(i + 2, e - 1)); i = e - 1; }
        else if (src[i] === "`") { const e = src.indexOf("`", i + 1) < 0 ? src.length : src.indexOf("`", i + 1); sub(src.slice(i + 1, e)); i = e; }
        else w!.t += src[i];
      }
    }
    else if (src.startsWith("$(", i) || two === "<(" || two === ">(") { const e = closeParen(src, i + 2); sub(src.slice(i + 2, e - 1)); i = e - 1; }
    else if (c === "`") { const e = src.indexOf("`", i + 1) < 0 ? src.length : src.indexOf("`", i + 1); sub(src.slice(i + 1, e)); i = e; }
    else if (c === ">" || c === "<") {
      if (w && /^\d+$/.test((w as Word).t)) w = null; // fd prefix such as 2>
      endWord();
      const op = src.slice(i, i + 3) === "<<<" ? src.slice(i, i + 3) : ["<<", ">>", ">|", ">&", "<&"].includes(two) ? two : c;
      redir = op;
      i += op.length - 1;
      if (op === "<<" && src[i + 1] === "-") i++;
    } else word().t += c;
  }
  endCmd(false);
  return out;
}

interface Res { name: string; raw?: Word; args: Word[]; nested: string[]; sub: Word[][]; xargs: boolean; ask?: string }

/**
 * Peels wrappers (sudo, env, xargs, timeout, busybox, ...) off a command line.
 * name/args = the real command; nested = shell strings to re-parse (sh -c, env -S); sub = commands run by find -exec.
 * ponytail: option tables cover common flags only; an unknown wrapper option can make the wrong word look like the command.
 */
function unwrap(words: Word[]): Res {
  const r: Res = { name: "", args: [], nested: [], sub: [], xargs: false };
  let i = 0;
  for (let depth = 0; depth < 8; depth++) {
    while (i < words.length && (/^\w+=/.test(words[i].t) || RESERVED.has(words[i].t))) i += words[i].t === "function" ? 2 : 1; // function NAME { body }
    if (words[i]?.t === "trap" && words[i + 1]) { r.name = "trap"; r.nested.push(words[i + 1].t); return r; } // trap 'cmd' EXIT runs cmd later
    r.raw = words[i];
    r.name = basename(words[i]?.t ?? "").toLowerCase();
    const rest = words.slice(i + 1);
    r.args = rest;
    if (SHELLS.has(r.name)) {
      const k = rest.findIndex((x) => /^-[a-zA-Z]*c[a-zA-Z]*$/.test(x.t));
      const code = rest[k + 1]?.t === "--" ? rest[k + 2] : rest[k + 1]; // bash -c -- 'cmd'
      if (k >= 0 && code) r.nested.push(code.t);
      return r;
    }
    if (r.name === "busybox") { i++; continue; }
    if (STRING_RUNNERS[r.name]) {
      const k = rest.findIndex((x) => STRING_RUNNERS[r.name].test(x.t) || x.t.startsWith("--command="));
      if (k >= 0) r.nested.push(rest[k].t.startsWith("--command=") ? rest[k].t.slice(10) : rest[k + 1]?.t ?? "");
      return r;
    }
    if (r.name === "tmux") { // tmux new|neww|splitw|run 'cmd': the last word is a shell command
      const k = rest.findIndex((x) => /^(new|new-session|new-window|neww|split-window|splitw|run|run-shell|respawn-pane|respawnp)$/.test(x.t));
      const cmdWords = k >= 0 ? nonFlags(rest.slice(k + 1)) : [];
      if (cmdWords.length) r.nested.push(cmdWords.map((x) => x.t).join(" "));
      return r;
    }
    if (r.name === "alias") { for (const a of rest) if (a.t.includes("=")) r.nested.push(a.t.slice(a.t.indexOf("=") + 1)); return r; }
    if (r.name === "script") { // script -c 'cmd' file
      const k = rest.findIndex((x) => /^-[a-zA-Z]*c$/.test(x.t) || x.t.startsWith("--command"));
      if (k >= 0) r.nested.push(rest[k].t.includes("=") ? rest[k].t.slice(rest[k].t.indexOf("=") + 1) : rest[k + 1]?.t ?? "");
      return r;
    }
    if (r.name === "watch") { // watch runs its words through sh -c
      let k = 0;
      for (; k < rest.length; k++) { const t = rest[k].t; if (t === "--") { k++; break; } if (!t.startsWith("-")) break; if (t === "-n" || t === "--interval") k++; }
      r.nested.push(rest.slice(k).map((x) => x.t).join(" "));
      return r;
    }
    if (r.name === "gdb") {
      rest.forEach((x, k) => {
        if (!/^(-ex|-iex|--ex|--iex|--eval-command|--init-eval-command)$/.test(x.t)) return;
        const m = /^\s*(?:shell|!)\s*(.*)$/s.exec(rest[k + 1]?.t ?? "");
        if (m) r.nested.push(m[1]); else r.ask = "approve gdb -ex commands?";
      });
      const k = rest.findIndex((x) => x.t === "--args");
      if (k >= 0 && k + 1 < rest.length) { i += 2 + k; continue; }
      return r;
    }
    if (r.name === "find") {
      for (let k = 0; k < rest.length; k++) {
        if (!/^-(exec|execdir|ok|okdir)$/.test(rest[k].t)) continue;
        let e = k + 1;
        while (e < rest.length && rest[e].t !== ";" && rest[e].t !== "+") e++;
        r.sub.push(rest.slice(k + 1, e));
        k = e;
      }
      return r;
    }
    if (r.name !== "xargs" && !WRAPPERS.has(r.name)) return r;
    let k = 0;
    let skip = POSITIONAL[r.name] ?? 0;
    for (; k < rest.length; k++) {
      const t = rest[k].t;
      if (r.name === "env") { // -S str, -iS str, -Sstr, --split-string=str
        const m = /^-[a-zA-Z]*S(.*)$/.exec(t);
        if (m || t.startsWith("--split-string")) { r.nested.push(m ? m[1] || rest[k + 1]?.t || "" : t.includes("=") ? t.slice(t.indexOf("=") + 1) : rest[k + 1]?.t ?? ""); k = rest.length; break; }
      }
      if (r.name === "flock" && (t === "-c" || t === "--command")) { r.nested.push(rest[k + 1]?.t ?? ""); k = rest.length; break; }
      if (t === "--") { k++; break; }
      if (t.startsWith("-") && t !== "-") { if (OPT_ARG[r.name]?.has(t)) { k++; if (r.name === "taskset") skip = 0; } continue; }
      if (r.name === "env" && /^\w+=/.test(t)) continue;
      if (skip > 0) { skip--; continue; }
      break;
    }
    if (r.name === "xargs") r.xargs = true;
    if (k >= rest.length) { r.args = []; return r; }
    i += 1 + k;
  }
  return r;
}
const cmdName = (c: Cmd): string => unwrap(c.words).name;

/** Index of the git subcommand after global options. */
function gitSub(args: Word[]): number {
  let i = 0;
  while (i < args.length && args[i].t.startsWith("-")) i += GIT_OPT_ARG.has(args[i].t) ? 2 : 1;
  return i;
}
const CLONE_ARG = new Set(["--depth", "-b", "--branch", "-o", "--origin", "-c", "--config", "--reference", "-j", "--jobs", "--separate-git-dir", "--filter", "--template", "-u", "--upload-pack", "--shallow-since", "--shallow-exclude", "--server-option", "--bundle-uri"]);
function cloneTarget(args: Word[], i: number): Word[] {
  const pos: Word[] = [];
  const rest = args.slice(i + 1);
  for (let k = 0; k < rest.length; k++) {
    if (rest[k].t === "--") { pos.push(...rest.slice(k + 1)); break; }
    if (rest[k].t.startsWith("-")) { if (CLONE_ARG.has(rest[k].t)) k++; } else pos.push(rest[k]);
  }
  const base: Word[] = pos.length > 1 ? [pos[1]] : [DOT];
  return args.slice(0, i).some((a) => a.t === "-C") ? [{ t: "$-C", dyn: true, dl: false }] : base; // git -C: relative to an unknown dir
}

/** Brace lists a{b,c}d -> abd acd. ponytail: comma lists only, quoting ignored (over-expands, never under-expands). */
const braces = (s: string): string[] => {
  const m = /\{([^{}]*,[^{}]*)\}/.exec(s);
  if (!m) return [s];
  return m[1].split(",").flatMap((p) => braces(s.slice(0, m.index) + p + s.slice(m.index + m[0].length))).slice(0, 64);
};
const expand = (ws: Word[]): Word[] => ws.flatMap((w) => (w.t.includes("{") ? braces(w.t).map((t) => ({ ...w, t })) : [w]));

function unbalanced(s: string): boolean {
  let q = "";
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (q === "'") { if (c === "'") q = ""; }
    else if (c === "\\") i++;
    else if (q === '"') { if (c === '"') q = ""; }
    else if (c === "'" || c === '"') q = c;
  }
  return q !== "";
}
const RISKY = /\brm\b[^|;&]*-\w*[rR]|\b(curl|wget|cp|mv|install|ln|rsync|dd|sed|perl|truncate|chmod|chown|tee|tar|unzip|git|python3?|node)\b|>/;

export function decideBash(input: HookInput, root: string, env = process.env): Decision | null {
  const ti = input.tool_input ?? {};
  const raw = ti.command ?? ti.cmd ?? "";
  const cmd = Array.isArray(raw) ? raw.join(" ") : String(raw);
  const active = qeActive(root, env);
  const host = detectHost(input, env);
  const deny = (reason: string): Decision => ({ decision: "deny", reason: `agentic-qe: ${reason}` });
  const secret = findSecret(cmd);
  let ask: Decision | null = null;
  const realRoot = realRootOf(root);
  const anchor = anchorDir(env);
  const realQe = join(realRoot, ".qe");
  // nothing the agent runs may so much as name the anchor dir (it holds the approval key); .qe stays readable.
  // the folder name only counts as a path part, so text such as compare/a...agentic-qe-plugin is fine
  // checked on the raw text and on the words with quotes removed (~/."agentic-qe"); a glob may stand in for the tail
  const ANCHOR_NAME = /(?<![\w.-])\.agentic(?:-qe(?![\w-])|-q?[*?[]|[*?[])|plugins\/data\/agentic-qe|anchors\/(?:[0-9a-f]{16}|[^\s'"]*(?:\.key|[*?[]))/;
  const plain = parseShell(cmd).flatMap((c) => [...c.words, ...c.redirs.map((x) => x.target)]).map((x) => x.t).join(" ");
  if (cmd.includes(anchor) || ANCHOR_NAME.test(cmd) || ANCHOR_NAME.test(plain)) return deny("the ledger anchor directory is managed by hooks only");
  // the dashboard link reaches the model; its write header and cookie must not be replayed from the shell (AQE140-006, AQE141-006: also with quotes split)
  if (/x-qe-token|qe_dash(?:_\d+)?=/i.test(cmd) || /x-qe-token|qe_dash(?:_\d+)?=/i.test(plain)) return deny("dashboard credentials are for the browser; edit documents in the dashboard or with the file tools");
  const cdpath = !!env.CDPATH || /(^|[\s;&|])(export\s+)?CDPATH=/.test(cmd);
  const seenPipe = new Map<number, number>();

  /** Checks a flat command list. cwd = where relative paths resolve (null = unknown after a cd we cannot follow). Returns a deny, or null (asks go to `ask`). */
  const run = (cmds: Cmd[], cwd: string | null, depth: number): Decision | null => {
    const seenDl = new Set<number>();
    for (const c of cmds) {
      const r = unwrap(c.words);
      const name = r.name;
      const args = expand(r.args);
      const abs = (t: Word): string | null => { const p = shellPath(t.t); return isAbsolute(p) ? p : cwd === null ? null : resolve(cwd, p); };
      const fed = (seenPipe.get(c.pipe) ?? 0) > 0; // some earlier command writes into this one's stdin
      seenPipe.set(c.pipe, (seenPipe.get(c.pipe) ?? 0) + 1);
      /** Delete/move target: nothing may remove .qe/ (or an ancestor of it); deletes outside the project are refused too. */
      const delCheck = (t: Word, outside: boolean): Decision | null => {
        const at = abs(t);
        if (at === null || t.dyn || /[$`~]/.test(t.t)) return deny(`cannot verify delete target ${t.t}`);
        const { real, bad } = resolveReal(root, at);
        if (bad) return deny(`cannot verify delete target ${t.t}`);
        if (outside && !isInside(realRoot, real)) return deny(`deleting ${t.t} is blocked (outside the project)`);
        const inRoot = relative(realRoot, real).replace(/\\/g, "/"); // "/" or "\" (Windows)
        const first = inRoot && !inRoot.startsWith("..") && !isAbsolute(inRoot) ? inRoot.split("/")[0] : "";
        const globQe = /[*?[]/.test(first) && first.startsWith(".") && new RegExp("^" + first.replace(/[.+^${}()|\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\?/g, ".") + "$", "i").test(".qe");
        // case-folded: on macOS and Windows .QE is the same folder as .qe (harmless extra protection elsewhere)
        const lq = realQe.toLowerCase(), lr = real.toLowerCase();
        if (globQe || isInside(lq, lr) || isInside(lr, lq)) return deny(`${t.t} would delete, move or truncate .qe/, which hooks manage`);
        return null;
      };
      // nested shell text: sh -c '...', env -S '...', a heredoc fed to a shell
      const hereStr = c.redirs.filter((x) => x.op === "<<<").map((x) => x.target.t);
      for (const text of [...r.nested, ...(SHELLS.has(name) || name === "at" || name === "batch" ? [...(c.body ? [c.body] : []), ...hereStr] : []), ...(name === "eval" ? [args.map((a) => a.t).join(" ")] : [])]) {
        if (depth >= 4) return deny("commands are nested too deeply to verify");
        if (unbalanced(text)) { if (RISKY.test(text)) return deny(`cannot parse nested command: ${text.slice(0, 60)}`); continue; }
        const d = run(parseShell(text), cwd, depth + 1);
        if (d) return d;
      }
      // find ... -exec cmd {} ; : {} is the start path (descendants stay inside it)
      if (r.sub.length) {
        const roots = nonFlagsBeforeOpts(args);
        const subst: Word = roots.length === 1 && !roots[0].dyn ? roots[0] : { t: "$find", dyn: true, dl: false };
        const d = run(r.sub.map((ws) => ({ words: ws.map((x) => (x.t === "{}" ? subst : x)), redirs: [], pipe: c.pipe })), cwd, depth + 1);
        if (d) return d;
      }
      // cd / pushd: follow within this command line
      if (name === "cd" || name === "pushd" || name === "popd") {
        const d = args.find((x) => !x.t.startsWith("-"));
        const searched = cdpath && !/^(\/|\.\.?(\/|$))/.test(d?.t ?? ""); // CDPATH can send a bare name anywhere
        const to = name === "popd" || !d || d.dyn || searched || /[$`~]/.test(d.t) || cwd === null && !isAbsolute(d.t) ? null : resolveReal(cwd ?? "/", shellPath(d.t));
        cwd = to && !to.bad ? to.real : null; // ponytail: cd inside ( ) or after || is treated as taking effect
        continue;
      }
      // (c) downloads reaching an interpreter: by pipe, <(...), $(...), -c "$(...)"; applies even without a QE run
      if (DOWNLOAD.has(name)) seenDl.add(c.pipe);
      else if (INTERP.has(name) && (seenDl.has(c.pipe) || args.some((a) => a.dl))) return deny("piping a download into an interpreter is blocked");
      else if (SCRIPT_WRITES[name] && seenDl.has(c.pipe) && SCRIPT_WRITES[name](args.map((a) => a.t).join(" "), args)) return deny(`piping a download into ${name} that runs commands is blocked`);
      // interpreters (any form: -c code, script file, heredoc) that name hook-owned state. ponytail: only visible text is checked; a computed path in a script file is stopped by the approval mac, not here.
      const interp = ONELINER.has(name) || SHELLS.has(name) || /^python[\d.]*$/.test(name);
      const script = nonFlags(args).some((x) => x.t !== "-") || args.some((a) => /^-[a-zA-Z]*c$/.test(a.t));
      if (interp) {
        const code = [...args.map((a) => a.t), c.body ?? "", ...hereStr].join(" ");
        // inline Python/Node code may read the state folder; script files, shells and other interpreters are opaque, so any mention is denied
        const inline = /^(python[0-9.]*|node|deno|bun)$/.test(name) && (c.body !== undefined || hereStr.length > 0 || args.some((a) => /^-[a-zA-Z]*[ce]$|^--eval$/.test(a.t)));
        const qeText = code.includes(".qe") && (!inline || DESTRUCTIVE_API.test(code) || QE_WRITE_API.test(code));
        if (code.includes(anchor) || (active && (qeText || /memory-logger|approval-hook|on-decision/.test(code)))) return deny(`${name} touches .qe/, the ledger code or the ledger anchor directory, which hooks manage`);
        // the write-word list is not complete (open 'r+', touch, mkdir, writeSync): other inline code naming .qe asks (AQE140-003)
        if (active && inline && code.includes(".qe")) ask ??= { decision: "ask", reason: `agentic-qe: approve ${name} inline code that names .qe/? Only reading it is safe; the hooks own that folder.` };
        if (active && !script && (fed || c.body !== undefined || hereStr.length)) ask ??= { decision: "ask", reason: `agentic-qe: approve feeding piped or inline text to ${name}? It cannot be inspected.` };
      }
      // apply_patch run from the shell: same per-path checks as the Write guard
      if (name === "apply_patch" || name === "applypatch") {
        const text = c.body ?? args.map((a) => a.t).join("\n");
        for (const p of parsePatch(text)) {
          const at = abs({ t: p.file, dyn: false, dl: false });
          if (at === null) return active ? deny(`cannot verify patch path ${p.file}`) : null;
          const d = checkTarget(root, at, p.content, active, host);
          if (d?.decision === "deny") return d;
          ask ??= d;
        }
      }
      // (d) writes via redirection, tee and known writers
      const targets = c.redirs.filter((x) => /^(>>?|>\||&>>?|>&)$/.test(x.op) && !(x.op === ">&" && /^(\d+|-)$/.test(x.target.t))).map((x) => x.target);
      if (name === "tee") targets.push(...args.filter((a) => !a.t.startsWith("-")));
      targets.push(...(WRITERS[name]?.(args) ?? []));
      const sub = name === "git" ? gitSub(args) : 0;
      const rmR = name === "rm" && args.some((f) => /^-[a-zA-Z]*[rR]/.test(f.t) || f.t === "--recursive");
      if (name === "git" && args[sub]?.t === "clone") targets.push(...cloneTarget(args, sub));
      if (name === "git" && args[sub]?.t === "archive") targets.push(...optVal(args.slice(sub + 1), "o", "--output"));
      if (name === "curl" && args.some((a) => /^-[a-zA-Z]*O/.test(a.t) || a.t.startsWith("--remote-name"))) {
        targets.push(DOT); // remote-name: the file name comes from the URL
        ask ??= { decision: "ask", reason: "agentic-qe: approve curl saving a file named by the URL?" };
      }
            const isWriter = targets.length > 0 || rmR || name in WRITERS;
      if (isWriter && c.words.some((x) => /\$\{?IFS/.test(x.t))) return deny("$IFS inside a command that writes or deletes cannot be verified");
      for (const t of targets) {
        if (/^\/dev\/(null|stdout|stderr|tty)$/.test(t.t)) continue;
        if (secret) return deny("command writes content that looks like a secret");
        const at = abs(t);
        const unknown = at === null || t.dyn || /[$`]|^~|[?[]|(^|\/)\.[^/]*\*|\{[^}]*\.\.[^}]*\}/.test(t.t);
        if (!unknown && inAnchorDir(root, at)) return deny("the ledger anchor directory is managed by hooks only");
        if (!active) continue;
        if (unknown) return deny(`cannot verify write target ${t.t}`);
        const d = checkTarget(root, at, cmd, true, host);
        if (d?.decision === "deny") return d;
        ask ??= d;
      }
      if (!active) continue;
      if (r.ask) ask ??= { decision: "ask", reason: `agentic-qe: ${r.ask}` };
      // programs whose own text writes files or runs commands: the shell guard cannot follow them, so ask (limit R-2)
      const progText = args.filter((a) => !a.t.startsWith("-")).map((a) => a.t).join(" ") + " " + args.filter((a) => /^-[a-zA-Z]*[ef]$|^--expression/.test(a.t)).map((a) => a.t).join(" ");
      const why = SCRIPT_WRITES[name]?.(progText, args)
        ?? (EDITORS.has(name) && (args.some((a) => /^(-[a-zA-Z]*[csE]|-es|--cmd|\+.)/.test(a.t)) || fed || c.body !== undefined || hereStr.length) ? `${name} run with commands can write files` : null)
        ?? (name === "curl" && args.some((a) => /^-[a-zA-Z]*K$|^--config/.test(a.t)) ? "curl -K reads options, including output files, from a config file" : null)
        ?? ((name === "npx" || name === "bunx") && !args.some((a) => a.t === "--no-install" || a.t === "--offline") ? `${name} downloads and runs a package` : null)
        ?? ((name === "pnpm" || name === "yarn") && args[0]?.t === "dlx" ? `${name} dlx downloads and runs a package` : null)
        ?? (INLINE_FLAG[name] && args.some((a, k) => INLINE_FLAG[name].test(a.t) && DESTRUCTIVE_API.test(args[k + 1]?.t ?? "")) ? `${name} inline code that deletes, writes or runs processes` : null)
        ?? (/^(python[\d.]*|pypy3?)$/.test(name) && args.some((a, k) => /^-[a-zA-Z]*c$/.test(a.t) && DESTRUCTIVE_API.test(args[k + 1]?.t ?? "")) ? `${name} -c code that deletes, writes or runs processes` : null)
        ?? (((name === "tar" || name === "bsdtar") && tarExtract(args)) || (name === "unzip" && !hasFlag(args, /^-[a-zA-Z]*[lptvZ]/)) || (name === "cpio" && hasFlag(args, /^-[a-zA-Z]*i|^--extract$/)) || (/^7z[az]?$/.test(name) && /^[xe]$/.test(nonFlags(args)[0]?.t ?? ""))
          ? `extracting an archive can overwrite any file it names, including .qe/` : null)
        ?? ((name === "patch" || (name === "git" && /^(apply|am)$/.test(args[gitSub(args)]?.t ?? ""))) ? "a patch can change any file it names, including .qe/" : null)
        ?? (name === "git" && args[gitSub(args)]?.t === "reset" && args.some((a) => a.t === "--hard") ? "git reset --hard discards uncommitted changes" : null)
        ?? (SHELLS.has(name) && !r.nested.length && (c.redirs.some((x) => x.op === "<") || args.some((a) => a.dyn) || r.xargs) ? `${name} reading commands from a file, process substitution or xargs` : null);
      if (why) ask ??= { decision: "ask", reason: `agentic-qe: approve? ${why}, which the guard cannot inspect.` };
      // a hard link to an outside file lets a later write inside the project change it (ln without -s, cp -l)
      if ((name === "ln" && !hasFlag(args, /^-[a-zA-Z]*s|^--symbolic$/)) || (name === "cp" && hasFlag(args, /^-[a-zA-Z]*l|^--link$/))) {
        const srcs = tdir(args).length ? nonFlags(args) : nonFlags(args).slice(0, -1);
        if (srcs.some((s) => { const at = abs(s); return at === null || s.dyn || !isInside(realRoot, resolveReal(root, at).real); }))
          ask ??= { decision: "ask", reason: "agentic-qe: approve a hard link to a file outside the project? Writes through it would change that file." };
      }
      if (name === "eval") ask ??= { decision: "ask", reason: "agentic-qe: approve eval? The evaluated text cannot be fully inspected." };
      // a name that is partly literal and partly expanded or globbed (rm${IFS}-rf, /bin/r[m]) hides the real command
      const rawName = r.raw?.t ?? "";
      // $HOME/bin/tool, $TMPDIR/run.sh: a known variable then a plain path is asked about, not denied
      if (/^\$(\{(HOME|TMPDIR|PWD)\}|HOME|TMPDIR|PWD)\/[^$*?[\]{}]*$/.test(rawName)) ask ??= { decision: "ask", reason: `agentic-qe: approve running ${rawName.slice(0, 40)}? Its name starts with a variable.` };
      else if ((/[*?[\]{}]/.test(rawName.replace(/^\$\{\w+\}$/, "")) && rawName !== "[" && rawName !== "[[") || (/\$/.test(rawName) && !/^(\$\w+|\$\{\w+\}|\$\(\.\.\.\))$/.test(rawName))) return deny(`cannot verify the command name ${rawName.slice(0, 40)}`);
      if (/^\$|\$\(\.\.\.\)|^`/.test(name)) ask ??= { decision: "ask", reason: "agentic-qe: approve a command whose name comes from a variable or substitution?" };
      if (name === "ssh" || name === "scp" || name === "sftp" || (name === "rsync" && nonFlags(args).some((a) => /^[^\/\s]*:/.test(a.t)))) ask ??= { decision: "ask", reason: `agentic-qe: approve ${name} to a remote host?` };
      if (name === "claude" || name === "codex") {
        const nested = name === "claude" ? args.some((a) => /^(--print|--continue|--resume)$|^-[a-zA-Z]*[pcr]$/.test(a.t)) : /^(exec|e)$/.test(nonFlags(args)[0]?.t ?? "");
        if (nested) {
          if (NESTED_AGENT_APPROVAL.test(cmd)) return deny("approvals must come from the user, not a nested agent");
          ask ??= { decision: "ask", reason: `agentic-qe: approve starting a nested ${name} session?` };
        }
      }
      const flags = args.filter((a) => a.t.startsWith("-") && a.t !== "-");
      const rest = args.filter((a) => !a.t.startsWith("-") || a.t === "-");
      for (const t of DELETERS.has(name) ? rest : name === "mv" ? (tdir(args).length ? rest : rest.slice(0, -1)) : []) {
        const d = delCheck(t, name !== "mv");
        if (d) return d;
      }
      if (rmR || (name === "find" && flags.some((f) => f.t === "-delete"))) {
        const victims = name === "find" ? (nonFlagsBeforeOpts(args).length ? nonFlagsBeforeOpts(args) : [DOT]) : rest;
        if (r.xargs) return deny("rm -r with arguments from stdin is blocked");
        for (const t of victims) {
          const dd = name === "find" ? delCheck(t, true) : null;
          if (dd) return dd;
          const at = abs(t);
          if (at === null || t.dyn || /[$`*?[]|^~/.test(t.t) || /\{[^}]*\.\.[^}]*\}/.test(t.t)) return deny(`rm -r on ${t.t} is blocked (cannot verify: expansion, glob or unknown directory)`);
          const { real, bad } = resolveReal(root, at);
          if (bad || !isInside(realRoot, real) || real === realRoot) return deny(`rm -r on ${t.t} is blocked (unknown, outside the project, or the root itself)`);
        }
      } else if (name === "git") {
        const cfgKey = /^(core\.(hookspath|sshcommand|fsmonitor|pager|editor|askpass)|alias\.|credential\.helper|include)/i;
        for (let k = 0; k < sub; k++) if ((args[k].t === "-c" || args[k].t === "--config-env") && cfgKey.test(args[k + 1]?.t ?? "")) return deny(`git -c ${args[k + 1].t} is blocked`);
        const more = args.slice(sub + 1);
        if (args[sub]?.t === "config" && more.some((a) => /^--(global|system|file|blob)\b|^-f$/.test(a.t) || cfgKey.test(a.t))) return deny("git config of global/system settings, hooks, aliases or ssh commands is blocked");
        if (args[sub]?.t === "clean" && more.some((a) => /^-[a-zA-Z]*[xXd]/.test(a.t) || /^--(?!dry-run)/.test(a.t))) return deny("git clean with -d/-x/-X could remove .qe/");
        if (args[sub]?.t === "stash" && more.some((a) => /^-[a-zA-Z]*[ua]$/.test(a.t) || /^--(include-untracked|all)$/.test(a.t))) return deny("git stash with untracked files could remove .qe/");
        // working-tree commands that name .qe/ (checkout, restore, rm, mv): same rule as rm and mv
        if (/^(checkout|restore|rm|mv)$/.test(args[sub]?.t ?? "")) for (const t of nonFlags(more)) { const d = /^\.qe(\/|$)/i.test(t.t) ? delCheck(t, false) : null; if (d) return d; }
        if (args[sub]?.t === "worktree" && more[0]?.t === "add") for (const t of nonFlags(more.slice(1)).slice(0, 1)) {
          const at = abs(t);
          if (at === null || !isInside(realRoot, resolveReal(root, at).real)) return deny(`git worktree add ${t.t} writes outside the project`);
        }
        if (args[sub]?.t === "push") {
          const pa = args.slice(sub + 1);
          if (pa.some((a) => /^-[a-zA-Z]*f/.test(a.t) && !a.t.startsWith("--") || a.t.startsWith("--force") || a.t === "--mirror" || a.t.startsWith("+"))) return deny("git push --force is blocked");
          ask ??= { decision: "ask", reason: "agentic-qe: approve git push?" };
        }
      } else if (name === "mkdir" || name === "touch") {
        ask ??= { decision: "ask", reason: `agentic-qe: approve ${name === "mkdir" ? "creating folder(s)" : "creating file(s)"} via ${name} ${rest.map((x) => x.t).join(" ")}?` };
      }
    }
    return null;
  };

  const d = run(parseShell(cmd), input.cwd ? resolve(input.cwd) : root, 0);
  return d ?? ask;
}

/** Start paths of a find command line: the words before the first option or expression. */
function nonFlagsBeforeOpts(a: Word[]): Word[] {
  const k = a.findIndex((x) => /^(-|!|\()/.test(x.t));
  return k < 0 ? a : a.slice(0, k);
}

function main(): void {
  const input = readInput();
  emitDecision(decideBash(input, projectRoot(input)));
}

if (isMain(import.meta.url)) main();
