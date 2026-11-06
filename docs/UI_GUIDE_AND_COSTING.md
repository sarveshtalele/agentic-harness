# 🖥️ Platform UI Operational Guide & Comprehensive Cloud Costing Analysis

**Version:** 2.0.0 | **Branch:** `feature/azure-kudu-deployment` | **Target Platform:** Microsoft Agent Framework (MAF) & Azure App Service

---

## 📑 Table of Contents
1. [Executive Overview & Platform Layout](#1-executive-overview--platform-layout)
2. [Step-by-Step UI Operational Guide](#2-step-by-step-ui-operational-guide)
   - [2.1 Autonomous QE Harness (`/harness`)](#21-autonomous-qe-harness-harness)
   - [2.2 Skill Creator Studio (`/skills/studio`)](#22-skill-creator-studio-skillsstudio)
   - [2.3 Project Management & Multi-Agent Workspaces (`/projects`)](#23-project-management--multi-agent-workspaces-projects)
   - [2.4 Business Analyst (BA) Studio & BRD Synthesis (`/projects/[id]/ba`)](#24-business-analyst-ba-studio--brd-synthesis-projectsidba)
   - [2.5 QE Lifecycle Studio & 8-Gate Pipeline (`/projects/[id]/qe`)](#25-qe-lifecycle-studio--8-gate-pipeline-projectsidqe)
   - [2.6 Defect Reviewer & Automated Bug Healing (`/projects/[id]/bugs`)](#26-defect-reviewer--automated-bug-healing-projectsidbugs)
   - [2.7 Document Repository & ChromaDB RAG Vector Store (`/documents`)](#27-document-repository--chromadb-rag-vector-store-documents)
   - [2.8 Model Context Protocol (MCP) Server Registry (`/mcp`)](#28-model-context-protocol-mcp-server-registry-mcp)
   - [2.9 Gate Approvals & Human-in-the-Loop (HITL) Queue (`/approvals`)](#29-gate-approvals--human-in-the-loop-hitl-queue-approvals)
   - [2.10 AI Specialist Roster & Telemetry (`/agents`)](#210-ai-specialist-roster--telemetry-agents)
   - [2.11 OpenTelemetry Observability & Tracing (`/observability`)](#211-opentelemetry-observability--tracing-observability)
   - [2.12 Token Budget, Ledger & Cost Tracking (`/usage`)](#212-token-budget-ledger--cost-tracking-usage)
3. [Comprehensive Enterprise Costing & Pricing Breakdown](#3-comprehensive-enterprise-costing--pricing-breakdown)
   - [3.1 Azure Compute & App Service Plan Sizing](#31-azure-compute--app-service-plan-sizing)
   - [3.2 Database & Storage Tiers (SQLite WAL vs PostgreSQL)](#32-database--storage-tiers-sqlite-wal-vs-postgresql)
   - [3.3 Networking, Bandwidth & Security Costs](#33-networking-bandwidth--security-costs)
   - [3.4 LLM Model Token Economics & Multi-Model Benchmarking](#34-llm-model-token-economics--multi-model-benchmarking)
   - [3.5 Monthly Operational Run-Rate Comparison Table](#35-monthly-operational-run-rate-comparison-table)
   - [3.6 Cost Optimization Guardrails & Best Practices](#36-cost-optimization-guardrails--best-practices)
4. [Strict Branch Isolation & Protection Governance](#4-strict-branch-isolation--protection-governance)

---

## 1. Executive Overview & Platform Layout

The **Agentic Quality Engineering (QE) Platform** is an enterprise-grade autonomous testing and software verification operating system powered by the **Microsoft Agent Framework (MAF 2.0)**. 

The user interface follows a modern, responsive tripartite architecture:
* **Global Navigation Rail (Left):** Instant access to Projects, Autonomous QE Harness, Gate Approvals, AI Specialist Roster, Studios, MCP Registry, and Governance.
* **Primary Interactive Canvas (Center):** Conversational multi-agent loop, code visualizers, AST diff trees, and markdown document authoring.
* **Contextual Intelligence Rail (Right):** Dynamic inspection drawer rendering Active Skills, Real-time Task Ledgers, Benchmark Evals, and Token Consumption telemetry.

```
┌─────────────────┬──────────────────────────────────────────┬────────────────────────┐
│  NAVIGATION     │         PRIMARY WORKSPACE CANVAS         │  CONTEXT DRAWER        │
│                 │                                          │                        │
│ • Projects      │  [Project: MCP Server Market] [Gates:6/8]│  [Skills] [Tasks]      │
│ • QE Harness    │  ┌────────────────────────────────────┐  │  [Evals]  [Ledger]     │
│ • Gate Approvals│  │ Autonomous QE Harness Active       │  │                        │
│ • AI Roster     │  │ Select a goal or execute skills:   │  │ Active Task Ledger     │
│ • Skill Studio  │  │ [BRD] [PRD] [QE Loop] [Bug Fix]    │  │ ☑ 1. AST Intake        │
│ • Documents/RAG │  │ [Feature Build] [Security Audit]   │  │ ☑ 2. Repo Discovery    │
│ • MCP Registry  │  └────────────────────────────────────┘  │ ☐ 3. Test Synthesis    │
│ • Observability │  Chat Input: /create_agent_skill...      │ ☐ 4. Docker Execution  │
│ • Token Usage   │  [+ Attachment] [DeepSeek V3] [Plan Mode]│ Status: In-Progress    │
└─────────────────┴──────────────────────────────────────────┴────────────────────────┘
```

---

## 2. Step-by-Step UI Operational Guide

### 2.1 Autonomous QE Harness (`/harness`)

The **Autonomous QE Harness** is the central conversational workspace where multi-agent loops execute complex quality engineering workflows.

#### Step-by-Step User Flow:
1. **Select Target Project:** In the upper right project dropdown, pick your target project (e.g., `p1` or `MCP Server Market`). All agent tool executions will be strictly sandboxed to this project's repository.
2. **Launch a One-Click Quality Engineering Goal:**
   * **`Create BRD` (`Requirements`):** Analyzes target repository code and generates a complete Business Requirements Document with verified facts.
   * **`Create PRD` (`Product`):** Authors Product Requirements Documents containing grounded user stories, acceptance criteria, and API contracts.
   * **`Run Testing Lifecycle` (`Full QE Loop`):** Triggers Gates 0 through 8 end-to-end (Intake, Discovery, Requirements, Architecture, Test Design, Execution, Evaluation, Governance).
   * **`Feature Building` (`Sandbox Build`):** Implements code modifications in a sandboxed worktree with strict test validation.
   * **`GitHub Bug Fix & PR` (`Defect Repair`):** Scans code for failing tests or defect drift, diagnoses root causes, and scaffolds healing patches.
   * **`Run Security Audit` (`Cloudflare / NVIDIA`):** Audits zero-trust network policies and runs NVIDIA Skill Specter vulnerability scans.
   * **`Connect & Scan Repo` (`Intake Scan`):** Clones target GitHub repo into the local sandbox and parses AST manifests.
   * **`Create Agent Skill` (`Agent Skill`):** Launches the AI Skill Architect to synthesize, verify, and package a reusable skill.
3. **Conversational Command Input:**
   * Type `/` to invoke contextual autocomplete commands:
     - `/qe-discover`: Runs AST repo intelligence analysis.
     - `/qe-plan`: Synthesizes an 8-gate testing roadmap.
     - `/create_agent_skill`: Synthesizes a new domain skill package.
     - `/security-audit`: Executes zero-trust cloudflare and specter verification.
   * Attach files using the paperclip button (logs, BRDs, PRDs, Swagger JSON, or screenshots).
4. **Context Rail Monitoring:**
   * **`Skills` Tab:** Displays all loaded and active skills in the conversation context.
   * **`Tasks` Tab:** Shows real-time checkbox progression as agents complete individual tasks.
   * **`Evals` Tab:** Displays precision, recall, F1, and hallucination metrics for each agent turn.
   * **`Ledger` Tab:** Displays token usage, model latency, and execution cost.

---

### 2.2 Skill Creator Studio (`/skills/studio`)

The **Skill Creator Studio** allows engineers to synthesize, test, and package reusable agent skills with deterministic test suites grounded in domain specifications.

#### Step-by-Step User Flow:
1. **Define Specification Source:**
   * Click **`Custom Prompt`** to type requirements directly (e.g., *"Create a skill which will convert any md file to a .docx file"*).
   * Click **`Upload File`** to ground the skill on an uploaded BRD, architecture diagram, or API spec.
   * Click **`Project Specs`** to infer specifications from the target repository code.
2. **Run AI Skill Architect:**
   * Click the purple button: **`✨ AI Architect & Auto-Fill Skill Specifications`**.
   * The model analyzes the specification and populates:
     - **Skill Display Name:** e.g., `Markdown to DOCX Conversion Engine`.
     - **AI SDLC Category:** Select from dropdown (e.g., `Autonomous Test Synthesis`, `Defect Repair`, `Security Audit`).
     - **Target Project:** Binds the skill to a project workspace.
     - **Capability Description & Activation Brief:** Natural language instructions starting with `"Autonomous skill for... Use when..."`.
     - **Step-by-Step Task Checklist:** Generates an ordered list of tasks (e.g., `Parse markdown AST`, `Build OOXML styles`, `Emit document.docx`).
3. **Scaffold Package:**
   * Ensure checkbox **`Generate executable Python runner script ('scripts/run.py')`** is enabled.
   * Click **`Scaffold Agent Skill & Test Cases`**.
4. **Inspect Generated Artifacts:**
   * **`SKILL.md` Tab:** Standard YAML frontmatter, description, activation triggers, and instructions.
   * **`scripts/run.py` Tab:** Executable CLI implementation.
   * **`evals.json` Tab:** Ground truth verification criteria.
   * **`Test Cases Matrix` Tab:** Deterministic pytest test cases.
5. **Install & Test:**
   * Click **`Install Skill`** to register the skill into the local repository (`skills/<skill-name>/`).
   * Click **`Open QE Harness`** to test executing the skill in real-time.

---

### 2.3 Project Management & Multi-Agent Workspaces (`/projects`)

Projects define the isolated sandbox boundaries for codebases under test.

#### Step-by-Step User Flow:
1. **Create New Project:**
   * Click **`+ New Project`** in the header.
   * Enter Project Name, Description, and Repository URL (GitHub HTTPS or SSH).
   * Specify default target branch (`main`, `master`, or feature branch).
2. **Project Workspace Overview:**
   * Displays test coverage health, defect drift percentage, open approvals, and recent agent run timelines.
3. **Sub-Navigation:**
   * Switch between **BA Studio**, **QE Studio**, **Bug Repair**, **Repository**, and **Documents** using the project tab bar.

---

### 2.4 Business Analyst (BA) Studio & BRD Synthesis (`/projects/[id]/ba`)

Authors and verifies production-ready Business Requirements Documents directly from codebase AST intelligence.

#### Step-by-Step User Flow:
1. **Generate BRD:** Click **`Generate Grounded BRD`**. The `repo-intelligence-analyst` and `requirements-analyst` agents scan the repository and extract:
   - Business Domain Model & Workflows.
   - User Personas & Permissions.
   - Functional Requirement Verification Table.
   - Data Invariants & Non-Functional Performance SLAs.
2. **Review Evidence:** Every single fact in the BRD contains a clickable file and line citation (e.g., `src/backend/api/auth.py:45`).
3. **Export:** Click **`Export Markdown`** or **`Download .DOCX`** for formal stakeholder signoff.

---

### 2.5 QE Lifecycle Studio & 8-Gate Pipeline (`/projects/[id]/qe`)

Enforces the autonomous 8-Gate Quality Engineering methodology:
* **Gate 0 - Intake:** Repository clone, environment validation, test runner detection (`pytest`, `playwright`, `vitest`).
* **Gate 1 - Discovery:** AST parsing, route extraction, database schema reconstruction.
* **Gate 2 - Requirements:** Fact extraction and grounded requirement verification.
* **Gate 3 - Architecture:** System component mapping and boundary verification.
* **Gate 4 - Test Design:** Deterministic test scenario matrix and edge-case synthesis.
* **Gate 5 - Test Execution:** Sandboxed execution in Docker or local runner.
* **Gate 6 - Mutation & Defect Healing:** Bug injection, kill-ratio calculation, and defect repair.
* **Gate 7 - Evaluation & Telemetry:** Precision, recall, F1, groundedness, and hallucination scoring.
* **Gate 8 - Governance Signoff:** Policy validation and release promotion.

---

### 2.6 Defect Reviewer & Automated Bug Healing (`/projects/[id]/bugs`)

1. **Scan Defect Drift:** The `bug-reviewer` agent analyzes failed test runs and runtime error logs.
2. **Root-Cause Analysis:** Displays side-by-side diff between failing line and proposed AST patch.
3. **Healing Validation:** Runs the test suite against the healed code in an isolated git worktree.
4. **Scaffold PR:** Click **`Create GitHub Pull Request`** to push the verified fix directly to remote repository.

---

### 2.7 Document Repository & ChromaDB RAG Vector Store (`/documents`)

Enables semantic retrieval-augmented generation (RAG) across enterprise knowledge assets.
1. **Upload Documents:** Drag and drop `.pdf`, `.docx`, `.md`, or `.txt` files.
2. **Automated Vector Ingestion:** The background parser chunks documents into 500-token segments and generates vector embeddings stored in persistent ChromaDB.
3. **Semantic Querying:** Enter natural language queries (e.g., *"What is the timeout policy for payments?"*). The system returns exact chunk citations with similarity scores.

---

### 2.8 Model Context Protocol (MCP) Server Registry (`/mcp`)

Connects external developer tools to autonomous agents via the open Model Context Protocol standard:
1. **Installed MCP Servers:** Displays active connections (e.g., `Git MCP`, `Memory MCP`, `Filesystem MCP`, `Playwright MCP`).
2. **Add Custom Server:** Click **`Register MCP Server`**. Provide transport type (`stdio` or `sse`), executable command, and environment parameters.
3. **Tool Catalog:** Inspect live JSON schemas of all tools exposed by connected MCP servers.

---

### 2.9 Gate Approvals & Human-in-the-Loop (HITL) Queue (`/approvals`)

Provides strict enterprise oversight before destructive or high-risk actions execute:
1. **Pending Approvals Table:** Displays action type, requesting agent, target project, and confidence score.
2. **Review Action:** Click on any pending row to inspect proposed file writes, terminal commands, or branch merges.
3. **Approve / Reject:** Click **`Approve`** to let the agent proceed, or **`Reject with Guidance`** to send corrective feedback back to the agent loop.

---

### 2.10 AI Specialist Roster & Telemetry (`/agents`)

Inspect the 10 autonomous engineering personas:
* `repo-intelligence-analyst`: Deep codebase parsing and structure analysis.
* `requirements-analyst`: User story extraction and requirement validation.
* `confidence-reviewer`: Hallucination detection and fact verification.
* `test-designer`: Deterministic test matrix and edge-case generation.
* `bug-reviewer`: AST defect diagnosis and patch authoring.
* `security-auditor`: Cloudflare Zero-Trust and NVIDIA Skill Specter audits.
* Click any agent card to inspect historical prompt versions, average response tokens, and precision/recall trends.

---

### 2.11 OpenTelemetry Observability & Tracing (`/observability`)

1. **Trace Waterfall:** Real-time Gantt-style breakdown of multi-agent turns.
2. **Span Metrics:** Identifies latency bottlenecks across LLM API calls, tool executions, and file operations.
3. **Error Telemetry:** Detailed stack traces for any tool or model exceptions.

---

### 2.12 Token Budget, Ledger & Cost Tracking (`/usage`)

1. **Total Spend Overview:** Visualizes spend by model provider (DeepSeek, OpenAI, Anthropic).
2. **Token Ledger:** Granular per-request audit logs containing prompt tokens, completion tokens, cached tokens, and calculated dollar cost.
3. **Budget Hard Caps:** Configure soft warnings and hard stops to prevent unexpected cost overruns.

---

## 3. Comprehensive Enterprise Costing & Pricing Breakdown

### 3.1 Azure Compute & App Service Plan Sizing

The platform hosts both the FastAPI backend and Next.js frontend on a **single shared Linux App Service Plan**, drastically reducing operational infrastructure expenses.

| Azure App Service Plan Tier | vCPU | RAM | Storage | Hourly Rate | Estimated Monthly Cost | Recommended Operational Use Case |
|---|---|---|---|---|---|---|
| **Basic B1 (Linux)** | 1 | 1.75 GB | 10 GB | $0.017 | **$12.41 / mo** | **Development, Staging, Small Teams (< 10 engineers).** *Uses pre-built standalone Next.js bundle to eliminate Oryx OOM.* |
| **Standard S1 (Linux)** | 1 | 1.75 GB | 50 GB | $0.096 | **$70.08 / mo** | **Medium Teams.** *Adds autoscale (up to 10 instances) and daily automated Azure backup.* |
| **Premium P1v3 (Linux)** | 2 | 8.00 GB | 250 GB | $0.113 | **$82.49 / mo** | **Enterprise Production.** *High-memory for concurrent multi-agent Docker containers, fast NVMe SSD, VNet integration.* |

---

### 3.2 Database & Storage Tiers (SQLite WAL vs PostgreSQL)

#### Architecture 1: Embedded SQLite WAL on App Service Storage (Default / Cost-Effective)
* **Monthly Cost:** **$0.00 / month** (Included within App Service plan storage).
* **Storage Limit:** Up to 10 GB (B1) or 250 GB (P1v3).
* **Concurrency:** Up to 50 concurrent agent threads with WAL (Write-Ahead Logging) mode. Non-blocking reads; instant checkpointing.
* **Persistent Mount:** `/home/atlas/data/atlas.db` backed by Azure CIFS storage (`WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`).

#### Architecture 2: Azure Database for PostgreSQL Flexible Server (Enterprise Distributed)
* **Burstable B1ms (1 vCPU, 2 GB RAM, 32 GB Storage):** **~$14.60 / month**.
* **General Purpose D2s_v5 (2 vCPU, 8 GB RAM, 128 GB Storage):** **~$115.00 / month**.
* **Recommendation:** Begin with SQLite WAL on B1; seamlessly migrate to PostgreSQL Flexible Server when scaling beyond 100 concurrent agents.

---

### 3.3 Networking, Bandwidth & Security Costs

| Service Component | Sizing & Allocation | Cost Structure | Monthly Estimate |
|---|---|---|---|
| **Outbound Data Transfer (Egress)** | First 100 GB/month | Free tier on Azure | **$0.00** |
| **Additional Egress** | Beyond 100 GB | ~$0.087 per GB | **~$2.50** (typical usage) |
| **Custom Domain SSL** | App Service Managed Certificate | Included with B1/S1/P1v3 plans | **$0.00** |
| **Azure Front Door (Optional)** | Standard Profile (CDN & WAF) | $35.00 base + $0.01/10k requests | **$35.00** (optional) |

---

### 3.4 LLM Model Token Economics & Multi-Model Benchmarking

The platform supports pluggable LLM backends via the Microsoft Agent Framework. Costs depend on token throughput and model selection:

| Model Provider & Engine | Input (Prompt) Price / 1M Tokens | Output (Completion) Price / 1M Tokens | Cached Input Price / 1M Tokens | Typical Cost per QE Run (100k tokens) | Recommended Workflow Fit |
|---|---|---|---|---|---|
| **DeepSeek V3 (Global API)** | **$0.14** | **$0.28** | **$0.014** (90% discount) | **~$0.02** | Primary Workhorse (Discovery, Test Design, Bug Healing, BRD extraction) |
| **DeepSeek R1 (Reasoning)** | **$0.55** | **$2.19** | **$0.14** | **~$0.11** | Complex Root-Cause Diagnosis & Security Auditing |
| **OpenAI GPT-4o** | **$2.50** | **$10.00** | **$1.25** | **~$0.45** | Executive Summaries & High-Level Architecture |
| **Anthropic Claude 3.5 Sonnet** | **$3.00** | **$15.00** | **$0.30** | **~$0.60** | Complex Code Synthesis & Mutation Generation |
| **Local Ollama / vLLM (Self-Hosted)** | **$0.00** | **$0.00** | **$0.00** | **$0.00** | Air-gapped / Zero-Cost deployments on local GPUs |

---

### 3.5 Monthly Operational Run-Rate Comparison Table

| Operational Profile | Infrastructure Sizing | Database Tier | Average Monthly LLM Token Spend | Estimated Total Monthly Cost |
|---|---|---|---|---|
| **Tier A: Developer / Solo POC** | Azure App Service B1 ($12.41) | SQLite WAL ($0.00) | DeepSeek V3 (~$5.00) | **$17.41 / month** |
| **Tier B: Small Engineering Team (10 Devs)** | Azure App Service B1 ($12.41) | SQLite WAL ($0.00) | DeepSeek V3/R1 (~$45.00) | **$57.41 / month** |
| **Tier C: Growing Mid-Market (50 Devs)** | Azure App Service S1 ($70.08) | Postgres Burstable ($14.60) | DeepSeek + GPT-4o (~$120.00) | **$204.68 / month** |
| **Tier D: Enterprise Production (HA)** | Azure App Service P1v3 ($82.49) | Postgres GP D2s_v5 ($115.00) | Multi-Model Ensemble (~$250.00) | **$447.49 / month** |

---

### 3.6 Cost Optimization Guardrails & Best Practices

1. **Standalone Next.js Pre-Compilation (`--build-frontend`):**
   Pre-compiling the Next.js bundle removes devDependencies, reducing memory from 1.2 GB to 280 MB. This allows the frontend to run comfortably on a **$12.41/month Basic B1 plan** without upgrading to costly tiers.
2. **Context Compression & MAF Prompt Caching:**
   MAF caches static system prompts and repository AST schemas. Because DeepSeek provides a 90% discount on cached tokens ($0.014/1M), repeated turns in long conversations cost negligible fractions of a cent.
3. **Token Usage Budgets in `/usage`:**
   Configure monthly project caps (e.g., $100/month). The system will automatically switch agents to cheaper models or local Ollama instances when budget thresholds are reached.

---

## 4. Strict Branch Isolation & Protection Governance

> [!CAUTION]
> **GOVERNANCE MANDATE:**
> The branch **`feature/azure-kudu-deployment`** is strictly isolated.
> Under no circumstances can this branch be merged into `main`, `master`, or any other branch.

### Automated Checks Enforced:
1. **GitHub Actions Guard ([`.github/workflows/branch-lock-check.yml`](../.github/workflows/branch-lock-check.yml)):**
   Automatically fails any Pull Request targeting `main` from `feature/azure-kudu-deployment` or vice-versa.
2. **Local Pre-Merge Hook ([`scripts/verify_branch_isolation.sh`](../scripts/verify_branch_isolation.sh)):**
   Prevents local `git merge` execution with exit code 1.
3. **Standalone Operations:**
   All cloud conversions, packaging, and deployments must be performed directly on this branch.
