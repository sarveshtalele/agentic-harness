"""Governance of features (R2): role defaults, member overrides, and what the signed-in member may use."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core import auth
from backend.core.auth import features

router = APIRouter()


class OverrideIn(BaseModel):
    feature: str
    allowed: bool | None = None  # None removes the override


def _guarded(call):
    try:
        return call()
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/features/me")
def my_features():
    return features.mine()


@router.get("/api/features")
def all_features():
    return {"names": features.FEATURES, "roles": features.role_defaults(), "overrides": features.overrides()}


@router.put("/api/features/roles")
def put_roles(body: dict[str, list[str]]):
    return _guarded(lambda: features.set_role_defaults(body))


@router.put("/api/features/overrides/{user_id}")
def put_override(user_id: str, body: OverrideIn):
    return _guarded(lambda: features.set_override(user_id, body.feature, body.allowed))


@router.get("/api/features/effective/{user_id}")
def effective_for(user_id: str):
    try:
        account = auth.get_user(user_id)
    except KeyError as exc:
        raise HTTPException(404, "No such member") from exc
    return {"features": features.effective({"id": user_id, "role": "user", "account_role": account["account_role"]})}
