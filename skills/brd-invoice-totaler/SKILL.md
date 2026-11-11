---
name: brd-invoice-totaler
description: Computes invoice totals by reading a JSON object with lines (each having description, quantity, unit_price), discount_percent (0-100), and tax_percent (0-50). Returns subtotal, discount, tax, and total with half-up rounding to two decimals. Use when a user provides a JSON invoice payload and expects the exact payable total per the BRD rules.
metadata:
  author: admin
---
# Invoice Total Calculator

This skill validates and calculates invoice totals according to the BRD rules.

## Input Format

The skill reads a JSON object from standard input with this structure:

```json
{
  "lines": [
    {"description": "string", "quantity": number, "unit_price": number}
  ],
  "discount_percent": number,
  "tax_percent": number
}
```

## Computation Steps

1. Parse the JSON input from stdin into a Python dict.
2. Validate that `quantity` and `unit_price` in each line are non-negative numbers.
3. Validate that `discount_percent` is between 0 and 100 inclusive.
4. Validate that `tax_percent` is between 0 and 50 inclusive.
5. If any validation fails, output an error JSON with the field name that failed (see `assets/error_template.json`).
6. Compute subtotal = sum(quantity * unit_price) over all lines.
7. Compute discount = subtotal \* (discount_percent / 100), rounded half-up to 2 decimals.
8. Compute discounted = subtotal - discount.
9. Compute tax = discounted \* (tax_percent / 100), rounded half-up to 2 decimals.
10. Compute total = discounted + tax, rounded half-up to 2 decimals.
11. Output JSON with keys subtotal, discount, tax, total (see `assets/output_template.json`).

## Rounding Rule

All monetary values are rounded half-up to exactly 2 decimal places. Examples:
- 10.555 → 10.56
- 3.333 → 3.33
- 12.345 → 12.35

## Output Format

For valid input:
- `assets/output_template.json`

For validation errors:
- `assets/error_template.json`

## Files

- `scripts/invoice.py` – Core calculator functions.
- `scripts/run.py` – Entry point reading stdin and printing stdout.
- `scripts/test_invoice.py` – Pytest tests.
- `assets/output_template.json` – Template for valid output.
- `assets/error_template.json` – Template for error output.
