"""The agentic-qe plugin bridge: skill guide, plugin files, and the plugin's real check-gate.ts as the Gate 1 sensor."""
import json
import shutil
import uuid

import pytest

from backend.config import project_dir
from backend.core import script_runtime
from backend.qe import plugin_bridge as pb

node_ok = script_runtime.plan(pb.CHECK_GATE, pb.CHECK_GATE.parent.parent).argv is not None


def _project(code: str) -> str:
    pid = "p-" + uuid.uuid4().hex[:10]
    repo = project_dir(pid) / "repo"
    repo.mkdir(parents=True)
    (repo / "app.py").write_text(code, encoding="utf-8")
    return pid


def _req(rid, quote, line=1):
    return {"id": rid, "title": "Add", "statement": "Adds two numbers", "priority": "P1", "tier": "observed",
            "file": "app.py", "line": line, "quote": quote}


def test_guide_has_the_plugin_requirement_skills():
    text = pb.guide("qe-requirements", "extracting-requirements")
    assert "## extracting-requirements/SKILL.md" in text and "## extracting-requirements/references/REQUIREMENT_RULES.md" in text
    assert not text.startswith("---")
    with pytest.raises(FileNotFoundError):
        pb.guide("no-such-skill")


def test_app_name_is_a_plugin_safe_slug():
    assert pb.app_name("Proj 1/../x") == "Proj-1-..-x"
    assert all(c.isalnum() or c in "._-" for c in pb.app_name("a b/c\\d:e"))
    assert pb.app_name("///") == "app"


def test_requirements_file_maps_platform_fields():
    out = pb.requirements_file([_req("REQ-1", "def add(a, b):")])["requirements"][0]
    assert out == {"id": "REQ-1", "title": "Add", "text": "Adds two numbers", "priority": "P1",
                   "source_file": "repo/app.py", "line_number": 1, "quote": "def add(a, b):"}


def test_write_refuses_escape():
    pid = _project("x = 1\n")
    with pytest.raises(Exception):
        pb.write(pid, "..", "../../escape.json", {})
    shutil.rmtree(project_dir(pid))


@pytest.mark.skipif(not node_ok, reason="Node 22.6+ is needed to run the plugin's TypeScript")
def test_check_gate_passes_real_quotes_and_flags_invented_ones():
    pid = _project("def add(a, b):\n    return a + b\n")
    app = pb.app_name(pid)
    pb.write(pid, app, "02-requirements/requirements.json", pb.requirements_file([_req("REQ-1", "def add(a, b):")]))
    good = pb.check_gate(pid, app, 1)
    assert good["error"] is None, good
    assert good["ok"] is True and good["gaps"] == [], good
    assert good["validator"]["ok"] is True, good["validator"]
    assert (project_dir(pid) / "docs" / "qe" / app / "coverage-map.md").is_file()

    pb.write(pid, app, "02-requirements/requirements.json",
             pb.requirements_file([_req("REQ-1", "def add(a, b):"), _req("REQ-2", "def delete_everything():")]))
    bad = pb.check_gate(pid, app, 1)
    assert bad["ok"] is False
    assert "REQ-2" in bad["missing"] and "REQ-1" not in bad["missing"], bad
    assert any("not found verbatim" in g for g in bad["gaps"])
    shutil.rmtree(project_dir(pid))


def test_check_gate_reports_when_node_is_missing(monkeypatch):
    monkeypatch.setattr(script_runtime, "plan", lambda *a, **k: script_runtime.Plan("typescript", None, "Node.js is not installed here"))
    out = pb.check_gate("p-none", "app", 1)
    assert out["ok"] is False and "Node.js is not installed" in out["error"]


def test_plan_file_maps_areas_to_plugin_scenarios():
    plan = {"strategy": "s", "areas": [{"id": "A1", "name": "Add", "requirement_ids": ["REQ-1"], "risk": "P0", "level": "Unit",
                                        "framework": "pytest", "rationale": "r"}], "skipped_levels": {"E2E": "No user interface exists"}}
    out = pb.plan_file(plan)
    assert out["scenarios"] == [{"id": "SC-A1-001", "area": "Add", "title": "Add", "level": "Unit", "priority": "P0", "requirementIds": ["REQ-1"]}]
    assert out["skippedLevels"] == [{"level": "E2E", "reason": "No user interface exists"}]
    assert pb.scenario_id("area 7/x") == "SC-AREA-7-X-001" and pb.scenario_id("--") == "SC-AREA-001"


@pytest.mark.skipif(not node_ok, reason="Node 22.6+ is needed to run the plugin's TypeScript")
def test_gate2_needs_every_level_or_a_real_reason():
    pid = _project("def add(a, b):\n    return a + b\n")
    app = pb.app_name(pid)
    pb.write(pid, app, "02-requirements/requirements.json", pb.requirements_file([_req("REQ-1", "def add(a, b):")]))
    area = {"id": "A1", "name": "Add", "requirement_ids": ["REQ-1"], "risk": "P1", "level": "Unit", "framework": "pytest", "rationale": "r"}
    pb.write(pid, app, "03-plan/plan.json", pb.plan_file({"strategy": "s", "areas": [area], "skipped_levels": {"Integration": "No IO", "E2E": "No UI"}}))
    short = pb.check_gate(pid, app, 2)
    assert short["ok"] is False and any("no Integration scenarios" in g for g in short["gaps"]), short
    reasons = {"Integration": "The function has no I/O or collaborators", "E2E": "There is no user interface or entry point"}
    pb.write(pid, app, "03-plan/plan.json", pb.plan_file({"strategy": "s", "areas": [area], "skipped_levels": reasons}))
    good = pb.check_gate(pid, app, 2)
    assert good["ok"] is True and good["gaps"] == [], good
    shutil.rmtree(project_dir(pid))
