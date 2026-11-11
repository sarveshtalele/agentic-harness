---
name: docx-to-pptx-converter
description: Converts a Word DOCX document into a PowerPoint PPTX presentation. It creates one slide per top-level heading with its associated bullet points, a title slide from the document title, and a simple bar-chart infographic slide for every table whose second column holds numbers. It reports any headings or tables it could not place. Use when a DOCX document with structured headings, bullet lists, and numeric tables needs transformation into a presentation file.
metadata:
  author: admin
---
# docx-to-pptx-converter

## Steps

1. Read the DOCX file path from standard input or as an argument.
2. Load the DOCX document using python-docx.
3. Extract the document title (first Heading 1 or document core property title).
4. Create a new PowerPoint presentation using python-pptx.
5. Create a title slide with the extracted title.
6. Iterate through all paragraphs. For each Heading 1 (top-level heading), collect following paragraphs until next Heading 1, including bullet points (list-style paragraphs). Add a new slide per heading.
7. Scan all tables in the document. For each table, check if the second column (index 1) contains numeric values (all rows except header). If numeric, create a bar chart slide.
8. If any heading or table could not be placed (e.g., no content, non-numeric), log a warning.
9. Save the PPTX file.
10. Output the path to the PPTX file and any warnings.

## Decision Rules

- Title is the first Heading 1 in the document; fallback to document core title if missing.
- A heading is top-level if its paragraph style is 'Heading 1' or equivalent.
- Bullet points are paragraphs with a list style (e.g., 'List Bullet', 'List Paragraph').
- A table's second column is numeric if all rows (excluding header) have numeric values in that column.
- If no headings exist, only title slide and chart slides (if any) are created.

## References

- [Structure Details](references/structure.md)
- [python-docx documentation](https://python-docx.readthedocs.io/)
- [python-pptx documentation](https://python-pptx.readthedocs.io/)
