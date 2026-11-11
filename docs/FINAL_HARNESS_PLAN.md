# Final Plan: a complete, working MAF harness with no dummy data

> **Superseded on 2026-11-10 by `docs/MASTER_PLAN.md`,** the single active plan. The findings below stay valid.

Status: **written 2026-11-10 after re-checking the whole application.**
- The owner approved the plan direction on 2026-11-10 ("approve plan after revisiting everything").
- Deletions still need a yes on the exact list in Section 4. CLAUDE.md requires a listed yes for every removal.

This plan supersedes the phase order in:
- `docs/HARNESS_REBUILD_PLAN.md` (its findings stay valid);
- `docs/MODULARIZATION_PLAN.md`;
- `docs/HARNESS_GAP_ANALYSIS.md`;
- `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md`.

## 1. Goal and definition of done

The goal is a harness built on Microsoft Agent Framework (`create_harness_agent`) that a BA, developer, QE or admin can use on the web or on desktop, backed by Azure, with nothing invented anywhere. It is done when all of these hold:

1. **User stories.** All 14 stories in `docs/HARNESS_USER_STORIES.md` pass in the real browser on the real model (`tests/e2e/test_harness_stories.py`), and the rest of E2E stays green.
2. **CI gates.** The no-fabrication gate has an **empty** baseline (`tests/fabrication_baseline.json` = `{}`). The approvals gate passes. A new file-size gate allows no file over 200 lines except a listed, shrinking baseline.
3. **Real data only.** Every number shown in the UI comes from a stored measurement or says "not measured".
4. **Azure.** The deployment runs on PostgreSQL, Blob, Key Vault and Entra, with immutable document versions, and the desktop app signs in to it.

## 2. Where it stands (measured 2026-11-10)

| Check | Result |
|---|---|
| Offline suite | 618 passed |
| E2E platform suite, real model | 34 of 34 (`docs/evidence/runs/2026-11-10-1834-*`) |
| User stories, live API | 8 pass, 1 partial, 1 fail, 4 not built (`docs/evidence/runs/2026-11-10-harness-stories/`) |
| User stories, Playwright | See `docs/evidence/runs/2026-11-10-stories-e2e/` |
| Azure zip + Kudu | Both packages run through the real `startup.py` and `startup.js`; 28 of 28 pages, harness chat works |

## 3. Register of remaining dummy or invented data (complete as of this audit)

| ID | Where | What is invented | Fix | Phase |
|---|---|---|---|---|
| F-01 | `skills/evaluator/scripts/evaluate_skill.py` | Scores from constants: `recall = 95.0`, groundedness from body length, a fixed 98, "A+ PRODUCTION READY" | **Partly fixed 2026-11-10**: now reports measured checks only (MAF load, frontmatter and size rules, scripts parse without running, static scan); quality metrics show "not measured". Running eval cases on the model remains | F6 |
| F-02 | `app/skills/studio/page.tsx` | `evalResult.totalScore ?? 95`, `groundedness ?? 96`, `faithfulness ?? 98`, `verdict ?? "APPROVED"` | **Fixed 2026-11-10** | done |
| F-03 | `maf/evals/ragas_evaluator.py` | Constant 0.93-0.97 "Specter RAGAS" scores for any metric without a scorer | **Fixed 2026-11-10**: a "Not available" note, no score | done |
| F-04 | Existing `data/atlas.sqlite3` | Fake seeded projects and gates (D-05) and stored invented eval scores (F-03, D-04) | Migration that removes rows with `judge_model='ragas-specter-v1'` and the four seeded project ids | F1, owner yes |
| F-05 | `app/skills/page.tsx` | "Specter" score computed from a hash of the skill name; "59+ skills validated" | **Fixed 2026-11-10** | done |
| F-06 | Legacy harness: `components/HarnessView.tsx`, `src/backend/harness/*`, `api/harness.py`, `harness/agent_evals.py` | Hardcoded scorecards (142 evaluations, A+), canned plan, design, generate, review, heal, stories and gherkin tools, template BRDs, fake "thoughts", "NVIDIA/Cloudflare" claims | Retire; the MAF harness replaces it (Section 4) | F1, owner yes |
| F-07 | `api/mcp.py` seed, `api/mcp_playwright_tools.py`, `app/mcp/page.tsx` | Servers seeded as "connected" with tool counts, no real connection | **Partly fixed 2026-11-10**: status is `not_connected`, tool lists are labelled declared, no tool is invented for an unknown server. Real connections remain | F4 |
| F-08 | `repos/sandbox.py` | `ensure_sandbox` writes a made-up README and commit when no repository exists; `info()` returns `sandbox_ready: True` always; `generate_pull_request_sim` (unused) stores sha `'dummy'` | **Fixed 2026-11-10** except the unused function, which is on the deletion list | done |
| F-09 | `skills/*/scripts/run.py` in `comprehensive-quality-strategy-test-plan-agent-skill`, `markdown-to-docx-document-converter`, and `data-to-table-creator` (untracked) | Each script reports every step PASSED without doing anything | Mark them `NOT_IMPLEMENTED` like the fixed Studio template, or implement them | F1, owner yes (skill content) |
| F-10 | `content/docs.ts`, `app/agents/[key]/page.tsx` | "Cloudflare WAF", "NVIDIA Skill Specter A+ compliance", invented "standards" | **Fixed 2026-11-10** | done |
| F-11 | `app/skills/studio/page.tsx` | Shows `prj_mcp_market` when no project is chosen | **Fixed 2026-11-10** | done |
| F-12 | `core/seed_data.py`, `scripts/populate_seeded_repos.py` | Fabricated projects, gates and metrics (no longer run at startup) | Retire | F1, owner yes |

