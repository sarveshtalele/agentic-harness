"""Red and blue team: XML and zip attacks and upload limits."""

from __future__ import annotations

import io
import zipfile

import pytest

from backend.core import files

from backend.repos import doc_parser, ingest

pytest_plugins = ["tests.helpers_api"]


# ==============================================================================
# 1. XXE ATTACK MITIGATION ON DOCUMENT PARSING
# ==============================================================================

def test_xxe_external_entity_injection_blocked():
    """Verify that safe_parse_xml blocks XXE attacks targeting local files."""
    xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE test [
      <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <test>
      <data>&xxe;</data>
    </test>"""

    with pytest.raises(doc_parser.XXEError):
        doc_parser.safe_parse_xml(xxe_payload)


def test_xxe_billion_laughs_expansion_blocked():
    """Verify that recursive XML entity expansion (Billion Laughs DoS) is neutralized."""
    billion_laughs_payload = """<?xml version="1.0"?>
    <!DOCTYPE lolz [
     <!ENTITY lol "lol">
     <!ELEMENT lolz (#PCDATA)>
     <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
     <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
     <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
    ]>
    <lolz>&lol3;</lolz>"""

    with pytest.raises(doc_parser.XXEError):
        doc_parser.safe_parse_xml(billion_laughs_payload)


def test_docx_xxe_payload_detected_and_rejected():
    """Verify that a DOCX containing embedded XXE payload is rejected upon parsing."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <!DOCTYPE w:document [
              <!ENTITY xxe SYSTEM "file:///etc/passwd">
            ]>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body>
            </w:document>""",
        )
        z.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
              <Default Extension="xml" ContentType="application/xml"/>
            </Types>""",
        )

    docx_bytes = bio.getvalue()

    with pytest.raises(doc_parser.XXEError):
        doc_parser.parse_docx_to_markdown(docx_bytes)

    # Also verify via core files.extract_text entry point
    with pytest.raises(doc_parser.XXEError):
        files.extract_text("malicious.docx", docx_bytes)


def test_valid_docx_parses_successfully():
    """Verify that benign DOCX documents continue to parse accurately into Markdown."""
    blob = files.markdown_to_docx("Security Specs", "## Hardening\n\n- Zero Trust\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    markdown = doc_parser.parse_docx_to_markdown(blob)
    assert "## Hardening" in markdown
    assert "Zero Trust" in markdown
    assert "| 1 | 2 |" in markdown


# ==============================================================================
# 2. ZIP SLIP & DIRECTORY TRAVERSAL MITIGATION
# ==============================================================================

def test_zip_slip_traversal_refused_in_doc_parser(tmp_path):
    """Verify that Zip Slip directory traversal payloads are blocked during archive validation."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("../../sensitive_file.txt", "MALICIOUS PAYLOAD")
    zip_bytes = bio.getvalue()

    with pytest.raises(doc_parser.ZipSlipError):
        doc_parser.validate_zip_archive(zip_bytes)

    dest_dir = tmp_path / "extracted"
    with pytest.raises(doc_parser.ZipSlipError):
        doc_parser.safe_extract_zip(zip_bytes, dest_dir)

    # Ensure no file was written outside or inside target
    assert not (tmp_path / "sensitive_file.txt").exists()


def test_zip_slip_traversal_refused_in_ingest(tmp_path):
    """Verify that repo ingestion safe_extract refuses Zip Slip paths."""
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../../../evil.sh", "echo evil")

    target = tmp_path / "workspace"
    target.mkdir()

    with pytest.raises(ingest.IngestError) as exc:
        ingest.safe_extract(archive, target)
    assert "escapes the workspace" in str(exc.value)


def test_zip_bomb_large_expansion_rejected():
    """Verify that archives with suspicious compression ratios or excessive sizes are rejected."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        # Create an entry with high compression ratio (sparse data)
        z.writestr("huge.txt", "A" * (2 * 1024 * 1024))
    zip_bytes = bio.getvalue()

    # Artificially low uncompressed limit to test rejection
    with pytest.raises(doc_parser.ZipBombError):
        doc_parser.validate_zip_archive(zip_bytes, max_uncompressed=1024 * 1024)


def test_document_max_upload_size_enforced():
    """Verify that oversized documents exceeding MAX_DOC_SIZE (20MB) are rejected."""
    oversized = b"0" * (doc_parser.MAX_DOC_SIZE + 1024)
    with pytest.raises(doc_parser.DocumentSecurityError):
        doc_parser.parse_docx_to_markdown(oversized)
