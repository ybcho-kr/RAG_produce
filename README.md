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

`SearchService`를 사용해 형식별 파서를 통해 문서를 불러오고, 자동으로 밀집/희소 인덱스를 구축할 수 있습니다:

```bash
python -m serve.api tests/data/sample.md "finance research"
```

또는 샘플 파이프라인 스크립트를 실행하세요:

```bash
python examples/simple_pipeline.py
```

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
- `src/index/`: 밀집 및 희소 인덱서
- `src/retrieval/`: RRF 융합을 사용하는 하이브리드 검색
- `src/rerank/`: 크로스 인코더 스타일 재랭커
- `src/serve/`: 검색 서비스 진입점
- `src/eval/`: 오프라인 지표 헬퍼
- `tests/`: 샘플 픽스처가 포함된 단위 및 통합 테스트
- `examples/`: 엔드투엔드 사용 예제

## 엔드투엔드 흐름

1. **수집**: `ingest.loader.load_document(path)`가 확장자에 따라 파서를 선택하고, `schema.validators`로 검증된 `DocumentBlocks`를 생성합니다.
2. **청킹**: `chunk.parent_child.chunk_document`가 필요한 메타데이터와 경계 정렬을 갖춘 상위/하위 청크를 만듭니다.
3. **인덱싱**: `SearchService.ingest`가 하위 청크를 밀집 및 희소 저장소에 인덱싱합니다.
4. **검색**: `HybridRetriever`가 RRF를 통해 밀집/희소 결과를 융합하고 후보를 반환합니다.
5. **재랭킹 및 서빙**: `CrossEncoderReranker`가 후보를 정렬하고, `SearchService.search`가 토큰 예산 내에서 부모(±1 형제)를 확장하여 최종 컨텍스트를 반환합니다.
6. **평가**: `src/eval/metrics.py`의 recall@k, nDCG@k, MRR 등의 지표를 사용합니다. 샘플 명령은 `tests/eval/README.md`를 참고하세요.
