---
name: planning-quality-strategy
description: Creates a comprehensive quality strategy and test plan for a software project from its requirements. Use when a list of requirements exists and a structured plan is needed that includes scope, risks, test levels, entry/exit criteria, environments, data, and a traceability table.
---

# Quality Strategy & Test Plan Skill

This skill builds a quality strategy and test plan from a list of project requirements.

## Steps

1. **Receive requirements** — Accept the input as a block of text. Assume each line or numbered item is a requirement unless marked out-of-scope.
2. **Extract scope and out-of-scope** — Identify requirements explicitly labeled "out-of-scope" or "Out of scope". The rest are in scope.
3. **Identify risks** — For each in-scope requirement, list one or more risks (what could go wrong). Use the [risk-ranking-guide](references/risk-ranking-guide.md) to assign likelihood (Low/Medium/High) and impact (Low/Medium/High).
4. **Define test levels** — Describe what each level covers, using the [test-levels-guide](references/test-levels-guide.md).
   - Unit tests
   - Integration tests
   - End-to-end tests
5. **Specify entry and exit criteria** — Decide overall conditions for starting and ending testing.
6. **List test environments and data** — Describe what environments and test data are needed.
7. **Build traceability table** — Map each requirement to the tests that verify it, using the [traceability-table template](assets/traceability-table.csv).
8. **Assemble document** — Write the final document following the [quality-strategy-output template](assets/quality-strategy-output.md).

## Files

- `references/quality-strategy-template.md` — Template for the full document structure.
- `references/risk-ranking-guide.md` — Guidance on ranking risks.
- `references/test-levels-guide.md` — Descriptions of test levels.
- `assets/quality-strategy-output.md` — Final document output template.
- `assets/traceability-table.csv` — Traceability table CSV template.

## Constraints

- Only use information from the input. Do not add external details.
- Risks must be plausible and derived from the requirements.
- The document must include all sections from the template.
