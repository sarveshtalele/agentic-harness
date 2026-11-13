# Phase 3: final review, harness accuracy, size, naming, full testing, guides

Owner request, 2026-11-13: review the whole project and find gaps, errors and inconsistencies in the UI and the backend;
reduce its size on SDLC principles; test every feature through the harness and the UI with Playwright, with evidence;
create a skill and test it with the QE cycle; run and verify the QE cycle on two repositories
(`sarveshtalele/personal-finance-mcp`, `sarveshtalele/mcp-server-market-v2`); fix the harness and BA Studio; give the
application professional, consistent naming and English; make local and Azure deployment work and write the developer
guide, the end-to-end guide and the README. Then continue Phase 2 (step 12 onward) where it stopped.

## 1. Why the harness is still not accurate (measured, 2026-11-13)

From the live agentic-qe run on `personal-finance-mcp` (`docs/evidence/runs/2026-11-13-qe-cycle-g5/`, stopped at Gate 0)
and the earlier runs:

| # | Cause | Evidence | Fix |
|---|---|---|---|
| A1 | **The repository runs in the platform's own Python.** The harness shell inherits the platform's `PATH` and `PYTHONPATH`, so `python3` in the workspace is the platform's `.venv` (`mcp` 2.3) while the repository needs `mcp` 1.x. Its tests fail with `No module named 'mcp.server.fastmcp'` for reasons that are not the repository's. | session log: `pip show mcp` -> 2.3.0; pytest `ModuleNotFoundError` | Shell and runners get a `PATH` without the platform's virtual environment and no `PYTHONPATH`; Python repositories run in their own `.venv` in the workspace (made on first use, recorded); the same for Node (`node_modules` in the workspace). A test proves the repository's Python is not the platform's. |
| A2 | **Two tools for every file action.** MAF's file tools (`file_access_ls`, `file_access_read`, `file_access_grep`) and the platform's (`list_files`, `read_file`, `grep`) are both offered; the model alternated and listed folders 48 times in one turn. | session log tool counts | One set: keep MAF's file tools (they carry the approvals) and drop the platform's duplicates in the harness. |
| A3 | **Out-of-phase work.** At Gate 0 (intake only) the agent ran the test suite four times. | session log: `run_tests`, `pytest` during intake | The active command's allowed steps go in the pinned instructions; a phase command that says "wait for approval" ends the turn there (stop hook already exists; bind it to the command). |
| A4 | **Runner flags the repository does not have.** `--timeout=60` needs `pytest-timeout`, which this repository does not install. | pytest: `unrecognized arguments: --timeout=60` | The runner adds a flag only when the plugin is installed in the repository's environment. |
| A5 | **Plugin contracts not read.** Gate 1 refused three times on the 2026-11-12 run: requirements used a field the plugin does not read. | `2026-11-12-harness-plugin-cycle3` | `describe_contract` and `check_gate` tools (done, 7dd659c); prove on the live run. |
| A6 | **Weak model for long procedures.** The configured model is `deepseek-v4-flash-global`, a fast model; it repeated brainstorm questions and wandered in long plugin procedures. | brainstorm live runs; discovery eval 18/20 | Code checks over model output (done for repeats); run the cycle once with a stronger model if the proxy offers one, and report both. |
| A7 | **Harness page error toast:** "Runtime info request failed with status 500" (CopilotKit runtime) when no model is allowed for the account. | screenshot 2026-11-13 | Answer with the real reason, not a 500. |

## 2. Size: what to remove (needs the owner's yes; nothing is deleted before it)

Tracked: 1,728 files, about 101 MB, of which `docs/` is about 92 MB (mostly evidence screenshots and run logs).

