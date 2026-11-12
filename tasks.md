# Tasks

`[x]` means done and checked by the test named in `docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md`. `[ ]` means not done or not verified.

## Foundation

- [x] Real `agent-framework` packages replace the hand-written engine
- [x] SQLite with numbered migrations (`src/backend/migrations`)
- [x] Encrypted secrets, redaction, path confinement, origin and host guard
- [x] Hash-chained ledger and signed gates
- [x] Versioned documents and prompts
- [x] Cross-platform launcher (`scripts/dev.py`)
- [x] Activity hook writing `progress.md`
- [x] `CLAUDE.md` guardrails including no deletion without permission
- [x] Previous code preserved in Git at commit 09f14fe

## Backend features

- [x] Git clone with `owner/repo`, ZIP upload, local folder import, re-sync
- [x] Private GitHub token: validate, encrypt, list repositories
- [x] Repository analysis from disk
- [x] Static scanners: ruff, secrets, JS rules, manifests
- [x] Workflows: `ba`, `qe`, `bug_scan`, `change`
- [x] Agent review with quote verification
- [x] Worktree branches, real test runs, retry, diff approval
- [x] Plugin rules: case multiplicity, one case per file, placeholder refusal, RED baseline, CSV and Jira export
- [x] Templates: built-in and upload
- [x] Source extraction: md, txt, pdf, docx, xlsx, pptx
- [x] Export: md, docx, feature, patch, csv, jira, changed-files ZIP
- [x] Document review and refine on demand
- [x] AG-UI chat with threads and memory
- [x] Agent evals through MAF
- [ ] Push, pull request, and merge against a real private repository. Code exists; it needs your token to verify

## UI

- [x] Projects page and inside-project routes
- [x] Overview, Repository, BA Studio, Documents, Feature Builder, Bug Scan, QE Studio, Governance, Runs & Metrics, Prompts, Copilot
- [x] Settings and Templates
- [x] Chat in a separate window

## Testing

- [x] Unit tests (`tests/test_core.py`)
- [x] Integration tests with real FastAPI, SQLite, git, pytest, and MAF (`tests/test_api_workflows.py`)
- [x] Playwright E2E on real model and browser with screenshots: 32 of 32
- [x] Windows, macOS, and Linux: offline tests and UI build run in CI

## Open items from the owner

- [x] Verify by eye: home page, Agents, live QE view, feature review, observability
- [x] Every feature tested on `personal-finance-mcp`, adding a new tool: 8 of 8 E2E tests pass
- [x] Complete screenshot evidence in `docs/evidence`
- [x] Lint clean: noise came from the `.next-run` build folder, which is now ignored
- [ ] Private repos: logic has offline tests with a stubbed GitHub API. A live check of connect, clone, pull request, and merge needs the owner's token
- [ ] A real Windows double-click of `start-windows.bat`. CI runs the code paths but not the launcher itself
- [x] Reviewer stricter, with deterministic checks (`core/doc_checks.py`)
- [x] Guardrails, evals, and governance for every agent (`maf/governance.py`, `maf/evals.py`, `evals/`)
- [x] Agent observability in the UI (`/agents`)
- [x] Refresh `tasks.md`, `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`, and other docs from final code
- [ ] `/advisor`: not available in this environment. Nothing to build

## Modular architecture and Azure

- [x] Split API routers, agents, tools, workflows into their own files
- [x] Model call limit and cut-off reply guard
- [x] Clean UI pass from screenshots: fixed the undefined result line and page overflow from long diffs
- [x] `docs/SYSTEM_DESIGN.md`, `docs/AZURE_DEPLOY.md` with INR prices
- [x] `scripts/package_azure.py`, backend and frontend startup scripts, run locally from the unpacked ZIPs
- [x] Clean production export: `python scripts/package_azure.py --repo`
- [ ] Deploy on real Azure. Needs your subscription

## Rename, observability, launchers

- [x] Rename to Agentic QE Platform. `ATLAS_` settings and the database file keep their names so existing data still works
- [x] Observability across projects, per project, and per run
- [x] `start-mac.command` run on macOS. `start-windows.bat` written; a real Windows double-click is not yet checked
- [x] Commit and push `feat/real-maf-platform`

## Sandbox, navigation, docs site

- [x] Full clones, complete scan with coverage, Fix all
- [x] Repository page shows the connected repository and sandbox first
- [x] Remove gate ribbon; link every card to its tab
- [x] Rebuild Documentation as a docs site
- [x] `README.md` and `docs/PROJECT_STRUCTURE.md`
- [x] Every feature passes on `personal-finance-mcp`: 10 of 10 E2E tests

## Document editor

- [x] In-place editing, table grids, images, live preview
- [x] BA Studio links to current and recent documents

## Accounts, accuracy, live views

