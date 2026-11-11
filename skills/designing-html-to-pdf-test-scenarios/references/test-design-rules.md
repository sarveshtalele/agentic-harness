# Test Design Rules

This document defines the rules for categorizing test cases in an HTML to PDF
conversion context.

## Categories

### Positive
- Valid, well-formed HTML that exercises supported features.
- Expected PDF output matches the intended layout.

### Negative
- Invalid HTML (e.g., missing closing tags, malformed attributes).
- Unsupported CSS properties (e.g., `grid` if not implemented).
- Expected behavior: converter returns an error, or gracefully degrades (e.g.,
  ignores unknown property).

### Boundary
- Limits documented in the specification or inferred from common practice.
- Examples: maximum heading level (6), maximum table columns (20), maximum
  file size (50 MB).
- Test at and just beyond each limit.

### Exception
- Unexpected or corrupted input data.
- Examples: binary file with `.html` extension, zero-byte file, unsupported
  character encoding.
- Expected behavior: clear error message, fallback to default, or safe abort.

## Example for Each Feature

| Feature   | Positive Example                      | Negative Example               | Boundary Example                        | Exception Example          |
|-----------|---------------------------------------|--------------------------------|----------------------------------------|----------------------------|
| headings  | `<h1>Title</h1>`                     | `<h1>Title` (missing close)    | 7 nested `<h1>` inside each other      | `<canvas>` element inside  |
| tables    | Simple 3x3 table                     | Table with unclosed `<tr>`     | 20 columns, 500 rows                    | Table inside a table       |
| images    | `<img src="photo.jpg">`            | `<img src="">`               | 1000 images on one page                 | SVG as an image            |
| CSS       | `color: #333`                        | `color: invalidvalue`          | 10 MB of inline CSS                     | CSS `@import` to a binary  |
| page breaks | `page-break-after: always`         | `page-break-after: bogus`      | 50 adjacent page breaks                 | Page break inside an inline element |
| encodings | UTF-8 with accented characters       | Invalid UTF-8 byte sequence    | 100 MB file with UTF-8                  | Binary encoding declared as UTF-8 |
| large files | 9 MB file (fast threshold)          | 51 MB file (over limit)        | Exactly 50 MB file                      | Zero-byte file             |
