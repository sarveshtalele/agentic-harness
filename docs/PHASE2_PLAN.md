# Phase 2 plan: a Claude Code-class harness on Microsoft Agent Framework, and the product changes around it

**Status: draft for the owner's approval (revision 3, 2026-11-12); decisions in section 17 taken. Nothing here is built.** The restart order stays in `docs/FINAL_PLAN.md`; its section 14 points here.

**Goal (owner, 2026-11-12):** one harness that does what Claude Code does (reads, edits, runs Bash and PowerShell, runs skill scripts in any common language, hooks, subagents, MCP, sessions, permissions, sandbox) built on MAF, usable three ways with the same core: the **`aqh` CLI** in a terminal on macOS and Windows (Linux too), the **desktop app**, and the **web app**.

**Owner decisions already taken:**
- Desktop: central sign-in with an admin-created account.
- Atlassian: the remote MCP server with OAuth; the only outside source in BA Studio, optional.
- Features: role defaults plus per-member overrides.
- Order: harness first.

**Decisions taken this revision** (section 17): the harness may run real shells (D-SHELL); web keeps the allowlisted runner; every shell command asks by default; the CLI uses the proxy base URL, key and model from settings.

---

## 1. What is wrong today, with evidence

| # | Seen in live runs and code | Cause |
|---|---|---|
| G1 | The model guessed `run_shell` lines for agentic-qe's `.ts` scripts | Plugin scripts are not tools |
| G2 | `file_access_ls(path=…)`: wrong argument (now an error) | The catalogue shows a name and one line; arguments only after `load_tools` |
| G3 | Requirements written with `source_evidence`, which the checker never reads | Output contracts invisible until a check fails |
| G4 | Plugin-owned files retried 14+ times | Hook rules learned only by being blocked (now remembered) |
| G5 | Platform QE tools called while a plugin command ran | Tools that step aside are not explained |
| G6 | `.claude/skills`, `.github/skills`, `.agents/skills` in a repository never seen | `_skills()` reads plugin skills and `skills/` only |
| G7 | MCP tools fixed at turn start | No refresh on `tools/list_changed` |
| G8 | Only `scripts/run.py` runs; TypeScript, Bash and PowerShell skill scripts are refused | `skill_runner.py` allows one Python entry point |
| G9 | A skill with a broken script looks like a working one | No health check, no flag |
| G10 | No number says discovery is better or worse | No discovery eval |
| **G11** | **No real shell:** `run_shell` splits the text into arguments and allows only `node`, `npx`, `npm`, `python`, `python3`, `pytest` and read-only `git`; no pipes, redirects, `&&`, environment changes, `cd`, Bash or PowerShell | `harness_kit/shell.py` follows the CLAUDE.md rule "Subprocesses take an argument list with no shell" |
| G12 | No background commands, no output streaming to the model, no long-running dev servers | Each command is one blocking call with a 2-minute timeout |
| G13 | No CLI: the harness is reachable only through the web app (and the desktop app that wraps it) | Plan item `aqh` not started |
| G14 | No sessions on disk, resume, fork or rewind; no permission modes beyond approve-each-call | Plan items 4 and 5 not started |

## 2. Research: what "do everything Claude Code does" means, checked against sources

### 2.1 Claude Code (code.claude.com docs, read 2026-11-12)

- **Tools:** Read, Write, Edit, Glob, Grep, Bash, PowerShell, Monitor (background command whose output lines come back to the model), NotebookEdit, LSP, WebFetch, WebSearch, Agent (subagents), Skill, ToolSearch (deferred tools), task tools (TaskCreate/List/Update/Stop), AskUserQuestion, EnterPlanMode/ExitPlanMode, EnterWorktree/ExitWorktree, MCP resource tools, cron and wake-up tools.
- **Bash:** each command in a separate process; `cd` carries over inside the project; environment variables do not persist (unless an env file is set); default timeout 2 minutes, maximum 10; a command past its timeout moves to the background; `run_in_background` for servers; output over ~30,000 characters is saved to a file and the model gets the path and a preview; exit code 1 is treated as normal for `grep`, `find`, `diff`, `test`.
- **PowerShell:** a separate tool; on Windows it is on by default (PowerShell 7 `pwsh.exe`, falling back to Windows PowerShell 5.1) and becomes the primary shell; Bash stays available for POSIX scripts through Git Bash; on macOS and Linux it needs `pwsh` 7+; runs with `-ExecutionPolicy Bypass` at process scope only. Hooks that inspect shell commands must match `Bash|PowerShell`.
- **Skills:** discovered from enterprise, personal `~/.claude/skills`, project `.claude/skills` (and nested ones up to the repository root), added directories, and plugins (namespaced); watched live without restart. Frontmatter: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context: fork`, `agent`, `background`, `hooks`, `paths`, `shell` (bash or powershell), `metadata`, `license`, `compatibility`. Substitutions `$ARGUMENTS`, `$0`, `$name`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`. `` !`command` `` runs a command before the model sees the skill and inserts its output. **Scripts run through the Bash or PowerShell tool**; the model calls `${CLAUDE_SKILL_DIR}/scripts/...` with the interpreter the skill names. So any language the machine can run is supported.
- **Hooks:** 30+ events (SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, Stop, SubagentStart/Stop, PreCompact, SessionEnd, FileChanged, ConfigChange, …); handler types `command`, `http`, `mcp_tool`, `prompt`, `agent`; exit 2 blocks; JSON `permissionDecision` allow, deny, ask, defer, `updatedInput`, `additionalContext`; configured in user, project, local, managed settings, plugins, skills and subagents.
- **Sandbox:** off by default; macOS Seatbelt, Linux and WSL2 bubblewrap with a network proxy and allow-listed domains; **native Windows has no sandbox**. Covers Bash, PowerShell, Monitor and child processes; not file tools, hooks or local MCP servers.

