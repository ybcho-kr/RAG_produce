from eval.metrics import faithfulness_proxy, mrr, ndcg_at_k, recall_at_k, slice_by_source


def test_eval_metrics_basic():
    preds = [["a", "b"], ["c", "d"], ["a", "d"]]
    labels = [["b"], ["d"], ["z"]]
    assert recall_at_k(preds, labels, k=1) <= 1
    assert ndcg_at_k(preds, labels, k=2) <= 1
    assert 0 <= mrr(preds, labels) <= 1


def test_slice_and_faithfulness():
    results = [{"source_type": "md", "chunk_id": "c1", "cited_chunks": ["c1"]}, {"chunk_id": "c2"}]
    sliced = slice_by_source(results)
    assert "md" in sliced
    faith = faithfulness_proxy(results)
    assert 0 <= faith <= 1
