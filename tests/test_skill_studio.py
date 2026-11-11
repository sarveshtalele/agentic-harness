"""Skill Studio end to end on a real store, real skills folder and real pytest, with ScriptedClient as the only stand-in (for the model).

plan -> edit -> approve -> generate -> checks -> test (real pytest) -> try on sample -> evaluate -> publish v1, v2 -> zip -> delete -> upload v3.
"""
from __future__ import annotations

import io
import json
import shutil
import zipfile

import pytest

from backend.config import SKILLS_DIR
from backend.core import skills as catalog
from backend.core.security import sha256
from backend.core.skill_studio.plans import canonical
from backend.db import db, rows
from backend.maf import llm
from tests import skill_studio_fixtures as fx
from tests.scripted_client import ScriptedClient
from tests.helpers_api import client, project  # noqa: F401 - fixtures


@pytest.fixture
def name():
    made = fx.unique_name()
    yield made
    shutil.rmtree(SKILLS_DIR / made, ignore_errors=True)  # only the folder this test published
    catalog.load(force=True)


def test_full_studio_flow(client, project, name):
    scripted = ScriptedClient(fx.rules(name))
    llm.set_client_override(scripted)
    plan = fx.new_plan(client, project["id"])
    pid = plan["id"]
    assert plan["status"] == "draft" and plan["plan"]["name"] == name and plan["source_sha256"] == sha256(fx.SOURCE)
    assert plan["prompt_ref"].startswith("skill-creator@v")
    with db() as con:
        calls = rows(con.execute("SELECT agent, prompt_ref FROM agent_calls WHERE agent='skill-creator' AND project_id=?", (project["id"],)))
    assert calls and calls[0]["prompt_ref"] == plan["prompt_ref"], "the plan call is recorded in agent_calls"
    assert "<untrusted-data" in scripted.calls[0] and fx.SOURCE.splitlines()[0] in scripted.calls[0]

    assert client.post(f"/api/skill-studio/plans/{pid}/generate").status_code == 409, "no generation before approval"
    edited = {**plan["plan"], "tasks": ["Find each invoice line", "Book one ledger line per item"]}
    assert client.patch(f"/api/skill-studio/plans/{pid}", json={"plan": edited}).json()["plan"]["tasks"][1] == "Book one ledger line per item"
    approved = client.post(f"/api/skill-studio/plans/{pid}/approve").json()
    assert approved["status"] == "approved" and approved["approved_by"] == "admin" and approved["plan_sha256"] == sha256(canonical(edited))
    assert client.patch(f"/api/skill-studio/plans/{pid}", json={"plan": edited}).status_code == 409, "an approved plan is fixed"

    generated = client.post(f"/api/skill-studio/plans/{pid}/generate").json()
    assert generated["summary"]["all_passed"], generated["checks"]
    assert {c["check"] for c in generated["checks"]} >= {"frontmatter", "name matches folder", "MAF loads it", "security scan", "scripts/test_ledger.py parses"}
    assert {f["path"] for f in generated["files"]} == set(fx.FILES)

    run = client.post(f"/api/skill-studio/plans/{pid}/test", json={"mode": "scripts"}).json()
    assert run["verdict"] == "PASS" and run["passed"] == 2 and run["failed"] == 0 and run["exit_code"] == 0, run
    tried = client.post(f"/api/skill-studio/plans/{pid}/test", json={"mode": "sample", "sample_text": "Invoice INV-7: 3 x Widget at 10 EUR"}).json()
    assert tried["output"] == "INV-7 Widget 3 net 30 EUR" and tried["tokens_in"] == 10

    graded = client.post(f"/api/skill-studio/plans/{pid}/evaluate").json()
    assert graded["metrics"] == {"assertion_pass_rate_with_skill": 1.0, "assertion_pass_rate_without_skill": 0.0, "skill_uplift": 1.0}
    assert graded["n"] == 2 and all(a["passed"] for c in graded["cases"] for a in c["with_skill"]["assertions"])
    with db() as con:
        stored = rows(con.execute("SELECT metric, value, n, judge_model, source, prompt_ref, self_graded FROM evaluation_metrics WHERE agent=?", (f"skill:{name}",)))
    assert {r["metric"] for r in stored} == set(graded["metrics"]) and all(r["n"] == 2 and r["judge_model"] == "deterministic-assertions" and r["source"] == "skill-studio"
                                                                          and r["self_graded"] == 0 and r["prompt_ref"] == graded["prompt_ref"] for r in stored)

    first = client.post(f"/api/skill-studio/plans/{pid}/publish")
    assert first.status_code == 201 and first.json()["version"] == 1 and (SKILLS_DIR / name / "scripts" / "ledger.py").is_file()
    assert name in catalog.load() and client.get(f"/api/skills/{name}").json()["description"] == fx.DESCRIPTION
    second = client.post(f"/api/skill-studio/plans/{pid}/publish").json()
    assert second["version"] == 2 and second["sha256"] == first.json()["sha256"]

    blob = client.get(f"/api/skill-studio/skills/{name}/versions/1/zip")
    assert blob.status_code == 200 and blob.headers["content-type"] == "application/zip"
    assert f"{name}/SKILL.md" in zipfile.ZipFile(io.BytesIO(blob.content)).namelist()

    gone = client.delete(f"/api/skill-studio/skills/{name}", params={"project_id": project["id"]}).json()
    assert gone["versions_kept"] == 2 and not (SKILLS_DIR / name).exists() and name not in catalog.load()
    assert [v["version"] for v in client.get(f"/api/skill-studio/skills/{name}/versions").json()["versions"]] == [2, 1], "deleting keeps every version"

    back = client.post("/api/skill-studio/upload", data={"project_id": project["id"]}, files={"file": ("skill.zip", blob.content, "application/zip")})
    assert back.status_code == 201 and back.json()["version"] == 3 and (SKILLS_DIR / name / "SKILL.md").is_file()
    with db() as con:
        actions = [r["action"] for r in rows(con.execute("SELECT action FROM ledger WHERE project_id=? AND action LIKE 'skill.%' ORDER BY seq", (project["id"],)))]
    assert actions == ["skill.plan.created", "skill.plan.edited", "skill.plan.approved", "skill.generated", "skill.evaluated", "skill.published", "skill.published", "skill.deleted", "skill.published"]


