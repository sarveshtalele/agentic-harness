# Error Reporting Format

When any data row has a different number of fields than the header row, the skill generates an error report.

The report is a plain text string with the following structure:

```
Rows with wrong number of fields:
Row <row_number>: field count <actual> (expected <expected>)
```

- Row numbers start from 1 (the first data row after the header).
- The expected count is the number of header fields.
- Multiple rows are listed one per line.
- If no errors, no error report is included in the output.

Example:
```
Rows with wrong number of fields:
Row 2: field count 2 (expected 3)
Row 3: field count 4 (expected 3)
```