"""Plugin skills on MAF: skill evals, the API and its access rule, and the Azure package."""
import json
import os
import subprocess
import sys
import zipfile

from backend.core import auth
from backend.core import skills as skill_lib
from backend.maf import evals, llm
from tests.scripted_client import ScriptedClient
from tests.helpers_api import USER_PASSWORD, client, make_user, project, sign_in, unique  # noqa: F401 - fixtures
from tests.helpers_skills import ARCHITECT, EXPECTED, ROOT


# ---- evals ------------------------------------------------------------------------------

def test_converted_checks_belong_to_real_plugin_cases():
    overlay = json.loads((ROOT / "evals/skills/checks.json").read_text(encoding="utf-8"))
    for name, queries in ((k, v) for k, v in overlay.items() if not k.startswith("_")):
        known = {case["query"] for case in skill_lib.eval_cases(name)}
        assert set(queries) <= known, f"{name} has checks for a query the plugin does not have"
        for rules in queries.values():
            assert evals.build_checks(rules), "a converted case has at least one real check"
    total = sum(len(skill_lib.eval_cases(n)) for n in skill_lib.names())
    converted = sum(len(q) for k, q in overlay.items() if not k.startswith("_"))
    assert total >= 33 and converted == 5, "only what code can literally check was converted"


def test_skill_cases_run_with_their_skill_and_ungradable_ones_are_not_scored(client):
    scripted = ScriptedClient([("Plan tests for the approved requirements", "Unit tests for logic, Integration for services."), (ARCHITECT, '{"strategy": "x", "areas": [], "skipped_levels": {}}')])
    llm.set_client_override(scripted)
    result = client.post("/api/agents/principal-test-architect/evals").json()
    skill_results = [r for r in result["results"] if r["skill"] == "planning-tests"]
    assert [r["passed"] for r in skill_results] == [False, None, None], "the reply never says API, so the one coded case fails; the others are not scored"
    assert skill_results[0]["failed_checks"] == ["contains:API"] and skill_results[1]["status"] == "needs_grader" and skill_results[1]["expected_behavior"]
    assert skill_results[0]["ungraded_expectations"], "the plugin's sentences are kept and marked as not graded"
    assert result["needs_grader"] == 2 and result["total"] == len(result["results"]) - 2
    asked = [c for c in scripted.calls if "Plan tests for the approved requirements" in c]
    assert len(asked) == 1 and '<skill name="planning-tests"' in asked[0], "the case runs with its skill"
    assert not any("Plan tests but there are no approved requirements" in c for c in scripted.calls), "a case that needs a grader never calls the model"
    plain = [c for c in scripted.calls if "Plan tests for the approved requirements" not in c]
    assert plain and not any("<skill name=" in c for c in plain), "the original cases still measure the prompt alone"
    llm.set_client_override(ScriptedClient([("Plan tests for the approved requirements", "Unit, Integration and API levels"), (ARCHITECT, '{"strategy": "x", "areas": [], "skipped_levels": {}}')]))
    better = client.post("/api/agents/principal-test-architect/evals").json()
    assert [r["passed"] for r in better["results"] if r["skill"]] == [True, None, None]


def test_the_matches_rule_is_a_real_regex_check(client):
    document = "## Scope\n## Functional Requirements\nFR-001 Reset link valid for 30 minutes\n## Open Questions\n"
    feature = "Feature: Login\n\n  @FR-001 @FR-002\n  Scenario: Sign in\n    Given a member\n    When they sign in\n    Then they see home\n"
    llm.set_client_override(ScriptedClient([("Convert into a Gherkin feature", feature), ("Write the document", document), ("web calculator", "Given, When, Then, Exception, but no story in the required form")]))
    result = client.post("/api/agents/business-analyst/evals").json()
    skill_case = next(r for r in result["results"] if r["skill"] and r["passed"] is not None)
    assert skill_case["passed"] is False and any(name.startswith("matches:") for name in skill_case["failed_checks"])


# ---- the API and its access rule ----------------------------------------------------------

def test_skills_api_is_read_only_for_any_signed_in_account(client):
    listed = client.get("/api/skills").json()
    assert EXPECTED.issubset({s["name"] for s in listed["skills"]}) and listed["problems"] == []
    planning = next(s for s in listed["skills"] if s["name"] == "planning-tests")
    assert planning["agents"] == ["principal-test-architect"] and planning["references"] == ["LEVEL_GUIDELINES.md"] and planning["description"] and planning["version"] == "1.4.0"
    detail = client.get("/api/skills/planning-tests").json()
    assert detail["body"].startswith("# Planning Tests") and "LEVEL_GUIDELINES.md" in detail["reference_text"]
    assert client.get("/api/skills/nope").status_code == 404
    name = unique("reader")
    make_user(client, name)
    for role_account, kind in ((name, "developer"),):
        other, _ = sign_in(role_account)
        assert other.get("/api/skills").status_code == 200 and other.get("/api/skills/planning-tests").status_code == 200
        assert other.post("/api/skills", json={}).status_code == 405 and other.delete("/api/skills/planning-tests").status_code == 405, kind
    from fastapi.testclient import TestClient

    from backend.app import app

    assert TestClient(app).get("/api/skills").status_code == 401
    viewer = {"id": "usr_v", "role": "user", "account_role": "viewer"}
    assert auth.rule_of("/api/skills") == "session" and auth.rule_of("/api/skills/planning-tests") == "session"
    assert auth.access_problem("GET", "/api/skills/planning-tests", viewer) is None


# ---- the Azure package -----------------------------------------------------------------------

def test_the_backend_package_holds_skills_that_load_from_the_configured_folder(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("package_azure", ROOT / "scripts/package_azure.py")
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    entries = package.backend_entries()
    for needed in ("skills/planning-tests/SKILL.md", "skills/planning-tests/references/LEVEL_GUIDELINES.md", "skills/generating-test-code/assets/playwright.config.ts", "skills/healing-tests/evals/evals.json"):
        assert needed in entries, f"{needed} is not in the backend ZIP"
    assert EXPECTED.issubset({n.split("/")[1] for n in entries if n.startswith("skills/") and n.endswith("/SKILL.md")})
    archive = tmp_path / "backend.zip"
    with zipfile.ZipFile(archive, "w") as bundle:  # the same entries the script writes
        for name, source in entries.items():
            bundle.write(source, name)
    unpacked = tmp_path / "unpacked"
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(unpacked)
    env = {**os.environ, "ATLAS_DATA_DIR": str(tmp_path / "data"), "ATLAS_SKILLS_DIR": str(unpacked / "skills"), "PYTHONPATH": str(unpacked / "src")}
    code = "from backend.core import skills\nprint(len(skills.load()), len(skills.problems()), skills.get('planning-tests').version)"
    out = subprocess.run([sys.executable, "-c", code], env=env, cwd=unpacked, capture_output=True, text=True, timeout=120)
    tokens = out.stdout.split()[-3:]
    assert int(tokens[0]) >= 13 and tokens[1:] == ["0", "1.4.0"], out.stderr[-500:]
