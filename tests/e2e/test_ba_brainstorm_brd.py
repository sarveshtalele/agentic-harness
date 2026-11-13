"""End to end on the real model: a BRD made by brainstorming in BA Studio, all in the browser.

Upload a slide deck, describe the need, pass Gate 0, answer the first question, let the model propose the rest, choose an
approach, answer the builder check, sign Gate 1, then open the BRD and check it: the template's sections are there and
the analyst's answer (500 EUR, 30 days) is in it. Run with  python scripts/dev.py live tests/e2e/test_ba_brainstorm_brd.py"""
import time

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers_app import LLM_TIMEOUT, UI, approve, shot
from tests.test_brainstorm_r3 import _pptx

pytestmark = [pytest.mark.e2e, pytest.mark.live]
NEED = "Customers can refund part of an order within 30 days"
ANSWER = "Finance approves refunds above 500 EUR; after 30 days refunds are refused"


def _next(page):
    """The next brainstorm step or approval card, whichever shows first; None when the run has finished."""
    deadline = time.time() + LLM_TIMEOUT / 1000
    while time.time() < deadline:
        for testid in ("brainstorm-step", "approval-card"):
            found = page.get_by_test_id(testid)
            if found.count() and found.first.is_visible():
                return testid, found.first
        status = page.get_by_test_id("run-status")
        if status.count():
            text = status.first.inner_text()
            if "failed" in text:
                raise AssertionError(f"Run failed: {page.locator('p[role=alert]').first.inner_text()}")
            if "completed" in text:
                return None
        page.wait_for_timeout(1000)
    raise AssertionError("Timed out waiting for the next brainstorm step")


def test_a_brd_from_brainstorming_in_ba_studio(page):
    project = page.request.post(f"{UI}/api/projects", data={"name": "Brainstorm BRD", "description": "Refunds"}).json()
    uploaded = page.request.post(f"{UI}/api/projects/{project['id']}/sources",
                                 multipart={"file": {"name": "kickoff.pptx", "mimeType": "application/octet-stream", "buffer": _pptx()}})
    assert uploaded.ok, uploaded.text()
    page.goto(f"{UI}/projects/{project['id']}/ba")
    page.get_by_label("What you need").fill(NEED)
    page.get_by_role("button", name="Start brainstorming").click()
    seen, started = [], time.time()
    for _ in range(20):
        step = _next(page)
        if step is None:
            break
        testid, card = step
        text = card.inner_text()
        if testid == "approval-card":
            gate = "Gate 1" if "Gate 1" in text or "G1" in text else "Gate 0" if "Gate 0" in text or "G0" in text else "approval"
            seen.append(gate)
            shot(page, f"brd-{gate.lower().replace(' ', '-')}")
            approve(card)
        elif card.get_by_label("Your answer").count():
            seen.append("question")
            if seen.count("question") == 1:
                card.get_by_label("Your answer").fill(ANSWER)
                shot(page, "brd-question-1")
                card.get_by_role("button", name="Answer").click()
            else:
                card.get_by_role("button", name="I don't know, propose something").click()
        elif card.get_by_role("button", name="Choose this").count():
            seen.append("approaches")
            shot(page, "brd-approaches")
            card.get_by_role("button", name="Choose this").first.click()
        else:  # the builder check: one box per question
            seen.append("builder check")
            for box in card.locator("textarea").all():
                box.fill("Use your proposal")
            shot(page, "brd-builder-check")
            card.get_by_role("button", name="Send answers").click()
        expect(card).to_be_hidden(timeout=60_000)
        if seen[-1] == "Gate 1":
            break
    print(f"\nsteps: {seen}; {int(time.time() - started)} s")
    assert seen[0] == "Gate 0" and "question" in seen and "approaches" in seen and seen[-1] == "Gate 1", seen

    docs = page.request.get(f"{UI}/api/projects/{project['id']}/documents").json()
    brd = next(d for d in docs if "brd" in (d.get("kind") or "").lower() or "BRD" in (d.get("title") or ""))
    body = page.request.get(f"{UI}/api/documents/{brd['id']}").json()["content"]
    for heading in ("Business Requirements Document", "Functional Requirements", "Business Rules", "Acceptance Criteria"):
        assert heading in body, f"BRD lacks {heading!r}"
    assert "500" in body and "30 days" in body, "the analyst's answer is not in the BRD"
    page.goto(f"{UI}/projects/{project['id']}/documents/{brd['id']}")
    expect(page.get_by_role("heading", name="Functional Requirements", exact=False).first).to_be_visible(timeout=30_000)
    shot(page, "brd-document")
