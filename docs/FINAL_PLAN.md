# Final plan: Agentic QE Harness (`aqh`), Skill Studio, Azure (for approval)

Date: 2026-11-12. Branch: `feature/maf-harness-platform`. **Nothing in sections 4 to 11 is built yet.** Implementation starts only after the owner approves this plan, and decisions D1 to D6 (section 12) are answered.

## 1. Where things stand (measured, 2026-11-11 and 2026-11-12)

| Area | State | Evidence |
|---|---|---|
| Offline suite | 679 passed on PostgreSQL (local) | `pytest tests -m "not e2e and not live and not smoke and not desktop"` |
| CI | **Not green yet.** The run for `06318ec` is in progress. It fixes the last known causes: `tenacity` missing for MAF MCP; Windows `initdb` folder rights; Ubuntu 26 beta apt mirror (now `ubuntu-24.04`) | GitHub Actions run 43157835613 |
| Desktop installers | **Built in CI:** DMG for Apple silicon and Intel, MSI for Windows, merged `latest.json` | run 43042356541, artifacts `desktop-*` and `desktop-latest-json` |
| Azure zips | Both start through their startup scripts with PostgreSQL: `API health: 200; UI /login: 200` | `scripts/azure_local.py --check` |
| Skill from a BRD | **Passes end to end.** Studio: plan, approve, generate, tests 13/13, evaluation uplift +0.12, publish. Harness: ran the skill (total 27.54, as the BRD says) and created an FR-6 validator skill from the BRD | `docs/evidence/runs/2026-11-11-skill-from-brd/` |
| QE cycle through the harness | **Stops at Gate 1.** Gate 0 is approved; discovery and requirements files are written. But the model wrote `requirements.json` with an empty list to satisfy the write guard, and three fix attempts left it empty | `docs/evidence/runs/2026-11-11-harness-plugin-cycle2/` (attempts 1 to 6) |

**Open defects found by the live runs (fixed in the plan below):**
1. The harness checks that a file *exists*, not that the step is *done*. The plugin's own gate-check script is the right oracle (section 5.3).
2. The harness stops every turn at 25 model rounds. The leaderboard's top harnesses have no turn cap inside the harness (section 3.1).
3. Context compaction drops files the model already read, so it reads them again (318 reads in one run).
4. Skill Studio does **not** load the `skill-creator` skill. It uses the `skill-creator` agent with `skills=()`, so `skills/skill-creator/SKILL.md` is never applied (`core/skill_studio/author.py:33`).
5. Live runs published three test skills into the repository's own `skills/` folder, and commit `e089d77` included them: `skills/brd-invoice-totaler`, `skills/computing-invoice-totals`, `skills/invoice-total-calculator`. Removal needs the owner's yes (D6), and tests must get a throwaway `ATLAS_SKILLS_DIR`.

## 2. Direct answers

- **Does Skill Studio use the skill-creator skill?** No. It uses the `skill-creator` agent and its prompt only. The plan (section 7) makes every Studio call load `skills/skill-creator` through MAF's skills, so its guidance applies.
- **Does the QE cycle use Chromium and Playwright for evidence?** Yes, for UI cases. agentic-qe's `qe-execute` runs `npx playwright test`; screenshots go to `test-results/` and are copied to `docs/qe/<app>/06-execution/evidence/e2e/`; Gate 5 refuses sign-off without them. The harness shell now passes `PLAYWRIGHT_BROWSERS_PATH`, so Chromium installed by `dev.py setup` is found.
- **REA (reverse engineering).** REA's own instructions say to skip it for source repositories: it is for compiled binaries and shipped apps. `deepseek-ai/deepseek-harness` is an open MIT source repository, so it was read directly: its docs, subsystems and package layout (section 3.2).
- **Kudu zip compared with `azure-litellm-proxy`.** That project zips the sources and lets Oryx build on deploy. Ours zips the sources and builds once in `startup.py` and `startup.js`. Running both builds was the discrepancy. Oryx is now turned off everywhere (`SCM_DO_BUILD_DURING_DEPLOYMENT=false`) and the guide says so. Two lessons are kept for the guide: `.node-version` matters when Oryx builds, and `Compress-Archive` in Windows PowerShell 5.1 can write backslash paths, which is why `package_azure_kudu.py` writes the zip itself.

