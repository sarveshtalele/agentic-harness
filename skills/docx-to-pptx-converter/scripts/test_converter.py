import pytest
import os
import tempfile
from docx import Document
from pptx import Presentation
from converter import convert_docx_to_pptx

def create_test_docx(title, headings, bullets_dict, tables):
    """Create a temporary DOCX file for testing."""
    doc = Document()
    # Set title
    if title:
        doc.add_heading(title, level=1)
    # Add headings and bullets
    for h in headings:
        doc.add_heading(h, level=1)
        for b in bullets_dict.get(h, []):
            doc.add_paragraph(b, style='List Bullet')
    # Add tables
    for table_data in tables:
        rows = len(table_data['rows'])
        cols = len(table_data['rows'][0]) if rows else 0
        table = doc.add_table(rows=rows, cols=cols)
        for i, row_data in enumerate(table_data['rows']):
            for j, cell_text in enumerate(row_data):
                table.rows[i].cells[j].text = str(cell_text)
    # Save to temp file
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
    doc.save(tmpfile.name)
    return tmpfile.name

def get_all_text_from_pptx(pptx_path):
    """Return all text from a PPTX file (title + body text only)."""
    prs = Presentation(pptx_path)
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    if para.text.strip():
                        texts.append(para.text.strip())
            if shape.has_chart:
                # For chart, include its title if any, and category/values info
                # We'll check the chart_data title or series name
                if shape.chart.has_title:
                    texts.append(shape.chart.chart_title.text_frame.paragraphs[0].text.strip())
    return texts

def test_title_slide_and_headings():
    """Test that title slide and heading slides are created."""
    title = "Project Overview"
    headings = ["Introduction"]
    bullets = {"Introduction": ["First bullet", "Second bullet"]}
    tables = [{'rows': [['Month', 'Value'], ['Jan', '10'], ['Feb', '20']]}]
    docx_path = create_test_docx(title, headings, bullets, tables)
    pptx_path, warnings = convert_docx_to_pptx(docx_path)
    assert os.path.isfile(pptx_path), "PPTX file not created"
    texts = get_all_text_from_pptx(pptx_path)
    # Check title slide: title text present
    assert "Project Overview" in texts, "title slide"
    # Check content slide heading: "Introduction"
    assert "Introduction" in texts, "Introduction heading"
    # Check bar chart: since we have a chart slide, check that there is a chart object in the PPTX
    prs_check = Presentation(pptx_path)
    chart_found = False
    for slide in prs_check.slides:
        for shape in slide.shapes:
            if shape.has_chart:
                chart_found = True
                break
    assert chart_found, "bar chart"
    os.unlink(docx_path)
    os.unlink(pptx_path)

def test_simple_docx_no_tables():
    """Test with no tables, only a heading."""
    title = ""
    headings = ["Summary"]
    bullets = {"Summary": ["Some bullet"]}
    tables = []
    docx_path = create_test_docx(title, headings, bullets, tables)
    pptx_path, warnings = convert_docx_to_pptx(docx_path)
    assert os.path.isfile(pptx_path)
    texts = get_all_text_from_pptx(pptx_path)
    assert "Summary" in texts
    # Check no chart
    prs_check = Presentation(pptx_path)
    chart_found = False
    for slide in prs_check.slides:
        for shape in slide.shapes:
            if shape.has_chart:
                chart_found = True
                break
    assert not chart_found, "bar chart not expected"
    os.unlink(docx_path)
    os.unlink(pptx_path)

def test_non_numeric_table():
    """Test table with non-numeric second column triggers warning."""
    title = "Test"
    headings = []
    bullets = {}
    tables = [{'rows': [['Item', 'Description'], ['A', 'Hello'], ['B', 'World']]}]
    docx_path = create_test_docx(title, headings, bullets, tables)
    pptx_path, warnings = convert_docx_to_pptx(docx_path)
    # Should have warnings about could not place
    assert any("could not place" in w.lower() or "skipped" in w.lower() or "non-numeric" in w.lower() for w in warnings), "Warning for non-numeric table"
    # Check no chart
    prs_check = Presentation(pptx_path)
    chart_found = False
    for slide in prs_check.slides:
        for shape in slide.shapes:
            if shape.has_chart:
                chart_found = True
                break
    assert not chart_found, "bar chart not expected"
    os.unlink(docx_path)
    os.unlink(pptx_path)

if __name__ == "__main__":
    pytest.main()
