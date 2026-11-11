# Next steps: status and restart point (2026-11-11)

This file is the restart point after a context compaction. The approved plan is `docs/MASTER_PLAN.md`, Part 2 (H1 to H9). This file says what is done, what is running, and exactly what comes next.

- Branch: `feature/maf-harness-platform`. Last commit `5a5e6df` (pushed).
- Everything below this line is **uncommitted**. Commit and push only when the owner says so. Never touch `main`.

## Owner decisions in force
- **Azure.** Deployment is zip plus Kudu **only**; GitHub cannot connect to the Azure web app. Region **eastus2**. Use PostgreSQL Flexible Server B1ms plus Blob Storage.
- **Harness first.** The QE Cycle UI is **on hold** until the harness runs the whole agentic-qe plugin.
- **Plugin.** Use the full agentic-qe plugin, branch `agentic-qe-plugin`, commit `8a7497b`, replacing `plugins/agentic-qe/`.
- **Web.** All features on the web, with 5 sandbox slots. stdio MCP, npx and plugin installs are desktop or local only.
- **Observability.** OpenTelemetry with a trace explorer. Admins see all traces and logs; members see only their own.
- **Fake skills.** Remove every fake Studio skill and recreate it from a similar requirement in Skill Studio (the first 5 on 2026-11-11, and the other 4 on 2026-11-11, "Yes, remove and recreate").
- **Harness shell.** The allowlist is node, npx, npm, python, pytest and read-only git, each command approved in chat. Use the official MAF tools package for the shell executor.

## Done (uncommitted)

| Item | Evidence |
|---|---|
| H1: deferred-tool index (every loadable tool by name and purpose in context), action-first tool descriptions, `skill-creator` skill hidden from the harness, acting instructions in `prompts/harness.md` | `tests/test_harness_discovery.py`. Live: 11 of 13 harness stories pass (HS-02, HS-07, HS-10 fixed). HS-06 waits for H3. Status test race fixed in the test (`all_inner_texts`), not rerun |
| H5, part one: 5 fake skills removed and recreated on the real model | `docs/evidence/runs/2026-11-11-skill-recreation*/`. Published: `planning-quality-strategy`, `markdown-to-docx-converter` (11/11 own tests), `designing-html-to-pdf-test-scenarios`, `tabular-data-converter` (5/5). The HTML-to-PDF converter was refused because it needs a PDF library |
| Skill Studio: publish requires the skill's own tests to PASS on the same files | `tests/test_skill_studio_publish.py` |
| Skill Studio: imports check (only standard library, the platform's declared packages, or the skill's own modules) | `core/skill_studio/checks.py` |
| Skill Studio: bounded repair loop (`POST /api/skill-studio/plans/{id}/repair`, 2 rounds). A repair that removes tests or assertions, or adds `assert True` or a skip, is refused | `tests/test_skill_studio_publish.py`. A "Repair from test failures" button is in `features/skills-studio/TestStep.tsx` |
| Scanner: a `<script>` mention in Markdown is medium, not blocking | `maf/skill_scan.py` |
| H9: OpenTelemetry spans (requests, tools, workflows, sandbox), local `spans` table (migration 020), optional OTLP, `/api/traces` (admin all, members own, others 404), `/traces` explorer UI | `tests/test_tracing_*.py`. **Not browser-checked yet** |
| H7: `docs/DESKTOP_RELEASE_GUIDE.md`; the build writes `latest-<os>.json` with SHA-256; the login page has a "Desktop app" section from `ATLAS_DOWNLOADS_URL` (`app/api/downloads/route.ts`) | Empty state checked in the browser |
| Harness: MAF loop nudges kept out of replies; a loop round with no tool call ends the todo loop | `tests/test_harness_m4.py` |
| Offline suite | 618 passed at the H9 writer's last run. Run again after the latest changes |

## Done later on 2026-11-11 (uncommitted)
- **Skill Studio error display.** A dict error detail was shown as Python text. `app.py` now uses the dict's message, `api.ts` keeps the structured detail, and `useCall` shows the message plus the kept reply file.
- **SKILL.md frontmatter.** Your failing case: the description had an unquoted colon, the YAML broke, and the error message misled the three retries. The server now writes name, description and author from the approved plan as quoted YAML, and keeps the model's body (`models.canonical_skill_md`, test in `test_skill_studio_publish.py`).
- **Script skills are evaluated by running `scripts/run.py`** (input on standard input, output printed), not by the model acting out SKILL.md. Every script skill must ship `run.py`.
- **Repair loop fix.** The step lost the plan's source text, and a 404 "Not found: source_text" hid it.
- **Agent tiles.**
  - A blank tile now shows its reason (n/a, "RAGAS is not installed", "No eval case has a labelled answer key", "No eval case gave the agent repository or document context to cite").
  - Every eval run records those reasons. Before, Recall, F1 and groundedness had no row and read "no evaluation has run".
