# Master Plan: one plan for the whole application

Status: written 2026-11-10. This is the only active plan. It merges the owner's request of 2026-11-10 with everything still open in the older plans.

The older plans keep their findings but no longer set the order of work:
- `docs/FINAL_HARNESS_PLAN.md` (dummy-data register F-01 to F-12);
- `docs/HARNESS_REBUILD_PLAN.md`;
- `docs/MODULARIZATION_PLAN.md`;
- `docs/HARNESS_GAP_ANALYSIS.md`;
- `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md`;
- `docs/DATA_ARCHITECTURE.md`.

## 1. Owner decisions recorded

| Date | Decision |
|---|---|
| 2026-11-10 | Data: fresh store `data/v2` (option A); the old `data/` is the backup |
| 2026-11-10 | **Yes to retiring legacy code:** <ul><li>the legacy harness: `HarnessView.tsx`, `src/backend/harness/*`, `api/harness.py`, the legacy `cli.py`;</li><li>the seed code: `core/seed_data.py`, `scripts/populate_seeded_repos.py`;</li><li>`api/mcp_playwright_tools.py`, once real MCP lists tools.</li></ul>Real parts move into `maf/` first |
| 2026-11-10 | Modularize first, then build. Every file stays at 200 lines or fewer, in feature folders |
| 2026-11-10 | **Azure is a cheap proof of concept,** reached as a browser link. <ul><li>No Redis and no cache database.</li><li>No harness on the web, because each harness user needs a dedicated workspace.</li><li>Access follows each member's project permissions.</li></ul> |
| 2026-11-10 | **Desktop:** Windows MSI and macOS DMG installers. The harness runs locally, with full harness behaviour on MAF only |
| 2026-11-10 | **Skill Studio:** <ul><li>asks whether the skill is instructions only or script based;</li><li>plans sub-agents and output formatting;</li><li>creates and really tests skills on real data.</li></ul> |
| 2026-11-10 | **Evidence:** an HTML report with screenshots for every user story, page and feature. No mocked data anywhere |

## 2. Definition of done

1. Every user story in `docs/USER_STORIES.md` (rewritten in M8 to cover every page) passes in Playwright on the real model, with a screenshot per step in the HTML report.
2. **CI gates.**
   - The fabrication baseline is `{}`.
   - The file-size baseline is `{}`, so no source file is over 200 lines.
   - The approvals gate passes.
3. The harness streams accurate replies with live status lines ("Analysing", "Creating", "Running tests"). Skills, tools, sub-agents, plugin commands and MCP tools are discovered on demand.
4. Skill Studio creates a skill from a real document, tests it on real data, scores it on the real model, and saves an immutable version.
5. MCP servers really connect and list their tools, and the harness can call them. Plugins install, enable and disable.
6. The Azure proof of concept is deployed from the step-by-step portal guide. It is first verified locally in the `web` profile (no harness).
7. Desktop installers build:
   - a macOS DMG locally;
   - a Windows MSI on the CI Windows runner.

   The desktop app runs the harness on its own local backend.

## 3. Phases

Each phase ends with:
- the offline suite, plus the E2E stories that phase turns green;
- evidence under `docs/evidence/runs/`;
- `PROGRESS.md`, `tasks.md` and the architecture docs updated.

Commit and push happen only when the owner says so, and only on `feature/maf-harness-platform`.

### M1. Retire legacy code (approved)

1. Move the real parts first. The static skill scanner (`harness/skill_specter.py`) becomes `maf/skills/security_scan.py`, without grades or "production ready" labels.
2. **Approvals.** Approval decisions stop calling the in-memory `approval_manager`; the database `approvals` table is the only source (`api/runs.py`, `api/governance.py`).
3. **Remove the legacy code.**
   - Backend: `src/backend/harness/`, `api/harness.py` and its router, `core/seed_data.py`, `scripts/populate_seeded_repos.py`.
   - Frontend: `components/HarnessView.tsx` and the `?engine=legacy` branch.
   - Tests that only exercise legacy code go too, and their real checks move to MAF tests.
4. **CLI.** `bin/harness` and `cli.py` are rebuilt on `maf/harness.py`, so the terminal harness is the same MAF harness.

### M2. Modularize (approved)

- **Backend.** A large module becomes a package of the same name whose `__init__.py` re-exports, so imports, routes and tests do not change. Packages: `api/skills`, `api/mcp`, `core/auth`, `repos/doc_parser`, `maf/engine`, `qe/execution`, `repos/sandbox`, `qe/emit`, `api/documents`, `api/projects`, `api/governance`, `api/settings`, `maf/runtime`, `maf/governance`, `maf/evals`, `maf/workflows/*`, `repos/ingest`, `core/models`, `qe/model`, `qe/confidence`.
- **Frontend.** Pages become thin. Their parts move to `src/frontend/features/<feature>/` (skills-studio, mcp, projects, findings, qe, ba, documents, runs, chat, agents, settings), and `content/docs.ts` is split by section.
- **Tests.** Test files over 200 lines split per feature, with no assertion removed.
- **CI gate.** A new `tests/test_file_size.py` acts as a ratchet like the fabrication gate. It ends at an empty baseline.

