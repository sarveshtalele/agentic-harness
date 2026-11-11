"""End-to-end, part 1: projects, repository, clone, rename and settings."""

import re

import zipfile

import pytest

from playwright.sync_api import expect

from tests.e2e.conftest import state
from tests.e2e.helpers_app import shot, UI

pytestmark = pytest.mark.e2e


API = "http://127.0.0.1:8010"


APP_ZIP = {
    "shop-main/inventory.py": '"""Stock keeping."""\n\n\ndef reserve(stock: int, quantity: int) -> int:\n    """Return stock left after reserving. Quantity must be positive and not exceed stock."""\n    if quantity <= 0:\n        raise ValueError("quantity must be positive")\n    if quantity > stock:\n        raise ValueError("not enough stock")\n    return stock - quantity\n\n\ndef restock(stock: int, quantity: int) -> int:\n    return stock - quantity\n',
    "shop-main/admin.py": 'import subprocess\n\n\ndef backup(path):\n    return subprocess.call("tar -czf backup.tgz " + path, shell=True)\n',
    "shop-main/tests/test_inventory.py": 'from inventory import reserve\n\n\ndef test_reserve():\n    assert reserve(5, 2) == 3\n',
    "shop-main/conftest.py": "",
    "shop-main/requirements.txt": "pytest\n",
}


def test_01_projects_page_replaces_the_dropdown(page):
    page.goto(UI)
    expect(page.get_by_role("heading", name="Projects")).to_be_visible()
    expect(page.get_by_text("No projects yet").or_(page.get_by_role("article").first)).to_be_visible()
    assert page.locator("header select").count() == 0, "no project dropdown"
    shot(page, "01-projects-empty")


def test_02_create_project_with_zip_upload(page, tmp_path):
    archive = tmp_path / "shop.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, body in APP_ZIP.items():
            bundle.writestr(name, body)
    page.get_by_role("button", name="New project").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Name").fill("Shop Inventory")
    dialog.get_by_label("Description").fill("Inventory service for the online shop")
    dialog.locator('input[type="file"]').set_input_files(archive)
    dialog.get_by_role("button", name=re.compile("Create project|Cloning")).click()
    page.wait_for_url(re.compile(r"/projects/prj_"), timeout=60_000)
    state["base"] = page.url
    state["id"] = page.url.rsplit("/", 1)[-1]
    expect(page.get_by_text("Recommended Action")).to_be_visible()  # the next-step banner
    expect(page.get_by_text("shop.zip")).to_be_visible()
    shot(page, "02-project-overview")


def test_03_repository_scan_shows_real_facts(page):
    page.goto(f"{state['base']}/repository")
    details = page.get_by_test_id("repo-details")
    expect(details).to_contain_text("pytest")
    expect(details).to_contain_text("Python")
    details.get_by_role("button", name="inventory.py", exact=True).click()
    expect(details.locator("pre")).to_contain_text("def reserve")
    shot(page, "03-repository-zip")


def test_04_real_public_github_clone(page):
    page.goto(UI)
    page.get_by_role("button", name="New project").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Name").fill("Agentic QE plugin")
    dialog.get_by_label("Git URL").fill("https://github.com/sarveshtalele/agentic-qe")
    dialog.get_by_role("button", name=re.compile("Create project|Cloning")).click()
    page.wait_for_url(re.compile(r"/projects/prj_"), timeout=240_000)
    page.goto(f"{page.url}/repository")
    details = page.get_by_test_id("repo-details")
    expect(details).to_contain_text("TypeScript", timeout=30_000)
    expect(details).to_contain_text("Recent commits")
    shot(page, "04-repository-github")
    page.goto(UI)
    expect(page.get_by_test_id("project-card")).to_have_count(2)
    shot(page, "05-projects-list")


def test_04b_rename_project_docs_and_brand(page):
    page.goto(UI)
    expect(page.get_by_text("Governed requirements, code changes, and test engineering for BAs and developers.")).to_have_count(0)
    page.get_by_role("button", name="Rename Agentic QE plugin").click()  # opens the in-app rename modal
    modal = page.get_by_role("dialog")
    modal.get_by_placeholder("Enter new project name").fill("Agentic QE repository")
    modal.get_by_role("button", name="Save Name").click()
    expect(page.get_by_role("heading", name="Agentic QE repository")).to_be_visible()
    page.get_by_role("link", name="Documentation").click()
    expect(page).to_have_url(re.compile("/docs/introduction"))
    expect(page.get_by_role("heading", level=1, name="Introduction")).to_be_visible()
    shot(page, "05b-documentation")
    page.get_by_role("navigation", name="Documentation").get_by_role("link", name="QE Studio").click()
    expect(page.get_by_role("heading", level=1, name="QE Studio")).to_be_visible()
    expect(page.get_by_test_id("docs-toc")).to_contain_text("The gates")
    page.get_by_role("navigation", name="Previous and next pages").get_by_role("link", name=re.compile("Copilot")).click()
    expect(page.get_by_role("heading", level=1, name="Copilot")).to_be_visible()
    page.get_by_label("Search documentation").fill("traceback")
    expect(page.get_by_test_id("docs-search-results")).to_contain_text("Bug Scan")
    page.get_by_role("link", name="Open app").click()
    expect(page.get_by_test_id("stat-projects")).to_be_visible()
    page.get_by_test_id("card-bugs").first.click()
    expect(page.get_by_role("heading", name="Bug Scan")).to_be_visible()
    expect(page.locator('ol[aria-label="Quality gates"]')).to_have_count(0)
    page.goto(UI)
    page.get_by_test_id("stat-findings").click()
    expect(page.get_by_role("heading", name="Open findings")).to_be_visible()
    page.goto(UI)
    page.get_by_test_id("stat-documents").click()
    expect(page.get_by_role("heading", level=1, name="Documents")).to_be_visible()


def test_05_settings_connection_is_real(page):
    page.goto(f"{UI}/settings")
    page.get_by_role("button", name="Test connection").click()
    expect(page.get_by_test_id("llm-ok")).to_contain_text("Connected to", timeout=90_000)
    assert "sk-" not in page.content()
    shot(page, "06-settings")
