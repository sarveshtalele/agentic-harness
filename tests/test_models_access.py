"""Which models a user may use and the order a call picks one."""

import asyncio
import json

import pytest

from backend.core import auth, models
from backend.db import db, rows
from backend.maf import llm

from tests.scripted_client import ScriptedClient
from tests.helpers_api import make_user, pending, rules, unique, wait_run
from tests.helpers_models import account, As, listed, start_ba


def used_models(run_id):
    with db() as con:
        return {r["agent"]: r["model"] for r in rows(con.execute("SELECT DISTINCT agent, model FROM agent_calls WHERE run_id=?", (run_id,)))}


def events_of(user_id):
    with db() as con:
        return [r["event"] for r in rows(con.execute("SELECT event FROM auth_events WHERE subject=?", (user_id,)))]


def ba_through_intake(c, run_id, statuses=("waiting_approval", "completed", "failed")):
    """Intake asks for a person's approval before any agent works, so the model calls start after it."""
    run = wait_run(c, run_id)
    c.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    return wait_run(c, run_id, statuses)


# ---- the list, ticks, and refusals ------------------------------------------------------

def test_a_model_the_user_was_not_given_is_refused_by_run_chat_and_agent_and_logged_by_account_id(client):
    llm.set_client_override(ScriptedClient(rules()))
    user, mine, project = account(client, ("m-a",))
    listed("m-other")
    refused = start_ba(mine, project, model="m-other")
    assert refused.status_code == 403 and refused.json()["code"] == "AQE-ALLOW-001" and "m-other" in refused.json()["message"]
    thread = mine.post(f"/api/projects/{project['id']}/chats", json={"agent": "project-copilot"}).json()
    assert mine.patch(f"/api/chats/{thread['id']}", json={"model": "m-other"}).status_code == 403, "the chat picker is checked on the server too"
    assert mine.post(f"/api/projects/{project['id']}/chats", json={"agent": "project-copilot", "model": "m-other"}).status_code == 403
    assert events_of(user["id"]).count("model.refused:m-other") == 3 and "qa-admin" not in json.dumps(events_of(user["id"]))
    assert mine.patch(f"/api/chats/{thread['id']}", json={"model": "m-a"}).json()["model"] == "m-a"
    # the admin can still point an agent at a model the user lacks, and then that user's work with that agent is refused, not quietly switched
    assert client.put("/api/agents/business-analyst/settings", json={"enabled": True, "max_tokens": None, "reason": "test", "model": "m-other"}).status_code == 200
    run = ba_through_intake(mine, start_ba(mine, project).json()["id"])
    assert run["status"] == "failed" and run["failure"]["code"] == "AQE-ALLOW-001" and "m-other" in run["failure"]["message"]
    client.put("/api/agents/business-analyst/settings", json={"enabled": True, "max_tokens": None, "reason": "", "model": ""})


def test_a_user_with_no_model_ticked_cannot_run_or_chat(client):
    llm.set_client_override(ScriptedClient(rules()))
    name = unique()
    make_user(client, name, models=[], features=["ba"])  # BA Studio, so the model check is what refuses (R2)
    mine = As(client, name)
    project = mine.post("/api/projects", json={"name": "None", "description": ""}).json()
    refused = start_ba(mine, project)
    assert refused.status_code == 403 and refused.json()["code"] == "AQE-ALLOW-001" and "No models are allowed" in refused.json()["message"]
    with pytest.raises(auth.AllowanceError, match="No models are allowed"):
        asyncio.run(_text(project["id"], "business-analyst", mine.get("/api/auth/me").json()["id"]))


async def _text(project_id, agent, user_id):
    from backend.maf.runtime import AgentCall

    auth.current_user.set({"id": user_id, "role": "user"})
    call = AgentCall(None, project_id, agent)
    return await call.text("hello")


def test_the_default_must_be_one_of_the_ticked_models_and_a_blank_one_becomes_the_first(client):
    listed("m-a", "m-b")
    name = unique()
    user = make_user(client, name, models=["m-a", "m-b"], model="m-b")
    assert user["models"] == ["m-a", "m-b"] and user["model"] == "m-b"
    assert client.patch(f"/api/users/{user['id']}", json={"model": "m-zzz"}).status_code == 400
    assert client.patch(f"/api/users/{user['id']}", json={"models": ["m-a"]}).json()["model"] == "m-a", "unticking the default moves it to a ticked model"
    assert client.patch(f"/api/users/{user['id']}", json={"models": ["m-a"], "model": "m-b"}).status_code == 400
    assert client.patch(f"/api/users/{user['id']}", json={"models": ["not-listed"]}).status_code == 400


