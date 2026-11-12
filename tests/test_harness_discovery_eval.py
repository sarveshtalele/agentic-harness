"""Live: the harness discovery eval (docs/PHASE2_PLAN.md section 8, step 1) on the real model and the real harness.

Each task in evals/harness/discovery.json runs in a fresh project holding the fixture repository, in its own chat thread,
with every approval card approved. Tool calls, results and the answer are recorded; `backend.maf.evals.discovery` scores
them. Results go to docs/evidence/runs/<date>-discovery-<label>/ (label from DISCOVERY_LABEL, default "baseline").
Run it with the model settings from your local store: `python scripts/dev.py live tests/test_harness_discovery_eval.py`.
A rate-limited model (HTTP 429) is retried on a fresh thread after a pause; a task that never got a model answer is
reported as not run, never as a failure of the harness.
"""
from __future__ import annotations

import io
import json
import os
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.config import ROOT, sandbox_dir
from backend.maf.evals.discovery import aggregate, score

pytestmark = pytest.mark.live
SPEC = json.loads((ROOT / "evals" / "harness" / "discovery.json").read_text(encoding="utf-8"))
LABEL = os.environ.get("DISCOVERY_LABEL", "baseline")
ONLY = {t for t in os.environ.get("DISCOVERY_ONLY", "").split(",") if t}
OUT = ROOT / "docs" / "evidence" / "runs" / f"{time.strftime('%Y-%m-%d')}-discovery-{LABEL}"
RETRIES, PAUSE = 4, 60


def _project(client, task_id: str) -> str:
    project = client.post("/api/projects", json={"name": f"eval {task_id}", "description": "discovery eval fixture"}).json()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for path, body in SPEC["repo"].items():
            bundle.writestr(path, body)
    assert client.post(f"/api/projects/{project['id']}/repo/zip", files={"file": ("shop.zip", buffer.getvalue(), "application/zip")}).status_code == 200
    return project["id"]


def _send(client, thread_id: str, text: str | None, run: str, resume=None) -> list[dict]:
    body = {"threadId": thread_id, "runId": run, "messages": [{"id": f"m_{run}", "role": "user", "content": text}] if text else [],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    if resume:
        body["resume"] = resume
    with client.stream("POST", "/agui/harness", json=body, timeout=1800) as response:
        raw = "".join(response.iter_text())
    return [json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")]


def _run(client, project_id: str, prompt: str) -> tuple[list[dict], str, str]:
    """(calls, answer, error) for one task, approving every card."""
    thread = client.post(f"/api/projects/{project_id}/chats", json={"agent": "harness"}).json()
    calls: dict[str, dict] = {}
    order: list[str] = []
    error = ""
    events, n = _send(client, thread["id"], prompt, "r0"), 0
    while True:
        for e in events:
            if e["type"] == "TOOL_CALL_START":
                calls[e["toolCallId"]] = {"name": e["toolCallName"], "args": "", "result": ""}
                order.append(e["toolCallId"])
            elif e["type"] == "TOOL_CALL_ARGS" and e["toolCallId"] in calls:
                calls[e["toolCallId"]]["args"] += e.get("delta", "")
            elif e["type"] == "TOOL_CALL_RESULT" and e.get("toolCallId") in calls:
                calls[e["toolCallId"]]["result"] = str(e.get("content"))[:4000]
            elif e["type"] == "RUN_ERROR":
                error = str(e.get("message"))
        last = events[-1] if events else {}
        interrupts = (last.get("outcome") or {}).get("interrupts") if last.get("type") == "RUN_FINISHED" else None
        if not interrupts or n >= 60:
            break
        n += 1
        events = _send(client, thread["id"], None, f"r{n}", resume=[{"interruptId": i["id"], "status": "resolved", "payload": {"approved": True}} for i in interrupts])
    messages = client.get(f"/api/chats/{thread['id']}").json()["messages"]
    answer = messages[-1]["content"] if messages and messages[-1]["role"] == "assistant" else ""
    _run.last_messages = [{"role": m["role"], "content": str(m["content"])[:1500]} for m in messages]  # the whole thread, for review
    return [calls[c] for c in order], answer, error


def test_discovery_eval():
    assert os.environ.get("DEFAULT_MODEL") and os.environ.get("OPENAI_API_KEY"), "the discovery eval needs a real model"
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = [t for t in SPEC["tasks"] if not ONLY or t["id"] in ONLY]
    results, not_run = [], []
    with TestClient(app) as client, (OUT / "transcript.jsonl").open("w", encoding="utf-8") as log:
        assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        for task in tasks:
            for attempt in range(RETRIES):
                project_id = _project(client, task["id"])
                started = time.monotonic()
                calls, answer, error = _run(client, project_id, task["prompt"])
                rate_limited = "429" in error or "busy" in error.lower()
                log.write(json.dumps({"task": task["id"], "attempt": attempt, "seconds": round(time.monotonic() - started), "error": error,
                                      "calls": calls, "answer": answer[:3000], "thread": getattr(_run, "last_messages", [])}) + "\n")
                log.flush()
                if not (rate_limited and not calls):
                    break
                time.sleep(PAUSE * (attempt + 1))
            if error and not calls and not answer:
                not_run.append({"id": task["id"], "error": error[:300]})
                continue
            results.append({**score(task, calls, answer, sandbox_dir(project_id)), "seconds": round(time.monotonic() - started), "error": error[:300]})
            print(task["id"], "passed" if results[-1]["passed"] else f"failed: {results[-1]['why']}", flush=True)
    summary = {"label": LABEL, "model": os.environ.get("DEFAULT_MODEL"), "date": time.strftime("%Y-%m-%d %H:%M"), **aggregate(results),
               "not_run": not_run, "by_kind": _by_kind(results)}
    (OUT / "results.json").write_text(json.dumps({"summary": summary, "tasks": results}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1), flush=True)
    assert results, f"no task got a model answer: {not_run}"
    assert len(results) + len(not_run) == len(tasks)


def _by_kind(results: list[dict]) -> dict:
    kinds: dict[str, list[dict]] = {}
    for r in results:
        kinds.setdefault(r["kind"], []).append(r)
    return {k: f"{sum(r['passed'] for r in v)}/{len(v)}" for k, v in sorted(kinds.items())}
