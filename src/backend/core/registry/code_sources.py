"""Registry sources in platform code: the tool files and the governed agents.

Tool files are read with `ast` (the `@tool(name=..., description=...)` call), so nothing is built for a project.
"""
from __future__ import annotations

import ast

from backend.config import ROOT
from backend.core.registry.model import Cap, Graph, digest, one_line, rel

# These write or run code, so a person approves each call. Every MCP tool is treated the same.
RISKY = frozenset({"start_workflow", "run_tests", "save_document", "remember", "create_skill"})
TOOLS_DIR = ROOT / "src" / "backend" / "maf" / "tools"
AGENTS_DIR = ROOT / "src" / "backend" / "maf" / "agents"


def _tool_calls(tree: ast.AST):
    """Every `tool(name="...", description="...")` call with literal strings (implicit concatenation included)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "tool":
            found = {k.arg: k.value.value for k in node.keywords if isinstance(k.value, ast.Constant) and isinstance(k.value.value, str)}
            if "name" in found:
                yield found["name"], found.get("description", "")


def platform_tools(g: Graph) -> None:
    for path in sorted(TOOLS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for name, description in _tool_calls(ast.parse(text)):
            g.add(Cap("tool", name, name, one_line(description), rel(path), digest(text), needs_approval=name in RISKY))


def agents(g: Graph) -> None:
    from backend.maf.agents import POLICIES
    from backend.maf.governance.policy import settings

    for key, policy in POLICIES.items():
        path = AGENTS_DIR / f"{key.replace('-', '_')}.py"
        cid = g.add(Cap("agent", key, key, policy.purpose, rel(path), digest(path.read_text(encoding="utf-8")), risk=policy.risk,
                        enabled=bool(settings(key)["enabled"]),
                        meta={"title": policy.name, "can_change_code": policy.can_change_code, "in_chat": policy.chat_tools is not None}))
        for tool in sorted(set(policy.chat_tools or ()) | set(policy.workflow_tools)):
            g.link_to(cid, "tool", tool, "uses_tool")
        for skill in policy.skills:
            g.link_to(cid, "skill", f"local-skills/{skill}", "applies_skill")  # policy skills are folders under skills/
