import pytest
from backend.harness.domain_brd_generator import (
    extract_topic_and_kind,
    build_atm_machine_brd,
    build_generic_domain_brd,
    generate_domain_brd,
)
from backend.core import documents
from backend.core.seed_data import seed_database
from backend.db import db


@pytest.fixture(autouse=True)
def ensure_db():
    seed_database()


def test_extract_topic_and_kind():
    topic, kind, title = extract_topic_and_kind("create BRD for ATM machine")
    assert "atm" in topic.lower()
    assert kind == "brd"
    assert "Business Requirements Document" in title

    topic, kind, title = extract_topic_and_kind("generate PRD for Payment Gateway")
    assert "Payment Gateway" in topic
    assert kind == "prd"
    assert "Product Requirements Document" in title

    topic, kind, title = extract_topic_and_kind("author BRD for Python Calculator React Application")
    assert "Calculator" in topic
    assert kind == "brd"

    topic, kind, title = extract_topic_and_kind("create BRD for https://github.com/sarveshtalele/mcp-server-market")
    assert "mcp-server-market" in topic.lower()
    assert kind == "brd"


def test_build_atm_machine_brd():
    content = build_atm_machine_brd("prj_agentic_qe", "ATM Machine System Specification")
    
    # Must contain essential ATM domain capabilities
    assert "ATM" in content or "Automated Teller Machine" in content
    assert "EMV chip" in content
    assert "3DES" in content
    assert "ISO-8583" in content
    assert "multi-denomination" in content.lower() or "Multi-Denomination" in content
    
    # Must contain structured Functional Requirements
    assert "FR-ATM-001" in content
    assert "FR-ATM-002" in content
    assert "FR-ATM-003" in content
    assert "FR-ATM-010" in content

    # Must contain Gherkin Acceptance Criteria with Given-When-Then
    assert "Feature: Automated Teller Machine (ATM)" in content
    assert "Scenario: Successful cash withdrawal" in content
    assert "Given" in content
    assert "When" in content
    assert "Then" in content

    # Must contain Quality Gates & Traceability Matrix
    assert "Gate 1" in content
    assert "Traceability Matrix" in content


def test_build_generic_domain_brd():
    content = build_generic_domain_brd(
        "Cloud Healthcare Telemedicine Platform",
        "prj_agentic_qe",
        "Business Requirements Document - Cloud Healthcare Telemedicine Platform"
    )
    
    assert "Cloud Healthcare Telemedicine Platform" in content
    assert "1. Executive Summary" in content
    assert "5. Detailed Functional Requirements" in content
    assert "8. Validated Gherkin Acceptance Scenarios" in content
    assert "Scenario:" in content
    assert "Given" in content
    assert "When" in content
    assert "Then" in content
    assert "Traceability Matrix" in content


def test_generate_domain_brd_saves_to_database():
    title, content, meta = generate_domain_brd("create BRD for ATM machine", "prj_agentic_qe")
    
    assert "ATM" in title or "Atm" in title
    assert len(content) > 1000
    assert meta["kind"] == "brd"
    assert meta["doc_id"].startswith("doc_")
    assert meta["review_score"] >= 85
    assert meta["verdict"] == "PASS"

    # Verify that the document is committed in the database with a valid SHA-256 hash
    doc_record = documents.get(meta["doc_id"])
    assert doc_record is not None
    assert doc_record["title"] == title
    assert len(doc_record["sha256"]) == 64
    assert doc_record["kind"] == "brd"
    assert doc_record["status"] == "draft"

    # Verify that companion Gherkin feature file document was created and left in draft
    gherkin_id = meta.get("gherkin_id")
    assert gherkin_id is not None
    gherkin_doc = documents.get(gherkin_id)
    assert gherkin_doc is not None
    assert gherkin_doc["kind"] == "gherkin"
    assert gherkin_doc["parent_id"] == meta["doc_id"]
    assert gherkin_doc["status"] == "draft"
