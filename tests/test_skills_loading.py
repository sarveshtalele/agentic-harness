"""Plugin skills on MAF: loading, the agent mapping, injection into the message, and what is recorded."""
import dataclasses
import json

import pytest

from backend.core import skills as skill_lib
from backend.db import db, rows
from backend.maf import governance, llm
from backend.maf import runtime as agents
from backend.maf.agents import POLICIES
from tests.scripted_client import ScriptedClient
from tests.helpers_api import client, project  # noqa: F401 - fixtures
from tests.helpers_skills import ARCHITECT, EXPECTED


# ---- loading and the agent mapping ------------------------------------------------

def test_every_skill_loads_through_maf_with_its_references():
    loaded = skill_lib.load(force=True)
    assert EXPECTED.issubset(set(loaded)) and skill_lib.problems() == []
    for name, skill in loaded.items():
        if name in EXPECTED:
            assert skill.description and skill.version == "1.4.0" and skill.body.startswith("#") and "name:" not in skill.body.split("\n")[0]
    assert set(skill_lib.references("planning-tests")) == {"LEVEL_GUIDELINES.md"}
    assert skill_lib.references("building-qe-dashboard") == {}
    assert skill_lib.get("planning-tests").sha256 and skill_lib.get("planning-tests").sha256 != skill_lib.get("tracing-coverage").sha256
    with pytest.raises(KeyError):
        skill_lib.get("no-such-skill")


def test_a_policy_that_names_an_unknown_skill_fails():
    unknown = {f"{key}: {name}" for key, policy in POLICIES.items() for name in policy.skills if name not in skill_lib.load()}
    assert not unknown, f"These policies name skills that do not exist in skills/: {sorted(unknown)}"
    assert {name for policy in POLICIES.values() for name in policy.skills} <= EXPECTED


def test_the_mapping_matches_the_plan_table():
    assert {key: policy.skills for key, policy in POLICIES.items() if policy.skills} == {
        "repo-intelligence-analyst": ("analyzing-repositories",), "requirements-analyst": ("extracting-requirements",), "business-analyst": ("authoring-user-stories",),
        "principal-test-architect": ("planning-tests",), "test-design-architect": ("designing-test-cases", "generating-test-data"), "test-automation-engineer": ("generating-test-code",),
        "defect-diagnostician": ("healing-tests",), "confidence-reviewer": ("tracing-coverage",), "qa-execution-engineer": ("executing-tests",)}
    assert len(POLICIES) == 14  # 13 platform agents and the Skill Studio's skill creator (M3); the harness moved out (STABLE_BUILD_PLAN)
    for key in ("bug-reviewer", "feature-engineer", "project-copilot", "bug-fix-reviewer", "skill-creator"):
        assert POLICIES[key].skills == () and skill_lib.for_agent(key) == []
    assert skill_lib.agent_of("building-qe-dashboard") == [] and skill_lib.agent_of("generating-test-data") == ["test-design-architect"]


def test_a_skill_maf_cannot_load_is_absent_and_reported(tmp_path):
    good = "---\nname: good-one\ndescription: A good skill.\nmetadata:\n  version: \"2.0\"\n---\n\n# Good\nDo the thing.\n"
    for folder, text in {"good-one": good, "Bad_Name": "---\nname: Bad_Name\ndescription: x\n---\n# no\n", "huge": "---\nname: huge\ndescription: Too big.\n---\n" + "x" * (skill_lib.BODY_LIMIT + 1)}.items():
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "SKILL.md").write_text(text, encoding="utf-8")
    loaded = skill_lib.load(root=tmp_path)
    assert set(loaded) == {"good-one"} and loaded["good-one"].version == "2.0"
    assert EXPECTED.issubset(set(skill_lib.names())), "loading another folder does not replace the platform's skills"


# ---- the skill text reaches the message, once, before the task --------------------

def call_for(project, key="principal-test-architect", **kwargs):
    scripted = ScriptedClient([(ARCHITECT, "ok")])
    llm.set_client_override(scripted)
    return scripted, agents.AgentCall(None, project["id"], key, **kwargs)


