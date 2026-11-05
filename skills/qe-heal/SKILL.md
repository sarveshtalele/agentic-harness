---
name: qe-heal
description: "Automatically diagnose test execution failures and heal broken selectors, fixtures, or mocks while strictly preserving assertions. Use when the user runs /agentic-qe:qe-heal or $qe-heal."
argument-hint: "<app-name> [--test-id <test-case-id>] [--max-attempts 3]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-heal
Invoke: `/agentic-qe:qe-heal` (Claude Code) or `$qe-heal` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flags: `--test-id <test-case-id>` (default: all failing tests), `--max-attempts <n>` (default `3`). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-heal <app-name> [--test-id <test-case-id>] [--max-attempts 3]
```

## What it does
1. Activates `healing-tests` skill and invokes `defect-diagnostician`.
2. Ingests execution failure logs, stack traces, and Playwright DOM snapshots / traces.
3. Classifies root cause:
   - **Test Flake / Selector Drift:** DOM element changed (`#submit` -> `#btn-submit`). Automatically proposes selector patch.
   - **Fixture / Mock Outdated:** API response format evolved. Proposes mock fixture alignment.
   - **Application Defect:** Real application bug or regression. Strictly logs defect in `docs/qe/<app-name>/07-healing/audit_log.json` (defects are recorded inside it) and does NOT mutate test code.
4. Enforces strict assertion preservation rule: Never weakens, deletes, or trivializes an assertion to force a pass.
5. Re-runs healed tests to verify pass verdict.
6. Emits `docs/qe/<app-name>/07-healing/audit_log.json`.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command has no gate.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/07-healing/audit_log.json`, plus any healed test file (each listed for approval before the write). Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-trace <app-name>
```
