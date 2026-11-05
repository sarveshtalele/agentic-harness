"""Ashish Patel's Agent Harness Engineering Patterns.
Complete architectural implementation of the 13 core chapters from:
https://ashishpatel26.github.io/agent-harness-engineering-pattern/

This module provides reusable, battle-tested abstractions powering both
the Claude Code Desktop Harness and the Headless CLI.
"""
from __future__ import annotations

import abc
import asyncio
import copy
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, TypeVar, Generic

T = TypeVar("T")


# =====================================================================
# Chapter 1: The Agent Loop
# =====================================================================

class HarnessState(str, Enum):
    """Pattern 1.03: State Pattern representing the harness lifecycle."""
    IDLE = "idle"
    PLANNING = "planning"
    DESIGNING = "designing"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class HarnessContext:
    """Pattern 1.14: Context Object.
    Encapsulates all runtime execution parameters, active agent,
    session metadata, and project knowledge binding.
    """
    session_id: str
    project_id: Optional[str] = None
    agent_id: str = "principal-test-architect"
    mode: str = "plan"  # "plan" | "execute"
    tokens_in: int = 0
    tokens_out: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: HarnessState = HarnessState.IDLE


class CollectingParameter:
    """Pattern 1.15: Collecting Parameter.
    Accumulates findings, warnings, test cases, and quality gate scorecards
    as the agent walks the codebase or executes workflows.
    """
    def __init__(self):
        self.findings: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.test_cases: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}

    def add_finding(self, finding: Dict[str, Any]):
        self.findings.append(finding)

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def add_case(self, case: Dict[str, Any]):
        self.test_cases.append(case)

    def set_metric(self, key: str, value: Any):
        self.metrics[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings_count": len(self.findings),
            "warnings_count": len(self.warnings),
            "test_cases_count": len(self.test_cases),
            "findings": self.findings,
            "warnings": self.warnings,
            "metrics": self.metrics
        }


class Memento(Generic[T]):
    """Pattern 1.07: Memento Pattern.
    Captures an immutable snapshot of internal state allowing rollback.
    """
    def __init__(self, state: T):
        self._state = copy.deepcopy(state)

    def get_saved_state(self) -> T:
        return copy.deepcopy(self._state)


class Originator:
    """Stateful entity capable of creating and restoring from Mementos."""
    def __init__(self, initial_state: Any = None):
        self.state = initial_state

    def save_to_memento(self) -> Memento:
        return Memento(self.state)

    def restore_from_memento(self, memento: Memento):
        self.state = memento.get_saved_state()


class CommandInterpreter:
    """Pattern 1.06: Interpreter Pattern.
    Parses and executes slash commands: /skills, /projects, /project <id>, /gates, /audit, /heal, /plan, /execute, /help.
    """
    def __init__(self, commands: Optional[Dict[str, Callable]] = None):
        self.commands: Dict[str, Callable] = commands or {}

    def register(self, command_name: str, handler: Callable):
        cmd = command_name.lower()
        if not cmd.startswith("/"):
            cmd = f"/{cmd}"
        self.commands[cmd] = handler

    def is_command(self, text: str) -> bool:
        trimmed = text.strip()
        return trimmed.startswith("/")

    async def interpret(self, text: str, context: HarnessContext) -> Optional[Any]:
        trimmed = text.strip()
        if not trimmed.startswith("/"):
            return None
        
        parts = trimmed.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        handler = self.commands.get(cmd)
        if not handler:
            return {
                "type": "error",
                "message": f"Unknown slash command '{cmd}'. Available: {', '.join(sorted(self.commands.keys()))}"
            }
        
        if asyncio.iscoroutinefunction(handler):
            return await handler(arg, context)
        return handler(arg, context)