### M3. Skill Studio rebuilt on real data

Every step below is enforced in code, not only in the UI.

1. **Source.** Upload a document (PDF, DOCX, MD), pick a project document, or write requirements. The source is stored and quoted.
2. **Kind.** The user chooses **instructions only** (`SKILL.md` plus `references/`) or **script based** (`scripts/` with real code and its own tests).
3. **Plan.** The model proposes:
   - the name and description;
   - a task list;
   - the file list;
   - the sub-agent plan (which specialist handles which part, or none);
   - the output formatting (templates in `assets/`).

   The user edits and approves it. The server keeps the approved plan's SHA-256 and refuses to generate from an unapproved or changed plan.
4. **Generate.** The model writes each file from the approved plan and the source. `SKILL.md` follows the Agent Skills rules:
   - name rules;
   - a description of 1024 characters or fewer;
   - a body of 500 lines or fewer;
   - progressive disclosure through `references/`.
5. **Test for real.**
   - MAF must load the skill.
   - A script-based skill runs its own tests in the project sandbox, with `clean_env`, a timeout and an argument list. This runs only in the `local` and `desktop` profiles, because skill code is untrusted on a shared server.
   - The skill also runs on a sample input the user picks from real project data.
6. **Evaluate on the model.**
   - Eval cases from `evals/evals.json` run on the real model, with the skill and without it.
   - Deterministic assertions grade them, plus an LLM judge marked `self_graded`.
   - Scores go to `evaluation_metrics` with the judge model, `n` and the source. No score is shown without a measurement.
7. **Save.**
   - Every save is an immutable skill version (SHA-256, author, prompt reference, ledger entry).
   - The skill installs into the skills folder.
   - It can be downloaded as a zip.
   - Zip upload is guarded against zip-slip and checked like a generated skill.
8. **Studio issue audit.** The full list of current Studio defects goes into `docs/SKILL_STUDIO_AUDIT.md` before any fix, and each one is closed by a test.

### M4. Harness: as good as or better than DeepSeek Harness, on MAF only

- **Progressive discovery.**
  - Skills come through `SkillsProvider` (done).
  - Tools come through a `find_tools` / `load_tools` pair. Only tool names and one-line descriptions are in the prompt, and full schemas load on demand.
  - Sub-agents come through `BackgroundAgentsProvider` over the governed specialists.
  - Plugin commands use the "/" menu (done).
  - MCP tools come from granted servers.
- **Streaming and status.**
  - AG-UI text streams token by token.
  - Each tool start emits a status line in plain words ("Analysing the repository", "Creating BRD", "Running tests", "Loading skill planning-tests"), shown live in the chat with a spinner.
  - The final reply is checked against the stored copy.
- **Harness engineering.**
  - Plan and execute modes persist per thread (AG-UI thread snapshot store).
  - The UI shows approval cards for risky tools.
  - Long threads use context compaction (MAF compaction strategy).
  - Turns can be cancelled and resumed.
  - Tool budgets come from settings (done).
  - Hooks: the agentic-qe Claude hooks are adapted through `create_agent_hooks_middleware`.
  - Per-project memory (done).
  - Every tool call is audited (done).
- **Profiles.** `ATLAS_PROFILE=web|local|desktop`. In the `web` profile the harness, sandbox runs, script execution and stdio MCP are switched off, and their routes return 403 with a clear message.
- **CLI.** `bin/harness` uses the same MAF harness (from M1).

### M5. MCP and plugins that really connect

- **Connections.**
  - `MCPStdioTool` in the `local` and `desktop` profiles.
  - `MCPStreamableHTTPTool` for remote servers in every profile.
- **Connect.** "Connect" opens a real session and stores the tools from `list_tools`. Status is `connected` only after that, otherwise `error` with the message. Declared tool lists go away.
- **Grants.** An admin grants servers and tools per role. The harness gets only granted, connected tools.
- **Plugins.**
  - Install from a folder or zip, with manifest validation.
  - Enable and disable.
  - A plugin's `.mcp.json` registers its servers.
  - Plugin skills and commands appear in the "/" menu.

### M6. Azure proof of concept (cheapest)

- **Hosting.** One Linux App Service plan, **B1**, holds two web apps: API (Python) and UI (Node).
  - SQLite on `/home` with the `DELETE` journal.
  - The model is the existing endpoint, with its key in app settings.
  - No Redis, no cache, no PostgreSQL, no Container Apps.
  - `ATLAS_PROFILE=web`.
- **Access.** Everyone signs in. Project members and roles (`core/auth.py`) decide what each person sees. The API accepts traffic only from the UI app (access restriction).
- **Guide.** `docs/AZURE_POC_PORTAL_GUIDE.md` gives every portal step in order: resource group, plan, two web apps, configuration, zip deploy through Kudu, the access restriction, the first admin, adding members, backup, and cost.
- **Local proof first.** The `web` profile runs locally from the same zips through `startup.py` and `startup.js`, and is checked in Playwright.
- **Upgrade path.** The path to PostgreSQL and Container Apps Jobs stays in `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md`.

