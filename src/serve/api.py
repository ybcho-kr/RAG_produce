from typing import Dict, List

from chunk.parent_child import chunk_document
from ingest.loader import load_document
from index.dense import DenseIndexer
from index.embedder import BGEEmbedder
from index.multivector import MultiVectorIndexer
from index.sparse import SparseIndexer
from metadata.enrich import enrich_child_metadata
from rerank.cross_encoder import CrossEncoderReranker
from retrieval.hybrid import HybridRetriever
from schema.validators import ChildChunk, DocumentBlocks, ParentChunk


class SearchService:
    def __init__(self) -> None:
        self.embedder = BGEEmbedder()
        self.dense = DenseIndexer(embedder=self.embedder)
        self.sparse = SparseIndexer(embedder=self.embedder, use_lexical_weights=True)
        self.multivector = MultiVectorIndexer(embedder=self.embedder)
        self.retriever = HybridRetriever(self.dense, self.sparse, self.multivector)
        self.reranker = CrossEncoderReranker()
        self.children: Dict[str, ChildChunk] = {}
        self.parents: Dict[str, ParentChunk] = {}

    def ingest(self, doc: DocumentBlocks) -> None:
        parents, children = chunk_document(doc, target_min_tokens=50, target_max_tokens=120)
        for parent in parents:
            self.parents[parent.parent_id] = parent
        for child in children:
            self.children[child.chunk_id] = child
            dense_vec = self.embedder.encode_dense(child.text)
            lexical_weights = self.embedder.encode_lexical(child.text)
            colbert_vectors = self.embedder.encode_colbert(child.text)
            self.dense.add(child.chunk_id, child.text, vector=dense_vec)
            self.sparse.add(child.chunk_id, child.text, lexical_weights=lexical_weights)
            self.multivector.add(child.chunk_id, child.text, token_vectors=colbert_vectors)

    def load_and_ingest(self, path: str) -> None:
        doc = load_document(path)
        self.ingest(doc)

    def _parent_expand(self, child: ChildChunk, token_budget: int = 400) -> str:
        siblings = [c for c in self.children.values() if c.parent_id == child.parent_id]
        siblings.sort(key=lambda c: c.order)
        idx = next((i for i, s in enumerate(siblings) if s.chunk_id == child.chunk_id), 0)
        context_chunks = [child]
        if idx > 0:
            context_chunks.insert(0, siblings[idx - 1])
        if idx + 1 < len(siblings):
            context_chunks.append(siblings[idx + 1])
        text_parts: List[str] = []
        total_tokens = 0
        for ch in context_chunks:
            tokens = len(ch.text.split())
            if total_tokens + tokens > token_budget:
                break
            total_tokens += tokens
            text_parts.append(ch.text)
        return "\n".join(text_parts)

    def search(self, query: str, top_n: int = 5) -> List[Dict]:
        fused = self.retriever.query(query, top_n=top_n * 2)
        candidates = [self.children[cid] for cid, _ in fused if cid in self.children][: top_n * 2]
        reranked = self.reranker.score(query, candidates)
        results = []
        for child, score in reranked[:top_n]:
            context = self._parent_expand(child)
            results.append(
                {
                    "chunk_id": child.chunk_id,
                    "parent_id": child.parent_id,
                    "score": score,
                    "text": context,
                    "metadata": child.metadata,
                }
            )
        return results


def search_cli(path: str, query: str) -> None:
    service = SearchService()
    service.load_and_ingest(path)
    for result in service.search(query):
        print(f"[{result['score']:.4f}] {result['text'][:80]}...")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lightweight RAG search service")
    parser.add_argument("path", help="Path to document (md/html/pdf/docx/pptx)")
    parser.add_argument("query", help="Query string")
    args = parser.parse_args()
    search_cli(args.path, args.query)
