import os
import sys
import pytest

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


@pytest.fixture
def auth_client():
    with TestClient(app) as test_client:
        login_res = test_client.post(
            "/api/auth/login",
            json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}
        )
        assert login_res.status_code == 200
        yield test_client


def test_get_servers_pre_seeded(auth_client):
    """Verify all 4 standard MCP servers are pre-seeded with tools, status, and correct types."""
    res = auth_client.get("/api/mcp/servers")
    assert res.status_code == 200
    data = res.json()
    assert "servers" in data
    servers = data["servers"]
    assert len(servers) >= 4

    # Verify standard servers exist
    server_ids = {s["id"]: s for s in servers}
    assert "mcp-filesystem" in server_ids
    assert "mcp-memory" in server_ids
    assert "mcp-fetch" in server_ids
    assert "mcp-github" in server_ids

    # a) Local NPX Filesystem
    fs = server_ids["mcp-filesystem"]
    assert fs["name"] == "Local NPX Filesystem"
    assert fs["type"] == "local_npx"
    assert "npx -y @modelcontextprotocol/server-filesystem" in fs["command"]
    assert fs["status"] == "connected"
    assert fs["total_tools"] >= 4
    assert fs["authorized_tools"] == fs["total_tools"]
    tool_names = [t["name"] for t in fs["tools"]]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "list_directory" in tool_names

    # b) Local NPX Memory
    mem = server_ids["mcp-memory"]
    assert mem["name"] == "Local NPX Memory"
    assert mem["type"] == "local_npx"
    assert "npx -y @modelcontextprotocol/server-memory" in mem["command"]
    assert mem["total_tools"] >= 4

    # c) Local NPX Fetch
    fetch = server_ids["mcp-fetch"]
    assert fetch["name"] == "Local NPX Fetch"
    assert fetch["type"] == "local_npx"
    assert "npx -y @modelcontextprotocol/server-fetch" in fetch["command"]
    assert any(t["name"] == "fetch" for t in fetch["tools"])

    # d) Remote GitHub MCP
    gh = server_ids["mcp-github"]
    assert gh["name"] == "Remote GitHub MCP"
    assert gh["type"] == "remote_sse"
    assert gh["url"] == "https://api.githubcopilot.com/mcp"
    assert gh["total_tools"] >= 4


def test_add_new_server_remote_and_local(auth_client):
    """Verify adding remote SSE/HTTP and local NPX servers with input validation."""
    # 1. Add remote SSE server
    remote_res = auth_client.post("/api/mcp/servers", json={
        "name": "Custom Remote Server",
        "type": "remote_sse",
        "url": "https://mcp.example.com/sse",
        "transport": "sse"
    })
    assert remote_res.status_code == 200
    remote_data = remote_res.json()
    remote_id = remote_data["id"]
    assert remote_data["name"] == "Custom Remote Server"
    assert remote_data["type"] == "remote_sse"
    assert remote_data["url"] == "https://mcp.example.com/sse"
    assert remote_data["total_tools"] >= 1

    # 2. Add local NPX server
    local_res = auth_client.post("/api/mcp/servers", json={
        "name": "Local SQLite MCP",
        "type": "local_npx",
        "command": "npx -y @modelcontextprotocol/server-sqlite --db test.db"
    })
    assert local_res.status_code == 200
    local_data = local_res.json()
    local_id = local_data["id"]
    assert local_data["name"] == "Local SQLite MCP"
    assert local_data["type"] == "local_npx"
    assert "read_query" in [t["name"] for t in local_data["tools"]]

    # 3. Validation: empty name
    bad_res1 = auth_client.post("/api/mcp/servers", json={"name": "", "command": "npx test"})
    assert bad_res1.status_code in (400, 422)

    # 4. Validation: neither command nor url
    bad_res2 = auth_client.post("/api/mcp/servers", json={"name": "Bad Server"})
    assert bad_res2.status_code == 400

    # 5. Validation: command injection attempts
    bad_res3 = auth_client.post("/api/mcp/servers", json={
        "name": "Injection Server",
        "command": "npx -y test; rm -rf /"
    })
    assert bad_res3.status_code == 400

    # Cleanup created servers
    auth_client.delete(f"/api/mcp/servers/{remote_id}")
    auth_client.delete(f"/api/mcp/servers/{local_id}")


