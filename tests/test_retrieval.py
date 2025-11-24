from index.dense import DenseIndexer
from index.sparse import SparseIndexer
from retrieval.hybrid import HybridRetriever


def test_hybrid_rrf_fusion():
    dense = DenseIndexer()
    sparse = SparseIndexer()
    dense.add("c1", "finance overview and research")
    dense.add("c2", "engineering details and compliance")
    sparse.add("c1", "finance overview and research")
    sparse.add("c2", "engineering details and compliance")
    retriever = HybridRetriever(dense, sparse)
    results = retriever.query("finance research", top_k_d=2, top_k_s=2, top_n=2)
    assert results[0][0] == "c1"
    assert len(results) == 2
