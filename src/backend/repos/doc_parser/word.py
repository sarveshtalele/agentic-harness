"""Word (.docx) parsing."""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Dict, List
from backend.repos.doc_parser.security import DocumentSecurityError, MAX_DOC_SIZE, safe_parse_xml, validate_zip_archive
from backend.repos.doc_parser.word_fallback import _parse_docx_xml_fallback
from backend.repos.doc_parser.markdown import extract_placeholders


def parse_docx_to_markdown(blob: bytes) -> str:
    """Parse a DOCX document into Markdown safely, verifying against XXE, Zip Slip, and Zip Bombs."""
    if len(blob) > MAX_DOC_SIZE:
        raise DocumentSecurityError(f"Document size {len(blob)} exceeds maximum upload limit {MAX_DOC_SIZE} bytes")

    zf = validate_zip_archive(blob)
    with zf:
        for name in zf.namelist():
            if name.endswith((".xml", ".rels")):
                xml_data = zf.read(name)
                safe_parse_xml(xml_data, forbid_dtd=False, forbid_entities=True)

    from docx import Document

    doc = Document(io.BytesIO(blob))
    out: list[str] = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        match = re.match(r"Heading (\d)", paragraph.style.name or "")
        out.append(f"{'#' * int(match.group(1))} {text}" if match else text)

    for table in doc.tables:
        for i, table_row in enumerate(table.rows):
            out.append("| " + " | ".join(c.text.strip() for c in table_row.cells) + " |")
            if i == 0:
                out.append("|" + " --- |" * len(table_row.cells))

    return "\n\n".join(out)


def _parse_docx(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Parse Word (.docx) document extracting paragraphs, headings, tables, and placeholders."""
    try:
        if len(content_bytes) > MAX_DOC_SIZE:
            raise DocumentSecurityError(f"Document size {len(content_bytes)} exceeds maximum limit {MAX_DOC_SIZE}")
        # Validate against Zip Slip, zip bombs, and XXE
        zf = validate_zip_archive(content_bytes)
        with zf:
            for name in zf.namelist():
                if name.endswith((".xml", ".rels")):
                    safe_parse_xml(zf.read(name), forbid_dtd=False, forbid_entities=True)

        from docx import Document
        doc = Document(io.BytesIO(content_bytes))
    except Exception:
        return _parse_docx_xml_fallback(content_bytes, filename)

    sections: List[Dict[str, Any]] = []
    tables_list: List[List[List[str]]] = []
    raw_lines: List[str] = []

    current_heading = ""
    current_level = 1
    current_content: List[str] = []
    title = ""

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        style_name = paragraph.style.name if paragraph.style else ""
        h_match = re.match(r"(?:Heading|heading)\s*(\d)", style_name)

        is_heading = bool(h_match) or style_name.lower() in ("heading 1", "heading 2", "heading 3", "title") or text.startswith("#")

        if is_heading:
            if current_heading or current_content:
                h_name = current_heading or "Overview"
                sections.append({
                    "heading": h_name,
                    "level": current_level,
                    "content": "\n".join(current_content).strip()
                })
                if not title and current_level == 1:
                    title = h_name

            if style_name.lower() == "title":
                current_level = 1
                current_heading = text
            elif h_match:
                current_level = int(h_match.group(1))
                current_heading = text
            elif text.startswith("#"):
                parts = text.split(" ", 1)
                current_level = len(parts[0])
                current_heading = parts[1] if len(parts) > 1 else text
            else:
                current_level = 1
                current_heading = text

            if not title and current_level == 1:
                title = current_heading

            raw_lines.append(f"{'#' * current_level} {current_heading}")
            current_content = []
        else:
            current_content.append(text)
            raw_lines.append(text)

    # Process tables in DOCX
    for table in doc.tables:
        table_rows: List[List[str]] = []
        md_table_lines: List[str] = []
        for i, row in enumerate(table.rows):
            cell_texts = [c.text.strip().replace("\n", " ") for c in row.cells]
            table_rows.append(cell_texts)
            md_table_lines.append("| " + " | ".join(cell_texts) + " |")
            if i == 0:
                md_table_lines.append("|" + " --- |" * len(cell_texts))

        if table_rows:
            tables_list.append(table_rows)
            table_md = "\n".join(md_table_lines)
            current_content.append(table_md)
            raw_lines.append(table_md)

    if current_heading or current_content:
        h_name = current_heading or "Overview"
        sections.append({
            "heading": h_name,
            "level": current_level,
            "content": "\n".join(current_content).strip()
        })
        if not title and current_level == 1:
            title = h_name

    raw_text = "\n\n".join(raw_lines).strip()
    if not title:
        title = sections[0]["heading"] if sections else Path(filename).stem.replace("_", " ").title()

    return {
        "title": title,
        "sections": sections,
        "tables": tables_list,
        "raw_text": raw_text,
        "placeholders": extract_placeholders(raw_text),
        "metadata": {}
    }
