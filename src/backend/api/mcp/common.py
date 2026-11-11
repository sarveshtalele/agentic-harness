"""Shared by the MCP routes: the admin check and turning a refusal into its HTTP status."""
from __future__ import annotations

from contextlib import contextmanager

from fastapi import HTTPException

from backend.core import auth
from backend.core.mcp import McpProblem


def require_admin() -> dict:
    """core/auth refuses these writes already; this second check keeps the rule next to the route."""
    user = auth.current_user.get()
    if not user or user["role"] != "admin":
        raise auth.Forbidden("Only an administrator can do this")
    return user


@contextmanager
def answered():
    try:
        yield
    except McpProblem as exc:
        raise HTTPException(exc.status, exc.message) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