| Group | Items | Why |
|---|---|---|
| Duplicate skills | 11 folders in `skills/` that are also in `plugins/agentic-qe/skills/` (analyzing-repositories, authoring-user-stories, building-qe-dashboard, designing-test-cases, executing-tests, extracting-requirements, generating-test-code, generating-test-data, healing-tests, planning-tests, tracing-coverage) | MAF already skips one copy of each ("Duplicate skill name"); two copies drift |
| Superseded plans and reports | `docs/FINAL_HARNESS_PLAN.md`, `HARNESS_REBUILD_PLAN.md`, `MASTER_PLAN.md`, `MODULARIZATION_PLAN.md`, `PLAN_NEXT_STEPS.md`, `HARNESS_GAP_ANALYSIS.md`, `CODEBASE_DUPLICATION_AND_MAPPING_REPORT.md`, `PRODUCTION_NAMING_CONVENTIONS_MAPPING.md`, `SKILL_STUDIO_AUDIT.md`, `SECURITY_REVIEW_2026-11-11.md`; root `BRANCH_README.md`, `UI_AUDIT_AND_AMBITION_REPORT.md`, root `USER_STORIES.md` (a copy of `docs/USER_STORIES.md`'s subject) | Replaced by `FINAL_PLAN.md`, `PHASE2_PLAN.md`, this plan and the architecture document; their open items are carried into section 4 first |
| Old evidence | `docs/evidence/runs/` folders from 2026-11-10 and 2026-11-11 (about 25 MB), the 39 tracked `ui-audit/*_prj_*` screenshots | Superseded by later runs; the final evidence set replaces them |
| Old launchers and tooling | `run.sh`, `run.bat`, `harness`, `harness.bat`, `bin/` (runs the retired `backend/cli.py`), `azure-pipelines.yml` (CI is GitHub Actions), root `playwright.config.ts`, root `package.json`/`package-lock.json`, `tests/e2e/production_screens.spec.ts` (TypeScript e2e not run anywhere) | `scripts/dev.py up`, `aqh` and the Python Playwright suite replace them |
| Activity log | `PROGRESS.md` is 12,700 lines, mostly hook log lines | Keep the Goal tracker; move the log to `data/` (not in git) |

## 3. Naming and English

One product name and one name per module, used the same way in the UI, API messages, documents and code comments.
Proposed (owner to confirm): product **Agentic QE Platform**; modules **Home, Projects, Harness, BA Studio, QE Cycle,
Skill Studio, MCP Servers, Approvals, Traces, Observability, Settings**; the command-line tool **aqh (Agentic QE
Platform CLI)**. Retire "Autonomous", "Enterprise QE", "AI SDLC", "Atlas" in visible text (the `ATLAS_` environment
names stay: renaming them breaks every deployment). A glossary goes in the developer guide, and a test fails on the
retired words in the UI.

## 4. Order of work

1. **Harness accuracy** A1 to A4 and A7, with tests; then the live run to Gate 5 on `personal-finance-mcp` with evidence (A5, A6).
2. **Size** (section 2) after the owner's yes.
3. **Naming and English** pass (section 3) over the UI, messages and documents.
4. **Feature test matrix with Playwright** (UI) and through the harness, each with a screenshot and a pass or fail line in one evidence report (`dev.py evidence`): sign-in and Home; feature access; projects and repository connect (git, ZIP, local folder); harness (plan and todos, file write with approval, bash, background task, skill, slash command, MCP tool, rewind); BA Studio (upload, brainstorm, BRD from a brief, Jira and Confluence stand-in); QE Cycle (G0 to G5 and the traceability view); Skill Studio (create, evaluate, publish); MCP Servers; Approvals; Traces; Observability; Settings; Users; Usage; Docs; desktop app; `aqh`.
5. **Two repositories**: the QE cycle to Gate 5 on `personal-finance-mcp` (public, cloned by the platform) and `mcp-server-market-v2` (private: cloned with the owner's existing `gh` sign-in into `data/` and bound as a local folder; no token is typed into the app); outputs verified: requirement quotes exist in the files, generated tests run in the repository's own environment, traceability has no invented links, verdicts follow the results.
6. **A skill per repository** made in Skill Studio from that repository's own documents, then tested by running the QE cycle with it.
7. **Gaps found by 4 to 6 fixed** in the UI and backend, each with a test.
8. **Deployment and guides**: local on macOS, Windows and Linux (`dev.py up`, CI proves it); Azure (`dev.py azure-local --check` locally; a real Azure deployment needs the owner's subscription and stays under the $25 a month cap); a new **Developer Guide** (setup, tests, CLI, desktop, Azure, troubleshooting) and a rewritten **README** with the end-to-end path.
9. Phase 2 step 13 (Azure guide, proposal workbook, documentation refresh) folds into 8.

## 5. Limits stated up front

- Azure: I cannot deploy to the owner's subscription; the deployment is checked locally with the Azure profile.
- Atlassian: the real server needs an Atlassian account; the stand-in proves the flow.
- Live runs use the model in the local store; token use and duration are recorded per run.
