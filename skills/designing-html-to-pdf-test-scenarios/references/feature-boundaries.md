# Feature Boundaries

Documented boundary values for each feature of the HTML to PDF converter.

## Headings
- Maximum heading level: 6 (`<h6>` is smallest, `<h1>` largest).
- No defined minimum; single heading is valid.

## Tables
- Maximum columns: 20
- Maximum rows: 500
- Cells may contain images or other HTML.
- Supported CSS for borders and backgrounds.

## Images
- Supported formats: JPEG, PNG, GIF (assumed unless spec says otherwise).
- No defined limit on file size per image; boundary tested with very large image
  (e.g., 50 MB single image).

## CSS
- Supported properties: as per spec (common ones: `color`, `font-*`,
  `page-break-*`, `border`, `background`).
- No defined limit on total CSS size; boundary tested with 10 MB inline CSS.

## Page Breaks
- Supported properties: `page-break-before`, `page-break-after`,
  `page-break-inside`.
- Adjacent page breaks are allowed.
- No defined maximum count; boundary tested with 50 consecutive breaks.

## Encodings
- Supported: UTF-8, ISO-8859-1, Windows-1252.
- Unsupported encoding: fallback to UTF-8 with warning.
- No file size limit specific to encoding.

## Very Large Files
- Fast (under 10 MB): processed quickly.
- Medium (10 MB to 50 MB): processed but may be slow.
- Over 50 MB: error triggered.

**Note:** All boundaries are taken from the specification provided. If the
spec is updated, these values must be updated accordingly.
