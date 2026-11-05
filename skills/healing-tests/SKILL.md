---
name: healing-tests
description: Diagnoses execution failures, distinguishes true defects from flaky test bugs, and repairs selectors and fixtures while preserving assertions. Use when tests fail or need healing.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep Edit Bash(node ${CLAUDE_SKILL_DIR}/scripts/diagnose-failure.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/apply-healing.ts *)
---

# Healing Tests

Autonomous diagnostic and remediation engine for failed tests.

## When to use
Activate when executing `/agentic-qe:qe-heal`, or whenever a test failure needs root-cause classification and potential self-healing.

## Workflow
1. **Trace Analysis:** Ingest error message, stack trace, and DOM snapshot.
2. **Defect Classification:**
   - Test bug (selector drift, fixture desynchronization).
   - Application defect (real bug / regression).
3. **Healing Generation:** For test bugs, synthesize the minimal surgical diff.
4. **Assertion Preservation Gate:** Strictly verify that NO assertions are removed or softened.
5. **Re-Verification:** Re-run the healed test to confirm it now passes legitimately.
6. **Logging:** Record all findings in `07-healing/audit_log.json`.

Failure signatures and the allowed or forbidden remediation for each: [references/HEALING_PATTERNS.md](references/HEALING_PATTERNS.md).

## Scripts
- `node "${CLAUDE_SKILL_DIR}/scripts/diagnose-failure.ts" <failure.json>` with `{"errorMessage","stackTrace"}` prints the category (`SELECTOR_DRIFT`, `APPLICATION_DEFECT`, `ENVIRONMENT_ERROR`) and whether it can be healed.
- `node "${CLAUDE_SKILL_DIR}/scripts/apply-healing.ts" <test-file> <broken-selector> <healed-selector>` prints the patched source in `patchedCode` and refuses any patch that changes the assertion count. It never writes the file; apply the diff with Edit after the user approves it.

In Codex, paths are relative to this skill's folder.
