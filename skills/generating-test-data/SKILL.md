---
name: generating-test-data
description: Generates deterministic synthetic test fixtures, schema mocks, and boundary edge datasets. Use when preparing test data for test execution.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep Write Bash(node ${CLAUDE_SKILL_DIR}/scripts/synthesize-data.ts *)
---

# Generating Test Data

Synthesizes high-fidelity mock fixtures conforming to application JSON schemas, TypeScript types, or database tables.

## When to use
Activate when running `/agentic-qe:qe-data`, or when creating mock payloads and test fixtures for test automation suites.

## Features
- **Schema Conformance:** Strictly respects required fields, types, formats, and ranges.
- **Negative & Edge Fixtures:** Generates out-of-bound numbers, malformed emails, nulls, and special characters.
- **Data Privacy & Masking:** Never embeds actual secrets or real user PII in synthetic fixtures.

## Workflow
1. Read the schemas, types or migrations the cases refer to. Take field rules from [assets/schema-templates.json](assets/schema-templates.json).
2. Build valid, invalid and boundary datasets, masking anything that looks like PII or a credential.
3. Write `04-design/fixtures.json` (ask before creating it).

## Scripts
Run `node "${CLAUDE_SKILL_DIR}/scripts/synthesize-data.ts" <spec.json>` with `{"kind":"user|boundary|pagination|auth", ...}` (see the header comment of the script for each shape). It prints deterministic JSON and writes nothing. In Codex, paths are relative to this skill's folder.