- [x] Admin login, users, allocations, owner-scoped data
- [x] Confidence review at every gate; reliable JSON handling
- [x] Discovery structure and checks
- [x] Live run log, document cards, agent cards and pages
- [x] `docs/AZURE_SYSTEM_DESIGN.md`, including multi-user sandboxes (design only)
- [ ] Build the design: PostgreSQL, Blob Storage, Key Vault, sandbox jobs

## Integrity fixes (Phase 1, done 2026-11-01)

- [x] The signer is the signed-in account id, never a typed name; `by` and `author` removed from request models
- [x] Fix all marks findings `fix_attempted`, not `fixed`, unless the verdict is PASS or NO NEW FAILURES; still open for the next Fix all
- [x] Saving a test case table rebuilds the stored cases from it, validated; an invalid table is refused with a 400

## Next, after your approval

- [ ] Consolidated in `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`: 15 phases, approved 2026-11-01. Phases 1 to 6 done, phase 7 next
- [x] Phase 1, agent names: agents use the plugin's hyphenated keys; `doc_reviewer` merged into `confidence-reviewer` and `gherkin_author` into `business-analyst`; migration `006_agent_plugin_names.sql` moves stored history (checked by `test_migration_006_*`)
- [ ] Phase 1, agent names: live evals of the merged prompts on the real model not yet run
- [ ] Phase 1, `qa-execution-engineer` arrives with phase 5

## Phase 2: errors, recovery, and debugging (ERR)

- [x] `core/errors.py` typed errors; `run_failures` table (migration 007) with the rejected reply saved under the run
- [x] JSON parsing never accepts a fragment; length, JSON, and schema failures have separate codes
- [x] `POST /api/runs/{id}/retry`; design and generate keep finished batches; partial result marked and not approvable
- [x] API error shape and `X-Request-Id`; run error card; `error.tsx` and `global-error.tsx`
- [x] No-cache control on model calls, checked against the real proxy
- [x] Broad `except` audit
- [x] Observability Errors tab, error code docs page (rest of Part 4 and 5)
- [x] Settings: admin-only application log download by day (OPS-4 link)
- [ ] Failure inside a gate approval handler cannot be retried safely yet
- [ ] Live run on a real repository to see a real partial result

## Phase 2, second half (OPS)

- [x] OPS-1 Observability paged and filtered in SQL, migration 008, Load more
- [x] OPS-2 One active run per project and workflow kind (409, atomic claim)
- [x] OPS-3, OPS-4 Daily JSONL app log, retention, admin download
- [x] OPS-5 Deleting a project removes its `data/runs/<id>/` folders
- [x] OPS-6 Model-free browser smoke test in CI (`python scripts/dev.py smoke`; first CI run on all three systems not seen yet)

## Awaiting your decision

- [ ] Rotate the model API key, which is in old Git history on `origin/main`
- [ ] Rewrite Git history to remove that key, if wanted
- [ ] Migrate old `data/sdlc.sqlite3` projects
- [x] A change review cannot show above 60 beside a failing test verdict; discovery accepts paths the repository itself mentions
- [x] A generated test file that cannot import no longer stops the other tests from running

## Phase 3a: models, allowed models, and limits (MDL), 2026-11-01

- [x] specs.md MDL-1 to MDL-5
- [x] Migration 009: `models`, `user_models`, `user_limits`, `agent_calls.model/user_id`, `agent_settings.model`, `runs.user_id/model`, `chat_threads.model`
- [x] `core/models.py`, `auth.check_allowance` / `auth.model_for`, `llm.test_connection` per model, `AQE-ALLOW-002`
- [x] Limit during a run: batch code re-raises it instead of splitting or swallowing it
- [x] Model, time zone, and usage endpoints in `api/settings.py`; users API in `api/auth.py`
- [x] UI: Users, Settings models, model picker on run forms and chat, header tokens, usage page
- [x] Tests (ScriptedClient)
- [x] Real two-model run through the proxy (`deepseek-v4-flash-global`, `kimi-k2.6`): each `agent_calls` row holds its model
- [ ] Not verified: Windows `tzdata`, the browser UI, e2e
- [ ] Next task, not built: roles and project members

## Phase 3b: roles, gate signing, members, account page (ROL), 2026-11-01

- [x] specs.md ROL-1 to ROL-8
- [x] Migration 010 (`users.role`, `sessions.last_seen`, `project_members`)
- [x] `core/auth.py`: roles, rules, members, gate signers, password change, idle timeout
- [x] API: members, transfer, gate roles, account password; role on users; project `my_role`, `can_sign`
- [x] Observability SQL includes member projects
- [x] UI (type-checked only): Account page, role select, gate roles, Members card, Approve hidden when not allowed
- [x] Tests: `tests/test_access.py`
- [ ] Not verified: browser UI, e2e
- [ ] Cost in rupees per user, deferred until the proxy reports cost per call
- [x] Agents page chooses a model per agent, and saving other controls keeps it

