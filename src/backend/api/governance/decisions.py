"""Gates, approvals, and the project ledger: the human decision routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.common import _project
from backend.core import auth, gates, ledger
from backend.db import db, row, rows
from backend.maf import engine

router = APIRouter()

@router.get("/api/projects/{project_id}/gates")
def project_gates(project_id: str):
    _project(project_id)
    return _named(gates.status(project_id))


def _named(items: list[dict]) -> list[dict]:
    names = auth.display_names({g["decided_by"] for g in items if g["decided_by"]})
    return [{**g, "decided_by_name": names.get(g["decided_by"], g["decided_by"])} for g in items]


class GateIn(BaseModel):
    approved: bool
    reason: str = ""


@router.post("/api/projects/{project_id}/gates/{gate}/decision")
def decide_gate(project_id: str, gate: int, body: GateIn):
    _project(project_id)
    auth.require_gate_signer(project_id, gate)
    gates.decide(project_id, gate, body.approved, auth.signer(), body.reason)
    return _named(gates.status(project_id))


@router.get("/api/projects/{project_id}/approvals")
def project_approvals(project_id: str, status: str = "pending"):
    _project(project_id)
    with db() as con:
        items = rows(con.execute("SELECT * FROM approvals WHERE project_id=? AND status=? ORDER BY created_at DESC", (project_id, status)))
    def _parse_payload(payload):
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except Exception:
            return {}
    return [{**a, "payload": _parse_payload(a.get("payload"))} for a in items]


class DecisionIn(BaseModel):
    approved: bool
    feedback: str = ""
    open_pr: bool = False


@router.post("/api/projects/{project_id}/approvals/{approval_id}/decide")
async def decide_project_approval(project_id: str, approval_id: str, body: DecisionIn):
    _project(project_id)
    with db() as con:
        appr_row = row(con.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)))
    if not appr_row or appr_row["project_id"] != project_id:
        raise HTTPException(404, f"Approval not found in this project: {approval_id}")
    try:
        return await engine.decide(approval_id, body.approved, auth.signer(), body.feedback, {"open_pr": body.open_pr})
    except auth.Forbidden:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/projects/{project_id}/ledger")
def project_ledger(project_id: str):
    _project(project_id)
    found = ledger.entries(project_id)
    names = auth.display_names({e["actor"] for e in found})
    return {"entries": [{**e, "actor_name": names.get(e["actor"], e["actor"])} for e in found], "verification": ledger.verify(project_id)}
