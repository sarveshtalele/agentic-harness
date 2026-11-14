"""QE v2 step 5: a greenfield QE run reads the uploaded documents through search; every requirement quote is checked on disk, and the plugin's Gates 1 to 3 apply."""
import json
from pathlib import Path

from backend.config import project_dir, sandbox_dir
from backend.core import documents
from backend.maf import engine, llm
from backend.qe import plugin_bridge
from tests.helpers_api import client, pending, project, wait_run  # noqa: F401 - fixtures
from tests.reviewing import rules as case_rules
from tests.scripted_client import ScriptedClient

SAMPLE = Path(__file__).parent.parent / "docs" / "samples" / "task-tracker-brd.md"
QUOTES = {  # exact lines of the sample BRD, one per requirement
    "REQ-001": ('The title is required, is trimmed of leading and trailing spaces, and must be 1 to 120 characters after trimming.', "422", "title must be 1 to 120 characters"),
    "REQ-002": ('Completing a task that is already done answers HTTP 409 with the message "task is already done".', "409", "task is already done"),
    "REQ-003": ('Completing or deleting a task id that does not exist answers HTTP 404 with the message "task not found".', "404", "task not found"),
}
INVENTED = "Every team member must sign in with a password before using the API."  # the BRD says the opposite: no sign-in in 1.0


def requirements_reply(source_path: str):
    def reply(text: str) -> str:
        assert "DOCUMENT CHUNKS" in text and source_path in text and "is already done" in text, "the analyst gets retrieved chunks with their file path, not whole documents"
        assert "APPROVED DOCUMENTS" not in text
        items = [{"id": i, "title": f"Rule {i}", "statement": q[0], "priority": "P0", "tier": "specified", "actor": "customer", "file": source_path, "line": 1, "quote": q[0],
                  "section": "Team Task Tracker > 3. Functional requirements", "error_behaviour": f"rejects with HTTP {q[1]}"} for i, q in QUOTES.items()]
        items.append({"id": "REQ-004", "title": "Sign in", "statement": INVENTED, "priority": "P0", "tier": "specified", "file": source_path, "line": 3, "quote": INVENTED})
        return json.dumps({"requirements": items})
    return reply


PLAN = json.dumps({"strategy": "API rules at unit level", "areas": [{"id": "A1", "name": "Task rules", "requirement_ids": list(QUOTES), "risk": "P0", "level": "Unit", "framework": "pytest", "rationale": "Pure rules"}],
                   "skipped_levels": {"Integration": "No database in version 1.0, tasks live in memory", "E2E": "The web page is covered by the later app build"}})


def cases() -> str:
    out = []
    for n, (rid, (_, status, message)) in enumerate(QUOTES.items(), 1):
        for kind, level_type in (("Positive", "Positive"), ("Negative", "Negative"), ("Boundary", "Negative (Boundary)"), ("Exception", "Exception")):
            out.append({"id": f"TC-TASK-{n}{kind[0]}", "requirement_id": rid, "scenario": f"{rid} {kind}", "type": level_type, "level": "Unit", "steps": [f"call the API for {rid}"],
                        "expected_result": f"answers HTTP {status} with the message '{message}'" if kind != "Positive" else "the API accepts the request", "oracle": "specified", "test_data": "title: 'x'"})
    return json.dumps({"cases": out})


def upload(client, project):
    done = client.post(f"/api/projects/{project['id']}/rag/documents", files=[("files", ("task-tracker-brd.md", SAMPLE.read_bytes(), "text/markdown"))])
    assert done.status_code == 201, done.text
    return done.json()["indexed"][0]


