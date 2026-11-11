"""E2E: Skill Creator Studio, US-51 (instructions skill from requirements) and US-53 (evaluate on the model).

The model is real, so the oracles are facts the server checks: the plan hash on screen equals the stored one, the MAF load
check passed, version 1 is published, and the metrics carry n. Skill Studio writes skills: run with ATLAS_SKILLS_DIR
pointing at a scratch copy of skills/.
"""
from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import EVIDENCE, api_get

pytestmark = pytest.mark.e2e
UI = "http://127.0.0.1:3010"
LLM = 420_000
story: dict = {}
REQUIREMENTS = (
    "Python code must never call subprocess with shell=True. Commands must be built as an argument list, never by joining strings. "
    "Every finding is reported with the file name and the line number."
)


def _shot(page, name: str) -> None:
    page.screenshot(path=str(EVIDENCE / f"{name}.png"), full_page=True)


def test_us51_instructions_skill_from_requirements(page):
    created = page.request.post(f"{UI}/api/projects", data={"name": "Studio story", "description": "Skill Studio checks"})
    assert created.ok, created.text()
    page.goto(f"{UI}/skills/studio")
    page.get_by_test_id("studio-project").select_option(created.json()["id"])
    page.get_by_test_id("studio-source-text").click()
    page.get_by_test_id("studio-source-input").fill(REQUIREMENTS)
    page.get_by_test_id("studio-kind-instructions").click()
    page.get_by_test_id("studio-request").fill("Create a skill that reviews Python code against these requirements.")
    _shot(page, "us-51-1-source-kind-request")
    page.get_by_test_id("studio-draft-plan").click()
    expect(page.get_by_test_id("studio-busy")).to_contain_text("Drafting the plan with the model")
    expect(page.get_by_test_id("studio-plan-name")).not_to_have_value("", timeout=LLM)
    expect(page.get_by_test_id("studio-task-0")).to_be_visible()
    story["plan_id"] = re.search(r"plan=(spl_\w+)", page.url).group(1)
    story["name"] = page.get_by_test_id("studio-plan-name").input_value()
    _shot(page, "us-51-2-plan-draft")
    page.get_by_test_id("studio-approve").click()
    page.get_by_role("button", name="Approve plan").last.click()
    expect(page.get_by_test_id("studio-plan-hash")).to_be_visible(timeout=30_000)
    stored = json.loads(api_get(f"/skill-studio/plans/{story['plan_id']}"))
    assert stored["status"] == "approved" and stored["plan_sha256"]
    assert page.get_by_test_id("studio-plan-hash").inner_text() == stored["plan_sha256"][:12]
    page.get_by_test_id("studio-generate").click()
    expect(page.get_by_test_id("studio-check-MAF loads it")).to_have_attribute("data-passed", "true", timeout=LLM)
    expect(page.get_by_test_id("studio-file-SKILL.md")).to_be_visible()
    _shot(page, "us-51-3-generated")
    page.get_by_test_id("studio-publish").click()
    expect(page.get_by_test_id("studio-version")).to_have_text("1", timeout=60_000)
    versions = json.loads(api_get(f"/skill-studio/skills/{story['name']}/versions"))["versions"]
    assert [v["version"] for v in versions] == [1]
    _shot(page, "us-51-4-published")


def test_us53_evaluation_reports_measured_results(page):
    page.goto(f"{UI}/skills/studio?plan={story['plan_id']}")
    page.get_by_test_id("studio-evaluate").click()
    expect(page.get_by_test_id("studio-busy")).to_contain_text("Evaluating on the model")
    metrics = page.get_by_test_id("studio-eval-metrics")
    expect(metrics).to_be_visible(timeout=LLM)
    expect(metrics).to_contain_text(re.compile(r"n=\d+"))
    expect(metrics).to_contain_text("judge deterministic-assertions")
    _shot(page, "us-53-1-evaluation")
    stored = json.loads(api_get(f"/skill-studio/plans/{story['plan_id']}"))
    assert metrics.inner_text().count(f"n={len(stored['plan']['eval_cases'])}") == 3
