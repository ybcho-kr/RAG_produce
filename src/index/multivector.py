from typing import Dict, List, Optional, Tuple

from index.embedder import BGEEmbedder


class MultiVectorIndexer:
    """ColBERT-style late interaction indexer using BGE-m3 token vectors."""

    def __init__(self, embedder: Optional[BGEEmbedder] = None) -> None:
        self.embedder = embedder or BGEEmbedder()
        self.token_vectors: Dict[str, List[List[float]]] = {}

    def add(self, chunk_id: str, text: str, token_vectors: Optional[List[List[float]]] = None) -> None:
        self.token_vectors[chunk_id] = token_vectors or self.embedder.encode_colbert(text)

    def _late_interaction_score(self, query_vecs: List[List[float]], doc_vecs: List[List[float]]) -> float:
        score = 0.0
        if not query_vecs or not doc_vecs:
            return score
        for q_vec in query_vecs:
            max_sim = max(sum(a * b for a, b in zip(q_vec, d_vec)) for d_vec in doc_vecs)
            score += max_sim
        return score / len(query_vecs)

    def query(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        q_vecs = self.embedder.encode_colbert(query)
        scores: List[Tuple[str, float]] = []
        for chunk_id, doc_vecs in self.token_vectors.items():
            score = self._late_interaction_score(q_vecs, doc_vecs)
            scores.append((chunk_id, score))
        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
