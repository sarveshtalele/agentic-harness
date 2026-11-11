"""MCP registry API: nothing is seeded, input is validated, writes are admin-only, and secrets never come back."""
import sys

import pytest

from backend.config import ROOT
from backend.db import db
from tests.helpers_api import client, make_user, sign_in, unique  # noqa: F401 - fixtures

ECHO = str(ROOT / "tests" / "fixtures" / "mcp_echo_server.py")
SEEDED = ("mcp-filesystem", "mcp-memory", "mcp-fetch", "mcp-github", "srv_playwright")


def test_nothing_is_seeded_and_catalog_is_templates_only(client):
    servers = client.get("/api/mcp/servers").json()
    assert not {s["id"] for s in servers["servers"]} & set(SEEDED)
    with db() as con:
        assert not con.execute(f"SELECT 1 FROM mcp_servers WHERE id IN ({','.join('?' * len(SEEDED))})", SEEDED).fetchone()
    templates = client.get("/api/mcp/catalog").json()["templates"]
    assert {"playwright", "filesystem", "fetch", "github"} <= {t["id"] for t in templates}
    assert all("tools" not in t and "status" not in t for t in templates)


def test_add_validates_command_url_and_transport(client):
    bad = [
        {"name": "", "command": "npx", "args": []},
        {"name": "no target"},
        {"name": "shell", "command": "bash", "args": ["-c", "rm -rf /"]},
        {"name": "joined", "command": "npx -y @x/y"},
        {"name": "plain http", "transport": "http", "url": "http://mcp.example.org/mcp"},
        {"name": "no scheme", "transport": "http", "url": "mcp.example.org"},
        {"name": "odd", "transport": "sse", "url": "https://mcp.example.org"},
    ]
    for body in bad:
        assert client.post("/api/mcp/servers", json=body).status_code == 400, body
    local = client.post("/api/mcp/servers", json={"name": "loopback", "transport": "http", "url": "http://127.0.0.1:9/mcp"})
    remote = client.post("/api/mcp/servers", json={"name": "remote", "transport": "http", "url": "https://mcp.example.org/mcp"})
    stdio = client.post("/api/mcp/servers", json={"name": "abs", "command": sys.executable, "args": [ECHO]})
    for made in (local, remote, stdio):
        assert made.status_code == 201, made.text
        body = made.json()
        assert body["status"] == "not_connected" and body["tools"] == [] and body["last_connected_at"] is None
    for made in (local, remote, stdio):
        assert client.delete(f"/api/mcp/servers/{made.json()['id']}").status_code == 200
    assert client.delete(f"/api/mcp/servers/{stdio.json()['id']}").status_code == 404


def test_secrets_are_encrypted_and_only_names_come_back(client):
    value = "hdr-" + unique("v")
    made = client.post("/api/mcp/servers", json={"name": "with header", "transport": "http", "url": "https://mcp.example.org/mcp", "headers": {"Authorization": value}})
    assert made.status_code == 201
    sid = made.json()["id"]
    assert made.json()["secret_names"] == ["Authorization"]
    for text in (made.text, client.get("/api/mcp/servers").text, client.get(f"/api/mcp/servers/{sid}").text):
        assert value not in text
    with db() as con:
        stored = con.execute("SELECT secrets_enc FROM mcp_servers WHERE id=?", (sid,)).fetchone()[0]
    assert stored and value not in stored
    edited = client.patch(f"/api/mcp/servers/{sid}", json={"name": "renamed"})
    assert edited.status_code == 200 and edited.json()["name"] == "renamed" and edited.json()["secret_names"] == ["Authorization"]
    client.delete(f"/api/mcp/servers/{sid}")


def test_old_fake_routes_are_gone(client):
    assert client.post("/api/mcp/execute", json={"command": "npx -y x"}).status_code in (404, 405)
    assert client.post("/api/mcp/tools/x/toggle", json={}).status_code in (403, 404, 405)


@pytest.fixture
def developer(client):
    name = unique("mcpdev")
    make_user(client, name, role="developer")
    other, response = sign_in(name)
    assert response.status_code == 200
    return other


def test_non_admin_lists_but_cannot_add_edit_connect_or_grant(client, developer):
    sid = client.post("/api/mcp/servers", json={"name": "admin made", "transport": "http", "url": "https://mcp.example.org/mcp"}).json()["id"]
    assert developer.get("/api/mcp/servers").status_code == 200
    assert developer.get("/api/mcp/catalog").status_code == 200
    assert developer.post("/api/mcp/servers", json={"name": "x", "command": sys.executable, "args": [ECHO]}).status_code == 403
    assert developer.patch(f"/api/mcp/servers/{sid}", json={"name": "y"}).status_code == 403
    assert developer.delete(f"/api/mcp/servers/{sid}").status_code == 403
    assert developer.post(f"/api/mcp/servers/{sid}/connect").status_code == 403
    assert developer.post("/api/mcp/grants", json={"server_id": sid, "tool_name": "*", "role": "developer"}).status_code == 403
    assert developer.get("/api/mcp/grants").status_code == 403
    client.delete(f"/api/mcp/servers/{sid}")
