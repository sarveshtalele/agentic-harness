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
