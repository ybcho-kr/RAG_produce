import hashlib
import math
from typing import Dict, List


class BGEEmbedder:
    """
    Lightweight, deterministic stand-in for the BGE-m3 encoder.

    The real BGE-m3 model yields three outputs in a single forward pass:
    - Dense embedding for first-stage vector search.
    - Lexical weights that approximate a sparse vector for lexical matching.
    - ColBERT-style token vectors for late interaction / multi-vector search.

    This helper mirrors that contract using stable hashing so the rest of the
    pipeline can be exercised without external dependencies.
    """

    def __init__(self, dim: int = 1024, colbert_dim: int = 128) -> None:
        self.dim = dim
        self.colbert_dim = colbert_dim

    def _tokenize(self, text: str) -> List[str]:
        return [tok for tok in text.lower().split() if tok]

    def _hash_to_unit_vector(self, text: str, dim: int) -> List[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        numbers = [int.from_bytes(h[i : i + 4], "big") for i in range(0, len(h), 4)]
        vec = [numbers[i % len(numbers)] % 1000 / 1000.0 for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def encode_dense(self, text: str) -> List[float]:
        """Return a deterministic dense embedding for the full text."""

        return self._hash_to_unit_vector(text, self.dim)

    def encode_lexical(self, text: str) -> Dict[str, float]:
        """Approximate BGE-m3 lexical weights for sparse retrieval."""

        weights: Dict[str, float] = {}
        tokens = self._tokenize(text)
        total = len(tokens) or 1
        for tok in tokens:
            # Use a stable hash-derived weight to mimic learned lexical scores.
            weight = (int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % 1000) / 1000.0
            weights[tok] = weights.get(tok, 0.0) + weight
        # Normalize by token count to keep magnitudes comparable across lengths.
        return {tok: w / total for tok, w in weights.items()}

    def encode_colbert(self, text: str) -> List[List[float]]:
        """
        Generate token-level vectors for late interaction.

        Each token becomes a small unit vector. Scoring can then use a max-sim
        aggregation similar to ColBERT.
        """

        return [self._hash_to_unit_vector(tok, self.colbert_dim) for tok in self._tokenize(text)]
