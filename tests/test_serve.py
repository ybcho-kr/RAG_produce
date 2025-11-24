from pathlib import Path

from ingest import markdown_html
from serve.api import SearchService


def test_search_service_end_to_end():
    service = SearchService()
    content = Path("tests/data/sample.md").read_text()
    doc = markdown_html.parse_markdown(content, doc_id="md-doc-end")
    service.ingest(doc)
    results = service.search("finance engineering")
    assert results, "Search should return results"
    for res in results:
        assert "text" in res
        assert res["metadata"].chunk_role == "child"
