---
name: extracting-requirements
description: Inverts codebases, public interfaces, and documentation into observable, testable requirements with verifiable evidence quotes. Use when extracting test requirements or preparing for test planning.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep Bash(node ${CLAUDE_SKILL_DIR}/scripts/extract-contracts.ts *)
---

# Extracting Requirements

Reverse-engineers observable functional behavior into structured, traceable requirements without hallucination.

## When to use
Activate when running `/agentic-qe:qe-requirements`, or whenever deriving testable behavior from source code, API routes, or Jira stories.

## Workflow
0. **Mode:** Brownfield reads code. Greenfield reads the approved user stories file (`docs/qe/<app>/02-requirements/user_stories.md`) instead of code.
1. **Source Inspection:** Locate route handlers, controllers, CLI command parsers, and business rules.
2. **Behavior Identification:** Express requirements in observable terms ("System returns 403 when token is expired").
3. **Evidence Extraction:** Brownfield: copy exact verbatim source quotes with `file:line` citations. Greenfield: quote the story ID plus the acceptance criterion text verbatim (e.g. `US-CALC-002 AC2: "Then an error 'Cannot divide by zero' is shown"`).
4. **Actor Classification:** Assign every requirement to an actor (`anonymous`, `customer`, `admin`, `system`).
5. **Output Delivery:** Write `02-requirements/requirements.json` and present for Gate 1 human approval.

## Strict Rules
- See [references/REQUIREMENT_RULES.md](references/REQUIREMENT_RULES.md) for anti-hallucination and evidence guidelines.

## Scripts
Run `node "${CLAUDE_SKILL_DIR}/scripts/extract-contracts.ts" <requirements.json> [--root <repo>]` before presenting Gate 1. It prints `{accepted, rejected}` and exits 1 if any requirement has no evidence quote or, with `--root`, if the quote is not found verbatim in its source file (brownfield). Drop or fix every rejected requirement. It writes nothing. In Codex, paths are relative to this skill's folder.
