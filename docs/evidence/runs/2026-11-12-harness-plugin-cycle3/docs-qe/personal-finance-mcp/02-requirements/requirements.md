---
doc_id: 02-requirements/requirements
created_at: 2026-11-12T13:08:34+05:30
created_by: agentic-qe v1.6.0
mode: brownfield
source_commit: aff44ea
---

# Personal Finance MCP - Requirements Document

**Doc ID:** REQ-PFM-MD-001
**Created At:** 2025-07-17T10:00:00Z
**Created By:** agentic-qe (harness)
**Mode:** brownfield
**Source Commit:** aff44ea06f

---

## 1. Product-Level Requirements

### REQ-PFM-001: Financial Tool Categories Listing
**Priority:** P0  
**Description:** The system MUST expose a `get_categories` tool that returns all available financial categories with their descriptions.  
**Source Evidence:** `server.py:44-54` — `app.tool("get_categories")(lambda: ...)` returns `categories_memory` dict containing category names and descriptions.

### REQ-PFM-002: Transaction Retrieval
**Priority:** P0  
**Description:** The system MUST expose a `get_transactions` tool that accepts an optional `category` filter and returns a list of transactions.  
**Source Evidence:** `server.py:56-70` — `app.tool("get_transactions")(lambda category=None: ...)` returns filtered `[t for t in transactions if ...]` or all transactions.

### REQ-PFM-003: Transaction Addition
**Priority:** P0  
**Description:** The system MUST expose an `add_transaction` tool that accepts `amount`, `category`, and optional `description`, and returns the new transaction with a generated ID.  
**Source Evidence:** `server.py:72-86` — `app.tool("add_transaction")(lambda amount, category, description="": ...)` appends to transactions list and returns `{"id": new_id, ...}`.

### REQ-PFM-004: Transaction Update
**Priority:** P0  
**Description:** The system MUST expose an `update_transaction` tool that accepts a `transaction_id` and optional fields to update and returns the updated transaction or raises ValueError if not found.  
**Source Evidence:** `server.py:88-104` — `app.tool("update_transaction")(lambda transaction_id, ...: ...)` iterates transactions, updates matching ID fields, raises ValueError(404) if not found.

### REQ-PFM-005: Transaction Deletion
**Priority:** P0  
**Description:** The system MUST expose a `delete_transaction` tool that accepts a `transaction_id`, removes the matching transaction, and returns a success confirmation or raises ValueError if not found.  
**Source Evidence:** `server.py:106-120` — `app.tool("delete_transaction")(lambda transaction_id: ...)` removes via `transactions[:] = [t for t in transactions if ...]` and returns `{"success": True}` or raises ValueError.

### REQ-PFM-006: Monthly Spending Summary
**Priority:** P0  
**Description:** The system MUST expose a `get_summary` tool that accepts `year` and `month` and returns category-wise totals and a grand total.  
**Source Evidence:** `server.py:122-137` — `app.tool("get_summary")(lambda year, month: ...)` filters by date, aggregates per category, returns `{"category_totals": {...}, "grand_total": ...}`.

### REQ-PFM-007: Spending Trends Calculation
**Priority:** P0  
**Description:** The system MUST expose a `get_spending_trends` tool that accepts optional `category` and `months` parameters and returns period-over-period spending data.  
**Source Evidence:** `server.py:139-155` — `app.tool("get_spending_trends")(lambda category=None, months=3: ...)` filters by category if given, groups by month, returns list of monthly trend entries.

### REQ-PFM-008: Budget Retrieval
**Priority:** P1  
**Description:** The system MUST expose a `get_budget` tool that returns all category-level budgets as a dict mapping category names to budget amounts.  
**Source Evidence:** `server.py:194-204` — `app.tool("get_budget")(lambda: ...)` returns `budgets` dict with category:amount mappings.

### REQ-PFM-009: Budget Setting
**Priority:** P1  
**Description:** The system MUST expose a `set_budget` tool that accepts `category` and `amount` and persists the budget entry.  
**Source Evidence:** `server.py:207-222` — `app.tool("set_budget")(lambda category, amount: ...)` stores in `budgets[category] = amount` and returns confirmation.

