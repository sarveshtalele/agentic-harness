import sys
from invoice import process_invoice

def main():
    input_text = sys.stdin.read()
    output = process_invoice(input_text)
    print(output)

if __name__ == "__main__":
    main()
