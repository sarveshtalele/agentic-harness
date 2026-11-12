"""The aqh CLI (docs/PHASE2_PLAN.md section 11.1): headless turns over AG-UI in a folder bound in place, output formats,
approval policy, session JSONL, and the model settings' precedence. The platform runs in-process (FastAPI's TestClient
is an httpx client, which is all aqh.client needs); the model is the scripted stand-in."""
import io
import json
import os

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.app import app
from backend.core import cli_workspaces
from backend.maf import llm
from backend.maf.harness_kit import shells
from tests.helpers_harness import NEEDLE, steps
from tests.scripted_client import ScriptedClient


@pytest.fixture
def cli(tmp_path, monkeypatch):
    folder, home = tmp_path / "my-app", tmp_path / "aqh-home"
    folder.mkdir()
    (folder / "README.md").write_text("# My app\n", encoding="utf-8")
    monkeypatch.setenv("AQH_HOME", str(home))
    monkeypatch.setattr(config, "PROFILE", "cli")
    monkeypatch.setattr(cli_workspaces, "FILE", tmp_path / "cli-workspaces.json")
    from aqh.client import Session

    with TestClient(app) as http:
        session = Session(http)
        session.login("qa-admin", os.environ["ATLAS_ADMIN_PASSWORD"])
        project = session.project_for(folder)
        yield session, project, folder, home
    llm.set_client_override(None)


def headless(cli, prompt, **kw):
    from aqh import headless as h

    session, project, folder, _ = cli
    out = io.StringIO()
    code = h.run(session, project, session.new_thread(project), prompt, folder=folder, out=out, **kw)
    return code, out.getvalue()


def test_a_headless_answer_in_each_format_and_the_session_log(cli):
    llm.set_client_override(ScriptedClient([(NEEDLE, steps("The app is a tiny shop."))]))
    code, text = headless(cli, "what is this?")
    assert code == 0 and text.strip() == "The app is a tiny shop."
    code, out = headless(cli, "what is this?", output="json")
    result = json.loads(out)
    assert result["type"] == "result" and result["result"] == "The app is a tiny shop." and not result["is_error"]
    code, out = headless(cli, "what is this?", output="stream-json")
    events = [json.loads(line) for line in out.splitlines()]
    assert events[0]["type"] == "RUN_STARTED" and events[-1]["type"] == "result"
    logs = list((cli[3] / "projects").rglob("*.jsonl"))
    assert logs and any('"USER_TEXT"' in p.read_text() for p in logs)  # each session is kept as JSON lines


@pytest.mark.skipif(not shells.find_bash(), reason="no bash on this machine")
def test_an_allowed_command_runs_in_the_real_folder_and_others_are_refused(cli):
    _, _, folder, _ = cli
    call = {"call": "bash", "args": {"command": "echo hello > note.txt", "description": "write a note"}}
    llm.set_client_override(ScriptedClient([(NEEDLE, steps(call, "Wrote it."))]))
    code, text = headless(cli, "write a note", allowed=["Bash(echo *)"])
    assert code == 0 and (folder / "note.txt").read_text().strip() == "hello"  # edited in place, not in a sandbox copy
    (folder / "note.txt").unlink()
    llm.set_client_override(ScriptedClient([(NEEDLE, steps(call, "Could not."))]))
    code, text = headless(cli, "write a note")
    assert code == 1 and "Not approved" in text and not (folder / "note.txt").exists()


def test_model_settings_precedence_never_needs_the_key_printed(tmp_path, monkeypatch):
    from aqh import settings

    monkeypatch.setenv("AQH_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    monkeypatch.setattr(settings, "keychain_get", lambda: None)
    settings.save_model("https://user.example/v1", "user-model")
    project = tmp_path / "proj"
    (project / ".aqh").mkdir(parents=True)
    (project / ".aqh" / "settings.json").write_text(json.dumps({"model": {"name": "project-model"}}))
    found = settings.model({"base_url": None}, cwd=project)
    assert (found["base_url"], found["name"], found["api_key"]) == ("https://user.example/v1", "project-model", "from-env")
    assert found["sources"] == {"base_url": "~/.aqh/settings.json", "name": "project .aqh/settings.json", "api_key": "environment OPENAI_API_KEY"}


def test_folders_are_bound_only_by_the_cli_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILE", "web")
    with pytest.raises(PermissionError):
        cli_workspaces.bind("prj_x", str(tmp_path))


def test_the_interactive_prompt_names_the_real_command():
    from rich.console import Console

    from aqh import repl

    console = Console(file=io.StringIO(), width=120)
    printer = repl._printer(console)
    for event in ({"type": "TOOL_CALL_START", "toolCallId": "c1", "toolCallName": "bash"},
                  {"type": "TOOL_CALL_ARGS", "toolCallId": "c1", "delta": '{"command": "npm test", "description": "run tests"}'},
                  {"type": "TOOL_CALL_END", "toolCallId": "c1"}):
        printer(event)
    asked = []
    decide = repl._decider(console, lambda question: asked.append(question) or "y", printer.calls)
    assert decide({"toolCallId": "c1", "message": "Approve running bash?"}) is True
    assert "bash: npm test" in asked[0]
    assert "● bash" in console.file.getvalue() and "npm test" in console.file.getvalue()
