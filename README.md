# RAG 생성 파이프라인

이 저장소는 `PLAN.md`에 정의된 엔드투엔드 파이프라인을 구현하며, 수집, 스키마 검증, 청킹, 메타데이터 보강, 하이브리드 검색, 재랭킹, 서빙, 평가 도구를 포함합니다. 구현은 경량이고 결정적이라 독립적으로 동작할 수 있습니다.

## 설치

The stack uses only the Python standard library plus `pytest` for tests. Create a virtual environment if desired and install test dependencies from `requirements.txt`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 수집 및 인덱스 생성

`SearchService`를 사용해 형식별 파서를 통해 문서를 불러오고, 자동으로 **BGE-m3 스타일 임베딩**을 활용한 밀집/희소/멀티벡터 인덱스를 구축할 수 있습니다:

```bash
python -m serve.api tests/data/sample.md "finance research"
```

또는 샘플 파이프라인 스크립트를 실행하세요:

```bash
python examples/simple_pipeline.py
```

### BGE-m3 스텁 임베더 출력
- **Dense**: 본문 단위 임베딩으로 1차 벡터 검색에 사용됩니다 (`index/dense.py`).
- **Lexical weights**: 토큰별 가중치로 BM25 대체 희소 매칭에 활용됩니다 (`index/sparse.py`, `use_lexical_weights=True`).
- **ColBERT-style token vectors**: 토큰 단위 멀티벡터를 생성해 Late Interaction 점수 계산에 사용됩니다 (`index/multivector.py`).

## 테스트 실행

모든 단위 및 통합 테스트를 실행합니다:

```bash
pytest
```

## 평가

오프라인 평가지표는 `src/eval/metrics.py`에 있습니다. 평가 흐름에 대한 간단한 README는 `eval/README.md`에, 테스트 지침은 `tests/eval/README.md`에 있습니다.

## 디렉터리 구조

- `src/ingest/`: 형식별 파서 및 로더 유틸리티
- `src/schema/`: 스키마 데이터클래스와 검증기
- `src/chunk/`: 상위/하위 청킹 로직
- `src/metadata/`: 메타데이터 보강 및 태깅
- `src/index/`: 밀집(`dense.py`), 희소(`sparse.py`), 멀티벡터(`multivector.py`) 인덱서와 결정적 BGE-m3 스텁 임베더(`embedder.py`)
- `src/retrieval/`: RRF 융합을 사용하는 하이브리드 검색
- `src/rerank/`: 크로스 인코더 스타일 재랭커
- `src/serve/`: 검색 서비스 진입점
- `src/eval/`: 오프라인 지표 헬퍼
- `tests/`: 샘플 픽스처가 포함된 단위 및 통합 테스트
- `examples/`: 엔드투엔드 사용 예제

## 엔드투엔드 흐름

1. **수집**: `ingest.loader.load_document(path)`가 확장자에 따라 파서를 선택하고, `schema.validators`로 검증된 `DocumentBlocks`를 생성합니다.
2. **청킹**: `chunk.parent_child.chunk_document`가 필요한 메타데이터와 경계 정렬을 갖춘 상위/하위 청크를 만듭니다.
3. **인덱싱**: `SearchService.ingest`가 하위 청크를 BGE-m3 임베더로 변환해 밀집 벡터, 토큰별 멀티벡터(ColBERT 스타일), 렉시컬 가중치 희소 표현을 각각 인덱싱합니다.
4. **검색**: `HybridRetriever`가 밀집, 희소(lexical weight), 멀티벡터 결과를 RRF로 융합해 후보를 반환합니다.
5. **재랭킹 및 서빙**: `CrossEncoderReranker`가 후보를 정렬하고, `SearchService.search`가 토큰 예산 내에서 부모(±1 형제)를 확장하여 최종 컨텍스트를 반환합니다.
6. **평가**: `src/eval/metrics.py`의 recall@k, nDCG@k, MRR 등의 지표를 사용합니다. 샘플 명령은 `tests/eval/README.md`를 참고하세요.
