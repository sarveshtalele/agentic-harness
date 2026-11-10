"""
Integration Tests for Universal Harness & Human-in-the-Loop (HITL) Approvals.
Tests:
1. Universal Tool Registration across all 9 platform feature domains:
   - 1. Repository inspection (inspect_repo, view_tree, read_file)
   - 2. BA Studio (create_user_stories, generate_gherkin)
   - 3. Documents Hub (create_document, read_document, update_document)
   - 4. Feature Builder (run_sandbox_command, implement_feature)
   - 5. Bug Scan & Healing (scan_defects, heal_test_drift)
   - 6. Quality Engineering (run_quality_lifecycle, check_gates)
   - 7. Governance & Approvals (list_pending_approvals, decide_approval)
   - 8. Observability (query_system_logs, get_error_summary)
   - 9. MCP Servers (list_mcp_servers, execute_mcp_tool)
2. Destructive vs. safe tool approval enforcement (requires_approval)
3. HITL Approval decisions via API:
   - POST /api/projects/{project_id}/approvals/{approval_id}/decide (approve and reject)
   - POST /api/approvals/{approval_id}/decide
   - POST /api/approvals
   - In-memory harness approval manager resolution
   - SQLite persistence and audit ledger append
4. Template Document Upload via API:
   - POST /api/projects/{project_id}/templates/upload (multipart FormData)
   - POST /api/templates/upload
5. Universal tool handlers execution & guardrails (traversal defense, assertion preservation)
"""
import io
import json
import os
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.db import db, rows, row, new_id, now
from backend.core import auth, ledger, gates
from backend.harness.qe_tools import build_qe_tools
from backend.harness.approval_manager import global_approval_manager


@pytest.fixture(autouse=True)
def _hitl_project():
    """Tools need a real project since P1 (plan D-19); this module creates its own instead of relying on seed data."""
    with db() as con:
        con.execute("INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived, owner_id) "
                    "VALUES ('prj_hitl_test', 'HITL test', '', ?, ?, 0, 'admin')", (now(), now()))
from backend.harness.harness_agent import HarnessAgent
from backend.harness.session import AgentSessionManager
from tests.test_api_workflows import unique

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_admin_client():
    c = TestClient(app)
    res = c.post("/api/auth/login", json={
        "username": os.environ["ATLAS_ADMIN_USERNAME"],
        "password": os.environ["ATLAS_ADMIN_PASSWORD"]
    })
    assert res.status_code == 200, res.text
    return c


# =========================================================================
# 1. UNIVERSAL TOOL REGISTRATION TESTS
# =========================================================================

def test_universal_qe_tools_registration():
    """Verify all 9 platform feature domains are registered in build_qe_tools."""
    tools = build_qe_tools(WORKSPACE_DIR)
    tool_map = {t.name: t for t in tools}

    # 1. Repository inspection
    assert "inspect_repo" in tool_map
    assert "view_tree" in tool_map
    assert "read_file" in tool_map
    assert not tool_map["inspect_repo"].requires_approval
    assert not tool_map["view_tree"].requires_approval
    assert not tool_map["read_file"].requires_approval

    # 2. BA Studio
    assert "create_user_stories" in tool_map
    assert "generate_gherkin" in tool_map
    assert not tool_map["create_user_stories"].requires_approval
    assert not tool_map["generate_gherkin"].requires_approval

    # 3. Documents Hub
    assert "create_document" in tool_map
    assert "read_document" in tool_map
    assert "update_document" in tool_map
    assert not tool_map["create_document"].requires_approval
    assert not tool_map["read_document"].requires_approval
    assert tool_map["update_document"].requires_approval is True

    # 4. Feature Builder
    assert "run_sandbox_command" in tool_map
    assert "implement_feature" in tool_map
    assert tool_map["run_sandbox_command"].requires_approval is True
    assert tool_map["implement_feature"].requires_approval is True

    # 5. Bug Scan & Healing
    assert "scan_defects" in tool_map
    assert "heal_test_drift" in tool_map
    assert not tool_map["scan_defects"].requires_approval
    assert tool_map["heal_test_drift"].requires_approval is True

    # 6. Quality Engineering
    assert "run_quality_lifecycle" not in tool_map  # gates are decided only by a named human
    assert "check_gates" in tool_map
    assert not tool_map["check_gates"].requires_approval

    # 7. Governance & Approvals
    assert "list_pending_approvals" in tool_map
    assert "decide_approval" not in tool_map  # agents never decide approvals
    assert not tool_map["list_pending_approvals"].requires_approval

    # 8. Observability
    assert "query_system_logs" in tool_map
    assert "get_error_summary" in tool_map
    assert not tool_map["query_system_logs"].requires_approval
    assert not tool_map["get_error_summary"].requires_approval

    # 9. MCP Servers
    assert "list_mcp_servers" in tool_map
    assert "execute_mcp_tool" in tool_map
    assert not tool_map["list_mcp_servers"].requires_approval
    assert tool_map["execute_mcp_tool"].requires_approval is True


