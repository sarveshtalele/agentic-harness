"""Routed permissions for helper agents (docs/PHASE2_PLAN.md section 10): writes and commands run only where a rule or the
mode allows them without a card; anything else goes back to the main agent."""
import asyncio
from types import SimpleNamespace

from agent_framework import Agent, tool

from backend.maf.harness_kit import permissions, plugin_agents
from tests.helpers_harness import steps
from tests.scripted_client import ScriptedClient


def run_gate(mode, rules, call):
    ran = []

    @tool(name="bash", description="Run a command.", approval_mode="never_require")
    def bash(command: str) -> str:
        ran.append(command)
        return "ran"

    scripted = ScriptedClient([("go", steps({"call": "bash", "args": {"command": call}}, "done"))])
    asyncio.run(Agent(scripted, tools=[bash], middleware=[permissions.subagent_gate(lambda: mode, lambda: rules)]).run("go"))
    return ran, "\n".join(scripted.calls)


def test_a_helper_runs_only_what_is_allowed_without_a_card():
    rules = {"allow": ["Bash(npm test)"], "ask": [], "deny": ["Bash(rm *)"]}
    assert run_gate("default", rules, "npm test")[0] == ["npm test"]
    ran, seen = run_gate("default", rules, "curl x")
    assert ran == [] and "main agent will do it with an approval card" in seen
    ran, seen = run_gate("bypass", rules, "rm -rf build")
    assert ran == [] and "denied by the permission rule Bash(rm *)" in seen


def test_build_gives_write_tools_only_to_agents_that_declare_them(tmp_path, monkeypatch):
    specs = [{"plugin": "p", "name": "p:reader", "body": "read", "description": "reads", "tools": ["Read", "Grep"], "ref": "r1"},
             {"plugin": "p", "name": "p:fixer", "body": "fix", "description": "fixes", "tools": ["Read", "Edit", "Bash"], "ref": "r2"}]
    monkeypatch.setattr(plugin_agents, "definitions", lambda: specs)
    monkeypatch.setattr(plugin_agents.llm, "client", lambda *a, **k: ScriptedClient([]))
    ws = SimpleNamespace(root=tmp_path, project_id="p", thread_id="t", user_id="u", env=lambda: {})
    reader, fixer = plugin_agents.build("p", "u", "m", ws, "acceptEdits", {"allow": [], "ask": [], "deny": []})
    assert "approval card" not in reader.description and "approval card" in fixer.description
    reader_access = next(p for p in reader.context_providers if p.__class__.__name__ == "FileAccessProvider")
    fixer_access = next(p for p in fixer.context_providers if p.__class__.__name__ == "FileAccessProvider")
    assert reader_access.disable_write_tools and not fixer_access.disable_write_tools
    assert fixer_access.disable_write_tool_approval  # no card it could not show; the gate decides instead
