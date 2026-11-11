"""Registry sources in platform code: the tool files, MAF's own harness tools, the governed agents and the harness.

Tool files are read with `ast` (the `@tool(name=..., description=...)` call), so nothing is built for a project. MAF's
harness tools are read from the installed `agent_framework` providers: each adds its tools in `before_run`, which here
gets a throwaway session and in-memory store, and no agent or model runs. Approval comes from `harness_kit/catalog.py`.
"""
from __future__ import annotations

import ast
import warnings

from backend.config import ROOT
from backend.core.registry.model import Cap, Graph, digest, one_line, rel

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
    from backend.maf.harness_kit.catalog import RISKY

    for path in sorted(TOOLS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for name, description in _tool_calls(ast.parse(text)):
            g.add(Cap("tool", name, name, one_line(description), rel(path), digest(text), needs_approval=name in RISKY))


async def _provider_tools(providers) -> list[tuple[str, object]]:
    from agent_framework import AgentSession, SessionContext

    found = []
    for provider in providers:
        context = SessionContext(session_id="registry", input_messages=[])
        await provider.before_run(agent=None, session=AgentSession(session_id="registry"), context=context, state={})
        found += [(type(provider).__name__, t) for t in context.tools]
    return found


def maf_builtins(g: Graph) -> None:
    """Todos, modes, file memory, file access, skills and the shell, as MAF builds them for the harness.

    ponytail: BackgroundAgentsProvider refuses to start without at least one built agent (and so a model), so its
    tools are not listed here; the harness's delegations are `delegates_to` links instead.
    """
    import agent_framework as af
    from agent_framework_tools.shell import LocalShellTool

    from backend.core.skills import _run
    from backend.maf import harness
    from backend.maf.harness_kit import shell

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # MAF marks the in-memory file store experimental
        providers = [af.TodoProvider(store=af.TodoSessionStore()), af.AgentModeProvider(default_mode="execute"),
                     af.FileMemoryProvider(af.InMemoryAgentFileStore()),
                     # read-only file access without approval, as maf/harness.py passes it (file_access_disable_readonly_tool_approval)
                     af.FileAccessProvider(af.InMemoryAgentFileStore(), disable_readonly_tool_approval=True),
                     harness._skills()]
        listed = _run(_provider_tools(providers))
    shell_tool = LocalShellTool().as_function(name=shell.NAME, description=shell.DESCRIPTION)
    for provider, tool in [*listed, ("ShellProvider", shell_tool)]:
        source = "src/backend/maf/harness_kit/shell.py" if provider == "ShellProvider" else f"agent_framework:{provider}"
        text = f"{provider}|{tool.name}|{tool.description}|{tool.approval_mode}"
        g.add(Cap("tool", tool.name, tool.name, one_line(tool.description), source, digest(text),
                  needs_approval=tool.approval_mode == "always_require", meta={"provider": provider}))


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


def harness_delegations(g: Graph) -> None:
    """The harness's background agents: the governed specialists, then every plugin agent (maf/harness.py adds both)."""
    from backend.maf.harness import AGENT
    from backend.maf.harness_kit.specialists import SPECIALISTS

    harness_id = g.aliases.get(("agent", AGENT))
    if not harness_id:
        return
    for key in SPECIALISTS:
        g.link_to(harness_id, "agent", key, "delegates_to", "specialist")
    for cid, cap in sorted(g.caps.items()):
        if cap.kind == "agent" and cap.plugin:
            g.link(harness_id, cid, "delegates_to", "plugin agent")

