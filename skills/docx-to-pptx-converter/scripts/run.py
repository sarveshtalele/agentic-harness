import sys
from converter import convert_docx_to_pptx

def main():
    input_text = sys.stdin.read().strip()
    if not input_text:
        print("Error: No input provided.")
        sys.exit(1)
    # Input is the file path to the DOCX
    docx_path = input_text.splitlines()[0]
    pptx_path, warnings = convert_docx_to_pptx(docx_path)
    print(f"Output PPTX: {pptx_path}")
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")

if __name__ == "__main__":
    main()
