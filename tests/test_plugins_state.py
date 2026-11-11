"""Plugin enable and disable, zip install (with zip-slip and symlink refusals), and .mcp.json server registration."""
import io
import json
import stat
import sys
import zipfile

import pytest

from backend.config import ROOT
from backend.core import plugin_install, plugins
from backend.db import db
from tests.helpers_api import client, make_user, sign_in, unique  # noqa: F401 - fixtures


def _zip(files: dict[str, str], links: tuple[str, ...] = ()) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
        for name in links:
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "/etc/passwd")
    return buf.getvalue()


def _plugin(root, pid, mcp=None):
    folder = root / "plugins" / pid
    (folder / "skills" / "helper").mkdir(parents=True)
    (folder / "plugin.json").write_text(json.dumps({"id": pid}))
    (folder / "skills" / "helper" / "SKILL.md").write_text(f"---\nname: {pid}-helper\ndescription: helps\n---\nbody\n")
    if mcp is not None:
        (folder / ".mcp.json").write_text(json.dumps(mcp))
    return folder


def test_disable_removes_skills_and_commands(tmp_path):
    pid = unique("plug")
    folder = _plugin(tmp_path, pid)
    assert (folder / "skills").resolve() in plugins.skill_paths(tmp_path)
    plugins.set_enabled(pid, False, "admin", root=tmp_path)
    assert (folder / "skills").resolve() not in plugins.skill_paths(tmp_path)
    assert not [e for e in plugins.slash_entries(tmp_path) if e["plugin"] == pid]
    assert plugins.skill_paths(tmp_path)[0] == plugins.SKILLS_DIR  # the repo's own skills stay
    plugins.set_enabled(pid, True, "admin", root=tmp_path)
    assert (folder / "skills").resolve() in plugins.skill_paths(tmp_path)
    with pytest.raises(ValueError):
        plugins.set_enabled("local-skills", False, "admin", root=tmp_path)


def test_api_enable_disable_is_admin_only_and_changes_the_slash_menu(client):
    name = unique("plugdev")
    make_user(client, name, role="developer")
    dev, _ = sign_in(name)
    assert dev.post("/api/plugins/agentic-qe/disable").status_code == 403
    off = client.post("/api/plugins/agentic-qe/disable")
    assert off.status_code == 200 and off.json()["enabled"] is False
    assert not [e for e in client.get("/api/plugins/slash").json() if e["plugin"] == "agentic-qe"]
    assert client.post("/api/plugins/agentic-qe/enable").json()["enabled"] is True
    assert [e for e in client.get("/api/plugins/slash").json() if e["plugin"] == "agentic-qe"]
    assert client.post("/api/plugins/no-such-plugin/disable").status_code == 404


def test_zip_install_into_root_and_refusals(tmp_path):
    good = _zip({"demo/plugin.json": json.dumps({"id": "demo-plugin"}), "demo/skills/s/SKILL.md": "---\nname: s\ndescription: d\n---\nb\n"})
    installed = plugin_install.install_zip(good, root=tmp_path)
    assert installed.id == "demo-plugin" and (tmp_path / "plugins" / "demo-plugin" / "plugin.json").is_file() and installed.skills_dir
    with pytest.raises(FileExistsError):
        plugin_install.install_zip(good, root=tmp_path)
    for bad in (_zip({"plugin.json": json.dumps({"id": "x1"}), "../escape.txt": "x"}),
                _zip({"plugin.json": json.dumps({"id": "x2"})}, links=("skills/link",)),
                _zip({"README.md": "no manifest"}),
                _zip({"plugin.json": json.dumps({"id": "Bad Id!"})}),
                b"not a zip"):
        with pytest.raises(ValueError):
            plugin_install.install_zip(bad, root=tmp_path)
    assert not (tmp_path / "escape.txt").exists() and not (tmp_path / "plugins" / "escape.txt").exists()
    assert sorted(p.name for p in (tmp_path / "plugins").iterdir()) == ["demo-plugin"]


def test_api_upload_refuses_zip_slip_and_existing_ids(client):
    pid = unique("slip")
    slip = _zip({"plugin.json": json.dumps({"id": pid}), "../../" + pid + ".txt": "x"})
    got = client.post("/api/plugins/upload", files={"file": ("p.zip", slip, "application/zip")})
    assert got.status_code == 400
    assert not (ROOT / "plugins" / pid).exists() and not (ROOT / f"{pid}.txt").exists() and not (ROOT.parent / f"{pid}.txt").exists()
    taken = _zip({"plugin.json": json.dumps({"id": "agentic-qe"})})
    assert client.post("/api/plugins/upload", files={"file": ("p.zip", taken, "application/zip")}).status_code == 409


def test_mcp_json_is_discovered_and_registers_servers(client, tmp_path, monkeypatch):
    pid = unique("mcpplug")
    script = str(ROOT / "tests" / "fixtures" / "mcp_echo_server.py")
    _plugin(tmp_path, pid, {"mcpServers": {"echo": {"command": sys.executable, "args": [script], "env": {"FIXTURE_ENV": "plain-value-1"}},
                                           "remote": {"type": "http", "url": "https://mcp.example.org/mcp"},
                                           "old": {"type": "sse", "url": "https://mcp.example.org/sse"}}})
    monkeypatch.setattr(plugins, "ROOT", tmp_path)
    listed = {p["id"]: p for p in client.get("/api/plugins").json()}[pid]
    assert {s["name"] for s in listed["mcp_servers"]} == {"echo", "remote"} and any("sse" in p for p in listed["problems"])
    assert next(s for s in listed["mcp_servers"] if s["name"] == "echo")["secret_names"] == ["FIXTURE_ENV"] and "plain-value-1" not in json.dumps(listed)
    name = unique("plugdev")
    make_user(client, name, role="developer")
    dev, _ = sign_in(name)
    assert dev.post(f"/api/plugins/{pid}/mcp/register").status_code == 403
    done = client.post(f"/api/plugins/{pid}/mcp/register")
    assert done.status_code == 200, done.text
    assert {s["name"] for s in done.json()["registered"]} == {"echo", "remote"}
    assert all(s["status"] == "not_connected" and s["plugin_id"] == pid for s in done.json()["registered"])
    assert set(client.post(f"/api/plugins/{pid}/mcp/register").json()["skipped"]) == {"echo", "remote"}  # registering twice adds nothing
    with db() as con:
        ids = [r[0] for r in con.execute("SELECT id FROM mcp_servers WHERE plugin_id=?", (pid,))]
    assert len(ids) == 2
    for sid in ids:
        client.delete(f"/api/mcp/servers/{sid}")
