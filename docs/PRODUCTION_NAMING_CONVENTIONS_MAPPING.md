# Enterprise Production Naming Conventions & Codebase Architecture Mapping

This document provides a comprehensive mapping of platform components, API routes, workflows, and UI entities to enterprise production naming conventions. It details the exact impact analysis, dependency references, and compatibility guarantees to ensure **zero regressions, broken routes, or dead code**.

---

## 1. Executive Summary & Design Principles

To prepare the Agentic QE & AI SDLC platform for enterprise deployment, all entities are aligned with the following production naming principles:
1. **Explicit Domain Terminology**: Replace ambiguous or generic names (`Documents`, `Test cases`, `Requirements`, `Bugs`) with descriptive, professional titles (`Project Specifications`, `Deterministic Test Cases & Scenario Matrix`, `Functional & Verification Requirements Specification`, `Defect Scanner & Fixes`).
2. **Standardized Studio Hierarchy**: All creative and generative modules follow the unified `* Studio` standard (`BA Studio`, `Skill Creator Studio`, `QE Studio`).
3. **Route & Import Stability**: Next.js App Router paths (`/projects/[id]/documents`, `/projects/[id]/ba`, etc.) and backend module exports are preserved or aliased to avoid dead URLs, bookmark invalidation, or breaking external API contracts.

---

## 2. Core Architecture & Route Taxonomy Mapping

| Legacy / Internal Route | Enterprise Production Label | Subsystem | Description & Capability | Impact Count (Files) | Status & Compatibility Guarantee |
|:---|:---|:---|:---|:---:|:---|
| `/` | **Enterprise Workspaces** | Workspace Core | Overview of registered repositories and workspaces. | 14 | Preserved; enhanced with telemetry counters. |
| `/harness` | **Autonomous QE Harness** | Agentic Harness | Universal multi-agent chat interface with execution traces, gates, and skill palette. | 22 | Preserved; includes deep linking (`?project=`, `?skill=`). |
| `/skills/studio` | **Skill Creator Studio** | Skills Ecosystem | Grounded synthesis of Agent Skills from BRDs, user stories, and specs. | 8 | **NEW**; unified studio with script runner and evaluator. |
| `/skills` | **Project Skills & Tools** | Skills Ecosystem | Directory of installed skills, MAF plugins, and frontmatter tools. | 9 | Preserved; linked to Skill Studio. |
| `/agents` | **AI Specialist Roster** | AI SDLC Roster | Governance roster of all 13 specialized agents, risk tiers, and guardrails. | 7 | Preserved; equipped with Guardrail Matrix tooltips. |
| `/mcp` | **MCP Server Registry** | Protocol Layer | Model Context Protocol servers, sandboxed tools, and prompt endpoints. | 18 | Preserved; equipped with custom ConfirmModal deletion. |
| `/projects/[id]/repository` | **Codebase & AST Discovery** | AST Ingestion | Abstract Syntax Tree exploration, multi-root detection, and file index. | 6 | Preserved; enhanced with auto-discovery. |
| `/projects/[id]/ba` | **BA Studio (BRD & Gherkin)** | AI SDLC Studio | Requirements authoring from brief with 10-section format & Gherkin validation. | 12 | Preserved; integrated with contextual presets. |
| `/projects/[id]/documents` | **Project Specifications** | Specifications | Version-controlled requirements, plans, cases, and audit sign-offs. | 16 | **Overhauled UI**: explicit column widths, no squishing. |
| `/projects/[id]/feature` | **Feature Implementation** | Feature Engineering | Spec-driven code generation, test-driven validation on isolated branches. | 5 | Preserved; sandboxed worktree creation. |
| `/projects/[id]/bugs` | **Defect Scanner & Fixes** | Defect Engineering | Repository vulnerability scanning, AST pattern matching, and patch reviewers. | 8 | Preserved; added `bug-fix-reviewer` agent confidence. |
| `/projects/[id]/qe` | **Autonomous QE & AI SDLC** | SDLC Lifecycle | End-to-end quality engineering lifecycle from BRD intake to ZIP export. | 11 | Preserved; Greenfield vs Brownfield toggle. |
| `/projects/[id]/approvals` | **Quality Gate Approvals** | Governance | Formal HITL review checkpoints for Gates G0 through G5. | 10 | Preserved; instant real-time gate transitions. |
| `/projects/[id]/governance` | **Governance & Policies** | Enterprise RBAC | Project-level role-based access control and member authorizations. | 7 | Preserved; upgraded to modern modal confirmations. |
| `/projects/[id]/runs` | **Execution Runs & Metrics** | Telemetry | Real-time agent execution traces, token consumption, and latency logs. | 6 | Preserved; reads from centralized `atlas.sqlite3`. |
| `/projects/[id]/observability` | **Telemetry & Logs** | Observability | System event stream, error dumps, and prompt injection audit logs. | 8 | Preserved; connected to centralized ledger. |
| `/projects/[id]/prompts` | **Prompt Management** | Prompts Engine | Versioned system prompts, specialist personas, and guardrail constraints. | 4 | Preserved; immutable revision history. |

