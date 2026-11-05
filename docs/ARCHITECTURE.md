# Complete File Inventory & Architectural Analysis: Agentic QE Platform

**Generated:** 2026-11-06  
**Repository Root:** `/Users/sarveshtalele/Downloads/agentic-harness`  
**Total Tracked & Source Files Scanned:** 661 (excluding `node_modules`, `.next`, `.git`, `__pycache__`)  
**Active Operational Files:** 554  
**Dead / Stale / Candidate Cleanup Files:** 71  
**State / Session / Data Files:** 34  

> [!IMPORTANT]
> This inventory was executed with zero mutations. No files have been deleted yet. Every file in the repository has been evaluated for role, status, and dependency impact so dead code can be safely removed without breaking active services or test suites.

## 1. System Architecture Diagram

The platform combines a **Next.js 14/16 App Router UI** (Port 3000), a **FastAPI backend** (Port 8000), **Microsoft Agent Framework (MAF 2.0)** multi-agent orchestration, **8 specialized QE agent personas**, **8 Human-in-the-Loop Quality Gates (G0–G7)**, **SQLite WAL persistence**, **Semantic & Tool Caching**, and **59 dynamic local skills**.

```mermaid
flowchart TD
    subgraph CLIENT [Frontend: Next.js 16 & React 18 (Port 3000)]
        UI_FRAME["Antigravity UI Shell: AppShell & ProjectShell"]
        STUDIOS["Studio Views: BA Studio | Bug Scan | Feature Builder | QE Studio | Governance | Observability"]
        HARNESS_VIEW["Agentic QE Harness: LeftSidebar | ChatContainer | ContextInspector | MagenticLedger | MCPTools"]
        CLIENT_MAF["Client MAF Protocols: AG-UI SSE Stream Adapter | CopilotKit Adapter | SlashCommandPalette"]
    end

    subgraph API_GATEWAY [Backend: FastAPI Gateway (Port 8000)]
        APP_FACTORY["FastAPI App Factory: CORS | SessionGuard | ErrorHandlers"]
        ROUTERS["15 Routers: /api/harness | /api/projects | /api/documents | /api/runs | /api/governance | /api/observability"]
        SECURITY["Security & Guardrails: PBKDF2 Auth | Fernet Tokens | Secret Scanner | Assertion Preservation Rule"]
    end

    subgraph AGENTIC_CORE [MAF 2.0 Multi-Agent QE Engine]
        HARNESS_AGENT["HarnessAgent Coordinator: Run Loop & SSE Event Generator"]
        MODE_PROV["AgentModeProvider: Plan Mode (Discovery) vs. Execute Mode (Action)"]
        MAGENTIC["Magentic-One Task Ledger: Subgoals & Handoff Router"]
        CACHE["Harness Cache: Semantic Prompt Cache & Deterministic Tool Cache"]
        
        subgraph SPECIALIST_PERSONAS [8 Specialized QE Agent Personas]
            A1["Principal Test Architect"]
            A2["Test Design Architect"]
            A3["Test Automation Engineer"]
            A4["QA Execution Engineer"]
            A5["Defect Diagnostician"]
            A6["Requirements Analyst"]
            A7["Business Analyst"]
            A8["Repo Intelligence Analyst"]
        end
    end

    subgraph QUALITY_GATES [8 Human-in-the-Loop Quality Gates]
        G0["G0: Intake & Discovery"]
        G1["G1: Requirements & User Stories"]
        G2["G2: Level-Allocated Test Plan"]
        G3["G3: Deterministic Test Design"]
        G4["G4: Test Code Generation"]
        G5["G5: Sandboxed Test Execution"]
        G6["G6: Assertion-Preserved Healing"]
        G7["G7: Release Sign-Off & Audit"]
    end

    subgraph SKILLS_ECOSYSTEM [Dynamic Local Skills & Extensions (59+ Skills)]
        DISCOVERY["LocalSkillDiscovery: Scans ./skills, ./plugins/agentic-qe, ./plugins/security-audit"]
        SPECTER["NVIDIA Skill Specter: 4 Security Checks & Scorecard Grading"]
        CLOUDFLARE["Cloudflare Security Audit: 15 Attack Classes & Ledger Audit"]
        MCP["MCP Client Manager: External Tool Protocol Connections"]
    end

    subgraph PERSISTENCE [Persistence & Cryptographic Knowledge Store]
        SQLITE["SQLite WAL (data/atlas.sqlite3): Projects, Docs, Versions, Findings, Runs, Users"]
        LEDGER["Append-Only Cryptographic Ledger: SHA-256 Chaining & Merkle Integrity"]
        SESSIONS["Persistent Session Records (.sessions/*.json): DeepSeek-style Tree"]
        WORKSPACES["Project Workspaces (data/projects/{id}): Git Repos & Ingested Code"]
    end

    CLIENT -->|REST / SSE HTTP| API_GATEWAY
    API_GATEWAY --> AGENTIC_CORE
    AGENTIC_CORE --> SPECIALIST_PERSONAS
    AGENTIC_CORE --> QUALITY_GATES
    AGENTIC_CORE --> SKILLS_ECOSYSTEM
    AGENTIC_CORE --> PERSISTENCE
    API_GATEWAY --> PERSISTENCE
```

## 2. Comparison Against 'Plan: Agentic QE design platform on MAF (2026-10-26)'

The plan from 2026-10-26 outlined explicit architectural decisions:
- **D1 (Remove)**: Legacy simulated imitation code to be removed.
- **D2 (Web UI Only)**: Focus exclusively on Web UI and eliminate obsolete standalone desktop wrappers/packaging.
- **D3 (Rename)**: Plugin renaming and standardization.
- **D4 (Reviewer)**: Independent confidence reviewer verifying each stage before gates open.
- **D5 (Removal List Approved)**: Section 8 removal list extended by D2.

### Status of Section 8 Removal Items

| Item from Section 8 Removal List | Original / Target Path | Status in Codebase | Finding & Action |
|---|---|---|---|
| Legacy imitation MAF engine | `src/backend/maf/core.py` | **REMOVED** | Gone; cleanly replaced by real MAF runtime `src/backend/maf/engine.py` |
| Simulated GitHub client (`ghp_simulated`) | `github/client.py` | **REMOVED** | Replaced by authentic Git CLI & API client in `src/backend/repos/` |
| Fake latency & hardcoded responses | `routes_agentic_qe.py` | **REMOVED** | Replaced by real streaming routes in `src/backend/api/` |
| Tautological tests (`assert True`) | `qe/scanner.py` | **REMOVED** | Replaced by strict assertion checkers and Ruff analysis |
| Monolithic 1021-line single page | `app/page.tsx` | **REMOVED** | Replaced by modular App Router (`/projects`, `/projects/[id]/*`) |
| Parallel Bash / PowerShell scripts in `scripts/` | `scripts/run.ps1`, `run.sh` | **CONSOLIDATED** | Master CLI created at `scripts/dev.py`; runners standardized |
| Legacy desktop packaging / static UI | `static/app.js`, `index.html` | **REMOVED** | Legacy static assets removed in favor of Next.js |
| Obsolete SDL3 database | `data/sdlc.sqlite3` | **REMOVED** | Cleanly superseded by production `data/atlas.sqlite3` |
| **Root Standalone Backend Duplicate** | `backend/` (21 files) | **PRESENT (DEAD)** | **CANDIDATE FOR REMOVAL.** Contains obsolete standalone precursor of `src/backend/harness/` |
| **Root Frontend Remnants in `src/`** | `src/app`, `src/components`, `src/lib` (41 files) | **PRESENT (DEAD)** | **CANDIDATE FOR REMOVAL.** Redundant copies prior to frontend migration into `src/frontend/` |
| **Root Next/Tailwind Config Duplicates** | `next.config.mjs`, `tailwind.config.ts`, `postcss.config.js` | **PRESENT (DEAD)** | **CANDIDATE FOR REMOVAL.** Unused by frontend compiler; `src/frontend/*` used |
| **Duplicate E2E Spec** | `e2e/harness.spec.ts` | **PRESENT (DEAD)** | **CANDIDATE FOR REMOVAL.** Exact copy of `tests/e2e/harness.spec.ts`; unreferenced by Playwright |
| **Orphaned Vitest Test** | `tests/unit/tc-test-001.test.ts` | **PRESENT (DEAD)** | **CANDIDATE FOR REMOVAL.** Broken generated sample with syntax error; not in pytest |
| **Ad-hoc Scratch Scripts** | `scratch/playwright_verify.py`, etc. | **PRESENT (DEAD)** | **CANDIDATE FOR REMOVAL.** Temporary scratch scripts |
| **Historical Reuse Audit Doc** | `docs/REUSE_AUDIT.md` | **PRESENT (OBSOLETE)** | **CANDIDATE FOR REMOVAL.** Documents 2026-10-26 branch audit; no longer relevant |

## 3. Detailed File Inventory by Module

