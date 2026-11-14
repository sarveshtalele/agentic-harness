# Harness plan (version 2): a QE harness on MAF built as a system of guides and sensors

Status: plan for owner review, 2026-11-14. The stable Agentic QE Platform ships without a harness
(`docs/STABLE_BUILD_PLAN.md`). This plan is for the separate harness application. It builds on three sources:

1. **The 15 measured mistakes** of the embedded harness: `HARNESS_ENGINEERING.md` section 2.
2. **The harness pattern catalogue** the owner shared: patterns per part, `HARNESS_ENGINEERING.md` section 4.
3. **Birgitta Böckeler, "Harness engineering for coding agent users"** (martinfowler.com, 2 April 2026). Its mental
   model is used here as the organising idea; the wording below is ours.

## 1. What changed in our thinking

The first plan treated the harness as a better agent loop: fewer tools, a cache, a state machine. Those are needed, but
they were not why it failed. It failed because **nothing told the model what good output looked like before it acted,
and nothing checked the output cheaply while it worked**. The model wandered for 20 minutes because the only check was a
human at the gate.

The article separates three layers: the model; the **builder harness** (what a coding-agent product ships: loop, tools,
context handling); and the **user harness** (what a team adds for its own codebase). Our product has to be both: a lean
builder harness, plus a first-class way to define, run and improve the user harness for each repository and each QE
stage. The user harness is where accuracy comes from.

## 2. The control model

Every control in the harness is one of four kinds:

| | Computational (deterministic, cheap, every time) | Inferential (model judgement, slower, used where only judgement can tell) |
|---|---|---|
| **Guide** (before the agent acts) | measured repository facts; the plugin's file contracts; language server and type information; scripts that produce part of the output (scan, extract, generate) | skills and their references; the repository's `CLAUDE.md` / `AGENTS.md`; the stage's instructions; examples of good output |
| **Sensor** (after the agent acts) | tests run for real; linters and type checkers; quotes checked against disk; the Gherkin parser; `check-gate.ts`; `qe_validate.py`; coverage and mutation testing of generated tests | reviewer agents (confidence reviewer, coverage auditor); a judge model on a rubric |

Rules:

- **Sensor output is written for the model.** Every sensor message says what is wrong, where, and how to fix it, in one
  short block. A failing check that only says "FAIL" is a defect in the harness.
- **Both directions, always.** A stage with guides but no sensors repeats mistakes it never learns about; a stage with
  sensors but no guides fails first and fixes later, burning time. Every stage has at least one of each.
- **Computational first.** A deterministic check runs before any inferential one; an inferential sensor is added only
  where no deterministic check can tell.

## 3. Keep quality left: where each sensor runs

| When | Sensors | Budget |
|---|---|---|
| After every write (inside the turn) | file contract, quote check, parser, linter on the changed file | milliseconds to seconds |
| End of a step | the plugin's `check-gate.ts`, `qe_validate.py`, the generated tests compiled and run | under 60 seconds |
| At a gate | reviewer agents, then the named person | minutes, once per gate |
| Continuously, outside a run | drift: traceability gaps, dead tests, flaky tests, dependency changes | nightly |

A finding moves left when it can: if reviewers keep finding the same problem at a gate, it becomes a computational
sensor at the end of the step, or a guide before it.

## 4. The steering loop (how the harness improves)

The owner's job, and the harness team's, is to steer by changing controls, not by retrying prompts:

1. Every run records which sensors fired, how often, and what the human changed at the gate.
2. A problem seen twice gets a new or better control: a guide (skill text, example, contract field) or a sensor (a
   check, a linter rule, a test).
3. Each control has an owner, a version and a test (a seeded mistake it must catch). Controls are code: reviewed,
   versioned, rolled back.
4. The harness reports **harness coverage**: the share of seeded defects its sensors catch, per stage. This answers the
   article's open question "if a sensor never fires, is the work good or the sensor blind?"

## 5. Three regulation categories for QE

| Category | What it keeps right | Guides | Sensors |
|---|---|---|---|
| Maintainability | generated test code is clean and idiomatic for its language | the language's test conventions; the repository's style | linters, formatters, duplication and complexity checks on generated tests |
| Architecture fitness | tests respect the repository's structure and run in its toolchain | measured layout, test runner, fixtures in use | tests run in the repository's own environment; structural checks (one test per case, files where the runner finds them) |
| Behaviour (the hard one) | the tests check what the requirements say | requirements with quotes from the code; approved BRDs and Gherkin | quote verification; traceability with no invented links; **mutation testing of the generated tests** (a test that survives a mutant does not check behaviour); the human at G1 and G4 |

