"""The case budget before design."""

import json
import re

import pytest

from backend.maf.workflows import qe, shared
from backend.qe import model

from tests.helpers_api import pending
from tests.helpers_confidence import base_rules, go_to_gate


KINDS = ["Positive", "Negative", "Negative (Boundary)", "Exception"]


def req(i, priority):
    return {"id": i, "title": i, "statement": "add returns the sum", "priority": priority, "tier": "observed", "file": "calc.py", "line": 2, "quote": "return a + b"}


def reqs(*pairs):
    return [req(f"REQ-{n:03d}", p) for n, p in enumerate(pairs, 1)]


# the quota table


@pytest.mark.parametrize(("priorities", "limit", "quota", "left", "over"), [
    (["P0", "P1", "P2", "P2"], 60, [4, 4, 2, 2], [], False),
    (["P1"] * 5 + ["P2"] * 2, 24, [4] * 5 + [2, 2], [], False),  # exactly the limit
    (["P1"] * 5 + ["P2"] * 2, 22, [4] * 5 + [1, 1], [], False),  # exactly the limit with one case each
    (["P1"] * 5 + ["P2"] * 2, 23, [4] * 5 + [1, 1], [], False),  # 2 each does not fit, so 1 each
    (["P0", "P0", "P0"], 8, [4, 4, 4], [], True),  # P0 alone passes the limit and is still designed
    (["P0", "P1", "P2", "P2"], 8, [4, 4], ["REQ-003", "REQ-004"], False),  # no room: named
    (["P1", "P1", "P2", "P2", "P2", "P2", "P2"], 11, [4, 4, 1, 1, 1], ["REQ-006", "REQ-007"], False),  # some get 1, the rest are named
    (["P0", "P0", "P2"], 7, [4, 4], ["REQ-003"], True),
    (["P2", "P2", "P2"], 6, [2, 2, 2], [], False),
    ([], 60, [], [], False),
])
def test_quota_table(priorities, limit, quota, left, over):
    result = model.case_quota(reqs(*priorities), limit)
    assert list(result["quota"].values()) == quota and result["left_out_requirements"] == left and result["p0_over_limit"] is over
    assert result["planned"] == sum(quota) and (result["planned"] <= limit or over)
    assert all(i in result["message"] for i in left)
    assert model.case_quota(reqs(*priorities), limit) == result, "deterministic"


def test_a_cut_keeps_the_plugins_required_kinds_first():
    case = lambda n, kind: {"requirement_id": "R", "type": kind, "scenario": str(n)}
    cases = [case(1, "Positive"), case(2, "Positive"), case(3, "Positive"), case(4, "Negative"), case(5, "Negative (Boundary)"), case(6, "Negative"), case(7, "Exception")]
    states_error = [{"id": "R", "error_behaviour": "raises TypeError for a non-number"}]
    kept, dropped = model.apply_quota(cases, {"R": 4}, states_error)
    assert sorted(c["type"] for c in kept) == ["Exception", "Negative", "Negative (Boundary)", "Positive"] and len(dropped) == 3
    kept, dropped = model.apply_quota(cases, {"R": 4}, [{"id": "R", "quote": "return a + b"}])
    assert sorted(c["type"] for c in kept) == ["Negative", "Negative", "Negative (Boundary)", "Positive"] and len(dropped) == 3, "no error behaviour stated: a third Negative, not an Exception"
    assert model.apply_quota(cases, {"R": 2})[0] == cases[:2] or len(model.apply_quota(cases, {"R": 2})[0]) == 2
    assert model.apply_quota(cases, {})[0] == [], "a requirement with no quota gets no cases"


# the workflow


def requirement_rules(items, planned=None):
    ids = planned or [r["id"] for r in items]
    plan = {"strategy": "Unit first", "areas": [{"id": "A1", "name": "Add", "requirement_ids": ids, "risk": "P1", "level": "Unit", "framework": "pytest", "rationale": "Pure logic"}], "skipped_levels": {"Integration": "No IO", "E2E": "No UI"}}
    return [("You are a requirements analyst", json.dumps({"requirements": items})), ("You are a principal test architect", json.dumps(plan))]


def designer(per_requirement, prompts):
    def reply(text):
        prompts.append(text)
        wanted = re.findall(r'"id": "(REQ-\d+)"', text.rsplit("REQUIREMENTS:", 1)[-1].split("CASE QUOTA")[0])
        return json.dumps({"cases": [{"id": f"x{n}", "requirement_id": r, "scenario": f"{r} scenario {n}", "type": KINDS[n % 4], "level": "Unit", "steps": ["call add"], "expected_result": "returns the sum 2", "oracle": "specified"}
                                     for r in wanted for n in range(per_requirement)]})
    return reply


def test_the_prompt_carries_the_quota_and_an_excess_case_is_dropped_before_review(client, project):
    prompts, seen = [], []
    items = reqs("P1", "P2")
    run, _ = go_to_gate(client, project, 3, base_rules(designer=designer(6, prompts), seen=seen, extra=requirement_rules(items)))
    assert "REQ-001: 4, REQ-002: 2" in prompts[0] and "at most this many cases" in prompts[0]
    reviewed = [key for kind, keys, _ in seen if kind == "design" for key in keys]
    assert len(reviewed) == 6, "only the cases within the quota were reviewed"
    payload = pending(run)["payload"]
    limit = payload["case_limit"]
    assert len(limit["dropped_over_quota"]) == 6 and "6 excess cases dropped before review" in limit["message"] and payload["confidence"]["counts"]["cases"] == 6
    assert limit["quota"] == {"REQ-001": 4, "REQ-002": 2} and not limit["left_out_requirements"] and limit["left_out"] == []