def test_generate_is_refused_when_the_stored_plan_changed_after_approval(client, project, name):
    llm.set_client_override(ScriptedClient(fx.rules(name)))
    pid = fx.new_plan(client, project["id"])["id"]
    client.post(f"/api/skill-studio/plans/{pid}/approve")
    with db() as con:
        stored = json.loads(con.execute("SELECT plan_json FROM skill_plans WHERE id=?", (pid,)).fetchone()[0])
        con.execute("UPDATE skill_plans SET plan_json=? WHERE id=?", (canonical({**stored, "tasks": ["Do something else"]}), pid))
    refused = client.post(f"/api/skill-studio/plans/{pid}/generate")
    assert refused.status_code == 409 and "approved SHA-256" in refused.json()["detail"]


def test_a_generated_path_outside_the_plan_is_refused_and_the_reply_kept(client, project, name):
    llm.set_client_override(ScriptedClient(fx.rules(name, extra=[{"path": "scripts/extra.py", "content": "X = 1\n"}])))
    pid = fx.new_plan(client, project["id"])["id"]
    client.post(f"/api/skill-studio/plans/{pid}/approve")
    refused = client.post(f"/api/skill-studio/plans/{pid}/generate")
    assert refused.status_code == 502, refused.text
    detail = refused.json()["detail"]
    assert "not in the approved plan" in detail["message"] and detail["reply_file"].endswith(".txt")
    assert client.get(f"/api/skill-studio/plans/{pid}").json()["status"] == "approved", "nothing was generated"


def test_an_instructions_skill_refuses_scripts(client, project, name):
    llm.set_client_override(ScriptedClient(fx.rules(name, kind="instructions", extra=[{"path": "scripts/run.py", "content": "X = 1\n"}])))
    plan = fx.new_plan(client, project["id"], kind="instructions")
    bad = {**plan["plan"], "files": [*plan["plan"]["files"], {"path": "scripts/run.py", "purpose": "a script"}]}
    refused = client.patch(f"/api/skill-studio/plans/{plan['id']}", json={"plan": bad})
    assert refused.status_code == 422 and "not allowed when kind is instructions" in refused.json()["detail"]
