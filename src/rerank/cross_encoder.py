from typing import List, Tuple

from schema.validators import ChildChunk


class CrossEncoderReranker:
    def score(self, query: str, candidates: List[ChildChunk]) -> List[Tuple[ChildChunk, float]]:
        query_terms = set(query.lower().split())
        results: List[Tuple[ChildChunk, float]] = []
        for cand in candidates:
            text_terms = cand.text.lower().split()
            overlap = len(query_terms.intersection(text_terms))
            score = overlap / max(len(query_terms), 1) + len(cand.text) * 1e-4
            results.append((cand, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results
