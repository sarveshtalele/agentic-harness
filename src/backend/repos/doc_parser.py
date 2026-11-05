"""Secure and intelligent document & template parser.

Supports Markdown (.md), Plain Text (.txt), Word (.docx), and PDF (.pdf).
Extracts document structure, headings, sections, tables, code blocks, frontmatter,
and template placeholders (e.g. {{project_name}}, [System Overview], {{scope}}).
Includes defense against XXE, Zip Slip, decompression bombs, and XML entity expansion.
"""
from __future__ import annotations

import io
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List

try:
    import defusedxml.ElementTree as defused_ET
    import defusedxml.common as defused_common
    HAVE_DEFUSEDXML = True
except ImportError:
    HAVE_DEFUSEDXML = False
    defused_ET = None
    defused_common = None

import xml.etree.ElementTree as ET

# Maximum upload size for documents: 20 MB
MAX_DOC_SIZE = 20 * 1024 * 1024
# Maximum uncompressed size for zip/archive payloads: 100 MB
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024
# Maximum compression ratio to prevent zip bombs
MAX_COMPRESSION_RATIO = 100
# Maximum file count in an archive
MAX_ZIP_ENTRIES = 5000


class DocumentSecurityError(ValueError):
    """Base error for document security violations."""
    pass


class XXEError(DocumentSecurityError):
    """Raised when XXE, DTD or forbidden entity expansions are detected."""
    pass


class ZipSlipError(DocumentSecurityError):
    """Raised when an archive entry attempts directory traversal / zip slip."""
    pass


class ZipBombError(DocumentSecurityError):
    """Raised when an archive entry size or compression ratio exceeds safe limits."""
    pass


def safe_parse_xml(content: str | bytes, forbid_dtd: bool = True, forbid_entities: bool = True) -> ET.Element:
    """Safely parse XML content, preventing XXE injection and Billion Laughs DoS."""
    raw_str = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content

    # Heuristic check for explicit DTD / ENTITY / SYSTEM attacks
    if forbid_dtd and re.search(r"<!DOCTYPE\b", raw_str, re.IGNORECASE):
        if re.search(r"<!ENTITY\b", raw_str, re.IGNORECASE):
            raise XXEError("XML contains forbidden entity declarations (XXE / Entity expansion)")
        if re.search(r"\bSYSTEM\b|\bPUBLIC\b", raw_str, re.IGNORECASE):
            raise XXEError("XML contains external entity or DTD reference (XXE)")

    if forbid_entities and re.search(r"<!ENTITY\b", raw_str, re.IGNORECASE):
        raise XXEError("XML contains forbidden entity declarations")

    if HAVE_DEFUSEDXML:
        try:
            return defused_ET.fromstring(
                content,
                forbid_dtd=forbid_dtd,
                forbid_entities=forbid_entities,
                forbid_external=True,
            )
        except (defused_common.DefusedXmlException, defused_common.EntitiesForbidden, defused_common.DTDForbidden) as exc:
            raise XXEError(f"Secure XML parser blocked unsafe payload: {exc}") from exc
        except Exception as exc:
            raise DocumentSecurityError(f"XML parse failure: {exc}") from exc

    # Fallback to standard ElementTree with entity/DTD prevention
    try:
        parser = ET.XMLParser()
        if hasattr(parser, "entity"):
            parser.entity = {}
        return ET.fromstring(raw_str, parser=parser)
    except Exception as exc:
        raise DocumentSecurityError(f"XML parse failure: {exc}") from exc


