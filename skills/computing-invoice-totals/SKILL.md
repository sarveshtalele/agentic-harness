---
name: computing-invoice-totals
description: Given a JSON invoice with line items, discount percent, and tax percent, computes the subtotal, discount, tax, and total rounded half up to two decimals. Returns a JSON result or an error message. Use when a user or process provides an invoice JSON and needs the payable total computed per a standard business rule (BRD). The concrete trigger is the BRD for invoice total calculator.
metadata:
  author: admin
---
# computing-invoice-totals

This skill reads an invoice JSON from standard input, validates the fields, and computes the payable total.

## Steps

1. Read the invoice JSON from standard input.
2. Validate that the input is valid JSON and contains the required fields: `lines`, `discount_percent`, `tax_percent`.
3. For each line, validate `quantity` (>= 0) and `unit_price` (>= 0).
4. Compute `subtotal = sum over lines of quantity * unit_price`.
5. Validate that `discount_percent` is between 0 and 100 inclusive.
6. Validate that `tax_percent` is between 0 and 50 inclusive.
7. Compute `discount = subtotal * discount_percent / 100`, rounded half up to 2 decimals.
8. Compute `discounted_amount = subtotal - discount`, rounded half up to 2 decimals.
9. Compute `tax = discounted_amount * tax_percent / 100`, rounded half up to 2 decimals.
10. Compute `total = discounted_amount + tax`, rounded half up to 2 decimals.
11. If any validation failed, output a JSON object with a single key `'error'` whose value describes the first invalid field.
12. Otherwise, output a JSON object with keys `subtotal`, `discount`, `tax`, `total`, each rounded half up to 2 decimals.

## Decision rules

- If JSON parsing fails: output `{"error": "... message about invalid JSON"}`.
- If required fields are missing: output `{"error": "missing field: <field>"}`.
- If a line has `quantity` < 0: output `{"error": "invalid quantity in line <index>"}`.
- If a line has `unit_price` < 0: output `{"error": "invalid unit_price in line <index>"}`.
- If `discount_percent` < 0 or > 100: output `{"error": "discount_percent out of range (0..100)"}`.
- If `tax_percent` < 0 or > 50: output `{"error": "tax_percent out of range (0..50)"}`.
- Otherwise: output successful invoice JSON.

## Related files

- [scripts/invoice_calculator.py](scripts/invoice_calculator.py) — pure calculation and validation functions.
- [scripts/run.py](scripts/run.py) — entry point that reads stdin, calls the calculator, and prints the result.
- [assets/invoice_output.json](assets/invoice_output.json) — template for successful output.
- [assets/invoice_error_output.json](assets/invoice_error_output.json) — template for error output.

## See also

- [BRD](references/brd.md)
