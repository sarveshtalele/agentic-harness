"""End-to-end, part 4: governance, prompts, agents, users, observability and theme."""

import base64

import os
import re
import time

import pytest

from playwright.sync_api import expect

from tests.e2e.conftest import state
from tests.e2e.helpers_app import EVIDENCE, shot, UI

pytestmark = pytest.mark.e2e


def test_14_governance_ledger_and_metrics_are_real(page):
    page.goto(f"{state['base']}/governance")
    expect(page.get_by_test_id("ledger-valid")).to_contain_text("Chain valid")
    expect(page.get_by_text("Administrator").first).to_be_visible()  # the ledger names the signed-in account
    shot(page, "19-governance")
    page.goto(f"{state['base']}/runs")
    expect(page.get_by_role("heading", name="Agent calls")).to_be_visible()
    expect(page.get_by_text("business-analyst").first).to_be_visible()
    expect(page.get_by_role("cell", name="Avg ms").or_(page.get_by_text("Avg ms")).first).to_be_visible()
    shot(page, "20-metrics")


def test_15_prompt_version_and_real_eval(page):
    page.goto(f"{state['base']}/prompts")
    page.get_by_role("button", name=re.compile("business.analyst", re.I)).click()
    page.get_by_role("button", name="Run with the real model").click()
    expect(page.get_by_text(re.compile(r"\d/6 passed"))).to_be_visible(timeout=180_000)
    box = page.get_by_label("Prompt body")
    box.fill(box.input_value() + "\nPrefer short scenario names.")
    page.get_by_label("Reason for change").fill("Shorter names")
    page.get_by_role("button", name="Save new version").click()
    expect(page.get_by_text("active v2")).to_be_visible()
    page.get_by_role("button", name="Activate").click()
    expect(page.get_by_text("active v1")).to_be_visible()
    shot(page, "21-prompts")


def test_15b_agents_page_evals_kill_switch_and_real_numbers(page):
    page.goto(f"{UI}/agents")
    cards = page.get_by_test_id("agent-card")
    expect(cards).to_have_count(14)  # the plugin's 8 agents, 5 platform agents (incl. bug-fix-reviewer), and the MAF project harness (P2)
    expect(page.get_by_test_id("risk-legend")).to_contain_text("can change code")
    page.get_by_role("button", name="Run all evaluations").click()
    expect(page.get_by_role("button", name="Running evaluations")).to_be_visible()
    expect(page.get_by_role("button", name="Run all evaluations")).to_be_enabled(timeout=420_000)
    expect(page.get_by_test_id("agent-cards")).not_to_contain_text("evals not run")
    state["eval_summary"] = page.get_by_test_id("agent-stats").inner_text()
    (EVIDENCE / "eval-summary.txt").write_text(page.get_by_test_id("agent-cards").inner_text())
    shot(page, "21b-agents")
    cards.filter(has_text=re.compile("confidence.reviewer", re.I)).click()
    expect(page).to_have_url(re.compile("/agents/confidence-reviewer"))
    detail = page.get_by_test_id("agent-detail")
    expect(page.get_by_test_id("agent-details-table")).to_contain_text("Tokens per model call")
    expect(detail).to_contain_text("scores weak doc low")
    detail.get_by_label("Reason").fill("Temporarily off for the test")
    detail.get_by_role("button", name="Disable agent").click()
    expect(page.get_by_test_id("agent-details-table")).to_contain_text("Disabled")
    shot(page, "21c-agent-disabled")
    page.get_by_test_id("agent-detail").get_by_role("button", name="Enable agent").click()
    expect(page.get_by_test_id("agent-detail").get_by_role("button", name="Disable agent")).to_be_visible()


