"""Doc parsers: Markdown and Word parsing."""
import io
import os
import sys
from docx import Document

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.repos.doc_parser import parse_document, _parse_docx_xml_fallback


def test_markdown_parser_with_headings_tables_and_sections():
    """Verify Markdown parser parses frontmatter, heading hierarchy, tables, and placeholders."""
    md_content = """---
title: E-Commerce Payment Gateway BRD
version: 1.0
---

# Executive Summary
The payment system enables secure card processing for {{project_name}}.
Main goal is zero-downtime transaction authorization.
[System Overview]

## Payment Methods & Capabilities
Supported mechanisms for {{scope}}:

| Code | Provider | Settlement Window | Active |
| --- | --- | --- | --- |
| PAY-01 | Stripe Cards | Instant | Yes |
| PAY-02 | Apple Pay | Instant | Yes |
| PAY-03 | Direct Debit | T+2 Days | No |

### Security & Compliance
- PCI-DSS Level 1 compliance required.
- TLS 1.3 encryption mandatory.

```python
def verify_signature(payload, secret):
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()
```

## Approval Matrix
Final sign-off from [Requirements] lead.
"""
    parsed = parse_document(md_content.encode("utf-8"), "payment_brd.md")

    assert parsed["title"] == "E-Commerce Payment Gateway BRD"
    assert len(parsed["sections"]) >= 3

    sec_headings = [s["heading"] for s in parsed["sections"]]
    assert "Executive Summary" in sec_headings
    assert "Payment Methods & Capabilities" in sec_headings
    assert "Security & Compliance" in sec_headings
    assert "Approval Matrix" in sec_headings

    # Check tables
    assert len(parsed["tables"]) == 1
    table_rows = parsed["tables"][0]
    assert len(table_rows) == 4  # Header + 3 rows
    assert table_rows[0] == ["Code", "Provider", "Settlement Window", "Active"]
    assert table_rows[1][0] == "PAY-01"

    # Check placeholders
    assert "{{project_name}}" in parsed["placeholders"]
    assert "{{scope}}" in parsed["placeholders"]
    assert "[System Overview]" in parsed["placeholders"]
    assert "[Requirements]" in parsed["placeholders"]


def test_docx_parser_extracting_paragraphs_headings_and_tables():
    """Verify Word (.docx) parser extracts structured headings, tables, and fallback xml."""
    doc = Document()
    doc.add_heading("Cloud Infrastructure Specification", level=1)
    doc.add_paragraph("Target architecture blueprint for {{project_name}}.")
    doc.add_heading("Networking & VPC", level=2)
    doc.add_paragraph("Virtual private cloud configuration adhering to [System Overview].")

    table = doc.add_table(rows=3, cols=3)
    headers = ["Subnet", "CIDR Block", "Public/Private"]
    for j, h in enumerate(headers):
        table.rows[0].cells[j].text = h
    row1 = ["App-Tier-A", "10.0.1.0/24", "Private"]
    for j, val in enumerate(row1):
        table.rows[1].cells[j].text = val
    row2 = ["Public-LB", "10.0.0.0/24", "Public"]
    for j, val in enumerate(row2):
        table.rows[2].cells[j].text = val

    doc.add_heading("Observability Requirements", level=3)
    doc.add_paragraph("All metrics monitored under {{scope}} guidelines.")

    buffer = io.BytesIO()
    doc.save(buffer)
    docx_bytes = buffer.getvalue()

    parsed = parse_document(docx_bytes, "infrastructure.docx")

    assert parsed["title"] == "Cloud Infrastructure Specification"
    assert len(parsed["sections"]) >= 3
    assert len(parsed["tables"]) == 1
    assert parsed["tables"][0][0] == ["Subnet", "CIDR Block", "Public/Private"]
    assert parsed["tables"][0][1][0] == "App-Tier-A"
    assert "{{project_name}}" in parsed["placeholders"]
    assert "[System Overview]" in parsed["placeholders"]
    assert "{{scope}}" in parsed["placeholders"]

    # Verify safe XML fallback parser also parses correctly
    fallback = _parse_docx_xml_fallback(docx_bytes, "infrastructure.docx")
    assert len(fallback["sections"]) >= 1
    assert "{{project_name}}" in fallback["placeholders"]
