import sys
import os
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.chart import XL_CHART_TYPE
from pptx.chart.data import CategoryChartData

def convert_docx_to_pptx(docx_path):
    """
    Convert a DOCX file to a PPTX presentation.
    Returns (pptx_path, warnings_list)
    """
    warnings = []
    
    # Validate file exists
    if not os.path.isfile(docx_path):
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")
    
    # Load DOCX
    doc = Document(docx_path)
    prs = Presentation()
    
    # Extract title
    title = ""
    for para in doc.paragraphs:
        if para.style.name == 'Heading 1':
            title = para.text.strip()
            break
    if not title:
        try:
            title = doc.core_properties.title or "Untitled"
        except AttributeError:
            title = "Untitled"
    
    # Create title slide
    slide_layout = prs.slide_layouts[6]  # blank layout
    slide = prs.slides.add_slide(slide_layout)
    title_box = slide.shapes.title
    if title_box is None:
        from pptx.util import Inches
        txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(2))
        tf = txBox.text_frame
        p = tf.add_paragraph()
        p.text = title
        p.font.size = Pt(44)
    else:
        title_box.text = title
    
    # Process headings and bullet points
    # Collect paragraphs grouped by heading 1
    current_heading = None
    current_content = []
    all_content = {}
    
    for para in doc.paragraphs:
        style_name = para.style.name
        text = para.text.strip()
        if style_name == 'Heading 1':
            if current_heading is not None:
                all_content[current_heading] = current_content
            current_heading = text
            current_content = []
        else:
            if current_heading is not None:
                current_content.append(text)
    if current_heading is not None:
        all_content[current_heading] = current_content
    
    # Create slides for each heading
    for heading, bullets in all_content.items():
        slide = prs.slides.add_slide(prs.slide_layouts[1])  # title and content layout
        title_shape = slide.shapes.title
        title_shape.text = heading
        # Add bullets to text body
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.clear()
        for bullet_text in bullets:
            if bullet_text:
                p = tf.add_paragraph()
                p.text = bullet_text
                p.level = 0
                p.font.size = Pt(18)
    
    # Process tables
    # Group tables into a separate slide list after content
    table_slides = []
    for table in doc.tables:
        # Check second column numeric
        if len(table.columns) < 2:
            warnings.append(f"Table with {len(table.columns)} columns skipped (need at least 2)")
            continue
        numeric = True
        for row in table.rows[1:]:  # skip header
            cell = row.cells[1]
            try:
                float(cell.text.strip())
            except ValueError:
                numeric = False
                break
        if not numeric:
            warnings.append(f"Table starting with '{table.rows[0].cells[0].text}' skipped: second column not numeric")
            continue
        # Create chart slide
        labels = []
        values = []
        for row in table.rows[1:]:
            labels.append(row.cells[0].text.strip())
            values.append(float(row.cells[1].text.strip()))
        chart_data = CategoryChartData()
        chart_data.categories = labels
        chart_data.add_series('Values', values)
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        chart = slide.shapes.add_chart(
            XL_CHART_TYPE.BAR_CLUSTERED,
            Inches(1), Inches(1), Inches(8), Inches(6),
            chart_data
        )
    
    # Save PPTX
    base = os.path.splitext(docx_path)[0]
    pptx_path = base + "_presentation.pptx"
    prs.save(pptx_path)
    
    return pptx_path, warnings

if __name__ == "__main__":
    # Example usage for testing
    if len(sys.argv) > 1:
        pptx, warns = convert_docx_to_pptx(sys.argv[1])
        print(f"Output: {pptx}")
        if warns:
            print("Warnings:", warns)
    else:
        print("Usage: python converter.py <docx_path>")