def test_low_priority_requirements_with_no_budget_are_named_before_any_design_call(client, project, monkeypatch):
    monkeypatch.setattr(qe, "MAX_CASES", 9)
    prompts = []
    run, _ = go_to_gate(client, project, 3, base_rules(designer=designer(4, prompts), extra=requirement_rules(reqs("P1", "P1", "P2", "P2"), planned=["REQ-001", "REQ-002", "REQ-003"])))
    assert prompts and not any("REQ-004" in p.rsplit("REQUIREMENTS:", 1)[-1].split("PLAN:")[0] for p in prompts), "no tokens were spent on the requirement that was left out"
    limit = pending(run)["payload"]["case_limit"]
    assert limit["left_out_requirements"] == ["REQ-004"] and limit["quota"]["REQ-003"] == 1 and "REQ-004" in limit["requirements_without_cases"]
    assert "REQ-004" in pending(run)["summary"]


def test_p0_over_the_limit_is_still_designed_and_said_openly(client, project, monkeypatch):
    monkeypatch.setattr(qe, "MAX_CASES", 3)
    run, _ = go_to_gate(client, project, 3, base_rules(designer=designer(4, []), extra=requirement_rules(reqs("P0", "P0"))))
    payload = pending(run)["payload"]
    assert payload["case_limit"]["p0_over_limit"] and payload["case_limit"]["left_out_count"] == 0 and payload["confidence"]["counts"]["cases"] == 8
    assert "exceeded" in payload["case_limit"]["message"]


def test_gap_revision_obeys_the_quota(client, project):
    prompts = []
    first = designer(4, prompts)
    state = {"n": 0}

    def reply(text):
        state["n"] += 1
        if state["n"] == 1:  # the first set has only one Negative case, so the checks send it back
            out = json.loads(first(text))
            for c in out["cases"]:
                c["type"] = "Positive" if c["type"] == "Negative (Boundary)" else c["type"]
                c["scenario"] += " first"
            return json.dumps(out)
        out = json.loads(first(text))
        out["cases"] = out["cases"] * 2  # a revision that ignores the quota
        for n, c in enumerate(out["cases"]):
            c["scenario"] = f"again {n}"
        return json.dumps(out)

    run, _ = go_to_gate(client, project, 3, base_rules(designer=reply, extra=requirement_rules(reqs("P1"))))
    assert state["n"] == 2 and any("Gaps:" in p for p in prompts) and "within the case quota" in prompts[-1]
    payload = pending(run)["payload"]
    assert payload["confidence"]["counts"]["cases"] == 4 and payload["case_limit"]["dropped_over_quota"] and not pending(run)["payload"].get("partial")


# evidence per review batch


def test_review_evidence_holds_only_the_batch_requirements_and_is_capped(tmp_path):
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text("\n".join(f"value_{name[0]}_{n} = {n}" for n in range(1, 801)), encoding="utf-8")
    one = {"id": "REQ-A", "priority": "P1", "statement": "A works", "file": "a.py", "line": 400, "quote": "value_a_400 = 400"}
    two = {"id": "REQ-B", "priority": "P1", "statement": "B works", "file": "b.py", "line": 10, "quote": "value_b_10 = 10"}
    text = shared.review_evidence("none", [one], tmp_path)
    assert "REQ-A" in text and "400: value_a_400 = 400" in text and "REQ-B" not in text and "b.py" not in text
    assert "100: value_a_100" not in text, "only the lines near the citation"
    assert len(text) <= shared.REVIEW_EVIDENCE_CHARS < len(shared.code_pack("none", tmp_path, ["a.py"]))
    many = [{**one, "id": f"REQ-{n}", "line": 1 + n * 20, "statement": "x" * 300} for n in range(60)]
    assert len(shared.review_evidence("none", many, tmp_path)) <= shared.REVIEW_EVIDENCE_CHARS
    assert "REQ-B" in shared.review_evidence("none", [one, two], tmp_path)


def test_each_design_review_batch_sees_only_its_own_requirements(client, project):
    seen = []
    items = reqs("P1", "P1", "P1", "P1", "P1")  # five requirements make two design batches of four and one
    run, _ = go_to_gate(client, project, 3, base_rules(designer=designer(4, []), seen=seen, extra=requirement_rules(items)))
    evidence = {tuple(keys): text.split("EVIDENCE:", 1)[1] for kind, keys, text in seen if kind == "design"}
    assert len(evidence) >= 2
    for text in evidence.values():
        assert len(text) <= shared.REVIEW_EVIDENCE_CHARS + 200
    last = next(text for text in evidence.values() if "REQ-005" in text)
    assert "REQ-001" not in last and "REQ-004" not in last
    first = next(text for text in evidence.values() if "REQ-001" in text)
    assert "REQ-005" not in first



def test_a_planned_low_priority_requirement_still_gets_one_case():
    rs = [{"id": f"R{i}", "priority": "P0"} for i in range(10)] + [{"id": "LOW", "priority": "P2"}]
    assert "LOW" not in model.case_quota(rs, 40)["quota"]
    planned = model.case_quota(rs, 40, {"LOW"})
    assert planned["quota"]["LOW"] == 1 and planned["left_out_requirements"] == []
