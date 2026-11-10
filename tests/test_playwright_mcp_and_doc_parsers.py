import io
import os
import sys
import pytest
from pathlib import Path
from docx import Document

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi.testclient import TestClient
from backend.app import app
from backend.repos.doc_parser import parse_document, extract_placeholders, _parse_docx_xml_fallback
from backend.api.mcp_playwright_tools import PLAYWRIGHT_MCP_TOOLS


@pytest.fixture
def auth_client():
    with TestClient(app) as test_client:
        login_res = test_client.post(
            "/api/auth/login",
            json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}
        )
        assert login_res.status_code == 200
        yield test_client


def test_playwright_mcp_all_tools_registered(auth_client):
    """Verify all 70+ official Playwright MCP tools are registered and returned via GET /api/mcp/servers."""
    res = auth_client.get("/api/mcp/servers")
    assert res.status_code == 200
    data = res.json()
    servers = data["servers"]

    pw_srv = next((s for s in servers if s["id"] == "srv_playwright"), None)
    assert pw_srv is not None, "srv_playwright must be pre-seeded and returned by /api/mcp/servers"
    assert pw_srv["name"] == "Playwright Browser Automation"
    assert pw_srv["command"] == "npx -y @playwright/mcp@latest"
    assert pw_srv["status"] == "connected"
    assert pw_srv["total_tools"] >= 70, f"Expected 70+ tools, found {pw_srv['total_tools']}"
    assert pw_srv["total_tools"] == 71

    tool_names = {t["name"] for t in pw_srv["tools"]}

    # 1. Core tools check
    core_tools = [
        "browser_navigate", "browser_navigate_back", "browser_snapshot", "browser_find",
        "browser_click", "browser_hover", "browser_drag", "browser_drop", "browser_type",
        "browser_fill_form", "browser_select_option", "browser_press_key", "browser_take_screenshot",
        "browser_tabs", "browser_handle_dialog", "browser_file_upload", "browser_console_messages",
        "browser_network_requests", "browser_network_request", "browser_evaluate",
        "browser_run_code_unsafe", "browser_wait_for", "browser_close", "browser_resize"
    ]
    for ct in core_tools:
        assert ct in tool_names, f"Core tool {ct} missing"

    # 2. Network tools check
    for nt in ["browser_route", "browser_route_list", "browser_unroute", "browser_network_state_set"]:
        assert nt in tool_names, f"Network tool {nt} missing"

    # 3. Storage tools check
    for st in [
        "browser_cookie_list", "browser_cookie_get", "browser_cookie_set", "browser_cookie_delete",
        "browser_cookie_clear", "browser_localstorage_list", "browser_localstorage_get",
        "browser_localstorage_set", "browser_localstorage_delete", "browser_localstorage_clear",
        "browser_sessionstorage_list", "browser_sessionstorage_get", "browser_sessionstorage_set",
        "browser_sessionstorage_delete", "browser_sessionstorage_clear", "browser_storage_state",
        "browser_set_storage_state"
    ]:
        assert st in tool_names, f"Storage tool {st} missing"

    # 4. Testing tools check
    for tt in [
        "browser_generate_locator", "browser_verify_element_visible",
        "browser_verify_text_visible", "browser_verify_list_visible", "browser_verify_value"
    ]:
        assert tt in tool_names, f"Testing tool {tt} missing"

    # 5. DevTools tools check
    for dt in [
        "browser_start_tracing", "browser_stop_tracing", "browser_start_video",
        "browser_stop_video", "browser_video_chapter", "browser_video_show_actions",
        "browser_video_hide_actions", "browser_start_recording", "browser_stop_recording",
        "browser_highlight", "browser_hide_highlight", "browser_annotate", "browser_resume"
    ]:
        assert dt in tool_names, f"DevTools tool {dt} missing"

    # 6. PDF, Vision, Config tools check
    assert "browser_pdf_save" in tool_names
    for vt in [
        "browser_mouse_move_xy", "browser_mouse_click_xy", "browser_mouse_drag_xy",
        "browser_mouse_down", "browser_mouse_up", "browser_mouse_wheel"
    ]:
        assert vt in tool_names, f"Vision tool {vt} missing"
    assert "browser_get_config" in tool_names

    # Check parameter schemas
    for t in pw_srv["tools"]:
        assert "description" in t and len(t["description"]) > 0
        assert "parameters_schema" in t
        assert isinstance(t["parameters_schema"], dict)


