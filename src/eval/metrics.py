import math
from collections import defaultdict
from typing import Dict, List


def recall_at_k(preds: List[List[str]], labels: List[List[str]], k: int = 5) -> float:
    hits = 0
    total = len(labels)
    for pred, gold in zip(preds, labels):
        hits += 1 if set(gold) & set(pred[:k]) else 0
    return hits / total if total else 0.0


def dcg(scores: List[int]) -> float:
    return sum(score / math.log2(idx + 2) for idx, score in enumerate(scores))


def ndcg_at_k(preds: List[List[str]], labels: List[List[str]], k: int = 5) -> float:
    total = 0.0
    for pred, gold in zip(preds, labels):
        scores = [1 if p in gold else 0 for p in pred[:k]]
        ideal = sorted(scores, reverse=True)
        total += dcg(scores) / (dcg(ideal) or 1)
    return total / len(labels) if labels else 0.0


def mrr(preds: List[List[str]], labels: List[List[str]]) -> float:
    acc = 0.0
    for pred, gold in zip(preds, labels):
        rank = next((idx + 1 for idx, p in enumerate(pred) if p in gold), 0)
        acc += 1 / rank if rank else 0
    return acc / len(labels) if labels else 0.0


def slice_by_source(results: List[Dict], source_key: str = "source_type") -> Dict[str, List[Dict]]:
    slices: Dict[str, List[Dict]] = defaultdict(list)
    for row in results:
        slices[row.get(source_key, "unknown")].append(row)
    return slices


def faithfulness_proxy(responses: List[Dict]) -> float:
    # Proxy: fraction of responses that include cited chunk_id in provenance
    faithful = 0
    for resp in responses:
        if resp.get("chunk_id") in resp.get("cited_chunks", [resp.get("chunk_id")]):
            faithful += 1
    return faithful / len(responses) if responses else 0.0
