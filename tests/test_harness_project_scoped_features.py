import os
import time
import pytest
from backend import config
from backend.db import db
from backend.core.seed_data import seed_database
from backend.harness.session import SessionState
from backend.harness.qe_tools import build_qe_tools
from backend.maf.evals.store import detail, card
from backend.core import gates, documents

def make_session(id: str, project_id: str) -> SessionState:
    now = int(time.time() * 1000)
    return SessionState(
        id=id,
        name=f"Session {id}",
        workingDir=os.getcwd(),
        projectId=project_id,
        createdAt=now,
        updatedAt=now
    )

@pytest.fixture(autouse=True)
def setup_test_environment():
    # force=True: other modules create prj_mcp_market without findings, and the app no longer seeds at startup (plan D-05),
    # so this module inserts its own fixture rows (INSERT OR IGNORE) whatever ran before it.
    seed_database(force=True)
    yield

@pytest.mark.asyncio
async def test_harness_document_creation_persists_to_selected_project(tmp_path):
    workspace = os.getcwd()
    tools = {t.name: t for t in build_qe_tools(workspace)}
    
    target_project = "prj_mcp_market"
    session = make_session("sess_test_doc_proj", target_project)
    
    # 1. Create document via handle_create_document
    res = await tools["create_document"].execute({
        "kind": "brd",
        "title": "Automated Trading System BRD",
        "content": "# Automated Trading System BRD\n\n10 Sections with strict validation."
    }, context={"session": session, "projectId": target_project})
    
    doc_id = res["documentId"]
    assert res["projectId"] == target_project
    assert res["status"] == "Created"
    
    # Verify in SQLite database
    with db() as con:
        row = con.execute("SELECT project_id, title, kind FROM documents WHERE id=?", (doc_id,)).fetchone()
        assert row is not None
        assert row["project_id"] == target_project
        assert row["kind"] == "brd"
        assert row["title"] == "Automated Trading System BRD"
        
    # Verify file saved on disk in project documents directory
    disk_path = config.project_dir(target_project) / "documents" / f"{doc_id}.md"
    assert disk_path.exists()
    with open(disk_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Automated Trading System BRD" in content

@pytest.mark.asyncio
async def test_harness_feature_building_writes_to_project_sandbox():
    workspace = os.getcwd()
    tools = {t.name: t for t in build_qe_tools(workspace)}
    
    target_project = "prj_ecommerce_core"
    session = make_session("sess_test_feat_proj", target_project)
    
    config.repo_dir(target_project).mkdir(parents=True, exist_ok=True)  # the project's real repository folder
    rel_path = "src/features/cart_discount.ts"
    code = "// Cart Discount Feature\nexport function calculateDiscount(subtotal: number) { return subtotal * 0.15; }\n"
    
    res = await tools["implement_feature"].execute({
        "filePath": rel_path,
        "code": code,
        "description": "Cart discount implementation"
    }, context={"session": session, "projectId": target_project})
    
    assert res["projectId"] == target_project
    assert res["status"] == "Implemented"
    assert res["fileWritten"] is True
    
    # Verify written inside the project's repository (config.repo_dir), not the platform's own folder
    expected_path = str(config.repo_dir(target_project) / rel_path)
    assert os.path.exists(expected_path)
    assert not os.path.exists(os.path.join(workspace, rel_path))
    with open(expected_path, "r", encoding="utf-8") as f:
        written_code = f.read()
    assert "calculateDiscount" in written_code

@pytest.mark.asyncio
async def test_harness_security_audit_persists_findings_and_gates_to_project():
    workspace = os.getcwd()
    tools = {t.name: t for t in build_qe_tools(workspace)}
    
    target_project = "prj_fintech_gateway"
    session = make_session("sess_test_sec_proj", target_project)
    
    # No repository: nothing was scanned, and the tool says so instead of reporting NoFindings
    from backend.db import now
    with db() as con:
        con.execute("INSERT OR IGNORE INTO projects (id, name, description, created_at, updated_at, archived, owner_id) "
                    "VALUES ('prj_sec_norepo', 'No repo', '', ?, ?, 0, 'admin')", (now(), now()))
    assert not config.repo_dir("prj_sec_norepo").exists()
    res = await tools["qe_security_audit"].execute({}, context={"projectId": "prj_sec_norepo"})
    assert res["status"] == "NotScanned" and res["reason"]

    # A fake AWS key line planted in the project's real repository is found
    repo = config.repo_dir(target_project)
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "settings.py").write_text('AWS_KEY = "AKIA' + 'QZXWVUTSRQ234567' + '"\n', encoding="utf-8")
    gate5_before = gates.is_approved(target_project, 5)
    res = await tools["qe_security_audit"].execute({}, context={"session": session, "projectId": target_project})

    assert res["projectId"] == target_project
    assert res["status"] in ("Analyzed", "Partial")
    assert any(f["rule"] == "SEC001" and f["file"] == "settings.py" for f in res["findings"]), res["findings"]
    assert "secrets" in res["analyzersRan"]
    assert isinstance(res["findings"], list)
    assert res["findingCount"] == sum(res["bySeverity"].values())
    assert "specterScore" not in res and "specterGrade" not in res

    # Real analysis only: no gate changes
    assert gates.is_approved(target_project, 5) == gate5_before