def test_greenfield_from_an_uploaded_brd_to_gate_3_cites_quotes_and_runs_the_plugin_checks(client, project):
    saved = upload(client, project)
    source = saved["source_path"]
    text = (sandbox_dir(project["id"]) / source).read_text(encoding="utf-8")
    scripted = ScriptedClient([
        ("TASK: RANK", '{"ids": []}'), ("You are a repository intelligence analyst", "## Purpose\nNo code yet"), ("You are a requirements analyst", requirements_reply(source)),
        ("You are a principal test architect", PLAN), *case_rules(), ("Score this requirements from the evidence", '{"score": 95, "verdict": "APPROVED", "issues": []}'),
        ("You are an independent reviewer", '{"score": 95, "verdict": "APPROVED", "issues": []}'), ("You are a test design architect", cases())])
    llm.set_client_override(scripted)
    run = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()  # no spec_first: the indexed document is enough
    seen = []
    for _ in range(4):
        run = wait_run(client, run["id"], timeout=120)
        assert run["status"] == "waiting_approval", run["error"]
        approval = pending(run)
        seen.append(approval["gate"])
        payload = approval["payload"]
        if approval["gate"] == 0:
            assert "task-tracker-brd.md v1" in approval["summary"] and "keyword only" in approval["summary"], approval["summary"]
            assert [d["doc_id"] for d in payload["sources"]] == [saved["doc_id"]] and payload["search"]["vector"] is False
        if approval["gate"] == 1:
            reqs = documents.get(payload["documents"][-1])["data"]
            assert [r["id"] for r in reqs] == list(QUOTES), "the invented sign-in requirement was dropped"
            for r in reqs:
                assert r["file"] == source and r["quote"] in text and r["section"] and r["tier"] == "specified"
                assert r["line"] == text.count("\n", 0, text.find(r["quote"])) + 1 and text.splitlines()[r["line"] - 1].count(r["quote"]) == 1
            check = payload["plugin_check"]
            assert check["error"] is None and check["ok"] is True and check["dropped"] == [], check
            assert "agentic-qe Gate 1 check: PASS." in approval["summary"] and "not applied" not in approval["summary"]
            written = json.loads((project_dir(project["id"]) / "docs" / "qe" / check["app"] / "02-requirements" / "requirements.json").read_text(encoding="utf-8"))
            assert {r["source_file"] for r in written["requirements"]} == {f"sandbox/{source}"}
            assert any("3 requirements verified; 1 dropped for missing evidence" in e["message"] for e in engine.events(run["id"]))
            assert any("DOCUMENT CHUNKS" in c for c in scripted.calls)
        if approval["gate"] in (2, 3):
            check = payload["plugin_check"]
            assert check is not None and check["ok"] is not None and check["error"] is None, check  # applied, not skipped
            assert f"agentic-qe Gate {approval['gate']} check" in approval["summary"] and "not applied" not in approval["summary"]
            assert payload["trace"]["verdict"] == "PASS", payload["trace"]
        if approval["gate"] == 3:
            found = documents.get(payload["documents"][-1])["data"]
            assert payload["design_audit"]["counts"]["COVERS"] == len(found["cases"]) == 12 and payload["design_audit"]["unaudited"] == []
            assert not [g for g in check["gaps"] if "quote" in g or "evidence" in g], check["gaps"]
            break
        assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True, "feedback": "ok"}).status_code == 200
    assert seen == [0, 1, 2, 3]


def test_the_plugin_gate_1_check_reads_the_saved_document_and_flags_a_quote_that_is_not_in_it(client, project):
    saved = upload(client, project)
    app = plugin_bridge.app_name(project["id"])
    good = {"id": "REQ-001", "title": "t", "statement": "s", "priority": "P0", "file": saved["source_path"], "line": 1, "quote": QUOTES["REQ-002"][0]}
    for requirement, flagged in ((good, []), ({**good, "quote": INVENTED}, ["REQ-001"])):
        plugin_bridge.write(project["id"], app, "02-requirements/requirements.json", plugin_bridge.requirements_file([requirement]))
        check = plugin_bridge.check_gate(project["id"], app, 1)
        assert check["error"] is None and check["missing"] == flagged and check["ok"] is (not flagged), check


def test_a_greenfield_run_without_a_document_still_stops_before_gate_0(client, project):
    scripted = ScriptedClient([])
    llm.set_client_override(scripted)
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()["id"])
    assert run["status"] == "failed" and "No code to test" in run["error"] and scripted.calls == []
