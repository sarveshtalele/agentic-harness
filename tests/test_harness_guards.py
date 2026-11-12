"""Harness guards (FINAL_PLAN 5.3): the command's own check after writes, the turn budget, repeat reminders and trimmed
results. Only the model and, for the check, the sandbox runner are stood in for."""
from __future__ import annotations

from backend.core import plugins
from backend.maf.harness_kit import active_command
from tests.helpers_harness import steps
from tests.scripted_client import ScriptedClient

APP = "demo-app"
REQS = f"docs/qe/{APP}/02-requirements/requirements.json"


def test_done_means_the_commands_check_passes_not_that_a_file_exists(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from agent_framework import Agent, tool

    from backend.maf.harness_kit import verify, write_first

    command = active_command.parse(plugins.expand_slash(f"/agentic-qe:qe-requirements {APP}"))
    command["paths"] = [REQS]  # one owed file, so the guard's next reason is the check itself
    assert command["check"][0] == "node" and command["check"][1].endswith("check-gate.ts") and command["check"][2:] == ["--gate", "1", "--app", APP]
    ran = []

    def fake_run(project_id, argv, cwd, timeout, extra_env):  # stands in for the sandbox; the real check needs a .qe run
        ran.append(argv)
        return {"exit_code": 1, "stdout": "Gate 1 check for demo-app: FAIL\n- 02-requirements/requirements.json lists no requirements"}

    monkeypatch.setattr(verify.sandbox, "execute_command", fake_run)
    ws = SimpleNamespace(project_id="p", thread_id="thr_check", root=tmp_path, env=lambda: {})

    @tool(name="file_access_write", description="Write a file.")
    def write(file_name: str, content: str) -> str:
        (tmp_path / file_name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / file_name).write_text(content)
        return f"wrote {file_name}"

    @tool(name="read_file", description="Read a file.")
    def read_file(path: str) -> str:
        return "content"

    reads = [{"call": "read_file", "args": {"path": f"f{i}.py"}} for i in range(write_first.NUDGE)]
    scripted = ScriptedClient([("go", steps({"call": "file_access_write", "args": {"file_name": REQS, "content": '{"requirements": []}'}}, *reads, "done"))])
    scripted.function_invocation_configuration["max_iterations"] = write_first.NUDGE + 5
    middleware = [write_first.write_first("thr_check", tmp_path, command), verify.verifier(ws, command)]
    asyncio.run(Agent(scripted, tools=[write, read_file], middleware=middleware).run("go"))
    seen = "\n".join(scripted.calls)
    assert ran and "the command's check ran after this write: FAIL" in seen and "lists no requirements" in seen
    assert verify.last("thr_check")["passed"] is False
    assert "Write the fixes its check lists" in seen  # the file exists, but the guard keeps steering while the check fails


def test_a_turn_stops_cleanly_when_its_time_budget_is_spent():
    import asyncio

    from agent_framework import Agent, tool

    from backend.maf.harness_kit.budget import turn_budget

    @tool(name="read_file", description="Read a file.")
    def read_file(path: str) -> str:
        return "content"

    scripted = ScriptedClient([("go", steps({"call": "read_file", "args": {"path": "a.py"}}, "done"))])
    from backend.maf.harness_kit import budget

    asyncio.run(Agent(scripted, tools=[read_file], middleware=[turn_budget("thr_budget", minutes=-1)]).run("go"))
    assert "content" not in "\n".join(scripted.calls)  # the tool never ran
    assert "budget" in budget.stopped["thr_budget"]  # the chat route shows this as the reply


def test_repeated_calls_get_a_reminder_and_huge_results_are_trimmed():
    import asyncio

    from agent_framework import Agent, tool

    from backend.maf.harness_kit.tool_hygiene import HEAD, LIMIT, tool_hygiene

    @tool(name="read_file", description="Read a file.")
    def read_file(path: str) -> str:
        return "x" * (LIMIT + 5000) if path == "big.txt" else "small"

    same = {"call": "read_file", "args": {"path": "a.py"}}
    scripted = ScriptedClient([("go", steps(same, same, same, {"call": "read_file", "args": {"path": "big.txt"}}, "done"))])
    asyncio.run(Agent(scripted, tools=[read_file], middleware=[tool_hygiene()]).run("go"))
    seen = "\n".join(scripted.calls)
    assert "This is call 3 of read_file with these same arguments" in seen and "This is call 2 of" not in seen
    assert f"characters cut from the middle of this {LIMIT + 5000}-character result" in scripted.calls[-1]
    assert "x" * (HEAD + 1) not in scripted.calls[-1]  # the model never receives the whole result
