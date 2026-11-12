---
doc_id: "01-discovery/summary"
created_at: "2025-07-18T00:00:00Z"
created_by: "agentic-qe-harness"
mode: "brownfield"
source_commit: "aff44ea06f"
---

# Discovery Summary — personal-finance-mcp

## Overview

| Field | Value |
|---|---|
| App Name | personal-finance-mcp |
| Repository | https://github.com/sarveshtalele/personal-finance-mcp |
| Commit | aff44ea06f |
| Total Files | 88 |
| Test Files | 12 |
| Mode | Brownfield |

---

## Stack

| Layer | Technology | Details |
|---|---|---|
| **Primary Language** | Python (38 files) | Core server logic, tools, and MCP protocol |
| **Frontend / Supporting** | JavaScript (15 files) | Client-side or supporting scripts |
| **Styling** | CSS (1 file) | Styling assets |
| **Test Runner** | pytest | Python testing framework |
| **Package Managers** | Python / JS | No lockfile detected in workspace |

---

## Architecture

- **Type:** MCP (Model Context Protocol) server
- **Description:** Personal finance MCP server providing tools for financial data access via the Model Context Protocol
- **Entrypoints:** Detected MCP tool entrypoints via `@mcp.tool()` decorators

### MCP Tools (Detected from source)

| Tool Name | Description | Input Schema |
|---|---|---|
| `view_account` | View details for an account | account_id (str, required) |
| `departments` | List all departments | — (no params) |
| `accounts` | List transactions | account_id (str, optional), department_id (str, optional) |
| `employees` | List employees | department_id (str, optional) |
| `salary_advance` | Request a salary advance | employee_id (str, required), amount (float, required), reason (str, required) |
| `budgets` | List all budgets | — (no params) |
| `budget` | View a specific budget | budget_id (str, required) |
| `spending` | View spending | budget_id (str, required) |
| `spending_by_category` | View spending by category | budget_id (str, required) |
| `retire` | View retirement projection | employee_id (str, required), current_age (int, optional), retirement_age (int, optional), monthly_contribution (float, optional), current_savings (float, optional) |
| `financial_health` | Assess financial health | employee_id (str, required) |
| `update_profile` | Update profile info | employee_id (str, required), field (str, required), value (str, required) |

---

## Test Inventory (Brownfield Baseline)

| Metric | Count |
|---|---|
| Test Files | 12 |
| Test Runner | pytest |
| Convention | `test_*.py` |
| Regression Baseline | 12 test files |

### Test Files

| File | Path |
|---|---|
| `test_departments.py` | `src/test_departments.py` |
| `test_accounts.py` | `src/test_accounts.py` |
| `test_employees.py` | `src/test_employees.py` |
| `test_salary_advance.py` | `src/test_salary_advance.py` |
| `test_budgets.py` | `src/test_budgets.py` |
| `test_budget.py` | `src/test_budget.py` |
| `test_spending.py` | `src/test_spending.py` |
| `test_spending_by_category.py` | `src/test_spending_by_category.py` |
| `test_retire.py` | `src/test_retire.py` |
| `test_financial_health.py` | `src/test_financial_health.py` |
| `test_view_account.py` | `src/test_view_account.py` |
| `test_update_profile.py` | `src/test_update_profile.py` |

### Coverage Observations

- Every detected MCP tool has a corresponding test file — 1:1 coverage by tool is present.
- No coverage gaps identified at the tool level.

---

## Key Observations

1. **Brownfield project** with full source code — existing test suite of 12 files provides a regression baseline.
2. **MCP protocol server** — all functionality is exposed as MCP tools with structured inputs (strings, floats, ints, optionals).
3. **pytest-only** — no JavaScript test runner detected despite 15 JS files.
4. **No CI workflows** detected in the workspace — test execution rely on manual runs.
5. **All MCP tools are tested** — each of the 12 tool entrypoints has a dedicated test file.

---

## Suggested Next Steps

```bash
/agentic-qe:qe-requirements personal-finance-mcp
```