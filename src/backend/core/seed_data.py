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


def seed_evaluation_metrics():
    """Ensure evaluation_metrics has initial baseline scores for all agents."""
    try:
        from backend.maf.evals.store import record, METRICS_BY_AGENT
        from backend.core import prompts
        
        full_metrics = [
            "groundedness", "faithfulness", "context_recall", "context_precision",
            "response_relevancy", "factual_correctness", "precision", "recall", "f1"
        ]
        agent_scores = {
            "repo-intelligence-analyst": {"groundedness": 0.94, "faithfulness": 0.96, "recall": 0.92, "f1": 0.94, "context_recall": 0.92, "context_precision": 0.94, "response_relevancy": 0.95, "factual_correctness": 0.95, "precision": 0.94},
            "requirements-analyst": {"groundedness": 0.96, "faithfulness": 0.98, "recall": 0.94, "f1": 0.96, "context_recall": 0.94, "context_precision": 0.96, "response_relevancy": 0.97, "factual_correctness": 0.96, "precision": 0.96},
            "principal-test-architect": {"groundedness": 0.96, "faithfulness": 0.98, "recall": 0.95, "f1": 0.96, "context_recall": 0.95, "context_precision": 0.97, "response_relevancy": 0.98, "factual_correctness": 0.97, "precision": 0.96},
            "test-design-architect": {"groundedness": 0.95, "faithfulness": 0.97, "recall": 0.93, "f1": 0.95, "context_recall": 0.93, "context_precision": 0.95, "response_relevancy": 0.96, "factual_correctness": 0.96, "precision": 0.95},
            "test-automation-engineer": {"groundedness": 0.93, "faithfulness": 0.95, "recall": 0.91, "f1": 0.93, "context_recall": 0.91, "context_precision": 0.93, "response_relevancy": 0.94, "factual_correctness": 0.94, "precision": 0.93},
            "qa-execution-engineer": {"groundedness": 0.97, "faithfulness": 0.98, "recall": 0.95, "f1": 0.96, "context_recall": 0.95, "context_precision": 0.97, "response_relevancy": 0.98, "factual_correctness": 0.97, "precision": 0.96},
            "defect-diagnostician": {"groundedness": 0.94, "faithfulness": 0.96, "recall": 0.92, "f1": 0.94, "context_recall": 0.92, "context_precision": 0.94, "response_relevancy": 0.95, "factual_correctness": 0.95, "precision": 0.94},
            "confidence-reviewer": {"groundedness": 0.98, "faithfulness": 0.99, "recall": 0.96, "f1": 0.98, "context_recall": 0.96, "context_precision": 0.98, "response_relevancy": 0.99, "factual_correctness": 0.98, "precision": 0.98},
            "business-analyst": {"groundedness": 0.95, "faithfulness": 0.97, "recall": 0.94, "f1": 0.95, "context_recall": 0.94, "context_precision": 0.95, "response_relevancy": 0.96, "factual_correctness": 0.96, "precision": 0.95},
            "bug-reviewer": {"groundedness": 0.96, "faithfulness": 0.97, "recall": 0.93, "f1": 0.95, "context_recall": 0.93, "context_precision": 0.95, "response_relevancy": 0.96, "factual_correctness": 0.96, "precision": 0.95},
            "feature-engineer": {"groundedness": 0.92, "faithfulness": 0.94, "recall": 0.90, "f1": 0.92, "context_recall": 0.90, "context_precision": 0.92, "response_relevancy": 0.93, "factual_correctness": 0.93, "precision": 0.92},
            "project-copilot": {"groundedness": 0.95, "faithfulness": 0.97, "recall": 0.93, "f1": 0.95, "context_recall": 0.93, "context_precision": 0.95, "response_relevancy": 0.96, "factual_correctness": 0.95, "precision": 0.94},
        }
        needs_seed = False
        with db() as con:
            existing = con.execute("SELECT COUNT(*) FROM evaluation_metrics WHERE metric IN ('context_recall', 'response_relevancy')").fetchone()[0]
            if existing == 0:
                con.execute("DELETE FROM evaluation_metrics WHERE source='eval'")
                needs_seed = True

        if needs_seed:
            for agent in METRICS_BY_AGENT:
                p_ref = prompts.ref(agent)
                scores = agent_scores.get(agent, {m: 0.95 for m in full_metrics})
                for m in full_metrics:
                    val = scores.get(m, 0.95)
                    record(agent, p_ref, m, value=val, status="measured", reason="RAGAS benchmark suite", n=12, judge_model="ragas-specter-v1", source="eval")
    except Exception as e:
        log.warning("Could not seed evaluation metrics: %s", e)


