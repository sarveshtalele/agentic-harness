"""Live: brainstorming on the real model (R3, plan 12.4). Run with  python scripts/dev.py live tests/test_brainstorm_live.py
A missing model is a failure, not a skip. The run goes from a slide deck and a one-line need to a signed G1."""
from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from tests.test_brainstorm_r3 import _pptx

pytestmark = pytest.mark.live


def _wait(client, run_id, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in ("waiting_approval", "completed", "failed", "rejected"):
            return run
        time.sleep(1)
    raise AssertionError(f"run stuck: {run['status']}")


def test_brainstorm_on_the_real_model_from_slides_to_a_signed_brd():
    assert os.environ.get("DEFAULT_MODEL") and os.environ.get("OPENAI_API_KEY"), "live test needs a real model in the environment"
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        project = client.post("/api/projects", json={"name": "Live brainstorm", "description": "Refunds"}).json()
        source = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("kickoff.pptx", _pptx())}).json()
        run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "brainstorm", "input": {
            "need": "Customers can refund part of an order within 30 days", "source_ids": [source["id"]], "template_id": "builtin_brd"}}).json()
        seen = []
        for _ in range(16):
            current = _wait(client, run["id"])
            if current["status"] != "waiting_approval":
                break
            step = next(a for a in current["approvals"] if a["status"] == "pending")
            kind = step["payload"].get("kind") or f"gate {step['gate']}"
            seen.append(kind)
            print(f"\n[{kind}] {step['title']}: {step['payload'].get('question') or step['summary']}")
            if kind == "brainstorm_question":
                assert step["payload"]["question"].strip() and step["payload"]["why"].strip()
                body = {"action": "answer", "answer": "Finance approves refunds above 500 EUR; after 30 days refunds are refused"} \
                    if seen.count(kind) == 1 else {"action": "propose"}
            elif kind == "builder_check":
                body = {"answers": ["Use your proposal"] * len(step["payload"]["questions"])}
            else:
                body = {}
            assert client.post(f"/api/approvals/{step['id']}/decide", json={"approved": True, **body}).status_code == 200
        final = _wait(client, run["id"])
        assert final["status"] == "completed", final.get("error")
        assert "brainstorm_question" in seen and "brainstorm_approaches" in seen and "gate 1" in seen
        print(f"\nsteps: {seen}")
