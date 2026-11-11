"""Document versions, Gherkin, prompts, templates and uploads."""

import io

import psycopg

import pytest
from docx import Document

from backend.core import documents, files, gherkin, prompts
from backend.db import db, now
from tests.helpers_core import project  # noqa: F401 - fixtures


def test_document_versions_are_immutable_and_restorable(project):
    doc = documents.create(project, "brd", "Doc", "one", "ann")
    documents.save_version(doc["id"], "two", "bob", note="edit")
    assert documents.save_version(doc["id"], "two", "bob")["version"] == 2  # same content, no new version
    assert [v["version"] for v in documents.versions(doc["id"])] == [2, 1]
    assert documents.get(doc["id"], 1)["content"] == "one"
    restored = documents.restore(doc["id"], 1, "ann")
    assert restored["version"] == 3 and restored["content"] == "one"
    assert "-two" in documents.diff(doc["id"], 2, 3)


def test_document_edit_resets_approval(project):
    doc = documents.create(project, "brd", "Doc", "one", "ann")
    assert documents.set_status(doc["id"], "approved", "ann")["status"] == "approved"
    assert documents.save_version(doc["id"], "two", "bob")["status"] == "draft"


VALID_GHERKIN = "Feature: Login\n\n  Scenario: Good login\n    Given a user\n    When they log in\n    Then they see the home page\n"


def test_document_writes_version_files(project):
    from backend.config import project_dir

    doc = documents.create(project, "gherkin", "F", VALID_GHERKIN, "ann")
    assert (project_dir(project) / "documents" / "gherkin" / doc["id"] / "v0001.feature").read_text() == VALID_GHERKIN


def test_document_content_is_redacted(project):
    doc = documents.create(project, "brd", "Doc", "key sk-" + "c" * 30, "ann")
    assert "c" * 30 not in doc["content"]


def test_gherkin_valid_counts():
    result = gherkin.validate(VALID_GHERKIN)
    assert result["valid"] and result["scenarios"] == 1 and result["steps"] == 3


@pytest.mark.parametrize("text", ["not gherkin at all", "Feature: Empty\n", "Feature: X\n  Scenario: no steps\n"])
def test_gherkin_invalid(text):
    assert not gherkin.validate(text)["valid"]


def test_invalid_gherkin_save_refused(project):
    doc = documents.create(project, "gherkin", "F", VALID_GHERKIN, "ann")
    with pytest.raises(documents.DocumentError):
        documents.save_version(doc["id"], "broken", "ann")


def test_prompt_versions(project):
    prompts.seed()
    before = prompts.active("project-copilot")
    created = prompts.add_version("project-copilot", "Be helpful and cite every claim.", "tweak", "ann")
    assert created["version"] == before["version"] + 1 and prompts.active("project-copilot")["body"].startswith("Be helpful")
    assert prompts.activate("project-copilot", before["version"])["sha256"] == before["sha256"]
    assert len(prompts.history("project-copilot")) >= 2
    prompts.seed()  # reseeding unchanged content adds nothing
    assert prompts.active("project-copilot")["version"] == before["version"]


def test_prompt_history_is_immutable_at_primary_key():
    prompts.seed()
    current = prompts.active("project-copilot")
    with pytest.raises(psycopg.errors.IntegrityError), db() as con:
        con.execute("INSERT INTO prompts VALUES (?,?,?,?,?,?,1,?)", ("project-copilot", current["version"], "x", "y", "", "", now()))


def test_template_headings_and_missing():
    body = "# T\n\n## Scope\ntext\n\n## Risks\n"
    assert files.template_headings(body) == ["Scope", "Risks"]
    assert files.missing_headings(body, "## Scope\nok") == ["Risks"]


def test_docx_export_and_import_keep_structure():
    blob = files.markdown_to_docx("Title", "## Scope\n\n- item **bold**\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    doc = Document(io.BytesIO(blob))
    assert any(p.text == "Scope" and p.style.name.startswith("Heading") for p in doc.paragraphs)
    assert doc.tables[0].rows[1].cells[1].text == "2"
    assert "## Scope" in files.extract_text("x.docx", blob)


def test_xlsx_and_pptx_sources_extract():
    from openpyxl import Workbook
    from pptx import Presentation

    book = Workbook()
    book.active.append(["Rule", "Limit"])
    buffer = io.BytesIO()
    book.save(buffer)
    assert "Rule | Limit" in files.extract_text("x.xlsx", buffer.getvalue())
    deck = Presentation()
    deck.slides.add_slide(deck.slide_layouts[0]).shapes.title.text = "Launch plan"
    buffer = io.BytesIO()
    deck.save(buffer)
    assert "Launch plan" in files.extract_text("x.pptx", buffer.getvalue())


def test_unsupported_upload_rejected():
    with pytest.raises(files.UnsupportedFile):
        files.extract_text("x.exe", b"MZ")
