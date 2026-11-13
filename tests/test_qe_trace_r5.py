"""R5 traceability view (docs/PHASE2_PLAN.md 12.5): read from the agentic-qe plugin's coverage-map.json in the workspace,
gaps first, with each requirement's quoted source and the run's evidence; files open read-only, never as HTML."""
import json

from backend.api import qe_trace
from tests.helpers_api import client, project  # noqa: F401 - fixtures

COVERAGE = {"app": "shop", "approvedUpTo": 4, "checks": [{"gate": 5, "ok": False, "gaps": ["REQ-2 has no passing test"]}], "coverage": {
    "requirements": [{"id": "REQ-1", "priority": "P0", "evidence": True, "quoteFound": True, "text": "Refunds above 500 EUR need approval"},
                     {"id": "REQ-2", "priority": "P1", "evidence": True, "quoteFound": False, "text": "Refunds after 30 days are refused"}],
    "scenarios": [{"id": "SC-API-001", "area": "API", "level": "Integration", "requirementIds": ["REQ-1"], "text": "approval"}],
    "cases": [{"id": "TC-001", "scenarioIds": ["SC-API-001"], "level": "Integration", "confidence": True, "text": "approve"}],
    "tests": [{"path": "tests/test_refund.py", "caseIds": ["TC-001"], "exists": True, "markers": ["TC-001"], "tests": 1, "assertions": 2}],
    "results": {"TC-001": "passed"}, "problems": []}}


def test_the_trace_reads_the_plugins_coverage_map_gaps_first(client, project, tmp_path, monkeypatch):
    monkeypatch.setattr(qe_trace, "sandbox_dir", lambda _: tmp_path)
    assert client.get(f"/api/projects/{project['id']}/qe/trace").json()["apps"] == []  # nothing invented before a run
    app = tmp_path / "docs" / "qe" / "shop"
    (app / "02-requirements").mkdir(parents=True)
    (app / "06-execution" / "evidence").mkdir(parents=True)
    (app / "coverage-map.json").write_text(json.dumps(COVERAGE), encoding="utf-8")
    (app / "02-requirements" / "requirements.json").write_text(json.dumps({"requirements": [
        {"id": "REQ-1", "source_file": "app/refunds.py", "line_number": 12, "quote": "if amount > 500:"}]}), encoding="utf-8")
    (app / "06-execution" / "junit.xml").write_text("<testsuite/>", encoding="utf-8")
    (app / "06-execution" / "evidence" / "page.html").write_text("<script>alert(1)</script>", encoding="utf-8")
    shown = client.get(f"/api/projects/{project['id']}/qe/trace").json()["apps"][0]
    assert [r["id"] for r in shown["rows"]] == ["REQ-2", "REQ-1"] and shown["rows"][0]["gap"] == "no scenario"  # the gap comes first
    covered = shown["rows"][1]
    assert covered["gap"] == "" and covered["cases"] == [{"case_id": "TC-001", "level": "Integration", "tests": ["tests/test_refund.py"], "result": "passed"}]
    assert covered["source"] == {"file": "app/refunds.py", "line": 12, "quote": "if amount > 500:"}
    assert shown["checks"][0]["gaps"] == ["REQ-2 has no passing test"] and "docs/qe/shop/06-execution/junit.xml" in shown["evidence"]
    page = client.get(f"/api/projects/{project['id']}/qe/file", params={"path": "docs/qe/shop/06-execution/evidence/page.html"})
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/plain")  # repository content is never run
    assert client.get(f"/api/projects/{project['id']}/qe/file", params={"path": "../../etc/passwd"}).status_code == 400