### Active Core Backend (Core, API, DB, Migrations) (47 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/backend/__init__.py` | Repository asset | `ACTIVE` |
| `src/backend/api/__init__.py` | API router registry aggregation | `ACTIVE` |
| `src/backend/api/auth.py` | Authentication endpoints (login, logout, session check, account info) | `ACTIVE` |
| `src/backend/api/chat.py` | AG-UI protocol and interactive chat endpoints | `ACTIVE` |
| `src/backend/api/common.py` | Shared API response helpers, error wrappers, and validation models | `ACTIVE` |
| `src/backend/api/documents.py` | PRD/BRD document CRUD, version history, Gherkin validation, DOCX/PDF export | `ACTIVE` |
| `src/backend/api/findings.py` | Static code analysis and bug scan findings endpoints | `ACTIVE` |
| `src/backend/api/governance.py` | Cryptographic ledger verification and quality gate sign-off endpoints | `ACTIVE` |
| `src/backend/api/harness.py` | Agentic QE Harness endpoints (sessions, plugins, skills, evals, MCP tools, chat SSE) | `ACTIVE` |
| `src/backend/api/logs.py` | Observability log streaming and querying endpoints | `ACTIVE` |
| `src/backend/api/observability.py` | Run telemetry, token expenditure tracking, and failure analytics endpoints | `ACTIVE` |
| `src/backend/api/projects.py` | Project workspace CRUD, member management, and settings endpoints | `ACTIVE` |
| `src/backend/api/repository.py` | Git clone, branch listing, ZIP archive ingestion, and AST inspection endpoints | `ACTIVE` |
| `src/backend/api/runs.py` | MAF workflow run dispatch, status polling, and gate resume endpoints | `ACTIVE` |
| `src/backend/api/settings.py` | Centralized LLM provider credentials and model configuration endpoints | `ACTIVE` |
| `src/backend/api/skills.py` | Dynamic skill catalog and inspection endpoints | `ACTIVE` |
| `src/backend/api/templates.py` | Document template catalog and upload endpoints | `ACTIVE` |
| `src/backend/app.py` | FastAPI application factory, global middleware, router registrations, and lifecycle handlers | `ACTIVE` |
| `src/backend/cli.py` | Interactive CLI REPL harness runner and streaming terminal driver | `ACTIVE` |
| `src/backend/config.py` | Environment configuration loader, directory paths, and runtime settings | `ACTIVE` |
| `src/backend/core/auth.py` | Session guard, password hashing (PBKDF2), Fernet token encryption, RBAC matrix | `ACTIVE` |
| `src/backend/core/doc_checks.py` | Document structural validation, quality gate verification heuristics | `ACTIVE` |
| `src/backend/core/documents.py` | Document storage, version history diffing, markdown/DOCX operations | `ACTIVE` |
| `src/backend/core/errors.py` | Typed platform exceptions, standard diagnostic codes, structured error payloads | `ACTIVE` |
| `src/backend/core/files.py` | Sandboxed filesystem utilities, workspace path security, template seeding | `ACTIVE` |
| `src/backend/core/gates.py` | Quality gate state transitions, confidence scoring requirements, human sign-off logic | `ACTIVE` |
| `src/backend/core/gherkin.py` | Gherkin syntax parser, scenario extractor, step table validator | `ACTIVE` |
| `src/backend/core/ledger.py` | Append-only cryptographic audit ledger with SHA-256 hash chaining | `ACTIVE` |
| `src/backend/core/logs.py` | Structured daily JSONL application logging engine | `ACTIVE` |
| `src/backend/core/models.py` | Core Pydantic domain models for projects, runs, gates, documents, and users | `ACTIVE` |
| `src/backend/core/prompts.py` | Prompt template storage, seeding, and version management | `ACTIVE` |
| `src/backend/core/security.py` | Secret scanner (regex + entropy) and Fernet symmetric encryption | `ACTIVE` |
| `src/backend/core/seed_data.py` | Database seeder for default administrator account and initial workspace | `ACTIVE` |
| `src/backend/core/skills.py` | Skill filesystem loader, policy validator, and prompt reference injector | `ACTIVE` |
| `src/backend/db.py` | SQLite database connection manager, WAL mode configuration, and migration runner | `ACTIVE` |
| `src/backend/migrations/001_init.sql` | SQL schema migration script: 001_init.sql | `ACTIVE` |
| `src/backend/migrations/002_evaluations.sql` | SQL schema migration script: 002_evaluations.sql | `ACTIVE` |
| `src/backend/migrations/003_agent_governance.sql` | SQL schema migration script: 003_agent_governance.sql | `ACTIVE` |
| `src/backend/migrations/004_tool_calls.sql` | SQL schema migration script: 004_tool_calls.sql | `ACTIVE` |
| `src/backend/migrations/005_users.sql` | SQL schema migration script: 005_users.sql | `ACTIVE` |
| `src/backend/migrations/006_agent_plugin_names.sql` | SQL schema migration script: 006_agent_plugin_names.sql | `ACTIVE` |
| `src/backend/migrations/007_run_failures.sql` | SQL schema migration script: 007_run_failures.sql | `ACTIVE` |
| `src/backend/migrations/008_observability_indexes.sql` | SQL schema migration script: 008_observability_indexes.sql | `ACTIVE` |
| `src/backend/migrations/009_models_limits.sql` | SQL schema migration script: 009_models_limits.sql | `ACTIVE` |
| `src/backend/migrations/010_roles_members.sql` | SQL schema migration script: 010_roles_members.sql | `ACTIVE` |
| `src/backend/migrations/011_skills_tool_check.sql` | SQL schema migration script: 011_skills_tool_check.sql | `ACTIVE` |
| `src/backend/migrations/012_evaluation_metrics.sql` | SQL schema migration script: 012_evaluation_metrics.sql | `ACTIVE` |

