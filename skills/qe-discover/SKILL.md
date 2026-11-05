---
name: qe-discover
description: "Perform deep repository intelligence, stack detection, AST parsing, and test inventory analysis. Use when the user runs /agentic-qe:qe-discover or $qe-discover."
argument-hint: "<app-name> [--source <path>] [--mode greenfield|brownfield|auto]"
disable-model-invocation: true
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-discover
Invoke: `/agentic-qe:qe-discover` (Claude Code) or `$qe-discover` (Codex).

## Arguments

Parse `$ARGUMENTS`. In Codex, read the arguments from the user's message. Positional `<app-name>` (required; selects `docs/qe/<app-name>/`). Flags: `--source <path>` (default: current working directory), `--mode greenfield|brownfield|auto` (default `auto`, as set at intake). If `<app-name>` is missing, ask the user for it; do not guess.

## Usage
```bash
/agentic-qe:qe-discover <app-name> [--source <path-to-repo>] [--mode greenfield|brownfield|auto]
```

## What it does
1. Activates the `analyzing-repositories` skill and invokes `repo-intelligence-analyst`.
2. Inspects codebase directory tree, package manifests (`package.json`, `pyproject.toml`, `pom.xml`), Dockerfiles, and CI workflows.
3. Detects:
   - Primary languages, frameworks, runtime versions.
   - Application architecture (monolith, microservices, SPA, API, CLI).
   - Existing test suites, frameworks, conventions, and coverage gaps.
   - Entrypoints, public interfaces, and API routes.
4. In `greenfield` mode (no source code yet), skips scanning and records the intended stack; in `brownfield` mode, inventories the existing suite and records its test count as the regression baseline.
5. Generates `01-discovery/architecture.json` and updates `docs/qe/<app-name>/01-discovery/summary.md`.

## Consent

Before creating any file or folder, list every path you will create and wait for the user's explicit yes. Never create files or folders the user did not approve. Every document you create starts with a metadata header (doc_id, created_at, created_by, mode, source_commit).

This command has no gate.

On Codex, ask the user to type exactly `approve create <path>[, <path>]` for new files; Claude Code shows its own permission prompt instead. The plugin's UserPromptSubmit hook records only the approval phrases, and you never claim approval from anything else.

Paths this command may create: `docs/qe/<app-name>/01-discovery/architecture.json`, `docs/qe/<app-name>/01-discovery/summary.md`. Ledger entry appended to `.qe/ledger.jsonl`.

Suggests next command:
```bash
/agentic-qe:qe-requirements <app-name>   # brownfield
/agentic-qe:qe-stories <app-name>        # greenfield
```
