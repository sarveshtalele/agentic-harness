"""End to end on the real model (R3, plan 12.4): BA Studio's brainstorm in the browser. Upload a slide deck, describe the
need, pass Gate 0, answer the first question with an edited play-back, see the next question, then stop.
Run with  python scripts/dev.py live tests/e2e/test_ba_brainstorm.py"""
import pytest
from playwright.sync_api import expect

from tests.e2e.helpers_app import UI, approve_next, shot
from tests.test_brainstorm_r3 import _pptx

pytestmark = [pytest.mark.e2e, pytest.mark.live]


def test_brainstorm_one_question_at_a_time_in_ba_studio(page):
    project = page.request.post(f"{UI}/api/projects", data={"name": "Brainstorm UI", "description": "Refunds"}).json()
    uploaded = page.request.post(f"{UI}/api/projects/{project['id']}/sources",
                                 multipart={"file": {"name": "kickoff.pptx", "mimeType": "application/octet-stream", "buffer": _pptx()}})
    assert uploaded.ok, uploaded.text()
    page.goto(f"{UI}/projects/{project['id']}/ba")
    page.get_by_label("What you need").fill("Customers can refund part of an order within 30 days")
    page.get_by_role("button", name="Start brainstorming").click()
    approve_next(page, "Gate 0")
    step = page.get_by_test_id("brainstorm-step")
    expect(step).to_contain_text("Brainstorm question 1", timeout=240_000)
    expect(step.get_by_label("Question")).not_to_be_empty()
    expect(step).to_contain_text("Why I ask:")
    shot(page, "r3-brainstorm-question-1")
    step.get_by_label("What I understood so far").fill("Partial refunds of card orders within 30 days; finance approves above 500 EUR (BA answer)")
    step.get_by_label("Your answer").fill("Finance approves refunds above 500 EUR; after 30 days refunds are refused")
    step.get_by_role("button", name="Answer").click()
    expect(step).to_contain_text("Brainstorm question 2", timeout=240_000)
    step.get_by_text("Earlier questions (1)").click()
    expect(step).to_contain_text("after 30 days refunds are refused")
    shot(page, "r3-brainstorm-question-2")
    step.get_by_role("button", name="Stop").click()
    expect(page.get_by_test_id("brainstorm-step")).to_have_count(0, timeout=60_000)
