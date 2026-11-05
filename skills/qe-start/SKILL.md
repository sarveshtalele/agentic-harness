---
name: qe-start
description: "Initialize autonomous Agentic QE intake with explicit scope, boundary rules, and target framework setup. Use when the user runs /agentic-qe:qe-start or $qe-start."
argument-hint: "<app-name> [--source <path>] [--mode greenfield|brownfield|auto] [--scope full-stack|api|ui|unit] [--frameworks playwright|vitest|pytest|junit|nunit|xunit|mstest]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-start
Invoke: `/agentic-qe:qe-start` (Claude Code) or `$qe-start` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; names the output folder `docs/qe/<app-name>/`). Flags: `--source` (default: current working directory), `--mode` (default `auto`: brownfield if the source already has code or tests, otherwise greenfield), `--scope` (default `full-stack`), `--frameworks` (default: inferred during intake and confirmed at Gate 0). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-start <app-name> [--source <path-to-repo>] [--mode greenfield|brownfield|auto] [--scope full-stack|api|ui|unit] [--frameworks playwright|vitest|pytest|junit|nunit|xunit|mstest]
```

## What it does
1. Prompts for or validates:
   - **Target Repository:** local path (from `--source`) or clone URL.
   - **Mode:** `greenfield` (no usable suite; build tests from scratch), `brownfield` (extend the existing suite), or `auto` (detect).
   - **Testing Scope:** `full-stack` (default), `api`, `ui`, or `unit`.
   - **Primary Test Frameworks:** e.g. Playwright TS, Vitest, PyTest, JUnit 5, NUnit/xUnit/MSTest (.NET).
   - **Boundary Isolation Rules:** Non-test source files marked read-only.
2. Shows the intake summary (detected mode, scope, frameworks, boundary rules) and every path it would create, then asks the user to type `approve gate 0 for <app-name> mode greenfield|brownfield`. It creates nothing, and never `.qe/`, before that.
3. When the plugin's hook records that message it creates `.qe/` (`run.json` and the hash-chained ledger) itself; from then on the hooks guard the run: they ask before every new file and stamp metadata on documents.
4. After the hook confirms Gate 0, generates `00-intake/scope.md` and `00-intake/manifest.json` under `docs/qe/<app-name>/` (with the user's yes for those paths).

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command ends at Gate 0 (Intake). Show the intake summary, then ask the user to type the whole message `approve gate 0 for <app-name> mode greenfield|brownfield` (or `reject gate 0`). The plugin's hook, not you, creates `.qe/` and `run.json` when it records that message. The live dashboard (started by the plugin at Gate 0) shows the gate, its documents and the next command, and updates as files change.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/00-intake/scope.md`, `docs/qe/<app-name>/00-intake/manifest.json`. The `.qe/` folder is created only by the plugin hook.

Suggests next command:
```bash
/agentic-qe:qe-discover <app-name>
```
