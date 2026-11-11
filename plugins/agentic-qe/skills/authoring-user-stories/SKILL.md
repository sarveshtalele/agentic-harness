---
name: authoring-user-stories
description: Writes BA-style user stories with Given/When/Then acceptance criteria and a test cases table (positive, negative, exception), exportable to CSV and Jira import format. Use when the user asks for user stories, acceptance criteria, a Jira story, or a test cases table, and for greenfield apps with no code yet.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep Write Bash(node ${CLAUDE_SKILL_DIR}/scripts/export-cases.ts *)
---

# Authoring User Stories

Turns a PRD, notes, or a verbal description into approved user stories plus a traceable test case table. Primary input for greenfield runs.

## When to use
Activate when running `/agentic-qe:qe-stories`, or when a user wants stories, acceptance criteria, or a test cases table for Jira.

## Workflow
1. **Gather:** Read the `--from` file or ask the user for the app description, roles, and goals. Never invent roles or features the user did not state.
2. **Stories:** Write each as `**US-<APP>-NNN**: As a <user/role>, I want to <functionality/action> so that <business benefit/value>.` plus Given/When/Then acceptance criteria and a P1-P3 priority.
3. **Cases:** Per story, at least 1 Positive, 2 Negative, 1 Exception. Boundary cases use `Negative (Boundary)`.
4. **Export:** Build `cases.json` and run the script below. Fix every reported error and rerun.
5. **Review:** Show the stories and table. Gate 1 (`approve gate 1 for <app>`) is approved after `/agentic-qe:qe-requirements`.

Template, column definitions and a worked example: [references/TEMPLATE.md](references/TEMPLATE.md).

## Scripts
Run `node "${CLAUDE_SKILL_DIR}/scripts/export-cases.ts" <cases.json> <out-dir>`.
It validates the input (exit 1 with specific errors on failure) and writes `02-requirements/user_stories.md`, `02-requirements/test_cases.csv` and `02-requirements/jira_import.csv` into `<out-dir>`, each with a metadata header. List the three paths and get the user's yes before running.

## Jira
Import `02-requirements/jira_import.csv` into Jira manually.
In Codex, paths are relative to this skill's folder.