### 2.2 Microsoft Agent Framework (`agent-framework.pdf`, 968 pages, and the installed 1.25 packages)

- **Harness Agent** (`create_harness_agent`): function invocation, per-call history, compaction, todos, plan and execute modes, file memory and file access, tool approval with standing rules, OpenTelemetry, skills, background agents, looping, and **shell execution composed from the shell package**. The UI is the application's job; .NET ships a sample console.
- **Shell package** `agent-framework-tools` (installed here, 1.0.0b261030): `LocalShellTool` (persistent or stateless mode, `shell=` to pick the program, working directory confinement, environment, timeout, 64 KiB output caps, `approval_mode`), `DockerShellTool` (container isolation), `ShellPolicy` (allow and deny patterns before approval), `ShellEnvironmentProvider` (probes shell family, OS, working directory and CLI versions: git, node, python, docker). The docs: one persistent shell per user session, never shared; the policy is only a pre-filter, keep approval on.
- **Agent Skills:** file, inline, class and MCP sources; `SkillsProvider` advertises names, `load_skill`, `read_skill_resource`, `run_skill_script`; file scripts discovered by `script_extensions` and run by the host's `script_runner`.
- **Agent Hooks:** implements the framework-neutral AGENT-HOOKS-0.1 contract (enforce or evaluate-only); Python only.
- **CodeAct** (Hyperlight, Monty) lets the model write a program that calls tools; noted, not planned.

### 2.3 Agent Skills spec (agentskills.io)

`scripts/` holds executable code; "Supported languages depend on the agent implementation"; the optional `compatibility` field states needs ("Requires Python 3.14+ and uv").

### 2.4 DeepSeek Harness (read earlier, `FINAL_PLAN.md` 3.2)

"Everything is a plugin" on a microkernel; a tool pipeline (log, pre-execute hooks and permission and sandbox, guards, execute with timeout and retry, post-execute, normalize errors); skills by rank (`.dsh/skills`, `.agents/skills`, user, bundled); spill of large outputs to files; repeat-tool reminder; session JSONL with versioned formats; worktrees; LSP.

### 2.5 Long-running harness practice (Anthropic engineering, "Effective harnesses for long-running agents")

An initializer session writes `init.sh`, a progress file and a JSON feature list (all failing; agents may change only the pass flag); each later session starts with `pwd`, git log and the progress file, picks one feature, starts the app with `init.sh`, runs an end-to-end check first, works one feature, tests it in a real browser, commits, and writes progress. Failure modes it fixes: premature victory, undocumented state, features marked done too early.

## 3. Target architecture

```
              +---------------- front ends ----------------+
              |  aqh CLI (terminal)   desktop app   web app |
              +---------------------+----------------------+
                                    |  one protocol: AG-UI events over HTTP/SSE,
                                    |  or in-process for the CLI's local mode
+-----------------------------------v-----------------------------------+
|                         harness core (Python, MAF)                    |
|  create_harness_agent + our providers and middleware                  |
|  - capability index (tools, skills, commands, agents, MCP, scripts)  |
|  - tool pipeline: log > hooks > permission rules > sandbox > approval |
|                   > execute (timeout, background, spill) > post hooks |
|  - shells: Bash, PowerShell (persistent sessions per conversation)    |
|  - script runtime: Python, TypeScript/JavaScript, Bash, PowerShell,   |
|                    any declared interpreter; health check and flags   |
|  - sessions: JSONL, resume, fork, checkpoints and rewind              |
|  - subagents, background tasks, worktrees, todos, plan mode           |
|  - MCP client: stdio and HTTP, OAuth, live list_changed               |
+-----------------------------------+-----------------------------------+
                                    |
              settings (managed > CLI flags > local > project > user)
              governance (features, gates, ledger) from the platform
```

**One core, three front ends.** The CLI can run the core in-process (local mode) or talk to a local or remote server (connected mode); the desktop app runs the same core behind its local server; the web app runs it on Azure with the restricted web profile (section 6).

## 4. Tools: parity table

| Claude Code | Ours (name the model sees) | Built on | Today | Plan |
|---|---|---|---|---|
| Read, Write, Edit | `read_file`, `write_file`, `edit_file` (string replace), `edit_lines` | MAF file access store | Yes (file_access_*) | Rename to the short names; keep old names as aliases one release |
| Glob, Grep | `glob`, `grep` | Python stdlib, ripgrep when present | Partly | Add `glob`; grep with ripgrep fallback |
| Bash | `bash` | MAF `LocalShellTool(shell=bash)` persistent per conversation | No (allowlist only) | **New** (section 5) |
| PowerShell | `powershell` | MAF `LocalShellTool(shell=pwsh or powershell.exe)` | No | **New**; primary shell on Windows |
| Monitor | `monitor` | background process + line stream into the next turn | No | **New** |
| Background tasks | `run_in_background` flag, `task_output`, `task_stop` | process registry per conversation | No | **New** |
| NotebookEdit | `edit_notebook` | nbformat | No | Later (low priority) |
| LSP | `lsp` | language servers (pyright, typescript-language-server) when installed | No | Later |
| WebFetch, WebSearch | `web_fetch` (allow-listed hosts) | httpx with proxy and redaction | No (web search off) | **New**, off on web profile unless an admin enables hosts |
| Agent | `agent` (subagents) and background agents | MAF background agents | Partly | Routed approvals, own context, worktree option |
| Skill | `load_skill`, `read_skill_resource`, `run_skill_script` | MAF `SkillsProvider` | Partly | Full frontmatter (section 7) |
| ToolSearch | `find_tools`, `load_tools` | our catalogue | Yes | Becomes the capability index (section 8) |
| TodoWrite / tasks | `todos_*` | MAF `TodoProvider` | Yes | Show in all front ends |
| Plan mode | `/plan`, `exit_plan` | MAF `AgentModeProvider` | Yes | Approval of the plan as a card |
| Worktrees | `enter_worktree`, `exit_worktree` | git worktree | Partly (generated code lands in a worktree) | **New** as tools |
| AskUserQuestion | `ask_user` | MAF request/response | No | **New** (also used by brainstorming) |
| MCP resources | `list_mcp_resources`, `read_mcp_resource` | MAF MCP tools | No | **New** |

