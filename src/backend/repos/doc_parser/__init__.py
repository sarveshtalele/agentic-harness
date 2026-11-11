"""Secure and intelligent document & template parser.

Supports Markdown (.md), Plain Text (.txt), Word (.docx), and PDF (.pdf).
Extracts document structure, headings, sections, tables, code blocks, frontmatter,
and template placeholders (e.g. {{project_name}}, [System Overview], {{scope}}).
Includes defense against XXE, Zip Slip, decompression bombs, and XML entity expansion.
"""
from __future__ import annotations

from .security import HAVE_DEFUSEDXML, defused_ET, defused_common
from .security import (
    MAX_DOC_SIZE,
    MAX_UNCOMPRESSED_SIZE,
    MAX_COMPRESSION_RATIO,
    MAX_ZIP_ENTRIES,
    DocumentSecurityError,
    XXEError,
    ZipSlipError,
    ZipBombError,
    safe_parse_xml,
    validate_zip_archive,
    safe_extract_zip,
)
from .markdown import (
    PLACEHOLDER_REGEXES,
    extract_placeholders,
    _parse_frontmatter,
    _parse_markdown_tables,
    _parse_markdown,
)
from .word import (
    parse_docx_to_markdown,
    _parse_docx,
)
from .word_fallback import (
    _parse_docx_xml_fallback,
)
from .pdf import (
    _parse_pdf,
)
from .dispatch import (
    parse_document,
)
