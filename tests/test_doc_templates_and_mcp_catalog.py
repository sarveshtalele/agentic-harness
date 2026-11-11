"""Doc templates: the MCP catalog entry for Playwright, template upload, and BRD generation."""
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from tests.helpers_doc_parsers import auth_client  # noqa: F401 - fixtures


def test_playwright_is_an_install_template_not_a_registered_server(auth_client):
    """Playwright is offered as a catalog template. It is never seeded as a server, and no tool list is declared for it."""
    catalog = auth_client.get("/api/mcp/catalog")
    assert catalog.status_code == 200
    pw = next(t for t in catalog.json()["templates"] if t["id"] == "playwright")
    assert pw["command"] == "npx" and pw["args"] == ["-y", "@playwright/mcp@latest"] and "tools" not in pw
    servers = auth_client.get("/api/mcp/servers").json()["servers"]
    assert not any(s["id"] == "srv_playwright" for s in servers)


def test_template_upload_and_custom_brd_generation(auth_client):
    """Test full workflow: upload custom template file, parse it, and generate customized BRD."""
    # 1. Create a test project
    p_res = auth_client.post("/api/projects", json={"name": "FinTech Hub", "description": "Banking platform"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # 2. Upload template
    template_md = """# {{project_name}} Core Banking BRD

## 1. Executive Summary
This document defines requirements for {{project_name}} initiated by {{author}}.
Status: {{status}} on {{date}}.

## 2. System Scope
{{scope}}

| Subsystem | Functionality | SLA |
| --- | --- | --- |
| Accounts | Balance queries and transfers | 99.99% |
| Cards | Card freeze and limits | 99.95% |

## 3. Requirements Breakdown
[System Overview]

## 4. Sign-Off & Approvals
Signatures required for release.
"""
    upload_res = auth_client.post(
        f"/api/projects/{project_id}/templates/upload",
        files={"file": ("banking_brd_template.md", template_md.encode("utf-8"), "text/markdown")}
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    template_id = upload_data["template_id"]
    document_id = upload_data["document_id"]
    assert template_id.startswith("tpl_")
    assert document_id.startswith("doc_")
    assert len(upload_data["sections"]) >= 4
    assert "{{project_name}}" in upload_data["placeholders"]

    # 3. Generate custom BRD using the uploaded template_id
    gen_res = auth_client.post(
        f"/api/projects/{project_id}/templates/generate-brd",
        json={
            "template_id": template_id,
            "title": "FinTech Hub Production BRD v1",
            "variables": {
                "project_name": "FinTech Hub Enterprise",
                "author": "Chief Architect",
                "scope": "Comprehensive retail banking ledger and real-time transaction processing.",
                "system_overview": "Multi-region active-active deployment with distributed Kafka event queues."
            },
            "context": "Confidential banking document approved by Risk Committee."
        }
    )
    assert gen_res.status_code == 201
    brd = gen_res.json()
    assert brd["kind"] == "brd"
    assert brd["title"] == "FinTech Hub Production BRD v1"
    assert brd["template_id"] == template_id
    assert len(brd["sections"]) >= 4

    # 4. Verify content substitutions
    content = brd["content"]
    assert "FinTech Hub Enterprise" in content
    assert "Chief Architect" in content
    assert "Multi-region active-active deployment" in content
    assert "Confidential banking document" in content
    assert "| Accounts | Balance queries and transfers | 99.99% |" in content

    # 5. Verify ledger notification event was recorded
    ledger_res = auth_client.get(f"/api/projects/{project_id}/ledger")
    assert ledger_res.status_code == 200
    ledger_entries = ledger_res.json()["entries"]
    event_actions = [e["action"] for e in ledger_entries]
    assert "template.uploaded" in event_actions
    assert "document.generated_brd" in event_actions

    # 6. Verify document retrieval via standard documents API
    get_doc = auth_client.get(f"/api/documents/{brd['id']}")
    assert get_doc.status_code == 200
    assert get_doc.json()["version"] == 1
    assert get_doc.json()["title"] == "FinTech Hub Production BRD v1"


def test_generate_brd_from_direct_sections(auth_client):
    """Test generating BRD with directly supplied sections array without template_id."""
    p_res = auth_client.post("/api/projects", json={"name": "Direct Sections Project", "description": "BRD test"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    sections = [
        {"heading": "Executive Summary", "level": 1, "content": "Overview for {{project_name}}."},
        {"heading": "System Architecture", "level": 2, "content": ""},
        {"heading": "Functional Requirements", "level": 2, "content": ""},
        {"heading": "Non-Functional Requirements", "level": 2, "content": ""}
    ]

    gen_res = auth_client.post(
        f"/api/projects/{project_id}/templates/generate-brd",
        json={
            "title": "Custom Architecture BRD",
            "sections": sections,
            "variables": {"project_name": "Direct Sections System"}
        }
    )
    assert gen_res.status_code == 201
    brd = gen_res.json()
    assert brd["kind"] == "brd"
    assert brd["title"] == "Custom Architecture BRD"
    assert len(brd["sections"]) == 4

    content = brd["content"]
    assert "Direct Sections System" in content
    assert "FR-001" in content or "Functional Requirements" in content
    assert "Performance" in content or "Non-Functional Requirements" in content