## 3. Research summary

### 3.1 Harness leaderboard (Joel Niklaus, Hugging Face)

The leaderboard holds the model fixed (GLM-5.3-Flash, DeepSeek-V4.1-Flash, Flint) and compares harnesses on Terminal-Bench 2.1 and DeepSWE v1.1, with 3 attempts per task:
- **Average:** mini-swe-agent scored highest (51.4%); Kimi Code, Hermes, Pi and Claude Code are statistically tied with it. OpenCode and OpenClaw finished last (27.3% for OpenClaw).
- **DeepSeek-V4.1-Flash** (our model): Hermes Agent led.

**What the strong harnesses share** (from the leaderboard's `harness-settings.md`):

| Choice | Strong harnesses | Ours today |
|---|---|---|
| Turn or step cap inside the harness | None (Claude Code, Codex, Pi, Kimi, Hermes, DeepSeek Harness) | 25 model rounds per turn, then "continue" |
| Compaction trigger | 85 to 90% of the window, or window minus a reply reserve | MAF token budget; tool results collapsed after the last 4 groups |
| What compaction keeps | The last ~15k to 20k tokens or the last N messages, plus an LLM summary of older history | The summary may drop the files already read |
| Overflow | Compact and retry once to 3 times (Pi, Kimi, fx) | No retry |
| Large tool results | Trimmed (DeepSeek Harness: over 8,192 characters), or old results cleared (Claude Code) | Full results until compaction |
| Loops | Repeat-tool reminder at 3, 5 and 8 identical calls (DeepSeek Harness); Cline stops after 3 consecutive mistakes | `write_first` guard only |
| Tool set | Few, strong tools: read, edit (string replace), write, bash, todo, subagent; tool search for the rest (Qwen) | Many platform tools plus a deferred index |

### 3.2 DeepSeek Harness (`deepseek-ai/deepseek-harness`, "Everything is a Plugin")

- **Architecture:** a microkernel on Cordis. Every capability is a plugin: tools, skills, MCP, compaction, spill, approval, plan mode, subagents, LSP, worktrees, terminal and UI panels.
- **Tool pipeline:**
  1. The `tool/call` is logged.
  2. The `pre-execute` waterfall runs: hooks, permission, sandbox.
  3. Guards (deny or abstain) run, with a one-shot approval.
  4. The `execute` waterfall runs: timeout, retry, metrics.
  5. The tool body runs, with filesystem write and edit intent gates.
  6. The `post-execute` waterfall runs: accept, block, replace, add context.
  7. The result is normalized (a throw becomes `isError`), and one model-facing `tool/result` is logged.
- **Skills:** discovery by rank. Project roots `.dsh/skills`, then `.agents/skills`, then custom folders, then user folders, then bundled. The catalog (name and description only) is sent once as a durable reminder and re-sent when it changes or after compaction. Bodies load on demand.
- **MCP:** servers are configured per scope. Tool names include the server name. Resources and server instructions join the system prompt, size-limited.
- **Other pieces worth taking:**
  - *Spill:* a large tool output is saved to a file, and the model gets a locator plus a preview.
  - *Repeat-tool reminder.*
  - *Structured error taxonomy.*
  - *Runtime argument validation:* we already do this with `strict_args`.
  - *Session JSONL persistence:* zstd-compressed, versioned formats with migrations.
  - *Explicit turn cancellation, goal mode, worktrees, LSP.*

### 3.3 Claude Code (official docs)

- **The loop:** gather context, act, verify. Sessions are JSONL under `~/.claude/projects/` (resume, fork). Files are snapshotted before edits (rewind).
- **Compaction:** a "Compact Instructions" section in CLAUDE.md steers what is kept. Thrash detection stops a compaction loop.
- **Discovery:**

  | What | Where | Precedence |
  |---|---|---|
  | Skills | `~/.claude/skills`, `.claude/skills` in the cwd and every parent up to the repository root, plugin skills (`/plugin:skill`), `--add-dir` | Enterprise, then personal, then project |
  | Subagents | Managed, then `--agents`, then `.claude/agents/`, then `~/.claude/agents/`, then plugin `agents/` | Higher wins |
  | MCP | Local (`~/.claude.json`, per project), project (`.mcp.json`, shared), user (`~/.claude.json`); managed config for admins | Local, then project, then user |

- **Context:** MCP tool definitions are deferred and loaded through tool search. Skill descriptions are always in context; bodies load on use. `disable-model-invocation` skills cost nothing until invoked.

### 3.4 Other agents' skill folders (to discover the same skills)

| Agent | Project | User |
|---|---|---|
| GitHub Copilot | `.github/skills`, `.claude/skills`, `.agents/skills` | `~/.copilot/skills`, `~/.agents/skills` |
| Google Antigravity | `.agents/skills` (legacy `.agent/skills`), and parents up to the repository root | `~/.gemini/config/skills` (legacy `~/.gemini/antigravity/skills`) |
| OpenAI Codex | `.agents/skills` | `~/.agents/skills`, `~/.codex/skills` |
| DeepSeek Harness | `.dsh/skills`, `.agents/skills` | `~/.dsh/skills`, `~/.agents/skills` |

### 3.5 What MAF 1.24/1.25 gives us

`create_harness_agent` brings function invocation, per-call history persistence, compaction (before and after, inside the tool loop), todos, plan and execute modes, file memory, file access, `SkillsProvider` with `skills_paths` (several folders) and a `script_runner`, background agents, a shell executor, tool approval with standing rules (`auto_approval_rules`), looping, OpenTelemetry, context providers and middleware. MCP tools: stdio, HTTP and WebSocket. AG-UI hosting.

## 4. Target architecture

```text
  Surfaces:   Web UI (Next.js)        Desktop (Electron)         CLI: aqh
                  |                        |                        |
                  +----------- AG-UI / REST -----------+------ in-process (same core)
                                                        |
  Harness core:  MAF create_harness_agent
                   + Discovery registry (skills, agents, commands, MCP, hooks; scopes and precedence)
                   + Tool pipeline middleware (pre: hooks, permission, sandbox lease | guards: repeat-tool, oracle
                     | execute: timeout, retry | post: hooks, spill, verify)
                   + Context engine (pinned command, catalog reminder, compaction with keep-recent, read cache)
                   + Session log (JSONL per session: events, approvals, checkpoints)
                   + Error taxonomy (one shape for model, tool, MCP, hook and sandbox failures)
  Capabilities:  plugins (Claude Code format) = skills + commands + agents + hooks + .mcp.json
  Storage:       PostgreSQL (state), files and JSONL (workspaces, sessions), Blob after G6
```

Principle: **one harness core and three surfaces.** The web UI, the desktop app and `aqh` run the same `harness.build`, so a fix lands everywhere.

## 5. Harness work (in order)

### 5.1 Discovery registry (skills, agents, commands, MCP, hooks)

- **Sources, from highest to lowest precedence:**

  | Rank | Scope | Folders |
  |---|---|---|
  | 1 | Platform | Admin-installed plugins, Studio-published skills |
  | 2 | Session | Added for this chat only |
  | 3 | User | `~/.aqh/{skills,agents}`, `~/.claude/{skills,agents}`, `~/.agents/skills`, `~/.copilot/skills`, `~/.gemini/config/skills` |
  | 4 | Project | `.aqh/`, `.claude/`, `.agents/`, `.agent/`, `.github/` (skills and agents), in the workspace root and its parents up to the git root |
  | 5 | Plugin | Namespaced `/plugin:name`, never shadowed |
  | 6 | Bundled | Bundled skills |

- **Collisions:** the higher rank wins. The loser stays reachable under `/<source>:<name>`, shown in the `/` menu.
- **Trust:**
  - Repository folders (project scope) are untrusted content (CLAUDE.md). Their skills, agents and commands are listed, but each needs a human "trust this repository's skills" approval once per repository and commit range before the model may load one (D1).
  - A repository's `.mcp.json` is listed but never started by itself: an admin or the owner approves it.
- **Discovery behaviour:** one registry feeds the `/` menu, the model's catalog reminder (name and description), `load_skill`, the subagent list and the MCP list. It is re-read when files change, and the catalog is re-sent after compaction.
- **MAF:** `SkillsProvider(FileSkillsSource([...]), DeduplicatingSkillsSource, FilteringSkillsSource)` covers skills. Agents become MAF background agents. The Phase R capability registry stores the result.

### 5.2 MCP scopes

- **Scopes:** platform (admin), project (per project, owner-managed, shared with members), user (personal, desktop and local), session (temporary).
- **Precedence for the same server name:** session, then project, then user, then platform.
- **Tool names** carry the server name. Schemas are deferred and loaded through `find_tools` and `load_tools` (already built).
- **The `aqh mcp` command:** `aqh mcp add [--scope user|project|session] <name> -- npx -y <package@version> …`. The same in the UI (MCP page: a scope selector), and `.mcp.json` import with approval.

### 5.3 The agent loop: no hard cap, an oracle instead

- **Rounds:** remove the 25-round turn cap. Keep a **budget** (tokens, minutes, cost) per turn and per run, shown live. Stop only on: a finished task, a pending approval, a budget, or a user stop.
- **Done means verified:** a plugin command declares its check (agentic-qe: `check-gate.ts --gate N`). After every write to the command's files, a post-execute hook runs the check and appends its result (PASS or FAIL with gaps) to the tool result. The loop continues while it says FAIL, and stops when PASS. This replaces "the file exists", which the model gamed with `"requirements": []`.
- **Repeat-tool reminder:** at 3, 5 and 8 identical calls, ask the model to change approach.
- **Read cache:** a re-read of an unchanged file returns "unchanged since your read at step N" plus its path, not the whole content again. This saves context and stops the re-read loop.
- **Spill:** a tool result over 8,000 characters is saved to `sessions/<id>/spill/` and the model gets a preview and a locator to read ranges.

### 5.4 Context and compaction

- **Pinned context (never compacted):** the active command, todos, the files written this session, and the plugin's gate state.
- **Compaction:** at 85% of the window, keep the last ~20k tokens, summarise older history with the pinned context, and re-send the skill catalog.
- **Overflow:** compact and retry once, then report.
- **Thrash detection:** two compactions in a row without progress stops the loop, with the reason.
- **MAF:** `TokenBudgetComposedStrategy` with `SummarizationStrategy` and `ToolResultCompactionStrategy` is already in place. Add a keep-recent strategy and the pinned-context provider (built: `ActiveCommandContext`).

### 5.5 Error handling

- **One error shape** for model, tool, MCP, hook, sandbox and database failures: `{code, message, action, retryable, trace_id}`. It is shown as a card in chat and in the CLI, recorded with the span, and the model gets the same text.
- **Retries:**
  - Model calls: back off on 429 and 5xx; a stall timeout (no first byte in 240 s) is reported.
  - Tools: a timeout per tool. A crashed MCP server is reconnected once.
- **Joinable logs:** every log line carries `trace_id` and `session_id` (Phase Q3).

### 5.6 Subagents

- **Definitions:**
  - Markdown agents from the discovery registry (`.claude/agents`, `.agents/agents`, plugin `agents/`). The frontmatter gives the tools allowed, skills to preload and the model.
  - **Fork mode** copies the conversation; **fresh mode** starts clean.
  - **Parallel runs:** MAF background agents, with `start`, `wait_for_first_completion` and results (built for plugin agents).
- **Live pane** (section 6) shows each subagent's status and tool calls.
- **Writes:** subagents that need writes get approval cards routed to the parent chat (MAF background agents have no approval channel today: a gap, section 10).

### 5.7 Sessions (like Claude Code)

- **One JSONL per session** with every event: user message, model message, tool call, tool result, approval, hook, compaction, error. Path: `<data>/sessions/<project>/<session-id>.jsonl`. It is readable, not encoded like MAF's `~session-…` file names.
- **Resume, fork and rewind.** Rewind uses file checkpoints taken before each write (the workspace is a git clone, so a checkpoint is a git stash or tree object).
- **Desktop:** `~/Library/Application Support/Agentic QE Platform/data/sessions/...` (macOS) and `%APPDATA%\...` (Windows).

### 5.8 RAG, only where it pays

- **A repository map instead of reading everything:** files, symbols and imports (tree-sitter or Python `ast`, plus `ripgrep`), with BM25 over paths, symbols and docstrings. The model asks "where is X handled" and gets ranked files. This attacks the 318-read pattern.
- **Evaluated** with a labelled question set per fixture repository: recall@5 and MRR. It is kept only if it raises task success, measured by the harness eval (5.9).

### 5.9 Harness evaluations

- **A harness eval suite:** about 30 small tasks on fixture repositories:
  - read and answer;
  - edit a function;
  - fix a failing test;
  - run a script;
  - use a skill;
  - create a skill;
  - delegate to a subagent;
  - call an MCP tool;
  - a plugin command to a passing gate.

  Each task has an outcome oracle (tests pass, file content matches, the gate is approved), with 3 attempts per task, scored like the leaderboard: resolve rate, solved on all 3, cost and time.
- **Release rule:** run on every harness change. It gates a release: no drop beyond the run-to-run noise measured on the same build.

## 6. UI: the right-hand pane (like Claude Code desktop)

- **Tabs in the harness page's right pane:**
  - **Tasks:** todos, live.
  - **Activity:** each tool call and subagent, live, with status, duration and result preview.
  - **Terminal:** xterm.js. Each command goes through the same approved shell: the allowlist, the approval card and the sandbox lease. It is used for `npx` skill and MCP installs, and for tests. Desktop and local only; read-only history on the web.
  - **Files:** the files changed this session, with diffs.
  - **Approvals.**
- **Status line:** model, tokens and cost so far, the budget left, and the active command.
- **The `/` menu:** skills, commands, agents and MCP prompts from the discovery registry, with their source shown (project, user, plugin).

## 7. Skill Studio

1. **Use the skill-creator skill:** every Studio call loads `skills/skill-creator` through MAF (`skills=("skill-creator",)`), on top of the agent prompt.
2. **A requirements page like the BRD page (G4):**
   - **The editable document:** purpose, input contract, outputs, tasks (a checklist, each task with an owner: instructions, script or subagent), subagents, formats, and eval cases with assertions.
   - **Versions:** every save is a version with its SHA-256; approval hashes that exact version.
   - **Tasks:** tasks show progress during generation and testing.
3. **A per-skill dependencies file,** installed in an isolated environment for tests (HTML-to-PDF needs a PDF library).
4. **The input contract** is stated in the plan, and eval inputs must follow it (found earlier: prose inputs for a DOCX skill).
5. **Install skills from npm or git in the terminal pane** (desktop): `npx skills add <package>` or `git clone` into the user scope, then discovered like any other skill and shown as untrusted until approved.

## 8. CLI: `aqh` (Agentic QE Harness)

- **Install:**
  - from a checkout: `pipx install .`, `uv tool install .`, or `pip install -e .` (a `pyproject.toml` with the console script `aqh`);
  - later, `pipx install agentic-qe-harness` from PyPI (D3).
- **Commands:**
  - `aqh`: an interactive session in the current folder, with a status line, approvals as prompts and `/` completion.
  - `aqh -p "task"`: print mode for scripts and CI.
  - `aqh --resume [id]`, `aqh --fork <id>`.
  - `aqh skills list|show|install`, `aqh agents list`, `aqh mcp add|list|remove --scope`, `aqh plugins install|enable|disable`.
  - `aqh sessions list|export`.
  - `aqh doctor`: checks Python, Node, PostgreSQL, the model and Playwright.
- **Two modes:**
  - Local: runs the core in-process against the local PostgreSQL and the current folder as the workspace.
  - Remote: `aqh --server https://…` signs in and talks to a deployed API over AG-UI.
- **Landing page:** an "Install the CLI" section with copy buttons for macOS and Linux (`pipx install …`) and Windows (`py -m pipx install …`), plus `aqh doctor`.
- `bin/harness` stays as a thin alias that runs `aqh`.

## 9. Azure plan and guide

**Cost cap: at most $25 a month** (owner, 2026-11-12). Always on, the standard plan costs about $28.50: B1 $12.41, PostgreSQL B1ms $12.41, 32 GiB storage $3.68, Blob about $0.10. The App Service plan and storage bill around the clock; PostgreSQL compute bills only while it runs.

**The standard therefore stops PostgreSQL outside working hours.** Running 12 hours a day on 22 weekdays is 264 h × $0.017 = $4.49.

| Item | Per month |
|---|---|
| App Service plan B1 | $12.41 |
| PostgreSQL B1ms, 264 h | $4.49 |
| PostgreSQL storage, 32 GiB | $3.68 |
| Blob | about $0.10 |
| Key Vault | under $0.01 |
| Start/stop automation (Azure Automation, free 500 job minutes) | $0 |
| **Total** | **about $20.70** |

Outside those hours the app shows a clear "database is stopped (outside working hours)" message, never an error page. The schedule is an app setting. The guide shows the cost per schedule, and that "always on" costs $28.50, above the cap.

- **Cost table:** keep the 2026-11-11 prices. Add:
  - an upgrade path (P0v3 plan, PostgreSQL B2s) with its price;
  - the free outbound allowance and the per-GB price after it;
  - Application Insights per GB;
  - a "stop at night" estimate;
  - a re-check command (`prices.azure.com` query) so prices can be refreshed.
- **Detailed portal steps:** one screenshot per step (resource group, Key Vault, PostgreSQL, storage, plan, two apps, identity, settings, ZipDeployUI, access restriction, firewall, first sign-in), taken in the portal by the owner or from a test subscription (D5), with every field named exactly as the portal shows it.
- **Zipping guide:**
  - macOS, Linux and Windows commands;
  - what the zip contains and why: forward slashes, LF startup scripts, tracked files only, `.deployment` with the build off;
  - a "verify the zip" step: `azure-local --check`, plus listing the zip's top folder;
  - common mistakes: Explorer zips, a wrong runtime stack, a missing startup command, Oryx turned on.
- **First real deployment** to a test subscription, with the evidence recorded: health, sign-in, a harness turn, a QE run. Not done yet.

## 10. MAF mapping: concept, MAF primitive, gap, plan

| Concept (Claude Code or DeepSeek Harness) | MAF primitive | Ours today | Gap | Plan |
|---|---|---|---|---|
| Agent loop with tools | `Agent`, function invocation, `create_harness_agent` | Yes | 25-round cap | 5.3: budgets instead |
| Run until the task is done | `loop_should_continue`, `loop_next_message` | Todos-based | Not oracle-based | 5.3: verification hook |
| Todos | `TodoProvider` | Yes | — | Show in the pane |
| Plan mode | `AgentModeProvider` | Yes (execute default) | — | — |
| Skills, progressive | `SkillsProvider`, `FileSkillsSource(skills_paths)` | Platform folders only | No project, user or `.github` folders; no trust step | 5.1 |
| Skill scripts | `script_runner` | Built (`skill_runner.py`) | Studio skills only | Plugin skills' scripts behind approval |
| Slash commands | **Not in MAF** | `plugins.expand_slash`, active command | Built | Registry-driven `/` menu |
| Subagents | Background agents (experimental) | Plugin agents read-only | No approval channel for subagent writes (**not in MAF**) | 5.6: route approvals to the parent |
| Fork a subagent with context | **Not in MAF** | — | — | Copy the history into a new session |
| MCP | `MCPStdioTool`, `MCPStreamableHTTPTool`, `MCPWebsocketTool` | Platform registry, grants | No scopes | 5.2 |
| MCP scopes and `.mcp.json` | **Not in MAF** | — | — | 5.2 |
| Tool search and deferred schemas | `FunctionInvocationContext.add_tools` (experimental) | `find_tools`, `load_tools` | — | Keep |
| Hooks (PreToolUse and others) | Function and chat middleware | Adapter for 5 events | No Stop, PreCompact or Notification | Extend the adapter |
| Tool pipeline (pre, guard, execute, post) | Middleware chain | Partly | No timeout or retry layer, no spill | 5.3, 5.5 |
| Argument validation | Pydantic input models | `strict_args` | — | — |
| Approvals with standing rules | `ToolApprovalMiddleware`, `auto_approval_rules` | Per call | "Always allow this command" not exposed | UI and CLI option |
| Compaction | `TokenBudgetComposedStrategy` and strategies | Yes | No keep-recent, no retry on overflow, no thrash stop | 5.4 |
| Spill of large results | **Not in MAF** | — | — | 5.3: middleware |
| Read cache | **Not in MAF** | — | — | 5.3: middleware |
| Repeat-tool reminder | **Not in MAF** | — | — | 5.3: middleware |
| Session history | `FileHistoryProvider` (JSONL) | Encoded file names | Not resumable or forkable by id | 5.7 |
| File checkpoints and rewind | **Not in MAF** | — | — | 5.7: git-based |
| Shell | `LocalShellTool` (`agent-framework-tools`, pre-release) | Allowlist, approval, lease | No persistent cwd, no background jobs | Add jobs with output streaming |
| Interactive terminal | **Not in MAF** | — | — | 6: xterm.js through the approved shell |
| File access | `FileAccessProvider`, `FileSystemAgentFileStore` | Yes | — | — |
| Memory | `FileMemoryProvider` | Per user and project | — | — |
| Observability | OpenTelemetry | Spans, `/traces` | Logs not joined | 5.5 |
| Error taxonomy | Exceptions, `include_detailed_errors` | Partial | No single shape | 5.5 |
| Model retries | Client retry settings | `max_retries=1` | No backoff or stall policy | 5.5 |
| AG-UI streaming | `AgentFrameworkAgent` | Yes | — | — |
| CLI | **Not in MAF** | `bin/harness` | Basic | 8: `aqh` |
| Evaluations | `evaluate_agent`, evaluators | Agent evals, RAGAS | No harness task eval | 5.9 |
| RAG over code | **Not in MAF** (bring your own index) | Capability registry BM25 | No repository map | 5.8 |
| LSP code intelligence | **Not in MAF** | — | — | Later (not planned now) |
| Worktrees | **Not in MAF** | Sandbox clone per project | One workspace per thread | Later |

## 11. Tests and evidence

Every feature gets:
1. **Offline tests** with the scripted model (`tests/`).
2. **A Playwright story** in `tests/e2e/`, written as user stories in `docs/HARNESS_USER_STORIES.md`:
   - `/` menu sources;
   - project and user skills;
   - the trust prompt;
   - MCP scopes;
   - the terminal pane install;
   - subagents in the activity pane;
   - resume and fork;
   - rewind;
   - budgets and stop;
   - error cards;
   - landing page CLI install.
3. **A CLI story test:** `aqh -p` in a subprocess against a fixture repository.
4. **Live runs** on the real model, with transcripts in `docs/evidence/runs/`:
   - the full agentic-qe cycle to Gate 5 on `personal-finance-mcp`;
   - the harness eval suite (5.9) before and after each harness change.
5. **One HTML evidence report** per run (`dev.py evidence`).

## 12. Decisions for the owner

| # | Decision | Proposed default |
|---|---|---|
| D1 | Repository skills, agents and instruction files (`.claude/`, `.github/`, `AGENTS.md`, `CLAUDE.md`) are untrusted content. Load them after a once-per-repository human approval? | Yes, approval once per repository; listed but not loaded before it |
| D2 | Replace the 25-round cap with budgets (tokens, time, cost) per turn and per run? | Yes. Defaults: 2M tokens, 30 min, set per user on the Usage page |
| D3 | CLI distribution | `pipx install` from the repository now; PyPI package `agentic-qe-harness` later |
| D4 | Desktop database | Keep requiring an installed PostgreSQL now; bundle PostgreSQL binaries in the installer next |
| D5 | Portal screenshots for the guide | The owner captures them, or a test subscription for the agent to deploy to |
| D6 | Delete the three test skills committed in `e089d77` (`skills/brd-invoice-totaler`, `skills/computing-invoice-totals`, `skills/invoice-total-calculator`), and point tests at a throwaway skills folder? | Yes |

## 13. Order of work (after approval)

1. **CI green on all three systems** (in progress), and D6.
2. **The harness core:**
   - the verification oracle and no cap (5.3);
   - the read cache, spill and repeat reminder (5.3);
   - compaction with keep-recent (5.4);
   - the error taxonomy (5.5).

   Then **the live agentic-qe cycle to Gate 5.**
3. **The discovery registry with scopes and trust** (5.1, 5.2), the `/` menu, and the MCP scopes UI and CLI.
4. **Sessions:** JSONL, resume, fork, rewind (5.7).
5. **Subagents** with routed approvals (5.6), and **the right pane:** activity, terminal, files (6).
6. **The `aqh` CLI** (8) and the landing page install section.
7. **Skill Studio:** the skill-creator skill, the requirements page and dependencies (7).
8. **The harness eval suite** (5.9), and the repository map only if the eval shows a gain (5.8).
9. **The Azure guide refresh,** and a first deployment to a test subscription with evidence (9).
10. **Desktop with bundled PostgreSQL** (D4), and signed installers once certificates exist.
