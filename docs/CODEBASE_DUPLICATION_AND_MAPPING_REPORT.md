# Codebase Duplication, Component Consolidation & Architecture Mapping Report

> **Target:** Agentic QE Platform & Multi-Agent Autonomous Harness  
> **Date:** November 2026  
> **Audience:** Core Engineering & Architecture Team  
> **Objective:** Identify duplicate frontend/backend components, eliminate redundant patterns, specify component reuse strategies, and map shared foundational infrastructure.

---

## 1. Executive Summary

This audit reviewed all frontend React/Next.js components, API routers, Microsoft Agent Framework (MAF 2.0) workflows, and shared core utilities. The audit identified five primary duplication clusters:
1. **Modal Dialogs & Confirmation Prompts:** Previously fragmented across native `window.confirm()` and one-off popup `div` implementations; now consolidated into the universal `ConfirmModal.tsx`.
2. **Workflow Run Observers & Run Panels:** Multiple pages (`bugs/page.tsx`, `qe/page.tsx`, `ba/page.tsx`) previously duplicated run-fetching intervals, state variables, and tab-persistence logic.
3. **Document Spec Viewing & Gherkin Rendering:** Fragmented markdown renderers and textareas replaced with `DocumentEditor.tsx` and interactive `GherkinVisualizer.tsx`.
4. **Member & Governance Access:** Replaced loose "Team Members & Roles" text inputs with `ProjectGovernanceAccess` tied to central RBAC policies and the cryptographic audit ledger.
5. **Static Import Resolvers in QE Workflows:** Duplicate module resolution logic between `emit.py` and `execution.py` unified with automatic multi-root discovery (`src/`, `backend/`, `modules/`, `core/`).

---

## 2. Component Duplication & Consolidation Mapping Table

