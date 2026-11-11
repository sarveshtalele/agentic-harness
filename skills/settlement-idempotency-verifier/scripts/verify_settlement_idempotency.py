import json
import sys
from collections import defaultdict

def verify_idempotency(records):
    """
    Verifies idempotency for a list of settlement records.
    Returns a dict with:
      - duplicates: list of record ids that are duplicates
      - conflicts: list of record ids that are conflicts
      - merchant_totals: dict mapping merchant_id -> total unique settled amount
    """
    if not isinstance(records, list):
        raise ValueError("Input must be a JSON array")

    for rec in records:
        if not isinstance(rec, dict):
            raise ValueError("Each record must be an object")
        for field in ('id', 'merchant_id', 'amount', 'idempotency_key'):
            if field not in rec:
                raise ValueError(f"Record missing field: {field}")

    # Group by idempotency key
    groups = defaultdict(list)
    for rec in records:
        groups[rec['idempotency_key']].append(rec)

    duplicates = []
    conflicts = []
    # first occurrence per key: store id, amount, merchant_id
    unique_settlements = {}  # merchant -> list of amounts
    merchant_totals = defaultdict(float)

    for key, recs in groups.items():
        first = recs[0]
        first_amount = first['amount']
        merchant = first['merchant_id']
        # Add first occurrence to unique settlements
        merchant_totals[merchant] += first_amount

        for rec in recs[1:]:
            if rec['amount'] == first_amount:
                duplicates.append(rec['id'])
            else:
                conflicts.append(rec['id'])

    return {
        'duplicates': duplicates,
        'conflicts': conflicts,
        'merchant_totals': dict(merchant_totals)
    }

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("Empty input")
        records = json.loads(raw)
        result = verify_idempotency(records)
        
        # Build report
        lines = []
        if result['duplicates']:
            ids = ', '.join(result['duplicates'])
            lines.append(f"Duplicate record ids: {ids}")
        else:
            lines.append("No duplicates found.")
        if result['conflicts']:
            ids = ', '.join(result['conflicts'])
            lines.append(f"Conflict record ids: {ids}")
        else:
            lines.append("No conflicts found.")
        
        lines.append("Per-merchant unique totals:")
        for merchant, total in sorted(result['merchant_totals'].items()):
            lines.append(f"  {merchant}: {total}")
        
        report = '\n'.join(lines)
        print(report)
        
        if result['duplicates'] or result['conflicts']:
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
