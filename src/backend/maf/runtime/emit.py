"""The live-activity emitter: a workflow run binds it so tool and agent activity lands on the run timeline."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Callable

_emit: ContextVar[Callable | None] = ContextVar("agent_emit", default=None)


def set_emitter(callback: Callable | None) -> None:
    """Workflow runs bind this so tool activity lands on the live run timeline."""
    _emit.set(callback)