- **The 4 other fake skills were removed.**
  - Recreated: `docx-to-pptx-converter` and `settlement-idempotency-verifier`, rerunning under the new rules.
  - The two Markdown-to-DOCX duplicates are covered by `markdown-to-docx-converter`.
- **RAGAS.** A project `.venv` is being created with `requirements.txt` and `requirements-evals.txt`, so RAGAS can measure faithfulness. That install needs the sandbox off for TLS.

Still to do for real agent scores:
- Run every agent's evals with RAGAS on the real model.
- Add labelled answer keys and repository context to the eval cases (`evals/*.json`), so Recall, F1 and groundedness can be measured. Labels come from the case's own construction (a planted bug, a known requirement list), never invented.

## Skill recreation results (live, 2026-11-11, `docs/evidence/runs/2026-11-11-skill-recreation-5/`)
- `docx-to-pptx-converter`: 1 of 3 tests passed, the **repair loop** got it to 3 of 3 in one round, and it was published.
- `settlement-idempotency-verifier`: 7 of 7 tests passed and it was published.
- Both evaluations show a negative uplift. The causes, from the evidence:
  - DOCX to PPTX: `run.py` crashed on every case, because the eval inputs are prose, not DOCX files.
  - Settlement: the script is right on every case, but the assertions are brittle ("not_contains 'Duplicate'" fails on the honest sentence "No duplicates found").
- Evaluation now reports script crashes as `script_failures` plus a note, instead of hiding them in the pass rate.

**Next for Skill Studio evaluation (H5):**
1. The plan states the script's **input contract** (what `run.py` reads), and eval inputs must follow it.
2. File-based skills get fixtures: `evals/fixtures/` built by a planned `scripts/make_fixtures.py`, since DOCX cannot be written as text.
3. Assertions are reviewed in the plan before approval, with the UI showing the risk of negative wording.
4. Per-skill dependencies are installed in an isolated environment, so HTML to PDF can use a PDF library.

## Owner report 2026-11-11 (Markdown-HTML-converter, `prj_015c85df23f2`)
- **Analysis:** `docs/analysis/2026-11-11-markdown-html-converter-trace.md` (18 bugs, 15 log gaps). Plan: `docs/MASTER_PLAN.md`, **Phase Q** (Q1 QE workflow, Q2 chat approvals and history, Q3 joinable logs, Q4 proof).
- **Fixed the same day:**
  - The approver `***`: the admin password equalled "admin", and the masking replaced every "admin". Secrets under 12 characters are no longer substring-masked, and the admin is warned about a weak password.
  - Approver name, role and email are shown; user email is stored encrypted.
  - Skill Creator Studio is hidden inside projects.
- **Owner action needed:** change `ATLAS_ADMIN_PASSWORD` (it equals the username) and restart.

## Capability registry (owner request 2026-11-11), `docs/MASTER_PLAN.md` Phase R
- A table of every tool, agent, skill, command, workflow, stage, plugin, hook, script and MCP tool, with links (contains, performed_by, uses_tool, applies_skill, runs_script, delegates_to, serves). It is derived from code by a deterministic sync, never typed by hand.
- **The harness reads it on every run:** an index in context, plus `find_capability` (BM25) and `describe_capability`. Each tool call records its capability id.
- **Status:** registry core, sync, API, UI and `docs/CAPABILITY_REGISTRY.md` are being built by a writer. The harness wiring follows after H2 and H3.

## Done after the env batch (2026-11-11)
- **Q1, QE workflow bugs:** B1–B7 and B14–B18 are fixed, with offline tests in `tests/test_qe_correctness.py`. Not rerun on the real model yet (that is Q4). Rejecting a gate now needs a reason, and the UI still allows an empty reject.
- **Phase R, capability registry:**
  - core, sync, API and the `/capabilities` UI are built, with `docs/CAPABILITY_REGISTRY.md`;
  - 187 capabilities and 309 links;
  - not checked in a browser;
  - the harness wiring (`find_capability`, `describe_capability`, `index_text`) comes next.