## Phase 4: plugin skills on MAF (PLG), 2026-11-02

- [x] specs.md PLG-1 to PLG-11, `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md` updated first
- [x] `core/skills.py`, `skills` field on every policy, `ATLAS_SKILLS_DIR`
- [x] `AgentCall` skill injection, `skill` events, `agent_calls.skills`, `prompt_ref` with skill hash (migration 011)
- [x] Chat skill pick (one call per user message) and `SkillsProvider` on models that pass the tool check
- [x] `llm.tool_check`, `models` columns, **Check tools** button, chat warning, health
- [x] Skill evals joined to agent evals (code checks only), Skills API and page, navigation
- [x] `scripts/package_azure.py` includes `skills/`
- [x] Tests: `tests/test_skills.py`
- [x] Real tool check on `deepseek-v4-flash-global`, `kimi-k2.6`, `claude-sonnet-4-5`: all three failed. The proxy shows the model only a `read_file` tool, not the one offered
- [ ] Not verified: e2e, a live workflow run with skills (the model SDK could not reach the proxy from the sandbox; token cost was measured with raw HTTP), the browser UI
- [ ] 28 of 33 plugin eval cases need a grader (phase 6)
- [ ] `qa-execution-engineer` and Skill Studio are later phases; `executing-tests` and `building-qe-dashboard` have no agent yet

## Phase 5a: per-case confidence and gate reopening (CNF), 2026-11-02

- [x] specs.md CNF-1 to CNF-12 written first
- [x] `qe/confidence.py`: rubric, verdict by code, citation checks through `safe_path`, low confidence, post-execution cap
- [x] `maf/workflows/shared.py` and `qe.py`: per-case review in batches of 8, send-back of REJECT cases alone (one round), NOT RUN on a failed batch, token report
- [x] `engine.decide`: a gate with a REJECT record needs a reason, written to the ledger
- [x] `core/gates.py`, `core/documents.py`, API: editing an approved document reopens its gate and the later ones; `reopened` and `would_reopen`
- [x] Prompts: requirements rules; reviewer sections for cases, tests and plan; eval fixes
- [x] UI (type-checked only): per-case table in the approval card, reason field, reopen warning on the document page
- [x] `scripts/gen_structure.py` describes `skills/` files
- [ ] Not verified: a live run on the real model, the browser UI, e2e (the owner runs these)
- [ ] Not built, on purpose, next: test signature checks, setup step, data stage, defect records, case limits

## Phase 5b: test checks, setup, data, defects, limits, execution agent (TST), 2026-11-02

- [x] specs.md TST-1 to TST-14 written first
- [x] `qe/emit.py`: import, signature, and third-party checks with `ast`; signatures for the prompt; send-back alone, one round
- [x] `qe/execution.py`: sandbox inventory, `environment_facts`, `environment_notes`, `HEALING_PATTERNS`, new `classify_failure`, pytest extra arguments
- [x] `workflows/qe.py`: stage `prepare` (install moved here), stage `data` carrying Gate 3, defect records, heal guard, case limit, token estimate, execution summary
- [x] `qe/test_data.py`: port of `synthesize-data.ts`
- [x] Agent `qa-execution-engineer`: policy, prompt, evals, mapping; 12 agents; `tests/e2e/test_app.py` count 11 to 12
- [x] Tests with ScriptedClient and real small modules in `tests/test_emit.py` and `tests/test_execution_stages.py`
- [ ] Not verified: a live run on the finance repository (the owner runs it), e2e, the browser UI
- [ ] Not built, on purpose: starting the app for tests that need a server (phase 7)

## Phase 5c: token budget (TST-12, TST-15 to TST-17), 2026-11-02

- [x] specs.md TST-12 rewritten, TST-15 to TST-17 added first
- [x] `model.case_quota`, quota in the design prompt, excess dropped before review, gap revision obeys it; `limit_cases` kept as a final check
- [x] Review evidence per batch capped at 12,000 characters (design and generated tests)
- [x] Review batch split-retry; reviewer id matching
- [x] Token limit re-checked inside the model gate; Gate token line
- [x] e2e `approve_next` fills `reject-reason` when visible
- [x] Tests in `tests/test_token_budget.py`
- [ ] Not verified: a live run on the finance repository, e2e, the browser UI
- [x] `tracing-coverage #2` eval: the case now names its review type, and passes on the real model
- [ ] Feature Builder sometimes ends with a failing test verdict on the finance repository (`test_f4`). Phase 7 gives it the whole repository

## Phase 6: evaluation metrics (EVL), 2026-11-02

