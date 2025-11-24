from pathlib import Path

from ingest import docx, loader, markdown_html, pdf, pptx


def test_markdown_parser_blocks():
    content = Path("tests/data/sample.md").read_text()
    doc = markdown_html.parse_markdown(content, doc_id="md-doc")
    assert doc.source_type == "md"
    assert any(b.type == "heading" for b in doc.blocks)
    assert any(b.type == "table" for b in doc.blocks)
    assert any(b.type == "code" for b in doc.blocks)


def test_pdf_parser_blocks():
    content = Path("tests/data/sample.pdf.txt").read_text()
    doc = pdf.parse_pdf(content, doc_id="pdf-doc")
    assert any(b.type == "table" for b in doc.blocks)
    assert any(b.type == "figure" for b in doc.blocks)


def test_docx_parser_blocks():
    content = Path("tests/data/sample.docx.txt").read_text()
    doc = docx.parse_docx(content, doc_id="docx-doc")
    assert any(b.type == "heading" for b in doc.blocks)
    assert any(b.type == "list_item" for b in doc.blocks)


def test_pptx_parser_blocks():
    content = Path("tests/data/sample.pptx.txt").read_text()
    doc = pptx.parse_pptx(content, doc_id="pptx-doc")
    assert any(b.page_no == 1 for b in doc.blocks)
    assert any(b.type == "list_item" for b in doc.blocks)


def test_loader_selects_parser():
    path = Path("tests/data/sample.md")
    doc = loader.load_document(str(path))
    assert doc.doc_id
    assert doc.source_type == "md"
