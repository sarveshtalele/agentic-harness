"""Markdown and plain text parsing, placeholders, frontmatter, tables."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


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
