# 1. 저장소 스캔 요약
- 저장소 구조: 현재 최소 구성이며 `README.md`만 존재하고, 아직 소스 디렉터리나 RAG 파이프라인 코드가 없습니다.
- 진입점 / 모듈: 없음. 수집, 인덱싱, 서빙 컴포넌트가 없습니다.
- 기존 RAG 코드: 없음. 새 구현이 필요합니다.
- 설치/테스트/실행 명령: 정의되어 있지 않습니다. 파이썬 환경(예: `uv` 또는 `requirements.txt`가 추가된 `pip`)을 초기화하고, 모듈이 생성되면 CI용 `make test`를 정의하는 것을 권장합니다.
- 통합 제안: `src/` 아래에 `ingest`, `parsing`, `chunking`, `metadata`, `index`, `retrieval`, `rerank`, `serve` 하위 패키지와 `tests/`를 두는 모듈화된 패키지 구조를 도입합니다. 파이썬 기반 스택을 가정합니다.

# 2. 목표 아키텍처
```
[Ingest] → [블록 스키마로 정규화] → [계층적 청킹(부모/자식)] → [메타데이터 보강]
        → [밀집 인덱스] + [희소 인덱스] → [하이브리드 검색(RRF 융합)] → [재랭킹]
        → [부모 확장] → [서빙 API]
```
- 단계별 입출력:
  - 수집: 입력 = 원시 문서(pdf, md/html, docx, pptx 등); 출력 = 원시 텍스트 + 구조 힌트.
  - 정규화: 입력 = 원시 파싱 결과; 출력 = 정규 블록 스키마를 따르는 `DocumentBlocks` JSON.
  - 청킹: 입력 = `DocumentBlocks`; 출력 = `ParentChunk` + `ChildChunk` 목록과 링크.
  - 메타데이터 보강: 입력 = 청크; 출력 = 필수 메타데이터 필드가 채워지고 검증된 청크.
  - 밀집 인덱싱: 입력 = 텍스트 + 메타데이터가 있는 자식 청크; 출력 = `chunk_id`로 키를 둔 벡터 저장.
  - 희소 인덱싱: 입력 = 자식 청크; 출력 = `chunk_id`로 키를 둔 희소 포스팅/BM25 또는 SPLADE 벡터.
  - 하이브리드 검색: 입력 = 쿼리; 출력 = 융합된 자식 청크 랭킹 후보.
  - 재랭킹: 입력 = 융합 후보; 출력 = 점수가 재정렬된 자식 청크.
  - 부모 확장: 입력 = 재랭킹된 자식 청크; 출력 = 토큰 예산 내에서 이웃 자식이 포함된 부모 수준 컨텍스트.
  - 서빙: 입력 = 쿼리; 출력 = 검색/확장된 컨텍스트와 후속 LLM QA를 위한 관련 메타데이터.

# 3. 정규 스키마
## 3.1 DocumentBlocks(정규화 결과)
| 필드 | 타입 | 필수 | 불변 조건 |
| --- | --- | --- | --- |
| doc_id | string | Y | 소스 문서별로 안정적이어야 함; UUID 또는 결정적 해시. |
| source_type | enum(pdf, md, html, docx, doc, pptx, ppt, txt, other) | Y | 수집 타입과 일치. |
| title | string 또는 null | N | 사용할 수 없으면 null; 추측 금지. |
| blocks | list[Block] | Y | 문서 순서를 유지. |