---

## 2. Component-Level Requirements

### REQ-PFM-010: MCP Server Initialization
**Priority:** P0  
**Description:** The system MUST initialize a FastMCP server instance with the name "Personal Finance Manager".  
**Source Evidence:** `server.py:29` — `app = FastMCP("Personal Finance Manager")`.

### REQ-PFM-011: In-Memory Transaction Storage
**Priority:** P0  
**Description:** The system MUST maintain an in-memory list of transactions that persists across tool invocations during the server session.  
**Source Evidence:** `server.py:30` — `transactions: list = []`.

### REQ-PFM-012: In-Memory Budgets Storage
**Priority:** P1  
**Description:** The system MUST maintain an in-memory dict of category budgets persisted across tool invocations during the server session.  
**Source Evidence:** `server.py:31` — `budgets: dict[str, float] = {}`.

### REQ-PFM-013: Category Definitions with Descriptions
**Priority:** P0  
**Description:** The system MUST define a fixed set of financial categories: food, transportation, utilities, entertainment, healthcare, education, shopping, bills, salary, investment, rental, and miscellaneous, each with a description.  
**Source Evidence:** `server.py:34-42` — `categories_memory` dict defines 12 categories with description strings.

### REQ-PFM-014: Transaction Amount Validation
**Priority:** P1  
**Description:** The system MUST store transaction amounts as floats and ensure non-empty amounts are accepted.  
**Source Evidence:** `server.py:75` — `"amount": amount` stored as float; `server.py:96-98` — update tool preserves amount field.

### REQ-PFM-015: Transaction Category Validation
**Priority:** P1  
**Description:** The system MUST accept and store a category string for each transaction against the known category set.  
**Source Evidence:** `server.py:76` — `"category": category` stored as string.

### REQ-PFM-016: Transaction Description Storage
**Priority:** P2  
**Description:** The system MUST store an optional description string with each transaction, defaulting to empty string.  
**Source Evidence:** `server.py:77` — `"description": description` stored as string; `server.py:72` — `description=""` default parameter.

### REQ-PFM-017: Timestamped Transactions
**Priority:** P1  
**Description:** The system MUST record the current ISO-format datetime when each transaction is added.  
**Source Evidence:** `server.py:78` — `"date": datetime.now().isoformat()`.

### REQ-PFM-018: Auto-Generated Transaction IDs
**Priority:** P1  
**Description:** The system MUST assign sequential integer IDs to new transactions.  
**Source Evidence:** `server.py:74` — `"id": len(transactions) + 1`.

### REQ-PFM-019: Transaction Update Partial Merging
**Priority:** P1  
**Description:** The system MUST merge only the provided fields when updating a transaction, preserving unspecified fields.  
**Source Evidence:** `server.py:99-102` — `for key, value in updates.items(): ... if value is not None: t[key] = value`.

### REQ-PFM-020: Summary Date Filtering
**Priority:** P0  
**Description:** The system MUST filter transactions by exact year and month for the summary calculation, parsing dates from ISO format.  
**Source Evidence:** `server.py:126-128` — `datetime.fromisoformat(t["date"])` and comparison with `.month` and `.year`.

### REQ-PFM-021: Summary Grand Total Calculation
**Priority:** P0  
**Description:** The system MUST sum all filtered transaction amounts as the grand total in the summary.  
**Source Evidence:** `server.py:136` — `"grand_total": sum(t["amount"] for t in filtered)`.

### REQ-PFM-022: Summary Category Aggregation
**Priority:** P0  
**Description:** The system MUST group filtered transactions by category and compute subtotals for each category in the summary.  
**Source Evidence:** `server.py:130-135` — `category_totals[c] = category_totals.get(c, 0) + t["amount"]`.

### REQ-PFM-023: Spending Trends Month Grouping
**Priority:** P0  
**Description:** The system MUST group transactions by year-month for the spending trends output.  
**Source Evidence:** `server.py:147-149` — `month_key = f"{parsed.year}-{parsed.month:02d}"` grouping.

