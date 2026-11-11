"""End-to-end, part 3: bug scan, feature builder, QE lifecycle, chat and harness."""

import re
import time

import pytest

from playwright.sync_api import expect

from tests.e2e.conftest import api_get, state
from tests.e2e.helpers_app import approve, approve_next, EVIDENCE, LLM_TIMEOUT, shot, UI, wait_card

pytestmark = pytest.mark.e2e


def test_09_bug_scan_finds_real_issues(page):
    page.goto(f"{state['base']}/bugs")
    page.get_by_role("button", name="Scan repository").click()
    expect(page.get_by_test_id("run-status")).to_contain_text("completed", timeout=LLM_TIMEOUT)
    findings = page.get_by_test_id("findings")
    expect(findings).to_contain_text("admin.py", timeout=20_000)
    expect(findings).to_contain_text("shell=True")
    shot(page, "10-bug-scan")


def test_10_feature_builder_runs_real_tests_on_a_branch(page):
    page.goto(f"{state['base']}/feature")
    page.locator('input[name="feature-title"]').fill("Fix restock")
    page.locator('textarea[name="feature-spec"]').fill("In inventory.py, restock(stock, quantity) wrongly subtracts. It must return stock + quantity and raise ValueError when quantity is not positive. Add tests in tests/test_inventory.py.")
    page.get_by_role("button", name="Build feature").click()
    card = wait_card(page, "Review change")
    expect(card).to_contain_text("stock + quantity")
    expect(card).to_contain_text("PASS")
    shot(page, "11-feature-diff")
    approve(card)
    expect(page.get_by_test_id("run-status")).to_contain_text("completed", timeout=60_000)
    expect(page.get_by_text("Commit", exact=False).first).to_be_visible()
    shot(page, "12-feature-committed")


def test_10b_fix_a_finding_on_a_branch(page):
    page.goto(f"{state['base']}/bugs")
    row = page.get_by_test_id("findings").get_by_test_id("finding").filter(has_text="admin.py").first
    row.get_by_role("button", name="Fix on a branch").click()
    card = wait_card(page, "Review change")
    expect(card).to_contain_text("diff --git a/admin.py")
    shot(page, "12b-bug-fix-diff")
    approve(card)
    expect(page.get_by_test_id("run-status")).to_contain_text("completed", timeout=60_000)


def test_11_qe_lifecycle_real_model_real_pytest(page):
    page.goto(f"{state['base']}/qe")
    page.get_by_role("button", name="Start QE lifecycle").click()
    expect(page.get_by_test_id("run-stages")).to_be_visible(timeout=30_000)
    expect(page.get_by_test_id("run-metrics")).to_contain_text("Elapsed")
    for gate in range(1, 5):
        approve_next(page, f"Gate {gate}")
        if gate == 3:
            shot(page, "13-qe-progress")
    card = wait_card(page, "Gate 5")
    summary = card.inner_text()
    assert re.search(r"Verdict (PASS|FAIL): \d+/[1-9]\d* tests passed", summary), f"tests must really execute: {summary}"
    state["qe_tokens"] = page.get_by_test_id("run-metrics").inner_text()
    shot(page, "14-qe-gate5")
    approve_next(page, "Gate 5")
    expect(page.get_by_test_id("run-status")).to_contain_text("completed", timeout=60_000)
    shot(page, "15-qe-complete")


def test_12_chat_answers_from_real_documents_and_persists(page):
    page.goto(f"{state['base']}/chat")
    page.get_by_role("button", name="New chat").click()
    pane = page.get_by_test_id("chat-pane")
    box = pane.locator("textarea")
    box.fill("List the saved documents in this project with their kinds. Use your tools.")
    box.press("Enter")
    expect(pane).to_contain_text("Inventory BRD", timeout=180_000)
    shot(page, "16-chat-documents")
    page.wait_for_timeout(3000)
    page.reload()
    saved = page.get_by_role("list", name="Saved chats").get_by_role("button", name=re.compile("^List the saved documents"))
    expect(saved).to_be_visible(timeout=15_000)
    saved.click()
    expect(page.get_by_test_id("chat-pane")).to_contain_text("Inventory BRD", timeout=15_000)
    shot(page, "17-chat-reopened")


def test_13_chat_memory_new_window_and_specialist_agent(page):
    with page.expect_popup() as popup:
        page.get_by_role("link", name="Open in new window").click()
    window = popup.value
    window.wait_for_load_state()
    window.get_by_label("Agent for new chat").select_option("project-copilot")
    window.get_by_role("button", name="New chat").click()
    pane = window.get_by_test_id("chat-pane")
    box = pane.locator("textarea")
    box.fill("Remember this for the project: the release freeze starts on Friday.")
    box.press("Enter")
    deadline = time.time() + 180
    while time.time() < deadline:
        if b"freeze" in api_get(f"/projects/{state['id']}/memories"):
            break
        time.sleep(2)
    else:
        raise AssertionError("the agent did not store the memory")
    expect(window.get_by_text(re.compile(r"Project memory \(1\)"))).to_be_visible(timeout=30_000)
    window.get_by_label("Agent for new chat").select_option("principal-test-architect")
    window.get_by_role("button", name="New chat").click()
    messages = window.get_by_test_id("chat-messages")
    expect(messages).to_contain_text("Ask about this project", timeout=15_000)  # a truly empty chat
    expect(messages).not_to_contain_text("Friday")
    box = window.get_by_test_id("chat-pane").locator("textarea")
    box.fill("When does the release freeze start, according to what you remember for this project?")
    box.press("Enter")
    expect(messages.locator('[data-role="assistant"]').last).to_contain_text("Friday", timeout=180_000)
    window.set_viewport_size({"width": 1100, "height": 800})
    window.screenshot(path=str(EVIDENCE / "18-chat-new-window.png"))
    window.close()


def test_13b_harness_page_plans_scans_and_shows_todos(page):
    """/harness runs MAF's create_harness_agent: a real todo appears in the panel and the real scan result reaches the reply."""
    page.goto(f"{UI}/harness?project={state['id']}")
    expect(page.get_by_label("Agent for new chat")).to_have_value("harness", timeout=15_000)
    page.get_by_role("button", name="New chat").click()
    pane = page.get_by_test_id("chat-pane")
    box = pane.locator("textarea")
    expect(box).to_be_enabled(timeout=30_000)
    box.fill("Add exactly one todo titled 'Scan the repository'. Then call scan_repository. Then mark that todo complete. "
             "Then reply with the number of findings it returned.")
    box.press("Enter")
    expect(page.get_by_test_id("harness-todo").first).to_contain_text("Scan the repository", timeout=LLM_TIMEOUT)
    expect(pane.locator('[data-role="assistant"]').last).to_contain_text(re.compile(r"\d"), timeout=LLM_TIMEOUT)
    shot(page, "13b-harness-page")
