"""Shared fixtures, constants and helpers for the API workflow tests."""

import io
import json
import os

import secrets
import time
import zipfile

import pytest

from fastapi.testclient import TestClient

from backend.app import app
from backend.maf import llm


BRD = """# Business Requirements Document (BRD)

## 1. Executive Summary
Lets members reset a password.

## 2. Business Objectives
1. Reduce support tickets.

## 3. Scope
Password reset only.

## 4. Stakeholders
Members.

## 5. Current State and Proposed State
Current State: manual password reset requests.
Proposed State: self-serve email password reset link.

## 6. Functional Requirements
FR-001 A member can request a reset link by email.

## 7. Non-Functional Requirements
Links expire within 30 minutes.

## 8. Business Rules
One active link per member.

## 9. Data and Integration Requirements
Integrates with email service provider.

## 10. Assumptions and Constraints
Email is verified.

## 11. Dependencies
SMTP or SendGrid delivery service.

## 12. Risks and Mitigations
Abuse is rate limited.

## 13. Transition Requirements
None.

## 14. Acceptance Criteria
User receives email with valid token.

## 15. Requirement Traceability
FR-001 maps to reset endpoint.

## 16. Open Questions
None.

## 17. Approval and Sign-Off
Approved by product owner.

## 18. References and Glossary
None.
"""


FEATURE = "Feature: Password reset\n\n  @FR-001\n  Scenario: Member requests a link\n    Given a member with a verified email\n    When they request a reset\n    Then a link valid for 30 minutes is sent\n"


GOOD_REVIEW = '{"score": 90, "verdict": "APPROVED", "issues": []}'


def rules():
    return [
        ("Review type: requirements document", GOOD_REVIEW),
        ("Convert this document's requirements into one Gherkin feature file", FEATURE),
        ("Artifact: requirements document", lambda text: BRD + ("\nRevised after feedback.\n" if "REVISE IT" in text else "")),
    ]


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


@pytest.fixture
def project(client):
    return client.post("/api/projects", json={"name": "Shop", "description": "Demo"}).json()


def wait_run(client, run_id, statuses=("waiting_approval", "completed", "failed", "rejected"), timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in statuses:
            return run
        time.sleep(0.1)
    raise AssertionError(f"Run stuck: {client.get(f'/api/runs/{run_id}').json()}")


def pending(run):
    return next(a for a in run["approvals"] if a["status"] == "pending")


def upload_repo(client, project, entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for name, body in entries.items():
            bundle.writestr(name, body)
    response = client.post(f"/api/projects/{project['id']}/repo/zip", files={"file": ("code.zip", buffer.getvalue(), "application/zip")})
    assert response.status_code == 200, response.text
    return response.json()


BUGGY = {"README.md": "# demo\n", "app/core.py": "import subprocess\n\n\ndef run(cmd):\n    return subprocess.call(cmd, shell=True)\n\n\ndef div(a, b):\n    return a / b\n"}


CALC = {"calc.py": "def add(a, b):\n    return a - b\n", "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n", "conftest.py": ""}


def edit_script(*edits):
    """Replies for an agent that sends structured edits. A string entry ends one reply; later entries form the next."""
    groups, current = [], []
    for edit in edits:
        if isinstance(edit, str):
            groups.append(current)
            current = []
        elif edit[0] == "write_file":
            current.append({"path": edit[1]["path"], "action": "create", "content": edit[1]["content"]})
        else:
            current.append({"path": edit[1]["path"], "action": "replace", "search": edit[1]["search"], "replace": edit[1]["replace"]})
    replies = iter(json.dumps({"summary": "Done.", "edits": group}) for group in [*groups, current])
    return lambda _: next(replies, json.dumps({"summary": "Done.", "edits": []}))


FIX_ADD = ("replace_text", {"path": "calc.py", "search": "return a - b", "replace": "return a + b"})


REQUIREMENTS = json.dumps({"requirements": [{"id": "REQ-001", "title": "Add", "statement": "add returns the sum", "priority": "P0", "tier": "observed", "file": "calc.py", "line": 2, "quote": "return a + b"},
                                            {"id": "REQ-002", "title": "Fake", "statement": "invented", "priority": "P0", "tier": "observed", "file": "calc.py", "line": 1, "quote": "not in the file"}]})


PLAN = json.dumps({"strategy": "Unit first", "areas": [{"id": "A1", "name": "Add", "requirement_ids": ["REQ-001"], "risk": "P0", "level": "Unit", "framework": "pytest", "rationale": "Pure logic"}], "skipped_levels": {"Integration": "No IO", "E2E": "No UI"}})


CASES = json.dumps({"cases": [
    {"id": "TC-APP-001", "requirement_id": "REQ-001", "scenario": "Adds", "type": "Positive", "level": "Unit", "steps": ["call add(2,3)"], "expected_result": "returns 5", "oracle": "specified", "test_data": "2, 3"},
    {"id": "TC-APP-002", "requirement_id": "REQ-001", "scenario": "Negatives", "type": "Negative", "level": "Unit", "steps": ["call add(-1,1)"], "expected_result": "returns 0", "oracle": "derived"},
    {"id": "TC-APP-003", "requirement_id": "REQ-001", "scenario": "Zero", "type": "Negative (Boundary)", "level": "Unit", "steps": ["call add(0,0)"], "expected_result": "returns 0", "oracle": "derived"},
    {"id": "TC-APP-004", "requirement_id": "REQ-001", "scenario": "Bad type", "type": "Exception", "level": "Unit", "steps": ["call add(1,None)"], "expected_result": "raises TypeError", "oracle": "specified"}]})


def _test_file(number, body):
    return {"path": f"tests/agentic_qe/test_tc_app_{number:03d}.py", "case_ids": [f"TC-APP-{number:03d}"], "content": f"# CASE_ID: TC-APP-{number:03d}\nimport pytest\nfrom calc import add\n\n\ndef test_TC_APP_{number:03d}():\n    {body}\n"}


TESTS = json.dumps({"framework": "pytest", "files": [
    _test_file(1, "assert add(2, 3) == 5"), _test_file(2, "assert add(-1, 1) == 0"), _test_file(3, "assert add(0, 0) == 0"),
    _test_file(4, "with pytest.raises(TypeError):\n        add(1, None)")]})


USER_PASSWORD = secrets.token_urlsafe(15)


def make_user(admin, name="priya.tester", **extra):
    """A user may use only ticked models, so tests give each one the listed test models unless they say otherwise."""
    from backend.core import models

    for listed in ("test-model", extra.get("model")):
        if listed:
            models.add(listed, enabled=True)
    extra = {"models": ["test-model", *([extra["model"]] if extra.get("model") else [])], **extra}
    made = admin.post("/api/users", json={"username": name, "password": USER_PASSWORD, **extra})
    assert made.status_code == 201, made.text
    return made.json()


def sign_in(name="priya.tester", password=USER_PASSWORD):
    other = TestClient(app)
    response = other.post("/api/auth/login", json={"username": name, "password": password})
    return other, response


def unique(prefix="user"):
    return f"{prefix}{time.time_ns()}"