### M7. Desktop app

- **Shell.** `apps/desktop` is an Electron shell. It starts the bundled backend (PyInstaller one-folder) and the Next.js standalone server on loopback ports, in the `desktop` profile, with a local SQLite store under the user's app-data folder.
- **Installers.** `electron-builder` produces a DMG and zip on macOS and an MSI (WiX) on Windows. The Windows build runs on the CI `windows-latest` runner.
- **Signing.** Builds are unsigned until the owner supplies signing certificates. The guide says how users open an unsigned app.
- **Verification.** The packaged app is launched and driven by Playwright's Electron support for the harness stories.

### M8. Tests and evidence

- **User stories.** `docs/USER_STORIES.md` gets one story per page and feature: projects, repository, BA, QE, findings, feature builder, documents, governance and approvals, runs, observability, agents, skills, Skill Studio, MCP, plugins, settings, users, usage, harness, desktop and Azure.
- **Test layers.**
  - **Unit** per module.
  - **Integration** per API router on a real temporary store.
  - **E2E:** Playwright per story on the real model and real repositories.
- **HTML report.** `scripts/evidence_report.py` writes `report.html`: each story with its steps, its screenshots inline, pass or fail, and the run's model, commit and timings. Failures stay failures.
- **Real RAGAS.** `requirements-evals.txt` installs into the project `.venv`, and agent evals run on the real model and are stored as measurements.

### M9. Final proof

1. A full run on the web profile, the desktop app and the Azure proof of concept.
2. An Opus review.
3. The final HTML report.
4. The README and guides.

## 4. Order and parallel work

M1 then M2 come first and in that order, because everything after them edits the split files.

After M2, these touch separate files and run in parallel, one writer each:
- M3 (Skill Studio);
- M4 (harness);
- M5 (MCP and plugins).

M6 and M7 follow M4, because they need the profiles. M8 runs alongside every phase and closes in M9.

---

# Part 2 (revised 2026-11-11): harness first, zip deployment only

Status: **approved by the owner on 2026-11-11** ("yes"), with these additions:
- OpenTelemetry observability with a trace explorer (H9);
- a desktop release guide (H7);
- region eastus2;
- remove the fake skills and recreate them with similar requirements in Skill Studio, checking the result (H5).

The owner's direction:
- Focus on the harness, Skill Studio, agents, progressive discovery and full harness behaviour, compared with DeepSeek Harness.
- The harness must run the whole agentic-qe plugin.
- The QE Cycle UI is **on hold**.
- Azure is deployed **only by zip through Kudu**; GitHub cannot be connected to the Azure web app.

Part 1 is committed as `5a5e6df` on `feature/maf-harness-platform`.

## 1. Where the harness stands (live run on the real model, 2026-11-11)

9 of 13 stories pass (the first run of the day passed 4). Passing:
- planning with todos;
- repository scan with file and line;
- the tool audit;
- `run_tests` with exact counts;
- QE method skills;
- the honest no-repository answer;
- sub-agent delegation;
- the admin grants page;
- live status lines.

## 2. Root causes, from the run's own evidence

| Story | What the run shows | Root cause (first principles) |
|---|---|---|
| HS-02, HS-07 "start the BA / QE workflow" | The model called `find_tools`, loaded `project_status` or `run_tests`, read the same files again, and never called `start_workflow` | **The model can only use a tool it knows exists.** Discovery today is a keyword search the model must guess, so it never learned `start_workflow` exists, and the search ranked other tools first. Every turn also starts with `mode_get` and re-reads files already read, which spends the round budget |
| HS-10 "create a skill with your tool" | The model loaded the `skill-creator` *skill*, read its resources, and looked for scripts to scaffold files. It never saw the `create_skill` *tool* | **Two ways to do one job, and the visible one is wrong.** The skill-creator skill describes a scripts workflow the harness cannot run. The tool that works was hidden behind discovery |
| HS-06 `/agentic-qe:qe-start` | The model answered with a test run instead of the plugin's Gate 0 intake | **The harness has no plugin runtime.** The platform holds only the plugin's skills. The plugin's commands depend on its Node scripts, hooks (guards, ledger, approval phrases), validators and `.qe/` state, and the harness can neither run a command nor write files. No prompt fixes that |
| (all) | Repeated reads, `mode_get` each turn, long exploration before acting | **The harness instructions favour exploring over acting.** MAF's default harness instructions are generic, and ours add no rule for "do exactly what was asked, then verify" |

## 3. Harness against DeepSeek Harness (what is still missing)

