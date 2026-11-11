"""Re-entering a run from its latest checkpoint, for a retry and for a decided approval."""
from __future__ import annotations

from backend.maf.engine.execution import _storage
from backend.maf.engine.registry import REGISTRY, _ensure_workflows
from backend.maf.engine.stages import compile_workflow


async def _rerun(run: dict):
    _ensure_workflows()
    storage = _storage(run["id"])
    workflow = compile_workflow(REGISTRY[run["workflow"]](), run["id"], run["project_id"], storage)
    latest = await storage.get_latest(workflow_name=workflow.name)
    if latest is None:  # it failed before the first checkpoint, so it starts again from its input
        stream = workflow.run({**run["input"], "project_id": run["project_id"], "run_id": run["id"], "_to": ""}, stream=True)
    else:
        stream = workflow.run(checkpoint_id=latest.checkpoint_id, checkpoint_storage=storage, stream=True)
    async for event in stream:
        yield event


async def _resume(run: dict, approval_id: str, response: str):
    _ensure_workflows()
    storage = _storage(run["id"])
    workflow = compile_workflow(REGISTRY[run["workflow"]](), run["id"], run["project_id"], storage)
    latest = await storage.get_latest(workflow_name=workflow.name)
    if latest is None:
        raise RuntimeError("No checkpoint found to resume this run")
    async for _ in workflow.run(checkpoint_id=latest.checkpoint_id, checkpoint_storage=storage, stream=True):
        pass  # replays the pending request so the response below has something to answer
    async for event in workflow.run(responses={approval_id: response}, stream=True):
        yield event
