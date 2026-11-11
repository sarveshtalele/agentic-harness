import json
import math

def round_half_up(value, decimals=2):
    multiplier = 10 ** decimals
    return math.floor(value * multiplier + 0.5) / multiplier

def validate_invoice(data):
    if not isinstance(data, dict):
        return "input must be a JSON object"
    if "lines" not in data:
        return "missing field: lines"
    if "discount_percent" not in data:
        return "missing field: discount_percent"
    if "tax_percent" not in data:
        return "missing field: tax_percent"
    if not isinstance(data["lines"], list):
        return "lines must be an array"
    for i, line in enumerate(data["lines"]):
        if not isinstance(line, dict):
            return f"invalid line at index {i}: not an object"
        if "quantity" not in line:
            return f"missing field: quantity in line {i}"
        if "unit_price" not in line:
            return f"missing field: unit_price in line {i}"
        if not isinstance(line["quantity"], (int, float)):
            return f"invalid quantity in line {i}"
        if not isinstance(line["unit_price"], (int, float)):
            return f"invalid unit_price in line {i}"
        if line["quantity"] < 0:
            return f"invalid quantity in line {i}"
        if line["unit_price"] < 0:
            return f"invalid unit_price in line {i}"
    dp = data["discount_percent"]
    tp = data["tax_percent"]
    if not isinstance(dp, (int, float)):
        return "discount_percent must be a number"
    if dp < 0 or dp > 100:
        return "discount_percent out of range (0..100)"
    if not isinstance(tp, (int, float)):
        return "tax_percent must be a number"
    if tp < 0 or tp > 50:
        return "tax_percent out of range (0..50)"
    return None

def compute_invoice(data):
    error = validate_invoice(data)
    if error:
        return {"error": error}
    subtotal = round_half_up(sum(line["quantity"] * line["unit_price"] for line in data["lines"]))
    discount = round_half_up(subtotal * data["discount_percent"] / 100)
    discounted_amount = round_half_up(subtotal - discount)
    tax = round_half_up(discounted_amount * data["tax_percent"] / 100)
    total = round_half_up(discounted_amount + tax)
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": total
    }


def compute_from_json(json_str):
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"invalid JSON: {e}"}
    return compute_invoice(data)
