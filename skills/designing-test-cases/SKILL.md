---
name: designing-test-cases
description: Designs structured test cases across positive, negative, exception, and boundary value scenarios with deterministic oracles. Use when detailing test case specifications.
metadata:
  author: Sarvesh Talele
  version: "1.4.0"
---

# Designing Test Cases

Designs thorough, automatable test cases adhering to ISTQB techniques and deterministic oracle standards.

## When to use
Activate when the design stage runs (plugin command `qe-design`), or when authoring granular test specifications for approved plan areas.

## Scenario Multiplicity Requirement
For every requirement or user story, this skill MUST produce:
- **Positive:** Nominal happy path scenario proving intended functionality.
- **Negative (2-3):** Rejection paths, malformed inputs, unauthorized access attempts.
- **Exception (1), only when the requirement states error behaviour** (its `error_behaviour`, or a raise or throw in its quote). Otherwise design another Negative case. Never invent an error type, message or limit.
- **Boundary Value:** Edges of the requirement's input type. A string: empty, whitespace only, one character, the longest stated length and one more. A number: minimum, maximum, 0, just above and just below a stated limit. A list or object: empty, one item, the largest stated size.
- **Test data** is a value of the requirement's `input_type`. Another type appears only in an Exception case for a requirement that states how it is handled. Code refuses a case that breaks this (`qe/model/domain.py`).

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
After designing, the `confidence-reviewer` agent scores every case against the real repository: the component it tests (file, line, symbol), then `source_proven`, `correct_target`, `expected_derivable` and `fixture_validity`, out of 100. Save the result to `docs/qe/<app>/04-design/confidence.json`. The platform then checks it in code (`qe/confidence/`) with kind `design`. The check covers the arithmetic and the verdict rule, and that every cited `file:line` exists; a missing citation makes the case REJECT. Fix each REVISE or REJECT case and review it again. Anything left is shown to the user at the gate.

## Platform code step
The platform checks the designed cases (a JSON array) in code. It returns `{count, errors}` and fails when a case lacks `caseId`, `scenario`, `expectedResult` or an oracle kind; fix every error and rerun. It writes nothing. See `skills/README.md` and `docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md`.
