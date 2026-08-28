#!/usr/bin/env python3
"""Gate 13A: group similar multilingual pocket i answers."""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/answer-clustering-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/answer-clustering-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/answer-clustering-result-v0.1.json"


def pair_f1(scores: list[float], labels: list[bool], threshold: float) -> tuple[float, int, int, int]:
    predictions = [score >= threshold for score in scores]
    tp = sum(prediction and label for prediction, label in zip(predictions, labels))
    fp = sum(prediction and not label for prediction, label in zip(predictions, labels))
    fn = sum(not prediction and label for prediction, label in zip(predictions, labels))
    denominator = 2 * tp + fp + fn
    return ((2 * tp / denominator) if denominator else 1.0, tp, fp, fn)


def choose_threshold(scores: list[float], labels: list[bool]) -> tuple[float, dict]:
    candidates = sorted(set(scores), reverse=True)
    candidates = [min(1.000001, candidates[0] + 0.000001)] + candidates + [-1.0]
    best = None
    for threshold in candidates:
        f1, tp, fp, fn = pair_f1(scores, labels, threshold)
        candidate = (f1, threshold, tp, fp, fn)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    assert best is not None
    return best[1], {"f1": best[0], "tp": best[2], "fp": best[3], "fn": best[4]}


def components(ids: list[str], pair_scores: dict[tuple[str, str], float], threshold: float) -> list[list[str]]:
    parent = {item: item for item in ids}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    for (left, right), score in pair_scores.items():
        if score >= threshold:
            union(left, right)
    groups: dict[str, list[str]] = {}
    for item in ids:
        groups.setdefault(find(item), []).append(item)
    return sorted((sorted(group) for group in groups.values()), key=lambda group: group[0])


def mean_pool(model_output, attention_mask):
    import torch

    token_embeddings = model_output[0]
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)


def embed(texts: list[str], repository: str, revision: str, batch_size: int) -> list[list[float]]:
    import torch
    import torch.nn.functional as functional
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(repository, revision=revision)
    model = AutoModel.from_pretrained(repository, revision=revision, dtype=torch.float32).eval()
    values = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        inputs = tokenizer(batch, padding=True, truncation=True, max_length=256, return_tensors="pt")
        with torch.inference_mode():
            pooled = mean_pool(model(**inputs), inputs["attention_mask"])
            normalized = functional.normalize(pooled, p=2, dim=1)
        values.extend(normalized.tolist())
    return values


def cosine(left: list[float], right: list[float]) -> float:
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def run(batch_size: int = 16) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_run" or world["status"] != "frozen_before_run":
        raise RuntimeError("Gate 13A is not frozen")
    answers = world["answers"]
    calibration = world["calibration_pairs"]
    texts = []
    for pair in calibration:
        texts.extend([pair["left"], pair["right"]])
    texts.extend(item["text"] for item in answers)
    unique_texts = list(dict.fromkeys(texts))
    vectors = embed(unique_texts, protocol["model"]["repository"], protocol["model"]["revision"], batch_size)
    by_text = dict(zip(unique_texts, vectors))

    calibration_scores = [cosine(by_text[item["left"]], by_text[item["right"]]) for item in calibration]
    calibration_labels = [bool(item["same_meaning"]) for item in calibration]
    threshold, calibration_metric = choose_threshold(calibration_scores, calibration_labels)

    pair_scores = {}
    for left, right in combinations(answers, 2):
        pair_scores[(left["id"], right["id"])] = cosine(by_text[left["text"]], by_text[right["text"]])
    predicted = components([item["id"] for item in answers], pair_scores, threshold)
    predicted_by_id = {item: index + 1 for index, group in enumerate(predicted) for item in group}
    gold_by_id = {item["id"]: item["gold_group"] for item in answers}

    pair_records = []
    for (left, right), score in sorted(pair_scores.items()):
        expected_same = gold_by_id[left] == gold_by_id[right]
        actual_same = predicted_by_id[left] == predicted_by_id[right]
        pair_records.append({
            "left": left, "right": right,
            "score": round(score, 6),
            "expected_same": expected_same,
            "actual_same": actual_same,
            "correct": expected_same == actual_same,
        })
    tp = sum(item["actual_same"] and item["expected_same"] for item in pair_records)
    fp = sum(item["actual_same"] and not item["expected_same"] for item in pair_records)
    fn = sum(not item["actual_same"] and item["expected_same"] for item in pair_records)
    pairwise_f1 = (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else 1.0

    gold_groups = {}
    for item in answers:
        gold_groups.setdefault(item["gold_group"], []).append(item["id"])
    exact_multi = 0
    for group_id in [f"G{index}" for index in range(1, 7)]:
        expected = set(gold_groups[group_id])
        found = next(set(group) for group in predicted if expected & set(group))
        exact_multi += found == expected

    forbidden = []
    for rule in world["forbidden_merges"]:
        merged = any(
            any(gold_by_id[item] == rule["left_group"] for item in group)
            and any(gold_by_id[item] == rule["right_group"] for item in group)
            for group in predicted
        )
        forbidden.append({**rule, "merged": merged})

    clusters = []
    by_id = {item["id"]: item for item in answers}
    for index, group in enumerate(predicted, 1):
        clusters.append({
            "cluster_id": f"C{index:02d}",
            "answer_ids": group,
            "gold_groups": sorted({gold_by_id[item] for item in group}),
            "answers": [by_id[item] for item in group],
        })
    summary = {
        "answers": len(answers),
        "predicted_groups": len(predicted),
        "gold_groups": len(gold_groups),
        "pairwise_f1": round(pairwise_f1, 6),
        "pairwise_tp": tp,
        "pairwise_fp": fp,
        "pairwise_fn": fn,
        "exact_paraphrase_groups": exact_multi,
        "paraphrase_groups_total": 6,
        "forbidden_merges": sum(item["merged"] for item in forbidden),
        "lost_answers": len(answers) - sum(len(group) for group in predicted),
    }
    gate = protocol["locked_gate"]
    passed = (
        summary["pairwise_f1"] >= gate["pairwise_f1_minimum"]
        and summary["exact_paraphrase_groups"] == 6
        and summary["forbidden_merges"] == gate["forbidden_related_or_opposing_merges"]
        and summary["lost_answers"] == gate["lost_answers"]
    )
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "13A",
        "status": "synthetic_development_run_complete",
        "protocol": "/experiments/E007/answer-clustering-protocol-v0.1.json",
        "world": "/experiments/E007/answer-clustering-world-v0.1.json",
        "model": protocol["model"],
        "threshold": round(threshold, 6),
        "calibration": {
            **{key: round(value, 6) if isinstance(value, float) else value for key, value in calibration_metric.items()},
            "records": [
                {**item, "score": round(score, 6), "predicted_same": score >= threshold}
                for item, score in zip(calibration, calibration_scores)
            ],
        },
        "summary": summary,
        "passed_locked_gate": passed,
        "clusters": clusters,
        "forbidden_merge_checks": forbidden,
        "pair_records": pair_records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    result = run(args.batch_size)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"threshold": result["threshold"], "summary": result["summary"], "passed_locked_gate": result["passed_locked_gate"]}, indent=2))


if __name__ == "__main__":
    main()
