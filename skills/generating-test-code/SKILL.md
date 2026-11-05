---
name: generating-test-code
description: Synthesizes compilable, idiomatic test source code (Playwright TS, Vitest, PyTest, JUnit 5, NUnit/xUnit/MSTest) with 1:1 case traceability. Use when generating automated test suites.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep Write Bash(node ${CLAUDE_SKILL_DIR}/scripts/emit-tests.ts *)
---

# Generating Test Code

Emits concrete test automation source files conforming to the native framework and idiom of the target repository.

## When to use
Activate when running `/agentic-qe:qe-generate`, or when converting approved design specifications into executable test code.

## Strict Standards
1. **One Case Per File:** Exactly one test declaration per emitted test file.
2. **Canonical Comment:** First line must contain `// CASE_ID: <case-id>` (`# CASE_ID:` in Python), with designed case ids only, never requirement ids. One test file per case or per small group; every designed case must appear in exactly one file. List each file in `05-generation/manifest.json` as `{ "files": [{ "path", "caseIds": [...] }] }`.
3. **No Placeholders:** Zero `pass`, `TODO`, ellipsis (`...`), or `assert True`.
4. **Clean Imports:** Only import dependencies present in repository manifests. Maximum 10 imports.
5. **UI tests:** Playwright locators come from the real page. See the Playwright section of [references/LANGUAGE_RULES.md](references/LANGUAGE_RULES.md).
6. **UI evidence:** Copy `assets/playwright.config.ts` into the project. Wrap each case step in `test.step(...)` and attach a step screenshot (`<CASE_ID> step N`) after key assertions.
7. **Rules per Language:** See [references/LANGUAGE_RULES.md](references/LANGUAGE_RULES.md). Pinned tool versions: [references/VERSIONS.md](references/VERSIONS.md).

## Scripts
Run `node "${CLAUDE_SKILL_DIR}/scripts/emit-tests.ts" <spec.json>` with `{"caseId","scenario","route","assertion"}`. It prints a validated Playwright test to stdout (exit 1 on an invalid `caseId` or route) and writes nothing; save the output only after the user approves the file. In Codex, paths are relative to this skill's folder.
