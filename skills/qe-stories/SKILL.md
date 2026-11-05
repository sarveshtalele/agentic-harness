---
name: qe-stories
description: "Author BA-style user stories with Given/When/Then acceptance criteria and a positive/negative/exception test case table, exportable to CSV and Jira import format. Use when the user runs /agentic-qe:qe-stories or $qe-stories."
argument-hint: "<app-name> [--from <prd-or-notes-path>]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-stories
Invoke: `/agentic-qe:qe-stories` (Claude Code) or `$qe-stories` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flag: `--from <prd-or-notes-path>` (default: none; ask the user to describe the application). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-stories <app-name> [--from <path-to-prd-or-notes>]
```

## What it does
1. Activates the `authoring-user-stories` skill. Chain: in greenfield, `/agentic-qe:qe-start` -> `/agentic-qe:qe-discover` -> `/agentic-qe:qe-stories` -> `/agentic-qe:qe-requirements`; in brownfield it is optional.
2. Writes stories as `**US-<APP>-NNN**: As a <user/role>, I want to <functionality/action> so that <business benefit/value>.` with Given/When/Then acceptance criteria and a P1-P3 priority.
3. Builds the test case table (TC ID | User Story ID | Scenario | Type | Precondition | Test Data | Steps | Expected Result | Priority | Automation Candidate | Remarks). Every story gets at least 1 Positive, 2 Negative, 1 Exception case.
4. Runs `export-cases.ts` to validate the cases and write the Markdown, CSV and Jira import files.
5. Jira: import `02-requirements/jira_import.csv` into Jira manually.
6. Displays the stories and the user's review comes before `/agentic-qe:qe-requirements`; Gate 1 (Requirements) is approved once, there.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command has no gate. Gate 1 (Requirements) is approved once, after `/agentic-qe:qe-requirements`, and covers the stories too.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/02-requirements/user_stories.md`, `docs/qe/<app-name>/02-requirements/test_cases.csv`, `docs/qe/<app-name>/02-requirements/jira_import.csv`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-requirements <app-name>
```
