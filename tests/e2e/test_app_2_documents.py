"""End-to-end, part 2: BA workflow, Gherkin and document editing."""

import base64
import io

import re

from pathlib import Path

import pytest
from docx import Document
from playwright.sync_api import expect

from tests.e2e.conftest import state
from tests.e2e.helpers_app import approve_next, shot, UI, wait_card

pytestmark = pytest.mark.e2e


def test_06_ba_workflow_with_template_gherkin_and_gates(page):
    page.goto(f"{state['base']}/ba")
    page.locator('textarea[name="brief"]').fill("Warehouse staff need to reserve and restock inventory. Reservations must never exceed available stock. Quantities must be positive. Managers want an audit of every stock change.")
    page.locator('input[name="doc-title"]').fill("Inventory BRD")
    page.get_by_role("button", name="Generate Requirements Document").click()
    wait_card(page, "Gate 0")
    page.goto(f"{UI}/projects")
    expect(page.get_by_test_id("stat-need-approval")).to_contain_text("1")
    page.get_by_role("navigation", name="Workspace").get_by_role("link", name=re.compile("^Approvals")).click()
    expect(page.get_by_test_id("approvals-summary")).to_contain_text("1 project needs your approval")
    shot(page, "06b-approvals-page")
    approve_next(page, "Gate 0")
    expect(page.get_by_text("Nothing needs your approval")).to_be_visible(timeout=15_000)
    page.goto(f"{state['base']}/runs")
    page.get_by_role("link", name="ba", exact=True).first.click()
    card = wait_card(page, "Gate 1")
    shot(page, "07-ba-gate1")
    links = card.get_by_role("link").evaluate_all("items => items.map(a => a.getAttribute('href'))")
    state["brd"], state["gherkin"] = links
    approve_next(page, "Gate 1")
    expect(page.get_by_test_id("run-status")).to_contain_text("completed", timeout=60_000)


def test_07_gherkin_is_editable_valid_and_downloadable(page):
    page.goto(UI + state["gherkin"])
    expect(page.get_by_test_id("gherkin-status")).to_contain_text("Valid Gherkin")
    expect(page.locator("pre").filter(has_text="Feature:")).to_be_visible()
    page.get_by_role("tab", name="source").click()
    box = page.get_by_label("Document content")
    original = box.input_value()
    assert original.lstrip().startswith(("Feature:", "@"))
    box.fill("this is not gherkin")
    page.get_by_role("button", name="Save version").click()
    expect(page.locator("p[role=alert]")).to_contain_text("Invalid Gherkin")
    box.fill(original + "\n  Scenario: Manager reviews audit\n    Given a stock change\n    When the manager opens the audit\n    Then the change is listed\n")
    page.get_by_label("Change note").fill("Added audit scenario")
    page.get_by_role("button", name="Save version").click()
    expect(page.get_by_test_id("doc-version")).to_have_text("v2")
    shot(page, "08-gherkin-editor")
    with page.expect_download() as info:
        page.get_by_role("link", name=".feature").click()
    assert info.value.suggested_filename.endswith(".feature") and "Manager reviews audit" in Path(info.value.path()).read_text()


def test_07b_gherkin_examples_are_an_editable_table(page):
    page.goto(UI + state["gherkin"])
    page.get_by_role("tab", name="source").click()
    box = page.get_by_label("Document content")
    box.fill(box.input_value() + "\n  Scenario Outline: Reserve quantities\n    Given stock of <stock>\n    When I reserve <wanted>\n    Then the result is <left>\n\n    Examples:\n      | stock | wanted | left |\n      | 5 | 2 | 3 |\n")
    page.get_by_role("tab", name="document").click()
    grid = page.get_by_test_id("table-block").last
    grid.get_by_label("row 2, column 1").fill("9")
    grid.get_by_role("button", name="Add row").click()
    grid.get_by_label("row 3, column 1").fill("4")
    grid.get_by_label("row 3, column 2").fill("1")
    grid.get_by_label("row 3, column 3").fill("3")
    page.get_by_role("button", name="Save version").click()
    expect(page.get_by_text("Saved as a new version")).to_be_visible(timeout=15_000)
    expect(page.get_by_test_id("gherkin-status")).to_contain_text("Valid Gherkin")
    page.get_by_role("tab", name="source").click()
    assert re.search(r"\| 9 +\| 2 +\| 3 +\|\n +\| 4 +\| 1 +\| 3 +\|", page.get_by_label("Document content").input_value())
    shot(page, "08c-gherkin-table")


