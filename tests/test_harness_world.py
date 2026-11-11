"""Plan H2 on the real MAF stack (only the model is ScriptedClient), with a real git repository: the allowlisted shell asks
for approval, runs in the workspace without a shell and is audited; a program outside the allowlist is refused; the write
tool cannot leave the workspace; the web profile has 5 sandbox slots and refuses the sixth by naming the queue."""
from __future__ import annotations

import contextlib
import os

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.app import app
from backend.config import sandbox_dir
from backend.core.security import PathEscape
from backend.maf import harness, llm
from backend.maf.harness_kit import leases, shell
from backend.maf.harness_kit.workspace import WorkspaceStore
from tests.helpers_harness import NEEDLE, approve, interrupt_of, ledger_rows, project_with_repo, steps, turn
from tests.scripted_client import ScriptedClient


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        assert test_client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        yield test_client
    llm.set_client_override(None)


@pytest.fixture
def thread(client):
    project = project_with_repo(client)
    return client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()


def test_allowlist_rules():
    assert shell.refusal(["git", "status", "--short"]) is None and shell.refusal(["node", "x.ts"]) is None
    assert "not allowed" in shell.refusal(["rm", "-rf", "/"]) and "not allowed" in shell.refusal(["/usr/bin/node", "x"])
    assert "read-only verbs" in shell.refusal(["git", "commit", "-m", "x"]) and "read-only verbs" in shell.refusal(["git", "-c", "core.pager=sh", "log"])
    assert "--output" in shell.refusal(["git", "diff", "--output=/tmp/x"]) and "only lists" in shell.refusal(["git", "branch", "-D", "main"])


def test_command_outside_the_allowlist_is_refused_and_nothing_runs(client, thread):
    scripted = ScriptedClient([(NEEDLE, steps({"call": "run_shell", "args": {"command": "curl https://example.com"}}, "Refused."))])
    llm.set_client_override(scripted)
    first = turn(client, thread["id"], "Fetch the page", "r1")
    assert "run_shell" in interrupt_of(first)["message"]  # even a refused program gets the card first; MAF approves before the body runs
    approve(client, thread["id"], first, "r2")
    assert "Command rejected: curl is not allowed" in scripted.calls[-1]
    assert ledger_rows(thread["project_id"], "harness.shell") == []  # nothing ran, so no command row


def test_allowed_command_waits_for_approval_then_runs_in_the_workspace_and_is_audited(client, thread):
    command = 'python3 -c "import os; print(os.getcwd()); print(os.environ.get(\'ATLAS_ADMIN_PASSWORD\'))"'
    scripted = ScriptedClient([(NEEDLE, steps({"call": "run_shell", "args": {"command": command}}, "Ran it."))])
    llm.set_client_override(scripted)
    first = turn(client, thread["id"], "Where are you?", "r1")
    interrupt_of(first)
    assert ledger_rows(thread["project_id"], "harness.shell") == []  # not before a human answered
    approve(client, thread["id"], first, "r2")
    root = str(sandbox_dir(thread["project_id"]).resolve())
    assert root in scripted.calls[-1] and "exit_code: 0" in scripted.calls[-1]
    assert "None" in scripted.calls[-1]  # clean_sandbox_env: the platform's secrets are not in the command's environment
    [row] = ledger_rows(thread["project_id"], "harness.shell")
    assert row["data"]["exit_code"] == 0 and row["data"]["command"].startswith("python3 -c") and root in row["data"]["stdout_tail"]
    history = "".join(f.read_text(encoding="utf-8") for f in (harness.HARNESS_DIR / thread["project_id"] / "history").rglob("*") if f.is_file())
    assert "exit_code: 0" in history  # the shell result is kept in the per-call history like any other tool result


def test_rejected_command_never_runs(client, thread):
    llm.set_client_override(ScriptedClient([(NEEDLE, steps({"call": "run_shell", "args": {"command": "git status"}}, "Not run."))]))
    approve(client, thread["id"], turn(client, thread["id"], "Status?", "r1"), "r2", approved=False)
    assert ledger_rows(thread["project_id"], "harness.shell") == []


@pytest.mark.asyncio
async def test_the_store_cannot_leave_the_workspace_or_touch_protected_folders(tmp_path):
    store = WorkspaceStore(tmp_path / "ws")
    await store.write("docs/note.md", "ok")
    assert (tmp_path / "ws" / "docs" / "note.md").read_text() == "ok"
    for bad in ("../escape.txt", "/etc/escape.txt", "docs/../../escape.txt"):
        with pytest.raises(ValueError):
            await store.write(bad, "x")
    for protected in (".git/config", ".qe/run.json", "node_modules/x.js"):
        with pytest.raises(PathEscape):
            await store.write(protected, "x")
    assert not (tmp_path / "escape.txt").exists()


def test_write_tool_through_the_harness_needs_approval_and_stays_inside(client, thread):
    scripted = ScriptedClient([(NEEDLE, steps({"call": "file_access_write", "args": {"file_name": "../outside.txt", "content": "x"}}, "Done."))])
    llm.set_client_override(scripted)
    approve(client, thread["id"], turn(client, thread["id"], "Write outside", "r1"), "r2")
    assert "Could not write file '../outside.txt'" in scripted.calls[-1]
    assert not (sandbox_dir(thread["project_id"]).parent / "outside.txt").exists()
    llm.set_client_override(ScriptedClient([(NEEDLE, steps({"call": "file_access_write", "args": {"file_name": "notes/plan.md", "content": "# Plan"}}, "Written."))]))
    approve(client, thread["id"], turn(client, thread["id"], "Write a note", "r3"), "r4")
    assert (sandbox_dir(thread["project_id"]) / "notes" / "plan.md").read_text() == "# Plan"


def test_web_profile_has_five_sandbox_slots_and_refuses_the_sixth(client, thread, monkeypatch):
    monkeypatch.setattr(config, "PROFILE", "web")
    assert config.MAX_SANDBOXES == 5
    with contextlib.ExitStack() as held:
        for n in range(5):
            held.enter_context(leases.lease("shell", thread["project_id"], f"t{n}", "admin"))
        with pytest.raises(leases.SandboxBusy, match="Sandbox queue full: all 5"):
            with leases.lease("shell", thread["project_id"], "t6", "admin"):
                pass
        scripted = ScriptedClient([(NEEDLE, steps({"call": "run_shell", "args": {"command": "git status"}}, "Busy."))])
        llm.set_client_override(scripted)
        approve(client, thread["id"], turn(client, thread["id"], "Status?", "r1"), "r2")
        assert "Sandbox queue full" in scripted.calls[-1] and ledger_rows(thread["project_id"], "harness.shell") == []
    with leases.lease("shell", thread["project_id"], "t7", "admin") as lease_id:  # the slots are free again
        assert lease_id
    monkeypatch.setattr(config, "PROFILE", "local")