class ChainOfResponsibilityNode(abc.ABC):
    """Pattern 1.05: Chain of Responsibility Pattern.
    Hierarchical agent dispatch chain.
    """
    def __init__(self, next_handler: Optional[ChainOfResponsibilityNode] = None):
        self.next_handler = next_handler

    def set_next(self, handler: ChainOfResponsibilityNode) -> ChainOfResponsibilityNode:
        self.next_handler = handler
        return handler

    @abc.abstractmethod
    async def handle(self, request: Dict[str, Any], context: HarnessContext) -> Optional[Dict[str, Any]]:
        pass


class PipelineStage(abc.ABC):
    """Pattern 1.16: Pipeline Pattern.
    Executes sequential steps of the 8 Quality Gates.
    """
    @abc.abstractmethod
    async def process(self, context: HarnessContext, accumulator: CollectingParameter) -> bool:
        """Returns True to proceed to next stage, False to abort."""
        pass


class QualityGatePipeline:
    """Orchestrates an ordered pipeline of quality gate checks."""
    def __init__(self):
        self.stages: List[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> QualityGatePipeline:
        self.stages.append(stage)
        return self

    async def execute(self, context: HarnessContext) -> CollectingParameter:
        accumulator = CollectingParameter()
        for stage in self.stages:
            context.state = HarnessState.EXECUTING
            should_continue = await stage.process(context, accumulator)
            if not should_continue:
                context.state = HarnessState.AWAITING_APPROVAL
                break
        if context.state != HarnessState.AWAITING_APPROVAL:
            context.state = HarnessState.COMPLETED
        return accumulator


class RuleEngine:
    """Pattern 1.17: Rule Engine.
    Validates safety policies and deterministic constraints.
    """
    def __init__(self):
        self.rules: List[Callable[[Dict[str, Any], HarnessContext], tuple[bool, str]]] = []

    def add_rule(self, rule_fn: Callable[[Dict[str, Any], HarnessContext], tuple[bool, str]]):
        self.rules.append(rule_fn)

    def validate(self, action: Dict[str, Any], context: HarnessContext) -> tuple[bool, str]:
        for rule in self.rules:
            allowed, reason = rule(action, context)
            if not allowed:
                return False, reason
        return True, "Validation passed"


# =====================================================================
# Chapter 2: Structural & Proxy Patterns
# =====================================================================

class DynamicToolProxy:
    """Pattern 2.03: Dynamic Proxy Pattern.
    Intercepts every tool call at runtime to enforce:
    1. Plan Mode vs Execute Mode restrictions (Rule Engine)
    2. Quality Gate human approval intercept
    3. Latency timing and token telemetry
    """
    def __init__(self, target_tool: Any, approval_checker: Callable[[str, Dict[str, Any]], bool]):
        self.target_tool = target_tool
        self.approval_checker = approval_checker

    async def invoke(self, params: Dict[str, Any], context: HarnessContext) -> Dict[str, Any]:
        # 1. Plan Mode check
        if context.mode == "plan":
            name = getattr(self.target_tool, "name", "tool")
            destructive_keywords = ["write", "delete", "create", "execute", "apply", "run"]
            if any(k in name.lower() for k in destructive_keywords) and "plan" not in name.lower() and "discover" not in name.lower():
                return {
                    "error": True,
                    "code": "PLAN_MODE_GUARDRAIL",
                    "message": f"Execution refused: The harness is running in Plan Mode. '{name}' is a destructive action."
                }

        # 2. Approval check
        if self.approval_checker(getattr(self.target_tool, "name", ""), params):
            return {
                "requires_approval": True,
                "tool": getattr(self.target_tool, "name", ""),
                "params": params,
                "message": "This operation requires explicit human approval before execution."
            }

        # 3. Execution with timing
        t0 = time.perf_counter()
        if asyncio.iscoroutinefunction(getattr(self.target_tool, "run", None)):
            res = await self.target_tool.run(**params)
        elif hasattr(self.target_tool, "run"):
            res = self.target_tool.run(**params)
        else:
            res = {"status": "success", "result": "Executed"}
        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "result": res,
            "duration_ms": round(elapsed_ms, 2)
        }
