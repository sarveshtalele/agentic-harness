---
name: qe-trace
description: "Build the requirements-to-tests-to-results traceability matrix and flag unmapped P0/P1 requirements and orphan tests. Use when the user runs /agentic-qe:qe-trace or $qe-trace."
argument-hint: "<app-name>"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-trace
Invoke: `/agentic-qe:qe-trace` (Claude Code) or `$qe-trace` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). No flags. If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-trace <app-name>
```

## What it does
1. Activates the `tracing-coverage` skill.
2. Reads `docs/qe/<app-name>/02-requirements/requirements.json` (or `02-requirements/user_stories.md` in greenfield), `docs/qe/<app-name>/04-design/test_cases.json`, and the JUnit XML in `results/`.
3. Maps each requirement to its test cases (by `// CASE_ID:` markers) and each test case to its executed result.
4. Flags unmapped P0/P1 requirements, orphan tests with no requirement, and failing tests.
5. Writes `docs/qe/<app-name>/08-traceability/matrix.json`.
6. Traceability check (not an approval gate): every P0/P1 requirement maps to at least one executed test. If it fails, lists the unmapped requirements and stops.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command has no gate.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/08-traceability/matrix.json`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-sign <app-name>
```
