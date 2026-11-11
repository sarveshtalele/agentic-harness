#!/usr/bin/env python3
"""
Markdown to DOCX converter.
Converts a Markdown file into a Word DOCX document.
"""

import sys
import re
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


def parse_markdown(content):
    """
    Parse Markdown content and return a list of (type, data) tuples.
    Supported types: heading, paragraph, bullet, number, table, code_block, unconverted.
    """
    lines = content.split('\n')
    elements = []
    i = 0
    unconverted = []
    in_code_block = False
    code_buffer = []
    code_lang = ''
    
    while i < len(lines):
        line = lines[i]
        
        # Check for fenced code block start/end
        if line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_buffer = []
                code_lang = line[3:].strip()
                i += 1
                continue
            else:
                elements.append(('code_block', '\n'.join(code_buffer), code_lang))
                in_code_block = False
                i += 1
                continue
        
        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue
        
        # Heading
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            elements.append(('heading', text, level))
            i += 1
            continue
        
        # Table (simple)
        if '|' in line and line.count('|') >= 2:
            # Check if next line is separator
            if i + 1 < len(lines) and re.match(r'^[|\s:-]+$', lines[i+1]):
                # Start of table
                table_rows = []
                header_row = [cell.strip() for cell in line.split('|') if cell.strip() != '']
                # Skip separator line
                i += 2
                while i < len(lines) and '|' in lines[i]:
                    row = [cell.strip() for cell in lines[i].split('|') if cell.strip() != '']
                    table_rows.append(row)
                    i += 1
                elements.append(('table', header_row, table_rows))
                continue
        
        # Bullet list
        bullet_match = re.match(r'^[-*+]\s+(.+)$', line)
        if bullet_match:
            text = bullet_match.group(1)
            elements.append(('bullet', text))
            i += 1
            continue
        
        # Numbered list
        number_match = re.match(r'^\d+\.\s+(.+)$', line)
        if number_match:
            text = number_match.group(1)
            elements.append(('number', text))
            i += 1
            continue
        
        # Empty line
        if line.strip() == '':
            i += 1
            continue
        
        # Fallback: paragraph (or unconverted)
        # Check for blockquote or HTML
        if line.startswith('>') or line.startswith('<'):
            elements.append(('unconverted', line))
            unconverted.append(line)
        else:
            elements.append(('paragraph', line))
        i += 1
    
    return elements, unconverted


def add_paragraph_with_formatting(doc, text):
    """
    Add a paragraph to doc, applying bold (**) and italic (*) formatting.
    Also handles inline code (`).
    """
    # Split on inline code, bold, italic patterns while preserving order
    # Use regex to find patterns: **text** or *text* or `text`
    pattern = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')
    parts = pattern.split(text)
    para = doc.add_paragraph()
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            run = para.add_run(part[2:-2])
            run.bold = True
        elif part.startswith('*') and part.endswith('*'):
            run = para.add_run(part[1:-1])
            run.italic = True
        elif part.startswith('`') and part.endswith('`'):
            run = para.add_run(part[1:-1])
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
        else:
            para.add_run(part)
    return para


def convert_to_docx(content, output_path):
    """
    Convert Markdown string content to a DOCX file at output_path.
    Returns a list of unconverted element strings (may be empty).
    """
    doc = Document()
    
    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    elements, unconverted = parse_markdown(content)
    
    for element in elements:
        if element[0] == 'heading':
            _, text, level = element
            doc.add_heading(text, level=level)
        elif element[0] == 'paragraph':
            _, text = element
            add_paragraph_with_formatting(doc, text)
        elif element[0] == 'bullet':
            _, text = element
            para = doc.add_paragraph(text, style='List Bullet')
        elif element[0] == 'number':
            _, text = element
            para = doc.add_paragraph(text, style='List Number')
        elif element[0] == 'table':
            _, header, rows = element
            num_cols = len(header)
            if not rows:
                table = doc.add_table(rows=1, cols=num_cols)
                for j, cell_text in enumerate(header):
                    table.rows[0].cells[j].text = cell_text
            else:
                table = doc.add_table(rows=1 + len(rows), cols=num_cols)
                for j, cell_text in enumerate(header):
                    table.rows[0].cells[j].text = cell_text
                for i, row in enumerate(rows):
                    for j, cell_text in enumerate(row):
                        if j < num_cols:
                            table.rows[i+1].cells[j].text = cell_text
                        else:
                            break
        elif element[0] == 'code_block':
            _, code, lang = element
            para = doc.add_paragraph()
            run = para.add_run(code)
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
            # Add light grey shading
            shading = run._element.get_or_add_rPr()
            shd = shading.makeelement(qn('w:shd'), {
                qn('w:val'): 'clear',
                qn('w:color'): 'auto',
                qn('w:fill'): 'F0F0F0',
            })
            shading.append(shd)
            para.paragraph_format.space_before = Pt(6)
            para.paragraph_format.space_after = Pt(6)
    
    doc.save(output_path)
    return unconverted


def main():
    """Entry point when run as script."""
    if len(sys.argv) < 2:
        print("Usage: md_to_docx.py <input.md> [output.docx]")
        print("If output.docx is omitted, saves to output.docx")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'output.docx'
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: file '{input_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    if not content:
        # Create empty DOCX
        doc = Document()
        doc.save(output_path)
        print(f"Empty DOCX created at {output_path}")
        print("Input file is empty.")
        sys.exit(0)
    
    unconverted = convert_to_docx(content, output_path)
    
    print(f"Docx file created at {output_path}")
    if unconverted:
        print("Unconverted elements:")
        for elem in unconverted:
            print(f"  - {elem}")
    else:
        print("Conversion successful – no unconverted elements.")


if __name__ == '__main__':
    main()