def test_playwright_tool_authorization_and_execution(auth_client):
    """Test tool authorization toggle (single and all) and execution blocking."""
    res = auth_client.get("/api/mcp/servers")
    pw_srv = next(s for s in res.json()["servers"] if s["id"] == "srv_playwright")
    tool = next(t for t in pw_srv["tools"] if t["name"] == "browser_navigate")
    tool_id = tool["id"]

    # 1. Disable single tool
    toggle_res = auth_client.post(f"/api/mcp/tools/{tool_id}/toggle", json={"authorized": False})
    assert toggle_res.status_code == 200
    assert toggle_res.json()["authorized"] is False

    # 2. Execution should now be rejected with 403 Forbidden
    exec_res = auth_client.post("/api/mcp/execute", json={
        "tool_id": tool_id,
        "arguments": {"url": "https://example.com"}
    })
    assert exec_res.status_code == 403

    # 3. Re-enable tool
    re_toggle = auth_client.post(f"/api/mcp/tools/{tool_id}/toggle", json={"authorized": True})
    assert re_toggle.status_code == 200
    assert re_toggle.json()["authorized"] is True

    # 4. Authorized now, so it passes the 403 check, and is honestly refused (501) instead of reporting a browser
    #    action that never ran: real MCP sessions arrive in plan P4 (D-14).
    exec_ok = auth_client.post("/api/mcp/execute", json={
        "tool_id": tool_id,
        "arguments": {"url": "https://example.com"}
    })
    assert exec_ok.status_code == 501
    assert "P4" in exec_ok.json()["detail"]

    # 5. Toggle all tools off
    toggle_all_off = auth_client.post("/api/mcp/servers/srv_playwright/toggle-all", json={"authorized": False})
    assert toggle_all_off.status_code == 200
    srv_check = auth_client.get("/api/mcp/servers").json()
    pw_srv_off = next(s for s in srv_check["servers"] if s["id"] == "srv_playwright")
    assert pw_srv_off["authorized_tools"] == 0

    # 6. Re-enable all tools
    toggle_all_on = auth_client.post("/api/mcp/servers/srv_playwright/toggle-all", json={"authorized": True})
    assert toggle_all_on.status_code == 200
    srv_check2 = auth_client.get("/api/mcp/servers").json()
    pw_srv_on = next(s for s in srv_check2["servers"] if s["id"] == "srv_playwright")
    assert pw_srv_on["authorized_tools"] == pw_srv_on["total_tools"]


def test_markdown_parser_with_headings_tables_and_sections():
    """Verify Markdown parser parses frontmatter, heading hierarchy, tables, and placeholders."""
    md_content = """---
title: E-Commerce Payment Gateway BRD
version: 1.0
---

# Executive Summary
The payment system enables secure card processing for {{project_name}}.
Main goal is zero-downtime transaction authorization.
[System Overview]

## Payment Methods & Capabilities
Supported mechanisms for {{scope}}:

| Code | Provider | Settlement Window | Active |
| --- | --- | --- | --- |
| PAY-01 | Stripe Cards | Instant | Yes |
| PAY-02 | Apple Pay | Instant | Yes |
| PAY-03 | Direct Debit | T+2 Days | No |

### Security & Compliance
- PCI-DSS Level 1 compliance required.
- TLS 1.3 encryption mandatory.

```python
def verify_signature(payload, secret):
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()
```

## Approval Matrix
Final sign-off from [Requirements] lead.
"""
    parsed = parse_document(md_content.encode("utf-8"), "payment_brd.md")

    assert parsed["title"] == "E-Commerce Payment Gateway BRD"
    assert len(parsed["sections"]) >= 3

    sec_headings = [s["heading"] for s in parsed["sections"]]
    assert "Executive Summary" in sec_headings
    assert "Payment Methods & Capabilities" in sec_headings
    assert "Security & Compliance" in sec_headings
    assert "Approval Matrix" in sec_headings

    # Check tables
    assert len(parsed["tables"]) == 1
    table_rows = parsed["tables"][0]
    assert len(table_rows) == 4  # Header + 3 rows
    assert table_rows[0] == ["Code", "Provider", "Settlement Window", "Active"]
    assert table_rows[1][0] == "PAY-01"

    # Check placeholders
    assert "{{project_name}}" in parsed["placeholders"]
    assert "{{scope}}" in parsed["placeholders"]
    assert "[System Overview]" in parsed["placeholders"]
    assert "[Requirements]" in parsed["placeholders"]