## 5. Shells: Bash and PowerShell, for real

### 5.1 Which shell, per platform

| Platform | Primary | Also | Found by |
|---|---|---|---|
| macOS | `bash` tool: `/bin/bash` (or `$SHELL` if it is bash or zsh) | `powershell` tool when `pwsh` 7+ is installed | `shutil.which` at session start |
| Linux | `bash` | `powershell` when `pwsh` is installed | same |
| Windows | `powershell` tool: `pwsh.exe` (7+), else `powershell.exe` (5.1), with `-NoProfile -ExecutionPolicy Bypass` at process scope | `bash` tool through Git Bash (`bash.exe` from Git for Windows) when installed; WSL bash when chosen in settings | same, plus the Git for Windows install path |

`ShellEnvironmentProvider` tells the model, every session, which shells exist, the OS, the working directory and the versions of git, node, python, docker, pwsh, so it writes commands for the right shell.

### 5.2 Behaviour (matches Claude Code where it matters)

- One **persistent** shell per conversation (MAF `mode="persistent"`), never shared between users or conversations; `cd` persists inside the workspace and is reset (with a note) if it leaves it; environment changes persist only in that shell.
- Timeout: default 2 minutes, the model may ask up to 10; a command that passes its timeout moves to the background instead of dying (servers keep running); background commands get 30 minutes by default, up to 2 hours.
- Output: up to 30,000 characters inline; beyond that the full output is saved to the session folder and the model gets the path, the size and the first 2,000 characters (spill, as DeepSeek Harness and Claude Code do); failures get head and tail.
- Exit code 1 counts as normal for `grep`, `rg`, `find`, `diff`, `test`, `git diff`, `git grep`.
- Every command: one approval card unless a permission rule or mode allows it (section 9), the ledger records command, exit code, duration and redacted output tail, and hooks receive `tool_name: "Bash"` or `"PowerShell"` with `tool_input.command`.

### 5.3 Isolation tiers (what keeps a real shell safe)

| Tier | Where | How |
|---|---|---|
| T0 approve each command | everywhere, default | approval card; deny rules first |
| T1 OS sandbox | macOS: Seatbelt profile (`sandbox-exec`) limiting writes to the workspace, temp and allowed folders, network through a local proxy with allowed hosts; Linux: bubblewrap with the same rules; **Windows: no OS sandbox exists** (as in Claude Code) so Windows stays at T0 unless WSL2 or a container is chosen | sandboxed commands may run without a card when the owner allows it ("auto-allow in sandbox") |
| T2 container | `DockerShellTool` when Docker is present (desktop, CI) | per-conversation container with the workspace mounted |
| Web profile on Azure | App Service has no Docker and no OS sandbox | real shells only inside a job container (Azure Container Apps Jobs, consumption plan) or not at all; see decision D-SHELL-WEB (section 17); until then the web profile keeps today's allowlisted runner |

## 6. Profiles

| Capability | CLI local | Desktop | Web (Azure) |
|---|---|---|---|
| Bash, PowerShell, background, monitor | Yes (T0, T1 on macOS and Linux) | Yes | Allowlisted runner (D-SHELL-WEB) |
| Skill scripts (any language) | Yes | Yes | Python and Node only, in sandbox slots (D-SHELL-WEB) |
| stdio MCP, `npx` installs, plugin installs | Yes | Yes | No (HTTP MCP only) |
| Worktrees | Yes | Yes | Yes (server workspace) |
| Web fetch | Allowed hosts | Allowed hosts | Admin-allowed hosts only |

## 7. Skills and scripts in every language

### 7.1 Discovery and live reload

- Scopes and precedence as Claude Code: managed (enterprise) > personal (`~/.claude/skills`, `~/.agents/skills`, `~/.aqh/skills`) > project (`.claude/skills`, `.github/skills`, `.agents/skills`, nested up to the repository root) > added directories > plugins (namespaced `/plugin:skill`) > platform `skills/`.
- A file watcher (polling every 2 seconds with content hashes, so it works the same on macOS and Windows) adds, changes and removes skills mid-session; `/reload-skills` forces it.

### 7.2 Frontmatter we honour

`name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `context: fork` with `agent` and `background`, `hooks`, `paths`, `shell`, `license`, `compatibility`, `metadata`. Substitutions `$ARGUMENTS`, `$N`, `$name`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}` (and `${AQH_SKILL_DIR}` as an alias). `` !`command` `` injection runs through the same permission rules, in the skill's `shell`.

### 7.3 Running scripts

Two ways, both supported, as in Claude Code and MAF:
1. **The model runs them through `bash` or `powershell`**, the way the skill's SKILL.md says (`python ${CLAUDE_SKILL_DIR}/scripts/x.py`, `node …/x.ts`, `bash …/x.sh`, `pwsh …/x.ps1`). Any language installed on the machine works.
2. **`run_skill_script`** (MAF) for skills that list scripts: our runner detects the language and runs it with an argument list, so it works without a shell (and is the path on the web profile).

Language detection for `run_skill_script` and for the health check, first match wins:

| Order | Signal | Example |
|---|---|---|
| 1 | Declared in SKILL.md: frontmatter `metadata.runtime`, or the command the body gives | `node ${CLAUDE_SKILL_DIR}/scripts/check.ts` |
| 2 | Shebang | `#!/usr/bin/env python3`, `node`, `tsx`, `bash`, `pwsh`, `ruby` |
| 3 | Extension | `.py` Python; `.ts .mts .cts` TypeScript; `.js .mjs .cjs` Node; `.sh .bash` Bash; `.ps1` PowerShell; `.rb` Ruby; `.go` (go run); `.java` (java single-file) |
| 4 | Project manifest next to the script | `package.json` (type, scripts, dependencies), `pyproject.toml` / `requirements.txt` |

