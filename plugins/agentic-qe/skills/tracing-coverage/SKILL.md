---
name: tracing-coverage
description: Computes requirements-to-test traceability, surfaces unmapped critical requirements and orphan tests, and reports executed results per case. Use when auditing test coverage or checking the traceability gate.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep Write Bash(node ${CLAUDE_SKILL_DIR}/scripts/build-matrix.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/check-gate.ts *)
---

# Tracing Coverage

Builds an end-to-end Traceability Matrix mapping Requirements -> Test Cases -> Executable Files -> Test Results.

## When to use
Activate during test planning review, prior to release dashboard generation, or when auditing QE coverage.

## Verification Gate
- **100% Critical Requirements Mapping:** Every P0 and P1 requirement MUST link to at least 1 verified test case.
- **Orphan Test Detection:** Flags test cases that do not map to an approved requirement ID.

## Scripts
Run `node "${CLAUDE_SKILL_DIR}/scripts/build-matrix.ts" <requirements.json> <cases.json> <results.json>`. Prints the traceability matrix as JSON to stdout (entries with per-case results, coverage percent, uncovered count, orphan cases); writes nothing.
Run `node "${CLAUDE_SKILL_DIR}/scripts/check-gate.ts" --gate <1-5> --app <app>` before asking for a gate approval. It rebuilds `docs/qe/<app>/coverage-map.md` (requirement, plan scenario, designed case, test file, result) and prints what that gate still needs; exit 1 while anything is missing. The approval hook runs the same check and refuses the gate until it passes, or until the user types `approve gate N with gaps: <reason>`.
In Codex, paths are relative to this skill's folder.
