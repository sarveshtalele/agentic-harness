"""Fallback .docx parser that reads document.xml directly."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List
from backend.repos.doc_parser.markdown import extract_placeholders
from backend.repos.doc_parser.security import safe_parse_xml, validate_zip_archive


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