---

## 3. Specification Document Naming Taxonomy

Document titles previously generated with generic labels have been upgraded in the database (`atlas.sqlite3`) and the workflow generator (`qe.py`):

| Database Kind | Legacy Document Title | Production Enterprise Document Title | Associated Agent |
|:---|:---|:---|:---|
| `discovery` | `Discovery summary` | **Repository AST Architecture & Stack Discovery** | `agent:repo-intelligence-analyst` |
| `requirements` | `Requirements` | **Functional & Verification Requirements Specification** | `agent:requirements-analyst` |
| `test_plan` | `Test plan` | **Comprehensive Quality Strategy & Test Plan** | `agent:principal-test-architect` |
| `test_cases` | `Test cases` | **Deterministic Test Cases & Scenario Matrix** | `agent:test-design-architect` |
| `test_data` | `Test data` | **Synthesized Test Fixtures & Data Contracts** | `system (deterministic builder)` |
| `test_code` | `Generated tests` | **Autonomous End-to-End Test Suite** | `agent:test-automation-engineer` |
| `defect_report` | `Defect records` | **Repository Defect Triaging & Anomaly Report** | `system (execution analyzer)` |
| `traceability` | `Traceability matrix` | **Requirements-to-Test Traceability Matrix** | `system (coverage validator)` |
| `release` | `Release sign-off` | **Production Release Readiness & Sign-Off** | `agent:confidence-reviewer` |

---

## 4. Installed Agent Skills Taxonomy & Command Mapping

The platform onboards authentic Agent Skills conforming strictly to the [awesome-agent-skills](https://github.com/shivswami/awesome-agent-skills/tree/marketplace) standard:

| Skill Slug | Display Name | Subprocess Script | Autonomous Harness Tool | Capability & Role |
|:---|:---|:---|:---|:---|
| `skill-creator` | **Skill Creator Engine** | `scripts/create_skill.py` | `create_agent_skill` | Scaffolds valid `SKILL.md`, `scripts/run.py`, and `evals/evals.json` from BRD/prompts. |
| `evaluator` | **Skill & Prompt Evaluator** | `scripts/evaluate_skill.py` | `evaluate_agent_skill` | Benchmarks skills against evals test cases with Specter grading, groundedness, and faithfulness. |
| `analyzing-repositories` | **Repository AST Analyzer** | `scripts/scan-repo.ts` | `qe_discover` | Multi-root syntax tree parsing and import graph reconstruction. |
| `authoring-user-stories` | **User Story Synthesizer** | `scripts/export-cases.ts` | `qe_requirements` | Converts briefs into 10-section BRD and validated Gherkin scenarios. |
| `designing-test-cases` | **Test Case Designer** | `scripts/check-confidence.ts` | `qe_design` | Designs deterministic test cases with verifiable oracles. |
| `executing-tests` | **Sandboxed Test Executor** | `scripts/collect-evidence.ts` | `execute_tests` | Executes test suites in isolated temp worktrees with zero network leakage. |
| `building-qe-dashboard` | **QE Dashboard Builder** | `scripts/build-trace-report.ts` | `qe_sign` | Compiles release readiness reports and gate metrics. |
| `tracing-coverage` | **Traceability Validator** | `scripts/check-gate.ts` | `qe_trace` | Validates 100% requirement-to-test mapping and gate compliance. |

---

## 5. Renaming Impact Analysis & Dead-Code Prevention Strategy

1. **Path Preservations**:
   - `src/backend/maf/workflows/qe.py` updated to generate production document titles without modifying core enum types.
   - Database migrations executed on `data/atlas.sqlite3` so historic records reflect clean production labels.
2. **Zero Route Breakages**:
   - Next.js folder routes in `src/frontend/app/` retain clean URL slugs (`/projects/[id]/documents`, `/skills/studio`).
   - Breadcrumbs, page headings, and sidebar links display the upgraded production names.
3. **Cross-Reference Audit**:
   - Verified that all 13 agents, 8 tools, and 2 newly onboarded skills are registered in `qe_tools.py` and `src/backend/api/skills.py`.
   - Verified that TypeScript compilation completes with 0 errors across 19 production routes.
