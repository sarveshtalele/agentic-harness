"""A script skill is published only after its own tests pass on exactly the files being published (live run 2026-11-11:
tabular-converter was published with 2 failing tests before this rule)."""
from __future__ import annotations

import json
import shutil

from backend.config import SKILLS_DIR
from backend.maf import llm
from tests import skill_studio_fixtures as fx
from tests.helpers_api import client, project  # noqa: F401 - fixtures
from tests.scripted_client import ScriptedClient

FAILING_TEST = "from ledger import lines\n\n\ndef test_wrong_net():\n    assert lines('Invoice INV-7: 3 x Widget at 10 EUR')[0]['net'] == 31\n"


def _generated(client, project_id, name, test_body=None):
    rules = fx.rules(name)
    if test_body:  # the planned test file, with a test that fails
        written = fx.files(name)
        written["files"] = [{**f, "content": test_body} if f["path"] == "scripts/test_ledger.py" else f for f in written["files"]]
        rules[1] = (rules[1][0], json.dumps(written))
    llm.set_client_override(ScriptedClient(rules))
    pid = fx.new_plan(client, project_id)["id"]
    assert client.post(f"/api/skill-studio/plans/{pid}/approve").status_code == 200
    assert client.post(f"/api/skill-studio/plans/{pid}/generate").status_code == 200
    return pid


def test_publish_needs_a_passing_test_run_on_the_same_files(client, project):
    name = fx.unique_name()
    try:
        pid = _generated(client, project["id"], name)
        refused = client.post(f"/api/skill-studio/plans/{pid}/publish")
        assert refused.status_code == 409 and "Run the skill's tests first" in refused.text
        assert client.post(f"/api/skill-studio/plans/{pid}/test", json={"mode": "scripts"}).json()["verdict"] == "PASS"
        assert client.post(f"/api/skill-studio/plans/{pid}/publish").status_code == 201
    finally:
        llm.set_client_override(None)
        shutil.rmtree(SKILLS_DIR / name, ignore_errors=True)


def test_failing_tests_block_publishing(client, project):
    name = fx.unique_name()
    try:
        pid = _generated(client, project["id"], name, test_body=FAILING_TEST)
        run = client.post(f"/api/skill-studio/plans/{pid}/test", json={"mode": "scripts"}).json()
        assert run["verdict"] == "FAIL" and run["failed"] == 1, run
        refused = client.post(f"/api/skill-studio/plans/{pid}/publish")
        assert refused.status_code == 409 and "did not pass (verdict FAIL)" in refused.text
        assert not (SKILLS_DIR / name).exists()
    finally:
        llm.set_client_override(None)
        shutil.rmtree(SKILLS_DIR / name, ignore_errors=True)


def _repair_rule(name, test_body):
    written = fx.files(name)
    written["files"] = [{**f, "content": test_body} if f["path"] == "scripts/test_ledger.py" else f for f in written["files"]]
    return ("TASK: repair the files", json.dumps(written))


def test_repair_fixes_a_wrong_expectation_and_then_the_skill_publishes(client, project):
    name = fx.unique_name()
    try:
        pid = _generated(client, project["id"], name, test_body=FAILING_TEST)
        fixed = FAILING_TEST.replace("== 31", "== 30")  # same test, same assertion, right expectation
        llm.set_client_override(ScriptedClient([_repair_rule(name, fixed)] + fx.rules(name)))
        result = client.post(f"/api/skill-studio/plans/{pid}/repair").json()
        assert result["verdict"] == "PASS" and result["rounds"] == 1 and result["history"][0]["verdict"] == "FAIL", result
        assert client.post(f"/api/skill-studio/plans/{pid}/publish").status_code == 201
    finally:
        llm.set_client_override(None)
        shutil.rmtree(SKILLS_DIR / name, ignore_errors=True)


def test_a_repair_that_weakens_the_tests_is_refused_and_not_written(client, project):
    name = fx.unique_name()
    try:
        pid = _generated(client, project["id"], name, test_body=FAILING_TEST)
        weakened = "from ledger import lines\n\n\ndef test_wrong_net():\n    lines('Invoice INV-7: 3 x Widget at 10 EUR')\n"
        llm.set_client_override(ScriptedClient([_repair_rule(name, weakened)] + fx.rules(name)))
        result = client.post(f"/api/skill-studio/plans/{pid}/repair").json()
        assert result["verdict"] == "REFUSED" and "removed assertions" in result["history"][-1]["detail"], result
        assert client.post(f"/api/skill-studio/plans/{pid}/publish").status_code == 409  # the failing files stay
    finally:
        llm.set_client_override(None)
        shutil.rmtree(SKILLS_DIR / name, ignore_errors=True)


def test_server_writes_frontmatter_so_an_unquoted_colon_cannot_break_it():
    """Owner report 2026-11-11: the model's description held 'syntax: headings' unquoted, the YAML broke three times, and the
    Studio showed a raw error. The server now writes name, description and author from the approved plan."""
    from backend.core.skill_studio.checks import frontmatter
    from backend.core.skill_studio.models import SkillPlan, files_schema
    name = fx.unique_name()
    plan = SkillPlan.model_validate({**fx.plan(name), "description": "Converts Markdown, supporting core syntax: headings and lists. Use when HTML is needed."})
    written = fx.files(name)
    written["files"] = [{**f, "content": f"---\nname: {name}\ndescription: Converts Markdown, supporting core syntax: headings\nversion: 9\n---\n# Body kept\n"}
                        if f["path"] == "SKILL.md" else f for f in written["files"]]
    checked = files_schema(plan, "scripts", "dev-1").model_validate(written)
    skill_md = next(f.content for f in checked.files if f.path == "SKILL.md")
    front, body = frontmatter(skill_md)
    assert front == {"name": name, "description": plan.description, "metadata": {"author": "dev-1"}}
    assert body.strip() == "# Body kept" and "version" not in skill_md


def test_a_script_skill_without_run_py_fails_its_checks(tmp_path):
    from backend.core.skill_studio import checks

    folder = tmp_path / "invoice-totals"
    (folder / "scripts").mkdir(parents=True)
    (folder / "SKILL.md").write_text("---\nname: invoice-totals\ndescription: Computes invoice totals.\n---\n\nRun the script.\n")
    (folder / "scripts" / "invoice_total_calculator.py").write_text("print('total')\n")  # what the live generation shipped instead of run.py
    entry = {c["check"]: c for c in checks.run(folder)}["scripts/run.py entry point"]
    assert not entry["passed"] and "no scripts/run.py" in entry["detail"]
    (folder / "scripts" / "run.py").write_text("import sys\nprint(sys.stdin.read())\n")
    assert {c["check"]: c for c in checks.run(folder)}["scripts/run.py entry point"]["passed"]
