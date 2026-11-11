"""Chat limits, admin work, usage export, secrets and migration 009."""

import asyncio
import json

from backend import config
from backend.core import auth, models
from backend.db import db, rows
from backend.maf import llm

from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import USER_PASSWORD
from tests.helpers_db import dump as dump_tables, fresh_database
from tests.helpers_models import account, at, spend, start_ba


def test_chat_obeys_the_limits_and_says_when_they_reset(client, monkeypatch):
    user, mine, project = account(client)
    client.patch(f"/api/users/{user['id']}", json={"limits": {"day": 100}})
    at(monkeypatch, "2026-11-04T10:00:00+00:00")
    spend(user["id"], 100, created_at="2026-11-04T09:00:00+00:00")
    llm.set_client_override(ScriptedClient([("You are the Agentic QE Platform project copilot", "Hello")]))
    thread = mine.post(f"/api/projects/{project['id']}/chats", json={"agent": "project-copilot"}).json()
    body = {"threadId": thread["id"], "runId": "r1", "messages": [{"id": "m1", "role": "user", "content": "hi"}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with mine.stream("POST", "/agui/project-copilot", json=body) as response:
        text = "".join(response.iter_text())
    assert "RUN_ERROR" in text and "AQE-ALLOW-002" in text and "resets at" in text and "Hello" not in text
    at(monkeypatch, "2026-11-04T19:00:00+00:00")
    with mine.stream("POST", "/agui/project-copilot", json=body) as response:
        text = "".join(response.iter_text())
    assert "Hello" in text and "RUN_ERROR" not in text
    with db() as con:
        last = rows(con.execute("SELECT model, user_id, source FROM agent_calls WHERE project_id=? ORDER BY id DESC LIMIT 1", (project["id"],)))[0]
    assert last == {"model": "m-a", "user_id": user["id"], "source": "chat"}


def test_admin_work_and_evals_never_count_against_a_user(client):
    from backend.maf import evals

    user, mine, project = account(client)
    llm.set_client_override(ScriptedClient([*case_rules(), ("You are an independent reviewer", "ok")]))
    evals._sandbox()

    async def as_admin():
        from backend.maf.runtime import AgentCall

        auth.current_user.set({"id": "admin", "role": "admin"})
        return await AgentCall(None, evals.EVAL_PROJECT, "confidence-reviewer", source="eval").text("x")

    before = mine.get("/api/auth/me").json()["tokens_used"]
    asyncio.run(as_admin())
    with db() as con:
        call = rows(con.execute("SELECT user_id FROM agent_calls WHERE source='eval' ORDER BY id DESC LIMIT 1"))[0]
    assert call["user_id"] == "admin" and mine.get("/api/auth/me").json()["tokens_used"] == before
    assert client.get("/api/auth/me").json()["usage"] is None, "the admin has no limits"


# ---- usage report ----------------------------------------------------------------------------

def test_usage_is_admin_only_exports_csv_and_an_empty_database_gives_empty_lists(client, tmp_path, monkeypatch):
    user, mine, project = account(client, ("m-usage-a", "m-usage-b"))
    spend(user["id"], 40, model="m-usage-a")
    spend(user["id"], 60, model="m-usage-b")
    assert mine.get("/api/usage").status_code == 403 and mine.get("/api/usage?format=csv").status_code == 403
    report = client.get("/api/usage").json()
    assert {"name": "m-usage-a", "tokens": 40} in report["by_model"] and {"name": "m-usage-b", "tokens": 60} in report["by_model"] and report["timezone"] == "Asia/Kolkata"
    assert any(r["name"] == mine.get("/api/auth/me").json()["username"] for r in report["by_user"]), "the admin sees login names"
    csv_text = client.get("/api/usage?format=csv").text
    assert csv_text.splitlines()[0] == "day,user,model,agent,calls,tokens_in,tokens_out" and "m-usage-b" in csv_text
    with fresh_database():
        assert models.usage_rows(30) == []


def test_user_names_in_usage_follow_the_existing_rule(client):
    user, mine, project = account(client)
    spend(user["id"], 5)
    assert mine.get("/api/usage").status_code == 403, "no other route shows login names to a user"
    assert "username" not in json.dumps(mine.get("/api/settings/models").json())


# ---- secrets ----------------------------------------------------------------------------------

def test_a_secret_and_a_password_in_a_reply_or_request_reach_no_table_or_log(client, caplog):
    secret = "sk-" + "Qw7" * 12
    caplog.set_level("DEBUG")
    llm.set_client_override(ScriptedClient([("You are the Agentic QE Platform project copilot", f"Your key is {secret} and password={USER_PASSWORD}")]))
    user, mine, project = account(client)
    thread = mine.post(f"/api/projects/{project['id']}/chats", json={"agent": "project-copilot"}).json()
    body = {"threadId": thread["id"], "runId": "r1", "messages": [{"id": "m1", "role": "user", "content": f"remember {secret}"}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}
    with mine.stream("POST", "/agui/project-copilot", json=body) as response:
        streamed = "".join(response.iter_text())
    assert start_ba(mine, project, model="m-other-unlisted").status_code == 403
    stored = dump_tables()
    username = mine.get("/api/auth/me").json()["username"]
    logs = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in config.LOGS.glob("*.jsonl")) if config.LOGS.exists() else ""
    for place, text in {"table": stored, "log": caplog.text + logs, "stream": streamed}.items():
        assert secret not in text and "Qw7Qw7Qw7Qw7" not in text, f"secret reached the {place}"
    assert USER_PASSWORD not in stored + caplog.text + logs, "the password is only in a hash"
    assert username not in stored, "login names are encrypted in the users table and absent elsewhere"
    with db() as con:
        events = json.dumps(rows(con.execute("SELECT * FROM auth_events")))
    assert username not in events and USER_PASSWORD not in events, "auth events name the account id, never the login"