def test_skill_text_reaches_the_agents_message_once_and_before_the_task(client, project):
    scripted, call = call_for(project)
    client.portal.call(call.text, "Plan the thing for REQ-001.")
    client.portal.call(call.text, "Plan it again.")
    sent = scripted.calls[0]
    assert '<skill name="planning-tests" version="1.4.0">' in sent
    assert '<reference skill="planning-tests" file="LEVEL_GUIDELINES.md">' in sent and skill_lib.references("planning-tests")["LEVEL_GUIDELINES.md"][:40] in sent
    assert sent.index("<skill name=") < sent.index("TASK:\nPlan the thing for REQ-001.")
    assert "reply only in the format this request asks for" in sent
    assert scripted.calls[1].count('<skill name="planning-tests"') == 1, "the session keeps it, so a second message does not send it again"


def test_a_stage_chooses_its_skills_and_references(client, project):
    scripted, call = call_for(project, "test-design-architect", skills=("designing-test-cases",))
    scripted.rules = [("You are a test design architect", "ok")]
    client.portal.call(call.text, "Design.")
    assert '<skill name="designing-test-cases"' in scripted.calls[0] and "generating-test-data" not in scripted.calls[0] and "ORACLE_TYPES.md" in scripted.calls[0]
    scripted, call = call_for(project, refs=())
    client.portal.call(call.text, "Plan.")
    assert '<skill name="planning-tests"' in scripted.calls[0] and "<reference" not in scripted.calls[0]
    scripted, call = call_for(project, skills=())
    client.portal.call(call.text, "Plan.")
    assert "<skill" not in scripted.calls[0] and call.prompt_ref == governance.prompts.ref("principal-test-architect")
    with pytest.raises(ValueError, match="does not use the skill"):
        call_for(project, skills=("healing-tests",))
    scripted, call = call_for(project, "project-copilot")
    assert call.skill_set.text == ""


def test_skill_text_is_bounded(monkeypatch):
    monkeypatch.setattr(skill_lib, "REFERENCE_LIMIT", 10)
    rendered = skill_lib.render(["executing-tests"])
    assert rendered.skipped == ["executing-tests/RUNNER_REGISTRY.md", "executing-tests/VERSIONS.md"] and "<reference" not in rendered.text
    assert len(skill_lib.render(["planning-tests", "designing-test-cases"]).text) < skill_lib.BODY_LIMIT


def test_the_json_format_rule_still_follows_the_skill(client, project):
    scripted, call = call_for(project)
    scripted.rules = [(ARCHITECT, '{"cases": []}')]

    class Shape(agents.BaseModel):
        cases: list

    client.portal.call(call.typed, "Plan it.", Shape)
    sent = scripted.calls[0]
    assert sent.index("<skill name=") < sent.index("TASK:") < sent.index("Reply with only one JSON object")


# ---- what is recorded: the live log, agent_calls, the prompt reference -------------

def test_skill_event_agent_call_row_and_prompt_reference(client, project, monkeypatch):
    events = []
    agents.set_emitter(lambda kind, message, data=None: events.append((kind, message, data or {})))
    try:
        scripted, call = call_for(project)
        client.portal.call(call.text, "Plan.")
    finally:
        agents.set_emitter(None)
    skill_events = [e for e in events if e[0] == "skill"]
    assert len(skill_events) == 1 and skill_events[0][2]["skill"] == "planning-tests" and skill_events[0][2]["version"] == "1.4.0"
    assert "planning-tests" in skill_events[0][1]
    with db() as con:
        row = rows(con.execute("SELECT * FROM agent_calls WHERE agent='principal-test-architect' ORDER BY id DESC LIMIT 1"))[0]
    used = json.loads(row["skills"])
    assert used == [{"name": "planning-tests", "version": "1.4.0", "sha256": skill_lib.get("planning-tests").sha256, "refs": ["LEVEL_GUIDELINES.md"]}]
    assert row["prompt_ref"] == call.prompt_ref and "+skills:" in row["prompt_ref"] and call.prompt_ref.startswith(governance.prompts.ref("principal-test-architect"))

    # a changed skill changes the reference, so a stored document version says which skill text made it
    changed = {**skill_lib.load(), "planning-tests": dataclasses.replace(skill_lib.get("planning-tests"), body=skill_lib.get("planning-tests").body + "\nAlso do this.")}
    monkeypatch.setitem(skill_lib._state, "skills", changed)
    other = agents.AgentCall(None, project["id"], "principal-test-architect")
    assert other.prompt_ref != call.prompt_ref and other.prompt_ref.split("+skills:")[0] == call.prompt_ref.split("+skills:")[0]
    assert agents.AgentCall(None, project["id"], "principal-test-architect", skills=()).prompt_ref == governance.prompts.ref("principal-test-architect"), "no skill sent, no suffix"