def test_harness_toolset_has_no_gate_approving_tools():
    names = {t.name for t in build_qe_tools(os.getcwd())}
    assert "run_quality_lifecycle" not in names
    assert "decide_approval" not in names

@pytest.mark.asyncio
async def test_harness_skill_execution_resolves_and_persists_per_project():
    workspace = os.getcwd()
    tools = {t.name: t for t in build_qe_tools(workspace)}
    
    target_project = "prj_ecommerce_core"
    session = make_session("sess_test_skills_proj", target_project)
    
    # 1. BA Studio User Stories
    us_res = await tools["create_user_stories"].execute({
        "feature": "One-Click Checkout"
    }, context={"session": session, "projectId": target_project})
    
    assert us_res["projectId"] == target_project
    assert "documentId" in us_res
    
    # 2. Gherkin Acceptance Scenarios
    gh_res = await tools["generate_gherkin"].execute({
        "featureTitle": "One-Click Checkout"
    }, context={"session": session, "projectId": target_project})
    
    assert gh_res["projectId"] == target_project
    assert "documentId" in gh_res
    
    # Verify documents in SQLite for ecommerce
    with db() as con:
        us_doc = con.execute("SELECT project_id, kind FROM documents WHERE id=?", (us_res["documentId"],)).fetchone()
        gh_doc = con.execute("SELECT project_id, kind FROM documents WHERE id=?", (gh_res["documentId"],)).fetchone()
        assert us_doc["project_id"] == target_project
        assert us_doc["kind"] == "user_stories"
        assert gh_doc["project_id"] == target_project
        assert gh_doc["kind"] == "gherkin"

def test_agent_metrics_not_reported_as_measured_without_an_eval_run():
    # No real eval run: any stored baseline rows are removed, so nothing may be reported as measured.
    with db() as con:
        con.execute("DELETE FROM evaluation_metrics")
    for agent in ["project-copilot", "business-analyst", "repo-intelligence-analyst", "confidence-reviewer"]:
        d = detail(agent)
        assert d["agent"] == agent
        for m in d["metrics"]:
            assert m["state"] in ("n/a", "not_measured"), f"Metric {m['metric']} on {agent} reported without a run: {m}"
            assert m.get("value") is None
            assert "ragas-specter-v1" not in m.get("judge_model", "")