def test_delete_server(auth_client):
    """Verify deleting an MCP server and its tools."""
    # Create temp server
    res = auth_client.post("/api/mcp/servers", json={
        "name": "To Delete Server",
        "type": "remote_sse",
        "url": "https://temp.mcp.example.com"
    })
    assert res.status_code == 200
    srv_id = res.json()["id"]

    # Delete server
    del_res = auth_client.delete(f"/api/mcp/servers/{srv_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Check that it no longer appears in GET /api/mcp/servers
    get_res = auth_client.get("/api/mcp/servers")
    server_ids = [s["id"] for s in get_res.json()["servers"]]
    assert srv_id not in server_ids

    # Deleting non-existent server returns 404
    del_404 = auth_client.delete(f"/api/mcp/servers/{srv_id}")
    assert del_404.status_code == 404


def test_toggle_all_tools_for_server(auth_client):
    """Verify master toggle to authorize/disable all tools for a server."""
    # Step 1: Disable all tools for mcp-fetch
    toggle_off = auth_client.post("/api/mcp/servers/mcp-fetch/toggle-all", json={"authorized": False})
    assert toggle_off.status_code == 200
    data_off = toggle_off.json()
    assert data_off["authorized_tools"] == 0
    for t in data_off["tools"]:
        assert t["authorized"] is False

    # Step 2: Toggle without body should flip back to authorized
    toggle_on = auth_client.post("/api/mcp/servers/mcp-fetch/toggle-all", json={})
    assert toggle_on.status_code == 200
    data_on = toggle_on.json()
    assert data_on["authorized_tools"] == data_on["total_tools"]
    for t in data_on["tools"]:
        assert t["authorized"] is True

    # 404 for nonexistent server
    not_found = auth_client.post("/api/mcp/servers/nonexistent-server-id/toggle-all", json={})
    assert not_found.status_code == 404


def test_toggle_single_tool(auth_client):
    """Verify individual tool authorization toggle switch."""
    # Get tool from mcp-fetch
    srv_res = auth_client.get("/api/mcp/servers")
    fetch_srv = [s for s in srv_res.json()["servers"] if s["id"] == "mcp-fetch"][0]
    tool = fetch_srv["tools"][0]
    tool_id = tool["id"]

    # Toggle off
    res_off = auth_client.post(f"/api/mcp/tools/{tool_id}/toggle", json={"authorized": False})
    assert res_off.status_code == 200
    assert res_off.json()["authorized"] is False

    # Toggle on without body
    res_on = auth_client.post(f"/api/mcp/tools/{tool_id}/toggle", json={})
    assert res_on.status_code == 200
    assert res_on.json()["authorized"] is True

    # 404 for nonexistent tool
    res_404 = auth_client.post("/api/mcp/tools/nonexistent-tool-id/toggle", json={})
    assert res_404.status_code == 404


def test_execute_tool_authorized_vs_disabled(auth_client):
    """Verify tool execution works when authorized, and is rejected with 403 when disabled."""
    srv_res = auth_client.get("/api/mcp/servers")
    fs_srv = [s for s in srv_res.json()["servers"] if s["id"] == "mcp-filesystem"][0]
    read_tool = [t for t in fs_srv["tools"] if t["name"] == "read_file"][0]
    tool_id = read_tool["id"]

    # Ensure tool is authorized
    auth_client.post(f"/api/mcp/tools/{tool_id}/toggle", json={"authorized": True})

    from backend.config import repo_dir
    pid = "prj_mcp_exec_test"
    from backend.db import db, now
    with db() as con:  # a real project row: file tools refuse ids that are not projects (review P1-R #4)
        con.execute("INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived, owner_id) "
                    "VALUES ('prj_mcp_exec_test', 'MCP exec test', '', ?, ?, 0, 'admin')", (now(), now()))
    (repo_dir(pid)).mkdir(parents=True, exist_ok=True)
    (repo_dir(pid) / "README.md").write_text("# real file\n", encoding="utf-8")

    # Execute authorized tool
    exec_res = auth_client.post("/api/mcp/execute", json={
        "tool_id": tool_id,
        "arguments": {"path": "README.md"},
        "project_id": pid,
    })
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "ok"
    assert exec_data["success"] is True
    assert "README.md" in exec_data["result"]["path"]
    assert exec_data["result"]["content"] == "# real file\n"

    # Now disable the tool
    auth_client.post(f"/api/mcp/tools/{tool_id}/toggle", json={"authorized": False})

    # Execute disabled tool -> MUST return 403 Forbidden
    blocked_res = auth_client.post("/api/mcp/execute", json={
        "tool_id": tool_id,
        "arguments": {"path": "README.md"},
        "project_id": pid,
    })
    assert blocked_res.status_code == 403
    assert "not authorized" in blocked_res.json().get("detail", "").lower() or "not authorized" in blocked_res.json().get("message", "").lower()

    # Re-enable for subsequent tests
    auth_client.post(f"/api/mcp/tools/{tool_id}/toggle", json={"authorized": True})


def test_execute_sandbox_security_traversal_blocked(auth_client):
    """Path escapes, absolute paths, missing project id, missing files and fake writes are all refused."""
    from backend.config import repo_dir
    pid = "prj_mcp_exec_test"
    from backend.db import db, now
    with db() as con:  # a real project row: file tools refuse ids that are not projects (review P1-R #4)
        con.execute("INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived, owner_id) "
                    "VALUES ('prj_mcp_exec_test', 'MCP exec test', '', ?, ?, 0, 'admin')", (now(), now()))
    repo_dir(pid).mkdir(parents=True, exist_ok=True)
    srv_res = auth_client.get("/api/mcp/servers")
    fs_srv = [s for s in srv_res.json()["servers"] if s["id"] == "mcp-filesystem"][0]
    tools = {t["name"]: t for t in fs_srv["tools"]}
    for t in ("read_file", "write_file", "list_directory"):
        auth_client.post(f"/api/mcp/tools/{tools[t]['id']}/toggle", json={"authorized": True})

    def run(tool, path, project_id=pid, **extra):
        body = {"tool_id": tools[tool]["id"], "arguments": {"path": path, **extra}}
        if project_id:
            body["project_id"] = project_id
        return auth_client.post("/api/mcp/execute", json=body)

    assert run("read_file", "../../../etc/shadow").status_code == 400  # needs the project row above
    assert run("read_file", "/etc/hosts").status_code == 400
    assert run("read_file", "README.md", project_id=None).status_code == 400
    assert run("read_file", "no-such-file.txt").status_code == 404
    assert run("write_file", "x.txt", content="hi").status_code == 501
    assert not (repo_dir(pid) / "x.txt").exists()
    (repo_dir(pid) / "b.txt").write_text("b", encoding="utf-8")
    (repo_dir(pid) / "a.txt").write_text("a", encoding="utf-8")
    listing = run("list_directory", ".")
    assert listing.status_code == 200
    assert listing.json()["result"]["entries"] == sorted(listing.json()["result"]["entries"])
    assert {"a.txt", "b.txt"} <= set(listing.json()["result"]["entries"])


def test_execute_npx_command_in_sandbox(auth_client):
    """Verify safe NPX command execution in sandbox and rejection of unsafe operators."""
    # 1. Safe execution
    exec_res = auth_client.post("/api/mcp/execute", json={
        "command": "npx -y @modelcontextprotocol/server-fetch"
    })
    assert exec_res.status_code == 200
    data = exec_res.json()
    # The result must match what really happened: no claim of a verified MCP server before P4.
    assert data["result"]["verified"] is False
    if data["exit_code"] is None:
        assert data["status"] == "running" and data["success"] is None
    else:
        assert data["success"] is (data["exit_code"] == 0)

    # 2. Command with unsafe chaining operator -> 400 Bad Request
    bad_res = auth_client.post("/api/mcp/execute", json={
        "command": "npx -y fetch && echo hacked"
    })
    assert bad_res.status_code == 400

    # 3. Non-npx command -> 400 Bad Request
    bad_res2 = auth_client.post("/api/mcp/execute", json={
        "command": "python -c 'print(1)'"
    })
    assert bad_res2.status_code == 400
