---
name: executing-tests
description: Dispatches test execution to local isolated runner adapters, capturing traces, standard streams, and JUnit XML reports. Use when executing automated tests.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Bash(npx --no-install playwright test:*) Bash(npx --no-install vitest run:*) Bash(pytest:*) Bash(python -m pytest:*) Bash(mvn test:*) Bash(node --test:*) Bash(./gradlew test:*) Bash(dotnet test:*) Bash(node ${CLAUDE_SKILL_DIR}/scripts/parse-junit.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/run-isolated.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/mcp-evidence.ts docs/qe/*) Bash(node ${CLAUDE_SKILL_DIR}/scripts/collect-evidence.ts *)
---

# Executing Tests

Executes test suites using runner adapters in project-local environments with structured log streaming and timeout enforcement.

## When to use
Activate when running `/agentic-qe:qe-execute`, or whenever invoking test runners to capture verified pass/fail execution evidence.

## Runner Adapters
Consult [references/RUNNER_REGISTRY.md](references/RUNNER_REGISTRY.md) for the allowed commands and report paths across Playwright, Vitest, PyTest, Maven and Gradle. Pinned tool versions: [references/VERSIONS.md](references/VERSIONS.md).

## Playwright UI runs
Set `BASE_URL` in the environment. If the Playwright MCP server is connected (`mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`), use `browser_snapshot` to read the real accessibility tree when a locator fails; otherwise read the page source. MCP setup is opt-in and never auto-started.

In greenfield mode the first run of test-first suites records a RED baseline: failures are expected until the app exists and are reported as baseline, not as defects.

## Screenshot evidence (required)
Run every UI suite with screenshots on (`screenshot: "on"`, or `testInfo.attach` per step). After the run, copy them out of the Playwright report: `node "${CLAUDE_SKILL_DIR}/scripts/collect-evidence.ts" results/playwright.json docs/qe/<app>/06-execution/evidence/e2e`. It writes `<caseId>-<step>.png` for each image attachment (base64 bodies and files), keeps only real PNG or JPEG data up to 5 MB, and refuses paths outside the project. `test-results/` is cleaned by the next run, so a screenshot that is not copied here is lost. The Gate 5 report embeds every image in `06-execution/evidence/`, and the dashboard flags any it does not show.

## MCP evidence
After the UI suite runs, write a plan `[{caseId, url, title?}]` from each E2E case's page to `docs/qe/<app>/06-execution/evidence/mcp-plan.json` and run `node "${CLAUDE_SKILL_DIR}/scripts/mcp-evidence.ts" docs/qe/<app>/06-execution/evidence/mcp-plan.json docs/qe/<app>/06-execution/evidence/mcp/`. It drives the Playwright MCP server headless and writes `<caseId>.png`, `<caseId>.snapshot.md` and `mcp-evidence.json`. With `BASE_URL` set, only its exact origin (host and port) is visited. Without it, only `localhost` URLs on the ports named in the plan (or `--port`) are visited, and well-known service ports are refused. A page that redirects to any other origin is recorded as `ok: false`; the redirect is detected after the browser follows it. If the MCP server cannot start (offline, or Node tooling missing), record "MCP evidence skipped: <reason>" and continue; test-runner screenshots remain the primary evidence.

## Scripts
- `node "${CLAUDE_SKILL_DIR}/scripts/parse-junit.ts" <results/junit.xml>` prints a JSON summary (total, passed, failed, skipped, durationMs, status, failures, cases); writes nothing.
- `node "${CLAUDE_SKILL_DIR}/scripts/run-isolated.ts" <total> <passed> <failed> <durationMs>` prints the verdict for raw counts (`INCONCLUSIVE` when total is 0).
- `scripts/mcp-evidence.ts`: see MCP evidence above.
- `scripts/collect-evidence.ts`: see Screenshot evidence above.

In Codex, paths are relative to this skill's folder.

## Verdict Integrity Rule
A run is ONLY marked `PASS` if test evidence confirms at least one executed passing test and zero failures. Empty suites or configuration errors are strictly marked `INCONCLUSIVE`.
