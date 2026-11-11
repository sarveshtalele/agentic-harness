"""Shared constants and helpers for the end-to-end app tests."""

import time

from pathlib import Path

from playwright.sync_api import expect


ROOT = Path(__file__).resolve().parents[2]


EVIDENCE = ROOT / "docs" / "evidence"


UI = "http://127.0.0.1:3010"


LLM_TIMEOUT = 420_000


def shot(page, name: str) -> None:
    page.screenshot(path=str(EVIDENCE / f"{name}.png"), full_page=True)


def wait_card(page, title_part: str):
    """Wait for an approval, or stop at once with the real error if the run failed."""
    card = page.get_by_test_id("approval-card")
    deadline = time.time() + LLM_TIMEOUT / 1000
    while time.time() < deadline:
        if card.count() and title_part in card.first.inner_text():
            return card
        status = page.get_by_test_id("run-status")
        if status.count() and "failed" in status.inner_text():
            raise AssertionError(f"Run failed: {page.locator('p[role=alert]').first.inner_text()}")
        page.wait_for_timeout(1000)
    raise AssertionError(f"Timed out waiting for {title_part}")


def approve(card) -> None:
    """The real flow: Approve stays disabled while REJECT items exist until a person gives a reason, so the reason is filled whenever its input is shown."""
    reason = card.get_by_test_id("reject-reason")
    if reason.count() and reason.first.is_visible():
        reason.first.fill("Reviewed by the tester: the open REJECT items are accepted for this end-to-end run")
    card.get_by_role("button", name="Approve").click()


def approve_next(page, title_part: str) -> None:
    card = wait_card(page, title_part)
    approve(card)
    expect(card.filter(has_text=title_part)).to_have_count(0, timeout=30_000)