- [x] specs.md EVL-1 to EVL-10, tasks.md, `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md` written first
- [x] `git mv maf/evals.py maf/evals/__init__.py` (approved)
- [x] `maf/evals/metrics.py`, `store.py`, `grader.py`, `ragas_evaluator.py`; migration 012; `requirements-evals.txt`; CI job `evals-install` (allowed to fail)
- [x] Benchmarks `shop` (repo, labels, 4 case files) and `finance` (labels only); labels marked `reviewed: false`
- [x] Case format (`context`, `context_files`, `reference`, `metrics`, `key`, `mutation`); API `/api/evals/cards`, `/api/agents/{agent}/metrics`, `/api/prompts/{agent}/scores`; live groundedness in `AgentCall.text`
- [x] Cards, agent page scores, prompts page scores (type-checked and linted only)
- [x] `docs/EVALUATIONS.md` and the docs page `evaluations`
- [x] `tracing-coverage #2` investigated: flaky (3 of 6 replies contain NOT_RUN) because the confidence-reviewer is asked a review-less question; no code change
- [x] Real numbers on `shop` for bug-reviewer, requirements-analyst, business-analyst (see the phase report)
- [ ] Not verified: the browser UI, the Windows install of requirements-evals.txt (CI job reports it), e2e
- [ ] Not done: labels reviewed by a person; `finance` cases run on the pinned commit; trend line on cards; Skill Studio agents; skill evals started by a user (no such feature yet)
- [x] Reviews stop first when tokens run low, cases a batch leaves out get one more try, and the default case limit is 40

## MAF harness rebuild (plan: `docs/HARNESS_REBUILD_PLAN.md`), awaiting approval

- [x] Audit: 23 fabricated-data and weak-handling items mapped (D-01 to D-23); harness mapping table; baseline 585 offline tests pass
- [x] Owner approved implementation on 2026-11-10 ("start Implementation"); open decisions keep their defaults (plan Section 10)
- [x] Playwright MCP added (`claude mcp add playwright npx @playwright/mcp@latest`, local scope, connected); Playwright 1.64.1 and Chromium already installed
- [x] Testing strategy and evidence report design (plan 8e); `scripts/evidence_report.py`, `python scripts/dev.py evidence`
- [x] P0 Branch `feature/maf-harness-platform`; architecture doc status correction (Section 9)
- [x] P1 Stop fabricated data (2026-11-10): D-01..D-05, D-10..D-12, D-15, D-19, D-22, plus review findings. Harness tools no longer approve gates or documents or mark session gates approved; `run_quality_lifecycle` and `decide_approval` unregistered; startup seeding removed from `app.py`, `cli.py`, `run.sh`, `run.bat`; security audit scans the real repo (`NotScanned` when none); MCP file tools confined to a real, visible project via `safe_path`, other canned MCP results now 501; `evals/store.py` no longer invents "measured" scores; log mask keeps uvicorn access lines working. Evidence: `docs/evidence/runs/2026-11-10-1213-8477250-dirty/`
- [x] CI gate 1 (`tests/test_no_fabrication.py`, ratchet 76 cases / 18 files) and gate 4 (`tests/test_agents_approve_nothing.py`, static + behavioural)
- [ ] P1 left for later phases: canned plan, design, generate, confidence, heal, stories and gherkin tool output (D-06..D-09, P2); `doc_handler` invented thought text (P2); `skill_dispatcher.py` sample paths (P2); session gates shown from `gates.status` (P2); D-24..D-29 wording (P3c); smoke and E2E not run here (port binding blocked)
- [ ] Owner decision: `feature/maf-harness-platform` was cut from `feature/azure-kudu-deployment`, which `scripts/verify_branch_isolation.sh` says must not be merged elsewhere. Rebase onto `main` before any PR?
- [x] P2 `maf/harness.py` factory on `create_harness_agent`, done 2026-11-10. Evidence in `docs/evidence/runs/2026-11-10-1237-f4710dc-dirty/`: 597 offline, live real-model pass, real UI chat. Scope:
  - new `harness` agent (`maf/agents/harness.py`, `prompts/harness.md`, `evals/harness.json`) served by the existing `/agui/{agent}` route and Chat UI
  - same governance, model allowance, deny-by-default tools, `tool_audit`, telemetry, and `ProjectContext` as other agents
  - MAF todos (file store per thread), plan/execute modes, file memory per user and project, and skills with progressive disclosure from `skills/`; `run_skill_script` always needs approval
  - per-call history stored under `data/harness/history` ("model-visible means logged"); sliding-window compaction like the other agents
  - legacy `/api/harness/chat` unchanged; `HarnessView` switches engines in P7 (`ATLAS_HARNESS_ENGINE` arrives with that switch)
  - deferred: background agents (experimental in MAF 1.24) and `agents/*.md` adapter go to P3b, MCP to P4, admin skill filter to P5
