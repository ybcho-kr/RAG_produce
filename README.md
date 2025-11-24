# RAG Produce Pipeline

This repository implements the end-to-end pipeline defined in `PLAN.md`, including ingestion, schema validation, chunking, metadata enrichment, hybrid retrieval, reranking, serving, and evaluation utilities. The implementation is lightweight and deterministic to remain self-contained.

## Installation

The stack uses only the Python standard library plus `pytest` for tests. Create a virtual environment if desired and install test dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pytest
```

## Ingest & Index

Use the `SearchService` to load documents via the format-specific parsers and build dense/sparse indices automatically:

```bash
python -m serve.api tests/data/sample.md "finance research"
```

Or run the sample pipeline script:

```bash
python examples/simple_pipeline.py
```

## Running Tests

Execute all unit and integration tests:

```bash
pytest
```

## Evaluation

Offline metrics are provided in `src/eval/metrics.py`. A short README for evaluation flows is available at `eval/README.md`, and test instructions at `tests/eval/README.md`.

## Directory Structure

- `src/ingest/`: format parsers and loader utilities
- `src/schema/`: schema dataclasses and validators
- `src/chunk/`: parent/child chunking logic
- `src/metadata/`: metadata enrichment and tagging
- `src/index/`: dense and sparse indexers
- `src/retrieval/`: hybrid retrieval with RRF fusion
- `src/rerank/`: cross-encoder style reranker
- `src/serve/`: search service entry points
- `src/eval/`: offline metric helpers
- `tests/`: unit and integration coverage with sample fixtures
- `examples/`: end-to-end usage sample

## End-to-End Flow

1. **Ingest**: `ingest.loader.load_document(path)` selects the parser based on extension and produces `DocumentBlocks` validated by `schema.validators`.
2. **Chunk**: `chunk.parent_child.chunk_document` builds parents and child chunks with required metadata and boundary alignment.
3. **Index**: `SearchService.ingest` indexes child chunks into dense and sparse stores.
4. **Retrieve**: `HybridRetriever` fuses dense/sparse results via RRF and returns candidates.
5. **Rerank & Serve**: `CrossEncoderReranker` orders candidates; `SearchService.search` expands parents (±1 sibling) under a token budget and returns final contexts.
6. **Evaluate**: Use metrics such as recall@k, nDCG@k, and MRR from `src/eval/metrics.py`; see `tests/eval/README.md` for sample commands.
