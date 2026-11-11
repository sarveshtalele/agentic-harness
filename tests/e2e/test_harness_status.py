"""E2E US-60: while the harness works, the chat shows one live status line from real AG-UI events, and the finished
reply keeps the lines it went through. Each line must match a real tool call shown in the reply's tool list.

Runs only with real servers, the real model and a browser (`-m e2e`).
"""
from __future__ import annotations

import re
import time

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import EVIDENCE
from tests.e2e.test_harness_stories import UI, _create_project

pytestmark = pytest.mark.e2e
PHRASES = {"Finding tools": "find_tools", "Loading tools": "load_tools", "Analysing the repository": "scan_repository"}


def test_status_line_follows_real_tool_calls(page, tmp_path):
    pid = _create_project(page, tmp_path, "Status calculator", True)
    page.goto(f"{UI}/harness?project={pid}")
    expect(page.get_by_label("Agent for new chat")).to_have_value("harness", timeout=15_000)
    page.get_by_role("button", name="New chat").click()
    pane = page.get_by_test_id("chat-pane")
    box = pane.locator("textarea")
    expect(box).to_be_enabled(timeout=30_000)
    box.fill("Scan the repository with the static analyzers and list each finding with file and line.")
    box.press("Enter")
    status = pane.get_by_test_id("run-status")
    expect(status).to_be_visible(timeout=10_000)
    expect(pane.get_by_role("button", name="Stop the agent")).to_be_visible()
    seen, deadline = set(), time.time() + 420
    while status.count() and time.time() < deadline:  # one live line, replaced as events arrive
        seen.update(text.strip() for text in status.all_inner_texts())  # no wait: the line may vanish when the run ends
        page.wait_for_timeout(200)
    assert "Thinking" in seen, seen
    trail = pane.get_by_test_id("status-trail").last.inner_text()
    tools = " ".join(pane.get_by_test_id("tool-calls").all_inner_texts())
    for phrase, tool in PHRASES.items():
        if phrase in trail:
            assert tool in tools, (phrase, tools)  # a status line only ever comes from a real tool call
    assert re.search(r"Analysing the repository", trail), trail
    page.screenshot(path=str(EVIDENCE / "hs-status-line.png"))