`Block` 객체:
| 필드 | 타입 | 필수 | 불변 조건 |
| --- | --- | --- | --- |
| block_id | string | Y | 문서 내 고유; 콘텐츠 + 위치의 안정적 해시. |
| type | enum(heading, paragraph, list_item, table, figure, code, equation, footnote) | Y | 파서에서 파생. |
| text | string 또는 null | N | 비텍스트 블록(예: 인라인 텍스트 없는 테이블)은 null; 생성 금지. |
| rich_text | string 또는 null | N | 가능할 때 인라인 포맷/HTML/마크업을 보존. |
| level | int 또는 null | N | 제목/목록 계층에만 사용; 그 외에는 null. |
| parent_id | string 또는 null | N | 중첩 구조 연결(예: 리스트 항목의 상위 리스트); 최상위면 null. |
| order | int | Y | 문서 내 순차 순서. |
| page_no | int 또는 null | N | 페이지/슬라이드 1부터 시작하는 인덱스; 없으면 null. |
| bbox | array[4] of float 또는 null | N | 가능하면 [x1,y1,x2,y2]; 감지되지 않으면 null. |
| table_json | object 또는 null | N | 정규화된 테이블 구조(행/열/셀); 테이블이 아니면 null. |
| table_summary | string 또는 null | N | 테이블 요약이 있으면 포함; 계산하지 않으면 null. |
| figure_caption | string 또는 null | N | 그림이면 캡션 텍스트; 아니면 null. |
| figure_alt | string 또는 null | N | 대체/앵커 텍스트가 있으면 포함. |
| tags | list[string] 또는 null | N | 파서 수준 태그; 없으면 null. |
| created_at | string (ISO8601) 또는 null | N | 파일 메타데이터가 있으면 사용; 없으면 null. |
| updated_at | string (ISO8601) 또는 null | N | 파일 메타데이터가 있으면 사용; 없으면 null. |

## 3.2 부모/자식 청크(청킹 결과)
`ParentChunk`:
| 필드 | 타입 | 필수 | 불변 조건 |
| --- | --- | --- | --- |
| parent_id | string | Y | 최상위 섹션/슬라이드 해시에서 파생. |
| doc_id | string | Y | DocumentBlocks FK. |
| title | string 또는 null | N | 섹션/슬라이드 제목; 없으면 null. |
| section_path | list[string] | Y | 루트 제목부터의 계층; 빈 리스트 허용. |
| text | string | Y | 포함된 블록의 연결 텍스트. |
| block_ids | list[string] | Y | 순서가 있는 블록 id. |
| page_range | tuple(int,int) 또는 null | N | 포함 시 시작~끝 페이지/슬라이드; 없으면 null. |
| metadata | object | Y | 아래 필수 메타데이터 필드를 포함해야 함. |

`ChildChunk`:
| 필드 | 타입 | 필수 | 불변 조건 |
| --- | --- | --- | --- |
| chunk_id | string | Y | parent_id + span의 안정적 해시. |
| parent_id | string | Y | ParentChunk FK. |
| doc_id | string | Y | DocumentBlocks FK. |
| text | string | Y | 목표 200-500 토큰; 블록/문장 경계를 맞춰야 함. |
| start_block | string | Y | 포함되는 첫 block_id. |
| end_block | string | Y | 포함되는 마지막 block_id. |
| order | int | Y | 부모 내 위치. |
| metadata | object | Y | 아래 필수 필드를 포함해야 함. |

## 3.3 메타데이터 필드(부모 및 자식에 적용)
| 필드 | 타입 | 필수 | Null 규칙 |
| --- | --- | --- | --- |
| doc_id | string | Y | null 금지. |
| parent_id | string | 자식에 Y; 부모는 null. |
| chunk_id | string | 자식에 Y; 부모는 null. |
| source_type | enum | Y | 수집 타입에서 파생; null 금지. |
| title | string 또는 null | N | 없으면 null. |
| section_path | list[string] | Y | 빈 리스트 허용. |
| chunk_role | enum(parent, child) | Y | null 금지. |
| page_no | int 또는 null | N | 없으면 null. |
| slide_no | int 또는 null | N | ppt용; 그 외 null. |
| bbox | array[4] 또는 null | N | 없으면 null. |
| created_at | string (ISO8601) 또는 null | N | 메타데이터에 없으면 null. |
| updated_at | string (ISO8601) 또는 null | N | 메타데이터에 없으면 null. |
| version | string 또는 int 또는 null | N | 파일 버전이 있으면 사용; 없으면 null. |
| domain_tags | list[string] 또는 null | N | 자동 추출; 신뢰도가 낮으면 null. |
| page_range | tuple(int,int) 또는 null | N | 알 수 있을 때 부모만 사용. |

- Null 정책: 값을 생성하지 말고, 추출 불가 또는 신뢰도가 낮을 경우 null을 설정합니다. 빈 문자열은 허용하지 않습니다.
- 검증기 위치: `src/schema/validators.py`에 Pydantic/Marshmallow 스키마와 `tests/schema/test_validators.py`의 pytest 커버리지를 추가할 계획입니다.