# =========================================================================
# 2. TOOL HANDLERS EXECUTION UNIT TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_repository_inspection_tools():
    """Verify inspect_repo, view_tree, and read_file safely execute."""
    tools = {t.name: t for t in build_qe_tools(WORKSPACE_DIR)}
    from backend import config
    repo = config.repo_dir("prj_hitl_test")  # the project's own repository, not the platform's folder
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "package.json").write_text('{"name": "hitl-fixture"}', encoding="utf-8")

    # inspect_repo
    res_inspect = await tools["inspect_repo"].execute({}, context={"projectId": "prj_hitl_test"})
    assert res_inspect["status"] == "Inspected"
    assert "repository" in res_inspect
    assert "detectedRunners" in res_inspect

    # view_tree
    res_tree = await tools["view_tree"].execute({"maxDepth": 2}, context={"projectId": "prj_hitl_test"})
    assert "tree" in res_tree
    assert res_tree["nodesCount"] > 0

    # read_file
    res_read = await tools["read_file"].execute({"filePath": "package.json"}, context={"projectId": "prj_hitl_test"})
    assert "hitl-fixture" in res_read["content"]

    # Platform files and escapes are refused, also through targetDir
    for bad in ("../../etc/passwd", os.path.join(WORKSPACE_DIR, "CLAUDE.md")):
        with pytest.raises(ValueError, match="escape"):
            await tools["read_file"].execute({"filePath": bad}, context={"projectId": "prj_hitl_test"})
    with pytest.raises(ValueError, match="escape"):
        await tools["inspect_repo"].execute({"targetDir": WORKSPACE_DIR}, context={"projectId": "prj_hitl_test"})


@pytest.mark.asyncio
async def test_tools_require_explicit_project():
    """No project selected is an explicit error, never a fabricated project id."""
    tools = {t.name: t for t in build_qe_tools(WORKSPACE_DIR)}
    with pytest.raises(ValueError, match="projectId is required"):
        await tools["inspect_repo"].execute({}, context={})


def test_decide_approval_and_lifecycle_are_not_registered():
    names = {t.name for t in build_qe_tools(WORKSPACE_DIR)}
    assert "decide_approval" not in names
    assert "run_quality_lifecycle" not in names


@pytest.mark.asyncio
async def test_ba_studio_tools():
    """Verify create_user_stories and generate_gherkin produce valid specs."""
    tools = {t.name: t for t in build_qe_tools(WORKSPACE_DIR)}

    stories_res = await tools["create_user_stories"].execute({"feature": "Payment Gateway Integration"}, context={"projectId": "prj_hitl_test"})
    assert stories_res["status"] == "Created"
    assert len(stories_res["userStories"]) >= 2
    assert stories_res["userStories"][0]["priority"] == "P0"

    gherkin_res = await tools["generate_gherkin"].execute({"userStoryId": "US-PAY-01", "featureTitle": "Payment Gateway"}, context={"projectId": "prj_hitl_test"})
    assert gherkin_res["status"] == "Generated"
    assert "Feature: Payment Gateway" in gherkin_res["gherkin"]
    assert "Scenario:" in gherkin_res["gherkin"]
    assert "Given" in gherkin_res["gherkin"]


@pytest.mark.asyncio
async def test_bug_scan_and_healing_tools():
    """Verify scan_defects and heal_test_drift work with assertion preservation."""
    tools = {t.name: t for t in build_qe_tools(WORKSPACE_DIR)}

    defects_res = await tools["scan_defects"].execute({}, context={})
    assert defects_res["status"] == "Scanned"
    assert "defectsCount" in defects_res

    # Legitimate heal (preserving assertion)
    heal_res = await tools["heal_test_drift"].execute({
        "failedTestFile": "tests/test_sample.ts",
        "originalCode": "await page.click('button.submit'); expect(page).toHaveURL('/done');",
        "healedCode": "await page.click('[data-testid=\"submit\"]'); expect(page).toHaveURL('/done');"
    }, context={})
    assert heal_res["status"] == "Healed"
    assert heal_res["assertionPreserved"] is True

    # Weakened assertion must raise error
    with pytest.raises(ValueError):
        await tools["heal_test_drift"].execute({
            "failedTestFile": "tests/test_sample.ts",
            "originalCode": "expect(user.role).toBe('admin'); expect(result.status).toBe(200);",
            "healedCode": "expect(result.status).toBe(200);"  # weakened: removed role check
        }, context={})


