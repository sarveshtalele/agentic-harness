import sys
from invoice_calculator import compute_from_json

def main():
    input_data = sys.stdin.read()
    result = compute_from_json(input_data)
    print(json.dumps(result))

if __name__ == "__main__":
    import json
    main()