### Active Backend Harness & Multi-Agent Engine (22 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/backend/harness/__init__.py` | Harness package initialization | `ACTIVE` |
| `src/backend/harness/agent_evals.py` | RAGAS agent evaluation engine with multi-metric scoring | `ACTIVE` |
| `src/backend/harness/agui_protocol.py` | AG-UI protocol streaming adapter and SSE event formatter | `ACTIVE` |
| `src/backend/harness/approval_manager.py` | Human-in-the-loop (HITL) tool execution approval manager | `ACTIVE` |
| `src/backend/harness/cache.py` | High-performance semantic prompt and tool-call cache | `ACTIVE` |
| `src/backend/harness/discovery.py` | Local dynamic skill & plugin discovery engine (59+ skills) | `ACTIVE` |
| `src/backend/harness/function_tool.py` | Declarative function tool wrapper and JSON schema generator | `ACTIVE` |
| `src/backend/harness/handoff.py` | Multi-agent handoff router and message routing executor | `ACTIVE` |
| `src/backend/harness/harness_agent.py` | Central coordinator agent driving the QE Harness multi-agent loop | `ACTIVE` |
| `src/backend/harness/llm_client.py` | Multi-provider LLM streaming client (OpenAI, DeepSeek, Anthropic, Custom) | `ACTIVE` |
| `src/backend/harness/llm_config.py` | LLM credential and provider configuration model | `ACTIVE` |
| `src/backend/harness/magentic.py` | Magentic-One style multi-agent task and subgoal ledger | `ACTIVE` |
| `src/backend/harness/mcp_manager.py` | Model Context Protocol (MCP) client connection manager | `ACTIVE` |
| `src/backend/harness/memory_provider.py` | Session context and file-backed long-term memory provider | `ACTIVE` |
| `src/backend/harness/mode_provider.py` | Plan vs. Execute mode gatekeeper and permission enforcer | `ACTIVE` |
| `src/backend/harness/patterns.py` | Implementation of 12 ashishpatel26 harness engineering patterns | `ACTIVE` |
| `src/backend/harness/project_repository.py` | Harness project workspace coordinator and context binder | `ACTIVE` |
| `src/backend/harness/qe_agents.py` | Registration of 8 specialized QE agent personas with prompt bindings | `ACTIVE` |
| `src/backend/harness/qe_guardrails.py` | Assertion Preservation Rule and code security guardrails | `ACTIVE` |
| `src/backend/harness/qe_tools.py` | Concrete QE tools (qe_discover_repo, qe_plan_strategy, qe_design_cases, qe_generate_code, etc.) | `ACTIVE` |
| `src/backend/harness/session.py` | Persistent session state store (.sessions/*.json) | `ACTIVE` |
| `src/backend/harness/todo_provider.py` | Interactive task and Todo item lifecycle tracker | `ACTIVE` |

### Active Microsoft Agent Framework (MAF) Workflows & Agents (47 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/backend/maf/agents/__init__.py` | Specialist agent definition and system prompt policy: __init__ | `ACTIVE` |
| `src/backend/maf/agents/bug_reviewer.py` | Specialist agent definition and system prompt policy: bug_reviewer | `ACTIVE` |
| `src/backend/maf/agents/business_analyst.py` | Specialist agent definition and system prompt policy: business_analyst | `ACTIVE` |
| `src/backend/maf/agents/confidence_reviewer.py` | Specialist agent definition and system prompt policy: confidence_reviewer | `ACTIVE` |
| `src/backend/maf/agents/defect_diagnostician.py` | Specialist agent definition and system prompt policy: defect_diagnostician | `ACTIVE` |
| `src/backend/maf/agents/feature_engineer.py` | Specialist agent definition and system prompt policy: feature_engineer | `ACTIVE` |
| `src/backend/maf/agents/policy.py` | Specialist agent definition and system prompt policy: policy | `ACTIVE` |
| `src/backend/maf/agents/principal_test_architect.py` | Specialist agent definition and system prompt policy: principal_test_architect | `ACTIVE` |
| `src/backend/maf/agents/project_copilot.py` | Specialist agent definition and system prompt policy: project_copilot | `ACTIVE` |
| `src/backend/maf/agents/qa_execution_engineer.py` | Specialist agent definition and system prompt policy: qa_execution_engineer | `ACTIVE` |
| `src/backend/maf/agents/repo_intelligence_analyst.py` | Specialist agent definition and system prompt policy: repo_intelligence_analyst | `ACTIVE` |
| `src/backend/maf/agents/requirements_analyst.py` | Specialist agent definition and system prompt policy: requirements_analyst | `ACTIVE` |
| `src/backend/maf/agents/test_automation_engineer.py` | Specialist agent definition and system prompt policy: test_automation_engineer | `ACTIVE` |
| `src/backend/maf/agents/test_design_architect.py` | Specialist agent definition and system prompt policy: test_design_architect | `ACTIVE` |
| `src/backend/maf/agui.py` | Microsoft Agent Framework AG-UI integration | `ACTIVE` |
| `src/backend/maf/engine.py` | Workflow execution engine with checkpointing and state resumption | `ACTIVE` |
| `src/backend/maf/evals/__init__.py` | Evaluation metric evaluator: __init__.py | `ACTIVE` |
| `src/backend/maf/evals/grader.py` | Evaluation metric evaluator: grader.py | `ACTIVE` |
| `src/backend/maf/evals/metrics.py` | Evaluation metric evaluator: metrics.py | `ACTIVE` |
| `src/backend/maf/evals/ragas_evaluator.py` | Evaluation metric evaluator: ragas_evaluator.py | `ACTIVE` |
| `src/backend/maf/evals/store.py` | Evaluation metric evaluator: store.py | `ACTIVE` |
| `src/backend/maf/governance.py` | MAF governance middleware and tool auditing | `ACTIVE` |
| `src/backend/maf/llm.py` | MAF LLM client wrapper | `ACTIVE` |
| `src/backend/maf/observability.py` | Agent telemetry and execution trace recorders | `ACTIVE` |
| `src/backend/maf/runtime.py` | Agent call lifecycle and prompt execution wrapper | `ACTIVE` |
| `src/backend/maf/skill_chat.py` | MAF skill injection into chat turns | `ACTIVE` |
| `src/backend/maf/tools/__init__.py` | MAF specialist tool implementation: __init__ | `ACTIVE` |
| `src/backend/maf/tools/common.py` | MAF specialist tool implementation: common | `ACTIVE` |
| `src/backend/maf/tools/grep.py` | MAF specialist tool implementation: grep | `ACTIVE` |
| `src/backend/maf/tools/list_documents.py` | MAF specialist tool implementation: list_documents | `ACTIVE` |
| `src/backend/maf/tools/list_files.py` | MAF specialist tool implementation: list_files | `ACTIVE` |
| `src/backend/maf/tools/list_findings.py` | MAF specialist tool implementation: list_findings | `ACTIVE` |
| `src/backend/maf/tools/project_status.py` | MAF specialist tool implementation: project_status | `ACTIVE` |
| `src/backend/maf/tools/read_document.py` | MAF specialist tool implementation: read_document | `ACTIVE` |
| `src/backend/maf/tools/read_file.py` | MAF specialist tool implementation: read_file | `ACTIVE` |
| `src/backend/maf/tools/remember.py` | MAF specialist tool implementation: remember | `ACTIVE` |
| `src/backend/maf/tools/save_document.py` | MAF specialist tool implementation: save_document | `ACTIVE` |
| `src/backend/maf/tools/search_documents.py` | MAF specialist tool implementation: search_documents | `ACTIVE` |
| `src/backend/maf/tools/start_workflow.py` | MAF specialist tool implementation: start_workflow | `ACTIVE` |
| `src/backend/maf/tools/verify_ledger.py` | MAF specialist tool implementation: verify_ledger | `ACTIVE` |
| `src/backend/maf/workflows/__init__.py` | MAF workflow builder and stage orchestrator: __init__ | `ACTIVE` |
| `src/backend/maf/workflows/ba.py` | MAF workflow builder and stage orchestrator: ba | `ACTIVE` |
| `src/backend/maf/workflows/bug_scan.py` | MAF workflow builder and stage orchestrator: bug_scan | `ACTIVE` |
| `src/backend/maf/workflows/change.py` | MAF workflow builder and stage orchestrator: change | `ACTIVE` |
| `src/backend/maf/workflows/edits.py` | MAF workflow builder and stage orchestrator: edits | `ACTIVE` |
| `src/backend/maf/workflows/qe.py` | MAF workflow builder and stage orchestrator: qe | `ACTIVE` |
| `src/backend/maf/workflows/shared.py` | MAF workflow builder and stage orchestrator: shared | `ACTIVE` |

### Active QE Logic & Repository Analysis (12 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/backend/qe/confidence.py` | QE Studio domain service: confidence | `ACTIVE` |
| `src/backend/qe/emit.py` | QE Studio domain service: emit | `ACTIVE` |
| `src/backend/qe/execution.py` | QE Studio domain service: execution | `ACTIVE` |
| `src/backend/qe/model.py` | QE Studio domain service: model | `ACTIVE` |
| `src/backend/qe/test_data.py` | QE Studio domain service: test_data | `ACTIVE` |
| `src/backend/qe/trace.py` | QE Studio domain service: trace | `ACTIVE` |
| `src/backend/repos/git.py` | Repository management and analysis service: git | `ACTIVE` |
| `src/backend/repos/github.py` | Repository management and analysis service: github | `ACTIVE` |
| `src/backend/repos/ingest.py` | Repository management and analysis service: ingest | `ACTIVE` |
| `src/backend/repos/sandbox.py` | Repository management and analysis service: sandbox | `ACTIVE` |
| `src/backend/repos/scan.py` | Repository management and analysis service: scan | `ACTIVE` |
| `src/backend/repos/static_analysis.py` | Repository management and analysis service: static_analysis | `ACTIVE` |

### Active Frontend App Router (src/frontend/app) (41 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/frontend/app/account/page.tsx` | Next.js App Router route page/handler: account/page.tsx | `ACTIVE` |
| `src/frontend/app/agents/[key]/page.tsx` | Next.js App Router route page/handler: agents/[key]/page.tsx | `ACTIVE` |
| `src/frontend/app/agents/page.tsx` | Next.js App Router route page/handler: agents/page.tsx | `ACTIVE` |
| `src/frontend/app/api/copilotkit/[[...path]]/route.ts` | Next.js App Router route page/handler: api/copilotkit/[[...path]]/route.ts | `ACTIVE` |
| `src/frontend/app/approvals/page.tsx` | Next.js App Router route page/handler: approvals/page.tsx | `ACTIVE` |
| `src/frontend/app/chat/[id]/page.tsx` | Next.js App Router route page/handler: chat/[id]/page.tsx | `ACTIVE` |
| `src/frontend/app/docs/[slug]/page.tsx` | Next.js App Router route page/handler: docs/[slug]/page.tsx | `ACTIVE` |
| `src/frontend/app/docs/layout.tsx` | Next.js App Router route page/handler: docs/layout.tsx | `ACTIVE` |
| `src/frontend/app/docs/page.tsx` | Next.js App Router route page/handler: docs/page.tsx | `ACTIVE` |
| `src/frontend/app/documents/page.tsx` | Next.js App Router route page/handler: documents/page.tsx | `ACTIVE` |
| `src/frontend/app/error.tsx` | Next.js App Router route page/handler: error.tsx | `ACTIVE` |
| `src/frontend/app/findings/page.tsx` | Next.js App Router route page/handler: findings/page.tsx | `ACTIVE` |
| `src/frontend/app/global-error.tsx` | Next.js App Router route page/handler: global-error.tsx | `ACTIVE` |
| `src/frontend/app/globals.css` | Next.js App Router route page/handler: globals.css | `ACTIVE` |
| `src/frontend/app/harness/page.tsx` | Next.js App Router route page/handler: harness/page.tsx | `ACTIVE` |
| `src/frontend/app/layout.tsx` | Next.js App Router route page/handler: layout.tsx | `ACTIVE` |
| `src/frontend/app/login/page.tsx` | Next.js App Router route page/handler: login/page.tsx | `ACTIVE` |
| `src/frontend/app/observability/page.tsx` | Next.js App Router route page/handler: observability/page.tsx | `ACTIVE` |
| `src/frontend/app/page.tsx` | Next.js App Router route page/handler: page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/approvals/page.tsx` | Next.js App Router route page/handler: projects/[id]/approvals/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/ba/page.tsx` | Next.js App Router route page/handler: projects/[id]/ba/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/bugs/page.tsx` | Next.js App Router route page/handler: projects/[id]/bugs/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/chat/page.tsx` | Next.js App Router route page/handler: projects/[id]/chat/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/documents/[docId]/page.tsx` | Next.js App Router route page/handler: projects/[id]/documents/[docId]/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/documents/page.tsx` | Next.js App Router route page/handler: projects/[id]/documents/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/feature/page.tsx` | Next.js App Router route page/handler: projects/[id]/feature/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/governance/page.tsx` | Next.js App Router route page/handler: projects/[id]/governance/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/harness/page.tsx` | Next.js App Router route page/handler: projects/[id]/harness/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/layout.tsx` | Next.js App Router route page/handler: projects/[id]/layout.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/observability/page.tsx` | Next.js App Router route page/handler: projects/[id]/observability/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/page.tsx` | Next.js App Router route page/handler: projects/[id]/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/prompts/page.tsx` | Next.js App Router route page/handler: projects/[id]/prompts/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/qe/page.tsx` | Next.js App Router route page/handler: projects/[id]/qe/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/repository/page.tsx` | Next.js App Router route page/handler: projects/[id]/repository/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/runs/[runId]/page.tsx` | Next.js App Router route page/handler: projects/[id]/runs/[runId]/page.tsx | `ACTIVE` |
| `src/frontend/app/projects/[id]/runs/page.tsx` | Next.js App Router route page/handler: projects/[id]/runs/page.tsx | `ACTIVE` |
| `src/frontend/app/settings/page.tsx` | Next.js App Router route page/handler: settings/page.tsx | `ACTIVE` |
| `src/frontend/app/skills/page.tsx` | Next.js App Router route page/handler: skills/page.tsx | `ACTIVE` |
| `src/frontend/app/templates/page.tsx` | Next.js App Router route page/handler: templates/page.tsx | `ACTIVE` |
| `src/frontend/app/usage/page.tsx` | Next.js App Router route page/handler: usage/page.tsx | `ACTIVE` |
| `src/frontend/app/users/page.tsx` | Next.js App Router route page/handler: users/page.tsx | `ACTIVE` |

### Active Frontend UI Components (src/frontend/components) (31 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/frontend/components/AppShell.tsx` | Active React component: AppShell.tsx | `ACTIVE` |
| `src/frontend/components/ApprovalsList.tsx` | Active React component: ApprovalsList.tsx | `ACTIVE` |
| `src/frontend/components/AuthGate.tsx` | Active React component: AuthGate.tsx | `ACTIVE` |
| `src/frontend/components/Chat.tsx` | Active React component: Chat.tsx | `ACTIVE` |
| `src/frontend/components/DocumentEditor.tsx` | Active React component: DocumentEditor.tsx | `ACTIVE` |
| `src/frontend/components/EvalScores.tsx` | Active React component: EvalScores.tsx | `ACTIVE` |
| `src/frontend/components/HarnessView.tsx` | Active React component: HarnessView.tsx | `ACTIVE` |
| `src/frontend/components/ModelPicker.tsx` | Active React component: ModelPicker.tsx | `ACTIVE` |
| `src/frontend/components/Observability.tsx` | Active React component: Observability.tsx | `ACTIVE` |
| `src/frontend/components/ProjectShell.tsx` | Active React component: ProjectShell.tsx | `ACTIVE` |
| `src/frontend/components/RunPanel.tsx` | Active React component: RunPanel.tsx | `ACTIVE` |
| `src/frontend/components/chat/ChatContainer.tsx` | Active React component: ChatContainer.tsx | `ACTIVE` |
| `src/frontend/components/chat/ChatMessageItem.tsx` | Active React component: ChatMessageItem.tsx | `ACTIVE` |
| `src/frontend/components/chat/PromptInput.tsx` | Active React component: PromptInput.tsx | `ACTIVE` |
| `src/frontend/components/chat/QualityGateApprovalCard.tsx` | Active React component: QualityGateApprovalCard.tsx | `ACTIVE` |
| `src/frontend/components/chat/SlashCommandPalette.tsx` | Active React component: SlashCommandPalette.tsx | `ACTIVE` |
| `src/frontend/components/chat/StopButton.tsx` | Active React component: StopButton.tsx | `ACTIVE` |
| `src/frontend/components/chat/ThinkingAccordion.tsx` | Active React component: ThinkingAccordion.tsx | `ACTIVE` |
| `src/frontend/components/chat/ToolCallCard.tsx` | Active React component: ToolCallCard.tsx | `ACTIVE` |
| `src/frontend/components/harness-ui/Badge.tsx` | Active React component: Badge.tsx | `ACTIVE` |
| `src/frontend/components/harness-ui/Button.tsx` | Active React component: Button.tsx | `ACTIVE` |
| `src/frontend/components/inspector/ContextInspector.tsx` | Active React component: ContextInspector.tsx | `ACTIVE` |
| `src/frontend/components/inspector/MCPToolsExplorer.tsx` | Active React component: MCPToolsExplorer.tsx | `ACTIVE` |
| `src/frontend/components/inspector/MagenticLedgerView.tsx` | Active React component: MagenticLedgerView.tsx | `ACTIVE` |
| `src/frontend/components/inspector/QualityGatesTracker.tsx` | Active React component: QualityGatesTracker.tsx | `ACTIVE` |
| `src/frontend/components/inspector/TodoChecklist.tsx` | Active React component: TodoChecklist.tsx | `ACTIVE` |
| `src/frontend/components/left-sidebar/LeftSidebar.tsx` | Active React component: LeftSidebar.tsx | `ACTIVE` |
| `src/frontend/components/modals/MCPSettingsModal.tsx` | Active React component: MCPSettingsModal.tsx | `ACTIVE` |
| `src/frontend/components/modals/ModelConfigModal.tsx` | Active React component: ModelConfigModal.tsx | `ACTIVE` |
| `src/frontend/components/theme/ThemeToggle.tsx` | Active React component: ThemeToggle.tsx | `ACTIVE` |
| `src/frontend/components/ui.tsx` | Active React component: ui.tsx | `ACTIVE` |

### Active Frontend Lib, State & Protocol Adapters (src/frontend/lib) (29 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/frontend/.gitignore` | Frontend build and package configuration: .gitignore | `ACTIVE` |
| `src/frontend/AGENTS.md` | Frontend build and package configuration: AGENTS.md | `ACTIVE` |
| `src/frontend/content/docs.ts` | Built-in documentation content dictionary | `ACTIVE` |
| `src/frontend/eslint.config.mjs` | Frontend build and package configuration: eslint.config.mjs | `ACTIVE` |
| `src/frontend/lib/api.ts` | Frontend client library / MAF protocol: api.ts | `ACTIVE` |
| `src/frontend/lib/maf/core/AgentModeProvider.ts` | Frontend client library / MAF protocol: maf/core/AgentModeProvider.ts | `ACTIVE` |
| `src/frontend/lib/maf/core/AgentSession.ts` | Frontend client library / MAF protocol: maf/core/AgentSession.ts | `ACTIVE` |
| `src/frontend/lib/maf/core/AgentSkillsProvider.ts` | Frontend client library / MAF protocol: maf/core/AgentSkillsProvider.ts | `ACTIVE` |
| `src/frontend/lib/maf/core/FileMemoryProvider.ts` | Frontend client library / MAF protocol: maf/core/FileMemoryProvider.ts | `ACTIVE` |
| `src/frontend/lib/maf/core/HarnessAgent.ts` | Frontend client library / MAF protocol: maf/core/HarnessAgent.ts | `ACTIVE` |
| `src/frontend/lib/maf/core/TodoProvider.ts` | Frontend client library / MAF protocol: maf/core/TodoProvider.ts | `ACTIVE` |
| `src/frontend/lib/maf/guardrails/QEGuardrails.ts` | Frontend client library / MAF protocol: maf/guardrails/QEGuardrails.ts | `ACTIVE` |
| `src/frontend/lib/maf/memory/CompactionEngine.ts` | Frontend client library / MAF protocol: maf/memory/CompactionEngine.ts | `ACTIVE` |
| `src/frontend/lib/maf/memory/SessionStore.ts` | Frontend client library / MAF protocol: maf/memory/SessionStore.ts | `ACTIVE` |
| `src/frontend/lib/maf/orchestrators/MagenticQEOrchestrator.ts` | Frontend client library / MAF protocol: maf/orchestrators/MagenticQEOrchestrator.ts | `ACTIVE` |
| `src/frontend/lib/maf/orchestrators/QEHandoffExecutor.ts` | Frontend client library / MAF protocol: maf/orchestrators/QEHandoffExecutor.ts | `ACTIVE` |
| `src/frontend/lib/maf/protocol/agui.ts` | Frontend client library / MAF protocol: maf/protocol/agui.ts | `ACTIVE` |
| `src/frontend/lib/maf/tools/FunctionTool.ts` | Frontend client library / MAF protocol: maf/tools/FunctionTool.ts | `ACTIVE` |
| `src/frontend/lib/maf/tools/MCPClientManager.ts` | Frontend client library / MAF protocol: maf/tools/MCPClientManager.ts | `ACTIVE` |
| `src/frontend/lib/maf/tools/ToolApprovalManager.ts` | Frontend client library / MAF protocol: maf/tools/ToolApprovalManager.ts | `ACTIVE` |
| `src/frontend/lib/maf/types/index.ts` | Frontend client library / MAF protocol: maf/types/index.ts | `ACTIVE` |
| `src/frontend/lib/qe/agents/index.ts` | Frontend client library / MAF protocol: qe/agents/index.ts | `ACTIVE` |
| `src/frontend/lib/qe/tools/index.ts` | Frontend client library / MAF protocol: qe/tools/index.ts | `ACTIVE` |
| `src/frontend/next-env.d.ts` | Frontend build and package configuration: next-env.d.ts | `ACTIVE` |
| `src/frontend/next.config.ts` | Frontend build and package configuration: next.config.ts | `ACTIVE` |
| `src/frontend/package-lock.json` | Frontend build and package configuration: package-lock.json | `ACTIVE` |
| `src/frontend/package.json` | Frontend build and package configuration: package.json | `ACTIVE` |
| `src/frontend/postcss.config.mjs` | Frontend build and package configuration: postcss.config.mjs | `ACTIVE` |
| `src/frontend/tsconfig.json` | Frontend build and package configuration: tsconfig.json | `ACTIVE` |

### Active Skills & Plugins (skills/, plugins/) (126 files)

| File Path | Role / Description | Status |
|---|---|---|
| `plugins/agentic-qe/skills/qe-data/SKILL.md` | Plugin skill specification: qe-data | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-data/agents/openai.yaml` | Plugin skill specification: qe-data | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-data/evals/evals.json` | Plugin skill specification: qe-data | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-design/SKILL.md` | Plugin skill specification: qe-design | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-design/agents/openai.yaml` | Plugin skill specification: qe-design | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-design/evals/evals.json` | Plugin skill specification: qe-design | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-discover/SKILL.md` | Plugin skill specification: qe-discover | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-discover/agents/openai.yaml` | Plugin skill specification: qe-discover | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-discover/evals/evals.json` | Plugin skill specification: qe-discover | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-doctor/SKILL.md` | Plugin skill specification: qe-doctor | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-doctor/agents/openai.yaml` | Plugin skill specification: qe-doctor | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-doctor/evals/evals.json` | Plugin skill specification: qe-doctor | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-doctor/scripts/agentic-qe.ts` | Plugin skill specification: qe-doctor | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-execute/SKILL.md` | Plugin skill specification: qe-execute | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-execute/agents/openai.yaml` | Plugin skill specification: qe-execute | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-execute/evals/evals.json` | Plugin skill specification: qe-execute | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-generate/SKILL.md` | Plugin skill specification: qe-generate | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-generate/agents/openai.yaml` | Plugin skill specification: qe-generate | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-generate/evals/evals.json` | Plugin skill specification: qe-generate | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-heal/SKILL.md` | Plugin skill specification: qe-heal | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-heal/agents/openai.yaml` | Plugin skill specification: qe-heal | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-heal/evals/evals.json` | Plugin skill specification: qe-heal | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/SKILL.md` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/agents/openai.yaml` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/evals/evals.json` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/scripts/dashboard-server.ts` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/scripts/dashboard-ui.ts` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/scripts/export-session.ts` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/scripts/panel-split.ts` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/scripts/panel.ts` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-panel/scripts/zip.ts` | Plugin skill specification: qe-panel | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-plan/SKILL.md` | Plugin skill specification: qe-plan | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-plan/agents/openai.yaml` | Plugin skill specification: qe-plan | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-plan/evals/evals.json` | Plugin skill specification: qe-plan | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-requirements/SKILL.md` | Plugin skill specification: qe-requirements | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-requirements/agents/openai.yaml` | Plugin skill specification: qe-requirements | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-requirements/evals/evals.json` | Plugin skill specification: qe-requirements | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-sign/SKILL.md` | Plugin skill specification: qe-sign | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-sign/agents/openai.yaml` | Plugin skill specification: qe-sign | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-sign/evals/evals.json` | Plugin skill specification: qe-sign | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-start/SKILL.md` | Plugin skill specification: qe-start | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-start/agents/openai.yaml` | Plugin skill specification: qe-start | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-start/evals/evals.json` | Plugin skill specification: qe-start | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-stories/SKILL.md` | Plugin skill specification: qe-stories | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-stories/agents/openai.yaml` | Plugin skill specification: qe-stories | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-stories/evals/evals.json` | Plugin skill specification: qe-stories | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-sync/SKILL.md` | Plugin skill specification: qe-sync | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-sync/agents/openai.yaml` | Plugin skill specification: qe-sync | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-sync/evals/evals.json` | Plugin skill specification: qe-sync | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-trace/SKILL.md` | Plugin skill specification: qe-trace | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-trace/agents/openai.yaml` | Plugin skill specification: qe-trace | `ACTIVE` |
| `plugins/agentic-qe/skills/qe-trace/evals/evals.json` | Plugin skill specification: qe-trace | `ACTIVE` |
| `plugins/security-audit/AI-AND-LLM.md` | Security audit rulebook / test script: AI-AND-LLM.md | `ACTIVE` |
| `plugins/security-audit/ATTACK-CLASSES.md` | Security audit rulebook / test script: ATTACK-CLASSES.md | `ACTIVE` |
| `plugins/security-audit/CLIENT-SIDE.md` | Security audit rulebook / test script: CLIENT-SIDE.md | `ACTIVE` |
| `plugins/security-audit/CLOUD-AND-DEPLOYMENT.md` | Security audit rulebook / test script: CLOUD-AND-DEPLOYMENT.md | `ACTIVE` |
| `plugins/security-audit/DATA-ISOLATION-AND-LIFECYCLE.md` | Security audit rulebook / test script: DATA-ISOLATION-AND-LIFECYCLE.md | `ACTIVE` |
| `plugins/security-audit/DESKTOP-MOBILE-AND-LOCAL-IPC.md` | Security audit rulebook / test script: DESKTOP-MOBILE-AND-LOCAL-IPC.md | `ACTIVE` |
| `plugins/security-audit/HUNTING.md` | Security audit rulebook / test script: HUNTING.md | `ACTIVE` |
| `plugins/security-audit/MEMORY-SAFETY-AND-BINARY.md` | Security audit rulebook / test script: MEMORY-SAFETY-AND-BINARY.md | `ACTIVE` |
| `plugins/security-audit/PROTOCOLS-RPC-AND-MESSAGING.md` | Security audit rulebook / test script: PROTOCOLS-RPC-AND-MESSAGING.md | `ACTIVE` |
| `plugins/security-audit/RECONNAISSANCE.md` | Security audit rulebook / test script: RECONNAISSANCE.md | `ACTIVE` |
| `plugins/security-audit/RESOURCE-EXHAUSTION-AND-AVAILABILITY.md` | Security audit rulebook / test script: RESOURCE-EXHAUSTION-AND-AVAILABILITY.md | `ACTIVE` |
| `plugins/security-audit/SKILL.md` | Security audit rulebook / test script: SKILL.md | `ACTIVE` |
| `plugins/security-audit/SUPPLY-CHAIN-AND-RELEASE.md` | Security audit rulebook / test script: SUPPLY-CHAIN-AND-RELEASE.md | `ACTIVE` |
| `plugins/security-audit/VALIDATION-AND-REPORTING.md` | Security audit rulebook / test script: VALIDATION-AND-REPORTING.md | `ACTIVE` |
| `plugins/security-audit/WEB-PROTOCOL-AND-AUTH.md` | Security audit rulebook / test script: WEB-PROTOCOL-AND-AUTH.md | `ACTIVE` |
| `plugins/security-audit/report-schema.json` | Security audit rulebook / test script: report-schema.json | `ACTIVE` |
| `plugins/security-audit/validate-coverage-ledger.cjs` | Security audit rulebook / test script: validate-coverage-ledger.cjs | `ACTIVE` |
| `plugins/security-audit/validate-coverage-ledger.test.cjs` | Security audit rulebook / test script: validate-coverage-ledger.test.cjs | `ACTIVE` |
| `plugins/security-audit/validate-findings.cjs` | Security audit rulebook / test script: validate-findings.cjs | `ACTIVE` |
| `plugins/security-audit/validate-findings.test.cjs` | Security audit rulebook / test script: validate-findings.test.cjs | `ACTIVE` |
| `skills/README.md` | Local QE skill specification and execution scripts: README.md | `ACTIVE` |
| `skills/analyzing-repositories/SKILL.md` | Local QE skill specification and execution scripts: analyzing-repositories | `ACTIVE` |
| `skills/analyzing-repositories/evals/evals.json` | Local QE skill specification and execution scripts: analyzing-repositories | `ACTIVE` |
| `skills/analyzing-repositories/references/STACK_SIGNALS.md` | Local QE skill specification and execution scripts: analyzing-repositories | `ACTIVE` |
| `skills/analyzing-repositories/scripts/scan-repo.ts` | Local QE skill specification and execution scripts: analyzing-repositories | `ACTIVE` |
| `skills/authoring-user-stories/SKILL.md` | Local QE skill specification and execution scripts: authoring-user-stories | `ACTIVE` |
| `skills/authoring-user-stories/evals/evals.json` | Local QE skill specification and execution scripts: authoring-user-stories | `ACTIVE` |
| `skills/authoring-user-stories/references/TEMPLATE.md` | Local QE skill specification and execution scripts: authoring-user-stories | `ACTIVE` |
| `skills/authoring-user-stories/scripts/export-cases.ts` | Local QE skill specification and execution scripts: authoring-user-stories | `ACTIVE` |
| `skills/building-qe-dashboard/SKILL.md` | Local QE skill specification and execution scripts: building-qe-dashboard | `ACTIVE` |
| `skills/building-qe-dashboard/evals/evals.json` | Local QE skill specification and execution scripts: building-qe-dashboard | `ACTIVE` |
| `skills/building-qe-dashboard/scripts/build-trace-report.ts` | Local QE skill specification and execution scripts: building-qe-dashboard | `ACTIVE` |
| `skills/building-qe-dashboard/scripts/gate-report-md.ts` | Local QE skill specification and execution scripts: building-qe-dashboard | `ACTIVE` |
| `skills/building-qe-dashboard/scripts/html.ts` | Local QE skill specification and execution scripts: building-qe-dashboard | `ACTIVE` |
| `skills/designing-test-cases/SKILL.md` | Local QE skill specification and execution scripts: designing-test-cases | `ACTIVE` |
| `skills/designing-test-cases/evals/evals.json` | Local QE skill specification and execution scripts: designing-test-cases | `ACTIVE` |
| `skills/designing-test-cases/references/ORACLE_TYPES.md` | Local QE skill specification and execution scripts: designing-test-cases | `ACTIVE` |
| `skills/designing-test-cases/scripts/check-confidence.ts` | Local QE skill specification and execution scripts: designing-test-cases | `ACTIVE` |
| `skills/designing-test-cases/scripts/generate-cases.ts` | Local QE skill specification and execution scripts: designing-test-cases | `ACTIVE` |
| `skills/executing-tests/SKILL.md` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/executing-tests/evals/evals.json` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/executing-tests/references/RUNNER_REGISTRY.md` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/executing-tests/references/VERSIONS.md` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/executing-tests/scripts/collect-evidence.ts` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/executing-tests/scripts/mcp-evidence.ts` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/executing-tests/scripts/parse-junit.ts` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/executing-tests/scripts/run-isolated.ts` | Local QE skill specification and execution scripts: executing-tests | `ACTIVE` |
| `skills/extracting-requirements/SKILL.md` | Local QE skill specification and execution scripts: extracting-requirements | `ACTIVE` |
| `skills/extracting-requirements/evals/evals.json` | Local QE skill specification and execution scripts: extracting-requirements | `ACTIVE` |
| `skills/extracting-requirements/references/REQUIREMENT_RULES.md` | Local QE skill specification and execution scripts: extracting-requirements | `ACTIVE` |
| `skills/extracting-requirements/scripts/extract-contracts.ts` | Local QE skill specification and execution scripts: extracting-requirements | `ACTIVE` |
| `skills/generating-test-code/SKILL.md` | Local QE skill specification and execution scripts: generating-test-code | `ACTIVE` |
| `skills/generating-test-code/assets/playwright.config.ts` | Local QE skill specification and execution scripts: generating-test-code | `ACTIVE` |
| `skills/generating-test-code/evals/evals.json` | Local QE skill specification and execution scripts: generating-test-code | `ACTIVE` |
| `skills/generating-test-code/references/LANGUAGE_RULES.md` | Local QE skill specification and execution scripts: generating-test-code | `ACTIVE` |
| `skills/generating-test-code/references/VERSIONS.md` | Local QE skill specification and execution scripts: generating-test-code | `ACTIVE` |
| `skills/generating-test-code/scripts/emit-tests.ts` | Local QE skill specification and execution scripts: generating-test-code | `ACTIVE` |
| `skills/generating-test-data/SKILL.md` | Local QE skill specification and execution scripts: generating-test-data | `ACTIVE` |
| `skills/generating-test-data/assets/schema-templates.json` | Local QE skill specification and execution scripts: generating-test-data | `ACTIVE` |
| `skills/generating-test-data/evals/evals.json` | Local QE skill specification and execution scripts: generating-test-data | `ACTIVE` |
| `skills/generating-test-data/scripts/synthesize-data.ts` | Local QE skill specification and execution scripts: generating-test-data | `ACTIVE` |
| `skills/healing-tests/SKILL.md` | Local QE skill specification and execution scripts: healing-tests | `ACTIVE` |
| `skills/healing-tests/evals/evals.json` | Local QE skill specification and execution scripts: healing-tests | `ACTIVE` |
| `skills/healing-tests/references/HEALING_PATTERNS.md` | Local QE skill specification and execution scripts: healing-tests | `ACTIVE` |
| `skills/healing-tests/scripts/apply-healing.ts` | Local QE skill specification and execution scripts: healing-tests | `ACTIVE` |
| `skills/healing-tests/scripts/diagnose-failure.ts` | Local QE skill specification and execution scripts: healing-tests | `ACTIVE` |
| `skills/planning-tests/SKILL.md` | Local QE skill specification and execution scripts: planning-tests | `ACTIVE` |
| `skills/planning-tests/evals/evals.json` | Local QE skill specification and execution scripts: planning-tests | `ACTIVE` |
| `skills/planning-tests/references/LEVEL_GUIDELINES.md` | Local QE skill specification and execution scripts: planning-tests | `ACTIVE` |
| `skills/planning-tests/scripts/calculate-risk.ts` | Local QE skill specification and execution scripts: planning-tests | `ACTIVE` |
| `skills/tracing-coverage/SKILL.md` | Local QE skill specification and execution scripts: tracing-coverage | `ACTIVE` |
| `skills/tracing-coverage/evals/evals.json` | Local QE skill specification and execution scripts: tracing-coverage | `ACTIVE` |
| `skills/tracing-coverage/scripts/build-matrix.ts` | Local QE skill specification and execution scripts: tracing-coverage | `ACTIVE` |
| `skills/tracing-coverage/scripts/check-gate.ts` | Local QE skill specification and execution scripts: tracing-coverage | `ACTIVE` |

### Active Evals, Prompts & Templates (42 files)

| File Path | Role / Description | Status |
|---|---|---|
| `evals/benchmarks/finance/labels.json` | Evaluation benchmark dataset / agent evaluation scenario: labels.json | `ACTIVE` |
| `evals/benchmarks/shop/cases/bug-reviewer.json` | Evaluation benchmark dataset / agent evaluation scenario: bug-reviewer.json | `ACTIVE` |
| `evals/benchmarks/shop/cases/business-analyst.json` | Evaluation benchmark dataset / agent evaluation scenario: business-analyst.json | `ACTIVE` |
| `evals/benchmarks/shop/cases/requirements-analyst.json` | Evaluation benchmark dataset / agent evaluation scenario: requirements-analyst.json | `ACTIVE` |
| `evals/benchmarks/shop/cases/test-automation-engineer.json` | Evaluation benchmark dataset / agent evaluation scenario: test-automation-engineer.json | `ACTIVE` |
| `evals/benchmarks/shop/labels.json` | Evaluation benchmark dataset / agent evaluation scenario: labels.json | `ACTIVE` |
| `evals/benchmarks/shop/repo/cart.py` | Evaluation benchmark dataset / agent evaluation scenario: cart.py | `ACTIVE` |
| `evals/benchmarks/shop/repo/inventory.py` | Evaluation benchmark dataset / agent evaluation scenario: inventory.py | `ACTIVE` |
| `evals/benchmarks/shop/repo/money.py` | Evaluation benchmark dataset / agent evaluation scenario: money.py | `ACTIVE` |
| `evals/benchmarks/shop/repo/orders.py` | Evaluation benchmark dataset / agent evaluation scenario: orders.py | `ACTIVE` |
| `evals/benchmarks/shop/repo/pricing.py` | Evaluation benchmark dataset / agent evaluation scenario: pricing.py | `ACTIVE` |
| `evals/benchmarks/shop/repo/pytest.ini` | Evaluation benchmark dataset / agent evaluation scenario: pytest.ini | `ACTIVE` |
| `evals/benchmarks/shop/repo/tests/test_money.py` | Evaluation benchmark dataset / agent evaluation scenario: test_money.py | `ACTIVE` |
| `evals/benchmarks/shop/repo/validators.py` | Evaluation benchmark dataset / agent evaluation scenario: validators.py | `ACTIVE` |
| `evals/bug-reviewer.json` | Evaluation benchmark dataset / agent evaluation scenario: bug-reviewer.json | `ACTIVE` |
| `evals/business-analyst.json` | Evaluation benchmark dataset / agent evaluation scenario: business-analyst.json | `ACTIVE` |
| `evals/confidence-reviewer.json` | Evaluation benchmark dataset / agent evaluation scenario: confidence-reviewer.json | `ACTIVE` |
| `evals/defect-diagnostician.json` | Evaluation benchmark dataset / agent evaluation scenario: defect-diagnostician.json | `ACTIVE` |
| `evals/feature-engineer.json` | Evaluation benchmark dataset / agent evaluation scenario: feature-engineer.json | `ACTIVE` |
| `evals/principal-test-architect.json` | Evaluation benchmark dataset / agent evaluation scenario: principal-test-architect.json | `ACTIVE` |
| `evals/project-copilot.json` | Evaluation benchmark dataset / agent evaluation scenario: project-copilot.json | `ACTIVE` |
| `evals/qa-execution-engineer.json` | Evaluation benchmark dataset / agent evaluation scenario: qa-execution-engineer.json | `ACTIVE` |
| `evals/repo-intelligence-analyst.json` | Evaluation benchmark dataset / agent evaluation scenario: repo-intelligence-analyst.json | `ACTIVE` |
| `evals/requirements-analyst.json` | Evaluation benchmark dataset / agent evaluation scenario: requirements-analyst.json | `ACTIVE` |
| `evals/skills/checks.json` | Evaluation benchmark dataset / agent evaluation scenario: checks.json | `ACTIVE` |
| `evals/test-automation-engineer.json` | Evaluation benchmark dataset / agent evaluation scenario: test-automation-engineer.json | `ACTIVE` |
| `evals/test-design-architect.json` | Evaluation benchmark dataset / agent evaluation scenario: test-design-architect.json | `ACTIVE` |
| `prompts/bug-reviewer.md` | Specialist agent baseline system prompt template: bug-reviewer | `ACTIVE` |
| `prompts/business-analyst.md` | Specialist agent baseline system prompt template: business-analyst | `ACTIVE` |
| `prompts/confidence-reviewer.md` | Specialist agent baseline system prompt template: confidence-reviewer | `ACTIVE` |
| `prompts/defect-diagnostician.md` | Specialist agent baseline system prompt template: defect-diagnostician | `ACTIVE` |
| `prompts/feature-engineer.md` | Specialist agent baseline system prompt template: feature-engineer | `ACTIVE` |
| `prompts/principal-test-architect.md` | Specialist agent baseline system prompt template: principal-test-architect | `ACTIVE` |
| `prompts/project-copilot.md` | Specialist agent baseline system prompt template: project-copilot | `ACTIVE` |
| `prompts/qa-execution-engineer.md` | Specialist agent baseline system prompt template: qa-execution-engineer | `ACTIVE` |
| `prompts/repo-intelligence-analyst.md` | Specialist agent baseline system prompt template: repo-intelligence-analyst | `ACTIVE` |
| `prompts/requirements-analyst.md` | Specialist agent baseline system prompt template: requirements-analyst | `ACTIVE` |
| `prompts/test-automation-engineer.md` | Specialist agent baseline system prompt template: test-automation-engineer | `ACTIVE` |
| `prompts/test-design-architect.md` | Specialist agent baseline system prompt template: test-design-architect | `ACTIVE` |
| `templates/brd.md` | BA document starter template: brd | `ACTIVE` |
| `templates/prd.md` | BA document starter template: prd | `ACTIVE` |
| `templates/stories.md` | BA document starter template: stories | `ACTIVE` |

### Active Scripts, DevOps & Launchers (33 files)

| File Path | Role / Description | Status |
|---|---|---|
| `.claude/settings.json` | Repository asset | `ACTIVE` |
| `.env` | Root environment and dependency configuration: .env | `ACTIVE` |
| `.env.example` | Root environment and dependency configuration: .env.example | `ACTIVE` |
| `.gitattributes` | Root environment and dependency configuration: .gitattributes | `ACTIVE` |
| `.github/workflows/ci.yml` | Repository asset | `ACTIVE` |
| `.gitignore` | Root environment and dependency configuration: .gitignore | `ACTIVE` |
| `.mcp.json` | Root environment and dependency configuration: .mcp.json | `ACTIVE` |
| `bin/harness` | CLI Harness cross-platform launcher: harness | `ACTIVE` |
| `bin/harness.bat` | CLI Harness cross-platform launcher: harness.bat | `ACTIVE` |
| `bin/harness.ps1` | CLI Harness cross-platform launcher: harness.ps1 | `ACTIVE` |
| `deploy/azure/backend_startup.py` | Azure App Service startup orchestration script: backend_startup.py | `ACTIVE` |
| `deploy/azure/frontend_startup.js` | Azure App Service startup orchestration script: frontend_startup.js | `ACTIVE` |
| `harness` | Root launcher script for dual-server FastAPI + Next.js orchestration | `ACTIVE` |
| `harness.bat` | Root launcher script for dual-server FastAPI + Next.js orchestration | `ACTIVE` |
| `package-lock.json` | Root environment and dependency configuration: package-lock.json | `ACTIVE` |
| `package.json` | Root environment and dependency configuration: package.json | `ACTIVE` |
| `playwright.config.ts` | Root environment and dependency configuration: playwright.config.ts | `ACTIVE` |
| `pytest.ini` | Root environment and dependency configuration: pytest.ini | `ACTIVE` |
| `requirements-evals.txt` | Root environment and dependency configuration: requirements-evals.txt | `ACTIVE` |
| `requirements.txt` | Root environment and dependency configuration: requirements.txt | `ACTIVE` |
| `run.bat` | Root launcher script for dual-server FastAPI + Next.js orchestration | `ACTIVE` |
| `run.sh` | Root launcher script for dual-server FastAPI + Next.js orchestration | `ACTIVE` |
| `scripts/capture_evidence.js` | Platform engineering / verification script: capture_evidence.js | `ACTIVE` |
| `scripts/capture_evidence.py` | Platform engineering / verification script: capture_evidence.py | `ACTIVE` |
| `scripts/dev.py` | Platform engineering / verification script: dev.py | `ACTIVE` |
| `scripts/gen_structure.py` | Platform engineering / verification script: gen_structure.py | `ACTIVE` |
| `scripts/hooks/activity_log.py` | Platform engineering / verification script: activity_log.py | `ACTIVE` |
| `scripts/package_azure.py` | Platform engineering / verification script: package_azure.py | `ACTIVE` |
| `scripts/verify_harness_enhancements.js` | Platform engineering / verification script: verify_harness_enhancements.js | `ACTIVE` |
| `scripts/verify_latest_fixes.js` | Platform engineering / verification script: verify_latest_fixes.js | `ACTIVE` |
| `start-mac.command` | Root launcher script for dual-server FastAPI + Next.js orchestration | `ACTIVE` |
| `start-windows.bat` | Root launcher script for dual-server FastAPI + Next.js orchestration | `ACTIVE` |
| `tsconfig.json` | Root environment and dependency configuration: tsconfig.json | `ACTIVE` |

### Active Test Suite (tests/) (25 files)

| File Path | Role / Description | Status |
|---|---|---|
| `tests/__init__.py` | Pytest/Playwright test suite module: __init__.py | `ACTIVE` |
| `tests/conftest.py` | Pytest/Playwright test suite module: conftest.py | `ACTIVE` |
| `tests/e2e/__init__.py` | Pytest/Playwright test suite module: __init__.py | `ACTIVE` |
| `tests/e2e/conftest.py` | Pytest/Playwright test suite module: conftest.py | `ACTIVE` |
| `tests/e2e/harness.spec.ts` | Pytest/Playwright test suite module: harness.spec.ts | `ACTIVE` |
| `tests/e2e/test_app.py` | Pytest/Playwright test suite module: test_app.py | `ACTIVE` |
| `tests/e2e/test_finance_repo.py` | Pytest/Playwright test suite module: test_finance_repo.py | `ACTIVE` |
| `tests/e2e/test_smoke.py` | Pytest/Playwright test suite module: test_smoke.py | `ACTIVE` |
| `tests/reviewing.py` | Pytest/Playwright test suite module: reviewing.py | `ACTIVE` |
| `tests/scripted_client.py` | Pytest/Playwright test suite module: scripted_client.py | `ACTIVE` |
| `tests/test_access.py` | Pytest/Playwright test suite module: test_access.py | `ACTIVE` |
| `tests/test_api_workflows.py` | Pytest/Playwright test suite module: test_api_workflows.py | `ACTIVE` |
| `tests/test_confidence.py` | Pytest/Playwright test suite module: test_confidence.py | `ACTIVE` |
| `tests/test_core.py` | Pytest/Playwright test suite module: test_core.py | `ACTIVE` |
| `tests/test_emit.py` | Pytest/Playwright test suite module: test_emit.py | `ACTIVE` |
| `tests/test_errors.py` | Pytest/Playwright test suite module: test_errors.py | `ACTIVE` |
| `tests/test_evaluation_metrics.py` | Pytest/Playwright test suite module: test_evaluation_metrics.py | `ACTIVE` |
| `tests/test_execution_stages.py` | Pytest/Playwright test suite module: test_execution_stages.py | `ACTIVE` |
| `tests/test_harness_backend.py` | Pytest/Playwright test suite module: test_harness_backend.py | `ACTIVE` |
| `tests/test_maf_backend.py` | Pytest/Playwright test suite module: test_maf_backend.py | `ACTIVE` |
| `tests/test_migration_006.py` | Pytest/Playwright test suite module: test_migration_006.py | `ACTIVE` |
| `tests/test_models.py` | Pytest/Playwright test suite module: test_models.py | `ACTIVE` |
| `tests/test_ops.py` | Pytest/Playwright test suite module: test_ops.py | `ACTIVE` |
| `tests/test_skills.py` | Pytest/Playwright test suite module: test_skills.py | `ACTIVE` |
| `tests/test_token_budget.py` | Pytest/Playwright test suite module: test_token_budget.py | `ACTIVE` |

### Active Documentation & Specifications (99 files)

| File Path | Role / Description | Status |
|---|---|---|
| `CLAUDE.md` | Root project specification, standard, or audit document: CLAUDE.md | `ACTIVE` |
| `DESIGN.md` | Root project specification, standard, or audit document: DESIGN.md | `ACTIVE` |
| `HARNESS_PATTERNS.md` | Root project specification, standard, or audit document: HARNESS_PATTERNS.md | `ACTIVE` |
| `MAF_EVALUATION_REPORT.md` | Root project specification, standard, or audit document: MAF_EVALUATION_REPORT.md | `ACTIVE` |
| `PROGRESS.md` | Root project specification, standard, or audit document: PROGRESS.md | `ACTIVE` |
| `README.md` | Root project specification, standard, or audit document: README.md | `ACTIVE` |
| `SECURITY_AUDIT_REPORT.md` | Root project specification, standard, or audit document: SECURITY_AUDIT_REPORT.md | `ACTIVE` |
| `UI_AUDIT_AND_AMBITION_REPORT.md` | Root project specification, standard, or audit document: UI_AUDIT_AND_AMBITION_REPORT.md | `ACTIVE` |
| `USER_STORIES.md` | Root project specification, standard, or audit document: USER_STORIES.md | `ACTIVE` |
| `agent-framework.pdf` | Root project specification, standard, or audit document: agent-framework.pdf | `ACTIVE` |
| `docs/ARCHITECTURE.md` | Platform architecture and technical specification: ARCHITECTURE.md | `ACTIVE` |
| `docs/AZURE_DEPLOY.md` | Platform architecture and technical specification: AZURE_DEPLOY.md | `ACTIVE` |
| `docs/AZURE_SYSTEM_DESIGN.md` | Platform architecture and technical specification: AZURE_SYSTEM_DESIGN.md | `ACTIVE` |
| `docs/EVALUATIONS.md` | Platform architecture and technical specification: EVALUATIONS.md | `ACTIVE` |
| `docs/PLUGIN_AND_UI_PLAN.md` | Platform architecture and technical specification: PLUGIN_AND_UI_PLAN.md | `ACTIVE` |
| `docs/PROJECT_STRUCTURE.md` | Platform architecture and technical specification: PROJECT_STRUCTURE.md | `ACTIVE` |
| `docs/SYSTEM_DESIGN.md` | Platform architecture and technical specification: SYSTEM_DESIGN.md | `ACTIVE` |
| `docs/evidence/01-projects-empty.png` | Milestone evidence asset: 01-projects-empty.png | `ACTIVE` |
| `docs/evidence/01_homepage.png` | Milestone evidence asset: 01_homepage.png | `ACTIVE` |
| `docs/evidence/01_homepage_dark.png` | Milestone evidence asset: 01_homepage_dark.png | `ACTIVE` |
| `docs/evidence/01_homepage_light.png` | Milestone evidence asset: 01_homepage_light.png | `ACTIVE` |
| `docs/evidence/02-project-overview.png` | Milestone evidence asset: 02-project-overview.png | `ACTIVE` |
| `docs/evidence/02_project_overview.png` | Milestone evidence asset: 02_project_overview.png | `ACTIVE` |
| `docs/evidence/02_project_overview_light.png` | Milestone evidence asset: 02_project_overview_light.png | `ACTIVE` |
| `docs/evidence/03-repository-zip.png` | Milestone evidence asset: 03-repository-zip.png | `ACTIVE` |
| `docs/evidence/03_harness_dark.png` | Milestone evidence asset: 03_harness_dark.png | `ACTIVE` |
| `docs/evidence/03_harness_light.png` | Milestone evidence asset: 03_harness_light.png | `ACTIVE` |
| `docs/evidence/03_project_harness_idle.png` | Milestone evidence asset: 03_project_harness_idle.png | `ACTIVE` |
| `docs/evidence/04-repository-github.png` | Milestone evidence asset: 04-repository-github.png | `ACTIVE` |
| `docs/evidence/04_harness_chat_stream.png` | Milestone evidence asset: 04_harness_chat_stream.png | `ACTIVE` |
| `docs/evidence/04_harness_skills_executed.png` | Milestone evidence asset: 04_harness_skills_executed.png | `ACTIVE` |
| `docs/evidence/05-projects-list.png` | Milestone evidence asset: 05-projects-list.png | `ACTIVE` |
| `docs/evidence/05_harness_tasks.png` | Milestone evidence asset: 05_harness_tasks.png | `ACTIVE` |
| `docs/evidence/05b-documentation.png` | Milestone evidence asset: 05b-documentation.png | `ACTIVE` |
| `docs/evidence/06-settings.png` | Milestone evidence asset: 06-settings.png | `ACTIVE` |
| `docs/evidence/06_harness_skills_tab.png` | Milestone evidence asset: 06_harness_skills_tab.png | `ACTIVE` |
| `docs/evidence/06b-approvals-page.png` | Milestone evidence asset: 06b-approvals-page.png | `ACTIVE` |
| `docs/evidence/07-ba-gate1.png` | Milestone evidence asset: 07-ba-gate1.png | `ACTIVE` |
| `docs/evidence/08-gherkin-editor.png` | Milestone evidence asset: 08-gherkin-editor.png | `ACTIVE` |
| `docs/evidence/08b-document-formatted.png` | Milestone evidence asset: 08b-document-formatted.png | `ACTIVE` |
| `docs/evidence/08c-gherkin-table.png` | Milestone evidence asset: 08c-gherkin-table.png | `ACTIVE` |
| `docs/evidence/08d-document-edited-in-place.png` | Milestone evidence asset: 08d-document-edited-in-place.png | `ACTIVE` |
| `docs/evidence/09-document-history.png` | Milestone evidence asset: 09-document-history.png | `ACTIVE` |
| `docs/evidence/10-bug-scan.png` | Milestone evidence asset: 10-bug-scan.png | `ACTIVE` |
| `docs/evidence/11-feature-diff.png` | Milestone evidence asset: 11-feature-diff.png | `ACTIVE` |
| `docs/evidence/12-feature-committed.png` | Milestone evidence asset: 12-feature-committed.png | `ACTIVE` |
| `docs/evidence/12b-bug-fix-diff.png` | Milestone evidence asset: 12b-bug-fix-diff.png | `ACTIVE` |
| `docs/evidence/13-qe-progress.png` | Milestone evidence asset: 13-qe-progress.png | `ACTIVE` |
| `docs/evidence/14-qe-gate5.png` | Milestone evidence asset: 14-qe-gate5.png | `ACTIVE` |
| `docs/evidence/15-qe-complete.png` | Milestone evidence asset: 15-qe-complete.png | `ACTIVE` |
| `docs/evidence/16-chat-documents.png` | Milestone evidence asset: 16-chat-documents.png | `ACTIVE` |
| `docs/evidence/17-chat-reopened.png` | Milestone evidence asset: 17-chat-reopened.png | `ACTIVE` |
| `docs/evidence/18-chat-new-window.png` | Milestone evidence asset: 18-chat-new-window.png | `ACTIVE` |
| `docs/evidence/19-governance.png` | Milestone evidence asset: 19-governance.png | `ACTIVE` |
| `docs/evidence/20-metrics.png` | Milestone evidence asset: 20-metrics.png | `ACTIVE` |
| `docs/evidence/21-prompts.png` | Milestone evidence asset: 21-prompts.png | `ACTIVE` |
| `docs/evidence/21b-agents.png` | Milestone evidence asset: 21b-agents.png | `ACTIVE` |
| `docs/evidence/21c-agent-disabled.png` | Milestone evidence asset: 21c-agent-disabled.png | `ACTIVE` |
| `docs/evidence/21d-observability-all.png` | Milestone evidence asset: 21d-observability-all.png | `ACTIVE` |
| `docs/evidence/21e-observability-run.png` | Milestone evidence asset: 21e-observability-run.png | `ACTIVE` |
| `docs/evidence/22-light-theme.png` | Milestone evidence asset: 22-light-theme.png | `ACTIVE` |
| `docs/evidence/22a-login.png` | Milestone evidence asset: 22a-login.png | `ACTIVE` |
| `docs/evidence/22b-users.png` | Milestone evidence asset: 22b-users.png | `ACTIVE` |
| `docs/evidence/eval-summary.txt` | Milestone evidence asset: eval-summary.txt | `ACTIVE` |
| `docs/evidence/evidence_antigravity_expanded_tree.png` | Milestone evidence asset: evidence_antigravity_expanded_tree.png | `ACTIVE` |
| `docs/evidence/evidence_antigravity_icon_collapsed.png` | Milestone evidence asset: evidence_antigravity_icon_collapsed.png | `ACTIVE` |
| `docs/evidence/evidence_antigravity_new_project_modal.png` | Milestone evidence asset: evidence_antigravity_new_project_modal.png | `ACTIVE` |
| `docs/evidence/evidence_global_harness.png` | Milestone evidence asset: evidence_global_harness.png | `ACTIVE` |
| `docs/evidence/evidence_harness_fixed_idle.png` | Milestone evidence asset: evidence_harness_fixed_idle.png | `ACTIVE` |
| `docs/evidence/evidence_harness_fixed_live_run.png` | Milestone evidence asset: evidence_harness_fixed_live_run.png | `ACTIVE` |
| `docs/evidence/evidence_harness_fixed_skills_tab.png` | Milestone evidence asset: evidence_harness_fixed_skills_tab.png | `ACTIVE` |
| `docs/evidence/evidence_harness_fixed_slash_palette.png` | Milestone evidence asset: evidence_harness_fixed_slash_palette.png | `ACTIVE` |
| `docs/evidence/evidence_project_redirect_to_harness.png` | Milestone evidence asset: evidence_project_redirect_to_harness.png | `ACTIVE` |
| `docs/evidence/evidence_project_view_clean.png` | Milestone evidence asset: evidence_project_view_clean.png | `ACTIVE` |
| `docs/evidence/f1-finance-repository.png` | Milestone evidence asset: f1-finance-repository.png | `ACTIVE` |
| `docs/evidence/f2-finance-ba-gate.png` | Milestone evidence asset: f2-finance-ba-gate.png | `ACTIVE` |
| `docs/evidence/f2-finance-brd-formatted.png` | Milestone evidence asset: f2-finance-brd-formatted.png | `ACTIVE` |
| `docs/evidence/f2-finance-gherkin.png` | Milestone evidence asset: f2-finance-gherkin.png | `ACTIVE` |
| `docs/evidence/f3-finance-bug-scan.png` | Milestone evidence asset: f3-finance-bug-scan.png | `ACTIVE` |
| `docs/evidence/f4-finance-feature-diff.png` | Milestone evidence asset: f4-finance-feature-diff.png | `ACTIVE` |
| `docs/evidence/f5-finance-fix-diff.png` | Milestone evidence asset: f5-finance-fix-diff.png | `ACTIVE` |
| `docs/evidence/f5b-finance-fix-all.png` | Milestone evidence asset: f5b-finance-fix-all.png | `ACTIVE` |
| `docs/evidence/f6-finance-qe-gate5.png` | Milestone evidence asset: f6-finance-qe-gate5.png | `ACTIVE` |
| `docs/evidence/f6-finance-qe-live.png` | Milestone evidence asset: f6-finance-qe-live.png | `ACTIVE` |
| `docs/evidence/f7-finance-chat.png` | Milestone evidence asset: f7-finance-chat.png | `ACTIVE` |
| `docs/evidence/f8-finance-governance.png` | Milestone evidence asset: f8-finance-governance.png | `ACTIVE` |
| `docs/evidence/finance-discovery.md` | Milestone evidence asset: finance-discovery.md | `ACTIVE` |
| `docs/evidence/finance-runs.json` | Milestone evidence asset: finance-runs.json | `ACTIVE` |
| `docs/evidence/server.log` | Milestone evidence asset: server.log | `ACTIVE` |
| `docs/evidence/where_is_harness_homepage.png` | Milestone evidence asset: where_is_harness_homepage.png | `ACTIVE` |
| `docs/evidence/where_is_harness_inside_harness.png` | Milestone evidence asset: where_is_harness_inside_harness.png | `ACTIVE` |
| `docs/evidence/where_is_harness_project_overview.png` | Milestone evidence asset: where_is_harness_project_overview.png | `ACTIVE` |
| `evidence_dark.png` | Root project specification, standard, or audit document: evidence_dark.png | `ACTIVE` |
| `evidence_light.png` | Root project specification, standard, or audit document: evidence_light.png | `ACTIVE` |
| `evidence_slash_palette.png` | Root project specification, standard, or audit document: evidence_slash_palette.png | `ACTIVE` |
| `maf-guide.md` | Root project specification, standard, or audit document: maf-guide.md | `ACTIVE` |
| `plan.md` | Root project specification, standard, or audit document: plan.md | `ACTIVE` |
| `specs.md` | Root project specification, standard, or audit document: specs.md | `ACTIVE` |
| `tasks.md` | Root project specification, standard, or audit document: tasks.md | `ACTIVE` |

### Data & Runtime State (data/, .sessions/) (34 files)

| File Path | Role / Description | Status |
|---|---|---|
| `.sessions/sess_1793888447517_152fae.json` | Persisted harness chat session JSON record: sess_1793888447517_152fae.json | `ACTIVE` |
| `.sessions/sess_1793888477802_405dd2.json` | Persisted harness chat session JSON record: sess_1793888477802_405dd2.json | `ACTIVE` |
| `.sessions/sess_1793888606120_550905.json` | Persisted harness chat session JSON record: sess_1793888606120_550905.json | `ACTIVE` |
| `.sessions/sess_1793888607332_1b9887.json` | Persisted harness chat session JSON record: sess_1793888607332_1b9887.json | `ACTIVE` |
| `.sessions/sess_1793888608595_774873.json` | Persisted harness chat session JSON record: sess_1793888608595_774873.json | `ACTIVE` |
| `.sessions/sess_1793888609829_300acf.json` | Persisted harness chat session JSON record: sess_1793888609829_300acf.json | `ACTIVE` |
| `.sessions/sess_1793888611139_41b3be.json` | Persisted harness chat session JSON record: sess_1793888611139_41b3be.json | `ACTIVE` |
| `.sessions/sess_1793888612374_088923.json` | Persisted harness chat session JSON record: sess_1793888612374_088923.json | `ACTIVE` |
| `.sessions/sess_1793888623127_8821f0.json` | Persisted harness chat session JSON record: sess_1793888623127_8821f0.json | `ACTIVE` |
| `.sessions/sess_1793888624334_95bf95.json` | Persisted harness chat session JSON record: sess_1793888624334_95bf95.json | `ACTIVE` |
| `.sessions/sess_1793888637838_87547f.json` | Persisted harness chat session JSON record: sess_1793888637838_87547f.json | `ACTIVE` |
| `.sessions/sess_1793888639045_5e3d6f.json` | Persisted harness chat session JSON record: sess_1793888639045_5e3d6f.json | `ACTIVE` |
| `.sessions/sess_1793888710742_9f665c.json` | Persisted harness chat session JSON record: sess_1793888710742_9f665c.json | `ACTIVE` |
| `.sessions/sess_1793888711977_44f8b8.json` | Persisted harness chat session JSON record: sess_1793888711977_44f8b8.json | `ACTIVE` |
| `.sessions/sess_1793888713246_9ba1f2.json` | Persisted harness chat session JSON record: sess_1793888713246_9ba1f2.json | `ACTIVE` |
| `.sessions/sess_1793888714492_5e1aa7.json` | Persisted harness chat session JSON record: sess_1793888714492_5e1aa7.json | `ACTIVE` |
| `.sessions/sess_1793888715826_d1a1ab.json` | Persisted harness chat session JSON record: sess_1793888715826_d1a1ab.json | `ACTIVE` |
| `.sessions/sess_1793888717079_e917f5.json` | Persisted harness chat session JSON record: sess_1793888717079_e917f5.json | `ACTIVE` |
| `.sessions/sess_1793888718334_8e5465.json` | Persisted harness chat session JSON record: sess_1793888718334_8e5465.json | `ACTIVE` |
| `.sessions/sess_1793888719593_1ef10e.json` | Persisted harness chat session JSON record: sess_1793888719593_1ef10e.json | `ACTIVE` |
| `.sessions/sess_1793888720810_9f136c.json` | Persisted harness chat session JSON record: sess_1793888720810_9f136c.json | `ACTIVE` |
| `.sessions/sess_1793888723380_a99d22.json` | Persisted harness chat session JSON record: sess_1793888723380_a99d22.json | `ACTIVE` |
| `.sessions/sess_1793888724548_50b8af.json` | Persisted harness chat session JSON record: sess_1793888724548_50b8af.json | `ACTIVE` |
| `.sessions/sess_1793890531833_ffbd30.json` | Persisted harness chat session JSON record: sess_1793890531833_ffbd30.json | `ACTIVE` |
| `.sessions/sess_1793890536850_51a5e0.json` | Persisted harness chat session JSON record: sess_1793890536850_51a5e0.json | `ACTIVE` |
| `.sessions/sess_1793894137005_a66b7b.json` | Persisted harness chat session JSON record: sess_1793894137005_a66b7b.json | `ACTIVE` |
| `.sessions/sess_1793894683848_f87fa8.json` | Persisted harness chat session JSON record: sess_1793894683848_f87fa8.json | `ACTIVE` |
| `.sessions/sess_1793902967144_3ffd3b.json` | Persisted harness chat session JSON record: sess_1793902967144_3ffd3b.json | `ACTIVE` |
| `.sessions/sess_1793903865119_19e501.json` | Persisted harness chat session JSON record: sess_1793903865119_19e501.json | `ACTIVE` |
| `data/.secret.key` | Runtime persistent SQLite database, encryption key, or project workspace: data/.secret.key | `ACTIVE` |
| `data/atlas.sqlite3` | Runtime persistent SQLite database, encryption key, or project workspace: data/atlas.sqlite3 | `ACTIVE` |
| `data/logs/app-2026-11-05.jsonl` | Runtime persistent SQLite database, encryption key, or project workspace: data/logs/app-2026-11-05.jsonl | `ACTIVE` |
| `data/projects/prj_agentic_qe/documents/brd/doc_b7dab2ea7088/v0001.md` | Root project specification, standard, or audit document: data/projects/prj_agentic_qe/documents/brd/doc_b7dab2ea7088/v0001.md | `ACTIVE` |
| `data/projects/prj_agentic_qe/documents/prd/doc_2cc7d0dd6271/v0001.md` | Root project specification, standard, or audit document: data/projects/prj_agentic_qe/documents/prd/doc_2cc7d0dd6271/v0001.md | `ACTIVE` |

### Stale / Dead Code: Root Standalone Backend Duplicates (backend/*) (21 files)

| File Path | Role / Description | Status |
|---|---|---|
| `backend/llm_config.json` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/core/harness_agent.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/core/memory_provider.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/core/mode_provider.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/core/session.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/core/todo_provider.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/llm/client.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/llm/config.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/orchestrators/handoff.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/orchestrators/magentic.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/protocol/agui.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/protocol/copilotkit.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/skills/discovery.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/tools/approval_manager.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/tools/function_tool.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/tools/mcp_manager.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/maf/tools/qe_guardrails.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/main.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/qe/agents.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/qe/tools.py` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |
| `backend/requirements.txt` | Precursor standalone harness backend implementation, now fully migrated and modularized into src/backend/harness and src/backend/api/harness.py | **`CANDIDATE_FOR_CLEANUP`** |

### Stale / Dead Code: Root Frontend Remnants (src/app, src/components, src/lib) (41 files)

| File Path | Role / Description | Status |
|---|---|---|
| `src/app/globals.css` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/app/layout.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/app/page.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/ChatContainer.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/ChatMessageItem.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/PromptInput.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/QualityGateApprovalCard.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/SlashCommandPalette.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/StopButton.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/ThinkingAccordion.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/chat/ToolCallCard.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/inspector/ContextInspector.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/inspector/MCPToolsExplorer.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/inspector/MagenticLedgerView.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/inspector/QualityGatesTracker.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/inspector/TodoChecklist.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/left-sidebar/LeftSidebar.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/modals/MCPSettingsModal.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/modals/ModelConfigModal.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/sidebar/SessionSidebar.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/theme/ThemeToggle.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/ui/Badge.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/components/ui/Button.tsx` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/core/AgentModeProvider.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/core/AgentSession.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/core/AgentSkillsProvider.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/core/FileMemoryProvider.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/core/HarnessAgent.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/core/TodoProvider.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/guardrails/QEGuardrails.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/memory/CompactionEngine.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/memory/SessionStore.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/orchestrators/MagenticQEOrchestrator.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/orchestrators/QEHandoffExecutor.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/protocol/agui.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/tools/FunctionTool.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/tools/MCPClientManager.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/tools/ToolApprovalManager.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/maf/types/index.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/qe/agents/index.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |
| `src/lib/qe/tools/index.ts` | Orphaned duplicate of Next.js frontend code prior to frontend extraction into src/frontend/; unreferenced by build | **`CANDIDATE_FOR_CLEANUP`** |

### Stale / Dead Code: Root Config Duplicates, Scratch Scripts & Orphaned Tests (8 files)

| File Path | Role / Description | Status |
|---|---|---|
| `e2e/harness.spec.ts` | Exact redundant copy of tests/e2e/harness.spec.ts; ignored by playwright.config.ts testDir | **`CANDIDATE_FOR_CLEANUP`** |
| `next-env.d.ts` | Root-level duplicate Next.js/Tailwind config; frontend compiler exclusively uses src/frontend/* | **`CANDIDATE_FOR_CLEANUP`** |
| `next.config.mjs` | Root-level duplicate Next.js/Tailwind config; frontend compiler exclusively uses src/frontend/* | **`CANDIDATE_FOR_CLEANUP`** |
| `postcss.config.js` | Root-level duplicate Next.js/Tailwind config; frontend compiler exclusively uses src/frontend/* | **`CANDIDATE_FOR_CLEANUP`** |
| `scratch/playwright_verify.py` | Temporary ad-hoc debug script used during development verification | **`CANDIDATE_FOR_CLEANUP`** |
| `scratch/test_antigravity_harness.py` | Temporary ad-hoc debug script used during development verification | **`CANDIDATE_FOR_CLEANUP`** |
| `tailwind.config.ts` | Root-level duplicate Next.js/Tailwind config; frontend compiler exclusively uses src/frontend/* | **`CANDIDATE_FOR_CLEANUP`** |
| `tests/unit/tc-test-001.test.ts` | Orphaned test-generator sample artifact containing vitest syntax errors; unused by pytest | **`CANDIDATE_FOR_CLEANUP`** |

### Stale / Obsolete Documentation (docs/REUSE_AUDIT.md) (1 files)

| File Path | Role / Description | Status |
|---|---|---|
| `docs/REUSE_AUDIT.md` | Historical audit document tracking deleted files from 2026-10-26 commit 09f14fe; superseded | **`OBSOLETE`** |

## 4. Exact Safe Cleanup Candidate List

The following **70 files** have been confirmed as dead, unreferenced, or duplicate. They can be removed safely once the test dependency in `tests/test_harness_backend.py` is retired or retargeted to `src/backend/harness`.

### Category A: Root Frontend Remnants in `src/` (41 Files) - Safe to delete immediately
These files were left over when the Next.js frontend was moved to `src/frontend/`. The Next.js compiler is rooted in `src/frontend/` and resolves `@/*` to `./*`, completely ignoring these files.

```text
src/app/globals.css
src/app/layout.tsx
src/app/page.tsx
src/components/chat/ChatContainer.tsx
src/components/chat/ChatMessageItem.tsx
src/components/chat/PromptInput.tsx
src/components/chat/QualityGateApprovalCard.tsx
src/components/chat/SlashCommandPalette.tsx
src/components/chat/StopButton.tsx
src/components/chat/ThinkingAccordion.tsx
src/components/chat/ToolCallCard.tsx
src/components/inspector/ContextInspector.tsx
src/components/inspector/MCPToolsExplorer.tsx
src/components/inspector/MagenticLedgerView.tsx
src/components/inspector/QualityGatesTracker.tsx
src/components/inspector/TodoChecklist.tsx
src/components/left-sidebar/LeftSidebar.tsx
src/components/modals/MCPSettingsModal.tsx
src/components/modals/ModelConfigModal.tsx
src/components/sidebar/SessionSidebar.tsx
src/components/theme/ThemeToggle.tsx
src/components/ui/Badge.tsx
src/components/ui/Button.tsx
src/lib/maf/core/AgentModeProvider.ts
src/lib/maf/core/AgentSession.ts
src/lib/maf/core/AgentSkillsProvider.ts
src/lib/maf/core/FileMemoryProvider.ts
src/lib/maf/core/HarnessAgent.ts
src/lib/maf/core/TodoProvider.ts
src/lib/maf/guardrails/QEGuardrails.ts
src/lib/maf/memory/CompactionEngine.ts
src/lib/maf/memory/SessionStore.ts
src/lib/maf/orchestrators/MagenticQEOrchestrator.ts
src/lib/maf/orchestrators/QEHandoffExecutor.ts
src/lib/maf/protocol/agui.ts
src/lib/maf/tools/FunctionTool.ts
src/lib/maf/tools/MCPClientManager.ts
src/lib/maf/tools/ToolApprovalManager.ts
src/lib/maf/types/index.ts
src/lib/qe/agents/index.ts
src/lib/qe/tools/index.ts
```

### Category B: Root Standalone Backend Precursor (`backend/`) (21 Files)
Every single file here exists in an upgraded, integrated form inside `src/backend/harness/` and `src/backend/api/harness.py`. Note: `tests/test_harness_backend.py` currently imports from `backend/main.py`. Because `tests/test_maf_backend.py` already thoroughly tests `src/backend/harness/`, `tests/test_harness_backend.py` should be retargeted or removed alongside this directory.

```text
backend/llm_config.json
backend/maf/core/harness_agent.py
backend/maf/core/memory_provider.py
backend/maf/core/mode_provider.py
backend/maf/core/session.py
backend/maf/core/todo_provider.py
backend/maf/llm/client.py
backend/maf/llm/config.py
backend/maf/orchestrators/handoff.py
backend/maf/orchestrators/magentic.py
backend/maf/protocol/agui.py
backend/maf/protocol/copilotkit.py
backend/maf/skills/discovery.py
backend/maf/tools/approval_manager.py
backend/maf/tools/function_tool.py
backend/maf/tools/mcp_manager.py
backend/maf/tools/qe_guardrails.py
backend/main.py
backend/qe/agents.py
backend/qe/tools.py
backend/requirements.txt
```

### Category C: Root Config Duplicates, Scratch Scripts & Orphaned Tests (7 Files) - Safe to delete immediately

```text
e2e/harness.spec.ts
next-env.d.ts
next.config.mjs
postcss.config.js
scratch/playwright_verify.py
scratch/test_antigravity_harness.py
tailwind.config.ts
tests/unit/tc-test-001.test.ts
```

### Category D: Obsolete Documentation (1 File)

```text
docs/REUSE_AUDIT.md
```

## 5. Verification & Safety Protocol for Cleanup

To guarantee zero breakage to active services:
1. **Frontend Isolation**: Run `npm --prefix src/frontend run build` and `npm --prefix src/frontend run lint`. Both run cleanly with zero references to root `src/app`, `src/components`, or `src/lib`.
2. **Backend Services**: Verify `run.sh` / `scripts/dev.py up`. Both explicitly execute `uvicorn backend.app:app` with `PYTHONPATH=src:ROOT`. They use `src/backend/app.py` and never touch root `backend/`.
3. **Test Suite Retargeting**: In `tests/test_harness_backend.py`, change import from `from main import app` to `from backend.app import app` (or retire the duplicate file since `test_maf_backend.py` covers all 32 test cases against the integrated harness). Then run `pytest tests/ -m "not live and not e2e"`.
4. **Playwright E2E**: `playwright test` continues to use `playwright.config.ts` (`testDir: ./tests/e2e`). Deleting root `e2e/harness.spec.ts` has zero effect on test execution.
