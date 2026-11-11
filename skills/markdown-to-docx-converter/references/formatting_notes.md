# Markdown to DOCX Formatting Notes

## Supported Elements

| Element         | Conversion Method                                                                 |
|-----------------|-----------------------------------------------------------------------------------|
| h1–h6           | `document.add_heading(text, level=n)`                                            |
| Paragraphs      | `document.add_paragraph()` with bold/italic runs                                 |
| Bulleted lists  | `style='List Bullet'`                                                            |
| Numbered lists  | `style='List Number'`                                                            |
| Tables          | `document.add_table(rows, cols)` with cell text                                  |
| Fenced code     | Monospaced paragraph with light grey shading                                    |
| Inline code     | Monospaced run within paragraph                                                  |
| Bold            | `run.bold = True`                                                                |
| Italic          | `run.italic = True`                                                              |

## Known Limitations

- **Nested formatting** (e.g., `***bold italic***`) is not handled correctly; only outermost is applied.
- **Blockquotes** (`>`) are recorded but not converted.
- **HTML tags** are recorded but not converted.
- **Images** (`![alt](src)`) are ignored and recorded.
- **Horizontal rules** (`---`, `***`, `___`) are ignored.
- **Fenced code block language identifiers** are stored but not used for syntax highlighting.
- **Tables with merged cells** are not supported.
- **Indented code blocks** (4 spaces) are treated as normal paragraphs.
- **Nested lists** are not supported.
- **Escaped characters** (e.g., `\*`) are not processed.

## Implementation Details

- The parser reads the file line by line and classifies elements using regular expressions.
- A simple state machine handles fenced code blocks (`\`\`\``).
- For tables, the header row is determined by the first row, and the separator line is skipped.
- Bold/italic formatting is applied by splitting paragraph text on `**` or `*` markers and creating runs.
- Code blocks are added as paragraphs with Consolas font and light grey background (`F0F0F0`).
