"""Ingest the Studydata markdown files and run sample RAG queries."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

from ingest import markdown_html
from serve.api import SearchService


def ingest_studydata(service: SearchService, data_dir: Path, limit: int | None = None) -> None:
    paths = sorted(data_dir.glob("*.md"))
    if limit:
        paths = paths[:limit]
    for path in paths:
        content = path.read_bytes().decode("utf-8", errors="replace")
        doc = markdown_html.parse_markdown(content, path=path, doc_id=path.stem)
        service.ingest(doc)


def format_result(result: dict) -> str:
    metadata = result["metadata"]
    doc_label = metadata.title or metadata.doc_id
    return f"({metadata.doc_id}) [{result['score']:.3f}] {doc_label}: {result['text'][:140]}..."


def run_queries(service: SearchService, queries: Iterable[str], top_n: int = 3) -> List[str]:
    outputs: List[str] = []
    for query in queries:
        outputs.append(f"\n[Query] {query}")
        for res in service.search(query, top_n=top_n):
            outputs.append(f"  - {format_result(res)}")
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent / "Studydata",
        help="Directory containing Studydata markdown files",
    )
    parser.add_argument(
        "--query",
        action="append",
        help="Custom query to run; can be specified multiple times. Defaults to four Studydata-related questions.",
    )
    parser.add_argument(
        "--limit-docs",
        type=int,
        help="Ingest only the first N markdown files (alphabetical) to speed up quick tests.",
    )
    parser.add_argument("--top-n", type=int, default=3, help="Number of results to display per query")
    args = parser.parse_args()

    queries = args.query or [
        "DGA는 무엇이며 왜 중요한가?",
        "초기 운전 변압기의 수소(H2) 농도 기준은?",
        "C2H2로 식별되는 D2 결함이 나타나면 무엇을 해야 하나요?",
        "부분방전(PD)은 어떻게 정의되며 모니터링이 필요한 이유는?",
    ]

    service = SearchService()
    ingest_studydata(service, args.data_dir, limit=args.limit_docs)

    for line in run_queries(service, queries, top_n=args.top_n):
        print(line)


if __name__ == "__main__":
    main()
