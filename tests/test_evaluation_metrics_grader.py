"""Evaluation metrics: the grader for plugin skill cases."""
import asyncio
import json

from backend.maf import evals, llm
from backend.maf.evals import grader
from tests.scripted_client import ScriptedClient
from tests.helpers_api import client, project  # noqa: F401 - fixtures


# ---- the grader for plugin skill cases -----------------------------------------------------------------------------

def test_grader_evidence_that_is_not_in_the_output_is_a_fail():
    output = "Unit tests cover the logic.   Integration tests cover the API."
    grades = [grader.Grade(expectation="a", verdict="PASS", evidence="unit tests cover the logic."),
              grader.Grade(expectation="b", verdict="PASS", evidence="Contract tests cover the service."),
              grader.Grade(expectation="c", verdict="PASS", evidence="")]
    got = grader.verify(output, ["a", "b", "c", "d"], grades)
    assert [g["verdict"] for g in got] == ["PASS", "FAIL", "FAIL", "FAIL"]
    assert got[1]["reason"] == "Evidence not found in the output" and got[2]["reason"] == "No evidence was quoted" and "no grade" in got[3]["reason"]


def judge_reply(evidence):
    def reply(text):
        block = text.split("EXPECTATIONS, in order:\n")[1].split("\n\nGive one grade")[0]
        listed = [line.split(". ", 1)[1] for line in block.splitlines()]
        return json.dumps({"grades": [{"expectation": e, "verdict": "PASS", "evidence": evidence, "reason": "r"} for e in listed]})
    return reply


def test_skill_cases_stay_needs_grader_without_a_judge_and_are_graded_with_one(client, monkeypatch):
    monkeypatch.delenv("ATLAS_EVAL_MODEL", raising=False)
    architect = "You are a principal test architect"
    agent_says = "Unit tests for the logic and Integration tests for the services."
    llm.set_client_override(ScriptedClient([("Plan tests", agent_says), (architect, '{"strategy": "x", "areas": [], "skipped_levels": {}}'), ("Save the test plan", agent_says)]))
    without = asyncio.run(evals._run_case("principal-test-architect", evals.skill_cases("principal-test-architect")[1]))
    assert without["passed"] is None and without["status"] == "needs_grader"
    monkeypatch.setenv("ATLAS_EVAL_MODEL", "judge-model")
    real = ScriptedClient([("You grade an AI agent's output", judge_reply("Unit tests for the logic")), ("Plan tests", agent_says), (architect, '{"strategy": "x", "areas": [], "skipped_levels": {}}')])
    llm.set_client_override(real)
    graded = asyncio.run(evals._run_case("principal-test-architect", evals.skill_cases("principal-test-architect")[1]))
    assert graded["passed"] is True and graded["status"] == "graded" and graded["judge_model"] == "judge-model" and graded["tokens"] > 0
    assert all(g["evidence"] for g in graded["grades"])
    llm.set_client_override(ScriptedClient([("You grade an AI agent's output", judge_reply("Words the agent never wrote")), ("Plan tests", agent_says), (architect, '{"strategy": "x", "areas": [], "skipped_levels": {}}')]))
    invented = asyncio.run(evals._run_case("principal-test-architect", evals.skill_cases("principal-test-architect")[1]))
    assert invented["passed"] is False and any("Evidence not found" in g["reason"] for g in invented["grades"])
