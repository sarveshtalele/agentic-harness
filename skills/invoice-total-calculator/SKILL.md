---
name: invoice-total-calculator
description: Computes invoice totals from JSON input as specified by the BRD. Given lines with quantity and unit_price, discount_percent (0–100) and tax_percent (0–50), it calculates subtotal, discount, tax, and total with half-up rounding to two decimals. Returns an error naming the field if any value is out of range. Use when finance staff need a reliable, repeatable invoice total computation from a JSON object.
metadata:
  author: admin
---
# Invoice total calculator

## Steps

1. Parse the JSON input object from standard input.
2. Validate that `lines` is an array; for each line, validate `quantity` is a non-negative number and `unit_price` is a non-negative number.
3. Validate that `discount_percent` is a number between 0 and 100 inclusive.
4. Validate that `tax_percent` is a number between 0 and 50 inclusive.
5. If any validation fails, output a JSON object with an `error` field naming the invalid field (e.g. `{"error": "discount_percent out of range"}`) and stop.
6. Compute subtotal = sum over lines of quantity * unit_price.
7. Compute discount = subtotal * discount_percent / 100, rounded half up to 2 decimals.
8. Compute discounted_amount = subtotal - discount.
9. Compute tax = discounted_amount * tax_percent / 100, rounded half up to 2 decimals.
10. Compute total = discounted_amount + tax, rounded half up to 2 decimals.
11. Output a JSON object with keys `subtotal`, `discount`, `tax`, `total`.

## Validation rules

- `quantity` >= 0
- `unit_price` >= 0
- 0 <= `discount_percent` <= 100
- 0 <= `tax_percent` <= 50

For half-up rounding, see the Python implementation in [scripts/invoice_total_calculator.py](scripts/invoice_total_calculator.py) and the entry point in [scripts/run.py](scripts/run.py).

## Output format

The output is JSON. The structure is shown in [assets/invoice_total_output_template.json](assets/invoice_total_output_template.json).

- On success: `{"subtotal": number, "discount": number, "tax": number, "total": number}`
- On validation error: `{"error": "<field name> out of range"}`