---
name: tabular-data-converter
description: "Converts CSV, JSON (list of objects), or pipe-delimited text into Markdown and HTML tables. Detects the header row, right-aligns numeric columns, and reports rows with an incorrect number of fields. Use when raw tabular data in these formats needs to be presented as a formatted table in documentation or a web context."
author: admin
---

# Tabular Data Converter

## Steps

1. **Detect format**: Examine the input text to determine if it is CSV (comma-separated), JSON (a JSON array of objects), or pipe-delimited (by detecting the first row containing pipes).
2. **Parse rows**: Split the input into rows. For JSON, convert each object to a row with keys as headers.
3. **Identify header**: Use the first row as the header row.
4. **Detect numeric columns**: For each column, check if all non-header values can be parsed as numbers (integers or floats). If yes, the column is numeric and will be right-aligned in tables.
5. **Generate Markdown table**: Build a Markdown table string with the header row, a separator row (with colons for alignment: left for text, right for numeric), and data rows. Numeric values are right-aligned.
6. **Generate HTML table**: Build an HTML table with the same alignment rules.
7. **Report row errors**: Compare each data row's field count to the header row's field count. If mismatched, record the row number and the number of fields found (and expected).
8. **Output**: Return a JSON object with keys `markdown_table`, `html_table`, and optionally `error_report`.

## Decision Rules

- If the input starts with `[` and is valid JSON, treat as JSON.
- If the first line contains a pipe `|`, treat as pipe-delimited.
- Otherwise, treat as CSV.
- Numeric detection: a column is numeric if every non-header cell can be converted to a float.

## Files

- `scripts/table_converter.py` – main converter logic
- `scripts/test_table_converter.py` – pytest tests
- `references/error_reporting.md` – error report details
- `assets/markdown_table.md` – Markdown table template
- `assets/html_table.html` – HTML table template
- `assets/error_report.md` – error report template

## Examples

See test cases in the test file for sample inputs and expected outputs.