Data clear-out and the target data layout: `docs/DATA_ARCHITECTURE.md`.

## 4. Deletion list for the owner's yes

All of this stays in Git history. Removal happens only after a yes, and the full suite and E2E run before and after.

- **Legacy harness backend:** `src/backend/harness/` (whole folder, 27 files) and `src/backend/api/harness.py`. Remove its router from `api/__init__.py`, and its tests: `tests/test_harness_universal_hitl.py`, `test_harness_specter_rag_and_skills.py`, `test_harness_project_scoped_features.py`, `test_harness_ba_studio_real_generation.py`, `test_e2e_full_scenarios.py`, `test_stress_and_concurrency.py` (harness parts).
- **Legacy harness UI:** `src/frontend/components/HarnessView.tsx` and the `?engine=legacy` branch.
- **Seed data:** `src/backend/core/seed_data.py`, `scripts/populate_seeded_repos.py`, `scripts/capture_evidence.py` (it targets the seeded projects).
- **Unused code:** `repos/sandbox.generate_pull_request_sim`.
- **Packagers:** merge three into one. Keep `scripts/package_azure_kudu.py`; retire `scripts/package_azure.py` and fold `scripts/azure_convert_and_deploy.py` setup-script generation into it.

Before removal, check what `bin/harness` (CLI) and the skill-test endpoints use from `src/backend/harness/`. Move anything real (for example `rag_store.py` if kept) into `maf/` first.

## 5. Phases

Each phase ends with:
- offline suite, smoke, E2E and story E2E on the real model;
- an Opus review;
- evidence under `docs/evidence/runs/`;
- an update to `PROGRESS.md`;
- one commit and push to `feature/maf-harness-platform` after the owner says so.

| Phase | Work | Stories it turns green | Subagents (model) |
|---|---|---|---|
| **F1** No dummy data | Fix F-02, F-05, F-08, F-10, F-11. With the owner's yes: retire F-06 and F-12, run the F-04 migration, fix F-09. The fabrication baseline goes to `{}` | HS-14 stays green | 2 Sonnet writers on separate files, Opus review |
| **F2** Modularization | `docs/MODULARIZATION_PLAN.md` Group B (backend packages, frontend `features/` folders), test splits, a file-size CI gate. Behaviour and imports stay the same | none (refactor) | 4 Sonnet writers by feature, Opus review |
| **F3** Commands, sub-agents, hooks, approvals (P3b) | Command registry (`/plugin:cmd`), `BackgroundAgentsProvider` over the governed specialists, Claude Code hook adapter for agentic-qe, AG-UI approval cards in `Chat.tsx`, mode persistence (thread snapshot store) | HS-06, HS-11 | Opus (design) + 2 Sonnet |
| **F4** Real MCP (P4) | Plugin `mcp.json`, `MCPStdioTool` (desktop) and `MCPStreamableHTTPTool` (Azure), MCP page from real status, NVIDIA SkillSpector as the first MCP server | (MCP part of HS-12) | Sonnet, Opus security review |
| **F5** Governance (P5) | `plugins`, `plugin_grants`, `mcp_grants` tables; admin-only writes; separation of duties; install from marketplace and enable/disable plugins; grants feed `FilteringSkillsSource` and MCP `allowed_tools` | HS-12 | Opus |
| **F6** Skills (P6) | Harness `create_skill` tool (draft, approve, write); evaluator rebuilt (F-01) with SkillSpector and measured eval cases; Studio task-list approval enforced in code; zip upload with zip-slip guard | HS-08, HS-09, HS-10 | Sonnet + Opus security review |
| **F7** Azure cloud | PostgreSQL behind `db.py`, immutable `document_versions`, Blob for files and harness state, Key Vault, Entra ID, Container Apps Jobs for sandbox runs, Service Bus workflows, App Insights | all stories on Azure | Opus (design) + Sonnet |
| **F8** Desktop | Electron cloud mode (Entra sign-in), then local mode (bundled backend, stdio MCP); signed installers for 3 OSes | HS stories in the desktop shell | Sonnet |
| **F9** Final proof | Full E2E + story E2E on web, deployed Azure (owner's subscription), and desktop; evidence report; docs | 14 of 14 | Sonnet runner, Opus final review |

## 6. Decisions needed from the owner

| # | Decision | Default |
|---|---|---|
| 1 | Yes to the Section 4 deletion list | Nothing removed |
| 2 | Purge F-04 rows from the existing database | Kept |
| 3 | F-09 skill scripts: mark NOT_IMPLEMENTED or implement | Mark |
| 4 | Azure decisions A to E in `docs/AZURE_DESKTOP_TARGET_ARCHITECTURE.md` | - |
| 5 | Marketplace licensing (TCS proprietary skills): runtime install only? | Runtime install only |
| 6 | NVIDIA SkillSpector install (`uv tool install`) | Not installed |
