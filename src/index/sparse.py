import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from index.embedder import BGEEmbedder


class SparseIndexer:
    """
    Sparse indexer that can operate in two modes:
    - Traditional BM25 scoring using term counts.
    - Lexical weight scoring using BGE-m3-generated weights (dense-sparse hybrid).
    """

    def __init__(self, embedder: Optional[BGEEmbedder] = None, use_lexical_weights: bool = False) -> None:
        self.embedder = embedder or BGEEmbedder()
        self.use_lexical_weights = use_lexical_weights
        self.doc_freq: Counter[str] = Counter()
        self.chunk_terms: Dict[str, Dict[str, float]] = {}
        self.total_docs = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def add(self, chunk_id: str, text: str, lexical_weights: Optional[Dict[str, float]] = None) -> None:
        if self.use_lexical_weights:
            weights = lexical_weights or self.embedder.encode_lexical(text)
            self.chunk_terms[chunk_id] = weights
            self.total_docs += 1
            for term in weights:
                self.doc_freq[term] += 1
            return

        terms_counter = Counter(self._tokenize(text))
        self.chunk_terms[chunk_id] = {term: float(count) for term, count in terms_counter.items()}
        self.total_docs += 1
        for term in terms_counter:
            self.doc_freq[term] += 1

    def _bm25(self, term: str, freq: float, doc_len: float, avg_len: float) -> float:
        k1, b = 1.5, 0.75
        idf = math.log((self.total_docs - self.doc_freq[term] + 0.5) / (self.doc_freq[term] + 0.5) + 1)
        return idf * ((freq * (k1 + 1)) / (freq + k1 * (1 - b + b * (doc_len / avg_len))))

    def _lexical_score(self, query_weights: Dict[str, float], doc_weights: Dict[str, float]) -> float:
        return sum(query_weights.get(term, 0.0) * doc_weights.get(term, 0.0) for term in doc_weights)

    def query(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if self.use_lexical_weights:
            q_weights = self.embedder.encode_lexical(query)
            scores: Dict[str, float] = {}
            for chunk_id, weights in self.chunk_terms.items():
                scores[chunk_id] = self._lexical_score(q_weights, weights)
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            return ranked[:top_k]

        q_terms = self._tokenize(query)
        avg_len = sum(sum(c.values()) for c in self.chunk_terms.values()) / max(self.total_docs, 1)
        scores: Dict[str, float] = defaultdict(float)
        for chunk_id, terms in self.chunk_terms.items():
            doc_len = sum(terms.values())
            for term in q_terms:
                if term in terms:
                    scores[chunk_id] += self._bm25(term, terms[term], doc_len, avg_len or 1.0)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
