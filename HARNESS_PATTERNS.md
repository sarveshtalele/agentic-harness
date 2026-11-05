# 📚 Agent Harness Engineering Patterns: Architectural Implementation

Comprehensive mapping and implementation of the **13 core chapters** from Ashish Patel's [*Agent Harness Engineering Patterns*](https://ashishpatel26.github.io/agent-harness-engineering-pattern/#top) as built in the **Agentic QE Platform & Harness** codebase.

---

## 🏛️ Architecture Matrix & Pattern Mapping

| Pattern Chapter | Pattern Name | Implementation File(s) | Description & Role in Agentic QE Harness |
| :--- | :--- | :--- | :--- |
| **1.01** | **Game Loop** | [`src/backend/harness/harness_agent.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/harness_agent.py) | Master event loop: read user/tool input, advance state, run LLM/tool, and stream SSE tokens. |
| **1.02** | **Update Method** | [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) | Tick-based progress tracking and timeout evaluation for long-running workflows and test execution. |
| **1.03** | **State Pattern** | [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) | Finite state machine (`IDLE`, `PLANNING`, `DESIGNING`, `EXECUTING`, `AWAITING_APPROVAL`, `COMPLETED`). |
| **1.04** | **Template Method** | [`src/backend/harness/qe_tools.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/qe_tools.py) | Base QE tool template enforcing parameter validation, permission checks, timing, and ledger recording. |
| **1.05** | **Chain of Responsibility** | [`src/backend/harness/handoff.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/handoff.py) | Autonomous agent delegation chain (Architect ➔ Requirements ➔ Designer ➔ Automation ➔ Signoff). |
| **1.06** | **Interpreter** | [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) & `cli.py` | Command parser for `/skills`, `/projects`, `/project <id>`, `/gates`, `/audit`, `/heal`, `/plan`, `/execute`. |
| **1.07** | **Memento** | [`src/backend/harness/session.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/session.py) | Snapshotting session states, todos, messages, and gate scorecards to disk (`.sessions/*.json`) for rollback. |
| **1.08** | **Iterator** | [`src/backend/harness/discovery.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/discovery.py) | Deep directory traversal scanning 58 skills across filesystem roots, frontmatters, and tools. |
| **1.09** | **Composite** | [`src/backend/core/documents.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/core/documents.py) | Tree hierarchy of specifications: PRD ➔ Epics ➔ User Stories ➔ Test Cases ➔ Assertion Nodes. |
| **1.10** | **Visitor** | [`src/backend/repos/ingest.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/repos/ingest.py) | AST visitor extracting exports, functions, test runners, and framework configurations across repositories. |
| **1.11** | **Acyclic Visitor** | [`src/backend/core/gherkin.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/core/gherkin.py) | Language-agnostic visitor parsing Gherkin scenarios and step definitions without circular dependencies. |
| **1.12** | **Double Dispatch** | [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) | Runtime routing of events between specific Agent personas and Tool types. |
| **1.13** | **Callback** | [`src/backend/harness/agui_protocol.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/agui_protocol.py) | SSE streaming callbacks delivering realtime token deltas, thought chunks, and approval interrupts. |
| **1.14** | **Context Object** | [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) | `HarnessContext` carrying `session_id`, `project_id`, `agent_id`, `mode`, tokens, and DB connection. |
| **1.15** | **Collecting Parameter** | [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) | Accumulator gathering findings, vulnerabilities, warnings, test cases, and coverage metrics in a run. |
| **1.16** | **Pipeline** | [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) | Linear pipeline coordinating Quality Gates G0 through G7 with deterministic preconditions. |
| **1.17** | **Rule Engine** | [`src/backend/harness/qe_guardrails.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/qe_guardrails.py) | Plan Mode guardrail: rejects destructive write/delete actions in plan mode; enforces binary allowlists. |

---

## 🏗️ Chapter 2: Structural, Proxy & Security Patterns

### 2.01 Adapter Pattern
- **File:** [`src/backend/harness/agui_protocol.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/agui_protocol.py) & [`src/frontend/lib/maf/protocol/agui.ts`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/frontend/lib/maf/protocol/agui.ts)
- **Role:** Converts Microsoft Agent Framework internal events into CopilotKit and AG-UI protocol standards consumed by React components.

### 2.02 Proxy Pattern
- **File:** [`src/backend/harness/llm_client.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/llm_client.py)
- **Role:** Intercepts LLM calls to enforce token budgets, API key validation, timeouts, and sanitized error masking.

### 2.03 Dynamic Proxy Pattern
- **File:** [`src/backend/harness/patterns.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/patterns.py) (`DynamicToolProxy`)
- **Role:** Wraps every tool invocation at runtime. Checks if human-in-the-loop approval is required for that specific quality gate before invoking target functions.

### 2.04 Decorator Pattern
- **File:** [`src/backend/core/security.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/core/security.py) & [`src/backend/harness/qe_tools.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/qe_tools.py)
- **Role:** Augments tool calls with execution duration timing, SHA-256 hash digests, and secret redaction.

### 2.05 Facade Pattern
- **File:** [`src/backend/harness/harness_agent.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/harness_agent.py) (`HarnessAgent`)
- **Role:** Unifies memory providers, mode controllers, todo managers, MCP clients, and LLM streaming behind a single `run(session, prompt)` interface.

---

## 💾 Chapter 3: Data & State Persistence Patterns

### 3.01 Repository Pattern
- **File:** [`src/backend/harness/project_repository.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/project_repository.py) (`ProjectRepository`)
- **Role:** Provides high-level domain query methods (`list_projects()`, `get_project()`, `find_project_by_name()`, `list_documents()`) abstracting SQLite queries.

### 3.02 Data Access Object (DAO) Pattern
- **File:** [`src/backend/db.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/db.py)
- **Role:** Manages SQLite low-level database connection pooling, cursor row-mapping (`row()`, `rows()`), and migration numbering.

### 3.03 Write-Ahead Log (WAL) Pattern
- **File:** [`src/backend/db.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/db.py#L47)
- **Role:** Configures `PRAGMA journal_mode=WAL` ensuring concurrent reading by multiple agents, CLI, and Web UI without locking writers.

### 3.04 Unit of Work Pattern
- **File:** [`src/backend/core/documents.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/core/documents.py)
- **Role:** Atomic transactions coordinating document versioning, SHA-256 calculations, and audit ledger entries in a single commit.

---

## ⚡ Chapter 4: Concurrency & Orchestration Patterns

### 4.01 Actor Model
- **File:** [`src/backend/harness/qe_agents.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/qe_agents.py) & [`src/backend/harness/magentic.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/harness/magentic.py)
- **Role:** Each of the 8 MAF agents functions as an autonomous actor with its own persona, allowed tool set, and message inbox.

### 4.02 Active Object Pattern
- **File:** [`src/backend/api/harness.py`](file:///Users/sarveshtalele/Downloads/agentic-harness/src/backend/api/harness.py) (`active_abort_events`)
- **Role:** Decouples chat invocation from asynchronous event loop execution, enabling the user to press `Stop Execution` or hit `Esc` to immediately cancel in-flight tasks.
