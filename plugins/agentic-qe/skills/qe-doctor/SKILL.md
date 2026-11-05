---
name: qe-doctor
description: "Check agentic-qe health: Node version, installed plugin version against this repository, scope, registered hooks, foreign folders in the installed copy, ledger integrity, Playwright and MCP availability. Use when the user runs /agentic-qe:qe-doctor or $qe-doctor."
disable-model-invocation: true
allowed-tools: Read Bash(node ${CLAUDE_SKILL_DIR}/scripts/agentic-qe.ts doctor*)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
---

# qe-doctor
Invoke: `/agentic-qe:qe-doctor` (Claude Code) or `$qe-doctor` (Codex). In Codex, run `node scripts/agentic-qe.ts doctor` from this skill's folder.

## What it does
Run `node "${CLAUDE_SKILL_DIR}/scripts/agentic-qe.ts" doctor --host auto` and show the result. Read-only; creates and changes nothing. Then suggest fixes for any failing check. A version mismatch between the installed plugin and this repository is an error; the fix is `claude plugin marketplace update agentic-qe && claude plugin update agentic-qe@agentic-qe --scope <scope>`.