# 4. 형식별 파싱 계획
## PDF
- 파서 후보: (1) `pymupdf`(빠르고 안정적, bbox 지원), (2) `pdfminer.six`(텍스트 정확, 느림), (3) `unstructured` PDF 로더(레이아웃 처리, 의존성 무거움).
- 선택: 속도와 레이아웃(bbox/페이지)의 균형을 위해 `pymupdf`, 까다로운 인코딩은 `pdfminer.six`로 대체.
- 매핑: 글꼴 크기/스타일 휴리스틱으로 제목 감지; 텍스트 블록에서 단락; 불릿 감지로 list_item; 테이블은 `camelot`/`tabula` 선택; 그림은 이미지+캡션; 코드는 모노스페이스 글꼴; 수식은 인라인 수학 마커; 각주는 위첨자 단서 사용.
- 노이즈 제거: 반복 패턴으로 헤더/푸터 제거; 페이지 번호 제거; 동일한 줄은 중복 제거.
- 테이블: 구조화된 JSON(`rows`, `cells`, `spans`) 추출; `table_summary`에 저장되는 휴리스틱 또는 LLM(외부) 기반 요약 생성.
- 그림: 이미지 주변에서 캡션/alt 텍스트 확보; `figure_caption`, `figure_alt`에 저장; OCR 캡셔닝을 켜면 선택적으로 요약.

## Markdown/HTML
- 파서 후보: (1) `markdown-it-py` + AST, (2) HTML용 `BeautifulSoup`, (3) `mdformat` 파싱.
- 선택: MD AST용 `markdown-it-py`; HTML용 `BeautifulSoup`; 통합 변환기로 블록 변환.
- 매핑: 제목은 `<h1-6>`; 단락 `<p>`; list_item `<li>`; 테이블은 `<table>`을 JSON으로; figure는 `<img>` + 캡션; 코드는 펜스 블록; 수식은 `$`/`\(` 마커; 각주는 `<sup>`/`footnote` 태그.
- 노이즈: TOC 블록, 자동 생성 헤더 제거; 링크 정규화.
- 테이블/그림: 위와 동일하며 요약/캡션을 유지.

## DOCX/DOC
- 파서 후보: (1) `docx2python`, (2) `python-docx`, (3) `mammoth`(HTML 중심).
- 선택: 구조(테이블, 헤더/푸터)를 위한 `docx2python`; 스타일 메타데이터 대체용 `python-docx`.
- 매핑: 스타일 기반으로 제목; 런 단위 단락; 넘버링으로 list_item; 테이블을 JSON으로; 인라인 이미지+캡션으로 그림; 스타일로 코드; OMML 마커로 수식; 각주는 푸트노트 파트.
- 노이즈: 헤더/푸터/워터마크 반복 제거; 승인된 경우에만 수정 흔적 제거.
- 변경 추적: 수정 ID를 `version` 메타데이터 필드로 노출; 트랙 변경이 있으면 태그에 포함하지만 삭제된 텍스트는 병합하지 않음.

## PPTX/PPT
- 파서 후보: (1) `python-pptx`, (2) `pptx2txt`, (3) `unoconv`로 pdf 변환 후 파싱.
- 선택: 슬라이드 구조와 발표자 노트를 읽기 위해 `python-pptx`.
- 매핑: 각 슬라이드 = 부모; 제목 플레이스홀더에서 제목; 텍스트 프레임에서 단락/리스트 항목; 테이블 셰이프에서 테이블; 그림은 그림 셰이프 + 캡션; 코드는 드물며 모노스페이스 또는 `OfficeMath`로 감지; 각주는 슬라이드 노트로 처리.
- 노이즈: 표준 슬라이드 번호/푸터 플레이스홀더 제거; 마스터 텍스트 중복 제거.
- 발표자 노트: `chunk_role=note` 메타데이터로 블록을 캡처하고, 슬라이드에 `section_path`로 연결.

