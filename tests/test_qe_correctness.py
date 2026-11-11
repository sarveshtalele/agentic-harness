"""QE workflow correctness fixes from the Markdown-HTML-converter trace (docs/analysis/2026-11-11-markdown-html-converter-trace.md, bugs B1 to B18)."""

import json

import pytest
from pydantic import ValidationError

from backend.core import documents, gates
from backend.db import db
from backend.maf import engine, llm
from backend.maf.engine import add_event
from backend.maf.workflows.qe.generate.files import GeneratedFile, _generated_file_problems
from backend.qe import model, test_data, trace
from backend.qe.emit import subject

from tests.helpers_api import CASES, REQUIREMENTS, client, pending, project, upload_repo, wait_run  # noqa: F401 (client and project are fixtures)
from tests.helpers_confidence import CALC, base_rules, go_to_gate
from tests.scripted_client import ScriptedClient

STRING_REQ = {"id": "REQ-1", "title": "Heading", "statement": "converts a heading", "priority": "P1", "quote": "FR-001: headings become h1 to h6", "input_type": "string"}


def case(data, kind="Negative", requirement="REQ-1", scenario="bad input"):
    return {"id": "TC-1", "requirement_id": requirement, "scenario": scenario, "type": kind, "test_data": data}


# B17: an empty repository stops before Gate 0, with no model call


@pytest.mark.parametrize("entries", [None, {".gitkeep": ""}])
def test_qe_on_a_repository_with_no_code_stops_before_gate_0_without_a_model_call(client, project, entries):
    if entries:
        upload_repo(client, project, entries)
    scripted = ScriptedClient([])
    llm.set_client_override(scripted)
    run = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()["id"])
    assert run["status"] == "failed" and "No code to test" in run["error"] and scripted.calls == [], "no token is spent on code that does not exist"
    spec_first = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe", "input": {"spec_first": True}}).json()["id"])
    assert spec_first["status"] == "waiting_approval" and pending(spec_first)["gate"] == 0, "spec-first keeps the greenfield path"


# B6: a test that defines or stubs its own subject is refused


def problems(tmp_path, content):
    (tmp_path / "calc.py").write_text(CALC, encoding="utf-8")
    return _generated_file_problems(GeneratedFile(path="tests/agentic_qe/test_tc_app_001.py", case_ids=["TC-APP-001"], content=content), {"TC-APP-001"}, tmp_path)


HEAD = "# CASE_ID: TC-APP-001\n"


@pytest.mark.parametrize(("body", "said"), [
    ("def convert_markdown_to_html(text):\n    return '<h1>' + text + '</h1>'\n\n\ndef test_TC_APP_001():\n    assert convert_markdown_to_html('x') == '<h1>x</h1>'\n", "imports no code from the repository"),
    ("from calc import add\n\n\ndef add(a, b):\n    return a + b\n\n\ndef test_TC_APP_001():\n    assert add(2, 3) == 5\n", "replaces the repository's real add"),
    ("import calc\n\n\ndef test_TC_APP_001(monkeypatch):\n    monkeypatch.setattr(calc, 'add', lambda a, b: 5)\n    assert calc.add(2, 3) == 5\n", "replaces add from the repository with a stub"),
])
def test_a_test_that_defines_or_stubs_its_subject_is_refused(tmp_path, body, said):
    found = problems(tmp_path, HEAD + body)
    assert any(said in p for p in found), found


def test_a_test_of_the_real_code_has_no_subject_finding(tmp_path):
    body = HEAD + "from calc import add\n\n\ndef _pair():\n    return 2, 3\n\n\ndef test_TC_APP_001():\n    assert add(*_pair()) == 5\n"
    assert problems(tmp_path, body) == []
    (tmp_path / "tests/agentic_qe").mkdir(parents=True)
    (tmp_path / "tests/agentic_qe/test_tc_app_001.py").write_text(body, encoding="utf-8")
    (tmp_path / "tests/agentic_qe/test_tc_app_002.py").write_text(HEAD + "def add(a, b):\n    return a + b\n\n\ndef test_TC_APP_002():\n    assert add(2, 3) == 5\n", encoding="utf-8")
    assert subject.exercises_repository(tmp_path, "tests/agentic_qe/test_tc_app_001.py") and not subject.exercises_repository(tmp_path, "tests/agentic_qe/test_tc_app_002.py")


# B5: the fixture keys are named and a wrong one is refused


def test_reading_a_key_fixtures_json_does_not_have_is_refused(tmp_path):
    body = HEAD + "import json\nfrom pathlib import Path\nfrom calc import add\n\nDATA = json.loads((Path(__file__).parent / 'fixtures.json').read_text())\n\n\ndef test_TC_APP_001():\n    assert DATA['cases']['TC-APP-001']['test_data'] and add(2, 3) == 5\n"
    assert any("'test_data', which fixtures.json does not have" in p and '"data"' in p and '"uses"' in p for p in problems(tmp_path, body))
    assert problems(tmp_path, body.replace("['test_data']", "['data']")) == []


# B7: no real execution is INCONCLUSIVE


def matrix(*cells):
    return {"rows": [{"cases": [{"test_file": f, "result": r} for f, r in cells]}]}


def test_stub_only_or_greenfield_results_are_inconclusive():
    passes = matrix(("a.py", "passed"), ("b.py", "passed"), ("c.py", "passed"))
    assert "No code under test" in trace.no_product_run("greenfield", passes, {"a.py", "b.py", "c.py"}), "greenfield with 3 passes"
    assert "None of the 3 executed tests" in trace.no_product_run("brownfield", passes, set()), "every pass came from a test of its own stub"
    assert trace.no_product_run("brownfield", matrix(("a.py", "passed"), ("b.py", "failed")), {"b.py"}) == ""
    assert trace.no_product_run("brownfield", matrix(("a.py", "not run")), set()) == "", "nothing ran: the zero-execution rule decides"