| Capability | DeepSeek Harness | Ours now | Gap to close |
|---|---|---|---|
| Tool discovery | Every capability is a plugin row the model can see | Keyword `find_tools` | Deferred-tool index: every tool's name and one-line purpose in context, schemas loaded on demand (as Claude Code does) |
| Execution world | `ctx.fs` and `ctx.sandbox`: file tools and subprocesses share one workspace | Read-only repository tools; `run_tests` only | A workspace per project and thread: MAF file access tools (write needs approval) and MAF's shell executor (`agent_framework_tools.shell`), confined to the workspace, with argument lists, an allowlist, timeouts, `clean_env` and approval for every command |
| Plugins | Everything is a plugin, with profiles and bundles | Skills and commands from plugins; MCP servers; grants | Full plugin runtime: install the whole plugin, run its commands, hooks, scripts and agents |
| Hooks | `agent/*`, `tools/*` events | Audit and telemetry middleware only | Claude Code hook adapter on MAF middleware (PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop) |
| Sessions | Append-only log, fork at a turn, replay | Chat rows, MAF history file, durable snapshots | Fork a thread at a message; a replay check that every model-visible message is logged |
| Sub-agents | Agent teams with a shared task board | 5 specialists as MAF background agents | The plugin's 9 agents as background agents, and background tasks that survive the turn |
| Safety statement | `SAFETY.md` | CLAUDE.md rules | `SAFETY.md` for operators |

## 4. Phases

Each phase ends with:
- offline tests;
- the harness stories on the real model in the browser;
- evidence;
- `PROGRESS.md`.

Commits and pushes happen only when the owner says so.

### H1. Discovery that the model can actually use (fixes HS-02, HS-07, HS-10)
1. **Deferred-tool index.** The harness context lists every tool the user may load, with its name and one line saying what it does. Schemas still load only through `load_tools(names)`. `find_tools` stays for long catalogues such as many MCP servers.
2. **Clear tool descriptions:**
   - `start_workflow` names its workflows (ba: requirements document, qe: tests, bug_scan, change);
   - `create_skill` says it is the way to make a skill;
   - every description starts with when to use it.
3. **One way per job.** The `skill-creator` skill is for Skill Studio's own model calls. The harness's skill list leaves it out, and the harness prompt says to call `create_skill` to make a skill.
4. **Harness instructions:**
   - do what the user asked directly;
   - read a file once per turn unless it changed;
   - do not call `mode_get` unless the mode matters;
   - after acting, verify with a tool and report counts from the tool, not from memory.
5. **New measure.** A harness eval set (`evals/harness.json`) with these prompts and code-checked oracles, run on the real model; the score is stored.

### H2. An execution world for the harness (prerequisite for the plugin)
1. **A workspace** per project (a clone of the project repository, as `run_tests` already uses) and a scratch area per thread.
2. **MAF file access** (`file_access_store`) on that workspace:
   - read tools auto-approved;
   - write tools need an approval card;
   - every path through `safe_path`.
3. **MAF shell executor** (`agent_framework_tools.shell`; install the official package):
   - commands run with argument lists, no shell, in the workspace;
   - allowlist `node`, `npx`, `npm`, `python`, `pytest`, `git` (read-only verbs);
   - a timeout and `clean_env`;
   - an approval card for every command;
   - every command and its exit code are audited.
4. **Profiles.**
   - Desktop and local: all of the above.
   - Web (Azure): the same tools, but every shell or write run takes one of **5 platform-wide sandbox slots**, with a queue and its position shown. stdio MCP and plugin installs stay desktop or local only.

### H3. The whole agentic-qe plugin runs inside the harness (fixes HS-06; the main goal)
1. **Install the full plugin** from branch `agentic-qe-plugin` at pinned commit `8a7497b`: manifest, commands, skills, 9 agents, `hooks/`, `scripts/`, `validators/`. It replaces today's skills-only copy (decision D4).
2. **Claude Code hook adapter on MAF middleware.** The plugin's `hooks.json` runs:
   - PreToolUse and PostToolUse around the harness's write and shell tools, honouring block decisions;
   - UserPromptSubmit on every user message, so typed phrases such as `approve gate 0 for <app>` are recorded by the plugin's own `approval-hook.ts`;
   - SubagentStop when a plugin agent finishes.

   The hook JSON follows the Claude Code protocol. `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PROJECT_DIR` point at the plugin and the workspace.
3. **Plugin agents.** The 9 `agents/*.md` become MAF background agents with the tools their front matter allows. The read-only reviewers stay read-only.
4. **Commands end to end.** `/agentic-qe:qe-start` through `/agentic-qe:qe-sign` run in the harness. The plugin's `check-gate.ts` and `qe_validate.py` decide gate completeness. Gates advance only when the human types the phrase.
5. **Proof:** the full brownfield cycle on `personal-finance-mcp` through the harness, on the real model.
   - Each command, approval phrase, generated test, JUnit result and gate report is kept as evidence.
   - It is compared with the plugin's own worked example (`examples/brownfield-personal-finance-mcp`): requirements with `file:line`, scenarios per level, cases, executed tests, pass and fail counts, coverage-map gaps and defects.

### H4. Harness behaviour parity
1. **Sessions.** Fork a thread at any message, and a replay test that every model-visible message is in the log.
2. **Background tasks** that outlive the turn, with their status in the todo panel.
3. **`SAFETY.md`** for operators.
4. **The CLI** (`bin/harness`) runs the same plugin commands; one story covers it.

### H5. Skill Studio and agents, completed
1. **F-09 skills** that report PASSED without doing anything (owner, 2026-11-11):
   - remove all 5;
   - recreate each from a similar requirement in Skill Studio on the real model;
   - record whether the plan, files, checks, script tests and evaluation come out accurate, as evidence.