- [x] Found while running P2 and fixed: telemetry missed streamed harness calls (`governance.telemetry` uses `with_result_hook`); CopilotKit route's hardcoded agent list crashed `harness` and `bug-fix-reviewer` chats (now read from `/api/chat/agents`); eval check keys guarded (`tests/test_eval_check_keys.py`)
- [x] Full test pass 2026-11-10 (owner: "test everything accurately"):
  - smoke 3/3 via Browser-pane launch (the sandbox blocks the Turbopack build from opening a port, the pane does not)
  - E2E real model: run 1 2/33 and run 2 18/33; regressions from earlier commits fixed (project create did not open the project, `364e868`; in-project chat redirected to the legacy harness, `0a80268`); drifted selectors updated for the owner's redesign (rename modal, BA button label, finding cards, QE install checkbox, next-step banner); `ConfirmModal` given `role="dialog"`
  - Azure Kudu package: `config.ROOT` found no prompts or skills inside the package (fixed, `tests/test_azure_package_runs.py`); WAL replaced by DELETE on the `/home` share in every Azure path; setup scripts now set `ATLAS_ALLOWED_HOSTS`, `ATLAS_ALLOWED_ORIGINS` and prompt for the admin; packager ships git-tracked files only; guide corrected (WAL, PostgreSQL claim, Linux drag-and-drop)
  - `.env` login works on a backend started from `.env`; the Browser-pane preview servers use their own throwaway admin from `.claude/launch.json`
  - E2E run 3 20/33. Found and fixed a real QE defect: the runner came from the model's free-text framework label, a model wrote "python", nothing ran and the verdict was INCONCLUSIVE. Code now picks the runner (`qe/execution.pick_runner`, `tests/test_pick_runner.py`)
  - Packaged UI (`startup.js`) left Turbopack's external-package symlinks pointing into the deleted build folder, so `/api/copilotkit` failed with "Cannot find module 'pino-<hash>'"; links are now replaced by real copies. Deployed-style run of both zips through the real `startup.py` and `startup.js`: 28 pages HTTP 200, 0 console errors, harness chat reaches MAF
  - Chat now ends a turn with `AQE-MODEL-TOOL-TEXT` when the model writes its tool call as text (E2E run 4, `test_13`), instead of showing and storing the markup
  - Final evidence `docs/evidence/runs/2026-11-10-1747-c6a8cfd-dirty/`: offline 606/606, smoke 3/3, live harness 1/1, E2E run 4 32/33 and run 5 30/33. The run 5 failures are traced in NOTES.md: model endpoint outage during design, Feature Builder change failing the repo tests (verdict FAIL is correct), QE tokens 699k over the 600k budget
- [ ] E2E stability on the real model: `test_11` timing, `test_f4` Feature Builder quality, `test_f8` token budget vary between runs
- [x] Harness page on MAF (P7 pulled forward, owner 2026-11-10 "start with both"):
  - `/harness` renders the MAF Chat with the `harness` agent and a panel of the thread's real MAF todos; the legacy view stays at `/harness?engine=legacy`
  - new harness tools: `run_tests` (registered runner chosen by code, run through `qe/execution.run_suite` in the project sandbox clone, verdict from JUnit), `scan_repository` (`static_analysis.run_all`, read-only), `sandbox_status` (`sandbox.info`); refused when the project has no real repository; arbitrary shell stays off
