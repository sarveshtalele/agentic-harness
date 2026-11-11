"""Secret redaction, error shape and failure records."""

import json

from fastapi.testclient import TestClient

from backend import config
from backend.app import app

from backend.db import db, rows
from backend.maf import llm
from backend.maf.runtime import AgentCall

from tests.scripted_client import ScriptedClient
from tests.helpers_errors import Designer, run_to_design


SECRET = "sk-" + "Zq9" * 12


def test_a_secret_in_a_rejected_reply_reaches_no_file_log_table_or_response(client, project, caplog):
    caplog.set_level("DEBUG")
    broken = '{"cases": [{"id": "A", "note": "key ' + SECRET + '", "x": '
    run = run_to_design(client, project, Designer(broken=broken))
    assert run["status"] == "failed"
    failure = run["failure"]
    saved = config.RUNS / run["id"] / failure["reply_file"]
    assert saved.is_file() and "sk-Z" in saved.read_text(encoding="utf-8"), "the reply is saved, with the secret masked"
    with db() as con:
        tables = {t["name"] for t in rows(con.execute("SELECT name FROM sqlite_master WHERE type='table'"))}
        stored = json.dumps({t: rows(con.execute(f"SELECT * FROM {t}")) for t in sorted(tables - {"users", "sessions"})}, default=str)
    files = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in (config.RUNS / run["id"]).rglob("*") if p.is_file())
    api = client.get(f"/api/runs/{run['id']}").text
    for place, text in {"table": stored, "file": files, "api": api, "log": caplog.text}.items():
        assert SECRET not in text and "Zq9Zq9Zq9Zq9" not in text, f"secret reached the {place}"
    assert failure["stack"] and "Traceback" in failure["stack"]


def test_every_error_has_the_same_shape_and_a_request_id(client, project, monkeypatch, caplog):
    import os

    from backend.maf import engine

    caplog.set_level("DEBUG")
    missing = client.get("/api/runs/run_missing")
    body = missing.json()
    assert missing.status_code == 404 and set(body) == {"code", "message", "action", "error_id", "detail"} and body["detail"] == body["message"] and body["error_id"].startswith("err_")
    assert missing.headers["X-Request-Id"].startswith("req_")
    invalid = client.post("/api/projects", json={"description": "no name"})
    assert invalid.status_code == 422 and isinstance(invalid.json()["detail"], list) and invalid.json()["message"] and invalid.headers["X-Request-Id"]
    anonymous = TestClient(app).get("/api/projects")
    assert anonymous.status_code == 401 and anonymous.json()["detail"] == "Sign in first" and anonymous.headers["X-Request-Id"]
    assert client.get("/api/health").headers["X-Request-Id"], "success responses carry it too"
    assert client.get("/api/health").headers["X-Request-Id"] != client.get("/api/health").headers["X-Request-Id"]
    llm.set_client_override(None)
    monkeypatch.setattr(llm, "current", lambda: {"base_url": "", "model": "", "api_key": ""})  # other tests may have saved a model in settings
    typed = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"})
    assert typed.status_code == 412 and typed.json()["code"] == "AQE-MODEL-006" and "Settings" in typed.json()["action"]
    # a bug becomes a 500 with an id, and the secret in its message goes nowhere
    def boom(_run_id):
        raise ZeroDivisionError(f"broke with {SECRET}")

    monkeypatch.setattr(engine, "get", boom)
    with TestClient(app, raise_server_exceptions=False) as quiet:
        quiet.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]})
        crashed = quiet.get("/api/runs/run_any")
    assert crashed.status_code == 500 and crashed.json()["code"] == "AQE-INT-001" and crashed.json()["error_id"] and crashed.headers["X-Request-Id"]
    assert SECRET not in crashed.text and SECRET not in caplog.text and crashed.json()["error_id"] in caplog.text


def test_failure_records_carry_what_is_needed_to_debug_them(client, project):
    run = run_to_design(client, project, Designer())
    failure = run["failure"]
    assert failure["agent"] == "test-design-architect" and failure["prompt_ref"].startswith("test-design-architect@v") and failure["attempt"] == 2
    assert failure["parse_pos"] is None and failure["technical"] and failure["reply_file"].startswith("failures/err_")
    assert (config.RUNS / run["id"] / failure["reply_file"]).read_text(encoding="utf-8") == "I cannot produce that."
    assert any(e["type"] == "error" and failure["code"] in e["message"] and e["data"]["error_id"] == failure["id"] for e in __import__("backend.maf.engine", fromlist=["x"]).events(run["id"])), "the live log carries the code"


def test_model_calls_carry_the_no_cache_control(client, project, monkeypatch):
    llm.set_client_override(ScriptedClient([("x", "ok")]))
    assert AgentCall(None, project["id"], "confidence-reviewer").agent.default_options["extra_body"] == {"cache": {"no-cache": True}}
    monkeypatch.setattr("backend.maf.runtime.factory.MODEL_NO_CACHE", False)
    assert "extra_body" not in AgentCall(None, project["id"], "confidence-reviewer").agent.default_options


def test_a_broken_reply_is_retried_with_the_text_that_broke(client):
    """A real failure: the model wrote "/api/nav?q=" + ' ' * 81 inside a JSON string list."""
    import asyncio

    from pydantic import BaseModel

    from backend.maf.runtime import AgentCall, format_rule
    from tests.scripted_client import ScriptedClient

    class Steps(BaseModel):
        steps: list[str]

    assert "never code or an expression" in format_rule(Steps)
    project = client.post("/api/projects", json={"name": "Broken reply"}).json()
    replies = iter(["""{"steps": ["GET /api/nav?q=" + ' ' * 81]}""", '{"steps": ["GET /api/nav with a query of 81 spaces"]}'])
    scripted = ScriptedClient([("Steps", lambda _: next(replies)), ("rejected", lambda _: next(replies))])
    llm.set_client_override(scripted)
    result = asyncio.run(AgentCall(None, project["id"], "test-design-architect").typed("Design", Steps))
    assert result.steps == ["GET /api/nav with a query of 81 spaces"]
    assert "The problem is here:" in scripted.calls[-1] and "* 81" in scripted.calls[-1]
