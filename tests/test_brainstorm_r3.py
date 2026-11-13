"""R3 (docs/PHASE2_PLAN.md 12.4): sources with their places, and brainstorming one question at a time to a signed BRD.
The model is the scripted stand-in; every human step goes through the real approvals API."""
import io
import json

import pytest

from backend.core import source_text
from backend.maf import llm
from tests.helpers_api import BRD, client, GOOD_REVIEW, FEATURE, pending, project, wait_run  # noqa: F401 - fixtures
from tests.scripted_client import ScriptedClient


def _pptx() -> bytes:
    from pptx import Presentation

    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = "Partial refunds"
    slide.notes_slide.notes_text_frame.text = "Finance approves refunds above 500 EUR"
    out = io.BytesIO()
    deck.save(out)
    return out.getvalue()


def test_sources_keep_slides_notes_and_pages_and_refuse_what_cannot_be_read(client, project, monkeypatch):
    made = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("kickoff.pptx", _pptx())}).json()
    text = source_text.extract_text("kickoff.pptx", _pptx())
    assert made["chars"] > 0 and "## Slide 1" in text and "Notes: Finance approves refunds above 500 EUR" in text
    monkeypatch.setattr(source_text, "soffice", lambda: None)
    refused = client.post(f"/api/projects/{project['id']}/sources", files={"file": ("legacy.ppt", b"\xd0\xcf\x11\xe0 not really")})
    assert refused.status_code == 415 and "LibreOffice" in refused.json()["message"]
    monkeypatch.setattr(source_text, "MAX_BYTES", 10)
    assert client.post(f"/api/projects/{project['id']}/sources", files={"file": ("big.md", b"x" * 50)}).status_code == 415


def test_brainstorm_asks_one_question_at_a_time_then_drafts_checks_and_signs(client, project):
    questions = iter([
        {"understood": "Partial refunds for card orders (kickoff.pptx slide 1)", "question": "Who approves a refund above 500 EUR?",
         "why": "It decides whether the BRD has a second approval path", "source": "kickoff.pptx slide 1", "done": False},
        {"understood": "Finance approves above 500 EUR (BA answer)", "question": "What happens after 30 days?", "why": "Refusal or a new path",
         "source": "the need", "done": False},
        {"understood": "Refunds after 30 days are refused (proposed)", "done": True},
    ])
    approaches = {"approaches": [{"name": "Manual approval queue", "summary": "Finance approves in a queue.", "tradeoffs": "Simple; slow"},
                                 {"name": "Rule-based auto approval", "summary": "Rules approve small refunds.", "tradeoffs": "Fast; rules to keep"}],
                  "recommended": 0}
    drafts = []
    llm.set_client_override(ScriptedClient([
        ("Artifact: brainstorm question.\n\nNEED", lambda _: json.dumps(next(questions))),
        ("Artifact: approaches.\n\nNEED", json.dumps(approaches)),
        ("Review type: builder check", '{"questions": ["Can finance reject a refund, and what does the customer see then?"]}'),
        ("Review type: requirements document", GOOD_REVIEW),
        ("Convert this document's requirements into one Gherkin feature file", FEATURE),
        ("Artifact: requirements document", lambda text: drafts.append(text) or BRD + ("\nRevised.\n" if "REVISE IT" in text else "")),
    ]))
    pid = project["id"]
    source = client.post(f"/api/projects/{pid}/sources", files={"file": ("kickoff.pptx", _pptx())}).json()
    run = client.post(f"/api/projects/{pid}/runs", json={"workflow": "brainstorm", "input": {
        "need": "Customers can refund part of an order within 30 days", "source_ids": [source["id"]], "template_id": "builtin_brd"}}).json()

    def step(**answer):
        current = wait_run(client, run["id"])
        assert current["status"] == "waiting_approval", current["error"]
        found = pending(current)
        assert client.post(f"/api/approvals/{found['id']}/decide", json={"approved": True, **answer}).status_code == 200
        return found

    assert step()["gate"] == 0
    first = step(action="answer", answer="Finance approves", question="Who signs off a refund above 500 EUR?")
    assert first["payload"]["kind"] == "brainstorm_question" and first["payload"]["why"] and first["payload"]["source"] == "kickoff.pptx slide 1"
    second = step(action="propose")
    assert second["payload"]["history"][0] == {"question": "Who signs off a refund above 500 EUR?", "answer": "Finance approves",
                                               "why": first["payload"]["why"], "source": "kickoff.pptx slide 1"}  # the edited question is kept
    pick = step(choice=1)
    assert pick["payload"]["kind"] == "brainstorm_approaches" and len(pick["payload"]["approaches"]) == 2
    check = step(answers=["Yes; the customer sees the reason"])
    assert check["payload"]["kind"] == "builder_check" and len(check["payload"]["questions"]) == 1
    gate1 = pending(wait_run(client, run["id"]))
    assert gate1["gate"] == 1
    assert "Rule-based auto approval" in drafts[0] and "Finance approves" in drafts[0] and "propose something" in drafts[0]
    assert "the customer sees the reason" in drafts[-1] and len(drafts) == 2  # one round of builder questions, then a redraft
    client.post(f"/api/approvals/{gate1['id']}/decide", json={"approved": True})
    assert wait_run(client, run["id"], ("completed", "failed"))["status"] == "completed"


@pytest.mark.parametrize("bad", [{"action": "delete-everything"}, {"choice": 9}, {"answers": ["a"] * 6}])
def test_answers_are_checked_at_the_door(client, bad):
    assert client.post("/api/approvals/apr_missing/decide", json={"approved": True, **bad}).status_code == 422