def test_15e_admin_creates_user_who_sees_only_their_own_work(page):
    name, secret = f"qa.user{int(time.time())}", base64.urlsafe_b64encode(os.urandom(15)).decode()
    page.goto(f"{UI}/users")
    page.locator('input[name="new-username"]').fill(name)
    page.locator('input[name="new-password"]').fill(secret)
    page.get_by_label("Allow deepseek-v4-flash-global").check()  # the configured model is in the list; a user can run only ticked models
    page.locator('input[name="new-tokens"]').fill("50000")
    page.locator('input[name="new-until"]').fill("2099-01-31")
    page.get_by_role("button", name="Create user").click()
    card = page.get_by_test_id("user-card").filter(has_text="50,000")
    expect(card).to_be_visible(timeout=15_000)
    assert secret not in page.content()
    shot(page, "22b-users")
    guest = page.context.browser.new_context(viewport={"width": 1440, "height": 900})
    tab = guest.new_page()
    tab.goto(f"{UI}/projects")
    expect(tab).to_have_url(re.compile("/login"), timeout=15_000)
    shot(tab, "22a-login")
    tab.get_by_label("Username").fill(name)
    tab.get_by_label("Password").fill("not-the-right-one")
    tab.get_by_role("button", name="Sign in").click()
    expect(tab.locator("p[role=alert]")).to_contain_text("not correct")
    tab.get_by_label("Password").fill(secret)
    tab.get_by_role("button", name="Sign in").click()
    expect(tab.get_by_test_id("signed-in-user")).to_contain_text(name, timeout=30_000)
    expect(tab.get_by_text("No projects yet")).to_be_visible(timeout=15_000)
    expect(tab.get_by_role("link", name="Users")).to_have_count(0)
    tab.goto(f"{state['base']}")
    expect(tab.get_by_text("Not found")).to_be_visible(timeout=15_000)
    guest.close()
    log = (EVIDENCE / "server.log").read_text(errors="replace")
    assert secret not in log and name not in log and os.environ["ATLAS_ADMIN_PASSWORD"] not in log


def test_15c_observability_across_projects_and_per_run(page):
    page.goto(f"{UI}/observability")
    expect(page.get_by_role("heading", name="Observability")).to_be_visible()
    log = page.get_by_test_id("observability-log")
    expect(log).to_be_visible(timeout=15_000)
    expect(page.get_by_test_id("ledger-integrity")).to_contain_text("Audit ledger verified")
    expect(page.get_by_test_id("mcp-note")).to_contain_text("no MCP server")
    page.get_by_role("tab", name=re.compile("^Skills")).click()
    expect(log.locator('[data-kind="skill"]').first).to_be_visible(timeout=10_000)
    expect(log.locator('[data-testid="log-entry"]:not([data-kind="skill"])')).to_have_count(0, timeout=10_000)
    expect(log).to_contain_text("planning-tests")
    page.get_by_role("tab", name=re.compile("^Agents")).click()
    expect(log.locator('[data-kind="agent"]').first).to_be_visible(timeout=10_000)
    log.locator('[data-kind="agent"] button').first.click()
    expect(log).to_contain_text("prompt_ref")
    shot(page, "21d-observability-all")
    page.get_by_role("tab", name=re.compile("^Tools")).click()
    expect(log.locator('[data-kind="tool"]').first).to_be_visible(timeout=10_000)
    page.goto(f"{state['base']}/observability")
    first_run = page.get_by_label("Run").locator("option").nth(1).get_attribute("value")
    page.get_by_label("Run").select_option(first_run)
    expect(page.get_by_test_id("observability-log")).to_be_visible(timeout=10_000)
    shot(page, "21e-observability-run")
    with page.expect_download() as download:
        page.get_by_role("link", name="Download JSON").click()
    assert download.value.suggested_filename == "agentic-qe-observability.json"


def test_16_light_theme_and_no_page_errors(page):
    page.goto(state["base"])
    page.get_by_role("button", name="Switch to light mode").click()
    shot(page, "22-light-theme")
    page.get_by_role("button", name="Switch to dark mode").click()
    assert state["console_errors"] == [], state["console_errors"]
