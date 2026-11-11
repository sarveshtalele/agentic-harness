"""A plugin's `agents/*.md` (Claude Code sub-agents) as MAF background agents of the harness (plan H3).

Each file's front matter gives the name, description and tools; its body is the agent's instructions. The agent is named
`<plugin>:<name>`, as Claude Code names plugin agents, so it never clashes with the governed specialists. Read, Glob, Grep
and LS map to MAF's read-only file access tools on the thread's workspace, with no approval needed. Write, Edit and Bash are
not given: MAF background agents run without an approval channel (`bg_agent.run` returns an approval request nobody can
answer), and every write or command in the harness needs a human's yes, so the harness itself does those steps. Read-only
agents such as `confidence-reviewer` and `coverage-auditor` therefore stay read-only.

Every tool call is audited under the agent's own name; model rounds count against the harness's governance and allowance.
When one finishes, the plugins' SubagentStop hooks run with `agent_type` and `last_assistant_message`, which is how
agentic-qe records the reviewers' verdicts itself; the hooks' notes are added to the agent's answer for the harness.
"""
from __future__ import annotations

import asyncio
import json
import logging

from agent_framework import Agent, Content, FileAccessProvider, Message, agent_middleware

from backend.core import auth, plugin_grants, plugin_hooks, plugins
from backend.core.security import sha256
from backend.maf import governance, llm
from backend.maf.harness_kit.workspace import WorkspaceStore
from backend.maf.runtime import tool_audit

READ = frozenset({"Read", "Glob", "Grep", "LS"})
LOG = logging.getLogger("aqe.chat")


def definitions() -> list[dict]:
    """Every agent file of every enabled plugin this user may use: plugin, name, description, tools, body, ref."""
    granted = plugin_grants.allowed(plugin_grants.role_of(auth.current_user.get()))
    found = []
    for plugin in plugins.discover():
        if plugin.id == "local-skills" or not plugin.enabled or not granted(plugin.id) or not (plugin.root / "agents").is_dir():
            continue
        for path in sorted((plugin.root / "agents").glob("*.md")):
            front, body = plugins._split(path)
            raw = front.get("tools") or []
            names = [str(t).strip() for t in (raw.split(",") if isinstance(raw, str) else raw) if str(t).strip()]
            found.append({"plugin": plugin.id, "name": f"{plugin.id}:{front.get('name') or path.stem}", "body": body.strip(),
                          "description": " ".join(str(front.get("description", "")).split()), "tools": names,
                          "ref": f"plugin:{plugin.id}/agents/{path.name}@{sha256(path.read_text(encoding='utf-8'))[:12]}"})
    return found


def _on_stop(name: str, workspace):
    @agent_middleware
    async def stopped(context, call_next) -> None:
        await call_next()
        text = getattr(context.result, "text", "") or ""
        outcome = await asyncio.to_thread(plugin_hooks.dispatch, "SubagentStop", {
            "session_id": workspace.thread_id, "agent_type": name, "agent_id": name, "last_assistant_message": text, "stop_hook_active": False},
            project_id=workspace.project_id, project_dir=workspace.root, env_extra=workspace.env())
        notes = outcome.context + [f"Hook problem (reported, not fatal): {e}" for e in outcome.errors]
        if notes and context.result is not None:
            context.result.messages.append(Message(role="assistant", contents=[Content.from_text("\n".join(notes))]))

    return stopped


def build(project_id: str, user_id: str | None, model: str, workspace) -> list[Agent]:
    """The plugin agents for one harness turn. Without a workspace (no repository) there is nothing for them to read."""
    if workspace is None:
        return []
    agents = []
    for spec in definitions():
        readable = bool(READ & set(spec["tools"]))
        kept_back = sorted(set(spec["tools"]) - READ)
        providers = [FileAccessProvider(WorkspaceStore(workspace.root), disable_write_tools=True, disable_readonly_tool_approval=True)] if readable else []
        note = f" In this harness it only reads; {', '.join(kept_back)} stay with the harness, which asks the user first." if kept_back else ""
        telemetry = governance.telemetry("harness", project_id, None, "chat", model, user_id, spec["ref"], json.dumps([spec["name"]]))
        agents.append(Agent(client=llm.client(model), name=spec["name"], description=spec["description"] + note, instructions=spec["body"],
                            context_providers=providers, middleware=[tool_audit(spec["name"], project_id, None, "chat"), telemetry, _on_stop(spec["name"], workspace)]))
    LOG.info("harness: %d plugin agents for project %s", len(agents), project_id)
    return agents