def test_project_sdlc_export_zip_package():
    import io
    import zipfile
    from fastapi.testclient import TestClient
    from backend.app import app

    with TestClient(app) as client:
        admin_user = os.environ.get("ATLAS_ADMIN_USERNAME", "qa-admin")
        admin_pass = os.environ.get("ATLAS_ADMIN_PASSWORD", "")
        login_res = client.post(
            "/api/auth/login",
            json={"username": admin_user, "password": admin_pass},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"

        res = client.get("/api/projects/prj_mcp_market/export-zip")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/zip"
        assert "prj_mcp_market_sdlc_export.zip" in res.headers["content-disposition"]

        zf = zipfile.ZipFile(io.BytesIO(res.content))
        names = zf.namelist()
        assert "setup_mac_linux.sh" in names
        assert "setup_windows.bat" in names
        assert "README_SETUP.md" in names

        sh_content = zf.read("setup_mac_linux.sh").decode("utf-8")
        assert "python3 -m venv" in sh_content
        assert "pytest" in sh_content

        bat_content = zf.read("setup_windows.bat").decode("utf-8")
        assert "call .venv\\Scripts\\activate.bat" in bat_content

        readme_content = zf.read("README_SETUP.md").decode("utf-8")
        assert "Architecture Overview" in readme_content

@pytest.mark.asyncio
async def test_harness_bug_fixes_query_grounded_in_centralized_db():
    from backend.harness.harness_agent import HarnessAgent
    from backend.harness.llm_config import LLMConfig
    from backend.db import db

    with db() as con:
        expected_count = con.execute("SELECT COUNT(*) as c FROM findings WHERE project_id='prj_mcp_market'").fetchone()["c"]

    harness = HarnessAgent()
    now_ms = int(time.time() * 1000)
    session = SessionState(
        id="sess_test_bugs_grounding",
        name="Bug Grounding Test",
        workingDir=os.getcwd(),
        projectId="prj_mcp_market",
        createdAt=now_ms,
        updatedAt=now_ms
    )
    config = LLMConfig(api_key="", base_url="https://api.openai.com/v1")
    chunks = []
    async for c in harness.run(session, "How many bug fixes are listed for this application", config):
        chunks.append(c)
    full_output = "".join(chunks)

    # Verify grounding facts from atlas.sqlite3
    assert "Centralized Database Grounding" in full_output
    assert f"{expected_count} defect findings" in full_output
    assert "scan_defects" in full_output
    assert "| Bug ID | Severity | Location | Defect Description / Title | Rule | Status |" in full_output

@pytest.mark.asyncio
async def test_harness_documents_query_grounded_in_centralized_db():
    from backend.harness.harness_agent import HarnessAgent
    from backend.harness.llm_config import LLMConfig
    from backend.db import db

    with db() as con:
        docs_count = con.execute("SELECT COUNT(*) as c FROM documents WHERE project_id='prj_mcp_market'").fetchone()["c"]

    harness = HarnessAgent()
    now_ms = int(time.time() * 1000)
    session = SessionState(
        id="sess_test_docs_grounding",
        name="Docs Grounding Test",
        workingDir=os.getcwd(),
        projectId="prj_mcp_market",
        createdAt=now_ms,
        updatedAt=now_ms
    )
    config = LLMConfig(api_key="", base_url="https://api.openai.com/v1")
    chunks = []
    async for c in harness.run(session, "how many documents are created for this project", config):
        chunks.append(c)
    full_output = "".join(chunks)

    assert "Centralized Database Grounding" in full_output
    assert f"{docs_count} governed documents" in full_output
    assert "read_document" in full_output

@pytest.mark.asyncio
async def test_harness_quality_gates_query_grounded_in_centralized_db():
    from backend.harness.harness_agent import HarnessAgent
    from backend.harness.llm_config import LLMConfig
    from backend.db import db

    with db() as con:
        gates_count = con.execute("SELECT COUNT(*) as c FROM gates WHERE project_id='prj_mcp_market'").fetchone()["c"]
        approved = con.execute("SELECT COUNT(*) as c FROM gates WHERE project_id='prj_mcp_market' AND status='approved'").fetchone()["c"]

    harness = HarnessAgent()
    now_ms = int(time.time() * 1000)
    session = SessionState(
        id="sess_test_gates_grounding",
        name="Gates Grounding Test",
        workingDir=os.getcwd(),
        projectId="prj_mcp_market",
        createdAt=now_ms,
        updatedAt=now_ms
    )
    config = LLMConfig(api_key="", base_url="https://api.openai.com/v1")
    chunks = []
    async for c in harness.run(session, "show quality gates status", config):
        chunks.append(c)
    full_output = "".join(chunks)

    assert "Centralized Database Grounding" in full_output
    assert "Quality Engineering Gates Scorecard" in full_output
    assert f"{approved}/{gates_count} Gates Approved" in full_output
    assert "check_gates" in full_output

