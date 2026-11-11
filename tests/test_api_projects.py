"""Projects, settings, documents and templates through the real API."""

import io
import json

from docx import Document
from tests.helpers_api import client, FEATURE, project  # noqa: F401 - fixtures


def test_project_crud_and_empty_state_has_no_fabricated_data(client):
    created = client.post("/api/projects", json={"name": "Empty"}).json()
    overview = client.get(f"/api/projects/{created['id']}/overview").json()
    assert overview["repo"] is None and overview["documents"] == [] and overview["recent_runs"] == []
    assert client.get(f"/api/projects/{created['id']}/metrics").json() == {"runs": [], "durations": [], "tools": [], "agents": []}
    assert client.patch(f"/api/projects/{created['id']}", json={"archived": True}).json()["archived"] is True
    assert created["id"] not in [p["id"] for p in client.get("/api/projects").json()]
    assert client.delete(f"/api/projects/{created['id']}").status_code == 204
    assert client.get(f"/api/projects/{created['id']}").status_code == 404


def test_blank_project_name_rejected(client):
    assert client.post("/api/projects", json={"name": ""}).status_code == 422


def test_cross_site_write_and_rebinding_blocked(client):
    assert client.post("/api/projects", json={"name": "x"}, headers={"origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/projects", headers={"host": "evil.example"}).status_code == 403
    assert client.post("/api/projects", json={"name": "ok"}, headers={"origin": "http://localhost:3000"}).status_code == 201


def test_run_without_model_gives_actionable_error(client, project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    response = client.post(f"/api/projects/{project['id']}/runs", json={"workflow": "bug_scan"})
    assert response.status_code == 412 and "Settings" in response.json()["detail"]


def test_llm_key_never_returned_and_encrypted(client):
    public = client.put("/api/settings/llm", json={"model": "m", "api_key": "fake-key-123456", "base_url": "https://x.test/v1"}).json()
    assert "fake-key-123456" not in json.dumps(public) and public["api_key_hint"] == "…3456"
    from backend.db import db

    with db() as con:
        stored = con.execute("SELECT value FROM settings WHERE key='llm_api_key'").fetchone()["value"]
        con.execute("DELETE FROM settings")
    assert "fake-key" not in stored


def test_connection_test_reports_real_failure(client):
    result = client.post("/api/settings/llm/test", json={"base_url": "http://127.0.0.1:9/v1", "model": "m", "api_key": "k"}).json()
    assert result["ok"] is False and "Cannot reach" in result["error"]


def test_document_lifecycle_and_exports(client, project):
    doc = client.post(f"/api/projects/{project['id']}/documents", json={"title": "Spec", "kind": "brd", "template_id": "builtin_brd"}).json()
    assert "Scope" in doc["content"]
    saved = client.put(f"/api/documents/{doc['id']}", json={"content": "## Scope\n\nEdited **text**\n", "note": "mine"}).json()
    assert saved["version"] == 2 and saved["author"] == "admin"
    md = client.get(f"/api/documents/{doc['id']}/export/md")
    assert md.text.startswith("## Scope") and "attachment" in md.headers["content-disposition"]
    docx = client.get(f"/api/documents/{doc['id']}/export/docx")
    assert any("Edited" in p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
    assert client.get(f"/api/documents/{doc['id']}/versions").json()[0]["note"] == "mine"
    assert client.post(f"/api/documents/{doc['id']}/restore/1").json()["version"] == 3
    assert client.get(f"/api/documents/{doc['id']}/export/pdf").status_code == 400


def test_invalid_gherkin_edit_refused_by_api(client, project):
    doc = client.post(f"/api/projects/{project['id']}/documents", json={"title": "F", "kind": "gherkin", "content": FEATURE}).json()
    response = client.put(f"/api/documents/{doc['id']}", json={"content": "oops"})
    assert response.status_code == 400 and "Gherkin" in response.json()["detail"]
    assert client.get(f"/api/documents/{doc['id']}").json()["version"] == 1


def test_template_upload_is_markdown_only_and_builtin_protected(client, project):
    word = Document()
    word.add_heading("Our Template", 1)
    buffer = io.BytesIO()
    word.save(buffer)
    refused = client.post("/api/templates/upload", files={"file": ("ours.docx", buffer.getvalue())}, data={"name": "Ours", "kind": "brd", "project_id": project["id"]})
    assert refused.status_code == 415 and "Markdown" in refused.json()["detail"]
    assert client.post("/api/templates/upload", files={"file": ("bad.md", b"\xff\xfe# x")}, data={"name": "Bad", "kind": "brd"}).status_code == 415
    md = b"# Our Template\n\n## Purpose\nWhy.\n\n## Controls\nHow.\n"
    created = client.post("/api/templates/upload", files={"file": ("ours.md", md)}, data={"name": "Ours", "kind": "brd", "project_id": project["id"]}).json()
    assert created["headings"] == ["Purpose", "Controls"]
    assert created["id"] in [t["id"] for t in client.get(f"/api/templates?project_id={project['id']}").json()]
    assert client.delete("/api/templates/builtin_brd").status_code == 400


def test_source_upload_dedupes_and_rejects_empty(client, project):
    first = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("n.md", b"notes")}).json()
    second = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("copy.md", b"notes")}).json()
    assert first["id"] == second["id"] and second["duplicate"]
    assert client.post(f"/api/projects/{project['id']}/sources", files={"file": ("e.md", b"  ")}).status_code == 400
