"""Real MCP over stdio: the fixture server in tests/fixtures is started through MAF's MCPStdioTool. Nothing is mocked."""
import shutil
import sys

import pytest

from backend import config
from backend.config import LOGS, ROOT
from backend.core import auth
from backend.core.mcp import mcp_tools_for
from backend.db import db
from tests.helpers_api import client, make_user, sign_in, unique  # noqa: F401 - fixtures

ECHO = str(ROOT / "tests" / "fixtures" / "mcp_echo_server.py")
ADMIN = {"id": auth.ADMIN_ID, "role": "admin", "account_role": "admin"}


@pytest.fixture
def echo(client):
    marker = unique("envvalue-")  # made fresh per test; it must never come back or reach a log
    made = client.post("/api/mcp/servers", json={"name": "echo", "command": sys.executable, "args": [ECHO], "env": {"ECHO_FIXTURE_VALUE": marker}})
    assert made.status_code == 201, made.text
    yield made.json()["id"], marker
    client.delete(f"/api/mcp/servers/{made.json()['id']}")


@pytest.fixture
def project(client):
    return client.post("/api/projects", json={"name": "MCP calls"}).json()["id"]


def _grant(client, sid, tool, role):
    made = client.post("/api/mcp/grants", json={"server_id": sid, "tool_name": tool, "role": role})
    assert made.status_code == 201, made.text
    return made.json()["id"]


def test_connect_lists_exactly_the_real_tools(client, echo):
    sid, _ = echo
    got = client.post(f"/api/mcp/servers/{sid}/connect")
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["status"] == "connected" and body["error_message"] == "" and body["last_connected_at"] and body["tools_listed_at"]
    tools = {t["name"]: t for t in body["tools"]}
    assert set(tools) == {"echo", "add"}
    assert tools["add"]["input_schema"]["properties"].keys() == {"a", "b"} and tools["echo"]["description"] == "Return the text unchanged."


def test_call_needs_a_grant_then_returns_the_real_result_and_is_audited(client, echo, project):
    sid, _ = echo
    assert client.post(f"/api/mcp/servers/{sid}/connect").json()["status"] == "connected"
    call = lambda tool, args: client.post(f"/api/mcp/servers/{sid}/tools/{tool}/call", json={"project_id": project, "arguments": args})
    assert call("echo", {"text": "hello"}).status_code == 403  # no grant yet, not even for the admin
    gid = _grant(client, sid, "echo", "admin")
    got = call("echo", {"text": "hello mcp"})
    assert got.status_code == 200, got.text
    assert got.json()["ok"] is True and "hello mcp" in got.json()["content"][0]["text"]
    assert call("add", {"a": 2, "b": 3}).status_code == 403  # the grant names echo only
    _grant(client, sid, "*", "admin")
    assert '"result": 5' in call("add", {"a": 2, "b": 3}).json()["content"][0]["text"]
    assert call("nope", {}).status_code == 404
    with db() as con:
        audited = con.execute("SELECT kind, status FROM tool_calls WHERE project_id=? AND tool=?", (project, f"{sid}/echo")).fetchall()
        ledgered = con.execute("SELECT 1 FROM ledger WHERE project_id=? AND action='mcp.tool_called' AND target=?", (project, f"{sid}/echo")).fetchall()
    assert [tuple(r) for r in audited] == [("mcp", "ok")] and len(ledgered) == 1
    assert client.delete(f"/api/mcp/grants/{gid}").status_code == 200


def test_developer_needs_a_grant_for_their_role(client, echo, project):
    sid, _ = echo
    client.post(f"/api/mcp/servers/{sid}/connect")
    name = unique("mcpcaller")
    user = make_user(client, name, role="developer", features=["mcp"])
    dev, _ = sign_in(name)
    assert client.post(f"/api/projects/{project}/members", json={"username": name, "role": "developer"}).status_code == 201
    body = {"project_id": project, "arguments": {"text": "x"}}
    assert dev.post(f"/api/mcp/servers/{sid}/tools/echo/call", json=body).status_code == 403
    _grant(client, sid, "echo", "developer")
    assert dev.post(f"/api/mcp/servers/{sid}/tools/echo/call", json=body).status_code == 200
    assert dev.post(f"/api/mcp/servers/{sid}/tools/echo/call", json={**body, "project_id": "prj_not_theirs"}).status_code == 404
    dev_user = {"id": user["id"], "role": "user", "account_role": "developer"}
    assert [t.allowed_tools for t in mcp_tools_for(project, dev_user) if t.name == sid] == [["echo"]]
    assert not mcp_tools_for("prj_not_theirs", dev_user)


def test_bad_command_is_an_error_with_a_message_and_no_tools(client):
    made = client.post("/api/mcp/servers", json={"name": "dies", "command": sys.executable, "args": ["-c", "import sys; sys.exit(3)"]}).json()
    got = client.post(f"/api/mcp/servers/{made['id']}/connect").json()
    assert got["status"] == "error" and got["error_message"] and got["tools"] == []
    assert client.post(f"/api/mcp/servers/{made['id']}/tools/echo/call", json={"project_id": "x", "arguments": {}}).status_code in (404, 409)
    if not shutil.which("uvx"):  # an allowed program that is not installed must say so
        missing = client.post("/api/mcp/servers", json={"name": "gone", "command": "uvx", "args": ["x"]}).json()
        assert "not found" in client.post(f"/api/mcp/servers/{missing['id']}/connect").json()["error_message"]
        client.delete(f"/api/mcp/servers/{missing['id']}")
    client.delete(f"/api/mcp/servers/{made['id']}")


def test_web_profile_refuses_stdio(client, echo, monkeypatch):
    sid, _ = echo
    assert client.post(f"/api/mcp/servers/{sid}/connect").json()["status"] == "connected"
    _grant(client, sid, "*", "admin")
    assert [t.name for t in mcp_tools_for("any", ADMIN) if t.name == sid] == [sid]
    monkeypatch.setattr(config, "PROFILE", "web")
    refused = client.post(f"/api/mcp/servers/{sid}/connect")
    assert refused.status_code == 403 and "desktop app" in refused.json()["message"]
    assert client.post("/api/mcp/servers", json={"name": "w", "command": sys.executable, "args": [ECHO]}).status_code == 403
    assert not [t for t in mcp_tools_for("any", ADMIN) if t.name == sid]


def test_no_env_value_in_any_response_or_log(client, echo, project):
    sid, marker = echo
    responses = [client.post(f"/api/mcp/servers/{sid}/connect"), client.get("/api/mcp/servers"), client.get(f"/api/mcp/servers/{sid}")]
    _grant(client, sid, "echo", "admin")
    responses.append(client.post(f"/api/mcp/servers/{sid}/tools/echo/call", json={"project_id": project, "arguments": {"text": "plain"}}))
    assert responses[0].json()["secret_names"] == ["ECHO_FIXTURE_VALUE"] and responses[-1].status_code == 200
    assert all(marker not in r.text for r in responses)
    assert all(marker not in p.read_text(encoding="utf-8", errors="replace") for p in LOGS.glob("*") if p.is_file())
