"""The load_tools harness tool: add catalogue tools for the rest of the chat thread (MAF progressive tool exposure)."""
from __future__ import annotations

import json

from agent_framework import FunctionInvocationContext, tool


def build(catalogue, loaded):
    @tool(name="load_tools", description="Load tools by their exact names from find_tools. They stay available for the rest of this chat.")
    def load_tools(names: list[str], ctx: FunctionInvocationContext) -> str:
        known = [n for n in dict.fromkeys(names) if n in catalogue]
        refused = [n for n in names if n not in catalogue]
        if known:
            loaded.add(known)
            now = [t for t in catalogue.resolve([n for n in known if n in catalogue.tools])]
            if now and ctx.tools is not None:
                ctx.add_tools(now)  # usable from the next model step of this turn
        later = [n for n in known if n in catalogue.mcp]  # MAF opens MCP sessions when a run starts
        return json.dumps({"loaded": [n for n in known if n not in later], "loaded_next_turn": later,
                           "refused": {n: "not a tool this harness may load; use find_tools" for n in refused}})

    return load_tools
