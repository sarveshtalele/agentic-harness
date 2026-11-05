---
name: qe-requirements
description: "Reverse-engineer observable testable requirements, API contracts, and user roles with verifiable source evidence quotes. Use when the user runs /agentic-qe:qe-requirements or $qe-requirements."
argument-hint: "<app-name> [--specs <path>]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-requirements
Invoke: `/agentic-qe:qe-requirements` (Claude Code) or `$qe-requirements` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flag: `--specs <path>` (default: none; requirements come from code, routes, and README only). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-requirements <app-name> [--specs <path-to-specs-or-jira>]
```

## What it does
0. Mode note: brownfield extracts from code with `file:line` evidence; greenfield extracts from the approved `docs/qe/<app-name>/02-requirements/user_stories.md`, citing story ID + acceptance criterion text as evidence.
1. Activates the `extracting-requirements` skill and invokes `requirements-analyst`.
2. Analyzes discovered routes, business logic files, controllers, and documentation (plus `--specs` if given).
3. Extracts testable requirements with:
   - **Observable Behavior:** Verifiable statements without speculative claims.
   - **Actors:** System, admin, authenticated customer, anonymous visitor, CLI user.
   - **Tiers:** Product-level (README/docs promises) vs Component-level (function contracts).
   - **Evidence Quotes:** Mandatory verbatim source code quote with `file:line` reference.
4. Generates `docs/qe/<app-name>/02-requirements/requirements.json` and `docs/qe/<app-name>/02-requirements/requirements.md`.
5. Runs `node "${CLAUDE_SKILL_DIR}/../tracing-coverage/scripts/check-gate.ts" --gate 1 --app <app-name>` and shows its output. Every requirement needs an `id`, a `priority` (P0 to P3) and source evidence. While it prints FAIL, fix the gaps and do not ask for approval: the plugin refuses to record the gate.
6. Enforces **Gate 1 (Requirements)**: displays the extracted requirements (greenfield: together with the stories) and waits for `approve gate 1 for <app-name>` before planning.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command ends at Gate 1 (Requirements). The user approves by typing the whole message `approve gate 1 for <app-name>` and rejects with `reject gate 1`; the plugin's UserPromptSubmit hook records only these exact messages. The live dashboard (started by the plugin at Gate 0) shows the gate, its documents and the next command, and updates as files change.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/02-requirements/requirements.json`, `docs/qe/<app-name>/02-requirements/requirements.md`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-plan <app-name>
```
