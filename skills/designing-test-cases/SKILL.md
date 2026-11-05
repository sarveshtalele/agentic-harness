---
name: designing-test-cases
description: Designs structured test cases across positive, negative, exception, and boundary value scenarios with deterministic oracles. Use when detailing test case specifications.
compatibility: Requires Node.js 22.18+ (runs TypeScript natively)
metadata:
  author: Sarvesh Talele
  version: "1.6.0"
allowed-tools: Read Glob Grep Write Bash(node ${CLAUDE_SKILL_DIR}/scripts/generate-cases.ts *) Bash(node ${CLAUDE_SKILL_DIR}/scripts/check-confidence.ts *)
---

# Designing Test Cases

Designs thorough, automatable test cases adhering to ISTQB techniques and deterministic oracle standards.

## When to use
Activate when executing `/agentic-qe:qe-design`, or when authoring granular test specifications for approved plan areas.

## Scenario Multiplicity Requirement
For every requirement or user story, this skill MUST produce:
- **Positive:** Nominal happy path scenario proving intended functionality.
- **Negative (2-3):** Rejection paths, malformed inputs, unauthorized access attempts.
- **Exception (1):** Error handling under service failures or system exceptions.
- **Boundary Value:** Edge extremes (minimum, maximum, 0, just-above, just-below).

## Plan coverage
Every scenario in `03-plan/plan.json` gets at least one case, and each case lists the scenarios it covers in `planScenarioIds`. The coverage map (`docs/qe/<app>/coverage-map.md`) shows what is still missing; Gate 3 is refused until nothing is.

## Test levels
Allocate cases across **Unit** (pure logic, no I/O), **Integration** (API/service/DB boundary) and **E2E** (browser via Playwright), as the plan allows. Record each case's optional JSON field `level`: `Unit | Integration | E2E`. A level may be skipped only with a written reason in the plan (e.g. "no UI"). `level` is not a table column.

## Output columns
Every case table uses exactly these 11 columns, in order: `TC ID | User Story ID | Scenario | Type | Precondition | Test Data | Steps | Expected Result | Priority | Automation Candidate | Remarks`.
- **Type mapping:** `Positive`, `Negative`, `Exception`; boundary cases are `Negative (Boundary)`.
- **Priority:** P1-P3. **Automation Candidate:** `Yes (<tool>)` or `No`.
- **User Story ID:** the story or requirement ID the case verifies.

## Oracle Types
See [references/ORACLE_TYPES.md](references/ORACLE_TYPES.md) for details on `specified`, `derived`, `metamorphic`, and `golden` oracles.

## Confidence review (per case)
After designing, the `confidence-reviewer` agent scores every case against the real repository: the component it tests (file, line, symbol), then `source_proven`, `correct_target`, `expected_derivable` and `fixture_validity`, out of 100. Write the result to `docs/qe/<app>/04-design/confidence.json` and run `node "${CLAUDE_SKILL_DIR}/scripts/check-confidence.ts" docs/qe/<app>/04-design/confidence.json --kind design`. It checks the arithmetic and the verdict rule, and that every cited `file:line` exists; a missing citation makes the case REJECT. Fix each REVISE or REJECT case and review it again. Anything left is shown to the user at the gate.

## Scripts
Run `node "${CLAUDE_SKILL_DIR}/scripts/generate-cases.ts" <cases.json>` on the designed cases (a JSON array). It prints `{count, errors}` and exits 1 when a case lacks `caseId`, `scenario`, `expectedResult` or an oracle kind; fix every error and rerun. It writes nothing. In Codex, paths are relative to this skill's folder.
