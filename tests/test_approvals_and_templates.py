"""Project approval decisions come only from the approvals table; template upload. Kept from the retired legacy suite."""
import io
import json
import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.db import db, new_id, now, row
from tests.helpers_api import unique


@pytest.fixture
def admin():
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": os.environ["ATLAS_ADMIN_USERNAME"], "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield client


def _pending(admin, gate: int, title: str) -> tuple[str, str]:
    project = admin.post("/api/projects", json={"name": unique("appr"), "description": "approvals"}).json()["id"]
    run_id, approval_id, stamp = new_id("run"), new_id("appr"), now()
    with db() as con:
        con.execute("INSERT INTO runs (id, project_id, workflow, status, input, started_at, state) VALUES (?,?,?,?,?,?,?)",
                    (run_id, project, "qe", "awaiting_approval", "{}", stamp, json.dumps({})))
        con.execute("INSERT INTO approvals (id, run_id, project_id, gate, title, summary, payload, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (approval_id, run_id, project, gate, title, "check", "{}", "pending", stamp))
    return project, approval_id


@pytest.mark.parametrize("approved,status", [(True, "approved"), (False, "rejected")])
def test_project_approval_decision_is_stored_with_feedback_and_ledgered(admin, approved, status):
    project, approval_id = _pending(admin, 0, "Gate 0: Intake")
    assert any(a["id"] == approval_id for a in admin.get(f"/api/projects/{project}/approvals").json())
    got = admin.post(f"/api/projects/{project}/approvals/{approval_id}/decide", json={"approved": approved, "feedback": "checked by a human"})
    assert got.status_code == 200, got.text
    with db() as con:
        stored = row(con.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)))
    assert stored["status"] == status and stored["feedback"] == "checked by a human" and stored["decided_at"]
    assert any("gate" in e["action"] or "approval" in e["action"] for e in admin.get(f"/api/projects/{project}/ledger").json()["entries"])


def test_unknown_or_foreign_approval_is_404_and_nothing_is_ledgered(admin):
    project, approval_id = _pending(admin, 1, "Gate 1")
    other = admin.post("/api/projects", json={"name": unique("other"), "description": ""}).json()["id"]
    before = len(admin.get(f"/api/projects/{other}/ledger").json()["entries"])
    assert admin.post(f"/api/projects/{other}/approvals/appr_missing/decide", json={"approved": True, "feedback": ""}).status_code == 404
    assert admin.post(f"/api/projects/{other}/approvals/{approval_id}/decide", json={"approved": True, "feedback": ""}).status_code == 404
    assert len(admin.get(f"/api/projects/{other}/ledger").json()["entries"]) == before
    assert admin.post("/api/approvals/appr_missing/decide", json={"approved": True, "feedback": ""}).status_code == 404


def test_template_upload_reads_markdown_sections_and_plain_text(admin):
    project = admin.post("/api/projects", json={"name": unique("tpl"), "description": ""}).json()["id"]
    md = b"# BRD template\n\n## Summary\nGoals.\n\n## Requirements\nFR-1.\n\n## Acceptance\nCriteria.\n"
    got = admin.post(f"/api/projects/{project}/templates/upload", files={"file": ("brd.md", io.BytesIO(md), "text/markdown")})
    assert got.status_code == 201 and got.json()["template_id"] and len(got.json()["sections"]) >= 3
    got = admin.post(f"/api/projects/{project}/templates/upload", files={"file": ("plain.txt", io.BytesIO(b"Requirement 1: fast login.\n"), "text/plain")})
    assert got.status_code == 201 and len(got.json()["sections"]) >= 1
