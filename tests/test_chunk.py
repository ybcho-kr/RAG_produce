from pathlib import Path

from chunk.parent_child import chunk_document
from ingest import markdown_html


def test_chunk_document_boundaries():
    content = Path("tests/data/sample.md").read_text()
    doc = markdown_html.parse_markdown(content, doc_id="md-doc")
    parents, children = chunk_document(doc, target_min_tokens=50, target_max_tokens=120)
    assert parents, "parents should be created"
    assert children, "children should be created"
    parent_lookup = {p.parent_id: set(p.block_ids) for p in parents}
    for child in children:
        block_ids = parent_lookup[child.parent_id]
        assert child.start_block in block_ids
        assert child.end_block in block_ids
        assert child.metadata.chunk_role == "child"


def test_semantic_chunking_flag_changes_order():
    content = Path("tests/data/sample.md").read_text()
    doc = markdown_html.parse_markdown(content, doc_id="md-doc2")
    _, children_plain = chunk_document(doc, target_min_tokens=30, target_max_tokens=60, semantic_chunking=False)
    _, children_semantic = chunk_document(doc, target_min_tokens=30, target_max_tokens=60, semantic_chunking=True)
    plain_orders = [c.text for c in children_plain]
    semantic_orders = [c.text for c in children_semantic]
    assert plain_orders != semantic_orders, "semantic chunking should alter grouping"
