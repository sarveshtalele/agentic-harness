import sys
from invoice_total_calculator import process_input
import json

def main():
    input_text = sys.stdin.read()
    result = process_input(input_text)
    sys.stdout.write(json.dumps(result))

if __name__ == '__main__':
    main()