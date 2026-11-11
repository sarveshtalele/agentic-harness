"""Plain data types of the run engine: the approval payload, a stage spec, fan-out and a workflow definition."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from backend.maf.engine.run_context import RunContext


@dataclass
class ApprovalRequest:
    """Payload MAF carries through request_info and checkpoints. State is JSON so it stays portable."""

    stage: str = ""
    gate: int = -1  # -1 means a run-level approval that is not a numbered quality gate
    title: str = ""
    summary: str = ""
    payload: str = "{}"
    state: str = "{}"


@dataclass
class StageSpec:
    id: str
    fn: Callable[["RunContext", dict], Awaitable[dict]]
    label: str = ""
    # returns a gate request ({gate, title, summary, payload}) or None to continue without stopping
    approval: Callable[["RunContext", dict], dict | None] | None = None
    on_approved: Callable[["RunContext", dict, dict], Awaitable[dict]] | None = None
    on_rejected: str | None = None  # stage to loop back to with reviewer feedback; None ends the run
    next: str | None = None
    forward: bool = False  # sends to fan-out edges instead of naming a single next stage


@dataclass
class FanOut:
    source: str
    branches: list[str]
    merge_id: str
    merge_fn: Callable
    next: str | None = None


@dataclass
class Definition:
    name: str
    stages: list[StageSpec]
    fan_out: FanOut | None = None
    routes: dict[str, list[str]] = field(default_factory=dict)  # extra dynamic targets, e.g. review to draft


ApprovalRequest.__module__ = "backend.maf.engine"
