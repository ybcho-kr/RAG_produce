# 테스트 평가 지침

`tests/test_eval.py` 스위트는 오프라인 지표 헬퍼를 검증합니다. 아래 명령으로 테스트를 실행하세요:

```bash
pytest tests/test_eval.py
```

직접 실험하려면 샘플 인라인 흐름을 그대로 실행할 수 있습니다:

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