- [x] P3 first slice: plugin discovery (with the harness page, same day). Real repo: `local-skills` 20 skills, `agentic-qe` 15 commands (no manifest), `security-audit` 0 skills (its `SKILL.md` is at the folder root, no `skills/`). Left for P3: write routes, marketplace sidecar validation, undoable registration, hook/agent/command adapters (P3b): `core/plugins.py` discovers `plugins/*/plugin.json` and Claude-format `.claude-plugin/plugin.json`, plus `skills/` as the implicit `local-skills` plugin; `GET /api/plugins`; harness skills come from discovered plugins, with command skills (`disable-model-invocation: true`) kept out of the model's list
- [x] Harness user stories written and run live (`docs/HARNESS_USER_STORIES.md`): 8 pass, 1 partial, 1 fail (evaluator invents scores), 4 not built. Studio fixes: keyword fallbacks removed in API and UI (D-18), generated scripts report NOT_IMPLEMENTED
- [x] Evaluator reports measured checks only (MAF load, frontmatter and size rules, scripts parsed and never executed, static scan); quality metrics say "not measured" (2026-11-10). Left for P6: run the eval cases on the model, NVIDIA SkillSpector
- [x] 2026-11-10 owner report AQE-MODEL-TOOL-TEXT: the model hit MAF's 10-round tool limit, MAF asked for a final answer with tools off, and DeepSeek wrote its next call as text. The harness now has its own budget (`ATLAS_HARNESS_MAX_ROUNDS` 25, `ATLAS_HARNESS_MAX_TOOL_CALLS` 60); when a budget still runs out the reply keeps its text and says "continue" resumes
- [x] Debug log: `data/logs/errors-DAY.jsonl` keeps every warning and error with its source line and stack trace, redacted; download from Settings or `/api/logs?kind=errors`
- [x] "/" menu in the harness chat lists plugin commands (`/agentic-qe:qe-start`) and skills from `GET /api/plugins/slash`; a command sends its SKILL.md instructions with `$ARGUMENTS` filled, a skill name asks the harness to load it. Verified in the browser (`docs/evidence/runs/2026-11-10-slash-mcp/`)
- [x] Memory isolation per project tested (`test_memory_stays_inside_its_project`); deleting a project now also removes `data/harness/<project>/`. The legacy harness is not isolated and stays on the deletion list
- [x] Dummy data: sandbox no longer invents a README repository and `sandbox_ready` is real; MCP servers show `not_connected` and no tool is invented for an unknown server; Studio shows "(no project selected)". Fabrication baseline 76 to 60
- [x] Data clear-out, option A chosen by the owner 2026-11-10: `.env` points at `data/v2`, which started empty; old `data/` kept as the backup. A model must be set again on the Settings page
- [ ] Real RAGAS: install `requirements-evals.txt` into the project `.venv`, then run agent evals on the real model
- [x] Gap analysis vs DeepSeek Harness (`docs/HARNESS_GAP_ANALYSIS.md`); Azure + desktop target design (`docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md`); modularization plan (`docs/MODULARIZATION_PLAN.md`, waiting for owner yes)
- [ ] P3 Plugin manifests and discovery; `SkillsProvider` with admin filter
- [ ] P4 Real MCP through `MCPStdioTool` / `MCPStreamableHTTPTool`
- [ ] P5 Admin governance for plugins, skills, MCP; admin-only writes
- [ ] P6 Skill Studio: task list, edit, approve, generate, evaluate; zip upload
- [ ] P7 UI split and real-data panels
- [ ] P8 Durable loops (skill health, suite green) with code predicates and human gates
- [ ] P9 Electron desktop app (`apps/desktop`), DeepSeek Harness host pattern
- [ ] P10 Live E2E evidence and docs
- [ ] 200-line splits for touched files; docstring fixes (runs alongside P3-P7)
- [x] Revision 2 of the plan: marketplace skill format and 10-phase skill-creator lifecycle, real NVIDIA SkillSpector (D-17 corrected), DeepSeek plugin profiles, ambition lens with CI gates

## Master plan (docs/MASTER_PLAN.md, 2026-11-10)

- [x] M1 (2026-11-10) Legacy harness, seed code and legacy tests removed with `git rm` (owner yes): `src/backend/harness/` (33 files), `api/harness.py`, `core/seed_data.py`, `scripts/populate_seeded_repos.py`, `HarnessView.tsx`, 7 legacy test files. Real checks moved to `test_approvals_and_templates.py`, `test_skill_studio.py`, `test_project_export.py`. Scanner now `maf/skill_scan.py` (no grades). Approvals come only from the database; an unknown approval is 404 instead of a ledgered fake success. `bin/harness` is an AG-UI client of the MAF harness (`test_cli.py`). Also fixed: lines of code were estimated (50 per file), now counted; fake PR function removed. Fabrication baseline 60 to 2. Offline 570 passed
- [x] M2 Modularize (2026-11-10). Backend packages, frontend `features/`, `components/ui/`, `content/docs/`, `scripts/azure/`, and every test file split; the file-size gate `tests/test_file_size.py` has an EMPTY baseline: no platform file is over 200 lines (plugins/ and skills/ content excluded). Test counts unchanged by the splits. Offline 598 passed, 0 failed
- [x] M3 Skill Studio (2026-11-10). Audit `docs/SKILL_STUDIO_AUDIT.md` (21 issues). Backend `/api/skill-studio` on MAF `AgentCall` with the new `skill-creator` agent: source with SHA-256; kind instructions or scripts; plan with tasks, files, sub-agents, formats and eval cases; approval hashed and enforced; generation limited to planned paths; checks (MAF load, frontmatter, size, parse, scan); script tests in a scratch copy with clean env (desktop and local only); try on sample; evaluation with and without the skill stored with n and judge; immutable `skill_versions`, zip download and guarded upload; role checks; fabricated routes removed. UI rebuilt as a stepper with loading messages. Live on the real model: 7 of 7 checks, uplift +0.24 over 6 cases (`docs/evidence/runs/2026-11-10-skill-studio-live-2/`); fixed eval inputs that copied the source (uplift had measured -0.375). Browser E2E US-51 and US-53 pass on the real model (`docs/evidence/us-51-*.png`, `us-53-*.png`)
- [ ] M4 Harness. Built 2026-11-11: web/local/desktop profiles (harness desktop-only on web); find_tools/load_tools discovery over the governed catalogue and granted MCP tools; five specialists as MAF background agents; MAF compaction; durable thread snapshots for mode and approvals; approval cards for risky tools; live status lines; stop and continue; `create_skill` tool (draft plan only, human approves in Skill Studio); per-role plugin grants. Fixed after the first live run (9 of 13 stories failed): start in execute mode instead of plan mode; scan, sandbox status and findings in the core tools; duplicated status lines; MAF loop nudges leaking into the reply (`harness_kit/nudges.py`); a round without a tool call ends the todo loop. Offline 607 passed. Left: live story rerun, hooks need `agent-hooks-sdk`
- [ ] M5 MCP. Backend done 2026-11-10: MAF `MCPStdioTool`/`MCPStreamableHTTPTool`/`MCPWebsocketTool` connect for real; tools come only from `list_tools`; status connected only after a real session, otherwise error with the message; secrets encrypted, only names returned; calls need an admin grant per role and are audited (`tool_calls` kind mcp, ledger `mcp.tool_called`); stdio off in the web profile; catalog of install templates instead of seeded servers; `mcp_playwright_tools.py` retired; migration 017 removes the earlier seeded servers and declared tools. Plugins: upload (zip-slip guarded), enable and disable, `.mcp.json` registration. Tested against a real MCP server (`tests/fixtures/mcp_echo_server.py`). Offline 590 passed. Left: `/mcp` page and plugin UI (running), harness wiring (M4)
- [ ] M6 Azure proof of concept: portal guide `docs/AZURE_POC_PORTAL_GUIDE.md` written; `python scripts/dev.py azure-local` added; packager now ships new uncommitted files too. Left: run azure-local, split the packaging scripts (running)
- [ ] M7 Desktop: `apps/desktop` Electron app written. Dev-mode run verified 2026-11-10 by `tests/desktop/test_desktop_app.py` (real Electron over CDP: first-run admin stored with OS keychain encryption, backend and UI started, login window). Fixed: the app quit when the setup window closed. Left: PyInstaller backend bundle, DMG build, MSI on the CI Windows runner, harness stories in the packaged app
- [ ] M8 User stories for every page; unit, integration and Playwright E2E; HTML evidence report with screenshots; real RAGAS
- [ ] M9 Final proof on web, desktop and Azure; review; docs