Interpreters:

| Language | Command | Notes |
|---|---|---|
| Python | skill `.venv` python, else the platform python | deps from `requirements.txt` installed on desktop and CLI after an approval card |
| TypeScript | `node` 22.18+ (type stripping) | `tsx` when the skill depends on it or uses enums/namespaces |
| JavaScript | `node` | ESM or CommonJS by extension or `package.json` `type` |
| Bash | `bash` (macOS, Linux; Git Bash or WSL on Windows) | flagged on Windows when neither exists |
| PowerShell | `pwsh`, else `powershell.exe` on Windows | `-NoProfile -ExecutionPolicy Bypass` at process scope |
| Others | the declared or shebang interpreter if found on PATH | flagged "interpreter not installed" otherwise |

Input: CLI flags (`--name value`, MAF's convention) and JSON on standard input; the skill reads whichever it documents. Output: stdout, stderr tail, exit code, redacted, spilled when large.

### 7.4 Health check and flags

On discovery, install, publish, and any content change: interpreter present at the right version; syntax check (`python -m py_compile`; `node --check` for JS and TS; `bash -n`; PowerShell parser `[System.Management.Automation.Language.Parser]::ParseFile`); dependency check (Python imports, Node module resolution); smoke run `--help` or the skill's first eval case within 20 seconds. Result per script **ok** or **flagged** with one reason. A flagged skill: the model sees "flagged: <reason>; do not use", `run_skill_script` refuses it, `/skills`, the `/` menu and the harness pane show a red **Flagged** badge with the reason and **Check again**; three runtime failures in a row also flag it; every flag goes to the ledger. A skill flagged only on this machine (for example Bash on Windows without Git Bash) says so: "not runnable here".

## 8. The live capability index

(First draft: `FINAL_PLAN.md` 14.2; unchanged in intent, refined here.)

- **Sources**, each with a content hash: platform tools; MAF file and shell tools; skills from every scope with Claude Code precedence (user, project workspace `.claude/skills` `.github/skills` `.agents/skills`, plugin, platform); plugin commands, agents, hooks and scripts; MCP servers (live `tools/list`); output contracts (field names and shapes read from the plugin's normalizers, validators and templates).
- **One card per capability:** purpose, when to use it, argument schema with one valid example, preconditions (approval, plugin write window, profile), constraints (paths a hook protects), outputs and their contract, health (7.4), version hash.
- **Real time:** each turn re-hashes sources and rebuilds only changes; MCP refreshes on `notifications/tools/list_changed` and every 5 minutes. The model gets "changed since your last turn"; the right pane gets the same diff.
- **Model exposure in three tiers:** core tools loaded; a ranked index in the instructions (ranked by the active command and recent use); `load_tools` returns full cards. New tools: `describe_contract(path)` (fields a file must have) and plugin scripts as typed tools (for example `agentic_qe.check_gate(gate, app)`).
- **Command binding:** the active command's body is parsed for the tools, scripts, files and contracts it needs; those are preloaded and pinned.
- **Guards:** unknown tool names answer with the nearest three matches; strict arguments, refused-file memory, error shape stay.
- **Measured:** each call records tool chosen, first-try argument validity, refusals, invented names. A 20-task discovery eval with the real model runs before and after (baseline first); CI replays recorded traces with `ScriptedClient`.

## 9. Permissions, modes, hooks and settings

### 9.1 Permission modes

| Mode | Behaviour |
|---|---|
| `default` | Reads free; every write, shell command, script, web fetch and MCP call asks |
| `acceptEdits` | File writes and edits inside the workspace are allowed; shells still ask |
| `plan` | Read-only until the plan is approved (MAF plan mode) |
| `auto` | Commands inside the OS sandbox (T1) or a container (T2) run without a card; everything else asks |
| `bypass` | Everything allowed; CLI and desktop only, refused when a managed setting forbids it, never on web |

Switch with `/mode`, `Shift+Tab` in the CLI, or the mode menu in desktop and web.

### 9.2 Permission rules

Claude Code syntax: `Bash(npm run *)`, `PowerShell(Get-ChildItem *)`, `Read(~/secrets/**)`, `Edit(/src/**)`, `WebFetch(domain:github.com)`, `mcp__server__tool`. Lists `allow`, `ask`, `deny`; deny wins; MAF `ShellPolicy` gets the shell patterns as a pre-filter, and our tool pipeline applies the rest before MAF's approval. Rules come from settings (9.4), skills' `allowed-tools` (for the invoking turn only), and the admin's governance (web).

### 9.3 Hooks

- Events we fire: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, Stop, SubagentStart, SubagentStop, PreCompact, PostCompact, Notification, FileChanged, ConfigChange (today: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, SubagentStop).
- Handler types: `command` (argument list, `shell: powershell` honoured on Windows), `http`, `mcp_tool`; `prompt` and `agent` later.
- Contract: exit 2 blocks with stderr as the reason; JSON `continue`, `decision`, `permissionDecision` allow/deny/ask/defer, `updatedInput`, `additionalContext` (10,000 characters).
- Sources: managed, user, project, local settings; plugin `hooks/hooks.json`; skill and subagent frontmatter.
- Built on MAF function and agent middleware (Python Agent Hooks, AGENT-HOOKS-0.1, adopted when it leaves beta).

### 9.4 Settings files (same layout as Claude Code, so existing projects work)

Precedence: managed (`/Library/Application Support/AgenticQE/managed-settings.json`, `C:\ProgramData\AgenticQE\managed-settings.json`) > CLI flags > `.claude/settings.local.json` > `.claude/settings.json` > `~/.aqh/settings.json` (also reads `~/.claude/settings.json` read-only). Keys: `permissions`, `env`, `hooks`, `sandbox`, `defaultShell`, `model`, `enabledPlugins`, `mcpServers`. Changes are watched and fire ConfigChange.

## 10. Sessions, subagents, MCP and long-running work

- **Sessions:** every conversation is a JSONL file (`~/.aqh/projects/<project>/<session>.jsonl` for CLI and desktop; the database for web) with versioned records; `--resume`, `--continue`, `/resume`, fork a session, **checkpoints**: files are snapshotted before each edit, `/rewind` restores code, conversation, or both. Compaction keeps recent tool groups and a summary (MAF compaction, steered by a "Compact instructions" section in the project memory file).
- **Memory files:** `AGENTS.md` and `CLAUDE.md` (project, user, nested) loaded at start, as Claude Code and Codex do.
- **Subagents:** from `.claude/agents/`, `~/.claude/agents/`, plugins, and built-ins (explore, plan, general); own context, own tool list, optional worktree; approvals route to the parent's front end.
- **Background tasks:** `run_in_background`, `/tasks` list, stop; output files readable by the model; time limits as section 5.2.
- **MCP:** stdio and streamable HTTP; scopes local > project (`.mcp.json`) > user; OAuth 2.1 with PKCE for remote servers (Atlassian); tools deferred behind tool search; `list_changed` refresh; `/mcp` to connect, authenticate and see status.
- **Long-running mode** (from Anthropic's practice): `/init` writes `init.sh` or `init.ps1`, a progress file and a JSON feature list; each session starts by reading them, runs the app and a smoke test, works one feature, verifies it in a real browser (Playwright), commits on its branch, updates progress. Features may only flip their pass flag; tests may not be removed (our existing evidence rules).

## 11. Front ends

### 11.1 `aqh` CLI (macOS, Windows, Linux)

- Install: `pipx install agentic-qe-harness` or the desktop installer's "Add aqh to PATH"; one Python package, no shell scripts (Windows-safe).
- Interactive: a full-screen terminal UI (prompt_toolkit and rich): streaming answer, tool calls with collapsible output, approval prompts (`y`, `n`, always for this session, edit the command), todos, mode indicator, `/` menu with commands and skills (flagged ones disabled), `@` file mentions, `!` to run a shell command directly, `#` to add to memory, `Esc` to interrupt, `Esc Esc` to rewind, `Ctrl+R` history search, `Shift+Tab` mode cycle.
- Slash commands: `/help`, `/init`, `/mode`, `/model`, `/mcp`, `/skills`, `/reload-skills`, `/agents`, `/tasks`, `/todos`, `/resume`, `/rewind`, `/compact`, `/clear`, `/cost`, `/permissions`, `/hooks`, `/login`, `/logout`, `/doctor`, `/exit`, plus plugin commands.
- Headless: `aqh -p "prompt"` with `--output-format text|json|stream-json`, `--input-format stream-json`, `--allowedTools`, `--disallowedTools`, `--permission-mode`, `--max-turns` (off by default), `--add-dir`, `--model`, `--resume <id>`, `--continue`; exit code non-zero on failure. For CI and scripts.
- Modes: **local** (core in-process, workspace = current folder, model from the proxy settings per D-CLI, section 17) and **connected** (`aqh --server https://…` drives a server session; approvals still answered in the terminal).
- `aqh doctor`: shells found, interpreters and versions, Git Bash on Windows, sandbox available, MCP servers, skills flagged, model reachable.

### 11.2 Desktop app

- The same core behind its local server; adds a **Terminal** pane (a real PTY: node-pty with ConPTY on Windows) where the person runs their own commands and `npx` installs, and the harness's background tasks appear as tabs.
- Right pane tabs: Activity (live tool pipeline), Capabilities (index, flagged, changed), Files (diff per checkpoint, rewind), Terminal.
- Sign-in through the server (R6); local PostgreSQL bundled later (D4).

### 11.3 Web app

Same chat and panes; shells per section 6; approvals as cards; sessions in the database.



## 12. User journeys and screens

Plain text sketches; the final look uses the existing design tokens, fonts and light and dark themes, with no new colours.

### 12.1 Signed out: landing page

```
+----------------------------------------------------------------+
| Agentic QE Platform                               [ Sign in ]   |
|                                                                |
|  Governed AI agents for requirements, test design and test     |
|  runs, with every gate signed by a named person.               |
|                                                                |
|  [ What it does ]  [ How gates work ]  [ Security ]            |
+----------------------------------------------------------------+
```
- No installers, no CLI install section, no version numbers (R1). Only **Sign in**.

### 12.2 Sign in, then Home (new `/home`)

```
+----------------------------------------------------------------+
| Home                                    Priya (BA)  [Account v] |
|----------------------------------------------------------------|
| Continue where you left off                                     |
|  > Payments revamp  - BRD draft v3, 2 questions waiting         |
|  > Ledger API       - QE gate 2 waiting for your signature      |
|                                                                |
| Your work               | Desktop app (only if the admin allows)|
|  [ BA Studio ]          |  macOS Apple silicon  199 MB  [Get]   |
|  [ QE cycle ]           |  macOS Intel          206 MB  [Get]   |
|  [ Approvals (2) ]      |  Windows              173 MB  [Get]   |
|                         |  Version 0.1.0, SHA-256 on hover      |
+----------------------------------------------------------------+
```
- Tiles show only features this member may use (R2). The download panel shows only if "Desktop downloads" is allowed for them; otherwise it is absent, not greyed.

### 12.3 Admin: Governance, Features (new tab on the existing governance area)

```
+------------------------------------------------------------------+
| Governance > Features                        [ Save ] (ledgered) |
|------------------------------------------------------------------|
| Role defaults      Harness BA QE Bugs Skills MCP Docs Downloads  |
|  qe_lead              x    x  x   x     x     -    x     x       |
|  ba                   -    x  -   -     -     -    x     -       |
|  developer            x    -  x   x     -     -    x     x       |
|  viewer               -    -  -   -     -     -    x     -       |
|------------------------------------------------------------------|
| Member overrides   [ search member ]                             |
|  ravi (developer)   Harness: deny   Downloads: allow   [remove]   |
|  [ + add override ]                                              |
|------------------------------------------------------------------|
| Effective access for: [ priya v ]  -> BA, Docs                   |
+------------------------------------------------------------------+
```
- Every change is a ledger entry with who, when, before and after. "Effective access" previews what a member will see.

### 12.4 BA: from files to a signed BRD (BA Studio)

Step 1, sources:
```
+------------------------------------------------------------------+
| BA Studio > New BRD: Payments revamp                             |
| 1 Sources   2 Brainstorm   3 BRD draft   4 Review and sign G1    |
|------------------------------------------------------------------|
| Drop files here or [ Choose files ]   docx md txt pdf pptx       |
|  vision.docx      12 sections   parsed   [view] [remove]         |
|  kickoff.pptx     18 slides     parsed   [view] [remove]         |
|  legacy.ppt       needs LibreOffice on the server  [why?]        |
|                                                                  |
| Optional: Jira and Confluence (Atlassian)                        |
|  [ Connect Atlassian ]  (shown only if the admin enabled it)     |
|  After connecting: [ search Jira issues / Confluence pages ]     |
|   [x] PAY-142 Refund rules (Jira)   [x] Payments v2 spec (Conf.) |
|   [ Attach selected ]                                            |
|                                                                  |
| Describe what you need (one or two sentences)                    |
| [ Customers can refund part of an order within 30 days ...    ]  |
|                                          [ Start brainstorming ] |
+------------------------------------------------------------------+
```
Step 2, brainstorm (one question at a time, editable):
```
+------------------------------------------------------------------+
| 2 Brainstorm                                       Question 3 of ~8|
|------------------------------------------------------------------|
| What I understood so far (play-back)                    [edit]   |
|  Partial refunds for orders paid by card; finance team approves  |
|  above 500 EUR. Source: vision.docx s2, PAY-142.                 |
|                                                                  |
| Question                                                [edit]   |
|  Does a refund after 30 days need a different approval, or is it |
|  refused?   Why I ask: it decides whether the BRD has a second   |
|  approval path.   From: kickoff.pptx slide 7                     |
|                                                                  |
| Your answer                                                      |
| [                                                             ]  |
| [ Answer ]  [ Skip ]  [ I don't know - propose something ]       |
|------------------------------------------------------------------|
| History: Q1 answered, Q2 answered (edit any)                     |
+------------------------------------------------------------------+
```
Then **Approaches** (2 or 3, with trade-offs and the recommendation), the BA picks one; then the BRD draft is written; a reviewer agent checks it and returns at most one round of questions only the BA can answer; the BA edits the draft (every save a version) and signs G1.

### 12.5 QE lead: the QE cycle with full traceability

```
+------------------------------------------------------------------+
| QE cycle: Ledger API          G0 ok  G1 ok  G2 ...  G3  G4  G5   |
|------------------------------------------------------------------|
| Now: Gate 2 test plan     check: PASS   [ Sign gate 2 ]          |
|------------------------------------------------------------------|
| Trace  REQ-7 -> SC-12 -> TC-31 -> tests/test_refund.py::... -> PASS|
|        REQ-8 -> SC-13 -> (no case yet)                    gap     |
| Evidence: junit.xml, Playwright trace, coverage map (plugin)     |
+------------------------------------------------------------------+
```
- Every row links to the requirement's quoted source line, the test file and the run's evidence. Gaps are listed first.

### 12.6 Anyone: the harness

- Left: chat. Right pane tabs: **Activity** (live tool calls), **Capabilities** (what is loaded, available, flagged, changed this turn), **Files**, **Terminal** (desktop only).
- `/` menu lists commands, skills and flagged skills (flagged ones disabled with the reason).

### 12.7 Desktop first run (R6)

```
+------------------------------------------------+
| Agentic QE Platform                             |
| Server: [ https://aqe-ui-....azurewebsites.net ]|
| Username [        ]  Password [        ]        |
| [ Sign in ]                                     |
| Accounts are created by your admin.             |
+------------------------------------------------+
```
- The app verifies against the server, receives a signed session for N days, and starts its local backend under that member's identity and features. No "save as admin" step, no keychain prompt for a password (only the session token is stored, encrypted).

## 13. The six product changes, in detail

### R1 Home page and gated downloads
- `/home` after sign-in (12.2); the landing page loses installers and the CLI section.
- `/api/downloads` answers only members with the Downloads feature; others get 403.

### R2 Governance of features
- Features: Harness, BA Studio, QE cycle, Bugs and Feature, Skill Studio, MCP, Documents, Desktop downloads, Traces, Usage.
- Stored as role defaults plus member overrides; resolved once per request in `core/auth.py`; every API route names its feature (deny by default); the navigation hides what is denied; ledgered.

### R3 BA Studio uploads and brainstorming
- Uploads: `.docx` (python-docx), `.md`/`.txt`, `.pdf` (existing parser), `.pptx` (python-pptx, slide text and notes), `.ppt` via LibreOffice when installed (else a clear message). Each file becomes sections with file, page or slide; size limits; `redact()`; stored as a versioned document.
- Brainstorming: adapted from obra/superpowers `skills/brainstorming` (licence and attribution kept) as a MAF workflow with human-in-the-loop steps: look before asking (read sources), one question at a time with the reason and the source, play-back chunks, approaches, BRD draft, reviewer agent ("builder check"), BA approval. Questions and play-backs are editable in the UI. The superpowers browser companion is not ported: BA Studio is the companion.

### R4 Atlassian (optional, the only outside source in BA Studio)
- The admin enables the Atlassian remote MCP (`https://mcp.atlassian.com/v2/mcp`, streamable HTTP) and grants it to roles.
- Each member connects once with OAuth 2.1 (PKCE); tokens encrypted per member, never logged.
- In BA Studio, search Jira issues and Confluence pages, attach several; each becomes a document with its key or page id, version and link; refresh pulls a new version. Content is untrusted data.
- Tool names come from the server's live `tools/list` (section 8), not hardcoded.

### R5 QE cycle on the plugin's own scripts and agents
- Uses section 8's typed script tools and contracts and section 7's runner; the plugin's agents run as background agents.
- Traceability view (12.5); generated tests run against the real repository; evidence linked per case. Live run to Gate 5 with evidence (the item 2 goal).

### R6 Credentials and desktop sign-in
- First admin: the setup script generates a random password, prints it once, stores only its hash; Key Vault on Azure.
- Passwords: scrypt with a random salt (today) plus a server pepper from Key Vault; rehash on login when the cost changes; minimum 12 characters; a local breached-password list; lockout (exists).
- Desktop: central sign-in (12.7); the local backend starts only with a valid signed session and the member's features; no self-made admin; sign-out clears the session.
- Azure guide updated with the new settings and the desktop server URL.

## 14. UI quality: Playwright audit

`tests/e2e/test_ui_audit.py` (added 2026-11-12) opens every page signed out and as admin, desktop light, desktop dark and phone, takes full-page screenshots into `docs/evidence/ui-audit/`, and checks browser errors, failed requests, leaked raw text (undefined, NaN, null, `[object Object]`, template braces, stack traces), horizontal scroll, cut-off text, images without alt text and controls without names. Its findings are in section 14.1; each one is fixed, then the test must pass with zero findings, and it stays in the e2e suite.

### 14.1 Findings

Run on 2026-11-12: 34 pages x 3 views, 103 screenshots in `docs/evidence/ui-audit/`, 61 automatic findings plus what the screenshots show.

| # | Finding | Where | Fix |
|---|---|---|---|
| U1 | Every signed-in page scrolls sideways on a phone (30 pages): the sidebar stays open at 240 px and squeezes the content to about 100 px (stat cards and buttons wrap word by word) | App shell, phone width | Below 768 px the sidebar becomes a drawer behind a menu button; the header wraps its buttons into a menu |
| U2 | Text cut off on phone: the QE phase names (Intake, Plan, Requirements, Design, Generate, Release) and "no evaluation has run" (16 items) | Project QE page, `/agents` | Chips wrap onto new lines; tile text wraps |
| U3 | The light theme is ignored: with the system set to light, every page still renders dark | Theme | Follow the system setting until the person picks one with the theme button |
| U4 | Sidebar labels cut with an ellipsis: "Codebase & AST Discov…", "BA Studio (BRD & Gherki…", "Autonomous QE & AI SD…" | Project sidebar | Shorter labels: Repository, BA Studio, QE cycle, Defects, Approvals, Governance, Runs, Logs, Prompts |
| U5 | Jargon and inflated names: "Autonomous QE & AI SDLC Lifecycle", "Enterprise QE", "AI Specialist Roster", "One-Click Local Sandbox Execution Package" | Headings and nav | Plain names: "QE cycle", "Agents", "Download a runnable copy" |
| U6 | Two near-identical download buttons on the QE page: "Export SDLC Package (.ZIP)" and "Download Setup Package (.ZIP)" | Project QE page | One "Download" menu with both, each with a one-line description |
| U7 | The landing page calls `/api/auth/me` signed out and logs a 401 error in the browser console | `/` | Skip the call when there is no session cookie, or treat 401 as "signed out" without an error |
| U8 | The word "null" is shown on the capability registry | `/capabilities` | Render an empty value as "none" or leave the cell empty |
| U9 | The capability registry is one 10,000-pixel table with no grouping | `/capabilities` | Group by kind with counts, collapse groups, keep search; becomes the Capabilities view of section 8 |
| U10 | Stat cards on Projects truncate labels on narrow widths ("Proje…", "Open findi…") | `/projects` | Fixed by U1; labels wrap |

The audit test itself had one wrong path (`/chat` exists only as `/chat/<id>`); removed. After the fixes the test must report zero findings in all three views.

## 15. Tests and evidence

- **Parity matrix, run on macOS, Windows and Linux in CI** (GitHub runners), each with the real shells present on that runner:
  - shell: persistent `cd`, environment in one shell, pipes and redirects, timeout moving to background, background server reached by a later command, spill over 30,000 characters, exit-code-1 rules, PowerShell on Windows with Bash through Git Bash;
  - scripts: one fixture skill per language (Python, TypeScript, JavaScript, Bash, PowerShell, an undeclared `.rb`), each run both through the shell and through `run_skill_script`; health flags for a syntax error, a missing module, a missing interpreter;
  - permissions: modes, allow/ask/deny rules, deny wins, sandbox auto-allow on macOS and Linux;
  - hooks: each event fires with the Claude Code payload shape; exit 2 and JSON decisions;
  - sessions: resume, fork, rewind restores files.
- **CLI golden tests:** headless `aqh -p` with `ScriptedClient` and `--output-format stream-json`, compared to recorded event streams; interactive UI tested with a pseudo-terminal.
- **Live tests with the real model:** a CLI session that builds and tests a small app end to end (init, feature list, Playwright check, commit) on macOS and on Windows; the agentic-qe cycle to Gate 5; one BA brainstorm to a signed BRD.
- **Discovery eval:** 20 recorded tasks, baseline now and after; reports tool-selection accuracy, first-try argument validity, invented names.
- **Playwright stories with screenshots** for every journey in section 12, light and dark; the UI audit (section 14) at zero findings.

## 16. Order (after approval)

| Step | What | Done means |
|---|---|---|
| 1 | Discovery eval baseline (20 tasks) | numbers recorded before any harness change |
| 2 | Persistent Bash and PowerShell with background, monitor, spill (section 5), permission modes and rules (9.1, 9.2); short tool names move to step 4 | parity matrix shell and permission rows green on 3 OS |
| 3 | Script runtime all languages, health flags (section 7) | script rows green; flagged skills shown in `/skills` |
| 4 | Capability index, skill scopes, live reload, MCP refresh (sections 8, 7.1). Built without typed per-script tools, `describe_contract` and tool renames: real shells, exact plugin run lines and the after-write check cover them (architecture doc section 14) | eval after shows the gain |
| 5 | Hooks (9.3), settings files (9.4), sessions, checkpoints, rewind, subagents, background tasks (10) | hook and session rows green |
| 6 | `aqh` CLI interactive and headless (11.1) | golden tests green; live CLI session on macOS and Windows |
| 7 | OS sandbox tiers (5.3) | sandbox rows green on macOS and Linux; Windows documented as T0 or container (built 2026-11-13: T1 Seatbelt and bubblewrap in `harness_kit/os_sandbox.py`; Windows stays T0 with cards; container T2 not built) |
| 8 | R6 credentials and desktop sign-in; desktop Terminal pane (11.2) | security tests; desktop story |
| 9 | R2 features governance, R1 home and gated downloads | stories and audit |
| 10 | UI audit fixes (section 14) | audit zero findings |
| 11 | R3 uploads and brainstorming, R4 Atlassian | stories; live brainstorm |
| 12 | R5 QE cycle to Gate 5 with traceability | live evidence |
| 13 | Azure guide, proposal workbook, docs | updated with real numbers |

## 17. Owner decisions (2026-11-12)

1. **D-SHELL: yes.** CLAUDE.md now allows the harness's `bash` and `powershell` tools to run shell commands, only through MAF `LocalShellTool` or `DockerShellTool`, after deny rules, hooks and approval, confined to the workspace, with every command in the ledger. Every other subprocess keeps the argument-list rule.
2. **D-SHELL-WEB: keep the allowlisted runner** on Azure. Full shells run in the CLI and the desktop app; the web profile runs Python and Node skill scripts in sandbox slots. No new Azure resource.
3. **D-SANDBOX: ask for every shell command** by default in the CLI and the desktop app; a person can switch a session to `auto` (sandboxed commands without a card on macOS and Linux; Windows still asks).
4. **D-CLI: the project's model proxy settings.** The CLI uses the same OpenAI-compatible proxy the platform uses: base URL, key and model name, which each person can change in a settings file:
   - `~/.aqh/settings.json` (user) and `.aqh/settings.json` (project) hold `model.baseUrl` and `model.name`, plus an `env` block as in Claude Code (`OPENAI_BASE_URL`, `DEFAULT_MODEL`);
   - the key is read from `OPENAI_API_KEY` in the environment or the settings `env` block, or stored with `aqh config set-key` in the operating system's keychain (macOS Keychain, Windows Credential Manager) so it is not left in plain text; the file is created with owner-only permissions and the key is never logged or printed;
   - precedence: CLI flags > project settings > user settings > environment; `aqh doctor` shows which source won (by name, never the value);
   - a person signed in to the server can also run in connected mode, where the server's model settings and governance apply.

## 18. MAF mapping

| Need | MAF primitive |
|---|---|
| Harness loop, todos, modes, compaction, memory, approvals, background agents | `create_harness_agent` |
| Bash, PowerShell | `agent_framework.tools.LocalShellTool` (persistent, `shell=`), `ShellPolicy`, `ShellEnvironmentProvider`; `DockerShellTool` for T2 |
| Skills from every scope, scripts in every language | `FileSkillsSource` with all paths and `script_extensions`, `script_runner` (section 7.3), `DeduplicatingSkillsSource` |
| Capability index and diff | `ContextProvider` |
| Plugin scripts as tools | `FunctionTool` with `input_model` |
| Hooks and permission pipeline | function and agent middleware; Agent Hooks (AGENT-HOOKS-0.1) when stable |
| Ask the user, brainstorming | workflow request/response (human in the loop) |
| MCP | MCP tools (stdio, streamable HTTP), `load_tools`, `list_changed` |
| Sessions | `AgentSession` with file history; our JSONL store and checkpoints |
| Front-end events | AG-UI events (web, desktop); in-process events (CLI local mode) |

## 19. Limits stated up front

- Native Windows has no OS sandbox (Claude Code has the same limit); Windows runs commands after approval, or in WSL2 or a container when chosen.
- A real shell on Azure needs D-SHELL-WEB (b); until then the web profile is deliberately narrower than CLI and desktop.
- Atlassian: Cloud only (remote server).
- LSP and notebook editing come after the core.
- CodeAct (the model writing programs that call tools) is not planned.

## 20. Discovery eval results (2026-11-13)

Same 20 tasks, real model (deepseek-v4-flash-global), every approval approved; scored by `backend/maf/evals/discovery.py`. Two answer checks were widened to patterns after the runs (a table row "Failed | 1" states the same fact as "1 failed"), and all three runs were re-scored with the same rule (`results-rescored.json` in each folder).

| Run | Code | Passed | Right tool used | Right tool first | Valid arguments | Invented tool names |
|---|---|---|---|---|---|---|
| Baseline | `b76ddbd` (before steps 2 to 4) | 13/20 (65%) | 85% | 55% | 100% | 6 |
| After steps 2 to 4 | `c6897c7` | 16/20 (80%) | 95% | 60% | 100% | 36 |
| After the eval fixes | working tree, 2026-11-13 | 18/20 (90%) | 95% | 55% | 99% | 4 |

The eval found: `run_skill_script` crashed on MAF's real skill objects (fixed); the model kept calling the web-only `run_shell` (now the primary shell's alias on local and desktop); deferred tools were called unloaded (now loaded on the spot). Still failing: `create-file` (the model explored and never wrote) and `run-ts` (the model tried `npx tsx`; the shell note now says Node runs .ts directly). Evidence: `docs/evidence/runs/2026-11-13-discovery-{baseline,after,after-fixes}/`.