def validate_zip_archive(
    archive_blob_or_path: bytes | Path | io.BytesIO,
    max_size: int = MAX_DOC_SIZE,
    max_uncompressed: int = MAX_UNCOMPRESSED_SIZE,
) -> zipfile.ZipFile:
    """Validate archive integrity, checking for Zip Slip, excessive entries, and Zip Bombs."""
    if isinstance(archive_blob_or_path, (bytes, bytearray)):
        if len(archive_blob_or_path) > max_size:
            raise ZipBombError(f"Upload size {len(archive_blob_or_path)} bytes exceeds maximum {max_size} bytes")
        stream = io.BytesIO(archive_blob_or_path)
    elif isinstance(archive_blob_or_path, io.BytesIO):
        blob = archive_blob_or_path.getvalue()
        if len(blob) > max_size:
            raise ZipBombError(f"Upload size {len(blob)} bytes exceeds maximum {max_size} bytes")
        stream = archive_blob_or_path
    elif isinstance(archive_blob_or_path, Path):
        st_size = archive_blob_or_path.stat().st_size
        if st_size > max_size:
            raise ZipBombError(f"Upload size {st_size} bytes exceeds maximum {max_size} bytes")
        stream = open(archive_blob_or_path, "rb")
    else:
        raise TypeError("Expected bytes, BytesIO, or Path")

    try:
        zf = zipfile.ZipFile(stream)
    except zipfile.BadZipFile as exc:
        raise DocumentSecurityError("Invalid or corrupted zip archive") from exc

    infos = zf.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise ZipBombError(f"Archive entry count {len(infos)} exceeds maximum {MAX_ZIP_ENTRIES}")

    total_uncompressed = 0
    for info in infos:
        clean_name = info.filename.replace("\\", "/")
        if clean_name.startswith("/") or clean_name.startswith("../") or "/../" in clean_name or clean_name == "..":
            raise ZipSlipError(f"Zip Slip / traversal detected in entry: {info.filename}")

        parts = Path(clean_name).parts
        if ".." in parts:
            raise ZipSlipError(f"Zip Slip / traversal path detected: {info.filename}")

        total_uncompressed += info.file_size
        if total_uncompressed > max_uncompressed:
            raise ZipBombError(f"Uncompressed archive size exceeds limit ({max_uncompressed} bytes)")

        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > MAX_COMPRESSION_RATIO and info.file_size > 1_000_000:
                raise ZipBombError(f"Zip bomb detected: compression ratio {ratio:.1f} exceeds limit")

    return zf


def safe_extract_zip(
    archive: bytes | Path | io.BytesIO,
    target_dir: Path,
    sanitize_names: bool = True,
) -> list[Path]:
    """Safely extract archive entries, strictly sanitizing filenames and confirming destination bounds."""
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    zf = validate_zip_archive(archive)

    extracted_paths: list[Path] = []
    with zf:
        for info in zf.infolist():
            raw_name = info.filename.replace("\\", "/")
            if sanitize_names:
                safe_name = Path(raw_name).name
                if not safe_name:
                    continue
                dest = (target_dir / safe_name).resolve()
            else:
                dest = (target_dir / raw_name).resolve()

            if not dest.is_relative_to(target_dir):
                raise ZipSlipError(f"Entry {info.filename} escapes destination directory {target_dir}")

            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted_paths.append(dest)

    return extracted_paths


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


# =========================================================================
# Intelligent Template & Document Parsing (Markdown, DOCX, TXT, PDF)
# =========================================================================

PLACEHOLDER_REGEXES = [
    re.compile(r"\{\{([^{}]+)\}\}"),           # {{project_name}}, {{scope}}
    re.compile(r"\[([A-Z][A-Za-z0-9_\s\-]{2,50})\]"),  # [System Overview], [Requirements]
    re.compile(r"<<([^<>]+)>>"),               # <<project_name>>
    re.compile(r"<([A-Z][A-Za-z0-9_\s\-]{2,50})>"),    # <System Overview>
]


def extract_placeholders(text: str) -> List[str]:
    """Extract template placeholders like {{project_name}} or [System Overview]."""
    found: List[str] = []
    seen: set[str] = set()
    for reg in PLACEHOLDER_REGEXES:
        for match in reg.finditer(text):
            full_match = match.group(0).strip()
            if full_match not in seen:
                seen.add(full_match)
                found.append(full_match)
    return found


