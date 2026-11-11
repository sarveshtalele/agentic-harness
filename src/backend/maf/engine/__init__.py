"""Run manager over real MAF workflows: typed stages, HITL via request_info, file checkpoints, durable events.

Resume always rebuilds the workflow and restores the latest checkpoint, so an app restart between a gate
request and its decision behaves exactly like the normal path.
"""
from __future__ import annotations

import json
import re

from backend.config import RUN_TOKEN_LIMIT
from backend.core import auth, gates, ledger
from backend.core.errors import AllowanceError
from backend.db import db, new_id, now, row
from backend.maf import runtime as agent_module
from backend.maf.engine.execution import _active, _finish, _guarded, _spawn, _storage
from backend.maf.engine.registry import REGISTRY, _ensure_workflows
from backend.maf.engine.resume import _rerun, _resume
from backend.maf.engine.queries import ACTIVE, RunActive, events, get, recover
from backend.maf.engine.run_context import RunContext, add_event, part_key
from backend.maf.engine.specs import ApprovalRequest, Definition, FanOut, StageSpec
from backend.maf.engine.stages import Stage, compile_workflow
from backend.qe import confidence


MIN_REASON = 10  # characters; "a" and "ok" were accepted as reasons for approving REJECT items


def weak_reason(reason: str, title: str = "") -> str:
    """Why a reason for a REJECT decision is not a real one, or "": too short, fewer than two words, or the gate's own title repeated."""
    text = " ".join(reason.split())
    if len(text) < MIN_REASON:
        return f"this one has {len(text)} characters, fewer than {MIN_REASON}"
    if len(re.findall(r"[^\W\d_]{2,}", text)) < 2:
        return "it needs at least two words"
    if title and text.lower().strip(" .") == " ".join(title.split()).lower().strip(" ."):
        return "it repeats the gate's title"
    return ""


def cancel(run_id: str) -> dict:
    """Stop a running run, or close one waiting on a human so its approval can no longer be used."""
    run = get(run_id)
    task = _active.get(run_id)
    if task and not task.done():
        task.cancel()
    elif run["status"] == "waiting_approval":
        with db() as con:
            con.execute("UPDATE approvals SET status='cancelled' WHERE run_id=? AND status='pending'", (run_id,))
        _finish(run_id, "cancelled")
    else:
        raise ValueError(f"Run is already {run['status']}")
    return get(run_id)


async def start(project_id: str, workflow: str, payload: dict, model: str = "") -> dict:
    _ensure_workflows()
    if workflow not in REGISTRY:
        raise ValueError(f"Unknown workflow {workflow}. Use one of: {', '.join(sorted(REGISTRY))}")
    llm_check = agent_module.llm.client  # fails early with a clear message when no model is configured
    llm_check()
    starter = (auth.current_user.get() or {}).get("id")
    auth.model_for(project_id, "", None, starter, model)  # refuses at once a model this account may not use, or an account with none
    auth.check_allowance(project_id, starter)
    run_id = new_id("run")
    with db() as con:  # one statement inside one write transaction decides who wins, so two starts cannot both take the slot
        con.execute("BEGIN IMMEDIATE")
        claimed = con.execute(
            """INSERT INTO runs (id, project_id, workflow, status, input, started_at, user_id, model)
               SELECT ?,?,?,?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM runs WHERE project_id=? AND workflow=? AND status IN ('running','waiting_approval'))""",
            (run_id, project_id, workflow, "running", json.dumps(payload), now(), starter, model.strip(), project_id, workflow)).rowcount
    if not claimed:
        raise RunActive(project_id, workflow)
    ledger.append(project_id, starter or "system", "run.started", run_id, {"workflow": workflow, "model": model.strip()})
    add_event(run_id, "status", "", "running")
    storage = _storage(run_id)
    compiled = compile_workflow(REGISTRY[workflow](), run_id, project_id, storage)
    state = {**payload, "project_id": project_id, "run_id": run_id, "_to": ""}
    _spawn(run_id, _guarded(run_id, project_id, compiled.run(state, stream=True)))
    return get(run_id)