def test_07c_edit_document_in_place_with_tables_and_images(page):
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAEBgIApD5fRAAAAABJRU5ErkJggg==")
    page.goto(UI + state["brd"])
    bar = page.get_by_test_id("save-bar")
    expect(bar.get_by_role("button", name="Save version")).to_be_disabled()
    block = page.get_by_test_id("text-block").nth(1)
    block.click()
    editor = page.get_by_label("Edit this block")
    editor.fill(editor.input_value() + " Added in place.")
    expect(page.get_by_test_id("live-preview")).to_contain_text("Added in place.")
    editor.blur()
    tools = page.get_by_test_id("doc-toolbar")
    tools.get_by_role("button", name="Add table").click()
    grid = page.get_by_test_id("table-block").last
    grid.get_by_label("row 1, column 1").fill("Owner")
    grid.get_by_label("row 2, column 1").fill("Priya | Ops")
    grid.get_by_role("button", name="Add column").click()
    grid.get_by_label("row 2, column 3").fill("Reviewed")
    tools.get_by_label("Add image").set_input_files({"name": "diagram.png", "mimeType": "image/png", "buffer": png})
    image = page.get_by_test_id("document-page").locator('img[alt="diagram.png"]')
    expect(image).to_be_visible(timeout=15_000)
    assert image.evaluate("i => i.naturalWidth") == 1
    page.get_by_label("Change note").fill("Edited in place")
    bar.get_by_role("button", name="Save version").click()
    expect(page.get_by_text("Saved as a new version")).to_be_visible(timeout=15_000)
    shot(page, "08d-document-edited-in-place")
    page.reload()
    assert page.get_by_test_id("table-block").last.get_by_label("row 2, column 1").input_value() == "Priya | Ops"
    expect(page.get_by_test_id("document-page").locator('img[alt="diagram.png"]')).to_be_visible()
    page.get_by_role("tab", name="source").click()
    text = page.get_by_label("Document content").input_value()
    assert "Added in place." in text and r"Priya \| Ops" in text and "](/api/documents/" in text
    page.get_by_label("Document content").fill(text + "\n\nTyped in source.\n")
    expect(page.get_by_test_id("source-preview")).to_contain_text("Typed in source.")
    page.get_by_role("button", name="Discard changes").click()
    expect(page.get_by_test_id("source-preview")).not_to_contain_text("Typed in source.")
    with page.expect_download() as info:
        page.get_by_role("link", name=".docx").click()
    assert len(Document(io.BytesIO(Path(info.value.path()).read_bytes())).inline_shapes) == 1


def test_08_document_edit_history_restore_and_exports(page):
    page.goto(UI + state["brd"])
    expect(page.locator(".prose-atlas h2").first).to_be_visible()  # opens formatted, not as raw markdown
    shot(page, "08b-document-formatted")
    page.get_by_role("tab", name="source").click()
    box = page.get_by_label("Document content")
    original = box.input_value()
    for heading in ("Executive Summary", "Functional Requirements", "Open Questions"):
        assert heading in original, "template headings are kept"
    box.fill(original + "\n\nEdited by a human reviewer.\n")
    page.get_by_role("button", name="Save version").click()
    version = page.get_by_test_id("doc-version")
    expect(version).not_to_have_text(re.compile(r"v1$"))
    edited = int(version.inner_text()[1:])
    with page.expect_download() as info:
        page.get_by_role("link", name=".docx").click()
    text = "\n".join(p.text for p in Document(io.BytesIO(Path(info.value.path()).read_bytes())).paragraphs)
    assert "Edited by a human reviewer." in text
    with page.expect_download() as info:
        page.get_by_role("link", name=".md").click()
    assert "Edited by a human reviewer." in Path(info.value.path()).read_text()
    page.get_by_role("tab", name=re.compile("history")).click()
    page.get_by_role("button", name=re.compile("Diff with")).first.click()
    expect(page.locator("pre")).to_contain_text("Edited by a human reviewer.")
    shot(page, "09-document-history")
    page.get_by_role("button", name="Restore").first.click()
    expect(version).to_have_text(f"v{edited + 1}")
