# Test Evaluation Instructions

The `tests/test_eval.py` suite validates the offline metric helpers. Run the tests with:

```bash
pytest tests/test_eval.py
```

To experiment manually, you can replicate the sample inline flow:

```bash
python - <<'PY'
from eval.metrics import recall_at_k, ndcg_at_k, mrr, faithfulness_proxy
preds = [["c1", "c2"], ["c3", "c1"]]
labels = [["c1"], ["c3"]]
print("recall@1", recall_at_k(preds, labels, k=1))
print("ndcg@2", ndcg_at_k(preds, labels, k=2))
print("mrr", mrr(preds, labels))
print("faithfulness", faithfulness_proxy([{\"chunk_id\": \"c1\", \"cited_chunks\": [\"c1\"]}]))
PY
```