# B1 and B3: Exception only on stated error behaviour; test data of the stated input type


@pytest.mark.parametrize("data", ["42", "None", "null", "input = 123 (integer)", "A Python list containing one element", "[1, 2]"])
def test_test_data_of_another_type_than_the_string_input_is_refused(data):
    found = model.case_problems([STRING_REQ], [case(data)])
    assert len(found) == 1 and "the requirement states its input type as string" in found[0][1]


def test_test_data_that_fits_or_is_allowed_is_kept():
    assert model.case_problems([STRING_REQ], [case("'# Title'"), case("####### Seven hashes"), case("")]) == []
    assert model.case_problems([{**STRING_REQ, "input_type": "number"}], [case("2, 3"), case("-1"), case("0.5")]) == []
    assert model.case_problems([{**STRING_REQ, "input_type": ""}], [case("42")]) == [], "no stated input type: nothing to check against"
    erring = {**STRING_REQ, "error_behaviour": "raises TypeError for a non-string"}
    assert model.case_problems([erring], [case("42", "Exception")]) == [], "a wrong type is allowed where the requirement states how it is handled"
    assert model.case_problems([STRING_REQ], [case("42", "Exception")]), "but not in an invented Exception case"


def test_every_case_needs_an_oracle_and_input_types_are_named_one_way():
    with pytest.raises(ValidationError):
        model.TestCase(id="T", requirement_id="R", scenario="s", type="Positive", level="Unit", steps=["a"], expected_result="returns 5")
    assert [model.Requirement(id="R", title="t", statement="s", input_type=t).input_type for t in ("str", "Markdown", "int", "dict", "weird", "")] == ["string", "string", "integer", "object", "", ""]


def test_a_case_of_the_wrong_type_is_revised_then_refused_at_gate_3(client, project):
    typed = json.loads(REQUIREMENTS)
    typed["requirements"][0]["input_type"] = "number"
    bad = json.loads(CASES)
    bad["cases"][1]["test_data"] = "'minus one'"
    designs = []
    rules = base_rules(designer=lambda t: (designs.append(t), json.dumps(bad))[1], extra=[("You are a requirements analyst", json.dumps(typed))])
    run, _ = go_to_gate(client, project, 3, rules)
    assert len(designs) == 2 and "a string, but the requirement states its input type as number" in designs[1], "sent back once with the reason"
    gaps = run["state"]["design_gaps"]
    assert any(g.startswith("refused REQ-001") for g in gaps) and "REQ-001: needs 2 Negative cases" in gaps and len(run["state"]["cases"]) == 3, "the refusal and the gap it opens are both named"
    assert "refused REQ-001" in pending(run)["summary"]
    assert "'minus one'" not in json.dumps(run["state"]["cases"])
    fixtures = client.get(f"/api/documents/{pending(run)['payload']['documents'][1]}").json()["data"]
    assert fixtures["cases"]["TC-APP-002"]["uses"] == ["boundary.number"] and list(fixtures["datasets"]["boundary"]) == ["number"], "B4: the boundary set follows the stated input type"


# B14, B15, B18


def test_a_reason_for_a_reject_decision_must_be_real():
    assert engine.weak_reason("a") and engine.weak_reason("ok fine") and engine.weak_reason("1234567890 !!") and engine.weak_reason("Gate 3: approve test design", "Gate 3: approve test design")
    assert engine.weak_reason("Known defect, tracked") == ""


def test_approving_reject_items_with_a_one_letter_reason_is_refused(client, project):
    always = lambda kind, key: {"scores": {"source_proven": 5, "correct_target": 10, "expected_derivable": 10, "fixture_validity": 5}} if kind == "design" and key == "C2" else None
    run, _ = go_to_gate(client, project, 3, base_rules(grade=always, extra=[("Rewrite only this one test case", lambda t: "I cannot")]))
    refused = client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": True, "feedback": "a"})
    assert refused.status_code == 400 and "fewer than 10" in refused.text
    sent_back = client.post(f"/api/approvals/{pending(run)['id']}/decide", json={"approved": False, "feedback": "no"})
    assert sent_back.status_code == 400 and "Rejecting gate 3" in sent_back.text


def test_gates_3_to_5_approve_the_documents_they_cover(client, project):
    pid = project["id"]
    made = {kind: documents.create(pid, kind, kind, "body", "system", data=[])["id"] for kind in ("test_cases", "test_data", "test_code", "release", "traceability", "defect_report")}
    for number in range(6):
        gates.decide(pid, number, True, "Ann Reviewer", "checked by a human")
    assert {kind: documents.get(i)["status"] for kind, i in made.items()} == dict.fromkeys(made, "approved")


def test_run_event_data_is_redacted_like_the_message(client, project):
    llm.set_client_override(ScriptedClient([]))
    run_id = wait_run(client, client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "qe"}).json()["id"])["id"]
    secret = "sk-" + "b" * 32
    add_event(run_id, "log", "", f"key {secret}", {"nested": [{"token": secret}], "password": "hunter2-long-pass"})
    with db() as con:
        message, data = con.execute("SELECT message, data FROM run_events WHERE run_id=? ORDER BY seq DESC LIMIT 1", (run_id,)).fetchone()
    assert secret not in message and secret not in data and json.loads(data)["nested"][0]["token"] != secret
    assert json.loads(data)["password"] == "***", "a login field is masked in data as it is in a message"
