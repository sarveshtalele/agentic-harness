"""Solution architect (QE v2 step 6): typed output, and the code checks that refuse an unknown stack or an uncovered requirement."""
import json

import pytest

from backend.maf import llm
from backend.maf.agents import POLICIES
from backend.qe import architecture, stacks
from backend.qe.model import ArchitectureNote
from backend.qe.stacks import StackError
from tests.helpers_api import client, project  # noqa: F401 - fixtures
from tests.scripted_client import ScriptedClient

REQS = [{"id": "REQ-001", "title": "List expenses", "statement": "A user sees expenses.", "quote": "Users see expenses"},
        {"id": "REQ-002", "title": "Add expense", "statement": "A user adds an expense.", "quote": "Users add an expense"}]


def note(**change) -> dict:
    base = {"stack_id": "python-fastapi-react", "rationale": "A web page and a small API.",
            "modules": [{"name": "expenses", "purpose": "List and add", "requirement_ids": ["REQ-001", "REQ-002"]}],
            "data_model": [{"name": "Expense", "fields": ["id", "amount", "date"], "requirement_ids": ["REQ-001"]}],
            "api_routes": [{"method": "GET", "path": "/health", "purpose": "liveness", "requirement_ids": ["REQ-001"]}],
            "pages": [{"path": "/", "purpose": "the list", "requirement_ids": ["REQ-001"]}], "risks": []}
    return base | change


def test_the_agent_is_registered_with_its_prompt_and_eval():
    assert "solution-architect" in POLICIES
    root = stacks.ROOT.parents[1]
    assert (root / "prompts" / "solution-architect.md").is_file()
    cases = json.loads((root / "evals" / "solution-architect.json").read_text(encoding="utf-8"))
    assert cases and all(c["checks"]["json_schema"] == "ArchitectureNote" for c in cases)


def test_a_complete_note_passes():
    parsed = ArchitectureNote.model_validate(note())
    assert architecture.check_architecture(parsed, ["REQ-001", "REQ-002"]).stack_id == "python-fastapi-react"


@pytest.mark.parametrize("change,ids,message", [
    ({"stack_id": "rust-actix"}, ["REQ-001", "REQ-002"], "Unknown stack"),
    ({}, ["REQ-001", "REQ-002", "REQ-003"], "No module covers these requirements: REQ-003"),
    ({"api_routes": [{"method": "GET", "path": "/x", "purpose": "x", "requirement_ids": ["REQ-999"]}]}, ["REQ-001", "REQ-002"], "REQ-999"),
    ({"stack_id": "go"}, ["REQ-001", "REQ-002"], "no web page"),
])
def test_a_note_that_breaks_a_rule_is_refused(change, ids, message):
    with pytest.raises(StackError, match=message):
        architecture.check_architecture(ArchitectureNote.model_validate(note(**change)), ids)


def test_a_note_with_no_modules_fails_the_type():
    with pytest.raises(ValueError):
        ArchitectureNote.model_validate(note(modules=[]))


async def test_the_agent_reply_is_checked_and_a_refusal_is_sent_back_once(client, project):  # noqa: F811
    replies = [json.dumps(note(stack_id="rust-actix")), json.dumps(note())]
    scripted = ScriptedClient([("REQUIREMENTS:", lambda text: replies.pop(0))])
    llm.set_client_override(scripted)
    try:
        result = await architecture.design_architecture(None, project["id"], REQS)
    finally:
        llm.set_client_override(None)
    assert result.stack_id == "python-fastapi-react"
    assert "was refused: Unknown stack 'rust-actix'" in scripted.calls[-1]


async def test_a_note_still_refused_after_the_second_round_raises(client, project):  # noqa: F811
    llm.set_client_override(ScriptedClient([("REQUIREMENTS:", json.dumps(note(stack_id="rust-actix")))]))
    try:
        with pytest.raises(StackError, match="Unknown stack"):
            await architecture.design_architecture(None, project["id"], REQS)
    finally:
        llm.set_client_override(None)