2. **Skill Studio.**
   - In the desktop and local profiles, script tests run in the H2 workspace.
   - The harness `create_skill` hands over to the Studio plan.
3. **Agents.**
   - Every agent's eval set runs on the real model, with scores stored with `n` and the judge.
   - Install `requirements-evals.txt` for real RAGAS metrics.
   - Agent pages show only measured numbers.

### H6. Environments, and Azure by zip deployment
1. **Two isolated environments:**
   - **Local** (`--env local`): SQLite and disk in `data/local/`, `.env.local`, all features.
   - **Azure:** settings in App Service only.
   - Templates in `deploy/environments/`.
   - `python scripts/dev.py env-check --env local|azure` lists what is missing.
2. **Azure on PostgreSQL and Blob:**
   - Azure Database for PostgreSQL Flexible Server, Burstable B1ms;
   - Blob Storage containers `documents`, `uploads`, `evidence`, `skills`, `workspaces`, `downloads`;
   - Key Vault references with managed identity;
   - no Redis.
   - Code: a database dialect layer chosen by `ATLAS_DATABASE_URL`, PostgreSQL migrations, and a storage layer for disk or Blob.
3. **Zip deployment only.**
   - `python scripts/package_azure_kudu.py` builds the two zips; `azure-local` proves them on this machine first.
   - The owner uploads them in Kudu `ZipDeployUI`.
   - GitHub Actions only builds, tests and attaches the zips and installers as artifacts. It never connects to Azure.
