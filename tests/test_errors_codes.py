"""Broken JSON, error codes and evidence failures."""

import json

import subprocess

import httpx
import openai
import pytest

from pydantic import BaseModel

from backend.core import errors
from backend.db import db
from backend.maf import llm
from backend.maf.runtime import AgentCall, extract_json
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient
from tests.helpers_api import GOOD_REVIEW, make_user, pending, sign_in, unique, upload_repo, wait_run


class Shape(BaseModel):
    cases: list[dict]


def ask(project, reply, schema=Shape, agent="confidence-reviewer", attempts=3):
    """Run AgentCall.typed against a scripted reply and return the error it ends with."""
    scripted = ScriptedClient([("Review this", reply)])
    llm.set_client_override(scripted)
    return scripted, AgentCall(None, project["id"], agent)


def fails(client, project, reply, schema=Shape):
    scripted, call = ask(project, reply, schema)
    with pytest.raises(errors.AqeError) as caught:
        client.portal.call(call.typed, "Review this", schema)
    return caught.value, scripted


def request():
    return httpx.Request("POST", "http://proxy.test/v1/chat/completions")


def refuse(exc):
    def raiser(_text):
        raise exc

    return raiser


def test_broken_json_of_every_kind_is_never_replaced_by_a_fragment(client, project):
    cut_off = '{"cases": [{"id": "A", "x": 1}, {"id": "B", "x": '
    error, scripted = fails(client, project, cut_off)
    assert error.code == "AQE-MODEL-001" and "not valid JSON near character" in error.message and error.detail["parse_pos"] > 0
    assert error.retryable and error.action and "That reply was rejected" in scripted.calls[-1], "the position goes back to the model"
    assert error.detail["reply"] == cut_off.strip()
    nested = '{"cases": [{"id": "A", "steps": [{"k": 1}], "x": '  # a complete list inside a case is not the answer
    for names in (("cases",), ()):
        with pytest.raises(ValueError, match="not valid JSON"):
            extract_json(nested, names)
    with pytest.raises(ValueError):
        extract_json('{"cases": [{"id": "A"} {"id": "B"}]}', ("cases",))  # a missing comma
    shaped, _ = fails(client, project, '{"id": "A", "requirement_id": "R"}')
    assert shaped.code == "AQE-MODEL-003" and "not valid JSON" not in shaped.message and "cases" in shaped.message
    # a raw line break and a lone backslash are repaired, and the whole object comes back, not a part of it
    assert extract_json('{"cases": [{"id": "A", "note": "line one\nline two"}, {"id": "B"}]}', ("cases",))["cases"][1] == {"id": "B"}
    assert extract_json(r'{"cases": [{"id": "A", "pattern": "\d+ in C:\Users"}, {"id": "B"}]}', ("cases",))["cases"][0]["pattern"] == r"\d+ in C:\Users"


def test_each_error_code_comes_from_a_real_failure(client, project, tmp_path):
    from backend.core import auth
    from backend.maf.workflows import qe
    from backend.maf.engine import RunContext
    from backend.repos import git

    truncated = {"cut_off": '{"cases": [{"id": "A"'}
    error, _ = fails(client, project, truncated)
    assert error.code == "AQE-MODEL-002" and error.detail["finish_reason"] == "length" and "token limit" in error.action and not error.retryable
    assert fails(client, project, "plain prose")[0].code == "AQE-MODEL-001"
    assert fails(client, project, '{"id": "A"}')[0].code == "AQE-MODEL-003"
    timeout, _ = fails(client, project, refuse(openai.APITimeoutError(request=request())))
    assert timeout.code == "AQE-MODEL-004" and timeout.retryable and "ATLAS_MODEL_TIMEOUT" in timeout.action
    refused, _ = fails(client, project, refuse(RuntimeError("400 finish_reason content_filter blocked by label 'Jailbreak'")))
    assert refused.code == "AQE-MODEL-005" and "Jailbreak" in refused.message and not refused.retryable
    reply = httpx.Response(401, request=request(), headers={"x-request-id": "req-from-provider"})
    key, _ = fails(client, project, refuse(openai.AuthenticationError("bad key", response=reply, body=None)))
    assert key.code == "AQE-MODEL-006" and not key.retryable and "Settings" in key.action
    assert key.detail["provider_status"] == 401 and key.detail["provider_request_id"] == "req-from-provider", "the provider's status and request id are kept"
    busy, _ = fails(client, project, refuse(openai.RateLimitError("slow down", response=httpx.Response(429, request=request()), body=None)))
    assert busy.code == "AQE-MODEL-006" and busy.retryable and busy.detail["provider_status"] == 429
    assert fails(client, project, refuse(openai.APIConnectionError(request=request())))[0].code == "AQE-MODEL-006"
    # allocation
    name = unique()
    make_user(client, name, token_limit=0)
    owner, _ = sign_in(name)
    limited = owner.post("/api/projects", json={"name": "Limited", "description": ""}).json()
    with db() as con:
        con.execute("INSERT INTO agent_calls (agent, project_id, source, prompt_ref, tokens_in, tokens_out, latency_ms, tool_calls, status, created_at) VALUES ('project-copilot', ?, 'chat', 'x', 5, 5, 1, 0, 'ok', '2026-01-01')", (limited["id"],))
    with pytest.raises(errors.AllowanceError) as caught:
        auth.check_allowance(limited["id"])
    assert caught.value.code == "AQE-ALLOW-001" and "administrator" in caught.value.action and not caught.value.retryable
    # git
    with pytest.raises(errors.RepoError) as caught:
        git.run(["definitely-not-a-git-command"], cwd=tmp_path)
    assert caught.value.code == "AQE-REPO-001" and "repository" in caught.value.action
    # tests that could not run
    def timed_out(*_):
        raise subprocess.TimeoutExpired("pip", 1)

    from backend.qe import execution

    original = execution.install_dependencies
    execution.install_dependencies = timed_out
    try:
        with pytest.raises(errors.ExecutionError) as caught:
            client.portal.call(qe.qe_prepare, RunContext("run_x", project["id"], "prepare"), {"worktree": str(tmp_path), "install_deps": True, "framework": "pytest", "mode": "brownfield"})
    finally:
        execution.install_dependencies = original
    assert caught.value.code == "AQE-TEST-001" and "install dependencies" in caught.value.action
    # a bug in this application
    bug = errors.classify(ZeroDivisionError("division by zero"))
    assert bug.code == "AQE-INT-001" and "diagnostics" in bug.action and not bug.retryable
    # old types still work
    assert issubclass(errors.AllowanceError, RuntimeError) and issubclass(git.GitError, RuntimeError) and issubclass(llm.LLMNotConfigured, RuntimeError)


def test_evidence_failure_is_aqe_evid_001_on_the_run(client, project):
    upload_repo(client, project, {"calc.py": "def add(a, b):\n    return a + b\n", "conftest.py": ""})
    fake = json.dumps({"requirements": [{"id": "REQ-001", "title": "x", "statement": "invented", "priority": "P0", "tier": "observed", "file": "calc.py", "line": 1, "quote": "not in the file"}]})
    llm.set_client_override(ScriptedClient([("You are a repository intelligence analyst", "## Purpose\nCalc"), ("You are a requirements analyst", fake), *case_rules(), ("You are an independent reviewer", GOOD_REVIEW)]))
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()
    run = wait_run(client, run["id"])
    client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True})
    run = wait_run(client, run["id"], ("failed",))
    assert run["failure"]["code"] == "AQE-EVID-001" and run["failure"]["stage"] == "requirements" and "Review the requirements" in run["failure"]["action"]
