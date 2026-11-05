---
name: qe-panel
description: "Show QE progress in one view: phases in order, gates 0-5, test counts per level, blockers, ledger trust and the next command; with --serve, the link to the live browser dashboard; with --export, a read-only HTML snapshot of it. Use when the user runs /agentic-qe:qe-panel or $qe-panel, or asks for QE status, progress or the dashboard link."
argument-hint: "[<app>] [--once|--watch|--split|--serve|--export|--session]"
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash(node ${CLAUDE_SKILL_DIR}/scripts/panel.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/panel-split.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/dashboard-server.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/export-session.ts *)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-panel
Invoke: `/agentic-qe:qe-panel` (Claude Code) or `$qe-panel` (Codex). In Codex, run `node scripts/panel.ts` from this skill's folder.

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Optional positional `<app>`. Flags: `--once` (default), `--watch`, `--split`, `--serve`, `--export`. The terminal views are read-only.

## Usage
```bash
/agentic-qe:qe-panel [<app>] [--once|--watch|--split|--serve|--export]
```

## What it does
- Default or `--once`: run `node "${CLAUDE_SKILL_DIR}/scripts/panel.ts" --once [--app <app>]` and print its output.
- `--watch`: on Claude Code 2.1.287 or later (Desktop 2.1.286), where mods load by default, the plugin opens the live pane beside the transcript and adds a note saying so: start nothing else. Never run `--watch` with Bash yourself, in the foreground or the background: it never ends and its frames reach no one. Without the note, the pane is not loaded: print one frame (`--once`), tell the user to check that `/plugin` lists `agentic-qe` with its version and a `mod active` line (Claude Code 2.1.287 or later; update the plugin if the version is old), and give the command for their own terminal: `node "${CLAUDE_SKILL_DIR}/scripts/panel.ts" --watch`.
- `--split`: where the pane opened (see `--watch`), start nothing else. Otherwise run `node "${CLAUDE_SKILL_DIR}/scripts/panel-split.ts" --app <app>`. It opens the live panel beside the session (tmux, iTerm, WezTerm, Windows Terminal) or prints the exact command to run in a second terminal or the desktop app's Terminal panel.
- `--serve`: run `node "${CLAUDE_SKILL_DIR}/scripts/dashboard-server.ts" --root . [--app <app>] --open` in the background and tell the user the URL it prints; `--open` also opens it in their browser. If a dashboard already runs for this project it prints that link and exits. `--link` only prints the link of a running dashboard.
- `--export`: run `node "${CLAUDE_SKILL_DIR}/scripts/dashboard-server.ts" --root . [--app <app>] --export` and tell the user the path it prints (`docs/qe/<app>/09-release/dashboard.html`): one self-contained, read-only HTML file of the dashboard with every document rendered and every screenshot embedded. The plugin also writes it by itself after `approve gate 5`. Phase documents live at `docs/qe/<app>/<NN-phase>/<file>`.
- `--session`: run `node "${CLAUDE_SKILL_DIR}/scripts/export-session.ts" --root . --app <app>` and tell the user the path it prints (`docs/qe/<app>/sessions/session-<time>.md`, with a `.json` beside it): the plugin's own record of the run (gates and accepted gaps, commands and tool activity, coverage, tests in the repo, validator, results), never the conversation. The pane's **export session** button and `/qe-pane export` do the same.
- Numbers you report come from these scripts' output only (`panel.ts --json`, `check-gate.ts`); never state counts of your own. On Windows, `!` commands run in Git Bash: write paths with forward slashes. Never ask the user to start the dashboard; the start command does it.

The panel shows:
- Phases in strict order. A phase is done only when its artifact exists and every earlier required phase is done; otherwise it shows as out of order. Execute counts as done when the execution summary exists or `results/` holds unit, integration or E2E JUnit files. Heal appears only when tests fail.
- Gates 0 to 5 (intake, requirements and stories, plan, design, generate, release). If the ledger is untrusted, every gate shows as pending.
- Test counts per level, blockers, ledger trust and the next command.

## Live dashboard (`--serve`)
The plugin starts the dashboard by itself when the user sends `/agentic-qe:qe-start <app>` (or `$qe-start`), opens it in their browser, and starts it again after `approve gate 0 for <app>` if it is not running. It updates as files change. Do not run `--serve` after a start command unless the user asks. The `open_browser` option (default `true`) turns the browser opening off. It listens on `127.0.0.1` only, always on port 4173 (option `dashboard_port`); one dashboard runs per project, and a second start or `--serve` hands back the running one's link. Only when another project's dashboard holds the port does it take the next free one up to 4190 and needs the access link: a one-time token that sets an HttpOnly cookie. The link is shown to the user when the run starts and by `--serve`; do not repeat it elsewhere or write it into files.
- Views: overview and verdict, gates 0 to 5, requirements and stories, test cases, traceability, results, defects, files, activity. Download ZIP exports `docs/qe/<app>/` and `results/`.
- It shows the next command (`/agentic-qe:qe-<x> <app>` or `$qe-<x> <app>`) and the approval phrase (`approve gate N`) with copy buttons. It never approves a gate and never runs an agent.
- Users can edit existing documents (`.md .json .csv .txt .yml .yaml` under `docs/qe/<app>/`) and, after Gate 4, generated test sources listed in the manifest. Every save is logged as a `doc_edit` ledger record, reopens that document's gate and every later approved gate (shown as REOPENED), and the user re-approves by typing the phrase.
- `.qe/` and `results/` are never writable from the browser.
- Files: `scripts/dashboard-server.ts` (server and API), `scripts/dashboard-ui.ts` (page, CSS and script as strings), `scripts/zip.ts` (ZIP writer for Download ZIP).
- Stop it with Ctrl+C in its terminal or by killing the pid in `.qe/dashboard.json`.
