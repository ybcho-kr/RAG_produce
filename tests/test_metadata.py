from pathlib import Path

from chunk.parent_child import build_parents
from ingest import markdown_html
from metadata.enrich import _domain_tags


def test_metadata_contains_required_fields():
    content = Path("tests/data/sample.md").read_text()
    doc = markdown_html.parse_markdown(content, doc_id="md-doc")
    parents = build_parents(doc)
    parent = parents[0]
    assert parent.metadata.doc_id == doc.doc_id
    assert parent.metadata.chunk_role == "parent"
    assert parent.metadata.section_path is not None


def test_domain_tag_extraction():
    tags = _domain_tags("Finance engineering legal text")
    assert tags == ["finance", "engineering", "legal"]
