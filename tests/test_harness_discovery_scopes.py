"""Tool and skill discovery (docs/PHASE2_PLAN.md section 8, step 4): skill scopes, the tool index's arguments, nearest
names for an invented tool, Claude Code's command substitutions, and the MCP tool-list refresh."""
import io
import os
import zipfile
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend import config
from backend.app import app
from backend.core.command_args import substitute
from backend.core.mcp import harness as mcp_harness
from backend.maf import llm
from backend.maf.harness_kit import skill_scopes
from backend.maf.harness_kit.catalog import signature
from backend.maf.harness_kit.unknown_tools import suggest
from tests.helpers_harness import NEEDLE, steps, turn
from tests.scripted_client import ScriptedClient

SKILL = "---\nname: release-notes\ndescription: Draft release notes from CHANGELOG.md. Use when asked for release notes.\n---\nRead CHANGELOG.md.\n"


def test_skill_precedence_is_personal_then_project_then_plugins(tmp_path, monkeypatch):
    home, repo, plugin = tmp_path / "home", tmp_path / "repo", tmp_path / "plugin-skills"
    for folder in (home / ".claude" / "skills", repo / ".claude" / "skills", repo / ".agents" / "skills", repo / ".github" / "skills", plugin):
        folder.mkdir(parents=True)
    monkeypatch.setattr(skill_scopes.Path, "home", lambda: home)
    monkeypatch.setattr(config, "PROFILE", "desktop")
    order = [p.relative_to(tmp_path).as_posix() for p in map(skill_scopes.Path, skill_scopes.ordered(repo, [plugin]))]
    assert order == ["home/.claude/skills", "repo/.claude/skills", "repo/.github/skills", "repo/.agents/skills", "plugin-skills"]
    monkeypatch.setattr(config, "PROFILE", "web")  # the shared server has no personal folder of yours
    assert "home/.claude/skills" not in [p.relative_to(tmp_path).as_posix() for p in map(skill_scopes.Path, skill_scopes.ordered(repo, [plugin]))]
    assert "repository content" in skill_scopes.note(repo)


def test_claude_code_substitutions():
    body = "Migrate $component from $from to $to; first $0, second $ARGUMENTS[1]; all: $ARGUMENTS; costs \\$5; $HOME; ${CLAUDE_PROJECT_DIR}"
    out = substitute(body, '"Search Bar" JavaScript TypeScript', ["component", "from", "to"], "/ws")
    assert out.startswith("Migrate Search Bar from JavaScript to TypeScript; first Search Bar, second JavaScript")
    assert "costs $5; $HOME; /ws" in out  # shell variables are left for the shell
    assert substitute("No placeholder.", "a b").endswith("ARGUMENTS: a b")


def test_index_shows_arguments_and_invented_names_get_the_nearest_real_ones():
    assert signature({"properties": {"directory": {}, "depth": {}}, "required": ["directory"]}) == "(directory, depth?)"
    assert "bash" in suggest("shell_exec", {"bash", "file_access_read"}, set())
    hint = suggest("run_test", {"bash"}, {"run_tests"})
    assert "run_tests" in hint and "load_tools first" in hint


def test_mcp_refresh_lists_only_stale_connected_servers(monkeypatch):
    old = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()
    servers = [{"id": "s_old", "status": "connected", "transport": "http", "tools_listed_at": old},
               {"id": "s_new", "status": "connected", "transport": "http", "tools_listed_at": fresh},
               {"id": "s_err", "status": "error", "transport": "http", "tools_listed_at": old}]
    monkeypatch.setattr(mcp_harness.registry, "all_servers", lambda: servers)
    monkeypatch.setattr(mcp_harness.registry, "CONNECTED", "connected")
    called = []

    async def fake_connect(server_id):
        called.append(server_id)

    import backend.core.mcp.connect as connect_module
    monkeypatch.setattr(connect_module, "connect", fake_connect)
    assert mcp_harness.refresh_stale() == ["s_old"]


def test_a_repository_skill_reaches_the_harness_and_a_wrong_tool_name_gets_a_hint():
    scripted = ScriptedClient([(NEEDLE, steps({"call": "shell_exec", "args": {"command": "ls"}}, "done"))])
    llm.set_client_override(scripted)
    try:
        with TestClient(app) as client:
            assert client.post("/api/auth/login", json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}).status_code == 200
            project = client.post("/api/projects", json={"name": "Skill scopes", "description": "repository skills"}).json()
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as bundle:
                bundle.writestr("CHANGELOG.md", "# Changelog\n")
                bundle.writestr(".claude/skills/release-notes/SKILL.md", SKILL)
            assert client.post(f"/api/projects/{project['id']}/repo/zip", files={"file": ("r.zip", buffer.getvalue(), "application/zip")}).status_code == 200
            thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "harness"}).json()
            turn(client, thread["id"], "write release notes", "r1")
            first = scripted.calls[0]
            assert "release-notes" in first and "Skills from this repository" in first  # found in .claude/skills, marked as repository content
            assert any("Closest real tools:" in call for call in scripted.calls[1:])  # the invented shell_exec got real names back
    finally:
        llm.set_client_override(None)