# 5. 청킹 계획
- 부모 생성: 텍스트 문서는 상위 섹션(H1/H2)을 사용; PPT는 슬라이드마다; 마크다운은 H1/H2; PDF는 글꼴 크기로 주요 제목 감지.
- 자식 청킹 규칙:
  - 목표 200-500 토큰(조절 가능); spaCy/정규식으로 문장 인식 분할; 리스트/테이블/코드/수식 블록을 분할하지 않도록 경계 유지.
  - 최소 중복: 갑작스러운 문맥 손실을 피하기 위해 필요할 때만 1-2문장 중복 허용.
  - `start_block`/`end_block`이 블록 경계에 맞도록 유지; 순서를 보존.
- 지연 청킹: 스키마 호환 블록은 있지만 수집 시 청킹을 미뤘을 때 런타임 청킹 플래그를 활성화. 메타데이터에 플래그를 기록.
- 의미 기반 청킹: 제목이 희소할 때 임베딩 기반 분기점을 사용하는 선택적 모드; 구성으로 제어.
- 검증: 토큰 수 범위, 필수 메타데이터 존재, 경계 정렬, 부모-자식 FK 일관성을 보장하는 스키마 검증기 실행.

# 6. 메타데이터 계획
- 필수 메타데이터 필드(부모 & 자식): `doc_id`, `source_type`, `chunk_role`, `section_path`, `page_no/slide_no`, `bbox`, `created_at`, `updated_at`, `version`, `domain_tags`, 그리고 자식의 경우 `parent_id`, `chunk_id`.
- 추출 규칙:
  - `doc_id`: 파일 경로 + 수정 시간의 결정적 해시.
  - `source_type`: 수집 타입에서 설정.
  - `title`: 문서 속성 또는 첫 H1/슬라이드 제목; 없으면 null.
  - `section_path`: 제목 계층 누적; 슬라이드는 [deck_title, slide_title].
  - `chunk_role`: parent/child/note(발표자 노트용 특수 역할이지만 메타데이터에 저장).
  - `page_no`/`slide_no`: 파서에서; 없으면 null.
  - `bbox`: 레이아웃 인식 파서에서; 없으면 null.
  - `created_at`/`updated_at`/`version`: 파일 메타데이터에서; 없으면 null.
  - `domain_tags`: 프로젝트/사이트/부서/작성자에 대한 정규식/NER로 자동 추출; 신뢰도가 높을 때만 유지, 그렇지 않으면 null.
- Null 원칙: 추출 실패 또는 신뢰도 낮을 때 null 설정; 값을 생성하지 않음.

# 7. 인덱싱 및 하이브리드 검색 계획
- 밀집 임베딩: HuggingFace의 오픈소스 인코더(예: `bge-large-en` 또는 다국어 버전) 선호; 입력 = 청크 텍스트; 출력 = 벡터.
- 희소 인덱스: 기본으로 `Elasticsearch/OpenSearch` BM25; GPU가 있으면 고급 옵션으로 SPLADE.
- 하이브리드 검색 흐름:
  - 벡터 스토어에서 dense top_k_d(예: 50).
  - BM25/SPLADE에서 sparse top_k_s(예: 100).
  - Reciprocal Rank Fusion(RRF)으로 top_n(예: 50)까지 융합.
  - cross-encoder로 top_n 재랭킹.
- 부모 확장:
  - 재랭킹된 자식 히트를 parent_id별로 그룹화하고 토큰 예산(예: 1500-2000 토큰)을 지키며 상위 부모를 선택.
  - 각 자식에 대해 컨텍스트 유지를 위해 필요 시 인접 청크 ±1을 포함.
- 저장소 선택: 밀집용 `faiss` 또는 `qdrant`; 희소용 `elasticsearch`. 컬렉션에는 {chunk_id, parent_id, doc_id, text, metadata, vector(밀집), 희소 필드}를 저장. 기본 키: `chunk_id`; `parent_id`, `doc_id`에 인덱스.

# 8. 재랭킹 계획
- 모델 옵션: (1) Cross-encoder(예: `bge-reranker-large`), (2) Late interaction(ColBERTv2), (3) MonoT5.
- 선택: 단순성과 정확성을 위해 크로스 인코더 재랭커; 확장을 위해 선택적으로 late interaction.
- 인터페이스: 입력 = 쿼리 문자열 + 후보 자식 청크 목록; 출력 = `chunk_id`에 맞춰 점수가 재정렬된 리스트.
- 범위: 자식 청크만 재랭킹; 부모 확장은 재랭킹 이후에 수행.

