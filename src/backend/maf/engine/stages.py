"""MAF executors for stages and fan-in, and the compiler from a Definition to a MAF workflow."""
from __future__ import annotations

import json
import logging

from agent_framework import Executor, Workflow, WorkflowBuilder, WorkflowContext, handler, response_handler

from backend.db import db
from backend.maf import runtime as agent_module
from backend.maf.engine.failures import _safely
from backend.maf.engine.run_context import RunContext
from backend.maf.engine.specs import ApprovalRequest, Definition, StageSpec

# rework loops back to the same stage on purpose, guarded by routing conditions and max_iterations
logging.getLogger("agent_framework._workflows._validation").setLevel(logging.ERROR)


class Stage(Executor):
    """One workflow step as a MAF executor. Routing lives in the message state, edges read it."""

    def __init__(self, spec: StageSpec, run_id: str, project_id: str):
        super().__init__(id=spec.id)
        self.spec, self.run_id, self.project_id = spec, run_id, project_id

    def _ctx(self) -> RunContext:
        rc = RunContext(self.run_id, self.project_id, self.spec.id)
        agent_module.set_emitter(rc.emit)
        return rc

    async def _advance(self, state: dict, ctx: WorkflowContext) -> None:
        with db() as con:
            con.execute("UPDATE runs SET state=? WHERE id=?", (json.dumps(_public_state(state), default=str), self.run_id))
        target = state.pop("_next", None) or self.spec.next
        if self.spec.forward:
            await ctx.send_message(state)
        elif target == "END" or target is None:
            await ctx.yield_output(json.dumps(state, default=str))
        else:
            await ctx.send_message({**state, "_to": target})

    @handler
    async def run(self, state: dict, ctx: WorkflowContext[dict, str]) -> None:
        rc = self._ctx()
        rc.log(f"Started {self.spec.label or self.spec.id}", kind="stage_start")
        state = {**state, **(await _safely(rc, self.spec.fn(rc, state)) or {})}
        if not state.get("partial"):  # a partial result keeps its batches for the rework that follows
            rc.clear_parts()
        state.pop("_to", None)
        rc.log(f"Finished {self.spec.label or self.spec.id}", kind="stage_end")
        request = self.spec.approval(rc, state) if self.spec.approval else None
        if request:
            await ctx.request_info(
                ApprovalRequest(stage=self.spec.id, gate=request.get("gate", -1), title=request["title"], summary=request["summary"],
                                payload=json.dumps(request.get("payload", {}), default=str), state=json.dumps(state, default=str)),
                str,
            )
            return
        await self._advance(state, ctx)

    @response_handler
    async def decided(self, original: ApprovalRequest, decision: str, ctx: WorkflowContext[dict, str]) -> None:
        rc = self._ctx()
        answer = json.loads(decision)
        state = json.loads(original.state)
        if answer["approved"]:
            rc.log(f"Approved by {answer['by']}", {"feedback": answer.get("feedback", "")}, "approved")
            if self.spec.on_approved:
                state = {**state, **(await _safely(rc, self.spec.on_approved(rc, state, answer)) or {})}
            state.pop("feedback", None)
            await self._advance(state, ctx)
            return
        rc.log(f"Rejected by {answer['by']}: {answer.get('feedback', '')}", kind="rejected")
        if self.spec.on_rejected:
            await ctx.send_message({**state, "feedback": answer.get("feedback", ""), "_to": self.spec.on_rejected})
        else:
            await ctx.yield_output(json.dumps({**state, "rejected": True}, default=str))


class Merge(Executor):
    """Fan-in target. MAF delivers a list once every fan-out branch has finished."""

    def __init__(self, id: str, fn, next_stage: str | None, run_id: str, project_id: str):
        super().__init__(id=id)
        self.fn, self.next_stage, self.run_id, self.project_id = fn, next_stage, run_id, project_id

    @handler
    async def merge(self, branches: list[dict], ctx: WorkflowContext[dict, str]) -> None:
        rc = RunContext(self.run_id, self.project_id, self.id)
        state = await _safely(rc, self.fn(rc, branches))
        if self.next_stage:
            await ctx.send_message({**state, "_to": self.next_stage})
        else:
            await ctx.yield_output(json.dumps(state, default=str))


def _public_state(state: dict) -> dict:
    return {k: v for k, v in state.items() if not k.startswith("_") and k not in {"context", "source_text"}}


def compile_workflow(definition: Definition, run_id: str, project_id: str, storage) -> Workflow:
    stages = {s.id: Stage(s, run_id, project_id) for s in definition.stages}
    first = stages[definition.stages[0].id]
    builder = WorkflowBuilder(start_executor=first, name=definition.name, checkpoint_storage=storage, max_iterations=120)

    def route(target: str):
        return lambda state: isinstance(state, dict) and state.get("_to") == target

    edges: set[tuple[str, str]] = set()
    fan = definition.fan_out
    for spec in definition.stages:
        targets = set(definition.routes.get(spec.id, []))
        if spec.next and spec.next != "END":
            targets.add(spec.next)
        if spec.on_rejected:
            targets.add(spec.on_rejected)
        for target in targets:
            if fan and spec.id in fan.branches:
                continue
            if (spec.id, target) not in edges:
                builder.add_edge(stages[spec.id], stages[target], condition=route(target))
                edges.add((spec.id, target))
    if fan:
        merge = Merge(fan.merge_id, fan.merge_fn, fan.next, run_id, project_id)
        builder.add_fan_out_edges(stages[fan.source], [stages[b] for b in fan.branches])
        builder.add_fan_in_edges([stages[b] for b in fan.branches], merge)
        if fan.next:
            builder.add_edge(merge, stages[fan.next], condition=route(fan.next))
    return builder.build()
