# Stable build plan: cloud-only Agentic QE Platform without the harness

Owner decisions, 2026-11-13 (asked and answered in the session):

| Question | Decision |
|---|---|
| Product shape | Cloud only (Azure). No desktop app, no command-line tool, no harness in the stable build. Local runs (`dev.py up`) stay for development and testing only |
| Removal | Delete the harness, the desktop app and the `aqh` CLI from `feature/maf-harness-platform` (list in `docs/harness/HARNESS_SEPARATION_PLAN.md` section 5). Everything removed stays on the `sarveshtalele/maf-harness` repository (`legacy/`). **Exception: `plugins/agentic-qe` stays**, because the QE Cycle now uses its skills |
| QE Cycle engine | The platform's own MAF workflow runs the stages in a fixed order. Each stage loads the agentic-qe plugin's skill (any language), runs its scripts, and validates the output with the plugin's checks; a named person signs each gate |
| Repository code on Azure | Runs in the backend App Service through the allowlisted runner, with timeouts and a workspace per project. Cost stays about $21 a month. Only trusted members until sandbox jobs exist |
| Node on Azure | `startup.py` downloads a pinned Node 22 LTS (checksum verified) into `/home` once |
| Languages executed on Azure | Python, JavaScript/TypeScript, Java, .NET and Go. Toolchains (JDK, .NET SDK, Go) are downloaded on demand into `/home`, checksum verified, the first time a repository in that language reaches Execute |
| Harness | Re-planned after the stable build, on MAF, from Birgitta Böckeler's "Harness engineering for coding agent users" (martinfowler.com, 2 April 2026) |

Priority: the QE Cycle end to end, with validation at every stage. Then the whole stable build verified end to end with
screenshots, and the Azure guide updated.

## Part A. Remove the harness, desktop app and CLI

1. Cut the coupling points (separation plan section 2): `maf/agui.py` harness branch, `/api/chats/{id}/todos` and
   terminal routes, `projects/crud.py` harness folder, `projects/__init__.py` import, `RISKY` moves to
   `core/registry`, `ATLAS_HARNESS_*` settings, the `harness` feature and its access rules, navigation, Home, project
   cards, landing page and desktop downloads.
2. Delete the files in the separation plan's section 5, except `plugins/agentic-qe`.
3. Update `README.md`, `docs/DEVELOPER_GUIDE.md`, `CLAUDE.md` (the D-SHELL exception leaves with the harness),
   `docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md`, `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`, and regenerate
   `docs/PROJECT_STRUCTURE.md`.
4. Gate: `dev.py test` with zero failures; `dev.py smoke`; a new test that `/agui/harness` and `/api/harness/*` answer
   404, no page links to the harness, and nothing under `src/` imports harness code; the UI audit with zero findings.

## Part B. QE Cycle on the agentic-qe plugin

The design follows the article's model: **guides** (feedforward) steer a stage before it acts, **sensors** (feedback)
check it after, each either **computational** (deterministic, cheap, every time) or **inferential** (model judgement,
used where only judgement can tell). The human signs the gate.

### B1. One stage, the same shape every time

```
guides:   plugin skill text + references + the file contract (field names from describe_contract)
          + facts already measured (stack, files, earlier stage outputs)
run:      deterministic scripts first (scan-repo, extract-contracts, generate-cases, emit-tests, run-isolated...)
          then one model task that writes the stage's plugin files (docs/qe/<app>/<phase>/...)
sensors:  computational: contract check, quotes checked against disk, check-gate.ts for the gate,
          qe_validate.py (pandas/numpy coverage, duplicates, drift), Gherkin parser, the tests actually run
          inferential: the plugin's reviewer agents (confidence-reviewer, coverage-auditor) where the plugin uses them
fix:      the sensors' messages go back to the model, at most two fix rounds; a third failure stops the stage
          with the sensor output shown, never a faked pass
gate:     the platform's approval card with the sensor verdicts; a named person signs; the plugin ledger records it
```

Budget per stage: 180 seconds and the model calls the stage needs (no open-ended loop); every run records seconds, model
calls, tokens, cache hits and sensor results.

### B2. Stages

| Gate | Stage | Plugin skill (guide) | Scripts (computational) | Sensors |
|---|---|---|---|---|
| G0 | Intake | qe-start | repository facts, mode (brownfield/greenfield) | run.json written by the plugin's approval hook logic |
| | Discover | qe-discover, analyzing-repositories | `scan-repo.ts` | architecture.json and summary contract; every cited file exists |
| G1 | Requirements | qe-requirements, extracting-requirements | `extract-contracts.ts` | contract check; quotes verified on disk; `check-gate.ts --gate 1` |
| G2 | Plan | qe-plan, planning-tests | | plan contract; `check-gate.ts --gate 2`; `qe_validate.py` |
| | Design | qe-design, designing-test-cases | `generate-cases.ts`, `check-confidence.ts` | cases contract; coverage of every scenario |
| G3 | Data | qe-data, generating-test-data | `synthesize-data.ts` | `check-gate.ts --gate 3`; `qe_validate.py` |
| G4 | Generate | qe-generate, generating-test-code | `emit-tests.ts` | tests compile or parse in the repository's toolchain; one test per case; `check-gate.ts --gate 4` |
| | Execute | qe-execute, executing-tests | `run-isolated.ts`, `parse-junit.ts`, `collect-evidence.ts` | real results from JUnit; zero executed is INCONCLUSIVE |
| | Heal | qe-heal, healing-tests | | only selectors and fixtures change; a real defect stays failing |
| | Trace | qe-trace, tracing-coverage | `build-trace-report.ts` | requirement to scenario to case to test to result; no invented links |
| G5 | Sign | qe-sign | `gate-report-md.ts` | `check-gate.ts --gate 5`; verdict follows the results |

