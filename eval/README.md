# Evaluation Guide

The evaluation helpers in `src/eval/metrics.py` implement recall@k, nDCG@k, and MRR along with slicing utilities and a lightweight faithfulness proxy. To run a sample evaluation flow:

```bash
python - <<'PY'
from eval.metrics import recall_at_k, ndcg_at_k, mrr
preds = [["c1", "c2", "c3"], ["c2", "c3", "c1"]]
labels = [["c2"], ["c3"]]
print("recall@2", recall_at_k(preds, labels, k=2))
print("ndcg@3", ndcg_at_k(preds, labels, k=3))
print("mrr", mrr(preds, labels))
PY
```

This repo also includes pytest coverage for the metrics in `tests/test_eval.py`. Extend `preds`/`labels` to plug in real evaluation corpora or slice by `source_type` using `slice_by_source`.
