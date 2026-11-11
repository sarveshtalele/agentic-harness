"""Live: harness user stories (docs/HARNESS_USER_STORIES.md) on the real model, real repository and real tools.

Run with OPENAI_BASE_URL, OPENAI_API_KEY, DEFAULT_MODEL set, and ATLAS_SKILLS_DIR pointing at a scratch copy of skills/
(Skill Studio writes there). Each test records what really happened in data/evidence/harness-stories.json.
"""
from __future__ import annotations

import io
import json
import os
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.config import ROOT
from backend.db import db

pytestmark = pytest.mark.live
OUT = ROOT / "data" / "evidence" / "harness-stories.json"
REPO = {
    "calc.py": "import subprocess\n\n\ndef add(a, b):\n    return a + b\n\n\ndef backup(path):\n    return subprocess.call('tar -czf b.tgz ' + path, shell=True)\n",
    "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    "requirements.txt": "pytest\n",
}


def record(story: str, outcome: dict) -> None:
    found = json.loads(OUT.read_text()) if OUT.exists() else {}
    found[story] = outcome
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(found, indent=2))


@pytest.fixture(scope="module")
def ctx():
    assert os.environ.get("DEFAULT_MODEL") and os.environ.get("OPENAI_API_KEY"), "live stories need a real model"
    assert os.environ.get("ATLAS_SKILLS_DIR"), "point ATLAS_SKILLS_DIR at a scratch copy; Skill Studio writes there"
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        project = client.post("/api/projects", json={"name": "Calculator", "description": "Small Python calculator with a backup helper"}).json()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as bundle:
            for name, body in REPO.items():
                bundle.writestr(name, body)
        assert client.post(f"/api/projects/{project['id']}/repo/zip", files={"file": ("calc.zip", buffer.getvalue(), "application/zip")}).status_code == 200
        yield client, project["id"]


def turn(client, pid: str, text: str) -> tuple[str, dict, list[str]]:
    thread = client.post(f"/api/projects/{pid}/chats", json={"agent": "harness"}).json()
    body = {"threadId": thread["id"], "runId": "r", "messages": [{"id": "m1", "role": "user", "content": text}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with client.stream("POST", "/agui/harness", json=body, timeout=600) as response:
        stream = "".join(response.iter_text())
    reply = client.get(f"/api/chats/{thread['id']}").json()["messages"][-1]["content"]
    with db() as con:
        tools = [r[0] for r in con.execute("SELECT tool FROM tool_calls WHERE project_id=? AND agent='harness' AND created_at >= ? ORDER BY id",
                                           (pid, thread["created_at"]))]
    return stream, {"thread": thread["id"], "reply": reply[:1500], "tools": tools}, tools


def test_hs01_hs03_hs13_plan_then_scan(ctx):
    client, pid = ctx
    stream, out, tools = turn(client, pid, "Add one todo per step, then scan the repository and tell me the number of findings with file and line.")
    todos = client.get(f"/api/chats/{out['thread']}/todos").json()["todos"]
    record("HS-01/HS-03/HS-13", {**out, "todos": todos})
    assert "RUN_FINISHED" in stream and todos and "scan_repository" in tools and "calc.py" in out["reply"]


def test_hs04_run_tests(ctx):
    client, pid = ctx
    stream, out, tools = turn(client, pid, "Run the repository's tests with run_tests and report the exact passed and failed counts.")
    record("HS-04", out)
    assert "run_tests" in tools and "1" in out["reply"]


def test_hs05_qe_method_skill(ctx):
    client, pid = ctx
    stream, out, tools = turn(client, pid, "Load the planning-tests skill and use it to outline a test plan for calc.py in five bullet points.")
    record("HS-05", out)
    assert "load_skill" in tools


def test_hs02_brd_through_the_ba_workflow(ctx):
    client, pid = ctx
    stream, out, tools = turn(client, pid, "Start the ba workflow with this brief: users need to back up a folder safely; paths must be validated; "
                                           "every backup is logged. Title it Backup BRD. Do not approve anything.")
    with db() as con:
        runs = [dict(r) for r in con.execute("SELECT workflow, status FROM runs WHERE project_id=? AND workflow='ba'", (pid,))]
    record("HS-02", {**out, "runs": runs})
    assert "start_workflow" in tools and runs


def test_hs07_qe_run_starts(ctx):
    client, pid = ctx
    stream, out, tools = turn(client, pid, "Start the qe workflow for this project. Do not approve anything.")
    with db() as con:
        runs = [dict(r) for r in con.execute("SELECT workflow, status FROM runs WHERE project_id=? AND workflow='qe'", (pid,))]
    record("HS-07", {**out, "runs": runs})
    assert "start_workflow" in tools and runs


def test_hs08_hs09_studio_creates_and_evaluates_a_skill(ctx):
    """The rebuilt Studio (plan M3): a plan from the model, approved by a person, generated, checked, and evaluated with and without the skill."""
    client, pid = ctx
    brief = "Check Python subprocess calls for shell=True and string-built commands, and report file and line."
    source = {"type": "text", "text": REPO["calc.py"] + "\nRule: a subprocess call with shell=True or a command built by string concatenation is a finding, reported as file:line."}
    plan = client.post("/api/skill-studio/plans", json={"project_id": pid, "kind": "instructions", "source": source, "request": brief})
    approved = client.post(f"/api/skill-studio/plans/{plan.json()['id']}/approve") if plan.status_code == 201 else None
    generated = client.post(f"/api/skill-studio/plans/{plan.json()['id']}/generate") if approved is not None and approved.status_code == 200 else None
    evaluate = client.post(f"/api/skill-studio/plans/{plan.json()['id']}/evaluate") if generated is not None and generated.status_code == 200 else None
    record("HS-08/HS-09", {"plan_status": plan.status_code, "plan": plan.json(), "generate_status": generated.status_code if generated else None,
                           "checks": generated.json().get("checks") if generated else None, "evaluate_status": evaluate.status_code if evaluate else None,
                           "evaluation": evaluate.json() if evaluate else None})
    assert plan.status_code == 201 and generated is not None and generated.status_code == 200, plan.text
    assert generated.json()["summary"]["all_passed"], generated.json()["checks"]
    assert evaluate is not None and evaluate.status_code == 200, evaluate.text if evaluate else "not evaluated"
    assert set(evaluate.json()["metrics"]) == {"assertion_pass_rate_with_skill", "assertion_pass_rate_without_skill", "skill_uplift"}
