"""Plugin skills on MAF: the live tool check."""
import asyncio
import json

import httpx
import pytest
from agent_framework import SkillsProvider, SkillsSourceContext

from backend.core import models
from backend.maf import llm, skill_chat
from backend.maf import runtime as agents
from tests.scripted_client import ScriptedClient
from tests.helpers_api import USER_PASSWORD, client, make_user, project, sign_in, unique  # noqa: F401 - fixtures


# ---- the live tool check -------------------------------------------------------------

KEY = "sk-test-secret-key-1234567890"


@pytest.fixture
def endpoint(monkeypatch):
    monkeypatch.setattr(llm, "current", lambda: {"base_url": "http://proxy.test/v1", "model": "", "api_key": KEY})
    models.add("tc-model", enabled=True)
    seen = []

    def serve(model_behavior):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            seen.append({"auth": request.headers["authorization"], **body})
            return model_behavior(body)

        return httpx.MockTransport(handler)

    return serve, seen


def called(name, call_id="call_1"):
    return httpx.Response(200, json={"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [{"id": call_id, "type": "function", "function": {"name": name, "arguments": "{}"}}]}}]})


def said(text, finish="stop"):
    return httpx.Response(200, json={"choices": [{"finish_reason": finish, "message": {"role": "assistant", "content": text}}]})


def tool_name(body):
    return body["tools"][0]["function"]["name"]


def good_model(body):
    if body["messages"][-1]["role"] == "tool":
        return said("The code is " + json.loads(body["messages"][-1]["content"])["reference"])
    return called(tool_name(body))


def check(client, transport):
    return client.portal.call(lambda: llm.tool_check("tc-model", transport=transport))


def test_tool_check_passes_a_model_that_calls_the_tool_and_uses_its_result(client, endpoint):
    serve, seen = endpoint
    result = check(client, serve(good_model))
    assert result["status"] == "passed" and result["tools_called"] == [tool_name(seen[0])] and result["max_tokens"] == llm.TOOL_CHECK_MAX_TOKENS
    assert len(seen) == 2 and all(r["max_tokens"] == llm.TOOL_CHECK_MAX_TOKENS and len(r["tools"]) == 1 for r in seen)
    assert tool_name(seen[0]).startswith("aqe_probe_") and seen[0]["messages"][0]["content"].count(tool_name(seen[0])) == 1
    token = json.loads(seen[1]["messages"][-1]["content"])["reference"]
    assert token.startswith("AQE-") and token not in json.dumps(seen[0]), "the unique token appears only in the tool's reply"
    stored = models.get("tc-model")
    assert stored["tools_status"] == "passed" and stored["tools_checked_at"] and stored["tools_max_tokens"] == llm.TOOL_CHECK_MAX_TOKENS
    other = check(client, serve(good_model))
    assert tool_name(seen[0]) != tool_name(seen[2]), "names are unique per check"
    assert KEY not in json.dumps([result, other, stored])


@pytest.mark.parametrize("name,behavior,reason", [
    ("a tool that was never offered", lambda body: called("read_file"), "read_file"),
    ("an answer in text", lambda body: said("I only have read_file."), "It said: I only have read_file."),
    ("nothing at all", lambda body: said("", "length"), "returned nothing"),
    ("the result ignored", lambda body: said("All done.") if body["messages"][-1]["role"] == "tool" else called(tool_name(body)), "ignored its result"),
    ("an empty final reply", lambda body: said("", "length") if body["messages"][-1]["role"] == "tool" else called(tool_name(body)), "then returned nothing"),
])
def test_tool_check_fails_for_each_way_a_model_can_misbehave(client, endpoint, name, behavior, reason):
    serve, _seen = endpoint
    result = check(client, serve(behavior))
    assert result["status"] == "failed" and reason in result["reason"], name
    stored = models.get("tc-model")
    assert stored["tools_status"] == "failed" and reason in stored["tools_reason"]


def test_tool_check_never_reveals_the_key_even_when_the_endpoint_echoes_it(client, endpoint):
    serve, _seen = endpoint
    result = check(client, serve(lambda body: httpx.Response(400, text=f"bad request, header was Bearer {KEY} and key {KEY}")))
    assert result["status"] == "failed" and result["reason"].startswith("HTTP 400") and KEY not in json.dumps(result) and KEY not in json.dumps(models.get("tc-model"))
    unreachable = httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError(f"cannot connect with {KEY}")))
    with pytest.raises(Exception) as caught:
        check(client, unreachable)
    assert KEY not in str(caught.value)


def test_tool_check_api_is_admin_only_and_shows_in_the_lists_and_health(client, endpoint, monkeypatch):
    serve, _seen = endpoint
    transport = serve(good_model)
    real = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kw: real(**{**kw, "transport": transport}))
    outcome = client.post("/api/models/tool-check", json={"name": "tc-model"})
    assert outcome.status_code == 200 and outcome.json()["status"] == "passed" and KEY not in outcome.text
    assert client.post("/api/models/tool-check", json={"name": "not-listed"}).status_code == 404
    listed = {m["name"]: m for m in client.get("/api/models").json()}
    assert listed["tc-model"]["tools_status"] == "passed" and listed["tc-model"]["tools_checked_at"]
    assert client.get("/api/settings/models").json()["tools"]["tc-model"]["status"] == "passed"
    health = client.get("/api/health").json()
    assert health["skills"]["loaded"] >= 13 and health["skills"]["problems"] == 0 and health["tool_checks"]["passed"] >= 1 and set(health["tool_checks"]) == {"passed", "failed", "not_checked"}
    name = unique("tester")
    make_user(client, name, models=["tc-model"])
    other, _ = sign_in(name)
    assert other.post("/api/models/tool-check", json={"name": "tc-model"}).status_code == 403
    assert other.get("/api/settings/models").json()["tools"]["tc-model"]["status"] == "passed", "chat can warn about a failed check"


def test_a_model_that_passed_the_check_gets_skills_provider_in_chat_and_others_get_the_pick(client, project):
    llm.set_client_override(ScriptedClient([]))
    models.add("tp-model", enabled=True)
    assert skill_chat.mode("principal-test-architect", "tp-model") == "pick" and skill_chat.mode("project-copilot", "tp-model") == "none"
    models.set_tool_check("tp-model", False, "ignored the result", 2000)
    assert skill_chat.mode("principal-test-architect", "tp-model") == "pick"
    plain = agents.build("principal-test-architect", project["id"], chat=True, model="tp-model", source="chat")
    assert not any(isinstance(p, SkillsProvider) for p in plain.context_providers)
    models.set_tool_check("tp-model", True, "ok", 2000)
    assert skill_chat.mode("principal-test-architect", "tp-model") == "provider"
    smart = agents.build("principal-test-architect", project["id"], chat=True, model="tp-model", source="chat")
    provider = next(p for p in smart.context_providers if isinstance(p, SkillsProvider))
    offered = asyncio.run(provider._source.get_skills(SkillsSourceContext(agent=smart)))
    assert [s.frontmatter.name for s in offered] == ["planning-tests"], "only this agent's skills"
    workflow = agents.build("principal-test-architect", project["id"], model="tp-model")
    assert not any(isinstance(p, SkillsProvider) for p in workflow.context_providers), "workflows never rely on a tool to load a skill"
