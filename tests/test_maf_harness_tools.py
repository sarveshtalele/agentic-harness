"""Harness sandbox and scan tools on a real uploaded repository: real pytest in the sandbox copy, real analyzers,
honest refusal without a repository, and the thread's MAF todos over the API."""
from __future__ import annotations

import io
import json
import os
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.maf import llm
from backend.maf.tools import run_tests, sandbox_status, scan_repository
from tests.scripted_client import ScriptedClient

NEEDLE = "You are the Agentic QE Platform project harness"
REPO = {
    "calc.py": "def add(a, b):\n    return a + b\n",
    "settings.py": 'AWS_KEY = "AKIA' + "ABCDEFGHIJKLMNOP" + '"\n',
    "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\ndef test_add_wrong():\n    assert add(2, 2) == 5\n",
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


def _project(client, with_repo: bool) -> dict:
    project = client.post("/api/projects", json={"name": "Harness tools", "description": "sandbox tests"}).json()
    if with_repo:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as bundle:
            for name, body in REPO.items():
                bundle.writestr(name, body)
        assert client.post(f"/api/projects/{project['id']}/repo/zip", files={"file": ("code.zip", buffer.getvalue(), "application/zip")}).status_code == 200
    return project


@pytest.mark.asyncio
async def test_run_tests_runs_the_real_suite_in_the_sandbox(client):
    pid = _project(client, True)["id"]
    out = json.loads(await run_tests.build(pid, "thr", None).func(target="."))
    result = out["results"][0]
    assert result["runner"] == "pytest" and result["total"] == 2 and result["passed"] == 1 and result["failed"] == 1
    assert result["verdict"] == "FAIL" and "test_add_wrong" in result["failures"][0]["test"]


@pytest.mark.asyncio
async def test_scan_finds_the_planted_secret_and_saves_nothing(client):
    pid = _project(client, True)["id"]
    out = json.loads(await scan_repository.build(pid, "thr", None).func())
    assert out["status"] == "Analyzed" and any(f["rule"] == "SEC001" and f["file"] == "settings.py" for f in out["findings"])
    assert client.get(f"/api/projects/{pid}/findings").json() == []  # read-only: nothing saved


@pytest.mark.asyncio
async def test_without_a_repository_every_tool_says_so(client):
    pid = _project(client, False)["id"]
    assert json.loads(await run_tests.build(pid, "thr", None).func(target="."))["verdict"] == "INCONCLUSIVE"
    assert json.loads(await scan_repository.build(pid, "thr", None).func())["status"] == "NotScanned"
    assert json.loads(sandbox_status.build(pid, "thr", None).func())["repository"] is False


@pytest.mark.asyncio
async def test_sandbox_status_reports_the_real_commit(client):
    pid = _project(client, True)["id"]
    status = json.loads(sandbox_status.build(pid, "thr", None).func())
    assert status["repository"] is True and len(status["commit"]) >= 7 and "sandbox_ready" not in status


def test_harness_uses_scan_tool_and_todos_show_over_the_api(client):
    pid = _project(client, True)["id"]
    calls = {"n": 0}

    def reply(_text):
        calls["n"] += 1
        return {1: {"call": "todos_add", "args": {"todos": [{"title": "Scan the repository"}]}}, 2: {"call": "load_tools", "args": {"names": ["scan_repository"]}},  # plan M4: found and loaded first
                3: {"call": "scan_repository", "args": {}}}.get(calls["n"], "Found one secret.")

    llm.set_client_override(ScriptedClient([(NEEDLE, reply)]))
    thread = client.post(f"/api/projects/{pid}/chats", json={"agent": "harness"}).json()
    body = {"threadId": thread["id"], "runId": "r1", "messages": [{"id": "m1", "role": "user", "content": "Scan it"}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with client.stream("POST", "/agui/harness", json=body) as response:
        text = "".join(response.iter_text())
    assert "RUN_FINISHED" in text and "SEC001" in text  # the real scan result reached the model and the stream
    todos = client.get(f"/api/chats/{thread['id']}/todos").json()["todos"]
    assert [t["title"] for t in todos] == ["Scan the repository"] and todos[0]["done"] is False
