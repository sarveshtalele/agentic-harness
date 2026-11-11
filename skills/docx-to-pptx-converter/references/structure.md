# Document Structure Parsing

## Heading Levels

The skill expects the DOCX to use standard Word heading styles:
- 'Heading 1' for top-level headings (each becomes a new slide)
- 'Heading 2' and below are ignored (content may be included under their parent H1)

## Lists

Bullet points are identified by paragraphs with list-style formatting (e.g., 'List Bullet', 'ListParagraph'). Numbered lists are treated similarly.

## Tables

Tables are separate from paragraphs. A table is considered numeric if all data cells in the second column can be parsed as floats.

## Missing Data

If a table has non-numeric data in the second column, it is skipped and reported in warnings.
If a heading has no following content, an empty slide is created.

## Libraries

- python-docx (version >= 0.8.11)
- python-pptx (version >= 0.6.21)
