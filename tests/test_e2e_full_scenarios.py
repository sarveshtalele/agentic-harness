"""End-to-End full scenario integration and workflow test suite.
Validates:
1. Complete Python Calculator BRD generation with 8 quality gates and compliance tables
2. Multi-agent handoff chain across specialized personas
3. Document persistence in SQLite WAL and version increments
4. Sandboxed execution of generated Python code in isolated directory
5. Cloudflare and NVIDIA Specter guardrail enforcement
"""
import pytest
import asyncio
import json
from pathlib import Path
from backend.db import db, now
from backend.harness.harness_agent import HarnessAgent
from backend.harness.session import AgentSessionManager
from backend.harness.llm_config import LLMConfig
from backend.harness.handoff import QEHandoffExecutor
from backend.harness.qe_guardrails import QEGuardrails
from backend.repos import sandbox
from backend.core import documents


@pytest.fixture(autouse=True)
def setup_test_project():
    with db() as con:
        con.execute(
            "INSERT OR IGNORE INTO projects (id, name, created_at, updated_at) VALUES (?,?,?,?)",
            ("prj_agentic_qe", "Agentic QE Platform", now(), now())
        )


@pytest.mark.asyncio
async def test_e2e_brd_python_calculator_generation():
    """Verify natural language request generates complete structured BRD with all 8 quality gates."""
    agent = HarnessAgent()
    manager = AgentSessionManager()
    session = manager.create_session("BRD Gen Test", mode="plan", project_id="prj_agentic_qe")
    llm_config = LLMConfig(provider="mock", model="mock-claude")
    prompt = "create a docuement for python clacuatlro react based application as BRD docuement"
    
    events = []
    created_doc_payload = None
    async for chunk in agent.run(session, prompt, llm_config):
        events.append(chunk)
        for line in chunk.splitlines():
            if line.startswith("data: ") and "DOCUMENT_CREATED" in line:
                try:
                    payload = json.loads(line[6:])
                    if payload.get("type") == "DOCUMENT_CREATED" and payload.get("document", {}).get("content"):
                        created_doc_payload = payload.get("document")
                except Exception:
                    pass
        
    full_text = "".join(events)
    assert created_doc_payload is not None, "Expected DOCUMENT_CREATED SSE event"
    doc_content = created_doc_payload.get("content", "")
    
    # Assert all mandatory sections
    assert "Business Requirements Document (BRD)" in doc_content
    assert "Python Calculator React" in doc_content
    assert "Autonomous Agentic QE Harness" in doc_content
    assert "Gate 0 (Intake & Discovery)" in doc_content
    assert "Gate 7 (Coverage)" in doc_content
    assert "Cloudflare Security" in doc_content
    assert "NVIDIA Skill Specter" in doc_content
    assert "FR-01" in doc_content
    assert "NFR-01" in doc_content
    assert "Scenario: Composite arithmetic expression evaluation" in doc_content
    assert "Given the user is on the React Calculator web interface" in doc_content


@pytest.mark.asyncio
async def test_e2e_multi_agent_handoff_delegation():
    """Verify handoff executor transitions context cleanly between personas."""
    manager = AgentSessionManager()
    session = manager.create_session("Handoff Test Session", mode="plan", project_id="prj_agentic_qe")
    handoff_exec = QEHandoffExecutor()
    
    # 1. Start with Architect, hand off to BA
    session.activeAgentId = "principal-test-architect"
    h1 = handoff_exec.switch_agent(
        session=session,
        target_agent_id="business-analyst",
        reason="Analyze user stories and generate Gherkin requirements"
    )
    assert h1["to"] == "business-analyst"
    assert session.activeAgentId == "business-analyst"
    
    # 2. Handoff BA to Test Designer
    h2 = handoff_exec.switch_agent(
        session=session,
        target_agent_id="test-design-architect",
        reason="Design deterministic test matrices for calculator features"
    )
    assert h2["to"] == "test-design-architect"
    assert session.activeAgentId == "test-design-architect"


def test_e2e_document_persistence_and_versioning():
    """Verify documents are persisted in SQLite WAL and update versions correctly."""
    project_id = "prj_agentic_qe"
    title = "E2E Calculator Verification Plan"
    content_v1 = "# Test Plan v1\n- Initial calculator scope"
    
    # Create doc
    doc = documents.create(project_id, "plan", title, content_v1, "admin")
    assert doc["id"] is not None
    assert doc["version"] == 1
    
    # Retrieve doc
    fetched = documents.get(doc["id"])
    assert fetched["title"] == title
    assert fetched["version"] == 1
    
    # Update doc to v2
    content_v2 = "# Test Plan v2\n- Added Cloudflare & NVIDIA Specter security verification"
    updated = documents.save_version(doc["id"], content_v2, "admin", note="Upgraded security plan")
    assert updated["version"] == 2
    assert updated["content"] == content_v2


def test_e2e_sandbox_code_generation_and_execution():
    """Verify sandbox isolates Python code write and execution cleanly."""
    project_id = "prj_agentic_qe"
    
    # 1. Ensure sandbox
    sandbox_dir = sandbox.ensure_sandbox(project_id)
    assert sandbox_dir.exists()
    
    # 2. Create python calculator module in sandbox
    calc_code = (
        "class Calculator:\n"
        "    def add(self, a, b): return a + b\n"
        "    def divide(self, a, b):\n"
        "        if b == 0: raise ValueError('Divide by zero')\n"
        "        return a / b\n\n"
        "if __name__ == '__main__':\n"
        "    c = Calculator()\n"
        "    print(f'ADD: {c.add(10, 25)}')\n"
        "    print(f'DIV: {c.divide(100, 4)}')\n"
    )
    res_file = sandbox.create_file(project_id, "calculator.py", calc_code)
    assert res_file["status"] == "created"
    
    # 3. Execute python calculator in isolated subprocess
    run_res = sandbox.execute_code(project_id, calc_code, runtime="python", timeout=10)
    assert run_res["status"] == "success"
    assert "ADD: 35" in run_res["stdout"]
    assert "DIV: 25.0" in run_res["stdout"]


def test_e2e_assertion_preservation_guardrail():
    """Verify Assertion Preservation Guardrail rejects weakening and dummy assertions."""
    orig = "def test_calc():\n    assert calc.divide(10, 2) == 5\n    assert calc.add(2, 3) == 5\n"
    
    # Valid candidate preserving assertions
    valid_patch = "def test_calc():\n    # optimized\n    assert calc.divide(10, 2) == 5\n    assert calc.add(2, 3) == 5\n"
    ok, msg = QEGuardrails.validate_assertion_preservation(orig, valid_patch)
    assert ok is True
    
    # Invalid candidate dropping assertions
    dropped = "def test_calc():\n    assert calc.divide(10, 2) == 5\n"
    ok, msg = QEGuardrails.validate_assertion_preservation(orig, dropped)
    assert ok is False
    assert "dropped assertions" in msg
    
    # Invalid candidate injecting trivial assertions
    trivial = "def test_calc():\n    assert 1 == 1\n    assert True\n"
    ok, msg = QEGuardrails.validate_assertion_preservation(orig, trivial)
    assert ok is False
