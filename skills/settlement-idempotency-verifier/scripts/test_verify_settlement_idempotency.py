import pytest
import json
import sys
from verify_settlement_idempotency import verify_idempotency

def test_no_issues():
    records = [
        {"id": "r1", "merchant_id": "M1", "amount": 100.0, "idempotency_key": "k1"},
        {"id": "r2", "merchant_id": "M2", "amount": 50.0, "idempotency_key": "k2"}
    ]
    result = verify_idempotency(records)
    assert result['duplicates'] == []
    assert result['conflicts'] == []
    assert result['merchant_totals'] == {'M1': 100.0, 'M2': 50.0}

def test_duplicate_same_amount():
    records = [
        {"id": "rec1", "merchant_id": "M1", "amount": 100.0, "idempotency_key": "key1"},
        {"id": "rec2", "merchant_id": "M1", "amount": 100.0, "idempotency_key": "key1"},
        {"id": "rec3", "merchant_id": "M2", "amount": 50.0, "idempotency_key": "key2"}
    ]
    result = verify_idempotency(records)
    assert result['duplicates'] == ['rec2']
    assert result['conflicts'] == []
    assert result['merchant_totals'] == {'M1': 100.0, 'M2': 50.0}

def test_conflict_different_amount():
    records = [
        {"id": "recA", "merchant_id": "M1", "amount": 100.0, "idempotency_key": "k1"},
        {"id": "recB", "merchant_id": "M1", "amount": 200.0, "idempotency_key": "k1"},
        {"id": "recC", "merchant_id": "M2", "amount": 50.0, "idempotency_key": "k2"}
    ]
    result = verify_idempotency(records)
    assert result['duplicates'] == []
    assert result['conflicts'] == ['recB']
    assert result['merchant_totals'] == {'M1': 100.0, 'M2': 50.0}

def test_duplicate_and_conflict():
    records = [
        {"id": "r1", "merchant_id": "M1", "amount": 100.0, "idempotency_key": "k1"},
        {"id": "r2", "merchant_id": "M1", "amount": 100.0, "idempotency_key": "k1"},
        {"id": "r3", "merchant_id": "M1", "amount": 200.0, "idempotency_key": "k2"},
        {"id": "r4", "merchant_id": "M1", "amount": 50.0, "idempotency_key": "k2"}
    ]
    result = verify_idempotency(records)
    assert result['duplicates'] == ['r2']
    assert result['conflicts'] == ['r4']
    assert result['merchant_totals'] == {'M1': 300.0}  # 100 + 200

def test_invalid_input_not_array():
    with pytest.raises(ValueError, match="Input must be a JSON array"):
        verify_idempotency({"not": "array"})

def test_missing_field():
    records = [{"id": "x", "merchant_id": "M1", "amount": 10}]  # missing idempotency_key
    with pytest.raises(ValueError, match="missing field: idempotency_key"):
        verify_idempotency(records)

def test_multiple_merchants():
    records = [
        {"id": "a", "merchant_id": "M1", "amount": 10.0, "idempotency_key": "k1"},
        {"id": "b", "merchant_id": "M1", "amount": 20.0, "idempotency_key": "k2"},
        {"id": "c", "merchant_id": "M2", "amount": 30.0, "idempotency_key": "k3"},
        {"id": "d", "merchant_id": "M2", "amount": 40.0, "idempotency_key": "k4"}
    ]
    result = verify_idempotency(records)
    assert result['merchant_totals'] == {'M1': 30.0, 'M2': 70.0}
