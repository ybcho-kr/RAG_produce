# 1. Repo Scan Summary
- Repository structure: minimal at present; only `README.md` exists, no source directories or RAG pipeline code yet.
- Entry points / modules: none available. No ingest, indexing, or serving components present.
- Existing RAG code: none. Fresh implementation required.
- Installation/testing/execution commands: not defined. Recommend initializing Python environment (e.g., `uv` or `pip` with `requirements.txt` to be added) and defining `make test` for CI once modules are created.
- Integration suggestion: introduce modular package structure under `src/` with subpackages for `ingest`, `parsing`, `chunking`, `metadata`, `index`, `retrieval`, `rerank`, and `serve` plus `tests/`. Plan assumes Python-based stack.

# 2. Target Architecture
```
[Ingest] → [Normalize to Block Schema] → [Hierarchical Chunking (Parent/Child)] → [Metadata Enrichment]
        → [Dense Index] + [Sparse Index] → [Hybrid Retrieval (RRF fusion)] → [Re-ranking]
        → [Parent Expansion] → [Serve API]
```
- Inputs/Outputs by stage:
  - Ingest: input = raw documents (pdf, md/html, docx, pptx, etc.); output = raw text + structural hints.
  - Normalize: input = raw parse results; output = `DocumentBlocks` JSON conforming to canonical block schema.
  - Chunking: input = `DocumentBlocks`; output = `ParentChunk` + `ChildChunk` lists with links.
  - Metadata Enrichment: input = chunks; output = chunks with required metadata fields populated/validated.
  - Dense Indexing: input = child chunks with text + metadata; output = stored vectors keyed by `chunk_id`.
  - Sparse Indexing: input = child chunks; output = sparse postings/BM25 or SPLADE vectors keyed by `chunk_id`.
  - Hybrid Retrieval: input = query; output = fused ranked child chunk candidates.
  - Re-ranking: input = fused candidates; output = re-ordered child chunks with scores.
  - Parent Expansion: input = reranked child chunks; output = parent-level contexts with neighboring children added under token budget.
  - Serve: input = query; output = retrieved/expanded contexts and associated metadata for downstream LLM QA.

# 3. Canonical Schemas
## 3.1 DocumentBlocks (Normalization Output)
| Field | Type | Required | Invariants |
| --- | --- | --- | --- |
| doc_id | string | Y | Stable per source document; UUID or deterministic hash. |
| source_type | enum(pdf, md, html, docx, doc, pptx, ppt, txt, other) | Y | Matches ingest type. |
| title | string or null | N | Null if unavailable; no guessing. |
| blocks | list[Block] | Y | Ordered as in document. |

`Block` object:
| Field | Type | Required | Invariants |
| --- | --- | --- | --- |
| block_id | string | Y | Unique within doc; stable hash of content + position. |
| type | enum(heading, paragraph, list_item, table, figure, code, equation, footnote) | Y | Derived from parser. |
| text | string or null | N | Null for non-textual blocks (e.g., table without inline text); no hallucination. |
| rich_text | string or null | N | Preserves inline formatting/HTML/markup when available. |
| level | int or null | N | Only for headings/list hierarchy; null otherwise. |
| parent_id | string or null | N | Links nested structures (e.g., list items under list block); null if top-level. |
| order | int | Y | Sequential order within document. |
| page_no | int or null | N | Page/slide index 1-based when available; null otherwise. |
| bbox | array[4] of float or null | N | [x1,y1,x2,y2] if available; null if not detected. |
| table_json | object or null | N | Normalized table structure (rows/cols/cells); null if not a table. |
| table_summary | string or null | N | Optional summary of table content; null if not computed. |
| figure_caption | string or null | N | Caption text if figure; null otherwise. |
| figure_alt | string or null | N | Alt/anchor text if available. |
| tags | list[string] or null | N | Parser-level tags; null if none. |
| created_at | string (ISO8601) or null | N | From file metadata if present; null otherwise. |
| updated_at | string (ISO8601) or null | N | From file metadata if present; null otherwise. |

## 3.2 Parent/Child Chunks (Chunking Output)
`ParentChunk`:
| Field | Type | Required | Invariants |
| --- | --- | --- | --- |
| parent_id | string | Y | Derived from top-level section/slide hash. |
| doc_id | string | Y | FK to DocumentBlocks. |
| title | string or null | N | Section/slide title; null if none. |
| section_path | list[string] | Y | Hierarchy from root headings; empty list allowed. |
| text | string | Y | Concatenated text of contained blocks. |
| block_ids | list[string] | Y | Ordered block ids. |
| page_range | tuple(int,int) or null | N | Inclusive page/slide span; null if unavailable. |
| metadata | object | Y | Must include required metadata fields below. |

`ChildChunk`:
| Field | Type | Required | Invariants |
| --- | --- | --- | --- |
| chunk_id | string | Y | Stable hash of parent_id + span. |
| parent_id | string | Y | FK to ParentChunk. |
| doc_id | string | Y | FK to DocumentBlocks. |
| text | string | Y | 200-500 token target; must align to block/sentence boundaries. |
| start_block | string | Y | First block_id included. |
| end_block | string | Y | Last block_id included. |
| order | int | Y | Position within parent. |
| metadata | object | Y | Must include required fields below. |

