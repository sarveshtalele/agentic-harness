---
name: qe-design
description: "Design structured test cases with positive, negative, exception, and boundary value scenarios using 4 deterministic test oracles. Use when the user runs /agentic-qe:qe-design or $qe-design."
argument-hint: "<app-name> [--technique ep|bva|state|decision]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-design
Invoke: `/agentic-qe:qe-design` (Claude Code) or `$qe-design` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flag: `--technique ep|bva|state|decision` (default: all four techniques). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-design <app-name> [--technique ep|bva|state|decision]
```

## What it does
1. Activates `designing-test-cases` skill and invokes `test-design-architect`.
2. Applies ISTQB techniques: Equivalence Partitioning, Boundary Value Analysis, State Transition, Combinatorial testing.
3. For every user story and requirement, designs:
   - At least 1 Positive test case.
   - 2 to 3 Negative test cases.
   - 1 Exception / error handling test case.
   - Boundary value test cases (min, max, nominal, just-below, just-above).
4. Tags each case with a `level` (Unit, Integration or E2E) in the JSON; a level may be skipped only with a written reason in the plan (e.g. "no UI").
5. Assigns deterministic oracles (`specified`, `derived`, `metamorphic`, `golden`).
6. Generates `docs/qe/<app-name>/04-design/test_cases.json` and `docs/qe/<app-name>/04-design/test_cases.md`. **Every plan scenario gets at least one case**, in every area and at every level the plan allocates (a plan of 109 scenarios is not designed with 26 cases). Each case names what it covers: `"planScenarioIds": ["SC-<AREA>-001"]`. Work area by area when there are many; the hand-off the plugin puts in your context lists the scenarios still without a case.
7. Invokes `confidence-reviewer` on **every case** (once per area when there are many). Its final answer is recorded by the plugin as `04-design/confidence.json`; **never write or edit that file yourself**: the write guard refuses it and the gate refuses a file written any other way. Run `check-confidence.ts`, fix REVISE and REJECT cases, and call the reviewer again for them.
8. Invokes `coverage-auditor` with `kind: design` on every case: it checks that each case really covers the scenario it names. Its answer is recorded as `04-design/audit.json`. Fix every PARTIAL or MISSES case and audit it again.
9. Runs `node "${CLAUDE_SKILL_DIR}/../tracing-coverage/scripts/check-gate.ts" --gate 3 --app <app-name>` and shows its output. While it prints FAIL, do the missing work; do not ask for approval.
10. Enforces **Gate 3 (Design)**: shows each case's confidence and any remaining REVISE or REJECT case with its reason and fix; the user reviews the cases and types `approve gate 3 for <app-name>`.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command ends at Gate 3 (Design). The user approves by typing the whole message `approve gate 3 for <app-name>` and rejects with `reject gate 3`; the plugin's UserPromptSubmit hook records only these exact messages. The live dashboard (started by the plugin at Gate 0) shows the gate, its documents and the next command, and updates as files change. Gate 3 covers the test cases and, if `/agentic-qe:qe-data` was run, the fixtures.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/04-design/test_cases.json`, `docs/qe/<app-name>/04-design/test_cases.md`. The plugin writes `04-design/confidence.json`, `04-design/audit.json`, `coverage-map.md`, `handoff.md` and the gate report; never write those. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-data <app-name>       # if cases need generated fixtures or schema mocks
/agentic-qe:qe-generate <app-name>   # if every case already carries concrete test data
```
