import json


def round_half_up(value, decimals=2):
    """Round a number to the given number of decimals using half-up rounding."""
    multiplier = 10 ** decimals
    # Shift decimal, add 0.5, floor for positive, subtract 0.5, ceiling for negative
    import math
    # Use Python's built-in rounding with ROUND_HALF_UP
    # Python's default round() uses bankers' rounding (half to even) for floats.
    # We implement half-up explicitly.
    if value >= 0:
        return math.floor(value * multiplier + 0.5) / multiplier
    else:
        return math.ceil(value * multiplier - 0.5) / multiplier


def validate_input(data):
    """Validate the parsed JSON input. Returns (is_valid, error_field)."""
    if "lines" not in data or not isinstance(data["lines"], list):
        return False, "lines"

    for line in data["lines"]:
        if not isinstance(line, dict):
            return False, "lines"
        if "quantity" not in line or "unit_price" not in line:
            return False, "quantity"
        qty = line["quantity"]
        price = line["unit_price"]
        if not isinstance(qty, (int, float)) or not isinstance(price, (int, float)):
            return False, "quantity"
        if qty < 0 or price < 0:
            return False, "quantity"

    if "discount_percent" not in data:
        return False, "discount_percent"
    discount = data["discount_percent"]
    if not isinstance(discount, (int, float)):
        return False, "discount_percent"
    if discount < 0 or discount > 100:
        return False, "discount_percent"

    if "tax_percent" not in data:
        return False, "tax_percent"
    tax = data["tax_percent"]
    if not isinstance(tax, (int, float)):
        return False, "tax_percent"
    if tax < 0 or tax > 50:
        return False, "tax_percent"

    return True, None


def compute_totals(data):
    """Compute invoice totals from validated data. Returns a dict with subtotal, discount, tax, total."""
    subtotal = sum(line["quantity"] * line["unit_price"] for line in data["lines"])
    subtotal = round_half_up(subtotal)

    discount_percent = data["discount_percent"]
    discount = round_half_up(subtotal * discount_percent / 100)

    discounted = subtotal - discount
    discounted = round_half_up(discounted)

    tax_percent = data["tax_percent"]
    tax = round_half_up(discounted * tax_percent / 100)

    total = round_half_up(discounted + tax)

    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": total
    }


def process_invoice(json_string):
    """Main processing function: takes a JSON string, returns result JSON string."""
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}", "field": ""})

    is_valid, error_field = validate_input(data)
    if not is_valid:
        return json.dumps({"error": f"Invalid value for field '{error_field}'", "field": error_field})

    result = compute_totals(data)
    return json.dumps(result)