| Component / Subsystem | Current Files / Locations | Duplicate Pattern Identified | Consolidated Single Source of Truth | Reuse Strategy & Improvement |
|---|---|---|---|---|
| **Confirmation & Alert Dialogs** | • `src/frontend/components/HarnessView.tsx`<br>• `src/frontend/app/mcp/page.tsx`<br>• `src/frontend/app/projects/[id]/documents/page.tsx`<br>• `src/frontend/app/projects/[id]/page.tsx` | Multiple local popup `div` backdrops, duplicate ESC handlers, and legacy `window.confirm()` calls | `src/frontend/components/ConfirmModal.tsx` | Universal modal accepting `isOpen`, `title`, `description`, `danger`, `onConfirm`, `onCancel`. Enforces consistent backdrop blur, keyboard trap, and WCAG accessibility across all pages. |
| **Gherkin Scenario Visualizer** | • `src/frontend/app/projects/[id]/documents/[docId]/page.tsx`<br>• `src/frontend/app/projects/[id]/ba/page.tsx`<br>• `src/frontend/components/HarnessView.tsx` | Raw `<pre><code>` blocks displaying monochrome Gherkin text without keyword styling or scenario badges | `src/frontend/components/GherkinVisualizer.tsx` | Parses Gherkin AST into structured Scenario blocks; renders color-coded badges for `Feature:`, `Scenario:`, `Given`, `When`, `Then`, `And`. Provides one-click Markdown and .feature export. |
| **Active Run Persistence & Tab Switching** | • `src/frontend/app/projects/[id]/bugs/page.tsx`<br>• `src/frontend/app/projects/[id]/qe/page.tsx`<br>• `src/frontend/app/projects/[id]/ba/page.tsx` | Each page implemented divergent `sessionStorage` keys; navigating between tabs caused active workflow state loss or empty findings display | Shared Run Memory Pattern & `RunList.tsx` auto-selection | Stores active `runId` in both `localStorage` and `sessionStorage`. On page mount, if no active run is running, automatically selects the latest completed run so findings and execution traces remain visible. |
| **Project Governance & Collaborators** | • `src/frontend/app/projects/[id]/page.tsx`<br>• `src/frontend/app/governance/page.tsx` | Legacy "Team Members & Roles" card allowed typing arbitrary usernames without checking directory existence or showing capability permissions | `ProjectGovernanceAccess` component in `src/frontend/app/projects/[id]/page.tsx` | Enforces enterprise RBAC: users must exist in Microsoft Entra ID / Admin-provisioned directory. Displays capability matrices per role (Lead Architect, QA Engineer, Developer, Viewer) and logs invitations to the immutable ledger. |
| **Guardrail Flags & Security Interception** | • `src/frontend/app/agents/page.tsx`<br>• `src/frontend/app/observability/page.tsx`<br>• `src/frontend/components/Observability.tsx` | Security cards displayed events (REMOVED, REDACTED) without clear explanations of threat vectors or what triggers them | `GUARDRAIL_FLAGS` Matrix with Interactive Info Tooltips (`src/frontend/app/agents/page.tsx`) | Table defines exact criteria, risk level, and defense heuristics for Prompt Injection, Secrets, Demarcation, Path Traversal, Tautological Asserts, Code Drift, and Token Limits. Hover tooltips explain each flag. |
| **Python AST Module Resolution & Import Checks** | • `src/backend/qe/emit.py` (`Project` class)<br>• `src/backend/qe/execution.py` (`invalid_test_code`) | `Project` only checked `worktree` and `worktree/src`; `invalid_test_code` only checked `worktree`. Repositories with `backend/`, `modules/`, or `core/` caused false "module does not exist" errors | Unified Subroot Discovery in `emit.py` & `execution.py` | Both utilities now inspect `("backend", "src", "server", "app", "modules", "core")`. Dotted import aliases (`backend.main` -> `backend.app.main`) are auto-resolved before static checks. |
| **Generated Test Syntax Sanitization** | • `src/backend/maf/workflows/qe.py`<br>• `src/backend/maf/workflows/edits.py` | Model responses containing markdown code fences (` ```python `) caused `SyntaxError: expected '('` in `apply_edits`, crashing the entire run | `_clean_code()` + Test Quarantine in `qe.py` | Code fences are automatically stripped. If a single test file fails syntax checks, it is auto-quarantined as `@pytest.mark.skip`, allowing the other 70+ valid tests to execute and produce complete JUnit evidence. |
| **Document & Quality Gate Synchronization** | • `src/backend/core/documents.py`<br>• `src/backend/core/gates.py`<br>• `src/frontend/components/ApprovalsList.tsx` | Approving a document did not update the corresponding quality gate in SQLite; approving a gate did not mark the draft document approved | Bidirectional Event Sync in `documents.set_status()` & `gates.decide()` | Approving BRD/PRD automatically decides Gate 1; approving Test Plan decides Gate 2; approving Gherkin decides Gate 3. Approving a gate updates pending documents to `approved`. |

---

## 3. Code Reuse Strategies & Optimization Guidelines

### Strategy 1: Centralized State Over Prop Drilling
- **Database Sole Source of Truth:** Never store domain entity replicas in disconnected memory maps. All pages query `/api/projects/{id}/...` backed by `atlas.sqlite3`.
- **Zero Mock Policy:** When testing or running UI, always assert against actual SQLite table rows and real worktree file paths.

### Strategy 2: Graceful Fault Containment
- In multi-agent test generation (where 50–100 tests are generated in batches), an individual model syntax defect in 1 file must **NEVER** abort the entire 8-gate lifecycle.
- Quarantine malformed files into skipped tests (`@pytest.mark.skip(reason=...)`), append findings to `unresolved`, and allow the remaining test suite to run.

### Strategy 3: Component Atomicity
- Shared interactive components (`ConfirmModal`, `GherkinVisualizer`, `DocumentEditor`, `ModelPicker`, `RunPanel`) reside exclusively in `src/frontend/components/` and are imported into page routers via relative paths.

---

## 4. Architectural Tasks & Verification Checklist

- [x] **Task 1: Universal Modal Consolidation:** Eliminate all native `confirm()` and `prompt()` dialogs in favor of `ConfirmModal.tsx`.
- [x] **Task 2: Eliminate Duplicate Markdown Documentation:** Removed redundant `AZURE_DEPLOY.md`, `AZURE_SYSTEM_DESIGN.md`, and `PROJECT_STRUCTURE.md`. Consolidated all deployment, pricing, and sandbox architecture into `AZURE_DEPLOYMENT_GUIDE.md`.
- [x] **Task 3: Grounded AST Import Grounding:** Multi-root discovery enabled for `backend/`, `modules/`, and `core/` to prevent false import rejections.
- [x] **Task 4: Test Syntax Error Quarantine:** Auto-strip markdown fences and quarantine malformed files rather than throwing fatal `AQE-INT-001` crashes.
- [x] **Task 5: Guardrail Flags Explanatory Table:** Added interactive threat mitigation matrix with info hover icons to `/agents`.
- [x] **Task 6: Enterprise Governance UI:** Replaced plain team members card with Enterprise RBAC Governance card enforcing pre-provisioned directory accounts.
- [x] **Task 7: Harness Chat History Reset:** Added backend endpoint `DELETE /api/harness/sessions` and UI "Clear All" button with confirmation modal.
- [x] **Task 8: Bidirectional Approvals Sync:** Synchronized document approvals with Quality Gates G0–G3.