## Master plan Part 2, revised 2026-11-11 (harness first, zip deployment; approved 2026-11-11)

- [x] H1 (2026-11-11) Deferred-tool index (every loadable tool by name and purpose in context), action-first descriptions, skill-creator hidden from the harness, acting instructions. Live: HS-02, HS-07, HS-10 now pass; 11 of 13 stories (HS-06 waits for H3; status test had a test race, fixed). Left: harness eval set
- [ ] H2 Execution world: workspace, MAF file access with approvals, MAF shell executor with allowlist and approvals, 5 sandbox slots on web
  - Built 2026-11-11 (offline tests pass, `tests/test_harness_world.py`): `harness_kit/workspace.py`, `shell.py`, `leases.py`, migration 021, `agent-framework-tools==1.0.0b261030`; the harness now runs on the web profile with 5 slots. Live: 19 approved shell commands ran and were audited; the validator environment was set up through `run_shell`
- [ ] H3 Full agentic-qe plugin in the harness: install @8a7497b, Claude Code hook adapter, plugin agents, commands end to end, personal-finance-mcp cycle through the harness
  - Built 2026-11-11: plugin @8a7497b, `core/plugin_hooks.py`, `harness_kit/hook_middleware.py`, `prompt_hooks.py`, `plugin_agents.py`; `tests/test_harness_plugin_hooks.py` runs the real guard-bash.ts and approval-hook.ts. Live cycle (`docs/evidence/runs/2026-11-11-harness-plugin/`): Gate 0 recorded by the plugin from the typed phrase; Gate 1 refused by the plugin because the model never wrote `02-requirements/requirements.json`; no phase document was written by the model (deepseek-v4-flash explored with 622 tool calls and confused the platform's `project_status` gates with the plugin's). Left: a cycle past Gate 1 on a model that follows the command steps
