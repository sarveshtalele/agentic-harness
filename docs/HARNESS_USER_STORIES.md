# Project Harness User Stories

Status: written 2026-11-10. Each story has acceptance criteria that code can check: an oracle that is not the model's own word. The "Result" column is filled from real runs (`docs/evidence/runs/`) and is never typed by hand without a run behind it.

Roles:
- **BA**: business analyst.
- **Dev**: developer.
- **QE**: quality engineer.
- **Admin**: platform administrator.

| ID | Story | Acceptance criteria (oracle) |
|---|---|---|
| HS-01 | As a BA, I ask the harness to plan a task, so that I see the steps before work starts. | A MAF todo list exists for the thread (`GET /api/chats/{thread}/todos` returns at least one item), and the todo panel on `/harness` shows it. |
| HS-02 | As a BA, I ask the harness to write a BRD from a brief, so that I get a governed requirements document. | A document of kind `brd` exists for the project, version 1, with SHA-256 and author. Either the BA workflow ran and is waiting at Gate 0, or `save_document` stored it. The harness never approves a gate. |
| HS-03 | As a Dev, I ask the harness to check the code, so that I know the real defects. | `scan_repository` ran; the reply's finding count equals the tool's count; each finding has file and line. |
| HS-04 | As a Dev, I ask the harness to run the tests, so that I know whether the suite passes. | `run_tests` ran with a registered runner. Counts come from JUnit. Zero executed is reported as INCONCLUSIVE. |
| HS-05 | As a QE, I ask the harness to plan tests using the QE method, so that the plan follows the agentic-qe skill. | `load_skill` was called with an agentic-qe method skill (for example `planning-tests`). The plan cites requirements or files that exist. |
| HS-06 | As a QE, I run an agentic-qe command (`/agentic-qe:qe-start`) from the harness, so that the plugin's gated lifecycle starts. | The command runs without a model turn first. The plugin's `.qe/` ledger is created only after the human types `approve gate 0`. |
| HS-07 | As a QE, I ask the harness to start a full QE run, so that tests are generated and executed in a sandbox. | `start_workflow` started a `qe` run. The run reaches Gate 1 for a human, and later executes more than 0 tests. |
| HS-08 | As a BA, I create a skill from a document in Skill Creator Studio, so that the team reuses the method. | The model proposes a task list, the user approves it, and then a skill folder is written that MAF `FileSkillsSource` loads. If the model fails, the user sees an error, not a keyword guess. |
| HS-09 | As a QE, I evaluate a created skill, so that I know whether it is safe and useful. | The evaluator runs on the real folder and reports spec, structure, and security findings with file and line. A skill that MAF cannot load fails. |
| HS-10 | As a Dev, I ask the harness to create a skill for me, so that I do not leave the chat. | The harness calls a skill-creation tool, which writes a draft only after my approval in chat. |
| HS-11 | As a QE, the harness delegates a sub-task to a specialist agent (sub-agent), so that long work runs in parallel. | `BackgroundAgentsProvider` starts a child agent (for example `test-design-architect`). Its result returns to the thread, and its tool calls are audited. |
| HS-12 | As an Admin, I control which plugins, skills, and MCP servers each user may use, so that governance holds. | An ungranted skill is absent from the model's list. Every grant change is in the ledger. |
| HS-13 | As any user, every model call and tool call in the harness is recorded, so that I can audit it. | Each round has an `agent_calls` row and each tool call has a `tool_calls` row. None of the harness's own tools is logged as refused. |
| HS-14 | As any user, the harness never shows invented output, so that I can trust it. | A missing model or repository gives a clear error. Tool-call text from the model ends the turn with `AQE-MODEL-TOOL-TEXT`. |

## Results, 2026-11-10

Run on the real model (deepseek-v4-flash-global), a real uploaded repository, and real tools. Live test: `tests/test_harness_stories_live.py`; recorded output: `data/evidence/harness-stories.json`. The browser check is E2E `test_13b`.

| ID | Result | Evidence |
|---|---|---|
| HS-01 | **Pass** | Two MAF todos created and completed (`mode_get`, `todos_add`, `todos_complete`); todo panel shown in the browser (E2E `test_13b`) |
| HS-02 | **Pass** | The harness called `start_workflow`; a `ba` run is `waiting_approval` at Gate 0. Nothing was approved |
| HS-03 | **Pass** | `scan_repository` ran; the reply names `calc.py` and the real `shell=True` finding |
| HS-04 | **Pass** | `run_tests` ran pytest in the sandbox; the reply's counts match JUnit (1 test) |
| HS-05 | **Pass** | `load_skill` (planning-tests), then `read_skill_resource` and real file reads |
| HS-06 | **Not built** | `qe-*` commands are hidden from the model and no command registry exists yet (P3b) |
| HS-07 | **Pass** | `start_workflow` started a `qe` run, which waits for a human at the gate |
| HS-08 | **Partial** | The suggestion came from the model (`source: model`); the created SKILL.md loads in MAF. The generated `scripts/run.py` reported every task PASSED without doing anything; fixed to report `NOT_IMPLEMENTED` and exit 2. The Studio keyword fallback was removed (D-18). Task-list approval is a UI step, not yet enforced in code |
| HS-09 | **Fail (real defect)** | `skills/evaluator/scripts/evaluate_skill.py` invents its scores: `recall = 95.0` always, groundedness from body length, a fixed 98 in the total, "A+ PRODUCTION READY". The live test now fails on this until the evaluator is rebuilt with measured checks and NVIDIA SkillSpector (P6) |
| HS-10 | **Not built** | The harness has no `create_skill` tool (P6) |
| HS-11 | **Not built** | No `BackgroundAgentsProvider` in the harness yet (P3b) |
| HS-12 | **Not built** | No admin grants yet (P5) |
| HS-13 | **Pass** | `agent_calls` and `tool_calls` rows for every round and tool (offline tests; tool lists recorded live) |
| HS-14 | **Pass** | Offline tests: "No model configured", NotScanned or INCONCLUSIVE without a repository, `AQE-MODEL-TOOL-TEXT` |
