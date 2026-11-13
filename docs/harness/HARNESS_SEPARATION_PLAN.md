# Harness separation and rebuild plan

Owner request, 2026-11-13: detach the harness from Agentic QE Platform completely; the platform runs without it; move
all harness code to a new folder; build a new, separate harness application on Microsoft Agent Framework (MAF), like
Claude Desktop or Codex, from a clean design that avoids every mistake made so far. Plan first, then migrate. After the
harness is removed, prove the platform is not broken: the full unit and integration suite, the browser smoke tests and a
final end-to-end run with screenshot evidence.

The design of the new harness is in `docs/harness/HARNESS_ENGINEERING.md`. This document is the migration.

## 1. Where things stand

| Branch | Holds | State |
|---|---|---|
| `feature/maf-harness-platform` | The platform with the current harness | Stable, pushed (`252f499`); last full suite 777 passed; BRD end-to-end passed live (108 s) |
| `feature/harness-rebuild` (new) | Harness work in progress (read cache, smaller plugin-step tool surface, shell starts at the workspace root) and this plan | Targeted tests pass; full suite not run on it |
| `main` | The owner's backup of a separate project | Never touched |

## 2. What the harness is today (inventory)

| Area | Paths | Size |
|---|---|---|
| Agent and kit | `src/backend/maf/harness.py`, `src/backend/maf/harness_kit/` (31 files), `src/backend/maf/agents/harness.py`, `src/backend/maf/unique_calls.py` | about 2,700 lines |
| AG-UI hosting for the harness | the harness branch of `src/backend/maf/agui.py`, `harness_kit/snapshots.py` (approval and thread snapshot stores) | part of 190 lines |
| Command-line tool | `src/aqh/` | 5 modules |
| Desktop app | `apps/desktop/` (Electron, Terminal pane) | about 1,000 lines plus build |
| Web UI | `src/frontend/app/harness/`, `src/frontend/components/MafHarness.tsx`, `TerminalPane.tsx`, harness parts of `features/chat/` | |
| Prompts, evals | `prompts/harness.md`, `evals/harness.json`, `evals/harness/` | |
| Plugin used through the harness | `plugins/agentic-qe` (slash commands run only in the harness) | pinned copy |
| Tests | 30 files: `test_harness_*`, `test_maf_harness*`, `test_aqh_cli`, `test_unique_call_ids`, `test_plugin_contract_r5`, `test_os_sandbox`, `test_credentials_r6`, `test_desktop_signin`, `tests/desktop/`, `test_discovery_eval_scoring`, `test_qe_cycle_live`, `helpers_harness.py` | |

**Coupling points in the platform** (each must be cut or replaced):

| Platform file | Uses the harness for | After separation |
|---|---|---|
| `src/backend/maf/agui.py` | builds the harness agent for `/agui/harness` | harness branch removed; other chat agents unchanged |
| `src/backend/api/chat.py` | `/api/chats/{id}/todos`, terminal | harness-only routes removed |
| `src/backend/api/projects/crud.py` | deletes the harness folder with a project | line removed |
| `src/backend/api/projects/__init__.py` | imports `harness` to register it | import removed |
| `src/backend/core/registry/code_sources.py` | `RISKY` from `harness_kit/catalog.py` | the list moves to `core/registry` (platform tools still need it) |
| `src/backend/config.py` | harness settings (`ATLAS_HARNESS_*`) | removed |
| `src/backend/core/auth/features.py` and `rules.py` | the `harness` feature and its routes | feature and routes removed; roles keep the rest |
| Frontend nav, Home, project cards, landing, desktop downloads | links to the Harness and the desktop app | links removed, or pointed at the separate harness app when it exists |
| `deploy/`, `scripts/dev.py`, `scripts/desktop_build.py`, `.github/workflows/desktop.yml` | desktop build and harness settings | move with the harness |

**What the platform keeps and must keep working:** Home, Projects (Git, ZIP, local folder), BA Studio (upload,
brainstorm, BRD, Jira and Confluence), QE Cycle through the platform's own workflow (`maf/workflows/qe*`, gates G0 to G5,
traceability view from the platform's own data), Skill Studio, MCP Servers, Approvals, Traces, Observability, Settings,
Users, Usage, the ledger and the document store.

**One decision for the owner:** the QE Cycle page's traceability view reads the agentic-qe plugin's `coverage-map.json`,
which only the harness writes. Without the harness it shows the platform workflow's own traceability (requirement,
scenario, case, test, result), which already exists. Proposed: keep the platform workflow's view; the plugin's view moves
to the harness app.

## 3. The new harness application

