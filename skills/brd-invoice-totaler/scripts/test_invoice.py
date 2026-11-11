import json
import pytest
from invoice import (
    round_half_up,
    validate_input,
    compute_totals,
    process_invoice
)


def test_round_half_up():
    assert round_half_up(10.555) == 10.56
    assert round_half_up(3.333) == 3.33
    assert round_half_up(12.345) == 12.35
    assert round_half_up(0.001) == 0.00
    assert round_half_up(0.005) == 0.01
    assert round_half_up(1.999) == 2.00
    assert round_half_up(2.5) == 2.5  # already exact


def test_validate_input_valid():
    data = {
        "lines": [{"description": "A", "quantity": 2, "unit_price": 10.00}],
        "discount_percent": 10,
        "tax_percent": 20
    }
    valid, field = validate_input(data)
    assert valid
    assert field is None


def test_validate_input_negative_quantity():
    data = {
        "lines": [{"description": "Bad", "quantity": -1, "unit_price": 10.00}],
        "discount_percent": 0,
        "tax_percent": 0
    }
    valid, field = validate_input(data)
    assert not valid
    assert field == "quantity"


def test_validate_input_negative_unit_price():
    data = {
        "lines": [{"description": "Bad", "quantity": 1, "unit_price": -5}],
        "discount_percent": 0,
        "tax_percent": 0
    }
    valid, field = validate_input(data)
    assert not valid
    assert field == "quantity"


def test_validate_input_discount_out_of_range():
    data = {
        "lines": [{"description": "Valid", "quantity": 1, "unit_price": 100}],
        "discount_percent": 150,
        "tax_percent": 10
    }
    valid, field = validate_input(data)
    assert not valid
    assert field == "discount_percent"


def test_validate_input_tax_out_of_range():
    data = {
        "lines": [{"description": "Valid", "quantity": 1, "unit_price": 100}],
        "discount_percent": 0,
        "tax_percent": 60
    }
    valid, field = validate_input(data)
    assert not valid
    assert field == "tax_percent"


def test_compute_totals_simple():
    data = {
        "lines": [{"description": "A", "quantity": 2, "unit_price": 10.00},
                   {"description": "B", "quantity": 1, "unit_price": 5.50}],
        "discount_percent": 10,
        "tax_percent": 20
    }
    result = compute_totals(data)
    assert result["subtotal"] == 25.50
    assert result["discount"] == 2.55
    assert result["tax"] == 4.59
    assert result["total"] == 27.54


def test_compute_totals_zero_quantity():
    data = {
        "lines": [{"description": "Zero", "quantity": 0, "unit_price": 100}],
        "discount_percent": 0,
        "tax_percent": 0
    }
    result = compute_totals(data)
    assert result["subtotal"] == 0.00
    assert result["discount"] == 0.00
    assert result["tax"] == 0.00
    assert result["total"] == 0.00


def test_compute_totals_high_percents():
    data = {
        "lines": [{"description": "High", "quantity": 1, "unit_price": 100}],
        "discount_percent": 50,
        "tax_percent": 50
    }
    result = compute_totals(data)
    assert result["subtotal"] == 100.00
    assert result["discount"] == 50.00
    assert result["tax"] == 25.00
    assert result["total"] == 75.00


def test_process_invoice_valid():
    input_str = '{"lines": [{"description": "A", "quantity": 2, "unit_price": 10.00}, {"description": "B", "quantity": 1, "unit_price": 5.50}], "discount_percent": 10, "tax_percent": 20}'
    output = process_invoice(input_str)
    data = json.loads(output)
    assert data["subtotal"] == 25.50
    assert data["discount"] == 2.55
    assert data["tax"] == 4.59
    assert data["total"] == 27.54


def test_process_invoice_error_negative_quantity():
    input_str = '{"lines": [{"description": "Bad", "quantity": -1, "unit_price": 10.00}], "discount_percent": 0, "tax_percent": 0}'
    output = process_invoice(input_str)
    data = json.loads(output)
    assert "error" in data
    assert data["field"] == "quantity"
    assert data.get("subtotal") is None


def test_process_invoice_error_discount_percent():
    input_str = '{"lines": [{"description": "A", "quantity": 1, "unit_price": 100}], "discount_percent": 150, "tax_percent": 10}'
    output = process_invoice(input_str)
    data = json.loads(output)
    assert "error" in data
    assert data["field"] == "discount_percent"


def test_process_invoice_error_tax_percent():
    input_str = '{"lines": [{"description": "A", "quantity": 1, "unit_price": 100}], "discount_percent": 0, "tax_percent": 60}'
    output = process_invoice(input_str)
    data = json.loads(output)
    assert "error" in data
    assert data["field"] == "tax_percent"