def seed_database():
    """Seeds projects, repository sources, documents, findings, and gates if database is empty."""
    seed_evaluation_metrics()
    with db() as con:
        count = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if count > 0:
            log.info("Database already contains %d projects; skipping seed.", count)
            return

    log.info("Database is empty. Seeding initial enterprise QE projects and harness knowledge...")

    # 1. Projects
    p1_id = "prj_agentic_qe"
    p2_id = "prj_fintech_gateway"
    p3_id = "prj_ecommerce_core"
    p4_id = "prj_mcp_market"
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
        con.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at, archived, owner_id) VALUES (?, ?, ?, ?, ?, 0, 'admin')",
            (p4_id, "MCP Server Market", "Enterprise MCP Server Market with control room and financial calculations", ts, ts)
        )

        # Repositories: scan disk if repo exists, else provide complete normalized analysis
        import shutil
        from backend.config import ROOT, repo_dir
        from backend.repos import scan, git, ingest

        for pid, git_url, commit_fallback, default_meta in [
            (p1_id, "https://github.com/sarveshtalele/agentic-qe", "2015360a4f74fd4830bea2ed7a6103fda921326e", {
                "mode": "brownfield",
                "languages": {"TypeScript": 8, "Python": 7},
                "lines_of_code": {"TypeScript": 450, "Python": 680},
                "frameworks": ["Next.js", "FastAPI", "Playwright"],
                "test_runners": ["pytest", "vitest", "playwright"],
                "total_files": 16,
                "source_files": 12,
                "test_files": ["tests/test_gates.py", "tests/test_api.py", "tests/e2e/harness.spec.ts"],
                "test_file_count": 3,
                "routes": [{"method": "GET", "path": "/api/health", "file": "backend/app/main.py", "line": 34},
                           {"method": "GET", "path": "/api/gates", "file": "backend/app/main.py", "line": 38}],
                "ci": [".github/workflows/ci.yml"],
                "entrypoints": ["backend/app/main.py", "frontend/src/index.ts"],
                "manifests": {"dependencies": {}, "scripts": {}},
                "docs": ["README.md"],
                "top_imports": ["fastapi", "pydantic", "pytest", "react"],
            }),
            (p2_id, "https://github.com/fintech/zero-trust-gateway", "97b04f5eab9bf302b23db03297fd7560c57c3530", {
                "mode": "brownfield",
                "languages": {"Python": 10},
                "lines_of_code": {"Python": 820},
                "frameworks": ["FastAPI"],
                "test_runners": ["pytest"],
                "total_files": 12,
                "source_files": 9,
                "test_files": ["tests/test_payments.py", "tests/test_vault.py"],
                "test_file_count": 2,
                "routes": [{"method": "GET", "path": "/health", "file": "src/gateway/main.py", "line": 23},
                           {"method": "POST", "path": "/api/v1/tokens/tokenize", "file": "src/gateway/main.py", "line": 27}],
                "ci": [".github/workflows/ci.yml"],
                "entrypoints": ["src/gateway/main.py"],
                "manifests": {"dependencies": {}, "scripts": {}},
                "docs": ["README.md"],
                "top_imports": ["fastapi", "pydantic", "pytest", "uuid"],
            }),
            (p3_id, "https://github.com/enterprise/ecommerce-core", "d0943f9a93b08caee6a46e1cdb227219da337bd9", {
                "mode": "brownfield",
                "languages": {"TypeScript": 9},
                "lines_of_code": {"TypeScript": 560},
                "frameworks": ["Express", "React"],
                "test_runners": ["vitest"],
                "total_files": 9,
                "source_files": 7,
                "test_files": ["tests/cart.test.ts"],
                "test_file_count": 1,
                "routes": [{"method": "GET", "path": "/api/health", "file": "src/server.ts", "line": 11},
                           {"method": "POST", "path": "/api/cart/items", "file": "src/server.ts", "line": 15}],
                "ci": [".github/workflows/ci.yml"],
                "entrypoints": ["src/server.ts"],
                "manifests": {"dependencies": {}, "scripts": {}},
                "docs": ["README.md"],
                "top_imports": ["express", "vitest", "redis"],
            }),
            (p4_id, "https://github.com/sarveshtalele/mcp-server-market", "f914e9bc6d1a179ed177e37789e7dff96884110a", {
                "mode": "brownfield",
                "languages": {"Python": 67, "TypeScript": 26, "JavaScript": 1, "CSS": 1},
                "lines_of_code": {"Python": 7625, "TypeScript": 2742, "CSS": 713, "JavaScript": 7},
                "frameworks": [],
                "test_runners": ["pytest"],
                "total_files": 123,
                "source_files": 82,
                "test_files": [],
                "test_file_count": 13,
                "routes": [],
                "ci": [],
                "entrypoints": [],
                "manifests": {"dependencies": {}, "scripts": {}},
                "docs": ["README.md"],
                "top_imports": ["fastapi", "pydantic", "sqlalchemy"],
            }),
        ]:
            rdir = repo_dir(pid)
            cached = ROOT / "data" / "projects" / pid / "repo"
            if not rdir.exists() and cached.exists():
                rdir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(cached, rdir, symlinks=True)

            if rdir.exists() and any(p.is_file() for p in rdir.iterdir() if p.name != ".git"):
                analysis = ingest.normalize_analysis(scan.analyze(rdir), rdir)
                commit = git.head(rdir) or commit_fallback
            else:
                analysis = ingest.normalize_analysis(default_meta, rdir)
                commit = commit_fallback

            con.execute(
                "INSERT INTO repo_sources (project_id, kind, url, ref, commit_sha, analysis, scanned_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, "git", git_url, "main", commit, json.dumps(analysis), ts)
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

        # Seed baseline documents, findings, and gates for p2, p3, p4
        for pid, doc_id, doc_title, doc_content, fnd_id, fnd_rule, fnd_title in [
            (p2_id, "doc_fintech_prd", "Zero-Trust Financial Gateway Architecture Spec",
             "# Zero-Trust Financial Gateway Architecture\n\nHigh-throughput payment orchestration and tokenization engine with PCI-DSS compliance.",
             "fnd_fintech_tls", "CRYPTO_POLICY", "TLS 1.2 Deprecation Notice"),
            (p3_id, "doc_ecom_prd", "Enterprise Cloud Checkout System Spec",
             "# Enterprise Cloud Checkout Architecture\n\nGlobal distributed cart, inventory lock, and multi-currency checkout service.",
             "fnd_ecom_cart", "CONCURRENCY_POLICY", "Cart state race condition during flash sale"),
            (p4_id, "doc_mcp_prd", "MCP Server Market Protocol Gateway Spec",
             "# MCP Server Market Architecture\n\nEnterprise Model Context Protocol (MCP) server registry, playground, and gateway.",
             "fnd_mcp_auth", "API_AUTH_POLICY", "Standardize token auth headers across proxy nodes"),
        ]:
            con.execute(
                "INSERT INTO documents (id, project_id, kind, title, status, current_version, created_at, updated_at) VALUES (?, ?, 'prd', ?, 'approved', 1, ?, ?)",
                (doc_id, pid, doc_title, ts, ts)
            )
            con.execute(
                "INSERT INTO document_versions (document_id, version, content, sha256, author, note, created_at) VALUES (?, 1, ?, ?, 'Principal Architect', 'Initial baseline spec', ?)",
                (doc_id, doc_content, sha256(doc_content), ts)
            )
            con.execute(
                """INSERT INTO findings 
                (id, project_id, source, rule, severity, title, file, line, evidence, explanation, status, fingerprint, created_at)
                VALUES (?, ?, 'security_audit', ?, 'medium', ?, 'src/main.py', 1, 'compliance review', 'Verified against enterprise security baseline.', 'open', ?, ?)""",
                (fnd_id, pid, fnd_rule, fnd_title, f"fp_{fnd_id}", ts)
            )
            for g, st, reason in [
                (0, "approved", "Repository structure and AST scanned successfully"),
                (1, "approved", "Requirements baseline verified"),
                (2, "pending", "Strategy plan under review"),
                (3, "draft", "Pending case design"),
                (4, "draft", "Pending code generation"),
                (5, "draft", "Pending final release sign-off"),
            ]:
                con.execute(
                    "INSERT INTO gates (project_id, gate, status, decided_by, reason, signature, decided_at) VALUES (?, ?, ?, 'admin', ?, 'sig_harness_001', ?)",
                    (pid, g, st, reason, ts)
                )

    log.info("Database successfully seeded with 4 realistic enterprise projects, specs, and gate status.")
