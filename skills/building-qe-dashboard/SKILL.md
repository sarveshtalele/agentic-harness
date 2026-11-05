---
name: building-qe-dashboard
description: Explains and opens the live QE dashboard, the single browser view of every phase document, gate, test result, defect and the next command, with in-browser editing and ZIP download. Use when the user asks for a report, dashboard, release evidence page, or where the QE outputs are.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep
---

# Building QE Dashboard

The plugin writes no HTML reports. Since 1.4.0 the live dashboard is the single source of truth for a QE run: a local web page that reads `docs/qe/<app>/` and `results/` as they change.

## When to use
The dashboard starts by itself after Gate 0 (`approve gate 0 for <app>`). Use this skill when the user asks for a report or dashboard, or the dashboard is not running.

## Steps
1. Ask the user to run `/agentic-qe:qe-panel --serve` (show the command so they can copy it). It prints the link of the running dashboard, or starts one. Never write the link into a file.
2. No execution evidence yet: say so and point to `/agentic-qe:qe-execute <app>`. Never show a pass rate that no result file supports.

## What the dashboard shows
- Overview: release verdict (PASS, FAIL or INCONCLUSIVE from the result files), KPI tiles, the next action with a copy button, and one card per gate (0 to 5) with its state: APPROVED, PENDING, REJECTED or REOPENED.
- Gate page: the gate's Markdown report and one card per artifact. Opening a card renders the document cleanly: Markdown with its images, JSON as tables and records (never raw), CSV as a table. Documents are edited only here, inside their gate; saving reopens that gate and every later approved gate, and the page shows the approval phrases to type.
- Insights: requirements, test cases, traceability, results, defects (why each failed and how to fix it), the evidence gallery with the screenshot guardrail, and the ledger activity.
- Download ZIP of all artifacts. Light, dark and auto themes.
- A read-only HTML snapshot, `docs/qe/<app>/09-release/dashboard.html`, written after `approve gate 5` or by `/agentic-qe:qe-panel --export`: documents pre-rendered, screenshots embedded, no server needed.

## Scripts
`scripts/build-trace-report.ts` is the data layer (`collectTrace(root, app)`). It reads the phase folders and the pre-1.4.0 flat file names, both case schemas (`tc_id`/`caseId`), and JUnit, TRX and Playwright results. `scripts/html.ts` holds the escaping, Markdown (with images through a resolver) and CSV helpers, and renders JSON as a readable document. `scripts/gate-report-md.ts` builds the Markdown gate report the approval hook writes to `docs/qe/<app>/<phase>/gate-<N>-report.md` after each approval; the Gate 5 report embeds every screenshot in `06-execution/evidence/`, and `checkReportImages` is the guardrail the dashboard shows. The server and page live in `skills/qe-panel/scripts/`.
