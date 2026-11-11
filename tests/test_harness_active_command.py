"""A typed plugin command stays the thread's active command (plan.md "Plugin command focus"): its instructions are in the
model's instructions on every call, the files it may create are shown as written or missing on disk, and the platform's
own QE and repository tools are not offered while it runs. Real plugin, real git repository; only the model is scripted."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.config import sandbox_dir
from backend.core import plugins
from backend.maf import llm
from backend.maf.agui import thread_messages
from backend.maf.harness_kit import active_command
from tests.helpers_harness import NEEDLE, project_with_repo, steps, turn
from tests.scripted_client import ScriptedClient

APP = "demo-app"
REQS = f"docs/qe/{APP}/02-requirements/requirements.json"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


@pytest.fixture
def thread(client):
    project = project_with_repo(client, "Command shop")
    return client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()


def test_the_command_text_gives_its_name_arguments_and_files():
    found = active_command.parse(plugins.expand_slash(f"/agentic-qe:qe-requirements {APP}"))
    assert found["name"] == "agentic-qe:qe-requirements" and found["args"] == APP
    assert found["paths"] == [REQS, f"docs/qe/{APP}/02-requirements/requirements.md"]  # the plugin's own .qe/ is never listed
    design = active_command.parse(plugins.expand_slash(f"/agentic-qe:qe-design {APP}"))["paths"]
    assert design == [f"docs/qe/{APP}/04-design/test_cases.json", f"docs/qe/{APP}/04-design/test_cases.md"]  # never the files the plugin writes itself
    assert active_command.parse(plugins.expand_slash(f"/agentic-qe:qe-generate {APP}"))["paths"] == [f"docs/qe/{APP}/05-generation/manifest.json"]  # greenfield-only aside left out
    assert active_command.parse("Load the skill planning-tests with load_skill, then use it") is None
    assert active_command.parse("hello") is None


def test_the_active_command_is_pinned_and_the_platform_qe_tools_step_aside(client, thread):
    scripted = ScriptedClient([(NEEDLE, steps("Reading the routes."))])
    llm.set_client_override(scripted)
    turn(client, thread["id"], "what is in this repository?", "r0")
    assert "read_file" in scripted.tools[-1] and "ACTIVE PLUGIN COMMAND" not in scripted.calls[-1]

    turn(client, thread["id"], f"/agentic-qe:qe-requirements {APP}", "r1")
    seen, offered = scripted.calls[-1], scripted.tools[-1]
    assert f"ACTIVE PLUGIN COMMAND: /agentic-qe:qe-requirements {APP}" in seen and f"- {REQS}: MISSING" in seen
    assert seen.count('<command name="agentic-qe:qe-requirements">') == 1  # in the instructions only, not again in the history
    assert {"file_access_write", "run_shell"} <= set(offered)
    assert not set(offered) & active_command.PLATFORM_QE_TOOLS
    assert thread_messages(thread["id"])[-2]["content"] == f"/agentic-qe:qe-requirements {APP}"  # the chat keeps what was typed

    written = sandbox_dir(thread["project_id"]) / REQS  # the step's file appears on disk (in a real run, an approved write)
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text('{"requirements": []}', encoding="utf-8")
    turn(client, thread["id"], "continue", "r2")
    seen = scripted.calls[-1]
    assert f"ACTIVE PLUGIN COMMAND: /agentic-qe:qe-requirements {APP}" in seen and f"- {REQS}: written (20 bytes)" in seen
    assert not set(scripted.tools[-1]) & active_command.PLATFORM_QE_TOOLS

    turn(client, thread["id"], f"/agentic-qe:qe-plan {APP}", "r3")  # the next command replaces it
    assert f"ACTIVE PLUGIN COMMAND: /agentic-qe:qe-plan {APP}" in scripted.calls[-1] and "qe-requirements" not in scripted.calls[-1].split("<command")[0]


def test_an_unknown_tool_argument_is_an_error_the_model_reads():
    import asyncio

    from agent_framework import Agent, tool

    from backend.maf.harness_kit.strict_args import strict_arguments

    @tool(name="ls", description="List a directory.")
    def ls(directory: str | None = None) -> str:
        return f"listed {directory}"

    scripted = ScriptedClient([("Extra inputs are not permitted", "fixed"), ("go", {"call": "ls", "args": {"path": "src"}})])
    scripted.function_invocation_configuration["include_detailed_errors"] = True  # what llm.client(detailed_errors=True) sets
    assert asyncio.run(Agent(scripted, tools=[ls], middleware=[strict_arguments]).run("go")).text == "fixed"
    assert "path" in scripted.calls[-1] and "listed" not in scripted.calls[-1]  # never the root listing for a misnamed argument


def test_reads_turn_into_writes_while_the_command_owes_files(tmp_path):
    import asyncio

    from agent_framework import Agent, tool

    from backend.maf.harness_kit import write_first

    @tool(name="read_file", description="Read a file.")
    def read_file(path: str) -> str:
        return f"content of {path}"

    command = {"name": "agentic-qe:qe-requirements", "args": APP, "body": "", "paths": [REQS]}
    reads = [{"call": "read_file", "args": {"path": f"f{i}.py"}} for i in range(write_first.LIMIT + 2)]
    scripted = ScriptedClient([("Refused:", "stopped reading"), ("go", steps(*reads, "done"))])
    scripted.function_invocation_configuration["max_iterations"] = write_first.LIMIT + 5
    asyncio.run(Agent(scripted, tools=[read_file], middleware=[write_first.write_first("thr_wf", tmp_path, command)]).run("go"))
    seen = "\n".join(scripted.calls)
    assert f"{write_first.NUDGE} reads in a row without a write. Write {REQS} now" in seen
    assert f"Refused: {write_first.LIMIT} reads in a row and nothing written while {REQS} is missing" in seen
    (tmp_path / REQS).parent.mkdir(parents=True)
    (tmp_path / REQS).write_text("{}")  # once the file exists nothing is counted or refused
    write_first._reads["thr_wf"] = 0
    again = ScriptedClient([("go", steps(*reads[:3], "done"))])
    asyncio.run(Agent(again, tools=[read_file], middleware=[write_first.write_first("thr_wf", tmp_path, command)]).run("go"))
    assert "[harness]" not in "\n".join(again.calls) and write_first._reads["thr_wf"] == 0


def test_files_that_wait_for_a_gate_are_never_pushed_out_early(tmp_path):
    start = active_command.parse(plugins.expand_slash(f"/agentic-qe:qe-start {APP} --mode brownfield"))
    assert start["after_gate"] == 0 and active_command.parse(plugins.expand_slash(f"/agentic-qe:qe-requirements {APP}"))["after_gate"] is None
    import asyncio

    from agent_framework import Agent, tool

    from backend.maf.harness_kit import write_first

    @tool(name="read_file", description="Read a file.")
    def read_file(path: str) -> str:
        return f"content of {path}"

    reads = [{"call": "read_file", "args": {"path": f"f{i}.py"}} for i in range(write_first.LIMIT + 2)]
    scripted = ScriptedClient([("go", steps(*reads, "done"))])
    scripted.function_invocation_configuration["max_iterations"] = write_first.LIMIT + 5
    asyncio.run(Agent(scripted, tools=[read_file], middleware=[write_first.write_first("thr_gate", tmp_path, start)]).run("go"))
    assert "Refused:" not in "\n".join(scripted.calls) and "[harness]" not in "\n".join(scripted.calls)
