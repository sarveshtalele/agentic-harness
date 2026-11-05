---
name: qe-sync
description: "Bring the run's documents in line with the tests that are in the repository now: map tests added or changed by hand to designed cases, update the generation manifest and the traceability matrix, and report what is out of date. Generates no tests and no new documents. Use when the user runs /agentic-qe:qe-sync or $qe-sync."
argument-hint: "<app-name>"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-sync
Invoke: `/agentic-qe:qe-sync` (Claude Code) or `$qe-sync` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). No flags. If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-sync <app-name>
```

## What it does
The user changed or added tests outside the plugin (in an editor, or by asking for a change). This command updates the run's documents to match; it never writes or changes a test, and never creates a document that the layout does not already have.

1. Runs `node "${CLAUDE_SKILL_DIR}/../tracing-coverage/scripts/check-gate.ts" --gate 5 --app <app-name> --json` and reads `inventory` (tests in the repo: existing, generated, added by hand) and the validator's findings. Show the numbers exactly as printed; never state counts of your own.
2. For each test file that names designed cases but is not in `05-generation/manifest.json`, adds it to the manifest's `files` list with its `caseIds`.
3. For each test added by hand with no `CASE_ID`: shows it to the user and asks which designed case it covers. Only when the user names one, adds the marker comment by asking the user to add it themselves, or records the mapping in the manifest. When it covers no designed case, lists it as an orphan; do not invent a case for it.
4. For each designed case whose test file changed since Gate 4 was approved, says that Gate 4 is reopened and the user approves it again after reviewing the change.
5. Updates `docs/qe/<app-name>/08-traceability/matrix.json` from the inventory and the results.
6. Runs the check again and shows its output, with the open gaps.

## Consent

This command writes only `docs/qe/<app-name>/04-design/test_cases.json` (only a mapping the user confirmed), `docs/qe/<app-name>/05-generation/manifest.json` and `docs/qe/<app-name>/08-traceability/matrix.json`. The plugin's write guard refuses everything else while it runs, including test files. Every document you update keeps its metadata header.

This command has no gate. A changed approved document reopens its gate; the user approves it again.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: none. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-execute <app-name>
```