### REQ-PFM-024: Spending Trends Amount Summation
**Priority:** P0  
**Description:** The system MUST sum transaction amounts per month group in the trends output.  
**Source Evidence:** `server.py:150` — `month_totals[month_key] = month_totals.get(month_key, 0) + t["amount"]`.

### REQ-PFM-025: Spending Trends Month Count Filtering
**Priority:** P1  
**Description:** The system MUST default to returning the last 3 months of spending trends when no `months` parameter is provided.  
**Source Evidence:** `server.py:139` — `months=3` default parameter; `server.py:152` — `sorted_months = sorted(month_totals.items())[-months:]` slicing.

### REQ-PFM-026: Spending Trends Category Filtering
**Priority:** P1  
**Description:** The system MUST optionally filter spending trends by a specific category.  
**Source Evidence:** `server.py:141` — `if category: filtered = [t for t in transactions if t["category"] == category]`.

### REQ-PFM-027: MCP Tool Registration Pattern
**Priority:** P2  
**Description:** The system MUST use the `@app.tool()` decorator pattern from the FastMCP library to register all financial tools.  
**Source Evidence:** `server.py:44,56,72,88,106,122,139,194,207` — All tools use `@app.tool("name")` decorator.

### REQ-PFM-028: Error Handling for Nonexistent Transaction Update
**Priority:** P0  
**Description:** The system MUST raise a ValueError with message "Transaction not found" when update is attempted on a nonexistent transaction_id.  
**Source Evidence:** `server.py:103` — `raise ValueError("Transaction not found")`.

### REQ-PFM-029: Error Handling for Nonexistent Transaction Deletion
**Priority:** P0  
**Description:** The system MUST raise a ValueError with message "Transaction not found" when deletion is attempted on a nonexistent transaction_id.  
**Source Evidence:** `server.py:119` — `raise ValueError("Transaction not found")`.

### REQ-PFM-030: Budget Category-Value Model
**Priority:** P1  
**Description:** The system MUST store each budget as a key-value pair mapping a category string to a float amount.  
**Source Evidence:** `server.py:209` — `budgets[category] = amount`.

### REQ-PFM-031: Budget Retrieval Returns Full Dict
**Priority:** P1  
**Description:** The system MUST return the complete budgets dictionary when get_budget is called.  
**Source Evidence:** `server.py:196-200` — Returns `{"budgets": budgets}`.

### REQ-PFM-032: Budget Set Confirmation
**Priority:** P2  
**Description:** The system MUST return a confirmation dict when a budget is successfully set.  
**Source Evidence:** `server.py:210-218` — Returns `{"message": f"Budget set for {category}: ${amount}", "budget": {"category": category, "amount": amount}}`.

### REQ-PFM-033: Server Entry Point with Main Guard
**Priority:** P0  
**Description:** The system MUST include a standard Python entry point guard that runs the server when the script is executed directly.  
**Source Evidence:** `server.py:226` — `if __name__ == "__main__"`; `server.py:230` — `app.run()` within the guard.

### REQ-PFM-034: Server in Quiet Mode
**Priority:** P2  
**Description:** The system MUST pass the `quiet=True` transport parameter when stopping the server.  
**Source Evidence:** `server.py:228` — `import sys` and `sys.argv = ["", "--quiet"]`; `server.py:230` — `app.run(transport="stdio")`.

### REQ-PFM-035: MCP Server Stdio Transport
**Priority:** P0  
**Description:** The system MUST run the MCP server over stdio transport.  
**Source Evidence:** `server.py:230` — `app.run(transport="stdio")`.

---

## 3. Test Coverage Summary

| Tier | Count | IDs |
|------|-------|-----|
| Product-Level | 9 | REQ-PFM-001 — REQ-PFM-009 |
| Component-Level | 26 | REQ-PFM-010 — REQ-PFM-035 |
| **Total** | **35** | **REQ-PFM-001 — REQ-PFM-035** |