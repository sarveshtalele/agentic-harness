"""The stable cloud build's feature walk (docs/STABLE_BUILD_PLAN.md, Part C): every page of every feature except the
harness opens, renders its heading, raises no script error and links nowhere near the removed harness or desktop app.
A full-page screenshot of each is kept in docs/evidence/stable-build/ as evidence. No model is needed: this proves the
features are present and working as pages; the real-model end-to-end runs prove the flows."""
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import ROOT
from tests.e2e.test_smoke import ADMIN, UI, app, browser, sign_in  # noqa: F401 - fixtures

pytestmark = pytest.mark.smoke
EVIDENCE = ROOT / "docs" / "evidence" / "stable-build"
TOP = ["/home", "/projects", "/approvals", "/agents", "/capabilities", "/documents", "/findings", "/mcp", "/observability",
       "/skills", "/skills/studio", "/templates", "/traces", "/usage", "/users", "/settings", "/account", "/docs"]
IN_PROJECT = ["", "/repository", "/ba", "/qe", "/documents", "/chat", "/bugs", "/feature", "/runs", "/approvals",
              "/governance", "/observability", "/prompts"]
GONE = re.compile(r"/harness|desktop-downloads|download-macos|download-windows")


def _check(tab, path: str, errors: list, name: str) -> None:
    tab.goto(f"{UI}{path}")
    main = tab.locator("main, article").first  # the docs section has its own frame with an article
    expect(main).to_be_visible(timeout=30_000)
    tab.wait_for_load_state("networkidle")
    assert main.inner_text().strip(), f"{path} rendered an empty page"
    html = tab.content()
    assert not GONE.search(html), f"{path} still links the harness or the desktop app"
    assert "Application error" not in html and "Unhandled Runtime Error" not in html, path
    tab.screenshot(path=str(EVIDENCE / f"{name}.png"), full_page=True)
    assert not errors, f"{path}: {errors}"


def test_every_feature_page_except_the_harness_works(browser):  # noqa: F811
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for old in EVIDENCE.glob("*.png"):  # one walk per folder: this run's screenshots replace the last run's
        old.unlink()
    tab = sign_in(browser, ADMIN)
    expect(tab.get_by_role("heading", name="Home")).to_be_visible(timeout=30_000)
    errors: list = []
    tab.on("pageerror", lambda e: errors.append(str(e)))
    nav = tab.get_by_role("navigation", name="Workspace")
    for label in ("Home", "Projects", "Approvals"):
        expect(nav.get_by_role("link", name=label).first).to_be_visible()
    expect(nav.get_by_role("link", name="Harness")).to_have_count(0)
    for path in TOP:
        _check(tab, path, errors, path.strip("/").replace("/", "_"))
    project = tab.request.post(f"{UI}/api/projects", data={"name": "Feature walk", "description": "Stable build evidence"})
    assert project.ok, project.text()
    pid = project.json()["id"]
    for sub in IN_PROJECT:
        _check(tab, f"/projects/{pid}{sub}", errors, "project" + sub.replace("/", "_"))
    assert len(list(EVIDENCE.glob("*.png"))) >= len(TOP) + len(IN_PROJECT)
