"""Capability registry API (plan Phase R). Reads are per user: an admin sees every capability, anyone else the slice they
may use (core/registry/visibility.py). Only an admin starts a sync; core/auth/rules.py refuses everyone else first.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.mcp.common import require_admin
from backend.core import auth, registry

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


@router.get("")
def list_capabilities(kind: str = "", q: str = "", plugin: str = "") -> dict:
    user = auth.current_user.get()
    return {"version": registry.latest(), "items": registry.listing(user, kind, q, plugin)}


@router.get("/tree")
def capability_tree() -> dict:
    return {"version": registry.latest(), "roots": registry.tree(auth.current_user.get())}


@router.post("/sync")
def sync_now() -> dict:
    return registry.sync(by=require_admin()["id"])


@router.get("/{name_or_id:path}")
def capability(name_or_id: str) -> dict:
    found = registry.detail(auth.current_user.get(), name_or_id)
    if not found:
        raise KeyError(f"capability {name_or_id}")
    return found
