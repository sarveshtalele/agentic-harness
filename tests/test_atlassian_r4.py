"""R4 (docs/PHASE2_PLAN.md): an MCP server behind OAuth 2.1 with PKCE, each member signed in on their own, and BA Studio's
search and attach. The provider is tests/fixtures/mcp_oauth_server.py, a real MCP server on a real port (the stand-in
for the Atlassian remote MCP, which needs a real Atlassian account)."""
import socket
import threading
import time
from urllib.parse import urlsplit

import httpx
import pytest
import uvicorn

from backend.db import db
from tests.fixtures import mcp_oauth_server as provider
from tests.helpers_api import client, make_user, sign_in, unique  # noqa: F401 - fixtures


@pytest.fixture(scope="module")
def base():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(provider.app(url), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            httpx.get(f"{url}/.well-known/oauth-authorization-server", timeout=1)
            break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield url
    server.should_exit = True
    thread.join(timeout=10)


def sign_in_with(member, start_path: str, return_to: str = "/home") -> httpx.Response:
    """What the browser does: open the provider's URL, follow its redirect back to our callback."""
    started = member.post(start_path, json={"return_to": return_to})
    assert started.status_code == 200, started.text
    redirected = httpx.get(started.json()["url"], follow_redirects=False)
    back = urlsplit(redirected.headers["location"])
    return member.get(f"{back.path}?{back.query}", follow_redirects=False)


def test_each_member_signs_in_then_searches_and_attaches_from_ba_studio(client, base):
    server = client.post("/api/mcp/servers", json={"name": "Atlassian", "transport": "http", "url": f"{base}/mcp", "auth": "oauth"}).json()
    sid = server["id"]
    failed = client.post(f"/api/mcp/servers/{sid}/connect").json()
    assert failed["status"] != "connected" and "Sign in" in failed["error_message"]  # no token yet: no tools are invented
    done = sign_in_with(client, f"/api/mcp/servers/{sid}/oauth/start")
    assert done.status_code == 303 and done.headers["location"].startswith("/home?connected=")
    assert provider.REGISTERED[-1]["token_endpoint_auth_method"] == "none"  # a public client with PKCE, no secret
    listed = client.post(f"/api/mcp/servers/{sid}/connect").json()
    assert listed["status"] == "connected" and {t["name"] for t in listed["tools"]} == {"search", "fetch"}
    assert client.post("/api/mcp/grants", json={"server_id": sid, "tool_name": "*", "role": "ba"}).status_code == 201

    name = unique("ba")
    make_user(client, name, role="ba")
    ba, _ = sign_in(name)
    project = ba.post("/api/projects", json={"name": "Refunds", "description": ""}).json()
    shown = ba.get(f"/api/projects/{project['id']}/atlassian").json()["sources"]
    assert shown == [{"id": sid, "name": "Atlassian", "search_tool": "search", "fetch_tool": "fetch", "connected": False}]
    assert ba.post(f"/api/projects/{project['id']}/atlassian/{sid}/search", json={"query": "refund"}).status_code == 401  # their own sign-in
    back = sign_in_with(ba, f"/api/projects/{project['id']}/atlassian/{sid}/connect", f"/projects/{project['id']}/ba")
    assert back.headers["location"] == f"/projects/{project['id']}/ba?connected={sid}"
    items = ba.post(f"/api/projects/{project['id']}/atlassian/{sid}/search", json={"query": "refund"}).json()["items"]
    assert {i["id"] for i in items} == {"PAY-142", "CONF-9"}
    attached = ba.post(f"/api/projects/{project['id']}/atlassian/{sid}/attach", json={"items": items}).json()["sources"]
    assert len(attached) == 2 and not any(s["unchanged"] for s in attached)
    sources = {s["filename"]: s for s in ba.get(f"/api/projects/{project['id']}/sources").json()}
    assert "PAY-142 Refund rules.md" in sources
    with db() as con:
        text = con.execute("SELECT text FROM sources WHERE id=?", (attached[0]["id"],)).fetchone()[0]
        stored = con.execute("SELECT token_enc FROM mcp_tokens WHERE server_id=? AND user_id=?", (sid, ba.get("/api/auth/me").json()["id"])).fetchone()[0]
    assert text.startswith("Source: Atlassian ") and "fetched" in text and "Refunds above 500 EUR need finance approval" in text
    assert not any(token in stored for token in provider.TOKENS)  # tokens are encrypted at rest
    again = ba.post(f"/api/projects/{project['id']}/atlassian/{sid}/attach", json={"items": items[:1]}).json()["sources"]
    assert again[0]["unchanged"]  # the same content is not stored twice; changed content would be a new source


def test_an_expired_token_is_refreshed_and_a_used_link_is_refused(client, base):
    server = client.post("/api/mcp/servers", json={"name": "Atlassian 2", "transport": "http", "url": f"{base}/mcp", "auth": "oauth"}).json()
    sid = server["id"]
    started = client.post(f"/api/mcp/servers/{sid}/oauth/start", json={"return_to": "/home"}).json()["url"]
    back = urlsplit(httpx.get(started, follow_redirects=False).headers["location"])
    assert client.get(f"{back.path}?{back.query}", follow_redirects=False).status_code == 303
    assert client.get(f"{back.path}?{back.query}", follow_redirects=False).status_code == 400  # a state is used once
    with db() as con:
        con.execute("UPDATE mcp_tokens SET expires_at=0 WHERE server_id=?", (sid,))
    assert client.post(f"/api/mcp/servers/{sid}/connect").json()["status"] == "connected"  # refreshed on the way
    assert client.delete(f"/api/mcp/servers/{sid}/oauth").json() == {"connected": False}
    assert client.post("/api/mcp/servers", json={"name": "x", "transport": "websocket", "url": "wss://e.org/x", "auth": "oauth"}).status_code == 400


def test_outside_sources_need_ba_studio(client):
    name = unique("dev")
    make_user(client, name, role="developer")
    dev, _ = sign_in(name)
    project = dev.post("/api/projects", json={"name": "Dev", "description": ""}).json()
    refused = dev.get(f"/api/projects/{project['id']}/atlassian")
    assert refused.status_code == 403 and "BA Studio" in refused.json()["message"]
