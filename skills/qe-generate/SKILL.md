---
name: qe-generate
description: "Synthesize compilable, idiomatic test source code (Playwright TS, Vitest, PyTest, JUnit 5, NUnit/xUnit/MSTest) with 1:1 case traceability. Use when the user runs /agentic-qe:qe-generate or $qe-generate."
argument-hint: "<app-name> [--target unit|api|ui|all] [--dry-run]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-generate
Invoke: `/agentic-qe:qe-generate` (Claude Code) or `$qe-generate` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flags: `--target unit|api|ui|all` (default `all`), `--dry-run` (default off; when on, stage files and show the diff without writing to the repository). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-generate <app-name> [--target unit|api|ui|all] [--dry-run]
```

## What it does
0. Mode note: in greenfield mode, tests are written before the app (test-first) and are expected to fail until the app exists; executing them first records a RED baseline.
1. Activates `generating-test-code` skill and invokes `test-automation-engineer`.
2. Translates approved design cases into executable test source files in the target repository's native conventions.
3. Enforces strict generation rules:
   - Exactly 1 test declaration per file for 100% granular traceability.
   - Exact canonical marker comment injected: `// CASE_ID: <test-case-id>`.
   - Real assertions, fixtures, and mocks; strictly zero `pass`, `TODO`, or `assert True`.
   - No speculative or uninstalled imports; mocks external network/disk boundaries without mocking the unit under test.
   - **Every designed case gets a test.** The first line of each test file is `CASE_ID: <TC-id>[, <TC-id>…]` (in the language's comment syntax), with designed case ids only; a requirement id (`REQ-…`) is not a case id and fails the gate.
   - Test files go in the project's test folders (`tests/`, `e2e/`, …), never under `docs/`. Write them **before** Gate 4: the gate checks the files on disk. The guard asks the user before each new file.
4. Records `docs/qe/<app-name>/05-generation/manifest.json` in exactly this shape: `{ "files": [{ "path": "tests/test_x.py", "caseIds": ["TC-…"], "level": "Unit" }] }`. Any other shape is reported as a gap.
5. Invokes `confidence-reviewer` with `kind: code` on **each test**: `compilable`, `assertion_integrity`, `import_safety` and `traceability_present`, out of 100. Its answer is recorded by the plugin as `05-generation/confidence.json`; never write it yourself. Then `coverage-auditor` with `kind: code` checks each test exercises its case (`05-generation/audit.json`).
6. Runs `node "${CLAUDE_SKILL_DIR}/../tracing-coverage/scripts/check-gate.ts" --gate 4 --app <app-name>` and shows its output. While it prints FAIL, do the missing work; do not ask for approval.
7. Enforces **Gate 4 (Generate)**: presents the test files and their case ids and waits for `approve gate 4 for <app-name>`. Changing an approved test file afterwards reopens Gate 4.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command ends at Gate 4 (Generate). The user approves by typing the whole message `approve gate 4 for <app-name>` and rejects with `reject gate 4`; the plugin's UserPromptSubmit hook records only these exact messages. The live dashboard (started by the plugin at Gate 0) shows the gate, its documents and the next command, and updates as files change. Test files are written to the repository only after this approval.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/05-generation/manifest.json` (greenfield also `docs/qe/<app-name>/05-generation/app_contract.md`), plus each generated test file in the target repository's test folders (listed in the manifest). The plugin writes `05-generation/confidence.json`, `05-generation/audit.json`, the coverage map and the gate report; never write those. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-execute <app-name>
```
