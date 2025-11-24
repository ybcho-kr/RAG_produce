import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple


class SparseIndexer:
    def __init__(self) -> None:
        self.doc_freq: Counter[str] = Counter()
        self.chunk_terms: Dict[str, Counter[str]] = {}
        self.total_docs = 0

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def add(self, chunk_id: str, text: str) -> None:
        terms = Counter(self._tokenize(text))
        self.chunk_terms[chunk_id] = terms
        self.total_docs += 1
        for term in terms:
            self.doc_freq[term] += 1

    def _bm25(self, term: str, freq: int, doc_len: int, avg_len: float) -> float:
        k1, b = 1.5, 0.75
        idf = math.log((self.total_docs - self.doc_freq[term] + 0.5) / (self.doc_freq[term] + 0.5) + 1)
        return idf * ((freq * (k1 + 1)) / (freq + k1 * (1 - b + b * (doc_len / avg_len))))

    def query(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
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