def test_switching_a_model_off_removes_it_for_everyone_and_the_wildcard_is_never_a_model(client):
    user, mine, project = account(client, ("m-a", "m-off"))
    assert mine.get("/api/settings/models").json()["models"] == ["m-a", "m-off"]
    client.patch("/api/models", json={"name": "m-off", "enabled": False})
    assert mine.get("/api/settings/models").json()["models"] == ["m-a"]
    assert start_ba(mine, project, model="m-off").status_code == 403
    assert client.post("/api/models", json={"name": "*"}).status_code == 400
    assert client.patch("/api/models", json={"name": "m-off", "is_default": True}).status_code == 400, "a switched-off model cannot be the default"
    assert mine.get("/api/models").status_code == 403 and mine.post("/api/models", json={"name": "x"}).status_code == 403


def test_load_from_proxy_drops_the_wildcard_enables_nothing_and_test_reports_an_empty_answer(client, monkeypatch):
    payloads = {"/models": {"data": [{"id": "*"}, {"id": "openai/*"}, {"id": "proxy-a"}, {"id": "proxy-b"}, {"id": "proxy-a"}]},
                "/chat/completions": {"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {"prompt_tokens": 5, "completion_tokens": 200}}}

    class Reply:
        status_code, text = 200, ""

        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    class Fake:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url, **_):
            return Reply(payloads["/models"])

        async def post(self, url, **_):
            return Reply(payloads["/chat/completions"])

    monkeypatch.setattr(llm.httpx, "AsyncClient", Fake)
    monkeypatch.setattr(llm, "current", lambda: {"base_url": "https://proxy.test/v1", "model": "proxy-a", "api_key": "key-123456789"})
    loaded = client.post("/api/models/load").json()
    assert loaded["listed"] == 2 and sorted(loaded["added"]) == ["proxy-a", "proxy-b"]
    by_name = {m["name"]: m for m in loaded["models"]}
    assert "*" not in by_name and not by_name["proxy-a"]["enabled"] and not by_name["proxy-b"]["enabled"], "listing does not mean it works"
    tested = client.post("/api/settings/llm/test", json={"model": "proxy-a"}).json()
    assert tested["ok"] is False and "answered with nothing" in tested["error"] and tested["tokens"] == 205
    payloads["/chat/completions"] = {"choices": [{"message": {"content": "PONG"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
    assert client.post("/api/settings/llm/test", json={"model": "proxy-a"}).json()["ok"] is True


# ---- which model a call uses ---------------------------------------------------------------

def test_model_order_is_run_then_agent_then_user_then_system_and_each_call_records_it(client):
    llm.set_client_override(ScriptedClient(rules()))
    listed("m-run", "m-agent", "m-user", "m-system")
    models.update("m-system", {"is_default": True})
    name = unique()
    user = make_user(client, name, models=["m-run", "m-agent", "m-user"], model="m-user", features=["ba"])
    mine = As(client, name)
    assert client.put("/api/agents/business-analyst/settings", json={"enabled": True, "max_tokens": None, "reason": "cheaper", "model": "m-agent"}).status_code == 200

    def fresh():
        return mine.post("/api/projects", json={"name": "Order", "description": ""}).json()

    first = start_ba(mine, fresh(), model="m-run").json()
    ba_through_intake(mine, first["id"])
    assert used_models(first["id"]) == {"business-analyst": "m-run", "confidence-reviewer": "m-run"}, "the run's choice beats the agent's model"
    second = start_ba(mine, fresh()).json()
    ba_through_intake(mine, second["id"])
    assert used_models(second["id"]) == {"business-analyst": "m-agent", "confidence-reviewer": "m-user"}, "the agent's model, else the user's default"
    third = start_ba(client, client.post("/api/projects", json={"name": "Admin", "description": ""}).json()).json()
    ba_through_intake(client, third["id"])
    assert used_models(third["id"]) == {"business-analyst": "m-agent", "confidence-reviewer": "m-system"}, "the admin has no default of their own, so the system default applies"
    with db() as con:
        owners = {r["user_id"] for r in rows(con.execute("SELECT DISTINCT user_id FROM agent_calls WHERE run_id IN (?,?)", (first["id"], second["id"])))}
    assert owners == {user["id"]}
    client.put("/api/agents/business-analyst/settings", json={"enabled": True, "max_tokens": None, "reason": "", "model": ""})


def test_an_agent_cannot_be_pointed_at_a_model_that_is_not_enabled(client):
    models.add("m-off-agent")
    refused = client.put("/api/agents/business-analyst/settings", json={"enabled": True, "max_tokens": None, "reason": "x", "model": "m-off-agent"})
    assert refused.status_code == 400 and "enabled" in refused.json()["message"]