## 3.3 Metadata Fields (applies to parents & children)
| Field | Type | Required | Null Rule |
| --- | --- | --- | --- |
| doc_id | string | Y | Never null. |
| parent_id | string | Y for child; null for parent. |
| chunk_id | string | Y for child; null for parent. |
| source_type | enum | Y | Derived from ingest; never null. |
| title | string or null | N | Null if missing. |
| section_path | list[string] | Y | Empty allowed. |
| chunk_role | enum(parent, child) | Y | Never null. |
| page_no | int or null | N | Null if unavailable. |
| slide_no | int or null | N | For ppt; null otherwise. |
| bbox | array[4] or null | N | Null if unavailable. |
| created_at | string (ISO8601) or null | N | Null if not in metadata. |
| updated_at | string (ISO8601) or null | N | Null if not in metadata. |
| version | string or int or null | N | Use file version if available; else null. |
| domain_tags | list[string] or null | N | Auto-extracted; null if not confident. |
| page_range | tuple(int,int) or null | N | Parent only when known. |

- Null policy: never fabricate values; if not extractable or low confidence, set null. No empty strings.
- Validator location: plan to add `src/schema/validators.py` with Pydantic/Marshmallow schemas plus pytest coverage in `tests/schema/test_validators.py`.

# 4. Format-specific Parsing Plan
## PDF
- Parser candidates: (1) `pymupdf` (fast, stable, bbox), (2) `pdfminer.six` (text-accurate, slower), (3) `unstructured` PDF loader (handles layout, but heavier deps).
- Choice: `pymupdf` for balance of speed + layout (bbox/page), fallback to `pdfminer.six` for tricky encodings.
- Mapping: headings via font size/style heuristics; paragraphs from text blocks; list_item from bullet detection; tables via `camelot`/`tabula` optional; figures from images + captions; code via monospaced font detection; equation via inline math markers; footnote via superscript cues.
- Noise removal: drop headers/footers via repeated patterns per page; strip page numbers; deduplicate identical lines.
- Tables: extract structured JSON (`rows`, `cells`, `spans`); generate `table.summary` via heuristic or LLM (out-of-band) stored in `table_summary`.
- Figures: capture caption/alt text if near image; store `figure_caption`, `figure_alt`; optional summary via OCR captioning if enabled.

## Markdown/HTML
- Parser candidates: (1) `markdown-it-py` + AST, (2) `BeautifulSoup` for HTML, (3) `mdformat` parsing.
- Choice: `markdown-it-py` for MD AST; `BeautifulSoup` for HTML; unified converter to blocks.
- Mapping: headings from `<h1-6>`; paragraphs `<p>`; list_item `<li>`; table `<table>` to JSON; figure from `<img>` + caption; code from fenced blocks; equation from `$`/`\(` markers; footnotes from `<sup>`/`footnote` tags.
- Noise: remove TOC blocks, autogenerated headers; normalize links.
- Tables/Figures: as above with summaries/captions preserved.

## DOCX/DOC
- Parser candidates: (1) `docx2python`, (2) `python-docx`, (3) `mammoth` (HTML focus).
- Choice: `docx2python` for structure (tables, headers/footers); `python-docx` fallback for styling metadata.
- Mapping: headings via style; paragraphs by runs; list_item via numbering; tables to JSON; figures via inline images + captions; code via styles; equations via OMML markers; footnotes via footnote parts.
- Noise: drop headers/footers/repeated watermarks; remove revision marks only if accepted.
- Track changes: expose as metadata field `version` with revision id; if tracked changes present, include in tags but do not merge deleted text.

## PPTX/PPT
- Parser candidates: (1) `python-pptx`, (2) `pptx2txt`, (3) `unoconv` to pdf then parse.
- Choice: `python-pptx` to read slide structure and speaker notes.
- Mapping: each slide = parent; headings from title placeholders; paragraphs/list_item from text frames; tables from table shapes; figures from picture shapes + captions; code/equation rarely present—detect via monospace or `OfficeMath`; footnotes via slide notes.
- Noise: drop slide numbers/footer placeholders if standard; remove duplicate master text.
- Speaker notes: capture as blocks with type `paragraph` and metadata `chunk_role=note`; link to slide via `section_path`.

# 5. Chunking Plan
- Parent creation: use top-level sections (H1/H2) for text docs; each slide for PPT; for Markdown, H1/H2; for PDF, detect major headings via font size.
- Child chunking rules:
  - Target 200-500 tokens (tunable); sentence-aware splitting using spaCy/regex; ensure boundaries do not split list/table/code/equation blocks.
  - Minimum overlap: allow 1-2 sentences overlap only when needed to avoid abrupt context loss.
  - Maintain `start_block`/`end_block` alignment to block boundaries; preserve order.
