"""Fixture for the backend API audit: an authenticated admin client and the four enterprise projects."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app


PROJECT_IDS = [
    "prj_agentic_qe",
    "prj_fintech_gateway",
    "prj_ecommerce_core",
    "prj_mcp_market",
]


@pytest.fixture(scope="module")
def client():
    """Authenticated admin TestClient fixture running lifespan."""
    from backend.db import db, now
    with db() as con:
        cur = con.cursor()
        sample_projects = [
            ("prj_agentic_qe", "Agentic QE Platform & Framework", "Full test engineering lifecycle"),
            ("prj_fintech_gateway", "Zero-Trust Financial Gateway", "Payment orchestration"),
            ("prj_ecommerce_core", "Enterprise Cloud Checkout", "Distributed cart & inventory"),
            ("prj_mcp_market", "MCP Server Market", "Marketplace and sandbox")
        ]
        stamp = now()
        for pid, name, desc in sample_projects:
            cur.execute(
                "INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived, owner_id) "
                "VALUES (?, ?, ?, ?, ?, 0, 'admin')",
                (pid, name, desc, stamp, stamp)
            )
            cur.execute(
                "INSERT OR IGNORE INTO repo_sources (project_id, kind, url, ref, commit_sha, analysis, scanned_at) "
                "VALUES (?, 'git', ?, 'main', '2015360', '{}', ?)",
                (pid, f"https://github.com/test/{pid}", stamp)
            )
    with TestClient(app) as test_client:
        admin_user = os.environ.get("ATLAS_ADMIN_USERNAME", "qa-admin")
        admin_pass = os.environ.get("ATLAS_ADMIN_PASSWORD", "")
        login_res = test_client.post(
            "/api/auth/login",
            json={"username": admin_user, "password": admin_pass},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        yield test_client
