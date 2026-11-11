import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from invoice_calculator import compute_invoice, compute_from_json, round_half_up

def test_acceptance():
    data = {
        "lines": [
            {"description": "item1", "quantity": 2, "unit_price": 10.00},
            {"description": "item2", "quantity": 1, "unit_price": 5.50}
        ],
        "discount_percent": 10,
        "tax_percent": 20
    }
    result = compute_invoice(data)
    assert result["subtotal"] == 25.5
    assert result["discount"] == 2.55
    assert result["tax"] == 4.59
    assert result["total"] == 27.54

def test_negative_quantity():
    data = {
        "lines": [{"description": "item1", "quantity": -1, "unit_price": 5.00}],
        "discount_percent": 0,
        "tax_percent": 0
    }
    result = compute_invoice(data)
    assert "error" in result
    assert "quantity" in result["error"]

def test_negative_unit_price():
    data = {
        "lines": [{"description": "item1", "quantity": 1, "unit_price": -5.00}],
        "discount_percent": 0,
        "tax_percent": 0
    }
    result = compute_invoice(data)
    assert "error" in result
    assert "unit_price" in result["error"]

def test_discount_percent_out_of_range_high():
    data = {
        "lines": [{"description": "item1", "quantity": 1, "unit_price": 10.00}],
        "discount_percent": 101,
        "tax_percent": 20
    }
    result = compute_invoice(data)
    assert "error" in result
    assert "discount_percent" in result["error"]

def test_tax_percent_out_of_range_high():
    data = {
        "lines": [{"description": "item1", "quantity": 1, "unit_price": 10.00}],
        "discount_percent": 0,
        "tax_percent": 51
    }
    result = compute_invoice(data)
    assert "error" in result
    assert "tax_percent" in result["error"]

def test_missing_lines():
    data = {"discount_percent": 0, "tax_percent": 0}
    result = compute_invoice(data)
    assert "error" in result
    assert "lines" in result["error"]

def test_missing_field():
    data = {"lines": [], "tax_percent": 0}
    result = compute_invoice(data)
    assert "error" in result
    assert "discount_percent" in result["error"]

def test_invalid_json():
    result = compute_from_json("{invalid")
    assert "error" in result
    assert "JSON" in result["error"]

def test_round_half_up():
    assert round_half_up(2.345, 2) == 2.35
    assert round_half_up(2.344, 2) == 2.34
    assert round_half_up(2.5, 0) == 3

def test_quantity_zero():
    data = {
        "lines": [{"description": "free", "quantity": 0, "unit_price": 100.00}],
        "discount_percent": 0,
        "tax_percent": 0
    }
    result = compute_invoice(data)
    assert "error" not in result
    assert result["subtotal"] == 0.0
    assert result["total"] == 0.0

def test_price_zero():
    data = {
        "lines": [{"description": "free", "quantity": 5, "unit_price": 0.00}],
        "discount_percent": 0,
        "tax_percent": 0
    }
    result = compute_invoice(data)
    assert "error" not in result
    assert result["subtotal"] == 0.0
    assert result["total"] == 0.0
