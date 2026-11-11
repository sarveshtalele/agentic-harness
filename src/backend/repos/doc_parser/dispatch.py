"""Universal document parser entry point."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from backend.repos.doc_parser.word import _parse_docx
from backend.repos.doc_parser.markdown import _parse_markdown
from backend.repos.doc_parser.pdf import _parse_pdf


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