def _parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Extract YAML-style frontmatter delimited by ---."""
    metadata: Dict[str, Any] = {}
    content = text
    if text.startswith("---\n") or text.startswith("---\r\n"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            content = parts[2].lstrip()
            for line in fm_text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip()] = val.strip().strip("\"'")
    return metadata, content


def _parse_markdown_tables(lines: List[str]) -> List[List[List[str]]]:
    """Extract markdown tables into 2D lists of cell strings."""
    tables: List[List[List[str]]] = []
    current_table: List[List[str]] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:-1]:
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                continue
            current_table.append(cells)
            in_table = True
        else:
            if in_table and current_table:
                tables.append(current_table)
                current_table = []
            in_table = False

    if current_table:
        tables.append(current_table)
    return tables


def _parse_markdown(text: str, filename: str) -> Dict[str, Any]:
    """Parse Markdown or Plain Text document into structured sections and metadata."""
    metadata, body = _parse_frontmatter(text)
    lines = body.splitlines()

    title = metadata.get("title") or ""
    sections: List[Dict[str, Any]] = []
    current_heading = ""
    current_level = 1
    current_content_lines: List[str] = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            current_content_lines.append(line)
            continue

        if not in_code_block:
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                if current_heading or current_content_lines:
                    content_text = "\n".join(current_content_lines).strip()
                    heading_name = current_heading or "Overview"
                    sections.append({
                        "heading": heading_name,
                        "level": current_level,
                        "content": content_text
                    })
                    if not title and current_level == 1:
                        title = heading_name

                current_level = len(heading_match.group(1))
                current_heading = heading_match.group(2).strip()
                current_content_lines = []
                if not title and current_level == 1:
                    title = current_heading
                continue

        current_content_lines.append(line)

    if current_heading or current_content_lines:
        content_text = "\n".join(current_content_lines).strip()
        heading_name = current_heading or ("Overview" if not sections else "Conclusion")
        sections.append({
            "heading": heading_name,
            "level": current_level,
            "content": content_text
        })
        if not title and current_level == 1:
            title = heading_name

    if not title:
        title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

    tables = _parse_markdown_tables(lines)
    placeholders = extract_placeholders(text)

    return {
        "title": title,
        "sections": sections,
        "tables": tables,
        "raw_text": body.strip() or text.strip(),
        "placeholders": placeholders,
        "metadata": metadata
    }


def _parse_docx_xml_fallback(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Safe fallback DOCX parser using zipfile and defused XML parsing."""
    try:
        zf = validate_zip_archive(content_bytes)
        with zf:
            xml_content = zf.read("word/document.xml")
            root = safe_parse_xml(xml_content, forbid_dtd=False, forbid_entities=True)

        namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: List[str] = []
        sections: List[Dict[str, Any]] = []
        current_heading = ""
        current_level = 1
        current_content: List[str] = []

        for p in root.iter(f"{{{namespaces['w']}}}p"):
            texts = [node.text for node in p.iter(f"{{{namespaces['w']}}}t") if node.text]
            full_p = "".join(texts).strip()
            if not full_p:
                continue
            paragraphs.append(full_p)

            p_style = p.find(f".//{{{namespaces['w']}}}pStyle")
            style_val = p_style.attrib.get(f"{{{namespaces['w']}}}val", "") if p_style is not None else ""
            h_match = re.match(r"(?:Heading|heading)(\d)", style_val)

            if h_match or full_p.startswith("#"):
                if current_heading or current_content:
                    sections.append({
                        "heading": current_heading or "Overview",
                        "level": current_level,
                        "content": "\n".join(current_content).strip()
                    })
                if h_match:
                    current_level = int(h_match.group(1))
                    current_heading = full_p
                else:
                    hashes, text_part = full_p.split(" ", 1) if " " in full_p else (full_p, "")
                    current_level = len(hashes)
                    current_heading = text_part
                current_content = []
            else:
                current_content.append(full_p)

        if current_heading or current_content:
            sections.append({
                "heading": current_heading or "Overview",
                "level": current_level,
                "content": "\n".join(current_content).strip()
            })

        raw_text = "\n\n".join(paragraphs)
        title = sections[0]["heading"] if sections else Path(filename).stem.title()
        return {
            "title": title,
            "sections": sections,
            "tables": [],
            "raw_text": raw_text,
            "placeholders": extract_placeholders(raw_text),
            "metadata": {}
        }
    except Exception as e:
        return {
            "title": Path(filename).stem.title(),
            "sections": [{"heading": "Overview", "level": 1, "content": f"Failed to parse docx xml: {e}"}],
            "tables": [],
            "raw_text": "",
            "placeholders": [],
            "metadata": {}
        }


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


def _parse_pdf(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Parse PDF document extracting text pages, headings, and structure."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content_bytes))
        page_texts = [p.extract_text() or "" for p in reader.pages]
        combined = "\n\n".join(t for t in page_texts if t.strip())
    except Exception:
        combined = ""

    parsed = _parse_markdown(combined, filename)
    parsed["title"] = parsed["title"] or Path(filename).stem.replace("_", " ").title()
    return parsed


def parse_document(content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Universal document & template parser.

    Supports .md, .txt, .docx, and .pdf.
    Returns:
        {
            "title": str,
            "sections": [{"heading": str, "level": int, "content": str}],
            "tables": list,
            "raw_text": str,
            "placeholders": list[str],
            "metadata": dict
        }
    """
    ext = Path(filename).suffix.lower()

    if ext in (".docx", ".doc"):
        return _parse_docx(content_bytes, filename)
    elif ext == ".pdf":
        return _parse_pdf(content_bytes, filename)
    elif ext in (".md", ".txt", ".rst") or not ext:
        text = content_bytes.decode("utf-8", errors="replace")
        return _parse_markdown(text, filename)
    else:
        text = content_bytes.decode("utf-8", errors="replace")
        return _parse_markdown(text, filename)
