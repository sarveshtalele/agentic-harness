import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Import the module dynamically from scripts folder
script_dir = Path(__file__).parent
spec = importlib.util.spec_from_file_location("invoice_total_calculator", script_dir / "invoice_total_calculator.py")
calc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)

class TestValidation:
    def test_valid_input(self):
        data = {
            "lines": [
                {"description": "item1", "quantity": 2, "unit_price": 10.00},
                {"description": "item2", "quantity": 1, "unit_price": 5.50}
            ],
            "discount_percent": 10,
            "tax_percent": 20
        }
        input_text = json.dumps(data)
        result = calc.process_input(input_text)
        assert 'error' not in result
        assert result['subtotal'] == 25.5
        assert result['discount'] == 2.55
        assert result['tax'] == 4.59
        assert result['total'] == 27.54

    def test_negative_quantity_error(self):
        data = {
            "lines": [{"description": "bad", "quantity": -1, "unit_price": 10.0}],
            "discount_percent": 0,
            "tax_percent": 0
        }
        input_text = json.dumps(data)
        result = calc.process_input(input_text)
        assert 'error' in result
        assert 'quantity' in result['error']

    def test_discount_percent_out_of_range(self):
        data = {
            "lines": [{"description": "valid", "quantity": 1, "unit_price": 100.0}],
            "discount_percent": 101,
            "tax_percent": 0
        }
        input_text = json.dumps(data)
        result = calc.process_input(input_text)
        assert 'error' in result
        assert 'discount_percent' in result['error']

    def test_tax_percent_out_of_range(self):
        data = {
            "lines": [{"description": "valid", "quantity": 1, "unit_price": 100.0}],
            "discount_percent": 0,
            "tax_percent": 51
        }
        input_text = json.dumps(data)
        result = calc.process_input(input_text)
        assert 'error' in result
        assert 'tax_percent' in result['error']

    def test_negative_unit_price_error(self):
        data = {
            "lines": [{"description": "negative", "quantity": 1, "unit_price": -0.01}],
            "discount_percent": 0,
            "tax_percent": 0
        }
        input_text = json.dumps(data)
        result = calc.process_input(input_text)
        assert 'error' in result
        assert 'unit_price' in result['error']

    def test_lines_missing(self):
        data = {"discount_percent": 0, "tax_percent": 0}
        input_text = json.dumps(data)
        result = calc.process_input(input_text)
        assert 'error' in result
        assert 'lines' in result['error']

    def test_invalid_json(self):
        result = calc.process_input('not json')
        assert 'error' in result
        assert 'invalid' in result['error']