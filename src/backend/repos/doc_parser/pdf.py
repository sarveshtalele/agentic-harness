"""PDF parsing."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict
from backend.repos.doc_parser.markdown import _parse_markdown


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