@pytest.mark.asyncio
async def test_mcp_servers_tools():
    """Verify list_mcp_servers and execute_mcp_tool."""
    tools = {t.name: t for t in build_qe_tools(WORKSPACE_DIR)}

    servers_res = await tools["list_mcp_servers"].execute({}, context={})
    assert servers_res["status"] == "Listed"
    assert servers_res["total"] >= 1

    exec_res = await tools["execute_mcp_tool"].execute({
        "serverId": "mcp-playwright",
        "toolName": "navigate",
        "arguments": {"url": "http://localhost:3000"}
    }, context={})
    # The harness has no MCP client, so it reports that nothing ran instead of inventing a success
    assert exec_res["executionStatus"] == "NOT_EXECUTED"
    assert exec_res["error"]


# =========================================================================
# 3. HITL APPROVAL DECISIONS VIA API TESTS
# =========================================================================

def test_hitl_approval_decide_project_endpoint():
    """Verify POST /api/projects/{project_id}/approvals/{approval_id}/decide works and updates SQLite + ledger."""
    admin_client = get_admin_client()

    # 1. Create target project
    proj_name = unique("hitl_proj")
    p_res = admin_client.post("/api/projects", json={"name": proj_name, "description": "HITL Test Project"})
    assert p_res.status_code == 201
    project_id = p_res.json()["id"]

    # 2. Insert dummy run and pending approval into SQLite
    run_id = new_id("run")
    approval_id = new_id("appr")
    stamp = now()

    with db() as con:
        con.execute(
            "INSERT INTO runs (id, project_id, workflow, status, input, started_at, state) VALUES (?,?,?,?,?,?,?)",
            (run_id, project_id, "test_generation", "awaiting_approval", "{}", stamp, json.dumps({}))
        )
        con.execute(
            "INSERT INTO approvals (id, run_id, project_id, gate, title, summary, payload, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (approval_id, run_id, project_id, 0, "Gate 0: Intake & Scope", "Verify intake scope", "{}", "pending", stamp)
        )

    # 3. Fetch pending approvals for project
    list_res = admin_client.get(f"/api/projects/{project_id}/approvals")
    assert list_res.status_code == 200
    approvals = list_res.json()
    assert any(a["id"] == approval_id for a in approvals)

    # 4. Decide approval via POST /api/projects/{project_id}/approvals/{approval_id}/decide
    decide_res = admin_client.post(
        f"/api/projects/{project_id}/approvals/{approval_id}/decide",
        json={"approved": True, "feedback": "Synthetic test data verified and approved"}
    )
    assert decide_res.status_code == 200

    # 5. Verify SQLite approval status updated
    with db() as con:
        updated_appr = row(con.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)))
        assert updated_appr is not None
        assert updated_appr["status"] == "approved"
        assert updated_appr["feedback"] == "Synthetic test data verified and approved"
        assert updated_appr["decided_at"] is not None

    # 6. Verify audit ledger entry recorded
    ledger_res = admin_client.get(f"/api/projects/{project_id}/ledger")
    assert ledger_res.status_code == 200
    ledger_entries = ledger_res.json()["entries"]
    assert any(
        "gate" in e.get("action", "") or "approval" in e.get("action", "")
        for e in ledger_entries
    )


def test_hitl_approval_rejection_project_endpoint():
    """Verify rejecting an approval via POST /api/projects/{project_id}/approvals/{approval_id}/decide."""
    admin_client = get_admin_client()

    p_res = admin_client.post("/api/projects", json={"name": unique("hitl_reject"), "description": "HITL Reject Test"})
    project_id = p_res.json()["id"]

    run_id = new_id("run")
    approval_id = new_id("appr")
    stamp = now()

    with db() as con:
        con.execute(
            "INSERT INTO runs (id, project_id, workflow, status, input, started_at, state) VALUES (?,?,?,?,?,?,?)",
            (run_id, project_id, "test_generation", "awaiting_approval", "{}", stamp, json.dumps({}))
        )
        con.execute(
            "INSERT INTO approvals (id, run_id, project_id, gate, title, summary, payload, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (approval_id, run_id, project_id, 3, "Gate 3: Deterministic Test Design", "Review oracles", "{}", "pending", stamp)
        )

    # Reject decision
    decide_res = admin_client.post(
        f"/api/projects/{project_id}/approvals/{approval_id}/decide",
        json={"approved": False, "feedback": "Missing boundary oracle"}
    )
    assert decide_res.status_code == 200

    with db() as con:
        updated_appr = row(con.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)))
        assert updated_appr["status"] == "rejected"
        assert updated_appr["feedback"] == "Missing boundary oracle"


