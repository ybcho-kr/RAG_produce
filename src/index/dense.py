import hashlib
import math
from typing import Dict, List, Tuple


class DenseIndexer:
    def __init__(self, dim: int = 16) -> None:
        self.dim = dim
        self.vectors: Dict[str, List[float]] = {}
        self.texts: Dict[str, str] = {}

    def _hash_to_vector(self, text: str) -> List[float]:
        h = hashlib.sha1(text.encode("utf-8")).hexdigest()
        numbers = [int(h[i : i + 4], 16) for i in range(0, len(h), 4)]
        vector = [numbers[i % len(numbers)] % 1000 / 1000.0 for i in range(self.dim)]
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def add(self, chunk_id: str, text: str) -> None:
        self.vectors[chunk_id] = self._hash_to_vector(text)
        self.texts[chunk_id] = text

    def query(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        q_vec = self._hash_to_vector(query)
        results: List[Tuple[str, float]] = []
        for chunk_id, vec in self.vectors.items():
            score = sum(a * b for a, b in zip(q_vec, vec))
            results.append((chunk_id, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
