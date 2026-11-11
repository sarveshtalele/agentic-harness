import json
import re

def convert(tabular_input: str) -> dict:
    """
    Convert tabular data from CSV, JSON, or pipe-delimited format into
    Markdown and HTML tables, with right-aligned numeric columns.
    Returns a dict with keys 'markdown_table', 'html_table', and optionally 'error_report'.
    """
    # Detect format
    stripped = tabular_input.strip()
    if stripped.startswith('['):
        data = json.loads(stripped)
        headers = list(data[0].keys())
        rows = [[str(row[h]) for h in headers] for row in data]
    else:
        lines = stripped.split('\n')
        first_line = lines[0]
        if '|' in first_line:
            delimiter = '|'
        else:
            delimiter = ','
        headers = [h.strip() for h in first_line.split(delimiter)]
        rows = []
        for line in lines[1:]:
            if line.strip():
                cells = [c.strip() for c in line.split(delimiter)]
                rows.append(cells)

    # Detect numeric columns
    num_cols = len(headers)
    numeric_cols = []
    for col_idx in range(num_cols):
        all_numeric = True
        for row in rows:
            if len(row) > col_idx:
                try:
                    float(row[col_idx])
                except ValueError:
                    all_numeric = False
                    break
        if all_numeric:
            numeric_cols.append(col_idx)

    # Build Markdown table
    md = '| ' + ' | '.join(headers) + ' |\n'
    separator = []
    for i in range(num_cols):
        if i in numeric_cols:
            separator.append('---:')
        else:
            separator.append('---')
    md += '| ' + ' | '.join(separator) + ' |\n'
    for row in rows:
        if len(row) == num_cols:
            md += '| ' + ' | '.join(row) + ' |\n'
        else:
            # still add row to table if possible, but it will be flagged
            md += '| ' + ' | '.join(row) + ' |\n'

    # Build HTML table
    html = '<table>\n<thead>\n<tr>'
    for h in headers:
        html += f'<th>{h}</th>'
    html += '</tr>\n</thead>\n<tbody>\n'
    for row in rows:
        html += '<tr>'
        for i, cell in enumerate(row):
            align = ' style="text-align: right;"' if i in numeric_cols else ''
            html += f'<td{align}>{cell}</td>'
        # fill missing cells with empty
        for i in range(len(row), num_cols):
            html += '<td></td>'
        html += '</tr>\n'
    html += '</tbody>\n</table>'

    # Error report
    error_lines = []
    for idx, row in enumerate(rows, start=1):
        if len(row) != num_cols:
            error_lines.append(f"Row {idx}: field count {len(row)} (expected {num_cols})")
    result = {
        'markdown_table': md,
        'html_table': html
    }
    if error_lines:
        result['error_report'] = 'Rows with wrong number of fields:\n' + '\n'.join(error_lines)
    return result