def test_hitl_approval_in_memory_resolution():
    """Verify in-flight harness tool approvals resolve when decision endpoint is called."""
    admin_client = get_admin_client()

    p_res = admin_client.post("/api/projects", json={"name": unique("hitl_mem"), "description": "HITL In-Memory Test"})
    project_id = p_res.json()["id"]

    # Register in-memory pending approval
    pending = global_approval_manager.register_pending(
        tool_call_id="call_test_123",
        tool_name="implement_feature",
        args={"filePath": "src/test.ts"},
        gate={"gateNumber": 4, "gateName": "Synthetic Test Data"}
    )
    appr_id = pending.approval_id

    # Call decide endpoint for this in-memory approval
    res = admin_client.post(
        f"/api/projects/{project_id}/approvals/{appr_id}/decide",
        json={"approved": True, "feedback": "Approved feature implementation"}
    )
    assert res.status_code == 200
    assert pending.future.done()
    assert pending.future.result()["action"] == "approve"


# =========================================================================
# 4. TEMPLATE DOCUMENT UPLOAD VIA API TESTS
# =========================================================================

def test_template_upload_project_endpoint():
    """Verify POST /api/projects/{project_id}/templates/upload accepts .md template."""
    admin_client = get_admin_client()

    p_res = admin_client.post("/api/projects", json={"name": unique("tpl_proj"), "description": "Template Project"})
    project_id = p_res.json()["id"]

    md_content = b"""# Custom BRD Specification Template

## Executive Summary
Business goals and scope.

## Functional Requirements
FR-1: Authentication.

## Quality Engineering Acceptance Criteria
Gate 1 through 8 enforcement.
"""

    res = admin_client.post(
        f"/api/projects/{project_id}/templates/upload",
        files={"file": ("custom_template.md", io.BytesIO(md_content), "text/markdown")}
    )
    assert res.status_code == 201
    data = res.json()
    assert "template_id" in data
    assert "sections" in data
    assert len(data["sections"]) >= 3


def test_template_upload_plain_text_fallback():
    """Verify POST /api/projects/{project_id}/templates/upload handles text files without headers gracefully."""
    admin_client = get_admin_client()

    p_res = admin_client.post("/api/projects", json={"name": unique("tpl_txt"), "description": "Plain Text Template"})
    project_id = p_res.json()["id"]

    plain_content = b"Plain requirements without markdown hash headers.\nRequirement 1: Fast login.\n"

    res = admin_client.post(
        f"/api/projects/{project_id}/templates/upload",
        files={"file": ("plain_spec.txt", io.BytesIO(plain_content), "text/plain")}
    )
    assert res.status_code == 201
    data = res.json()
    assert "template_id" in data
    assert len(data.get("sections", [])) >= 1


# =========================================================================
# 5. HARNESS AGENT UNIVERSAL INTENT RESOLUTION
# =========================================================================

def test_harness_agent_skill_tool_resolution():
    """Verify HarnessAgent._resolve_skill_tool routes skills across all 9 feature domains."""
    agent = HarnessAgent(WORKSPACE_DIR)

    # 1. Repo inspection
    t_name, _ = agent._resolve_skill_tool("view-tree", "View Tree")
    assert t_name == "view_tree"

    t_name, _ = agent._resolve_skill_tool("read_file", "Read File")
    assert t_name == "read_file"

    # 2. BA Studio
    t_name, _ = agent._resolve_skill_tool("user-stories", "Create User Stories")
    assert t_name == "create_user_stories"

    t_name, _ = agent._resolve_skill_tool("gherkin-specs", "Generate Gherkin")
    assert t_name == "generate_gherkin"

    # 3. Feature Builder
    t_name, _ = agent._resolve_skill_tool("implement-feature", "Build Feature")
    assert t_name == "implement_feature"

    # 4. Bug Scan & Healing
    t_name, _ = agent._resolve_skill_tool("heal-drift", "Heal Broken Test")
    assert t_name == "heal_test_drift"

    t_name, _ = agent._resolve_skill_tool("scan-bugs", "Defect Scanner")
    assert t_name == "scan_defects"

    # 5. Governance & Approvals
    t_name, _ = agent._resolve_skill_tool("approvals-list", "List Approvals")
    assert t_name == "list_pending_approvals"

    # 6. Observability
    t_name, _ = agent._resolve_skill_tool("system-logs", "Query Logs")
    assert t_name == "query_system_logs"

    # 7. MCP Servers
    t_name, _ = agent._resolve_skill_tool("mcp-tools", "MCP Explorer")
    assert t_name == "list_mcp_servers"
