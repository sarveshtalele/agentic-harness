"""Shared steps for the harness execution-world and plugin tests: a project with a real git repository (uploaded as a zip,
which the platform commits), AG-UI turns, and approving an interrupt the way the chat's Approve button does."""
from __future__ import annotations

import io
import json
import zipfile

REPO = {
    "app.py": "def add(a, b):\n    return a + b\n",
    "tests/test_app.py": "from app import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
}
NEEDLE = "You are the Agentic QE Platform project harness"


def project_with_repo(client, name: str = "World shop") -> dict:
    project = client.post("/api/projects", json={"name": name, "description": "harness world"}).json()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for path, body in REPO.items():
            bundle.writestr(path, body)
    assert client.post(f"/api/projects/{project['id']}/repo/zip", files={"file": ("code.zip", buffer.getvalue(), "application/zip")}).status_code == 200
    return project


def steps(*replies):
    """Model replies in order: a dict is a tool call, a string is the final text. The last reply repeats."""
    seen = {"n": 0}

    def reply(_text):
        seen["n"] += 1
        return replies[min(seen["n"], len(replies)) - 1]

    return reply


def turn(client, thread_id: str, text: str | None, run: str, resume=None) -> list[dict]:
    body = {"threadId": thread_id, "runId": run, "messages": [{"id": f"m_{run}", "role": "user", "content": text}] if text else [],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    if resume:
        body["resume"] = resume
    with client.stream("POST", "/agui/harness", json=body) as response:
        assert response.status_code == 200
        raw = "".join(response.iter_text())
    return [json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")]


def interrupt_of(events: list[dict]) -> dict:
    finished = events[-1]
    assert finished["type"] == "RUN_FINISHED" and finished["outcome"]["type"] == "interrupt", finished
    return finished["outcome"]["interrupts"][0]


def approve(client, thread_id: str, events: list[dict], run: str, approved: bool = True) -> list[dict]:
    interrupt = interrupt_of(events)
    return turn(client, thread_id, None, run, resume=[{"interruptId": interrupt["id"], "status": "resolved", "payload": {"approved": approved}}])


def ledger_rows(project_id: str, action: str) -> list[dict]:
    from backend.db import db

    with db() as con:
        return [{**dict(r), "data": json.loads(r["data"])} for r in con.execute("SELECT actor, action, target, data FROM ledger WHERE project_id=? AND action=? ORDER BY seq", (project_id, action))]