- [ ] H4 Harness parity: fork, replay check, background tasks, SAFETY.md, CLI commands
- [ ] H5 Skill Studio and agents. Done 2026-11-11: 5 fake skills removed and recreated live (quality strategy, markdown to docx 11/11 tests, html to pdf test design published; data to table published with 2 failing tests, so publish now requires the skill's own tests to PASS on the same files, and it was removed; html to pdf imported an uninstalled package, so a new check refuses imports outside the standard library and platform packages; scanner: an HTML <script> mention is medium, not blocking). Left: rerun of the two script skills, 4 more fake skills found (owner decision), per-skill dependencies, agent evals, RAGAS
- [ ] H6 Local and Azure environments; PostgreSQL and Blob; zip deployment guide
- [ ] H7 Desktop: docs/DESKTOP_RELEASE_GUIDE.md written; build writes latest-<os>.json with SHA-256; login page Desktop app section from ATLAS_DOWNLOADS_URL (verified empty state in the browser). Left: DMG and MSI builds
- [ ] H9 OpenTelemetry traces, local span store, optional OTLP, trace explorer (admin all, members own)
  - Built 2026-11-11: `core/tracing/`, migration 020, `/api/traces`, `/traces`, tests `tests/test_tracing_*.py`. Open: browser check, "View trace" link on harness replies (needs `features/chat`).
- [ ] H8 Evidence report for everything on local and Azure
- [ ] Phase Q (`docs/MASTER_PLAN.md`, trace `docs/analysis/2026-11-11-markdown-html-converter-trace.md`)
  - [x] Q1 (2026-11-11) B1 to B7, B14 to B18 fixed offline with `tests/test_qe_correctness.py`. Left: Q4 live rerun on the real model (empty repository stops at Gate 0; a real converter repository gives string-typed cases, no invented Exception case, no stubbed subject)
  - [ ] Q2 chat approvals and history (B9 to B13), Q3 joinable logs (G1 to G15), after H2 and H3
- On hold: QE Cycle UI on the plugin
- [x] Landing page (owner request 2026-11-11, smoke test `test_the_home_page_is_a_public_landing_page_with_downloads_and_sign_in`, screenshots `docs/evidence/screens/landing-*.png`): public `/` with desktop downloads and Sign in; projects list at `/projects`; links, sign-in redirect and e2e tests follow
- [x] Plugin command focus (owner 2026-11-11, offline tests pass; live cycle attempt 4 running): active command pinned in instructions, platform QE tools hidden during a plugin command, required files shown as written or missing; live agentic-qe cycle on personal-finance-mcp past Gate 1
- [x] G5 PostgreSQL only: psycopg pool, dialect translator, baseline schema, local cluster, data move verified; 672 offline tests pass on PostgreSQL. Left: owner's yes to delete the SQLite-only tests and old migrations; G6 Blob files
- [x] G7 Key Vault at startup (managed identity, `backend/keyvault.py`)
- [x] G8 desktop installers in CI (per-arch DMG, MSI, release on tag); first CI run pending a push
- [x] G9 standard Azure guide with East US 2 costs
- [x] FINAL_PLAN 5.5: one error shape for harness tool failures (`harness_kit/errors.py`), 2026-11-12
- [x] Budget stop and pinned command tell the user to re-send the plugin phase command, not "continue", 2026-11-12
- [x] agentic-qe Gate 1: documented evidence fields accepted, quotes checked on disk (`tests/test_agentic_qe_evidence.py`), 2026-11-12
- [x] Harness: files a plugin hook refused are not written again in the thread; write-first nudge cites only files read, 2026-11-12

## Phase 2 (docs/PHASE2_PLAN.md revision 3, 2026-11-12), awaiting approval
- [x] Owner decisions D-SHELL, D-SHELL-WEB, D-SANDBOX, D-CLI (plan section 17), 2026-11-12
- [ ] 1 Discovery eval baseline (20 tasks): built; run blocked by the model proxy's daily token quota; run later on commit b76ddbd
- [x] 2 Persistent Bash and PowerShell (background, new-output notes, spill); permission modes and rules; /mode (2026-11-12). Short tool names moved to step 4 with the capability index
- [x] 3 Script runtime for Python, TypeScript, JavaScript, Bash, PowerShell and shebang interpreters; health checks and flags (2026-11-12)
- [x] 4 Skill scopes (personal, repository, plugin) read every turn; tool index with arguments; nearest names for invented tools; MCP list refresh; command substitutions (2026-11-12). Eval after: waits for the model quota
- [x] 5 Settings files; hooks from settings, http hooks, updatedInput, PostToolUseFailure, Stop hooks; checkpoints and /rewind; helper-agent permissions; background tasks (step 2) (2026-11-13). Sessions as JSONL and conversation rewind move to step 6 with the CLI
- [ ] 6 `aqh` CLI interactive and headless; live CLI session on macOS and Windows
- [ ] 7 OS sandbox tiers (Seatbelt, bubblewrap; Windows approval or container)
- [ ] 8 R6 credentials and desktop sign-in; desktop Terminal pane
- [ ] 9 R2 features governance; R1 home and gated downloads
- [x] Playwright UI audit test (tests/e2e/test_ui_audit.py), 2026-11-12
- [ ] 10 UI audit fixes U1 to U10; audit at zero findings
- [ ] 11 R3 uploads and brainstorming; R4 Atlassian (optional)
- [ ] 12 R5 QE cycle to Gate 5 with traceability
- [ ] 13 Azure guide, proposal workbook, docs refresh
