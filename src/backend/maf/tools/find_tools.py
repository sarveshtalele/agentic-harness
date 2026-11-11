"""The find_tools harness tool: search the governed tool catalogue. Names and one-line descriptions only, no schemas."""
from __future__ import annotations

import json

from agent_framework import tool


def build(catalogue):
    @tool(name="find_tools", description="Search the tools you can load, by name or purpose (for example 'tests', 'document', 'workflow'). "
                                         "Returns names and one-line descriptions; call load_tools to use one. An empty query lists all.")
    def find_tools(query: str = "") -> str:
        found = catalogue.search(query)
        return json.dumps({"tools": found} if found else {"tools": [], "note": "No loadable tool matches. Try fewer or other words."})

    return find_tools
