import decimal
import json

def round_half_up(value, decimals=2):
    """Round a Decimal to given decimals using half-up rounding."""
    quantize_str = '0.' + '0' * decimals
    return value.quantize(decimal.Decimal(quantize_str), rounding=decimal.ROUND_HALF_UP)

def validate_input(data):
    """Validate the parsed JSON input. Returns None if valid, or an error string if invalid."""
    if 'lines' not in data:
        return 'lines missing'
    if not isinstance(data['lines'], list):
        return 'lines not an array'
    if len(data['lines']) == 0:
        return 'lines empty'
    for i, line in enumerate(data['lines']):
        if not isinstance(line, dict):
            return f'lines[{i}] not an object'
        if 'quantity' not in line:
            return f'lines[{i}] quantity missing'
        if 'unit_price' not in line:
            return f'lines[{i}] unit_price missing'
        qty = line['quantity']
        price = line['unit_price']
        if not isinstance(qty, (int, float)) or not isinstance(price, (int, float)):
            return f'lines[{i}] quantity or unit_price not a number'
        if qty < 0:
            return 'quantity out of range'
        if price < 0:
            return 'unit_price out of range'
    if 'discount_percent' not in data:
        return 'discount_percent missing'
    dp = data['discount_percent']
    if not isinstance(dp, (int, float)):
        return 'discount_percent not a number'
    if dp < 0 or dp > 100:
        return 'discount_percent out of range'
    if 'tax_percent' not in data:
        return 'tax_percent missing'
    tp = data['tax_percent']
    if not isinstance(tp, (int, float)):
        return 'tax_percent not a number'
    if tp < 0 or tp > 50:
        return 'tax_percent out of range'
    return None

def compute_invoice(data):
    """Given validated data, return a dict with subtotal, discount, tax, total."""
    subtotal = decimal.Decimal(0)
    for line in data['lines']:
        qty = decimal.Decimal(str(line['quantity']))
        price = decimal.Decimal(str(line['unit_price']))
        subtotal += qty * price
    discount_percent = decimal.Decimal(str(data['discount_percent']))
    tax_percent = decimal.Decimal(str(data['tax_percent']))
    discount_amount = round_half_up(subtotal * discount_percent / decimal.Decimal(100))
    discounted_amount = subtotal - discount_amount
    tax_amount = round_half_up(discounted_amount * tax_percent / decimal.Decimal(100))
    total = round_half_up(discounted_amount + tax_amount)
    return {
        'subtotal': float(round_half_up(subtotal)),
        'discount': float(discount_amount),
        'tax': float(tax_amount),
        'total': float(total)
    }

def process_input(input_text):
    """Take raw input string, return result dict for JSON serialization."""
    try:
        data = json.loads(input_text)
    except json.JSONDecodeError as e:
        return {'error': 'invalid JSON'}
    error = validate_input(data)
    if error:
        return {'error': error}
    return compute_invoice(data)