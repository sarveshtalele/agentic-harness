---
name: qe-plan
description: "Formulate a risk-weighted test strategy across Unit, Integration, API, and UI/E2E levels without cross-level duplication. Use when the user runs /agentic-qe:qe-plan or $qe-plan."
argument-hint: "<app-name> [--risk-priority P0|P1|P2]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-plan
Invoke: `/agentic-qe:qe-plan` (Claude Code) or `$qe-plan` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flag: `--risk-priority P0|P1|P2` (default: all priorities). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-plan <app-name> [--risk-priority P0|P1|P2]
```

## What it does
1. Activates `planning-tests` skill and invokes `principal-test-architect`.
2. Evaluates approved requirements against risk dimensions (business impact, change volatility, blast radius).
3. Allocates scenarios to the lowest test level that can prove the behavior:
   - **Unit:** Pure logic, calculations, data transformations, parsing.
   - **Integration / API:** HTTP routes, persistence, state transitions, external contracts.
   - **UI / E2E:** Critical user journeys, DOM interaction, client authentication.
4. Every plan allocates Unit, Integration and E2E cases; a level may be skipped only with a written reason in the plan (e.g. "no UI").
5. Invokes `confidence-reviewer` to independently score control coverage, level fit, and scenario derivability.
6. Generates `docs/qe/<app-name>/03-plan/strategy.md` and `docs/qe/<app-name>/03-plan/plan.json`. `plan.json` **lists every scenario**, never only a count: `"scenarios": [{ "id": "SC-<AREA>-001", "area": "<area>", "level": "Unit|Integration|E2E", "priority": "P0", "requirementIds": ["REQ-…"], "title": "…" }]`, plus `"totalScenarios"` equal to the list's length and `"skippedLevels": [{ "level": "E2E", "reason": "…" }]` for any level left out. Every P0 and P1 requirement is in at least one scenario's `requirementIds`. The next phases are checked against this list, scenario by scenario.
7. Runs `node "${CLAUDE_SKILL_DIR}/../tracing-coverage/scripts/check-gate.ts" --gate 2 --app <app-name>` and shows its output. While it prints FAIL, fix the plan; do not ask for approval.
8. Enforces **Gate 2 (Plan)**: the user reviews the test area distribution and types `approve gate 2 for <app-name>`.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command ends at Gate 2 (Plan). The user approves by typing the whole message `approve gate 2 for <app-name>` and rejects with `reject gate 2`; the plugin's UserPromptSubmit hook records only these exact messages. The live dashboard (started by the plugin at Gate 0) shows the gate, its documents and the next command, and updates as files change.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/03-plan/strategy.md`, `docs/qe/<app-name>/03-plan/plan.json`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-design <app-name>
```
