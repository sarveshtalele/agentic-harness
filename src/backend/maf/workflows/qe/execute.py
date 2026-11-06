"""QE Execute Stage: Running deterministic test suites in the isolated worktree sandbox."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.core.errors import AllowanceError
from backend.maf.engine import RunContext
from backend.maf.runtime import AgentCall
from backend.qe import execution, model


async def _explain(rc: RunContext, result: dict) -> dict:
    """The qa-execution-engineer's summary, accepted only if every number matches the JUnit counts."""
    own = {"text": execution.code_summary(result), "source": "code", "reason": ""}
    if result["passed"] + result["failed"] + result["skipped"] == 0:
        return {**own, "reason": "No test ran, so there is nothing to explain"}
    try:
        reply = await AgentCall(rc.run_id, rc.project_id, "qa-execution-engineer").typed(f"Explain this test result.\nEVIDENCE:\n{json.dumps(execution.summary_evidence(result))}", model.ExecutionSummary)
    except AllowanceError:
        raise
    except Exception as exc:
        rc.log(f"The execution summary did not run, so code's summary is used: {str(exc)[:200]}", kind="warning")
        return {**own, "reason": f"Agent summary did not run: {str(exc)[:200]}"}
    if problems := execution.summary_problems(reply.model_dump(), result):
        rc.log(f"The agent's execution summary was refused, so code's summary is used: {'; '.join(problems[:4])}", {"refused": reply.summary[:500]}, "warning")
        return {**own, "reason": "Agent summary refused: " + "; ".join(problems[:4])}
    return {"text": reply.summary, "source": "agent", "reason": ""}


async def qe_execute(rc: RunContext, state: dict) -> dict:
    worktree = Path(state["worktree"])
    framework = state["framework"].lower()
    runner = next((r for r in execution.REGISTERED if r in framework), framework)
    rc.log(f"[TEST_EXECUTION_STARTED] Launching runner '{runner}' in sandbox worktree {worktree}...")
    result = await asyncio.to_thread(execution.run_suite, runner, worktree, "tests/agentic_qe", worktree.parent / f"{rc.run_id}-results", int(state.get("timeout", 300)), tuple(state.get("pytest_args", [])))
    rc.log(f"[TEST_EXECUTION_COMPLETED] {runner}: {result['verdict']}. {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped", {"exit_code": result["exit_code"], "reason": result["reason"], "output": result["output"][-1500:]}, "test")
    explained = await _explain(rc, result)
    update = {"results": [result], "execution_summary": explained, "attempt_history": [*state.get("attempt_history", []), {k: result[k] for k in ("verdict", "passed", "failed")}]}
    if state["mode"] == "greenfield":
        rc.log("Greenfield RED baseline recorded. Failures are expected until the app exists.", kind="review")
        update["_next"] = "trace"
    elif result["failed"] and state.get("heal_attempts", 0) < 2:
        update["_next"] = "heal"
    else:
        update["_next"] = "trace"
    return update
