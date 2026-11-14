"""Gate 4 shows the validity result, and the run's tests download as a zip, through the real API with the scripted model."""
import io
import json
import zipfile

from fastapi.testclient import TestClient

from backend.app import app
from backend.config import project_dir
from backend.maf import engine, llm
from tests.helpers_access import account
from tests.helpers_api import CASES, PLAN, REQUIREMENTS, TESTS, client, pending, project, upload_repo, wait_run  # noqa: F401 - fixtures
from tests.helpers_validity import make_run_env
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient


def to_gate4(client, project, with_env, author=TESTS):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    if with_env:
        make_run_env(project_dir(project["id"]) / "worktrees" / "x")  # the .venv the run's worktree sits beside
    llm.set_client_override(ScriptedClient([
        ("You are a repository intelligence analyst", "## Purpose\nCalculator"), ("You are a requirements analyst", REQUIREMENTS), ("You are a principal test architect", PLAN),
        *case_rules(), ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
        ("You are a test design architect", CASES), ("You are a test automation engineer", author)]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    for _ in range(5):
        run = wait_run(client, run["id"])
        assert run["status"] == "waiting_approval", run["error"]
        approval = pending(run)
        if approval["gate"] == 4:
            return run, approval
        assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200
    raise AssertionError("Gate 4 was not reached")


def approve_gate4(client, run, approval):
    """The run state, and so the zip, is saved when the gate is approved."""
    assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200
    return wait_run(client, run["id"])


def test_gate4_shows_validity_and_the_zip_holds_valid_tests(client, project):
    run, approval = to_gate4(client, project, with_env=True)
    validation = approval["payload"]["validation"]
    assert "Validity: 4 of 4 tests valid; 0 need review (V1 0, V2b 0, V3 0, V4 0, V5 0, V6 0)." in approval["summary"]
    assert validation["counts"]["valid"] == 4 and validation["invalid"] == [] and len(validation["valid"]) == 4
    assert all(t["case_id"].startswith("TC-APP-") and {c["status"] for c in t["checks"].values()} == {"PASS"} for t in validation["tests"])
    assert validation["plugin_check"]["error"] is None, "check-gate ran; its provenance gaps are recorded, not failures"
    manifest = (project_dir(project["id"]) / "docs/qe").glob("*/05-generation/manifest.json")
    assert next(manifest).read_text(encoding="utf-8").count("caseIds") == 4
    assert client.get(f"/api/runs/{run['id']}/tests.zip").status_code == 400, "before Gate 4 is approved the run state has no validation yet"
    run = approve_gate4(client, run, approval)
    response = client.get(f"/api/runs/{run['id']}/tests.zip")
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert "VALIDATION.md" in names and "tests/agentic_qe/test_tc_app_001.py" in names and not any(n.startswith("needs-review/") for n in names)
    text = zipfile.ZipFile(io.BytesIO(response.content)).read("VALIDATION.md").decode()
    assert "python -m pytest tests/agentic_qe" in text and "| tests/agentic_qe/test_tc_app_004.py | TC-APP-004 | yes |" in text


def test_without_installed_dependencies_no_test_is_valid_and_the_zip_says_how_to_fix(client, project):
    run, approval = to_gate4(client, project, with_env=False)
    validation = approval["payload"]["validation"]
    assert validation["counts"]["valid"] == 0 and validation["counts"]["V3"] == 4 and validation["valid"] == []
    assert {t["checks"]["V3"]["status"] for t in validation["tests"]} == {"NOT CHECKED"}
    assert "Validity: 0 of 4 tests valid; 4 need review (V1 0, V2b 0, V3 4, V4 0, V5 0, V6 0)." in approval["summary"]
    run = approve_gate4(client, run, approval)
    bundle = zipfile.ZipFile(io.BytesIO(client.get(f"/api/runs/{run['id']}/tests.zip").content))
    assert "needs-review/test_tc_app_001.py" in bundle.namelist() and not any(n.startswith("tests/agentic_qe/test_") for n in bundle.namelist())
    assert "Install dependencies on" in bundle.read("VALIDATION.md").decode()


def test_only_the_projects_members_can_download_the_zip(client, project):
    run, approval = to_gate4(client, project, with_env=False)
    run = approve_gate4(client, run, approval)
    stranger, _ = account(client)
    assert stranger.get(f"/api/runs/{run['id']}/tests.zip").status_code == 404
    assert TestClient(app).get(f"/api/runs/{run['id']}/tests.zip").status_code == 401


NO_ASSERT = json.loads(TESTS)["files"][0]["content"].replace("assert add(2, 3) == 5", "result = add(2, 3)")


def author_sending_back(fixed):
    """First answer: file 1 has no assertion. A rewrite request gets the fixed file when `fixed`, the same bad file when not."""
    files = json.loads(TESTS)["files"]
    bad, good = {**files[0], "content": NO_ASSERT}, files[0]
    first = json.dumps({"framework": "pytest", "files": [bad, *files[1:]]})
    rewrite = json.dumps({"framework": "pytest", "files": [good if fixed else bad]})
    return lambda text: rewrite if "Rewrite only this generated test file" in text else first


def test_a_failed_check_goes_back_to_the_author_once_and_a_fixed_test_is_valid(client, project):
    run, approval = to_gate4(client, project, True, author_sending_back(fixed=True))
    validation = approval["payload"]["validation"]
    assert validation["counts"]["valid"] == 4 and validation["invalid"] == []
    sent_back = [e for e in engine.events(run["id"]) if "failed the validity checks" in e["message"]]
    assert len(sent_back) == 1 and "tests/agentic_qe/test_tc_app_001.py" in json.dumps(sent_back[0])


def test_a_test_still_failing_after_one_round_is_invalid_and_ships_in_needs_review(client, project):
    run, approval = to_gate4(client, project, True, author_sending_back(fixed=False))
    validation = approval["payload"]["validation"]
    assert (validation["counts"]["valid"], validation["counts"]["V5"]) == (3, 1)
    assert validation["invalid"] == ["tests/agentic_qe/test_tc_app_001.py"]
    bad = next(t for t in validation["tests"] if not t["valid"])
    assert bad["checks"]["V5"]["status"] == "FAIL" and "no assertion" in bad["checks"]["V5"]["message"]
    assert "Validity: 3 of 4 tests valid; 1 need review (V1 0, V2b 0, V3 0, V4 0, V5 1, V6 0)." in approval["summary"]
    names = zipfile.ZipFile(io.BytesIO(client.get(f"/api/runs/{approve_gate4(client, run, approval)['id']}/tests.zip").content)).namelist()
    assert "needs-review/test_tc_app_001.py" in names and "tests/agentic_qe/test_tc_app_002.py" in names
