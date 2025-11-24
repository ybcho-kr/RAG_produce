"""Generate synthetic Korean documents for bulk vector DB ingest and search tests."""
from __future__ import annotations

import argparse
import random
from typing import Iterable, List

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ingest.loader import DocumentBuilder
from schema.validators import DocumentBlocks
from serve.api import SearchService


THEMES = [
    "금융 시장 동향",
    "기후 변화와 에너지",
    "인공지능 산업 전망",
    "스마트 도시와 교통",
    "보건 의료 혁신",
    "문화 예술 정책",
    "우주 산업",
    "교육 기술",
]

SENTENCE_TEMPLATES = [
    "{theme}에 관한 현장의 목소리는 다양한 이해관계자들의 협력 필요성을 강조한다.",
    "최근 데이터는 {theme}에서 장기적인 투자와 규제 개선이 병행되어야 함을 보여준다.",
    "전문가들은 {theme} 관련 의사결정에서 투명성과 지속 가능성이 핵심이라고 분석한다.",
    "{theme}의 성공적인 확산을 위해서는 지역 사회의 참여와 교육이 필수적이다.",
    "국제 사례를 보면 {theme}에서 표준화와 상호 운용성 확보가 큰 과제로 드러난다.",
    "정부와 기업은 {theme}의 잠재력을 실현하기 위한 공동 로드맵을 마련하고 있다.",
    "{theme}은(는) 경제적 파급 효과 외에도 사회적 신뢰와 윤리 기준을 동반해야 한다.",
    "현장 실증 결과, {theme} 관련 파일럿 프로젝트는 확장성을 고려한 설계가 중요하다.",
    "{theme} 영역에서 데이터를 안전하게 활용하기 위한 보안 및 개인정보 보호 전략이 필요하다.",
    "이 보고서는 {theme}의 위험 요인을 정리하고 대응 방안을 제시한다.",
]


def build_paragraph(theme: str, sentences_per_paragraph: int, rng: random.Random) -> str:
    sentences = [rng.choice(SENTENCE_TEMPLATES).format(theme=theme) for _ in range(sentences_per_paragraph)]
    extra_detail = (
        "추가 분석에서는 현장의 정성적 인터뷰와 정량적 지표를 결합해 신뢰도를 높였다. "
        "이는 검색 테스트 시 다양한 키워드 매칭을 유도하기 위한 의도적인 중복 서술이다."
    )
    sentences.append(extra_detail)
    return " ".join(sentences)


def build_document(
    doc_id: str,
    theme: str,
    paragraphs_per_doc: int,
    sentences_per_paragraph: int,
    rng: random.Random,
) -> DocumentBlocks:
    builder = DocumentBuilder(source_type="md", title=f"{theme} 종합 보고서")
    order = 0
    order += 1
    builder.add_block(doc_id, "heading", f"{theme} 개요", order, level=1)
    for idx in range(paragraphs_per_doc):
        section_title = f"세부 분석 {idx + 1}"
        order += 1
        builder.add_block(doc_id, "heading", section_title, order, level=2)
        paragraph = build_paragraph(theme, sentences_per_paragraph, rng)
        order += 1
        builder.add_block(doc_id, "paragraph", paragraph, order)
    return builder.build(doc_id)


def generate_documents(
    count: int,
    paragraphs_per_doc: int,
    sentences_per_paragraph: int,
    seed: int,
) -> List[DocumentBlocks]:
    rng = random.Random(seed)
    documents: List[DocumentBlocks] = []
    for idx in range(count):
        theme = THEMES[idx % len(THEMES)]
        doc_id = f"korean-doc-{idx + 1:04d}"
        documents.append(build_document(doc_id, theme, paragraphs_per_doc, sentences_per_paragraph, rng))
    return documents


def ingest_documents(service: SearchService, documents: Iterable[DocumentBlocks]) -> None:
    for doc in documents:
        service.ingest(doc)


def run_queries(service: SearchService, queries: List[str], top_n: int) -> None:
    for query in queries:
        print(f"\n=== 검색어: {query} ===")
        for result in service.search(query, top_n=top_n):
            preview = result["text"][:120].replace("\n", " ")
            print(f"[{result['score']:.4f}] {preview}...")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=int, default=20, help="생성할 문서 수")
    parser.add_argument("--paragraphs", type=int, default=8, help="문서당 단락 수")
    parser.add_argument("--sentences", type=int, default=5, help="단락당 문장 수")
    parser.add_argument("--seed", type=int, default=13, help="재현 가능한 결과를 위한 시드")
    parser.add_argument("--top-n", type=int, default=3, help="질의당 반환할 상위 결과 수")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    documents = generate_documents(
        count=args.docs,
        paragraphs_per_doc=args.paragraphs,
        sentences_per_paragraph=args.sentences,
        seed=args.seed,
    )
    service = SearchService()
    ingest_documents(service, documents)
    print(f"총 {len(documents)}개 문서, {len(service.children)}개 하위 청크가 인덱싱되었습니다.")
    sample_queries = [
        "에너지 전환 투자 전략",
        "도시 교통 데이터 거버넌스",
        "의료 AI 윤리 기준",
        "금융 시장 리스크 관리",
    ]
    run_queries(service, sample_queries, top_n=args.top_n)


if __name__ == "__main__":
    main()