4. **Guide.** `docs/AZURE_POSTGRES_BLOB_PORTAL_GUIDE.md`, step by step in the portal:
   - resource group;
   - PostgreSQL (server, database, firewall for the web app's outbound IPs, SSL);
   - Storage account and containers;
   - Key Vault and managed identity role assignments;
   - the two web apps and their settings;
   - Kudu zip deploy;
   - verification, backup and restore, cost and teardown.

   It replaces the SQLite PoC guide.

### H7. Desktop installers and the login page
1. **Build.** CI builds the macOS DMG and the Windows MSI (with the PyInstaller backend) as artifacts. The DMG is also built and launched on this Mac.
2. **Publish.** The owner uploads them to the Blob `downloads` container with the `latest.json` that the build writes (version, SHA-256, size).
3. **Login page.** It shows the download links from `latest.json`, or says that no installer is published yet.
4. **Guide.** `docs/DESKTOP_RELEASE_GUIDE.md`, step by step:
   - run the CI build and download the artifacts;
   - check the SHA-256;
   - create the `downloads` container with public read access in the portal;
   - upload the DMG, the MSI and `latest.json`;
   - set `ATLAS_DOWNLOADS_URL` on the UI app;
   - verify the login page;
   - how users open an unsigned app on Windows and macOS;
   - updating to a new version.

### H9. Observability with OpenTelemetry and a trace explorer
1. **Traces.**
   - Turn on MAF's built-in OpenTelemetry instrumentation (`agent_framework.observability`), and add spans for API requests, tool calls, hooks, sandbox jobs and workflow stages.
   - Each span carries project, thread or run, user, agent, model, tokens, latency and status.
   - Inputs and outputs pass `redact()`, and secrets never appear.
2. **Where spans go.**
   - Always a local span store (a `spans` table through `backend.db`), so the explorer works without any cloud service.
   - Optionally an OTLP exporter (`OTEL_EXPORTER_OTLP_ENDPOINT`), for example Azure Monitor / Application Insights in eastus2, set only in the Azure environment.
3. **Trace explorer, like LangSmith.**
   - A list of runs (chat turns, workflow runs, Studio calls) with filters: project, user, agent, status, time.
   - One run opens as a tree and waterfall: agent, then model calls, tool calls, sub-agents and hooks. Each step shows inputs, outputs, tokens, duration and errors with stack id.
   - Search inside a run, and a link from every chat reply to its trace.
4. **Access.**
   - Admins see every trace and the application logs.
   - Members see only the traces of their own actions, enforced on the server through the deny-by-default route rules.
   - Log downloads stay admin only.
5. **Tests.**
   - A member cannot read another member's trace, by API or by UI.
   - Every harness tool call appears as a span with the same id as its `tool_calls` row.
   - No secret appears in a span.

### H8. Evidence
- All harness stories, the plugin cycle and the Skill Studio, MCP, CLI and desktop stories run on the real model.
- Everything goes into one `report.html` with screenshots, run on local and on the zip-deployed Azure app.

## 5. On hold
- **QE Cycle UI on the plugin.** Gate pages showing plugin artifacts; retiring the platform's own QE workflow. Resumes after H3 passes.
- **Entra ID sign-in, Container Apps Jobs, Front Door.**

## 6. Order
1. H1, then H2, then H3 (the main goal).
2. H4, H5 and H9 run beside H3 on separate files.
3. Then H6 and H7.
4. H8 closes.

## 7. Decisions for the owner

| # | Decision | Proposed |
|---|---|---|
| D1 | Harness on the web app with 5 sandbox slots (stdio MCP and plugin installs stay desktop or local only) | Yes |
| D3 | Azure region | **eastus2** (owner) |
| D4 | Replace `plugins/agentic-qe/` with the full plugin branch at `8a7497b` | Yes |
| D6 | F-09 skills | **Remove all 5 and recreate them in Skill Studio from similar requirements** (owner) |
| D7 | Public read access on the Blob `downloads` container only | Yes |
| D8 | Harness shell allowlist: `node`, `npx`, `npm`, `python`, `pytest`, `git` (read-only verbs), each command approved in chat | Yes |
| D9 | Install the official MAF tools package (`agent_framework_tools`) for the shell executor | Yes |

## Phase Q (added 2026-11-11): QE workflow correctness, chat approvals, joinable logs

Source: the owner's run of "Markdown-HTML-converter" (`prj_015c85df23f2`) and the evidence-backed trace in `docs/analysis/2026-11-11-markdown-html-converter-trace.md`. That document holds 18 bugs, each with its evidence and the test that catches it, and 15 log gaps. Bug ids below refer to it.

The QE Cycle **UI** stays on hold. These are backend correctness fixes: the harness starts the same QE workflow through `start_workflow`.

### Q1. QE workflow: never invent a subject, never call a stub a pass
Fixed in order of damage:
1. **B17. Empty-repository guard.** A QE run on a repository with no source files stops at Gate 0 with "no code to test" (a spec-first mode is offered separately). It never spends tokens inventing a contract. The run that started this spent 482k tokens.
2. **B6 and B7.**
   - A generated test that defines or stubs its own subject (the function under test) is refused in code.
   - A run whose only passes come from such tests, or from no real execution, is INCONCLUSIVE, never FAIL or PASS.
3. **B1 and B2.**
   - An Exception case is required only when the requirement states an error behaviour. The quota in `qe/model/quota.py` no longer forces one per P1 requirement.
   - The test-design prompt's contradictory rules are fixed.
   - Boundaries follow the requirement's input type, not only numbers.
4. **B3.** Each case's test data is checked against the requirement's stated input type (the BRD said string; the cases used `None`, `42` and a list), and every case must have an oracle.
5. **B4 and B5.**
   - Datasets are chosen from the requirement's input type, not by keyword. The word "negative" in a title chose `boundary.number`.
   - A generic payload is used only when the type matches.
   - The fixture key is named, so the `KeyError` is gone.
6. **B14, B15, B16, B18.**
   - A rejection or "approve with gaps" needs a real reason (a minimum length and wording check; one letter was accepted).
   - G3 to G5 approve the documents they cover.
   - The stale skill text is fixed.
   - Event `data` is redacted like `message`.

### Q2. Approvals in the harness chat, and chat history
- **B11.** Every tool approval or rejection in the chat is recorded: who, when, which tool and arguments (redacted), in the ledger and as a span.
- **B12.** When the harness starts a workflow, the chat shows its gate status and a link to approve on the Governance page. A gate waiting for a human appears in the chat, not only on the project page.
- **B10 and B13.**
  - A resume after an approval does not store the user's message again.
  - MAF's stored history does not replay old user turns as new ones.
  - The harness never says "the plan was approved" when it was not: it reads the plan's real status.
- **B9.** The approver shown everywhere comes from the stored `decided_by` (name, role and email since 2026-11-11), never from redacted event text.

### Q3. Logs that can be joined (gaps G1 to G15)
- Every model call is stored with its input and output (redacted, size-capped), linked to run, stage, thread, document and span (G1, G2).
- Every app and error log line carries `request_id`, `run_id`, `trace_id` (G3).
- The chat trace links to the workflow trace it starts, and gate resumes join the run's trace (G4, G5).
- The tool-approval lifecycle is logged (G6).
- Actors show their name, never `***` (G7, done for new rows with the masking fix).
- There is a span per model call with the right agent (G8, G9).
- Progress events during long model calls, and gate wait time recorded (G10, G12).
- Failed tests reach `run_failures` (G11).
- `run_events.data` is redacted (G13).
- MAF "Dropping client-supplied message" warnings are filtered (G14).
- Manual gate decisions keep their reason and context (G15).

### Q4. Proof
- **Rerun the owner's scenario on the real model:**
  - the same empty repository must stop at Gate 0;
  - a real Markdown-to-HTML repository must produce cases whose data matches string input, with no Exception case the BRD does not ask for, and no stubbed subjects;
  - the verdict must be computed from real executions.
- **Rerun the harness stories,** with the chat approval card checked in the browser.

**Order.**
1. Q1 now: QE workflow files only.
2. Q2 and Q3 after H2 and H3 land, because they share the harness and runtime files.
3. Q4 closes.

## Phase R (added 2026-11-11): capability registry the harness consults on every run

Owner request:
- one table of every tool, agent, skill, command and workflow, with what is nested in what and how they connect;
- the harness refers to it on every execution, so its discovery is accurate.

### What exists today (counted from code on 2026-11-11)
- **Platform tools:** 19, one per file in `maf/tools/`. MAF harness built-ins on top: todos, modes, file memory, `load_skill`, `read_skill_resource`, background agents; file access and shell from H2.
- **Agents:** 15 governed agents (`maf/agents/*`, each with a policy listing chat tools, workflow tools and skills). Plus 9 agentic-qe plugin agents (`plugins/agentic-qe/agents/*.md`).
- **Skills and commands:** 45 entries in the "/" menu: 30 skills and 15 plugin commands.
- **Workflows:** 4 (`ba`, `qe`, `bug_scan`, `change`). Their stages and agents live in code; for example `qe`: discover → repo-intelligence-analyst, requirements → requirements-analyst, plan → principal-test-architect, design → test-design-architect, generate → test-automation-engineer, execute → qa-execution-engineer, heal → defect-diagnostician, sign → confidence-reviewer.
- **MCP:** servers, and their tools listed by real `list_tools`, with grants per role.
- **Plugins:** manifests, hooks, scripts, agents.

### First principles
1. The model can only use what it can see. It can only choose well when it also sees how things connect: this command uses that skill and runs that script; this workflow's stage is done by that agent.
2. The registry is **derived from code and manifests by a sync, never typed by hand**, so it cannot drift. A capability that cannot be read from a source is not in the registry.
3. **Visibility is applied when it is read,** per user: role, plugin grants, MCP grants, profile, enabled state. The table holds everything; each user sees only what they may use.

### Data model (migration after the highest existing number)
- **`capabilities`:**
  - `id`; `kind` (tool | agent | skill | command | workflow | stage | plugin | mcp_server | mcp_tool | hook | script);
  - `name`, `qualified_name` (for example `agentic-qe:qe-plan`), `description`, `when_to_use`;
  - `source` (file path or plugin), `sha256` of its source;
  - `risk`, `needs_approval`, `profiles` (web / local / desktop), `enabled`, `updated_at`.
- **`capability_links`:**
  - `from_id`, `to_id`, `relation`, `detail`. Relations:
    - `contains` (plugin → skill / command / agent / hook / script; workflow → stage);
    - `performed_by` (stage → agent);
    - `uses_tool` (agent → tool);
    - `applies_skill` (agent → skill);
    - `runs_script` (command or skill → script);
    - `delegates_to` (harness → background agent);
    - `serves` (mcp_server → mcp_tool);
    - `gates` (stage → gate).
- **`registry_versions`:** one row per sync, with the hash of all rows, so a change is visible and the harness cache knows when to refresh.

### Sync (`core/registry/`)
- **Sources:**
  - tool objects (name, description, approval mode);
  - agent policies;
  - workflow stage modules, read with Python's `ast`: each stage module's `AgentCall` agent keys, no execution;
  - plugin manifests, skills' frontmatter, command skills;
  - script paths named in SKILL.md;
  - `hooks.json`;
  - plugin `agents/*.md` frontmatter;
  - the MCP registry.
- **When it runs:** at startup, and after a plugin install, enable or disable, a skill publish or delete, an MCP connect, or a grant change.
- It is deterministic, with no model call.

### Harness use on every execution
1. **Before the run,** a MAF context provider reads the user's visible slice of the registry, cached by registry version.
2. **It injects a compact index:** every capability by qualified name, with one-line purpose and kind, grouped by kind. It adds the links that matter for choosing: for each command its skills and scripts; for each workflow its stages and agents; for each background agent its skills.
3. **Two tools replace keyword `find_tools`:**
   - `find_capability(query)`: ranked by BM25 over name, description and linked names, using the standard library only;
   - `describe_capability(name)`: the full entry with its links up and down.

   `load_tools` keeps loading tool schemas.
4. **Each tool call, skill load, command and delegation** records the capability id on its `tool_calls` row and span. The trace explorer then shows which registry entry was used, and gaps can be measured, for example a capability never chosen when it should have been.
5. **The harness eval set** (H1) measures discovery accuracy on the real model: for each prompt, the expected capability is chosen.

### UI
- **`/capabilities`:**
  - a table with kind, name, description, source, risk, approval and visibility for me;
  - filters and search;
  - a nested tree view (plugin → commands → skills → scripts; workflow → stages → agents → tools and skills).
- Admins see everything. Members see their visible slice.

### Order
1. The registry core, sync, API, UI and tests: now, in files no other writer touches.
2. Harness wiring (context provider and the two tools): after H2 and H3 land.
3. The discovery accuracy measure on the real model closes it.

# Part 3 (owner goal, 2026-11-11): an accurate harness end to end, PostgreSQL only, Azure standard

**Owner goal.** The harness acts like Claude Code in real time. It develops a working application end to end, and it runs the whole agentic-qe cycle on a real repository. Every feature has evidence: skills, subagents, Skill Studio, the UI.

The deployment standard becomes **PostgreSQL plus Blob Storage in East US 2**. SQLite is removed now, so there is no migration later. Work goes in the order below. The harness comes first.

## G1. Harness accuracy on plugin commands (in progress)
- **Root cause of the stop at Gate 1:** `plan.md`, "Plugin command focus".
- **Done when:** a live `/agentic-qe:qe-start` … `qe-sign` cycle on `personal-finance-mcp` gets Gates 0 to 5 recorded by the plugin itself, each gate's documents are on disk and pass the plugin's validators, and the evidence is in `docs/evidence/runs/<date>-harness-plugin/`.
- **Also:** rerun the 13 harness stories and the status-line test on the real model, and produce one HTML evidence report.

## G2. The harness builds an application end to end
- **Story:** from a short requirement, in an empty repository, the harness plans with todos, writes the code and tests in the workspace (each write approved), runs the tests with the shell, fixes failures, and commits on a work branch. The run has to finish with green tests that the harness ran.
- **Evidence:** a live browser run with screenshots and the transcript.
- **Done when:** the generated app's tests pass when run again outside the harness.

## G3. Skills and subagents from the harness
- **Skills:** `create_skill` exists.
- **Subagents:** a harness tool creates a project subagent as a plugin-style `agents/<name>.md`, with read-only tools unless approved. It is registered in the capability registry and usable at once as a MAF background agent.
- **Proof:** both are made from chat and used in the same thread.

## G4. Skill Studio requirements page (BRD style, task based)
- The plan step becomes an editable document page, like the BRD page. Its sections:
  - purpose;
  - input contract;
  - outputs;
  - tasks, as a checklist with an owner (skill, script or subagent);
  - subagents;
  - formats;
  - eval cases with their assertions.
- Every edit is a new version (SHA-256, author). Approval hashes the edited version. Generation reads only the approved version.
- The page shows the risk of negative assertions before approval (from the H5 findings).

## G5. PostgreSQL only (SQLite removed)
- **Database layer:** `backend/db` moves to psycopg 3 (`psycopg[binary]`), one connection pool, and `ATLAS_DATABASE_URL` required everywhere. A missing or unreachable database is a clear startup error.
- **SQL changes:**
  - `?` becomes `%s`;
  - `INSERT OR IGNORE` and `INSERT OR REPLACE` become `ON CONFLICT`;
  - `BEGIN IMMEDIATE` becomes row locks (`SELECT … FOR UPDATE`) or advisory locks;
  - `sqlite_master` becomes `information_schema`;
  - JSON and time columns are checked one by one.
- **Migrations:** the `.sql` files are converted to PostgreSQL. A fresh database is built from them, and a test proves every table exists.
- **The ledger:** the hash chain is kept, and appends are serialised with an advisory lock.
- **Data move:** `scripts/sqlite_to_postgres.py` copies an existing store once, then re-verifies the ledger chain and the document SHA-256 values. It is the only code that still reads SQLite, and it is removed after the owner moves the data.
- **Tests:** each test session creates and drops its own database. CI installs PostgreSQL on Ubuntu, macOS and Windows.
- **Local:** PostgreSQL 16 from the official installer, Homebrew or Docker. `scripts/dev.py setup` checks for it and says how to get it.
- **Desktop (owner decision D-P1):** the default is a bundled PostgreSQL (the `embedded-postgres` binaries) started by the Electron main process on a free local port, with data in the user's app folder.
- **Removal:** the SQLite code and `ATLAS_SQLITE_JOURNAL` are removed. The exact files are listed for the owner's yes before deletion.

## G6. Blob Storage for files
- **What moves:** documents, uploads, evidence, published skills and installers move to Blob containers through one storage module.
- **Credentials:** a managed identity on Azure; local folders when `ATLAS_STORAGE_URL` is not set.
- **What stays:** workspaces and git clones stay on the instance's disk, because git needs a real filesystem. They are rebuilt from the repository when missing.

## G7. Key Vault for secrets
- **On Azure,** when `ATLAS_KEY_VAULT_URL` is set, the backend reads `atlas-admin-password`, `atlas-secret-key` and `atlas-database-url` from Key Vault. It authenticates with the App Service managed identity through the platform token endpoint, using `httpx` (already installed); no new SDK is added.
- **Locally,** `.env` stays. A secret is never logged, and never put in argv or a URL.
- **Tests** cover the token and secret requests against a local fake HTTP server.

## G8. Desktop installers in GitHub CI
- **On push** to `feature/maf-harness-platform`, `desktop.yml` builds the macOS DMG (arm64 and x64) and the Windows MSI and uploads them as workflow artifacts with `latest-<os>.json`.
- **On a `v*` tag,** it also creates a GitHub Release with the installers and the SHA-256 values.
- Code signing waits for the owner's certificates (unsigned builds are labelled so).

## G9. Azure standard guide (East US 2)
- **What it covers:** `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md` becomes the one standard: App Service plan B1 (two apps), PostgreSQL Flexible Server Burstable B1ms with 32 GiB, Blob Storage (Standard LRS, Hot), Key Vault Standard, and optional Application Insights.
- **Format:** every portal step, settings from Key Vault, zip deployment only, and a monthly cost table from the Azure pricing calculator for East US 2, with the date the prices were read.

## Order
1. G1.
2. G5 and G6, together, because the storage layer and the database layer both touch every module.
3. G7.
4. G8.
5. G4.
6. G2 and G3.
7. G9, kept current as each item lands.

After each item: the offline suite, the gates, lint, a browser check, and evidence. Commit only on the owner's word.