| Item | Proposal (owner to confirm) |
|---|---|
| Location | A new sibling folder and Git repository, `~/Downloads/maf-harness` (outside this repository, so it needs the owner's yes). The new repository gets its own `CLAUDE.md` with these rules |
| Shape | One harness core library on MAF; three clients over one session API: CLI (`aqh`), desktop (Electron, like Claude Desktop) and web. Hexagonal: ports for model, tools, store, sandbox, UI |
| What moves | Code is copied, not moved, into `legacy/` of the new repository as a read-only reference with a provenance note (source commit). Each piece is ported into the new design only with its tests |
| What is rebuilt | The turn loop, approvals, context building, tool surface and step control: these caused the failures (see `HARNESS_ENGINEERING.md` section 2) |
| What is ported nearly as is | Shells (with the root-start fix), OS sandbox (Seatbelt, bubblewrap), permission rules and modes, settings files and hooks, plugin hooks and contracts (`describe_contract`, `check_gate`), checkpoints and rewind, OAuth for MCP, the desktop sign-in and Terminal pane |
| Connection to the platform | None at first: the harness is a separate product. Later, optional: the harness can sign in to a platform server to read projects and post results through the platform's public API |

## 4. Order of work (each step ends green before the next starts)

| Step | Work | Proof |
|---|---|---|
| S0 | Freeze: stable branch untouched; work in progress on `feature/harness-rebuild` (done) | both branches pushed |
| S1 | This plan and `HARNESS_ENGINEERING.md`; owner approves location, scope and the deletion list (section 5) | owner's yes |
| S2 | Create the new repository: skeleton, `CLAUDE.md`, CI on 3 OS, `legacy/` copy with the source commit | CI green on an empty core |
| S3 | Strangler, step 1, in the platform: a `harness` switch that is off by default; with it off, no harness route, page, setting or import is loaded | full suite, smoke and BRD end-to-end green with the switch off |
| S4 | Remove the harness from the platform (after the owner's yes on the exact file list): delete the files in section 5, cut the coupling points in section 2 | see section 6, the final gate |
| S5 | Build the new harness core: turn state machine, session event log, request builder, tool registry and guard chain, model gateway, step contract (design document sections 3 to 6) | unit tests with recorded live transcripts as fixtures |
| S6 | Port shells, sandbox, permissions, hooks, plugins, checkpoints, MCP; then the CLI, then desktop, then web | each with its own tests; desktop Electron test |
| S7 | Live acceptance: the agentic-qe cycle to Gate 5 on `personal-finance-mcp` and `mcp-server-market-v2`, each stage measured | every stage 180 s or less, 40 tool calls or fewer, Gates 0 to 5 in the plugin ledger, evidence folder |

## 5. Deletion list for S4 (needs the owner's explicit yes; nothing is deleted before it)

Platform files removed after they are copied to the new repository: `src/backend/maf/harness.py`,
`src/backend/maf/harness_kit/`, `src/backend/maf/agents/harness.py`, `src/backend/maf/unique_calls.py`, `src/aqh/`,
`apps/desktop/`, `src/frontend/app/harness/`, `src/frontend/components/MafHarness.tsx`,
`src/frontend/components/TerminalPane.tsx`, `prompts/harness.md`, `evals/harness.json`, `evals/harness/`,
`scripts/desktop_build.py`, `.github/workflows/desktop.yml`, `docs/DESKTOP_APP_GUIDE.md`, `docs/DESKTOP_RELEASE_GUIDE.md`,
`docs/HARNESS_USER_STORIES.md`, `docs/HARNESS_MEMORY_AND_TOOLS.md`, the 30 harness test files listed in section 2, and
`plugins/agentic-qe` (it only runs in the harness; the platform's QE workflow does not use it). The 11 platform skills
that duplicate the plugin's stay with the platform's QE workflow.

Edited, not deleted: the coupling points in section 2, `README.md`, `docs/DEVELOPER_GUIDE.md`,
`docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md`, `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`, `docs/PROJECT_STRUCTURE.md`
(regenerated), `CLAUDE.md` (harness rules move to the new repository; D-SHELL leaves with them).

## 6. Final gate after removal (the owner's condition)

All on the platform branch, with the harness removed, real output recorded in one evidence report
(`docs/evidence/runs/<date>-platform-without-harness/`):

1. `python scripts/dev.py test`: the whole unit and integration suite; zero failures; the count is reported.
2. `python scripts/dev.py smoke`: browser smoke tests.
3. A new end-to-end check that no harness route, page or link remains: `/agui/harness` and `/api/harness/*` answer 404,
   the navigation has no Harness entry, Home and project pages render without errors (screenshots, light and dark).
4. `tests/e2e/test_ui_audit.py`: every page on desktop light, desktop dark and phone, zero findings.
5. End to end on the real model with screenshots: BA Studio brainstorm to a signed BRD with Markdown and Word export
   (`tests/e2e/test_ba_brainstorm_brd.py`); QE Cycle through the platform workflow from G0 to G5 on a real repository;
   Skill Studio create and publish; MCP Servers connect; Approvals, Traces, Observability, Settings, Users and Usage pages.
6. `python scripts/dev.py up` from a fresh clone on macOS; CI on Windows, macOS and Linux green.
7. `python scripts/dev.py azure-local --check` prints `API health: 200; UI /login: 200`.

A step that cannot run (for example the model endpoint answering HTTP 429) is reported as not run, never as passed.

## 7. Risks

| Risk | Handling |
|---|---|
| Something in the platform imports harness code indirectly | S3 runs the whole suite with the switch off before anything is deleted; an import check in CI fails on any `harness` import |
| The QE Cycle page loses the plugin's traceability | the platform workflow's own traceability view stays; decision in section 2 |
| Desktop users lose the app | the desktop app moves to the new repository; the platform stops offering its download until the new app is released |
| Model quota (HTTP 429) blocks live runs | live steps are scheduled after the daily reset; the cause is recorded in the evidence |
| History of the moved code | the `legacy/` copy records the source commit; `git log` of this repository keeps the full history |
