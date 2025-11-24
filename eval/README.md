# 평가 가이드

`src/eval/metrics.py`의 평가 헬퍼는 recall@k, nDCG@k, MRR을 구현하며 슬라이싱 유틸리티와 경량 신뢰도 프록시를 제공합니다. 샘플 평가 흐름을 실행하려면 아래를 사용하세요:

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

이 저장소에는 `tests/test_eval.py`에 지표에 대한 pytest 커버리지가 포함되어 있습니다. 실제 평가 코퍼라를 연결하려면 `preds`/`labels`를 확장하거나, `slice_by_source`를 사용해 `source_type`별로 슬라이싱할 수 있습니다.