Behaviour is where the harness is weakest, as the article says. Two concrete moves: mutation testing as a sensor on
generated tests, and approved fixtures (expected outputs a person signs once and the tests compare against).

## 6. Harnessability and harness templates

- **Assess at intake.** Score each repository on what the harness can use: types, a test runner, clear module
  boundaries, a lock file, existing tests. The score decides the mix: a well-typed, well-tested repository leans on
  computational sensors; a legacy one gets more inferential sensors and more human review, and the run says so.
- **Harness templates per topology.** One bundle of guides and sensors per common stack: Python service (pytest),
  Node or TypeScript web (vitest or jest), Java with Spring (JUnit 5, Maven or Gradle), .NET (xUnit), Go (`go test`). Each
  template pins its toolchain, test runner, linters, conventions and checks. This is also how "any language" stays
  manageable: a template narrows what the agent may produce, so the controls can cover it.

## 7. The human's role

People sign the gates, choose what the harness should regulate, and review where sensors are weak: misdiagnosis,
over-engineering, misunderstood requirements. The harness aims to spend human attention there, not to remove it. Gates
G0 to G5 stay human, as in the platform.

## 8. Architecture (builder harness)

Lean, as designed in `HARNESS_ENGINEERING.md` sections 3 to 7, plus one new core part:

| Part | Responsibility |
|---|---|
| Turn state machine | Idle, CallingModel, AwaitingApproval, RunningTool, StepCheck, Done; approvals owned by the core |
| Session event log | append-only, resumable after a crash, a model fault or HTTP 429; replay for tests |
| Request builder | stable prefix (tools, system), history, pinned step facts last; prompt-cache friendly |
| Tool registry and guard chain | about 15 tools per mode; deferred catalogue; aliases; path guard, sandbox, approval |
| **Controls engine (new)** | loads the guides for a step (skills, contracts, facts) and runs its sensors at the right time (after a write, at step end, at a gate); turns sensor output into model-ready fix messages; records every firing for the steering loop |
| Step contract | done = the step's files exist and its sensors pass; budget 180 s and 40 tool calls |
| Model gateway | retry with Retry-After, stall detection, circuit breaker, typed cost |

MAF primitives used: chat clients, `@tool` and MCP tools, function and chat middleware (sensors after writes), context
providers (guides), compaction strategies, skills sources, AG-UI for the web client. Not used: `create_harness_agent`'s
todo loop and AG-UI's collected-approval store (mistakes M4 and M8).

## 9. Phases

| Phase | Delivers | Proof |
|---|---|---|
| H0 | New repository from `feature/harness-rebuild`, CI on 3 OS, `legacy/` reference copy | CI green on the skeleton |
| H1 | Core: state machine, event log, request builder, model gateway | unit tests; replay of recorded live sessions |
| H2 | Tool registry, guard chain, sandbox, shells (root start), permissions, hooks | the existing ported tests |
| H3 | Controls engine with the computational sensors for the agentic-qe stages (contracts, quotes, Gherkin, check-gate, validator, test runs) | each sensor catches its seeded defect |
| H4 | Harness templates for Python, JS/TS, Java, .NET, Go | a sample repository per template through Execute |
| H5 | Inferential sensors (reviewers, judge) and mutation testing of generated tests | harness coverage report per stage |
| H6 | Clients: CLI first, then the others the owner chooses | client tests |
| H7 | Live acceptance: the QE cycle to Gate 5 on `personal-finance-mcp` and `mcp-server-market-v2` | every stage 180 s or less, 40 tool calls or fewer, Gates 0 to 5 in the plugin ledger, harness coverage reported |

## 10. Decisions needed from the owner before H0

1. **Location:** a new repository folder `~/Downloads/maf-harness` (outside this repository) or another place.
2. **Clients:** CLI only first, or CLI and web, or CLI, web and desktop.
3. **Relation to the platform:** fully separate, or able to sign in to a platform server later to read projects and post
   results through its public API.
