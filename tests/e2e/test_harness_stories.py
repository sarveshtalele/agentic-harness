"""E2E: every harness user story (docs/HARNESS_USER_STORIES.md) in the real browser, on the real model and repository.

A risky tool call stops at an approval card; `_ask` approves it as the human would and records it in story["approved"]. Skill Studio writes skills, so run with ATLAS_SKILLS_DIR pointing at a scratch copy of skills/.
"""
from __future__ import annotations

import json
import re
import time
import zipfile

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import EVIDENCE, api_get

pytestmark = pytest.mark.e2e
UI = "http://127.0.0.1:3010"
LLM = 420_000
story: dict = {}
REPO = {
    "calc.py": "import subprocess\n\n\ndef add(a, b):\n    return a + b\n\n\ndef backup(path):\n    return subprocess.call('tar -czf b.tgz ' + path, shell=True)\n",
    "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
}


def _create_project(page, tmp_path, name: str, with_repo: bool) -> str:
    page.goto(UI)
    page.get_by_role("button", name="New project").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Name").fill(name)
    dialog.get_by_label("Description").fill("Harness story checks")
    if with_repo:
        archive = tmp_path / "calc.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for path, body in REPO.items():
                bundle.writestr(path, body)
        dialog.locator('input[type="file"]').set_input_files(archive)
    dialog.get_by_role("button", name=re.compile("Create project|Cloning")).click()
    page.wait_for_url(re.compile(r"/projects/prj_"), timeout=60_000)
    return page.url.rsplit("/", 1)[-1]


def _ask(page, pid: str, prompt: str):
    """A new harness chat on /harness. Returns (pane, final reply): the reply is the one the server stored when the turn ended."""
    page.goto(f"{UI}/harness?project={pid}")
    expect(page.get_by_label("Agent for new chat")).to_have_value("harness", timeout=15_000)
    before = {c["id"] for c in json.loads(api_get(f"/projects/{pid}/chats"))}
    page.get_by_role("button", name="New chat").click()
    pane = page.get_by_test_id("chat-pane")
    box = pane.locator("textarea")
    expect(box).to_be_enabled(timeout=30_000)
    box.fill(prompt)
    box.press("Enter")
    deadline = time.time() + LLM / 1000
    while time.time() < deadline:
        cards = pane.get_by_test_id("approval-card")
        if cards.count():  # a risky tool waits for a human: approve it as the user would, and keep a record
            card = cards.first
            story.setdefault("approved", []).append(card.inner_text().splitlines()[0])
            card.get_by_role("button", name=re.compile("^Approve")).click()
            page.wait_for_timeout(1500)
            continue
        new = [c for c in json.loads(api_get(f"/projects/{pid}/chats")) if c["id"] not in before]
        messages = json.loads(api_get(f"/chats/{new[0]['id']}"))["messages"] if new else []
        if messages and messages[-1]["role"] == "assistant" and not pane.get_by_test_id("run-status").count():
            page.wait_for_timeout(1500)  # let the pane render the finished turn
            if not pane.get_by_test_id("approval-card").count():
                return pane, json.loads(api_get(f"/chats/{new[0]['id']}"))["messages"][-1]["content"]
        time.sleep(2)
    raise AssertionError("the harness turn did not finish")


def _shot(page, name: str) -> None:
    page.screenshot(path=str(EVIDENCE / f"hs-{name}.png"))


def test_hs00_setup_project(page, tmp_path):
    story["pid"] = _create_project(page, tmp_path, "Story calculator", True)


def test_hs01_hs03_plan_and_scan(page):
    pane, reply = _ask(page, story["pid"], "Add one todo per step, then scan the repository and tell me each finding with file and line.")
    expect(page.get_by_test_id("harness-todo").first).to_be_visible(timeout=30_000)
    expect(pane.get_by_test_id("tool-calls").filter(has_text="scan_repository").first).to_be_visible()
    assert "calc.py" in reply, reply
    _shot(page, "01-03-plan-scan")


def test_hs13_tool_calls_are_audited(page):
    page.goto(f"{UI}/projects/{story['pid']}/observability")
    log = page.get_by_test_id("observability-log")
    expect(log.locator('[data-kind="tool"]').filter(has_text="scan_repository").first).to_be_visible(timeout=30_000)


def test_hs04_run_tests(page):
    pane, reply = _ask(page, story["pid"], "Run the repository's tests with run_tests and give me the exact passed and failed counts.")
    expect(pane.get_by_test_id("tool-calls").filter(has_text="run_tests").first).to_be_visible()
    assert re.search(r"(?i)passed\W+1\b", reply), reply  # one test in the repository, and it passes
    _shot(page, "04-run-tests")


def test_hs05_qe_method_skill(page):
    pane, reply = _ask(page, story["pid"], "Load the planning-tests skill and use it to outline a test plan for calc.py in five bullets.")
    expect(pane.get_by_test_id("tool-calls").filter(has_text="load_skill").first).to_be_visible()
    _shot(page, "05-qe-skill")


def test_hs02_brd_through_ba_workflow(page):
    pane, reply = _ask(page, story["pid"], "Start the ba workflow with this brief: users back up a folder; paths must be validated; every backup is "
                                   "logged. Title it Backup BRD. Do not approve anything.")
    expect(pane.get_by_test_id("tool-calls").filter(has_text="start_workflow").first).to_be_visible()
    runs = json.loads(api_get(f"/projects/{story['pid']}/runs"))
    assert any(r["workflow"] == "ba" for r in runs), runs
    page.goto(f"{UI}/approvals")
    expect(page.get_by_text("Gate 0").first).to_be_visible(timeout=LLM)  # waits for a named human
    _shot(page, "02-brd-gate0")


def test_hs07_qe_run(page):
    pane, reply = _ask(page, story["pid"], "Start the qe workflow for this project. Do not approve anything.")
    expect(pane.get_by_test_id("tool-calls").filter(has_text="start_workflow").first).to_be_visible()
    runs = json.loads(api_get(f"/projects/{story['pid']}/runs"))
    assert any(r["workflow"] == "qe" for r in runs), runs


def test_hs14_no_repository_is_said_plainly(page, tmp_path):
    pid = _create_project(page, tmp_path, "Story empty", False)
    pane, reply = _ask(page, pid, "Run the tests with run_tests and report the result.")
    assert re.search(r"(?i)no repository|inconclusive|not connected", reply), reply


def test_hs06_plugin_command_runs(page):
    pane, reply = _ask(page, story["pid"], "/agentic-qe:qe-start calculator --mode brownfield")
    assert re.search(r"(?i)approve gate 0", reply), reply


def test_hs10_harness_creates_a_skill(page):
    pane, reply = _ask(page, story["pid"], "Create a new skill that checks for hardcoded secrets in Python files. Use your skill creation tool.")
    expect(pane.get_by_test_id("tool-calls").filter(has_text="create_skill").first).to_be_visible()


def test_hs11_subagent_delegation(page):
    pane, reply = _ask(page, story["pid"], "Delegate designing test cases for calc.py to the test-design-architect background agent and report its result.")
    expect(pane.get_by_test_id("tool-calls").filter(has_text="background_agents_start_task").first).to_be_visible()


def test_hs12_admin_grants_page(page):
    page.goto(f"{UI}/settings")
    expect(page.get_by_text(re.compile("plugin grants", re.IGNORECASE))).to_be_visible(timeout=15_000)
