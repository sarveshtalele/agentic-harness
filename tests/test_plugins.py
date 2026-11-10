"""Plugin discovery on fake plugin folders, and the read-only API against the real repo."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.core import plugins


def _skill(folder, name, extra=""):
    (folder / name).mkdir(parents=True)
    (folder / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: does {name}\n{extra}---\nbody\n", encoding="utf-8")


def _by_id(root):
    return {p.id: p for p in plugins.discover(root)}


def test_own_manifest_and_claude_manifest(tmp_path):
    own = tmp_path / "plugins" / "a"
    own.mkdir(parents=True)
    (own / "plugin.json").write_text(json.dumps({"id": "alpha", "version": "1.2", "description": "d", "skills": "sk"}))
    _skill(own / "sk", "one")
    claude = tmp_path / "plugins" / "b"
    (claude / ".claude-plugin").mkdir(parents=True)
    (claude / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "beta", "version": "2"}))
    _skill(claude / "skills", "two")
    found = _by_id(tmp_path)
    assert found["alpha"].version == "1.2" and found["alpha"].skills_dir == (own / "sk").resolve() and found["alpha"].manifest == "plugin.json" and not found["alpha"].problems
    assert found["beta"].manifest == ".claude-plugin/plugin.json" and found["beta"].skills_dir is not None and found["beta"].trust == "first-party"


def test_missing_manifest_is_listed_with_problem(tmp_path):
    folder = tmp_path / "plugins" / "bare"
    _skill(folder / "skills", "x")
    found = _by_id(tmp_path)["bare"]
    assert found.version == "" and "no manifest" in found.problems and found.skills_dir is not None


def test_invalid_json_is_a_problem_not_a_crash(tmp_path):
    folder = tmp_path / "plugins" / "bad"
    folder.mkdir(parents=True)
    (folder / "plugin.json").write_text("{nope")
    assert any("plugin.json" in p for p in _by_id(tmp_path)["bad"].problems)


def test_skills_path_escape_refused(tmp_path):
    folder = tmp_path / "plugins" / "evil"
    folder.mkdir(parents=True)
    (tmp_path / "escape").mkdir()
    (folder / "plugin.json").write_text(json.dumps({"skills": "../escape"}))
    found = _by_id(tmp_path)["evil"]
    assert found.skills_dir is None and any("escapes" in p for p in found.problems)


def test_command_skill_detection(tmp_path):
    _skill(tmp_path, "qe-run", "disable-model-invocation: true\n")
    _skill(tmp_path, "plain")
    _skill(tmp_path, "off", "disable-model-invocation: false\n")
    assert plugins.command_skill_names(tmp_path) == {"qe-run"}


def test_skill_paths_local_first(tmp_path):
    folder = tmp_path / "plugins" / "p"
    _skill(folder / "skills", "x")
    paths = plugins.skill_paths(tmp_path)
    assert paths[0] == plugins.SKILLS_DIR and paths[-1] == (folder / "skills").resolve() and len(paths) == len(set(paths))


def test_api_needs_sign_in_and_lists_real_plugins():
    with TestClient(app) as anon:
        assert anon.get("/api/plugins").status_code == 401
    import os

    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
        body = {p["id"]: p for p in client.get("/api/plugins").json()}
    assert body["local-skills"]["skills"] > 0
    qe = body["agentic-qe"]
    assert qe["skills"] > 0 and {"qe-start", "qe-plan", "qe-generate"} <= set(qe["commands"]) and qe["problems"] == ["no manifest"]
