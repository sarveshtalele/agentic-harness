"""HS-10: the harness create_skill tool writes a Skill Studio draft plan only after the user approves the call in chat.
The real MAF harness and Skill Studio run; only the model is ScriptedClient. The plan stays a draft for a human."""
from __future__ import annotations

import json

import pytest

from backend.core import auth, documents
from backend.db import db
from backend.maf import engine, harness, llm
from backend.maf.harness_kit.catalog import RISKY, LoadedTools
from backend.maf.tools import create_skill
from tests import skill_studio_fixtures as fx
from tests.scripted_client import ScriptedClient
from tests.test_harness_m4 import NEEDLE, client, steps, thread, turn  # noqa: F401 - fixtures


def _plans(project_id: str) -> list[dict]:
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM skill_plans WHERE project_id=? ORDER BY created_at", (project_id,))]


def test_create_skill_is_risky_and_loadable(client, thread):
    llm.set_client_override(ScriptedClient([]))
    agent = harness.build(thread["project_id"], thread["id"], engine.start, user_id="admin")
    loaded = next(p for p in agent.context_providers if isinstance(p, LoadedTools))
    assert "create_skill" in RISKY and loaded.catalogue.tools["create_skill"].approval_mode == "always_require"
    assert "create_skill" in [f["name"] for f in loaded.catalogue.search("skill")]
    assert "create_skill" not in [t.name for t in agent.default_options["tools"]]  # not core: found and loaded on demand


def test_create_skill_waits_for_approval_then_writes_a_draft_plan(client, thread):
    name = fx.unique_name()
    doc = documents.create(thread["project_id"], "brd", "Invoices", fx.SOURCE, "admin")
    call = {"call": "create_skill", "args": {"request": "Book invoice lines", "kind": "instructions", "document_id": doc["id"]}}
    scripted = ScriptedClient([("TASK: plan a new agent skill", json.dumps(fx.plan(name, "instructions"))),
                               (NEEDLE, steps({"call": "load_tools", "args": {"names": ["create_skill"]}}, call, "Planned."))])
    llm.set_client_override(scripted)
    finished = turn(client, thread["id"], "Make me a skill for booking invoices", "r1")[-1]
    assert finished["outcome"]["type"] == "interrupt"
    interrupt = finished["outcome"]["interrupts"][0]
    assert interrupt["reason"] == "tool_call" and "create_skill" in interrupt["message"]
    assert _plans(thread["project_id"]) == []  # nothing written before a human answered
    events = turn(client, thread["id"], None, "r2", resume=[{"interruptId": interrupt["id"], "status": "resolved", "payload": {"approved": True}}])
    result = json.loads(next(e for e in events if e["type"] == "TOOL_CALL_RESULT")["content"])
    [stored] = _plans(thread["project_id"])
    assert stored["status"] == "draft" and stored["author"] == auth.ADMIN_ID and stored["kind"] == "instructions"
    assert stored["approved_by"] == "" and stored["plan_sha256"] == "" and stored["source_type"] == "document"
    assert stored["source_ref"] == f"{doc['id']}@v{doc['version']}" and json.loads(stored["plan_json"])["name"] == name
    assert result == {"plan_id": stored["id"], "status": "draft", "name": name, "description": fx.DESCRIPTION, "tasks": 3, "subagents": 0,
                      "eval_cases": 2, "studio_url": f"/skills/studio?plan={stored['id']}", "note": create_skill.DRAFT}


def test_rejected_create_skill_writes_nothing(client, thread):
    call = {"call": "create_skill", "args": {"request": fx.SOURCE}}
    llm.set_client_override(ScriptedClient([(NEEDLE, steps({"call": "load_tools", "args": {"names": ["create_skill"]}}, call, "Not planned."))]))
    interrupt = turn(client, thread["id"], "Make a skill", "r1")[-1]["outcome"]["interrupts"][0]
    turn(client, thread["id"], None, "r2", resume=[{"interruptId": interrupt["id"], "status": "resolved", "payload": {"approved": False}}])
    assert _plans(thread["project_id"]) == []


@pytest.mark.asyncio
async def test_a_viewer_is_refused_and_an_unknown_document_is_not_found(client, thread):
    tool = create_skill.build(thread["project_id"])

    async def as_user(user: dict, arguments: dict) -> str:
        token = auth.current_user.set(user)
        try:
            return "".join(c.text or "" for c in await tool.invoke(arguments=arguments))
        finally:
            auth.current_user.reset(token)

    refused = await as_user({"id": "usr_viewer", "role": "user", "account_role": "viewer"}, {"request": fx.SOURCE})
    assert refused.startswith("No plan created") and "Only an administrator or a BA, developer or QE lead" in refused
    missing = await as_user({"id": auth.ADMIN_ID, "role": "admin", "account_role": "admin"}, {"request": fx.SOURCE, "document_id": "doc_missing"})
    assert missing.startswith("No plan created: not found")
    assert _plans(thread["project_id"]) == []
