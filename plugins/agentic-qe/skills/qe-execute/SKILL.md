---
name: qe-execute
description: "Execute generated and repository test suites in isolated runner environments, capturing structured logs and evidence. Use when the user runs /agentic-qe:qe-execute or $qe-execute."
argument-hint: "<app-name> [--suite unit|api|e2e|all] [--headless]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-execute
Invoke: `/agentic-qe:qe-execute` (Claude Code) or `$qe-execute` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flags: `--suite unit|api|e2e|all` (default `all`), `--headless` (default: the runner's own default). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-execute <app-name> [--suite unit|api|e2e|all] [--headless]
```

## What it does
1. Activates `executing-tests` skill and invokes `qa-execution-engineer`.
2. Inspects runner adapter registry (Playwright CLI, Vitest, PyTest, Maven Surefire, Gradle, dotnet test).
3. Executes test command in an isolated environment (venv / container / sandbox).
4. Streams live output to terminal / console, recording stdout, stderr, run duration, exit code.
5. Emits `docs/qe/<app-name>/06-execution/summary.json` and the JUnit XML report(s) in `results/*.xml` at the project root, plus `results/playwright.json`, `playwright-report/` (Playwright HTML report), `test-results/` (screenshots/traces) `docs/qe/<app-name>/06-execution/evidence/e2e/` (every UI screenshot, copied from the Playwright report by `collect-evidence.ts`; required) and `docs/qe/<app-name>/06-execution/evidence/mcp/` (MCP screenshots and snapshots).
6. Calculates pass/fail/skip counts. If tests fail, automatically flags them for `/agentic-qe:qe-heal`.
7. Runs every designed case: results are matched to cases by the `CASE_ID` in the test name (`tc_app_001_…`). Run `node "${CLAUDE_SKILL_DIR}/../tracing-coverage/scripts/check-gate.ts" --gate 5 --app <app-name>` and run whatever it lists as having no result.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command has no gate.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/06-execution/summary.json`, `results/*.xml`, `results/playwright.json`, `playwright-report/`, `test-results/`, `docs/qe/<app-name>/06-execution/evidence/e2e/`, `docs/qe/<app-name>/06-execution/evidence/mcp/`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-heal <app-name>      # brownfield, or greenfield after the app exists: if any test failed
/agentic-qe:qe-trace <app-name>     # if all tests passed
/agentic-qe:qe-execute <app-name>   # greenfield RED baseline (app not built yet): build the app, then run again
```
In greenfield mode, failures on the first run before the app exists are the expected RED baseline. Do not send them to /agentic-qe:qe-heal; tests are the specification and must not be changed to pass.
