from typing import Dict, List, Tuple

from index.dense import DenseIndexer
from index.multivector import MultiVectorIndexer
from index.sparse import SparseIndexer


class HybridRetriever:
    def __init__(
        self, dense: DenseIndexer, sparse: SparseIndexer, multivector: MultiVectorIndexer | None = None
    ) -> None:
        self.dense = dense
        self.sparse = sparse
        shared_embedder = getattr(dense, "embedder", None)
        self.multivector = multivector or MultiVectorIndexer(embedder=shared_embedder)

    def rrf_fuse(self, *hits_lists: List[List[Tuple[str, float]]], k: int = 60) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}
        for hits in hits_lists:
            for rank, (cid, _) in enumerate(hits):
                scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def query(
        self,
        query: str,
        top_k_d: int = 20,
        top_k_s: int = 40,
        top_k_mv: int = 20,
        top_n: int = 20,
    ) -> List[Tuple[str, float]]:
        dense_hits = self.dense.query(query, top_k=top_k_d)
        sparse_hits = self.sparse.query(query, top_k=top_k_s)
        multivector_hits = self.multivector.query(query, top_k=top_k_mv)
        fused = self.rrf_fuse(dense_hits, sparse_hits, multivector_hits)
        return fused[:top_n]
