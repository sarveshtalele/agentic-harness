"""OS sandbox tier T1 (docs/PHASE2_PLAN.md section 5.3): Seatbelt on macOS, bubblewrap on Linux, none on Windows.

The confinement test runs real commands inside the real sandbox and is skipped by name where the machine has none
(Windows, or a Linux runner without bwrap); the rules around it run everywhere.
"""
import asyncio
import json
import sys
import time
from types import SimpleNamespace

import pytest

from backend.maf.harness_kit import os_sandbox, permissions, shells

HAS_SANDBOX = os_sandbox.kind() is not None


@pytest.fixture
def ws(tmp_path, monkeypatch):
    root, scratch = tmp_path / "repo", tmp_path / "scratch"
    root.mkdir()
    scratch.mkdir()
    monkeypatch.setattr(shells.ledger, "append", lambda *a, **k: None)
    return SimpleNamespace(project_id="prj_t", thread_id=f"thr_{time.monotonic_ns()}", user_id="u", root=root.resolve(),
                           scratch=scratch.resolve(), env=lambda: {})


def test_auto_mode_skips_the_card_for_shells_only_inside_the_sandbox():
    call = {"command": "npm test", "description": "run tests"}
    assert permissions.decide("bash", call, "auto", {}, sandboxed=True)[0] == "allow"
    assert permissions.decide("bash", call, "auto", {}, sandboxed=False)[0] == "ask"
    assert permissions.decide("bash", call, "default", {}, sandboxed=True)[0] == "ask"  # the sandbox alone never approves
    assert permissions.decide("bash", call, "auto", {"deny": ["Bash(npm *)"]}, sandboxed=True)[0] == "deny"


def test_sandbox_is_on_in_auto_mode_or_from_trusted_settings_only(tmp_path, monkeypatch):
    monkeypatch.setattr(os_sandbox, "kind", lambda: "seatbelt")
    monkeypatch.setattr(os_sandbox.settings_files.Path, "home", lambda: tmp_path / "home")
    project = tmp_path / "proj"
    (project / ".aqh").mkdir(parents=True)
    (project / ".aqh" / "settings.json").write_text(json.dumps({"sandbox": {"enabled": True, "network": True}}))
    assert os_sandbox.active("auto", project) and not os_sandbox.active("default", project)  # a repository cannot turn it on
    (tmp_path / "home" / ".aqh").mkdir(parents=True)
    (tmp_path / "home" / ".aqh" / "settings.json").write_text(json.dumps({"sandbox": {"enabled": True}}))
    assert os_sandbox.active("default", project) and os_sandbox.settings(project) == {"enabled": True, "network": False}
    monkeypatch.setattr(os_sandbox, "kind", lambda: None)
    assert not os_sandbox.active("auto", project) and os_sandbox.wrap(["bash"], None) == ["bash"]  # Windows: no sandbox, cards stay


@pytest.mark.skipif(not (HAS_SANDBOX and shells.find_bash()), reason="no OS sandbox (Seatbelt or bubblewrap) or no bash here")
def test_a_sandboxed_shell_writes_only_in_the_workspace_and_has_no_network(ws, tmp_path, monkeypatch):
    monkeypatch.setattr(os_sandbox, "writable", lambda w: [w.root])  # the temp folder holds tmp_path, so keep only the root
    outside = tmp_path / "outside.txt"
    py = sys.executable.replace("\\", "/")
    net = f"\"{py}\" -c \"import socket; socket.create_connection(('1.1.1.1', 53), 3); print('NET' + '-OPEN')\""

    async def go():
        try:
            box = {"network": False}
            return [await shells.run(ws, "bash", c, sandbox=box) for c in
                    ("echo in > inside.txt && cat inside.txt", f"echo out > '{outside}'", net)]
        finally:
            await shells.close_thread(ws.thread_id)

    inside, wrote_outside, network = asyncio.run(go())
    assert "in" in inside and (ws.root / "inside.txt").read_text().strip() == "in"
    assert not outside.exists() and ("not permitted" in wrote_outside.lower() or "read-only" in wrote_outside.lower())
    assert "NET-OPEN" not in network.replace("'NET' + '-OPEN'", "") and "exit code 1" in network  # the traceback quotes the source
