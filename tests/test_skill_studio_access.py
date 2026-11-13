"""Skill Studio refusals: viewers, unseen projects and documents, the web profile, core skills, zip-slip, and zero tests run."""
from __future__ import annotations

import io
import json
import zipfile

import pytest

from backend import config
from backend.core import auth, documents
from backend.core.skill_studio import testing
from backend.maf import llm
from tests import skill_studio_fixtures as fx
from tests.scripted_client import ScriptedClient
from tests.helpers_api import client, make_user, project, sign_in, unique  # noqa: F401 - fixtures


def _account(admin, role: str):
    name = unique(role)
    make_user(admin, name, role=role, features=["skills"])  # the rules under test here are roles and projects, not R2
    other, signed = sign_in(name)
    assert signed.status_code == 200
    return other


def test_every_studio_path_has_an_access_rule():
    assert auth.rule_of("/api/skill-studio/plans") == "session" and auth.rule_of("/api/skill-studio/skills/x/versions/1/zip") == "session"


def test_a_viewer_reads_but_cannot_plan_publish_upload_or_delete(client, project):
    viewer = _account(client, "viewer")
    body = {"project_id": project["id"], "kind": "instructions", "source": {"type": "text", "text": fx.SOURCE}}
    assert viewer.post("/api/skill-studio/plans", json=body).status_code == 403
    assert viewer.post("/api/skill-studio/upload", data={"project_id": project["id"]}, files={"file": ("s.zip", b"x")}).status_code == 403
    assert viewer.delete("/api/skill-studio/skills/anything", params={"project_id": project["id"]}).status_code == 403
    assert viewer.get("/api/skill-studio/skills/anything/versions").status_code == 200


def test_a_developer_cannot_delete_and_cannot_use_another_users_project(client, project):
    developer = _account(client, "developer")
    body = {"project_id": project["id"], "kind": "instructions", "source": {"type": "text", "text": fx.SOURCE}}
    assert developer.post("/api/skill-studio/plans", json=body).status_code == 404, "someone else's project is not found"
    own = developer.post("/api/projects", json={"name": "Dev shop"}).json()
    assert developer.delete("/api/skill-studio/skills/anything", params={"project_id": own["id"]}).status_code == 403, "delete is admin only"


def test_documents_of_an_unseen_project_are_not_listed(client, project):
    hidden = documents.create(project["id"], "brd", "Admin BRD", "# Secret plan", "admin")
    developer = _account(client, "developer")
    own = developer.post("/api/projects", json={"name": "Dev docs"}).json()
    mine = documents.create(own["id"], "brd", "Dev BRD", "# Mine", "dev")
    assert developer.get("/api/skill-studio/documents", params={"project_id": project["id"]}).status_code == 404
    listed = developer.get("/api/skill-studio/documents", params={"project_id": own["id"]}).json()["documents"]
    assert [d["id"] for d in listed] == [mine["id"]] and hidden["id"] not in {d["id"] for d in listed}
    source = {"type": "document", "document_id": hidden["id"]}
    assert developer.post("/api/skill-studio/plans", json={"project_id": own["id"], "kind": "instructions", "source": source}).status_code == 404


def test_the_web_profile_refuses_script_runs(client, project, monkeypatch):
    llm.set_client_override(ScriptedClient(fx.rules(fx.unique_name())))
    pid = fx.new_plan(client, project["id"])["id"]
    monkeypatch.setattr(config, "PROFILE", "web")
    refused = client.post(f"/api/skill-studio/plans/{pid}/test", json={"mode": "scripts"})
    assert refused.status_code == 403 and refused.json()["detail"] == testing.WEB_REFUSAL


def test_zero_tests_collected_is_inconclusive_never_pass(tmp_path):
    draft = tmp_path / "empty-skill"
    (draft / "scripts").mkdir(parents=True)
    (draft / "scripts" / "helper.py").write_text("X = 1\n", encoding="utf-8")
    run = testing.run_pytest(draft)
    assert run["verdict"] == "INCONCLUSIVE" and run["passed"] == 0 and run["exit_code"] == 5


def _zip(entries: dict[str, str], link: str = "") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in entries.items():
            archive.writestr(name, text)
        if link:
            info = zipfile.ZipInfo(link)
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "/etc/passwd")
    return buffer.getvalue()


@pytest.mark.parametrize("entries,link,reason", [
    ({"evil/SKILL.md": "---\nname: evil\ndescription: x. Use when x.\n---\n", "evil/../../escape.txt": "x"}, "", "outside the skill folder"),
    ({"/abs/SKILL.md": "x"}, "", "outside the skill folder"),
    ({"evil/SKILL.md": "---\nname: evil\ndescription: x. Use when x.\n---\n"}, "evil/link", "symbolic link"),
    ({"evil/notes.md": "no skill here"}, "", "no SKILL.md"),
])
def test_unsafe_or_broken_zips_are_refused(client, project, entries, link, reason):
    refused = client.post("/api/skill-studio/upload", data={"project_id": project["id"]}, files={"file": ("s.zip", _zip(entries, link), "application/zip")})
    assert refused.status_code == 409 and reason in refused.json()["detail"], refused.text
    assert not (config.ROOT / "escape.txt").exists() and not (config.SKILLS_DIR / "evil").exists()


def test_core_skills_cannot_be_overwritten_or_deleted(client, project):
    core = _zip({"planning-tests/SKILL.md": "---\nname: planning-tests\ndescription: Plans. Use when planning.\n---\n# Body\n"})
    assert client.post("/api/skill-studio/upload", data={"project_id": project["id"]}, files={"file": ("s.zip", core)}).status_code == 409
    assert client.delete("/api/skill-studio/skills/planning-tests", params={"project_id": project["id"]}).status_code == 409
    assert (config.SKILLS_DIR / "planning-tests" / "SKILL.md").is_file()


def test_a_plan_reply_that_breaks_the_rules_is_a_502(client, project):
    name = fx.unique_name()
    bad = fx.plan(name)
    bad["description"] = "You can use this to book invoices."
    llm.set_client_override(ScriptedClient([("TASK: plan a new agent skill", json.dumps(bad))]))
    refused = client.post("/api/skill-studio/plans", json={"project_id": project["id"], "kind": "scripts", "source": {"type": "text", "text": fx.SOURCE}})
    assert refused.status_code == 502 and "Use when" in refused.json()["detail"]["message"]


def test_an_eval_input_that_repeats_the_source_is_refused():
    from backend.core.skill_studio.models import SkillPlan, plan_problems
    from tests.skill_studio_fixtures import SOURCE, plan
    good = SkillPlan.model_validate(plan("invoice-lines-x"))
    assert not [p for p in plan_problems(good, "scripts", set(), SOURCE) if "repeats the source" in p]
    copied = plan("invoice-lines-y")
    copied["eval_cases"][0]["input"] = SOURCE
    problems = plan_problems(SkillPlan.model_validate(copied), "scripts", set(), SOURCE)
    assert any("eval case 1 input repeats the source" in p for p in problems)
