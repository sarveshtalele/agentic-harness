"""QE Plan Stage: Principal Test Architect quality strategy and risk-weighted plan."""
from __future__ import annotations

import asyncio
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
from backend.qe import confidence, model, plugin_bridge


async def qe_plan(rc: RunContext, state: dict) -> dict:
    call = AgentCall(rc.run_id, rc.project_id, "principal-test-architect")
    a = _analysis(rc.project_id)
    prompt = f"Create the test plan.\nREQUIREMENTS:\n{json.dumps(state['requirements'])}\nDETECTED RUNNERS: {a['test_runners']}\nFRAMEWORKS: {a['frameworks']}\nEXISTING TESTS: {a.get('test_files', [])[:40]}" + (f"\nFEEDBACK:\n{state['feedback']}" if state.get("feedback") else "")
    plan = (await call.typed(prompt, model.TestPlan)).model_dump()
    score = model.plan_confidence(state["requirements"], plan)
    if score["verdict"] != "APPROVED":
        plan = (await call.typed(f"{prompt}\n\nAutomatic checks rejected your plan: {score['issues']}. Fix them.", model.TestPlan)).model_dump()
        score = model.plan_confidence(state["requirements"], plan)
    plan, plugin_check = await _plugin_sensor(rc, state, call, prompt, plan)
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
    return {"plan": plan, "plan_doc": doc["id"], "plan_score": score, "plan_review": review, "plan_plugin_check": plugin_check}


async def _plugin_sensor(rc: RunContext, state: dict, call: AgentCall, prompt: str, plan: dict) -> tuple[dict, dict]:
    """Gate 2 sensor: the plugin's check-gate.ts on its plan.json; its gaps go back to the architect once."""
    if state["mode"] != "brownfield":
        return plan, {"ok": None, "error": "greenfield: the plugin's gate check needs code-evidenced requirements"}
    app = plugin_bridge.app_name(rc.project_id)
    for attempt in range(2):
        plugin_bridge.write(rc.project_id, app, "03-plan/plan.json", plugin_bridge.plan_file(plan))
        check = await asyncio.to_thread(plugin_bridge.check_gate, rc.project_id, app, 2)
        if check["ok"] or check["error"] or attempt:
            break
        fixed = (await call.typed(f"{prompt}\n\nThe agentic-qe Gate 2 check failed. Fix each gap and send the complete plan "
                                  f"(a skipped level needs a reason of at least 10 characters):\n- " + "\n- ".join(check["gaps"]), model.TestPlan)).model_dump()
        if model.plan_confidence(state["requirements"], fixed)["score"] >= model.plan_confidence(state["requirements"], plan)["score"]:
            plan = fixed  # never trade a plan the deterministic score accepts for a worse one
    check["app"] = app
    rc.log(f"agentic-qe Gate 2 check: {'PASS' if check['ok'] else 'FAIL'}" + (f"; {check['error']}" if check["error"] else ""), check)
    return plan, check
