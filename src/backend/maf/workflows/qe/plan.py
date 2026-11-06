"""QE Plan Stage: Principal Test Architect quality strategy and risk-weighted plan."""
from __future__ import annotations

import json
from backend.config import repo_dir
from backend.core import documents
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.maf.workflows.qe.common import _cell
from backend.maf.workflows.shared import (
    code_pack,
    review_with_send_back,
    _analysis,
)
from backend.qe import confidence, model


async def qe_plan(rc: RunContext, state: dict) -> dict:
    call = AgentCall(rc.run_id, rc.project_id, "principal-test-architect")
    a = _analysis(rc.project_id)
    prompt = f"Create the test plan.\nREQUIREMENTS:\n{json.dumps(state['requirements'])}\nDETECTED RUNNERS: {a['test_runners']}\nFRAMEWORKS: {a['frameworks']}\nEXISTING TESTS: {a.get('test_files', [])[:40]}" + (f"\nFEEDBACK:\n{state['feedback']}" if state.get("feedback") else "")
    plan = (await call.typed(prompt, model.TestPlan)).model_dump()
    score = model.plan_confidence(state["requirements"], plan)
    if score["verdict"] != "APPROVED":
        plan = (await call.typed(f"{prompt}\n\nAutomatic checks rejected your plan: {score['issues']}. Fix them.", model.TestPlan)).model_dump()
        score = model.plan_confidence(state["requirements"], plan)
    root = repo_dir(rc.project_id)
    wanted_files = list(dict.fromkeys(r["file"] for r in state["requirements"] if r.get("file")))
    evidence = lambda _: f"REQUIREMENTS:\n{json.dumps(state['requirements'])}\n\nCODE (line numbers are before each line):\n{code_pack(rc.project_id, paths=wanted_files or None, limit=20_000)}"

    async def revise_plan(_: int, record: dict, calls: list) -> str:
        nonlocal plan
        again = AgentCall(rc.run_id, rc.project_id, "principal-test-architect")
        calls.append(again)
        plan = (await again.typed(f"{prompt}\n\nAn independent reviewer found these flaws in your plan. Fix each one and send the complete plan.\n{confidence.flaw_lines(record)}", model.TestPlan, attempts=2)).model_dump()
        return json.dumps(plan)

    records, tokens = await review_with_send_back(rc, "plan", "plan", [("PLAN", json.dumps(plan))], evidence, root if root.exists() else None, revise_plan)
    score = model.plan_confidence(state["requirements"], plan)
    review = confidence.summarise(records, tokens)
    rc.log(f"Plan score {score['score']} ({score['verdict']}), independent review {review['score']} ({review['verdict']})", {"deterministic": score, "review": review}, "review")
    body = f"{plan['strategy']}\n\n| Area | Requirements | Risk | Level | Framework | Rationale |\n|---|---|---|---|---|---|\n" + "\n".join(
        f"| {_cell(x['name'])} | {', '.join(x['requirement_ids'])} | {x['risk']} | {x['level']} | {x['framework']} | {_cell(x['rationale'])} |" for x in plan["areas"])
    doc = documents.create(rc.project_id, "test_plan", "Comprehensive Quality Strategy & Test Plan", body, "agent:principal-test-architect", data={"plan": plan, "score": score, "review": review}, prompt_ref=call.prompt_ref, run_id=rc.run_id)
    return {"plan": plan, "plan_doc": doc["id"], "plan_score": score, "plan_review": review}