- **CI fixes:**
  - `mcp>=2.2,<3` added to `requirements.txt`. agent-framework-core lists it only as an extra, so CI had no `mcp` and every stdio MCP test failed.
  - The branch-isolation test runs its `.sh` script through bash, Git's own on Windows, which fixes WinError 193.
- **Azure guide:** `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md` is now the end-to-end portal guide, with a UI tour.
- **Owner cleanup (not deleted):** an early registry probe created an `atlas.sqlite3` at the repo root and the empty folders `checkpoints/`, `logs/`, `projects/` and `runs/`. Git ignores or skips them all.

## Part 3 progress (owner goal 2026-11-11: accurate harness, PostgreSQL only, Azure standard)

- **G1 harness accuracy** (`maf/harness_kit/active_command.py`, `strict_args.py`; `tests/test_harness_active_command.py`):
  - A typed plugin command stays the thread's active command, in the instructions on every call.
  - The platform's QE workflow, gate and document tools are hidden while it runs.
  - Its files are listed as written or MISSING on disk.
  - Unknown tool arguments are now an error the model reads, with `include_detailed_errors`. Before, they were silently dropped: `file_access_ls(path=...)` listed the root 73 times.
  - Live cycle: `docs/evidence/runs/2026-11-11-harness-plugin-cycle2/`. Attempts 1 to 3 found the problems above, and attempt 4 runs with all fixes.
- **G5 PostgreSQL only:**
  - `backend/db.py` uses psycopg 3 with a pool; `backend/sql_dialect.py` translates the SQLite dialect; `migrations/postgres/0001_baseline.sql` is the final schema of migrations 001 to 023.
  - `backend/local_postgres.py` starts a local cluster for development, tests, `azure-local` and the desktop app.
  - `scripts/sqlite_to_postgres.py` moves a store once and verifies it. The owner's `data/v2` store was moved: every count matches, 2 of 2 ledgers verify, and 12 of 12 document hashes match.
  - Offline suite on PostgreSQL: 672 passed. The failures left are the SQLite-upgrade tests listed below.
- **G7 Key Vault:** `backend/keyvault.py` reads secrets with the managed identity (`ATLAS_KEY_VAULT_URL`); `tests/test_keyvault.py`.
- **G8 desktop CI:** `desktop.yml` builds the DMG (arm64 and x64, each on its own runner) and the MSI on every push that changes the app, and a `v*` tag makes a GitHub Release.
- **G9 guide:** `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md` is the standard: PostgreSQL B1ms, Blob, Key Vault, East US 2, about $28.50 a month (prices read 2026-11-11).
- **CI fixes:** the evals job ran a deleted test file; a Windows path case; macOS runners get PostgreSQL.
- **Waiting on the owner's yes to delete:**
  - the SQLite-only tests: `tests/test_migration_006.py`, `test_access_account.py::test_migration_010_…`, `test_models_usage.py::test_migration_009_…`, `test_core_platform.py::test_sqlite_journal_mode_is_a_setting`;
  - the old SQLite migrations `src/backend/migrations/0*.sql` (001 to 023), replaced by `migrations/postgres/0001_baseline.sql`.
- **Not done yet:** G6 (files in Blob), G4 (Skill Studio requirements page), G2 and G3 (an app built end to end; subagents from chat), bundled PostgreSQL for the desktop (D-P1).

## Batch after commit 16af7f7 (2026-11-11)
- **Harness `write_first` guard** (`maf/harness_kit/write_first.py`): while the active command owes files, 15 reads in a row nudge, and 25 refuse until something is written. Commands whose files follow a gate (qe-start) are exempt.
  - Found live: attempt 4 read 318 files and wrote none.
  - Attempt 5 wrote, but qe-start wrote before Gate 0, which is now exempt.
  - Attempt 6 is running.
