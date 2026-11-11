---
name: settlement-idempotency-verifier
description: Verifies settlement idempotency in a list of payment settlement records (JSON). Every idempotency key settles at most once. A retried request with the same key and the same amount is a duplicate and is reported. The same key with a different amount is a conflict and is reported. The total settled per merchant equals the sum of unique settlements. Prints every duplicate and conflict with its record ids. Use when a JSON array of settlement records needs verification for duplicate or conflicting uses of idempotency keys.
metadata:
  author: admin
---
# Settlement Idempotency Verifier

This skill processes a JSON array of settlement records from standard input, verifies idempotency, and prints a report.

## Steps

1. **Read input**: Read a JSON array of objects from standard input. Each object has:
   - `id`: string, unique record identifier
   - `merchant_id`: string, merchant identifier
   - `amount`: number, settlement amount
   - `idempotency_key`: string, key for idempotency

2. **Validate input**: Ensure input is a list of objects with required fields. If malformed, print error and exit with code 1.

3. **Group by idempotency_key**: For each key, collect all records with that key.

4. **Detect duplicates and conflicts**:
   - For each key with more than one record, let the first occurrence be the reference.
   - Any later record with same amount as first is a **duplicate**.
   - Any later record with different amount than first is a **conflict**.
   - Collect record IDs for duplicates and conflicts.

5. **Compute unique per-merchant totals**:
   - For each merchant, sum amounts of only the first occurrence of each idempotency key.

6. **Print report**: Follow template in `assets/report_template.txt`.

7. **Exit code**: If any duplicate or conflict was found, exit with code 1; otherwise exit with code 0.

## Reference

For full implementation details, see `scripts/verify_settlement_idempotency.py`.
