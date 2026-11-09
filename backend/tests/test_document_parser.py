"""Test document parsing service."""

import io
import docx
import pytest

from app.services.parsing.parser import parse_document, parse_docx


def test_parse_docx_content():
    doc = docx.Document()
    doc.add_paragraph("This is the first paragraph of brand guidelines.")
    doc.add_paragraph("Always protect corporate assets.")

    stream = io.BytesIO()
    doc.save(stream)
    content = stream.getvalue()

    text, doc_type = parse_document("guidelines.docx", content)
    assert doc_type == "docx"
    assert "first paragraph" in text
    assert "corporate assets" in text


def test_parse_text_content():
    sample = "Simple press release draft content."
    text, doc_type = parse_document("press_release.txt", sample.encode("utf-8"))
    assert doc_type == "text"
    assert text == sample