def test_docx_parser_extracting_paragraphs_headings_and_tables():
    """Verify Word (.docx) parser extracts structured headings, tables, and fallback xml."""
    doc = Document()
    doc.add_heading("Cloud Infrastructure Specification", level=1)
    doc.add_paragraph("Target architecture blueprint for {{project_name}}.")
    doc.add_heading("Networking & VPC", level=2)
    doc.add_paragraph("Virtual private cloud configuration adhering to [System Overview].")

    table = doc.add_table(rows=3, cols=3)
    headers = ["Subnet", "CIDR Block", "Public/Private"]
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = h
    row1 = ["App-Tier-A", "10.0.1.0/24", "Private"]
    for j, val in enumerate(row1):
        table.rows[1].cells[j].text = val
    row2 = ["Public-LB", "10.0.0.0/24", "Public"]
    for j, val in enumerate(row2):
        table.rows[2].cells[j].text = val

    doc.add_heading("Observability Requirements", level=3)
    doc.add_paragraph("All metrics monitored under {{scope}} guidelines.")

    buffer = io.BytesIO()
    doc.save(buffer)
    docx_bytes = buffer.getvalue()

    parsed = parse_document(docx_bytes, "infrastructure.docx")

    assert parsed["title"] == "Cloud Infrastructure Specification"
    assert len(parsed["sections"]) >= 3
    assert len(parsed["tables"]) == 1
    assert parsed["tables"][0][0] == ["Subnet", "CIDR Block", "Public/Private"]
    assert parsed["tables"][0][1][0] == "App-Tier-A"
    assert "{{project_name}}" in parsed["placeholders"]
    assert "[System Overview]" in parsed["placeholders"]
    assert "{{scope}}" in parsed["placeholders"]

    # Verify safe XML fallback parser also parses correctly
    fallback = _parse_docx_xml_fallback(docx_bytes, "infrastructure.docx")
    assert len(fallback["sections"]) >= 1
    assert "{{project_name}}" in fallback["placeholders"]


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


def test_playwright_add_server_auto_populates_all_tools(auth_client):
    """Test that connecting a new server with playwright in command automatically seeds all 71 tools."""
    add_res = auth_client.post(
        "/api/mcp/servers",
        json={
            "name": "Custom Dynamic Playwright",
            "type": "local_npx",
            "command": "npx -y @playwright/mcp@latest --caps=vision,pdf"
        }
    )
    assert add_res.status_code == 200
    srv = add_res.json()
    srv_id = srv["id"]
    assert srv["total_tools"] == 71
    tool_names = {t["name"] for t in srv["tools"]}
    assert "browser_pdf_save" in tool_names
    assert "browser_mouse_move_xy" in tool_names
    assert "browser_navigate" in tool_names

    # Clean up
    del_res = auth_client.delete(f"/api/mcp/servers/{srv_id}")
    assert del_res.status_code == 200


def test_playwright_sync_missing_tools_in_database():
    """Verify sync_playwright_tools adds missing tools to existing server in database."""
    from backend.db import db, new_id, now, rows
    from backend.api.mcp import sync_playwright_tools

    temp_srv_id = new_id("mcp_test_pw")
    ts = now()
    with db() as con:
        con.execute(
            "INSERT INTO mcp_servers (id, name, type, transport, command, url, status, error_message, created_at, updated_at) "
            "VALUES (?, 'Legacy Playwright Server', 'local_npx', 'stdio', 'npx -y @playwright/mcp', NULL, 'connected', '', ?, ?)",
            (temp_srv_id, ts, ts)
        )
        # Insert only 1 tool
        con.execute(
            "INSERT INTO mcp_tools (id, server_id, name, description, parameters_schema, authorized, created_at, updated_at) "
            "VALUES (?, ?, 'browser_navigate', 'Legacy tool', '{}', 1, ?, ?)",
            (new_id("tool"), temp_srv_id, ts, ts)
        )

    # Call sync
    sync_playwright_tools()

    with db() as con:
        tools = rows(con.execute("SELECT name FROM mcp_tools WHERE server_id=?", (temp_srv_id,)))
        # Clean up
        con.execute("DELETE FROM mcp_tools WHERE server_id=?", (temp_srv_id,))
        con.execute("DELETE FROM mcp_servers WHERE id=?", (temp_srv_id,))

    assert len(tools) == 71
    assert "browser_get_config" in {t["name"] for t in tools}
    assert "browser_pdf_save" in {t["name"] for t in tools}