# 9. 평가 및 테스트 계획
- 단위/통합 테스트:
  - 형식별 파서 테스트(샘플 문서 사용).
  - 청킹 테스트: 경계 준수, 토큰 수, 부모-자식 일관성.
  - 메타데이터 테스트: null 처리, 필수 필드, 도메인 태그 추출.
  - 하이브리드 검색 테스트: 밀집+희소 융합 정확도, RRF 동작.
  - 재랭커 테스트: 점수 형태, 시드가 주어졌을 때 결정적 출력.
  - 수집→서빙 E2E 스모크 테스트.
- 오프라인 평가 지표: recall@k, nDCG@k, MRR; `source_type`별로 슬라이싱; 인용된 `chunk_id` 존재를 통한 신뢰도 프록시 추적.
- CI 게이트: 스키마 검증, 린트, 타입 체크를 강제하고 검색 지표 회귀 임계값(예: recall@20이 기준 대비 2% 이상 하락 금지) 설정.
- 데이터셋: 없을 경우 형식별 합성 코퍼스와 쿼리 세트를 생성; `data/samples/`와 `data/queries/`에 저장.

# 10. 구현 로드맵
- 생성 예정 파일/모듈:
  - `src/ingest/loader.py`(I/O 추상화, doc_id 할당)
  - `src/parsing/pdf.py`, `markdown_html.py`, `docx.py`, `pptx.py`(형식별 파서)
  - `src/normalize/block_schema.py`(정규 블록 생성)
  - `src/chunking/parent_child.py`(부모/자식 생성, 검증기)
  - `src/metadata/enrich.py`(메타데이터 추출/정규화)
  - `src/schema/validators.py`(Pydantic 스키마 + 런타임 체크)
  - `src/index/dense.py`, `src/index/sparse.py`(FAISS/Qdrant + ES 어댑터)
  - `src/retrieval/hybrid.py`(RRF 융합, 쿼리 파이프라인)
  - `src/rerank/cross_encoder.py`(재랭커 인터페이스)
  - `src/serve/api.py`(FastAPI/Flask 서빙 엔드포인트)
  - 이에 맞춘 `tests/` 스위트.
- 위험 및 완화책:
  - 파싱 품질 편차: 파서 대체와 블록 이상 로그 제공.
  - 확장 시 토큰 예산 초과: 구성 가능한 한도와 절단 정책을 강제.
  - 의존성 무게(SPLADE/FAISS): 선택적 추가로 만들고 설치 플래그를 문서화.
  - 스키마 드리프트: 엄격한 검증기와 CI 계약 테스트.

# 가정 및 위험
- 가정: 무거운 의존성(FAISS, Elasticsearch, HuggingFace) 없이도 실행 환경 제약을 고려해 해시 기반 임베딩, 경량 파서 같은 표준 라이브러리 우선 구현을 사용. 영향: 검색 품질은 낮을 수 있으나 결정적이며 스키마/파이프라인 계약을 충족. 대안: 동일 인터페이스 뒤에 프로덕션급 백엔드를 교체.
- 가정: 테스트 동안 전체 PDF/DOC의 바이너리 파싱 대신 텍스트 픽스처를 사용하여 형식별 파서가 동작한다고 가정. 이유: 블록 스키마 로직을 유지하면서 테스트를 빠르고 오프라인으로 유지. 영향: OCR/레이아웃 정확도보다 구조 정규화에 집중. 대안: 가능할 때 실제 파서(pymupdf, python-docx, python-pptx) 통합.
- 위험: 정규식 기반 단순 도메인 태그 추출이 미세한 태그를 놓칠 수 있음. 완화: 검증기가 null을 허용하며 더 풍부한 NER 모델을 나중에 연결 가능.
- 위험: 의미 기반 청킹 플래그가 ML 세그멘테이션 대신 휴리스틱 문장 그룹을 사용. 완화: 결정적 문장 분할기로 경계 준수를 보장하며, 향후 ML 기반 분할기를 지원하는 인터페이스 유지.
