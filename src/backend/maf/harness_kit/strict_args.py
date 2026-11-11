"""Unknown tool arguments are an error the model can read, never silently dropped (found in the 2026-11-11 live cycle).

MAF validates a call's arguments with the tool's input model, and pydantic ignores extra keys by default. A model that
wrote `file_access_ls(path="src")` (the parameter is `directory`) got the workspace root back every time and listed it
73 times. This MAF chat middleware runs before each model call and makes every offered tool's input model forbid extra
keys, so the call fails with "path: Extra inputs are not permitted" (the harness client sets MAF's
`include_detailed_errors`), and the model corrects the name. The tools are built per turn, so nothing outside it changes.
"""
from __future__ import annotations

from agent_framework import chat_middleware
from pydantic import ConfigDict


@chat_middleware
async def strict_arguments(context, call_next) -> None:
    for tool in context.options.get("tools") or []:
        model = getattr(tool, "input_model", None)
        if model is not None and model.model_config.get("extra") != "forbid":
            tool.input_model = type(f"Strict{model.__name__}", (model,), {"model_config": ConfigDict(**{**model.model_config, "extra": "forbid"})})
    await call_next()
