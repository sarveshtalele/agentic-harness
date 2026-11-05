---
name: qe-data
description: "Generate deterministic synthetic test fixtures, schema mocks, and boundary edge datasets. Use when the user runs /agentic-qe:qe-data or $qe-data."
argument-hint: "<app-name> [--format json|yaml|sql]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-data
Invoke: `/agentic-qe:qe-data` (Claude Code) or `$qe-data` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flag: `--format json|yaml|sql` (default `json`). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-data <app-name> [--format json|yaml|sql]
```

## What it does
1. Activates `generating-test-data` skill.
2. Reads schemas, types, interfaces, and database migrations from target codebase.
3. Generates realistic, valid, invalid, and boundary test datasets.
4. Masks sensitive data patterns (PII, credentials, bearer tokens).
5. Emits `docs/qe/<app-name>/04-design/fixtures.json`.
6. Prepares deterministic fixtures for the test generation phase.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command has no gate.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/04-design/fixtures.json`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-generate <app-name>
```
