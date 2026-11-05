"""Initial seed data for Agentic QE Platform & Harness.
Populates SQLite Write-Ahead Log database (atlas.sqlite3) with real, high-quality projects,
specifications, Gherkin feature files, findings, gate scorecards, and audit events.
"""
from __future__ import annotations

import json
import logging
from backend.core.security import sha256
from backend.db import db, now, row, rows

log = logging.getLogger("aqe.seed")


def seed_database():
    """Seeds projects, repository sources, documents, findings, and gates if database is empty."""
    with db() as con:
        count = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if count > 0:
            log.info("Database already contains %d projects; skipping seed.", count)
            return

    log.info("Database is empty. Seeding initial enterprise QE projects and harness knowledge...")

    # 1. Project: Agentic QE Platform & Framework
    p1_id = "prj_agentic_qe"
    p2_id = "prj_fintech_gateway"
    p3_id = "prj_ecommerce_core"
    ts = now()

    with db() as con:
        # Projects
        con.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at, archived, owner_id) VALUES (?, ?, ?, ?, ?, 0, 'admin')",
            (p1_id, "Agentic QE Platform & Framework", "Full test engineering lifecycle harness with 8 quality gates, 58 local skills, and autonomous MAF agents.", ts, ts)
        )
        con.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at, archived, owner_id) VALUES (?, ?, ?, ?, ?, 0, 'admin')",
            (p2_id, "Zero-Trust Financial Gateway", "High-throughput payment orchestration and tokenization engine with PCI-DSS compliance.", ts, ts)
        )
        con.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at, archived, owner_id) VALUES (?, ?, ?, ?, ?, 0, 'admin')",
            (p3_id, "Enterprise Cloud Checkout", "Global distributed cart, inventory lock, and multi-currency checkout service.", ts, ts)
        )

        # Repositories
        p1_analysis = json.dumps({
            "languages": ["TypeScript", "Python", "Shell"],
            "frameworks": ["Next.js", "FastAPI", "Playwright"],
            "components": ["Harness Engine", "Local Skill Discovery", "MAF Protocol Adapter", "SQLite WAL"],
            "total_files": 142
        })
        con.execute(
            "INSERT INTO repo_sources (project_id, kind, url, ref, commit_sha, analysis, scanned_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p1_id, "github", "https://github.com/sarveshtalele/agentic-qe", "main", "a7f3e9c", p1_analysis, ts)
        )

        p2_analysis = json.dumps({
            "languages": ["Python", "Rust", "SQL"],
            "frameworks": ["FastAPI", "Tokio", "PostgreSQL"],
            "components": ["Idempotency Guard", "Token Vault", "Webhook Dispatcher"],
            "total_files": 89
        })
        con.execute(
            "INSERT INTO repo_sources (project_id, kind, url, ref, commit_sha, analysis, scanned_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p2_id, "github", "https://github.com/fintech/zero-trust-gateway", "main", "b41d8e2", p2_analysis, ts)
        )

        p3_analysis = json.dumps({
            "languages": ["TypeScript", "Go"],
            "frameworks": ["React", "Gin", "Redis"],
            "components": ["Cart Sync", "Inventory Lock", "Checkout State Machine"],
            "total_files": 115
        })
        con.execute(
            "INSERT INTO repo_sources (project_id, kind, url, ref, commit_sha, analysis, scanned_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p3_id, "github", "https://github.com/enterprise/ecommerce-core", "main", "e993ab1", p3_analysis, ts)
        )

        # Documents & Versions for prj_agentic_qe
        d1_id = "doc_aqe_prd"
        d1_body = """# Agentic QE System Architecture & Gate Guardrails

## 1. System Objectives
Autonomous quality engineering platform combining Microsoft Agent Framework (MAF 2.0),
58 local machine skills, and strict 8-stage quality gate verification.

## 2. Quality Gates Model
- Gate 0: Repository Discovery & AST Analysis
- Gate 1: Requirements Extraction & User Stories
- Gate 2: Level Allocation Fit (Unit, Integration, E2E)
- Gate 3: Deterministic Test Case Design
- Gate 4: Test Data Generation & Masking
- Gate 5: Automated Code Generation & Linting
- Gate 6: Execution & Self-Healing
- Gate 7: Traceability Matrix & Sign-off
"""
        con.execute(
            "INSERT INTO documents (id, project_id, kind, title, status, current_version, created_at, updated_at) VALUES (?, ?, 'prd', ?, 'approved', 1, ?, ?)",
            (d1_id, p1_id, "Agentic QE PRD & Architecture Spec", ts, ts)
        )
        con.execute(
            "INSERT INTO document_versions (document_id, version, content, sha256, author, note, created_at) VALUES (?, 1, ?, ?, 'Principal Test Architect', 'Initial version', ?)",
            (d1_id, d1_body, sha256(d1_body), ts)
        )

        d2_id = "doc_aqe_gherkin"
        d2_body = """Feature: Quality Gate Guardrails
  As a Quality Lead
  I want autonomous guardrails on every gate
  So that untested code cannot reach production

  Scenario: Prevent execution in Plan Mode
    Given the harness is running in "plan" mode
    When a tool requesting file deletion is invoked
    Then the action is refused with a plan-mode guardrail message
    And no destructive changes are applied

  Scenario: Require human approval for Gate Signoff
    Given test generation has completed
    When the agent requests signoff for Gate G4
    Then an approval card is emitted to the user
    And the execution pauses until explicit signoff
"""
        con.execute(
            "INSERT INTO documents (id, project_id, kind, title, status, current_version, created_at, updated_at) VALUES (?, ?, 'gherkin', ?, 'approved', 1, ?, ?)",
            (d2_id, p1_id, "Quality Gate Guardrails Specification", ts, ts)
        )
        con.execute(
            "INSERT INTO document_versions (document_id, version, content, sha256, author, note, created_at) VALUES (?, 1, ?, ?, 'Test Design Architect', 'Gherkin specification for quality gates', ?)",
            (d2_id, d2_body, sha256(d2_body), ts)
        )

        # Findings for prj_agentic_qe
        f1_id = "fnd_cors_dev"
        con.execute(
            """INSERT INTO findings 
            (id, project_id, source, rule, severity, title, file, line, evidence, explanation, status, fingerprint, created_at)
            VALUES (?, ?, 'security_audit', 'CORS_POLICY', 'high', 'CORS Wildcard Configuration in Local Dev', 'backend/main.py', 32, 'allow_origins=[\"*\"]', 'Wildcard CORS allows arbitrary origins to interact with local harness API.', 'closed', 'fp_cors_001', ?)""",
            (f1_id, p1_id, ts)
        )

        f2_id = "fnd_flaky_browser"
        con.execute(
            """INSERT INTO findings 
            (id, project_id, source, rule, severity, title, file, line, evidence, explanation, status, fingerprint, created_at)
            VALUES (?, ?, 'qe_execution', 'TEST_STABILITY', 'medium', 'Flaky browser teardown in Playwright CI runner', 'tests/e2e/test_ui.py', 45, 'browser.close() timeout on headless linux', 'Chromium zombie processes when runners abort prematurely.', 'open', 'fp_flaky_002', ?)""",
            (f2_id, p1_id, ts)
        )

        # Gates for prj_agentic_qe (G0-G3 approved, G4 pending)
        for g, st, reason in [
            (0, "approved", "Repository structure, 58 skills, and AST scanned successfully"),
            (1, "approved", "Requirements extracted and verified against Gherkin scenarios"),
            (2, "approved", "Level allocation fit passed: 60% Unit, 30% API, 10% E2E"),
            (3, "approved", "Deterministic test cases reviewed and mock boundaries established"),
            (4, "pending", "Synthesized test data awaiting approval from Data Officer"),
            (5, "draft", "Pending code generation"),
            (6, "draft", "Pending execution"),
            (7, "draft", "Pending final sign-off"),
        ]:
            con.execute(
                "INSERT INTO gates (project_id, gate, status, decided_by, reason, signature, decided_at) VALUES (?, ?, ?, 'admin', ?, 'sig_harness_001', ?)",
                (p1_id, g, st, reason, ts)
            )

        # Runs (inserted before approvals due to foreign key)
        run_id = "run_init_001"
        con.execute(
            """INSERT INTO runs (id, project_id, workflow, status, input, state, error, tokens_in, tokens_out, started_at, ended_at)
            VALUES (?, ?, 'qe_full_cycle', 'success', 'Automated test discovery and case design', '{}', '', 14200, 3180, ?, ?)""",
            (run_id, p1_id, ts, ts)
        )

        # Approvals
        appr_id = "appr_gate4_data"
        con.execute(
            """INSERT INTO approvals (id, run_id, project_id, gate, title, summary, payload, status, decided_by, created_at)
            VALUES (?, 'run_init_001', ?, 4, 'Gate 4: Synthetic Test Data Approval', 'Approve synthetic payment cards and user mock payloads for automated execution.', '{}', 'pending', NULL, ?)""",
            (appr_id, p1_id, ts)
        )

        # Memories
        con.execute(
            "INSERT INTO memories (id, project_id, content, source, created_at) VALUES ('mem_001', ?, 'Platform uses Microsoft Agent Framework (MAF 2.0) with AG-UI and CopilotKit protocol streaming.', 'Harness Architect', ?)",
            (p1_id, ts)
        )
        con.execute(
            "INSERT INTO memories (id, project_id, content, source, created_at) VALUES ('mem_002', ?, 'Local skills catalog loaded 58 active skills including cloudflare security-audit and all agentic-qe lifecycle capabilities.', 'Skill Discovery Engine', ?)",
            (p1_id, ts)
        )

    log.info("Database successfully seeded with 3 realistic enterprise projects, specs, and gate status.")