async def decide(approval_id: str, approved: bool, by: str, feedback: str = "", extra: dict | None = None) -> dict:
    _ensure_workflows()
    if not by.strip():
        raise ValueError("A named human signer is required")
    with db() as con:
        approval = row(con.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)))
    if not approval:
        raise KeyError(approval_id)
    if approval["status"] != "pending":
        raise ValueError(f"Approval already {approval['status']}")
    if approved and (partial := json.loads(approval["payload"]).get("partial")):
        raise ValueError(f"This result is partial and cannot be approved. Missing: {partial['missing']}. Send it back, or approve nothing and retry after fixing the cause.")
    rejected = confidence.reject_ids(json.loads(approval["payload"])) if approved and approval["gate"] is not None else []
    if rejected and (why := weak_reason(feedback, approval["title"])):  # code judged these REJECT; a person may still approve them, but must say why
        raise ValueError(f"These items were judged REJECT: {', '.join(rejected[:12])}{' and more' if len(rejected) > 12 else ''}. Approving them needs a reason, and {why}. Write it in the reason field.")
    if not approved and approval["gate"] is not None and (why := weak_reason(feedback, approval["title"])):
        raise ValueError(f"Rejecting gate {approval['gate']} sends the work back, so it needs a reason the agent can act on, and {why}. Write it in the reason field.")
    if approval["gate"] is not None:
        auth.require_gate_signer(approval["project_id"], approval["gate"])  # the account's role, not a name in the request
        gates.decide(approval["project_id"], approval["gate"], approved, by, feedback, approval["run_id"])
        if rejected:
            ledger.append(approval["project_id"], by, "gate.reject_accepted", f"G{approval['gate']}", {"reason": feedback, "items": rejected, "run_id": approval["run_id"]})
    else:
        ledger.append(approval["project_id"], by, "approval." + ("approved" if approved else "rejected"), approval["title"], {"run_id": approval["run_id"], "feedback": feedback})
    with db() as con:
        con.execute("UPDATE approvals SET status=?, decided_by=?, feedback=?, decided_at=? WHERE id=?",
                    ("approved" if approved else "rejected", by, feedback, now(), approval_id))
        run = row(con.execute("SELECT * FROM runs WHERE id=?", (approval["run_id"],)))
        con.execute("UPDATE runs SET status='running' WHERE id=?", (run["id"],))
    response = json.dumps({"approved": approved, "by": by, "feedback": feedback, **(extra or {})})
    _spawn(run["id"], _guarded(run["id"], run["project_id"], _resume(run, approval_id, response)))
    return get(run["id"])


async def retry(run_id: str, allow_unlimited: bool = False) -> dict:
    """Resume a failed or interrupted run from its latest checkpoint. Finished batches are kept by the stage itself."""
    run = get(run_id)
    agent_module.llm.client()  # a missing model fails now, with its own message
    acting = auth.acting_user(run["project_id"], run_id)
    if not allow_unlimited:
        auth.check_allowance(run["project_id"], acting)
        if run["tokens_in"] + run["tokens_out"] >= RUN_TOKEN_LIMIT:
            raise AllowanceError(f"Run stopped: it used {run['tokens_in'] + run['tokens_out']} tokens, over the limit of {RUN_TOKEN_LIMIT}.", action="Raise ATLAS_RUN_TOKEN_LIMIT, or ask your administrator, then retry.")
    with db() as con:  # one statement decides who wins, so two retries cannot both start, nor can a retry take a slot a newer run holds
        con.execute("BEGIN IMMEDIATE")
        claimed = con.execute(
            """UPDATE runs SET status='running', error='', ended_at=NULL WHERE id=? AND status IN ('failed','interrupted')
               AND NOT EXISTS (SELECT 1 FROM runs o WHERE o.project_id=runs.project_id AND o.workflow=runs.workflow AND o.status IN ('running','waiting_approval'))""", (run_id,)).rowcount
    if not claimed:
        if get(run_id)["status"] in {"failed", "interrupted"}:
            raise RunActive(run["project_id"], run["workflow"])
        raise ValueError(f"Run is {get(run_id)['status']}; only a failed or interrupted run can be retried")
    ledger.append(run["project_id"], (auth.current_user.get() or {}).get("id", "system"), "run.retried", run_id, {"after": run["status"]})
    add_event(run_id, "status", "", "running", {"retry": True})
    _spawn(run_id, _guarded(run_id, run["project_id"], _rerun(run)))
    return get(run_id)


__all__ = ["RunActive", "StageSpec", "Definition", "FanOut", "RunContext", "REGISTRY", "start", "decide", "retry", "recover", "get", "events", "part_key"]
