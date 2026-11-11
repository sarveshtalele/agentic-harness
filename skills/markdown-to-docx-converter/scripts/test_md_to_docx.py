#!/usr/bin/env python3
"""
Pytest tests for the markdown-to-docx converter.
"""

import sys
import os
import tempfile
import pytest

# Ensure script is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts import md_to_docx


def test_basic_heading_paragraph():
    """Test that headings and paragraphs are converted."""
    content = "# Heading\n\nA paragraph."
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_bold_italic():
    """Test bold and italic formatting."""
    content = "This is **bold** and *italic*."
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_bullet_list():
    """Test bulleted list."""
    content = "- Item 1\n- Item 2\n- Item 3"
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_numbered_list():
    """Test numbered list."""
    content = "1. First\n2. Second\n3. Third"
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_table():
    """Test table conversion."""
    content = "| A | B |\n|---|---|\n| 1 | 2 |"
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_code_block():
    """Test fenced code block."""
    content = "```python\nprint('hello')\n```"
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_unconverted_blockquote():
    """Test that blockquotes are reported unconverted."""
    content = "> This is a quote\n\nNormal paragraph."
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert len(unconverted) == 1
        assert ">" in unconverted[0]


def test_empty_input():
    """Test empty input file produces empty DOCX."""
    content = ""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'empty.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0  # valid docx has minimum size
        assert unconverted == []


def test_mixed_formatting():
    """Test bold and italic together."""
    content = "**bold and *italic* together**"
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_multilevel_headings():
    """Test h1 through h6."""
    content = ("# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\nParagraph.")
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []


def test_inline_code():
    """Test inline code with backticks."""
    content = "Use `print()` to output."
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test.docx')
        unconverted = md_to_docx.convert_to_docx(content, output_path)
        assert os.path.getsize(output_path) > 0
        assert unconverted == []
