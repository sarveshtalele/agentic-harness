---
name: markdown-to-docx-converter
description: Converts a Markdown file into a Word DOCX document while preserving headings, paragraphs, bulleted and numbered lists, bold and italic text, tables and code blocks. Produces a valid .docx file and reports any Markdown elements that could not be converted. Use when a Markdown file needs to be transformed into a formatted Word document for sharing, printing, or further editing.
author: admin
---

# Markdown to DOCX Converter

This skill converts a Markdown file into a Word DOCX document while preserving all supported formatting elements. It uses the `python-docx` library to create the output.

## Prerequisites

- Python 3.8 or later
- `python-docx` library (install via `pip install python-docx`)

## Steps

1. **Read input** – Read the Markdown file from the path provided by the user. If the file does not exist or cannot be read, report an error and stop.

2. **Parse Markdown** – Identify and classify each block element:
   - Headings (h1 through h6)
   - Paragraphs (including inline bold and italic)
   - Bulleted lists (unordered)
   - Numbered lists (ordered)
   - Tables
   - Fenced code blocks (with or without language hint)
   - Inline code
   - Horizontal rules (ignored)

   Any element not in this list (e.g., blockquotes, HTML, images) is recorded as unconverted.

3. **Create DOCX document** – Initialise a new `python-docx Document`.

4. **Apply formatting** – For each element in order:
   - **Heading**: Set `document.add_heading(text, level=n)` where n is 1–6.
   - **Paragraph**: Use `document.add_paragraph(text)`. For runs with bold or italic, split the paragraph and apply `run.bold = True` or `run.italic = True` as needed. Inline code is formatted with a monospaced font (Consolas or Courier New).
   - **Bulleted list**: Use `document.add_paragraph(text, style='List Bullet')`.
   - **Numbered list**: Use `document.add_paragraph(text, style='List Number')`.
   - **Table**: Create a table with `document.add_table(rows, cols)` and fill cells with text. Bold/italic runs inside table cells are supported.
   - **Code block**: Add a paragraph with monospaced font and light grey shading. Preserve leading whitespace.

5. **Save document** – Save the DOCX to the output path specified by the user. If no output path is given, default to `output.docx`.

6. **Generate report** – Print a report listing any unconverted elements. If all elements were converted, print "Conversion successful – no unconverted elements."

## Decision Rules

- **Unsupported elements**: Blockquotes, HTML tags, images, fenced code without language hint (still converted but recorded), and horizontal rules are recorded as unconverted but do not stop conversion.
- **Malformed Markdown**: If a table has inconsistent column counts, the script fills missing cells with empty strings.
- **Empty file**: If the Markdown file is empty, create an empty DOCX and report "Input file is empty."
- **Encoding**: Assume UTF-8 encoding.

## Limitations

See [references/formatting_notes.md](references/formatting_notes.md) for details on formatting decisions and known limitations.
