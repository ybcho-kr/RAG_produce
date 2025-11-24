from typing import Dict, List, Optional, Tuple

from index.embedder import BGEEmbedder


class DenseIndexer:
    """Dense indexer backed by the BGE-m3 embedder."""

    def __init__(self, embedder: Optional[BGEEmbedder] = None) -> None:
        self.embedder = embedder or BGEEmbedder()
        self.vectors: Dict[str, List[float]] = {}
        self.texts: Dict[str, str] = {}

    def add(self, chunk_id: str, text: str, vector: Optional[List[float]] = None) -> None:
        self.vectors[chunk_id] = vector or self.embedder.encode_dense(text)
        self.texts[chunk_id] = text

    def query(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        q_vec = self.embedder.encode_dense(query)
        results: List[Tuple[str, float]] = []
        for chunk_id, vec in self.vectors.items():
            score = sum(a * b for a, b in zip(q_vec, vec))
            results.append((chunk_id, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
