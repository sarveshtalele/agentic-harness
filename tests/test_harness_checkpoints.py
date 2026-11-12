"""File checkpoints and /rewind (docs/PHASE2_PLAN.md section 10)."""
import os
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app import app
from backend.config import sandbox_dir
from backend.maf import llm
from backend.maf.harness_kit import checkpoints
from tests.helpers_harness import NEEDLE, approve, project_with_repo, steps, turn
from tests.scripted_client import ScriptedClient


def test_rewind_restores_each_file_to_before_the_chosen_turn(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoints.ledger, "append", lambda *a, **k: None)
    root, store = tmp_path / "ws", tmp_path / "checkpoints"
    root.mkdir()
    (root / "a.py").write_text("v1\n", encoding="utf-8")
    ws = SimpleNamespace(root=root, project_id="p", thread_id="t", user_id="u")
    for turn_id, new_a, new_b in (("20261113-100000-000001", "v2\n", "made\n"), ("20261113-110000-000002", "v3\n", "made again\n")):
        checkpoints.save(ws, store, turn_id, "a.py")
        checkpoints.save(ws, store, turn_id, "b.py")
        checkpoints.save(ws, store, turn_id, "a.py")  # a second change in the same turn keeps the first snapshot
        (root / "a.py").write_text(new_a, encoding="utf-8")
        (root / "b.py").write_text(new_b, encoding="utf-8")
    assert "1. 10:00:00" in checkpoints.listing(store) and "2. 11:00:00" in checkpoints.listing(store)
    assert "Rewound 2 file(s)" in checkpoints.rewind(ws, store, 2)
    assert (root / "a.py").read_text() == "v2\n" and (root / "b.py").read_text() == "made\n"
    checkpoints.rewind(ws, store, 1)
    assert (root / "a.py").read_text() == "v1\n" and not (root / "b.py").exists()  # b.py did not exist before turn 1


def test_a_harness_write_is_checkpointed_and_rewind_answers_without_the_model():
    scripted = ScriptedClient([(NEEDLE, steps({"call": "file_access_write", "args": {"file_name": "app.py", "content": "def add(a, b):\n    return 0\n", "overwrite": True}}, "done"))])
    llm.set_client_override(scripted)
    try:
        with TestClient(app) as client:
            assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
            project = project_with_repo(client, "Rewind shop")
            thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
            approve(client, thread["id"], turn(client, thread["id"], "break add", "r1"), "r2")
            app_py = sandbox_dir(project["id"]) / "app.py"
            assert "return 0" in app_py.read_text()
            calls = len(scripted.calls)
            listed = "".join(e.get("delta", "") for e in turn(client, thread["id"], "/rewind", "r3") if e["type"] == "TEXT_MESSAGE_CONTENT")
            assert "1." in listed and "app.py" in listed
            done = "".join(e.get("delta", "") for e in turn(client, thread["id"], "/rewind 1", "r4") if e["type"] == "TEXT_MESSAGE_CONTENT")
            assert "Rewound 1 file(s)" in done and "return a + b" in app_py.read_text()
            assert len(scripted.calls) == calls  # the model was not called for /rewind
    finally:
        llm.set_client_override(None)
