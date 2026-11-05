---
name: qe-sign
description: "Formally capture QE Lead and Platform Admin digital sign-off and seal the release verification proof pack. Use when the user runs /agentic-qe:qe-sign or $qe-sign."
argument-hint: "<app-name> --signer <name> [--role \"QE Lead\"|\"Platform Admin\"]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-sign
Invoke: `/agentic-qe:qe-sign` (Claude Code) or `$qe-sign` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flags: `--signer <name>` (required; the signer's name is never guessed), `--role "QE Lead"|"Platform Admin"` (default `QE Lead`). If `<app-name>` or `--signer` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-sign <app-name> --signer <name> [--role "QE Lead"|"Platform Admin"]
```

## What it does
The plugin never signs on a person's behalf; the signer must run this command themselves.
1. Validates prerequisites:
   - 100% of critical (P0/P1) requirements mapped to test cases (`08-traceability/matrix.json`).
   - All tests passing (0 open unverified failures).
   - Execution results exist under `results/` and the live dashboard verdict is PASS.
   - Screenshot guardrail: every UI case has its screenshots in `06-execution/evidence/`, and the dashboard shows no guardrail warning. If a UI case has none, stop and run `/agentic-qe:qe-execute` again; never sign off without the evidence.
2. Runs `node "${CLAUDE_SKILL_DIR}/../tracing-coverage/scripts/check-gate.ts" --gate 5 --app <app-name>`: every designed case needs a test result. While it prints FAIL, run the missing tests; do not ask for sign-off. Gaps accepted at earlier gates (`with gaps:`) are listed in the release report.
3. Shows the release verdict and asks the signer to type `approve gate 5 for <app-name>` (Gate 5, release sign-off). After that approval the plugin writes the Markdown report `09-release/gate-5-report.md`, which embeds every screenshot.
4. Computes SHA-256 integrity hash of all generated test files, execution results, evidence images and the gate reports.
5. Generates `docs/qe/<app-name>/09-release/signoff.md` with:
   - Signer name, role, timestamp.
   - Final pass/fail metrics.
   - Cryptographic integrity block.
6. Appends the sign-off event to `.qe/ledger.jsonl`.
7. Seals release verification package ready for deployment pipeline CI/CD gating.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command ends at Gate 5 (Release sign-off). The user approves by typing the whole message `approve gate 5 for <app-name>` and rejects with `reject gate 5`; the plugin's UserPromptSubmit hook records only these exact messages. The live dashboard (started by the plugin at Gate 0) shows the gate, its documents and the next command, and updates as files change.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/09-release/signoff.md`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-panel <app-name>
```
