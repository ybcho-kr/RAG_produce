from schema.validators import ChildChunk, Metadata
from rerank.cross_encoder import CrossEncoderReranker


class DummyChild(ChildChunk):
    pass


def make_child(text: str) -> ChildChunk:
    metadata = Metadata(
        doc_id="d1",
        parent_id="p1",
        chunk_id=f"c-{len(text)}",
        source_type="md",
        title=None,
        section_path=[],
        chunk_role="child",
        page_no=None,
        slide_no=None,
        bbox=None,
        created_at=None,
        updated_at=None,
        version=None,
        domain_tags=None,
    )
    return ChildChunk(
        chunk_id=f"c-{len(text)}",
        parent_id="p1",
        doc_id="d1",
        text=text,
        start_block="b1",
        end_block="b1",
        order=0,
        metadata=metadata,
    )


def test_reranker_orders_by_overlap():
    reranker = CrossEncoderReranker()
    child1 = make_child("finance data and research goals" * 5)
    child2 = make_child("unrelated text with few overlaps" * 5)
    scores = reranker.score("finance research", [child2, child1])
    assert scores[0][0] == child1