The existing platform stages (`maf/workflows/qe/*`) are kept as the frame (gates, documents, ledger, approvals) and
changed to load the plugin skill, run the scripts and apply the sensors above. The plugin's files and ledger are written
in the project workspace, so the traceability view reads them.

### B3. Running code on Azure

- Node 22 LTS downloaded by `startup.py` into `/home/tools/node`, checksum verified.
- Python validator environment (pandas, numpy) created once in `/home/tools/qe-py`.
- On demand at Execute: Temurin JDK 21, .NET SDK 8, Go 1.22 into `/home/tools/<name>`, checksum verified; repository
  dependencies installed in the repository's own environment in its workspace (`.venv`, `node_modules`, Maven or Gradle
  cache, NuGet cache, Go module cache).
- Limits stated in the guide: B1 has 1.75 GB of memory and `/home` 10 GB; a large Java or .NET build may run slowly or
  fail for memory, and the run then says so. A bigger plan would raise the cost and needs the owner's yes.

### B4. Pilot: Requirements on the plugin (offline done 2026-11-14; live run pending)

One stage end to end before the others, through a small bridge, `src/backend/qe/plugin_bridge.py`:

| Part | What it does |
|---|---|
| Guide | the stage's plugin skill text (`qe-requirements`, `extracting-requirements` and its `REQUIREMENT_RULES.md`) goes into the requirements analyst's prompt, ahead of the code |
| Plugin files | the verified requirements are written as the plugin's `docs/qe/<app>/02-requirements/requirements.json` (`id`, `title`, `text`, `priority`, `source_file`, `line_number`, `quote`) in the project workspace; `<app>` is the project's name as a slug |
| Sensor (computational) | the plugin's own `check-gate.ts --gate 1 --json` runs on the workspace (Node, argument list, timeout); it re-checks every quote on disk and runs the pandas/numpy validator |
| Fix | requirements the sensor flags (no evidence, quote not found) are dropped and the check runs again, once; anything still failing is shown to the person at Gate 1, never hidden |
| Gate | the Gate 1 card shows the plugin's verdict (PASS or FAIL with its gaps) next to the existing reviewer score |
| Validator environment | the plugin's `qe-doctor` installer creates its pandas/numpy environment once under `data/qe-plugin-home` (local) or `/home/tools/qe-py` (Azure, B3) |

When the pilot passes its tests and a live run, the same bridge carries Plan (G2), Design and Data (G3), Generate (G4) and
Sign (G5), each with its own plugin skill, scripts and gate check.

Plan (G2), 2026-11-14: each plan area becomes a plugin scenario `SC-<AREA>-001` with its level and requirement ids, and
skipped levels keep their reasons, in `docs/qe/<app>/03-plan/plan.json`. `check-gate.ts --gate 2` runs on it. Its gaps go
back to the architect once, for example a missing level or a skipped level whose reason is under 10 characters. The fix is
kept only when it does not lower the deterministic plan score, and the verdict is shown on the G2 card. Live QE run:
`tests/test_qe_platform_live.py`, run with `python scripts/dev.py live`.

Limit: greenfield requirements cite approved documents, not code, so the plugin's quote check is recorded as not applied
for them. Evidence: `tests/test_plugin_bridge.py` (real `check-gate.ts`: a real quote passes, an invented one is flagged)
and the G1 assertions in `tests/test_api_change.py`.

## Part C. Verification (the owner's condition)

On the stable branch, real output in one evidence folder (`docs/evidence/runs/<date>-stable-build/`):

1. `dev.py test` (the whole unit and integration suite) and `dev.py smoke`.
2. The harness-removed check (Part A, step 4) and the UI audit (every page, light, dark, phone).
3. End to end on the real model, in the browser, with screenshots:
   - BA Studio: brainstorm to a signed BRD, Markdown and Word export;
   - QE Cycle: G0 to G5 on `personal-finance-mcp` (Python) and on `mcp-server-market-v2` (bound as a local folder);
     every stage's sensor results and seconds recorded;
   - QE Cycle on one small JavaScript, one Java, one .NET and one Go repository, through Execute;
   - Skill Studio create and publish; MCP Servers; Approvals; Traces; Observability; Settings; Users; Usage.
4. `dev.py azure-local --check` (API health 200, UI login 200), including the Node download.
5. CI green on Windows, macOS and Linux.

A step that cannot run (for example the model endpoint answering HTTP 429) is reported as not run.

## Part D. Azure guide

Update `docs/AZURE_DEPLOYMENT_GUIDE.md`: no desktop downloads container; the toolchain downloads and their disk use;
the runner and its limits; the trusted-members note; cost unchanged (about $21 a month).

## Part E. Then: the harness, re-planned

After Part C passes, rewrite the harness plan on MAF using the article's model (guides and sensors, computational and
inferential, keep quality left, regulation categories, harnessability, harness templates, the human's role), together
with the 15 measured mistakes in `docs/harness/HARNESS_ENGINEERING.md`.

## Order

A, then B (stage by stage, each with its tests and a live check), then D, then C, then E. Each part ends with the suite
green, a commit and a push, and the Goal tracker updated.
