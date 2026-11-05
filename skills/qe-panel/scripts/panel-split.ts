import { execFile } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain } from "../../../hooks/src/hook-common.ts";

export interface Plan { strategy: string; argv: string[] | null; command: string[]; note?: string }
const APP_RE = /^[A-Za-z0-9._-]{1,64}$/;

export function planSplit(app: string, env: Record<string, string | undefined> = process.env): Plan {
  if (!APP_RE.test(app)) throw new Error("invalid app name (allowed: A-Z a-z 0-9 . _ -, max 64)");
  const panel = resolve(dirname(fileURLToPath(import.meta.url)), "panel.ts");
  const cmd = [process.execPath, panel, "--watch", "--app", app];
  const as = (s: string) => `"${s.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  if (env.TMUX) return { strategy: "tmux", command: cmd, argv: ["tmux", "split-window", "-h", "-p", "40", ...cmd] };
  if (env.TERM_PROGRAM === "iTerm.app") {
    // every cmd part is AppleScript-quoted and shell-quoted in one pass; app is regex-validated, paths are quoted
    const sh = cmd.map((c) => `'${c.replace(/'/g, "'\\''")}'`).join(" ");
    return { strategy: "iterm", command: cmd, argv: ["osascript", "-e", 'tell application "iTerm2" to tell current session of current window', "-e", `split vertically with default profile command ${as(sh)}`, "-e", "end tell"] };
  }
  if (env.TERM_PROGRAM === "WezTerm") return { strategy: "wezterm", command: cmd, argv: ["wezterm", "cli", "split-pane", "--right", "--percent", "40", "--", ...cmd] };
  if (env.WT_SESSION) return { strategy: "windows-terminal", command: cmd, argv: ["wt", "-w", "0", "split-pane", "-V", ...cmd] };
  return { strategy: "manual", command: cmd, argv: null, note: `Run in a second terminal: ${cmd.join(" ")}\nClaude desktop app: open the Terminal panel beside the chat and run: ${cmd.join(" ")}` };
}

if (isMain(import.meta.url)) {
  const a = process.argv.slice(2);
  const i = a.indexOf("--app");
  try {
    const plan = planSplit(i >= 0 ? a[i + 1] ?? "" : "");
    if (a.includes("--dry-run")) console.log(JSON.stringify(plan, null, 2));
    else if (!plan.argv) console.log(plan.note);
    else execFile(plan.argv[0], plan.argv.slice(1), (err) => {
      if (err) { console.error(`Could not open split (${plan.strategy}): ${err.message}\n${planSplit(a[i + 1], {}).note}`); process.exitCode = 1; }
    });
  } catch (e) {
    console.error((e as Error).message);
    process.exitCode = 2;
  }
}