- Late chunking: enable flag for runtime chunking when schema-compliant blocks available but ingestion-time chunking deferred (e.g., long docs). Track flag in metadata.
- Semantic chunking: optional mode using embedding-based breakpoints when headings sparse; controlled by config.
- Validation: run schema validator ensuring token count bounds, required metadata present, boundary alignment, and parent-child FK consistency.

# 6. Metadata Plan
- Required metadata fields (parent & child): `doc_id`, `source_type`, `chunk_role`, `section_path`, `page_no/slide_no`, `bbox`, `created_at`, `updated_at`, `version`, `domain_tags`, plus `parent_id`, `chunk_id` for children.
- Extraction rules:
  - `doc_id`: deterministic hash of file path + modified time.
  - `source_type`: set from ingest type.
  - `title`: from document properties or first H1/slide title; null if missing.
  - `section_path`: accumulate heading hierarchy; for slides, [deck_title, slide_title].
  - `chunk_role`: parent/child/note (note specialized for speaker notes but stored in metadata).
  - `page_no`/`slide_no`: from parser; null otherwise.
  - `bbox`: from layout-aware parsers; null if not available.
  - `created_at`/`updated_at`/`version`: from file metadata; null if absent.
  - `domain_tags`: auto-extract via regex/NER for project/site/department/author; only keep high-confidence; else null.
- Null principle: if extraction fails or confidence low, set null; no fabricated values.

# 7. Indexing & Hybrid Retrieval Plan
- Dense embedding: prefer open-source encoder (e.g., `bge-large-en` or multilingual variant) via HuggingFace; input = chunk text; output = vector.
- Sparse index: `Elasticsearch/OpenSearch` BM25 as default; SPLADE as advanced option if GPU available.
- Hybrid retrieval flow:
  - dense top_k_d (e.g., 50) from vector store.
  - sparse top_k_s (e.g., 100) from BM25/SPLADE.
  - Fuse via Reciprocal Rank Fusion (RRF) to top_n (e.g., 50).
  - Re-rank top_n with cross-encoder.
- Parent expansion:
  - Group reranked child hits by parent_id; select top parents respecting token budget (e.g., 1500-2000 tokens).
  - For each child, optionally include neighboring chunks ±1 to preserve context.
- Storage choices: plan for `faiss` or `qdrant` for dense; `elasticsearch` for sparse. Collections store {chunk_id, parent_id, doc_id, text, metadata, vector (dense), sparse fields}. Primary keys: `chunk_id`; indices on `parent_id`, `doc_id`.

# 8. Reranking Plan
- Model options: (1) Cross-encoder (e.g., `bge-reranker-large`), (2) Late interaction (ColBERTv2), (3) MonoT5.
- Choice: cross-encoder reranker for simplicity/accuracy; late interaction optional for scaling.
- Interface: input = query string + list of candidate child chunks; output = reranked list with scores aligned to `chunk_id`.
- Scope: rerank child chunks only; parent expansion happens after rerank.

# 9. Evaluation & Tests Plan
- Unit/integration tests:
  - Parser-specific tests per format with sample docs.
  - Chunking tests: boundary adherence, token counts, parent-child consistency.
  - Metadata tests: null-handling, required fields, domain tag extraction.
  - Hybrid retrieval tests: dense+sparse fusion correctness, RRF behavior.
  - Reranker tests: scoring shape, deterministic output given seed.
  - E2E ingest→serve smoke test.
- Offline eval metrics: recall@k, nDCG@k, MRR; slice by `source_type`; track faithfulness proxy via cited `chunk_id` presence.
- CI gates: enforce schema validation, linting, type checks; regression thresholds on retrieval metrics (e.g., recall@20 must not drop >2% vs baseline).
- Datasets: if none available, generate synthetic corpora per format and query sets; store under `data/samples/` and `data/queries/`.

# 10. Implementation Roadmap
- Planned files/modules (to be created):
  - `src/ingest/loader.py` (I/O abstraction, doc_id assignment)
  - `src/parsing/pdf.py`, `markdown_html.py`, `docx.py`, `pptx.py` (format parsers)
  - `src/normalize/block_schema.py` (canonical block building)
  - `src/chunking/parent_child.py` (parent/child creation, validators)
  - `src/metadata/enrich.py` (metadata extraction/normalization)
  - `src/schema/validators.py` (Pydantic schemas + runtime checks)
  - `src/index/dense.py`, `src/index/sparse.py` (FAISS/Qdrant + ES adapters)
  - `src/retrieval/hybrid.py` (RRF fusion, query pipeline)
  - `src/rerank/cross_encoder.py` (reranker interface)
  - `src/serve/api.py` (FastAPI/Flask serving endpoints)
  - `tests/` suites matching modules.
- Risks & mitigations:
  - Parsing quality variance: provide parser fallbacks and logging of block anomalies.
  - Token budget overflows during expansion: enforce configurable limits and truncation policies.
  - Dependency weight (SPLADE/FAISS): make optional extras; document install flags.
  - Schema drift: strict validators and contract tests in CI.