- **`local_postgres`:** a new cluster gets its password over SQL, not from a password file, because the file is unreadable to `initdb` on Windows (CI failure). Unix sockets are off: a long app-data path broke the 103-byte limit.
- **Desktop MSI:** WiX needs an icon. Added `apps/desktop/assets/icon.png` and `icon.ico`.
- **Templates are Markdown only** (API refuses others with 415; UI pickers `.md`).
- **Security** (`docs/SECURITY_REVIEW_2026-11-11.md`):
  - pip-audit clean after removing the unused `chromadb`;
  - npm audit 33 to 19, all from 2 root advisories, accepted with reasons;
  - Bandit: 0 high, untrusted XML now parsed with defusedxml;
  - the CopilotKit route answers 401 or 413 before parsing.
- **`docs/PROJECT_STRUCTURE.md`:** all 1,069 files described, with Uses and Used by.
- **`docs/DESKTOP_RELEASE_GUIDE.md`:** GitHub Release publishing; install steps for everyone; where data and session JSONL files live; MCP via npx; plugins; scope.
- **Live skill from a BRD** (`docs/evidence/runs/2026-11-11-skill-from-brd/`): Studio plan, approve, generate and test passed 9 of 9 on the first run; the full run, including the harness, is running.

## Running or stopped

| Item | State | Restart |
|---|---|---|
| H2 + H3, plugin runtime in the harness | Opus writer stopped on the usage limit before changing plugin or harness files | Resume that writer (its brief is in the conversation). Otherwise start a new one with H2 + H3 from `docs/MASTER_PLAN.md`: workspace; MAF file access with approvals; the MAF shell executor from the official `agent_framework_tools` package; full plugin install at `8a7497b`; a Claude Code hook adapter (PreToolUse, PostToolUse, UserPromptSubmit, SubagentStop); plugin agents; `qe-*` commands end to end; a live `personal-finance-mcp` cycle through the harness, with evidence in `docs/evidence/runs/2026-11-11-harness-plugin/` |

## Next, in order
1. **Remove and recreate the 4 other fake Studio skills** on the real model: `create-skill-to-convert-docx-file-to-ppt-file-with-infographics`, `create-skill-to-convert-md-file-to-docx`, `markdown-to-docx-engine`, `settlement-idempotency-verifier`. Use the recreation runner (a parent reads the model from the original `data/` store and passes it only through the environment).
2. **Skill Studio error display (owner report).**
   - A rejected model reply shows as a raw Python dict (`{'message': ..., 'reply_file': ...}`). Show the message and the kept reply file properly.
   - Root cause: the model wrote SKILL.md without YAML frontmatter, and the schema refused it. Retry the generation once with the validation error, as other agent calls do, before giving up.
3. **Blank agent scores (owner report, Agents page).** Groundedness, Faithfulness, Recall and F1 show "—" for every agent. Find where these metrics come from (`maf/evals/store.py` METRICS_BY_AGENT, the evals runner, RAGAS). Run the agents' eval sets on the real model. Install `requirements-evals.txt` for RAGAS, so every applicable metric has a stored measurement with `n` and the judge. A metric that does not apply stays "n/a", never a number.
4. **H2 + H3** (see above).
5. **Browser checks:** `/traces` (tree, waterfall, member vs admin), the Studio repair button, and the login downloads section with a real `latest.json`.
6. **Rerun all harness stories and the status-line test** on the real model.
7. **The rest of the approved plan:**
   - H4: fork, replay, background tasks, `SAFETY.md`, CLI commands.
   - H5: per-skill dependencies installed in an isolated environment for tests, so the HTML-to-PDF converter can work; agent evals.
   - H6: local and Azure environments; the PostgreSQL and storage layers; `docs/AZURE_POSTGRES_BLOB_PORTAL_GUIDE.md` (zip deploy).
   - H7: DMG and MSI builds.
   - H8: one HTML evidence report for local and Azure.
8. **Update** `tasks.md`, `PROGRESS.md` and the spec after each step. Commit only on the owner's word.

## How to run things here
- **Offline suite:** `PYTHONPATH=src:. python3 -m pytest -q -p no:cacheprovider tests --ignore=tests/e2e -m "not live and not desktop"`.
- **Live browser stories:** use the scratch runner `run_e2e.py`, which reads the model from the original store with `ATLAS_DATA_DIR=<repo>/data` and passes it only by environment. Set `ATLAS_E2E_DIST_DIR=.next-e2e-v2`, because the `.next-e2e` cache is stale. These runs need the sandbox off: they bind ports and launch browsers.
- **Gates:** `tests/test_file_size.py` (empty baseline: no file over 200 lines), `tests/test_no_fabrication.py`, `tests/test_agents_approve_nothing.py`.
