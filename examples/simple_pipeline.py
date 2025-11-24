"""Run a small ingest→search example using the sample markdown file."""
from pathlib import Path

from ingest import markdown_html
from serve.api import SearchService


def main():
    service = SearchService()
    sample_path = Path(__file__).parent.parent / "tests" / "data" / "sample.md"
    doc = markdown_html.parse_markdown(sample_path.read_text(), doc_id="example-doc")
    service.ingest(doc)
    results = service.search("finance research")
    for res in results:
        print(f"Score: {res['score']:.3f} | Chunk: {res['chunk_id']} | Text: {res['text'][:80]}...")


if __name__ == "__main__":
    main()
