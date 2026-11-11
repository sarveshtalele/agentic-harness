"""Running one eval case against the real active prompt, and scoring its reply."""
from __future__ import annotations

from agent_framework import LocalEvaluator, evaluate_agent, evaluator
from pydantic import ValidationError

from backend.core.errors import classify
from backend.core.security import redact
from backend.db import db, now
from backend.maf import runtime as agents
from backend.maf.evals import grader, metrics, ragas_evaluator
from backend.maf.evals.cases import BENCH_DIR
from backend.maf.evals.checks import _schemas, build_checks

EVAL_PROJECT = "prj_agent_evals"
KEY_METRICS = ("precision", "recall", "f1")
STORED_TEXT = 6000  # characters of context and answer kept per case


def _sandbox() -> None:
    """Evals run in a hidden, archived project, so they cannot touch real project data."""
    with db() as con:
        con.execute("INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived) VALUES (?,?,?,?,?,1)",
                    (EVAL_PROJECT, "Agent evals", "Isolated project for agent evaluations", now(), now()))


def _find_items(answer: str, key: dict) -> list[dict]:
    found = agents.extract_json(answer)
    items = found.get(key.get("list", ""), []) if isinstance(found, dict) else found
    return [i if isinstance(i, dict) else {"text": str(i)} for i in items]


def _key_counts(answer: str, key: dict) -> dict:
    """Precision, recall, and F1 inputs for one case. A reply that is not JSON has every key item missed and nothing found."""
    if key.get("match") == "contains":
        return metrics.coverage(answer, key["items"])
    try:
        items = _find_items(answer, key)
    except (ValueError, AttributeError):
        items = []
    same = metrics.at_location if key.get("match") == "location" else metrics.has_keywords
    return metrics.match(items, key["items"], same)


async def _run_case(agent_key: str, case: dict) -> dict:
    _sandbox()  # every case runs in the eval project, whoever calls it
    case = {"checks": None, **case}
    if "skill" in case and not case["checks"]:  # nothing code can check: a judge grades it, and without one it stays unrun
        judge = ragas_evaluator.judge_model()
        if not judge or not case["expected_behavior"]:
            return {"name": case["name"], "category": "skill", "skill": case["skill"], "passed": None, "status": "needs_grader", "failed_checks": [], "expected_behavior": case["expected_behavior"]}
        return await _graded_skill_case(agent_key, case, judge)
    # existing cases measure the prompt alone, so they send no skill; a skill case sends exactly its skill
    call = agents.AgentCall(None, EVAL_PROJECT, agent_key, source="eval", skills=(case["skill"],) if "skill" in case else ())
    checks = case["checks"] or {}
    context = case.get("context", "")
    try:
        schema = _schemas().get(checks.get("json_schema"))
        message = case["query"] + (f"\nCODE:\n{context}" if case.get("context_files") else "")
        answer = await call.text(f"{message}\n\n{agents.format_rule(schema)}" if schema else message)
    except Exception as exc:  # a failing agent is an eval failure recorded in the result, not a crash of the whole suite
        error = classify(exc)
        return {"name": case["name"], "category": case.get("category", "quality"), "skill": case.get("skill", ""), "passed": False, "failed_checks": [f"error: {error.code} {error.message[:200]}"], "tokens": call.tokens}
    wanted = case.get("metrics", [])
    measured = {}
    if "groundedness" in wanted:
        measured["groundedness"] = metrics.groundedness(answer, context=context)
    if any(m in wanted for m in KEY_METRICS) and case.get("key"):
        measured["key"] = _key_counts(answer, case["key"])
    if case.get("mutation"):
        measured["mutation"] = _mutation(case, answer)
    evaluators = [LocalEvaluator(*build_checks(checks))] if checks else []
    outcome = await evaluate_agent(agent=call.agent, queries=[case["query"]], responses=[call.last_response], evaluators=evaluators or [LocalEvaluator(evaluator(lambda response: True, name="ran"))], eval_name=f"{agent_key}:{case['name']}")
    items = outcome[0].items or []
    failed = [s.name for item in items for s in item.scores if s.passed is False] if items else []
    counts = outcome[0].result_counts or {}
    passed = counts.get("failed", 0) == 0 and counts.get("errored", 0) == 0 and counts.get("passed", 0) > 0
    reasons = [f"failed {f}" for f in failed] + [c["reason"] for c in measured.get("groundedness", {}).get("bad", [])[:3]]
    result = {"name": case["name"], "category": case.get("category", "quality"), "skill": case.get("skill", ""), "passed": passed, "failed_checks": failed, "tokens": call.tokens, "model": call.model,
              "question": case["query"][:STORED_TEXT], "context": redact(context)[:STORED_TEXT], "answer": redact(answer)[:STORED_TEXT], "reference": case.get("reference", ""),
              "reason": "; ".join(reasons), "measured": measured, "wanted": wanted, "_item": (case["query"], answer, context, case.get("reference", ""))}
    if "skill" in case:  # only the code checks were scored; the plugin's sentences were not
        result["ungraded_expectations"] = case["expected_behavior"]
    return result


def _mutation(case: dict, answer: str) -> dict:
    """Generated tests run against the benchmark repository with each planted bug, in a temporary copy."""
    spec = case["mutation"]
    try:
        suite = _schemas()["GeneratedSuite"].model_validate(agents.extract_json(answer))
    except (ValueError, ValidationError) as exc:
        return {"verdict": "INCONCLUSIVE", "score": None, "reason": f"No usable tests in the reply: {str(exc)[:150]}", "killed": 0, "survived": 0, "not_applied": 0, "executed": 0, "mutants": []}
    return metrics.mutation_score(BENCH_DIR / case["benchmark"] / spec["repo"], {f.path: f.content for f in suite.files}, spec["mutants"], target=spec.get("target", "."))


async def _graded_skill_case(agent_key: str, case: dict, judge: str) -> dict:
    call = agents.AgentCall(None, EVAL_PROJECT, agent_key, source="eval", skills=(case["skill"],))
    base = {"name": case["name"], "category": "skill", "skill": case["skill"], "question": case["query"][:STORED_TEXT]}
    try:
        answer = await call.text(case["query"])
    except Exception as exc:
        error = classify(exc)
        return {**base, "passed": False, "failed_checks": [f"error: {error.code} {error.message[:200]}"], "tokens": call.tokens}
    graded = await grader.grade(case["query"], answer, case["expected_behavior"], judge=judge, agent_model=call.model)
    failed = [f"expectation: {g['expectation'][:120]} ({g['reason']})" for g in graded["grades"] if g["verdict"] != "PASS"]
    return {**base, "passed": graded["passed"], "status": "graded" if graded["passed"] is not None else "grader_failed", "failed_checks": failed + ([graded["error"]] if graded.get("error") else []),
            "answer": redact(answer)[:STORED_TEXT], "reason": "; ".join(failed), "grades": graded["grades"], "judge_model": judge, "self_graded": graded["self_graded"],
            "tokens": call.tokens + graded["tokens"], "model": call.model, "measured": {}, "wanted": []}
