# Modularization Plan: the 200-line rule and feature-based layout

> **Superseded on 2026-11-10 by `docs/MASTER_PLAN.md`,** the single active plan. The findings below stay valid.

Status: **waiting for the owner's yes.** Splitting a file overwrites it, and moving code into feature folders moves files; CLAUDE.md requires permission for both. Nothing below has been done.

What the rule check found (2026-11-10, `git ls-files | xargs wc -l`):
- Every file written in this rebuild (P1, P2, P3) is under 200 lines.
- The existing code still has **about 60 source files over 200 lines (≈25,000 lines)** and **21 test files over 200 lines**. They were not split.

## Rules for every split

- **Behaviour is preserved.**
  - Public import paths stay the same: a module becomes a package whose `__init__.py` re-exports, and API routes and paths are unchanged.
  - The offline suite, smoke, and E2E pass before and after.
  - No test is weakened.
- **Feature-based layout.**
  - Backend: a large module becomes a package named after its feature (`api/skills.py` becomes `api/skills/` with `catalog.py`, `studio.py`, `evaluate.py`).
  - Frontend: page-specific components move to `src/frontend/features/<feature>/` (`harness`, `skills-studio`, `mcp`, `projects`, `runs`, `documents`), and `app/**/page.tsx` stays a thin page.
- **One feature per subagent** (Sonnet), on separate files, so writers never collide. An Opus review follows each batch. Each batch is one commit after the owner says so.

## Group A: retire instead of split (legacy or fabricated code; needs a delete yes)

Splitting these would spend effort on code the rebuild replaces. The proposal is to remove each one once its replacement is live, after the owner says yes.

| File | Lines | Replaced by | Precondition |
|---|---|---|---|
| `src/frontend/components/HarnessView.tsx` | 3131 | `components/MafHarness.tsx` (MAF harness on `/harness`) | Owner confirms the legacy view (`?engine=legacy`) can go |
| `src/backend/harness/qe_tools.py`, `harness_agent.py`, `handlers/stream_engine.py`, `handlers/doc_handler.py`, `handlers/skill_handler.py`, `handlers/command_handler.py`, `grounding.py`, `discovery.py`, `intent_classifier.py`, `magentic.py`, `handoff.py`, `todo_provider.py`, `mode_provider.py`, `memory_provider.py`, `mcp_manager.py`, `function_tool.py` | about 3000 | `maf/harness.py` + MAF providers | Same as above; `api/harness.py` legacy routes go with them |
| `src/backend/harness/domain_brd_generator.py` | 434 | BA workflow (`maf/workflows/ba.py`) | Template BRDs are fabricated content (plan D-06) |
| `src/backend/harness/skill_specter.py`, `skill_tester.py` | 526 | evaluator plugin + NVIDIA SkillSpector (P6) | P6 done |
| `src/backend/core/seed_data.py`, `scripts/populate_seeded_repos.py` | 1061 | Nothing; they write fabricated projects and metrics (plan D-04/D-05) | Owner decision 3 |
| `src/backend/api/mcp_playwright_tools.py` | 797 | Real MCP `list_tools` (P4) | P4 done |

## Group B: split into feature packages (kept code)

| Backend file | Lines | Proposed modules |
|---|---|---|
| `api/mcp.py` | 845 | `api/mcp/{__init__,servers,tools,execute,catalog}.py` (rewritten by P4 anyway; split during P4) |
| `api/skills.py` | 787 | `api/skills/{__init__,catalog,studio_suggest,studio_scaffold,studio_save,evaluate,delete}.py` |
| `core/auth.py` | 582 | `core/auth/{__init__,admin,sessions,users,roles,rules,allowance}.py` |
| `repos/doc_parser.py` | 574 | `repos/doc_parser/{__init__,pdf,office,markdown,placeholders}.py` |
| `maf/engine.py` | 528 | `maf/engine/{__init__,run_context,approvals,events,checkpoints}.py` |
| `qe/execution.py` | 522 | `qe/execution/{__init__,runners,install,verdicts,static_checks,environment}.py` |
| `repos/sandbox.py` | 481 | `repos/sandbox/{__init__,setup,commands,git_ops,env}.py` |
| `qe/emit.py` | 476 | `qe/emit/{__init__,python,javascript,checks}.py` |
| `api/documents.py`, `api/projects.py`, `api/governance.py`, `api/settings.py` | 202-415 | one package each, split by sub-resource (versions, exports, members, gates, models) |
| `maf/runtime.py`, `maf/governance.py`, `maf/evals/__init__.py`, `maf/evals/metrics.py` | 202-361 | `runtime` into `build.py`, `agent_call.py`, `json_reply.py`; `evals` by metric family |
| `maf/workflows/shared.py`, `change.py`, `qe/generate.py` | 287-300 | per stage |
| `repos/ingest.py`, `core/models.py`, `qe/model.py`, `qe/confidence.py` | 220-287 | by concern |
| `scripts/azure_convert_and_deploy.py`, `scripts/package_azure_kudu.py` | 398-659 | `scripts/azure/{packaging,verify,setup_script}.py` and thin entry scripts; the three overlapping packagers merge into one (owner yes: it removes two scripts) |

| Frontend file | Lines | Proposed modules |
|---|---|---|
| `app/skills/studio/page.tsx` | 1280 | `features/skills-studio/{DocumentPicker,TaskList,SkillPreview,ScriptRunner,EvaluationCard}.tsx` + thin page |
| `content/docs.ts` | 810 | `content/docs/<section>.ts` + index |
| `app/mcp/page.tsx` | 801 | `features/mcp/*` (with P4) |
| `app/projects/[id]/page.tsx`, `bugs`, `qe`, `ba`, `documents`, `repository` pages | 256-642 | `features/projects/*`, `features/findings/*`, `features/qe/*`, `features/ba/*`, `features/documents/*` |
| `components/RunPanel.tsx`, `GherkinVisualizer.tsx`, `DocumentEditor.tsx`, `ui.tsx`, `Chat.tsx` | 213-602 | `features/runs/*`, `features/documents/gherkin/*`, `components/ui/*` (one file per primitive), `features/chat/*` |
| `app/skills/page.tsx`, `app/agents/*`, `app/settings/page.tsx`, `app/page.tsx` | 216-441 | per feature folder |

Tests over 200 lines (21 files): split per feature alongside the code they cover, with no assertion removed.

## Order

1. **Group A deletions,** once the owner says yes. They shrink the job by about 9,000 lines.
2. **Backend packages, highest churn first:** `api/skills`, `core/auth`, `qe/execution`, `maf/engine`, `repos/sandbox`.
3. **Frontend features:** skills studio, projects, runs, documents.
4. **Packagers merged into one,** once the owner says yes.
5. **Tests split.**
6. **CI gate** that fails on any new or grown file over 200 lines, as a ratchet with a baseline like the fabrication gate.
