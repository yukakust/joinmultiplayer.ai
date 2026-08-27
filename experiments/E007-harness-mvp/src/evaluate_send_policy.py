#!/usr/bin/env python3
"""Run the locked E007 Gate 3C send-policy comparison."""

from __future__ import annotations

import hashlib
import json
import math
import secrets
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL = ROOT / "site/experiments/E007/send-policy-protocol-v0.1.json"
MEMORY = ROOT / "site/experiments/E007/send-policy-memory-v0.1.json"
OUTPUT = ROOT / "site/experiments/E007/send-policy-result-v0.1.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def cosine(left, right) -> float:
    dot = float(sum(float(a) * float(b) for a, b in zip(left, right)))
    ln = math.sqrt(sum(float(value) ** 2 for value in left))
    rn = math.sqrt(sum(float(value) ** 2 for value in right))
    return max(-1.0, min(1.0, dot / (ln * rn))) if ln and rn else 0.0


def select_threshold(scores: list[float], labels: list[bool], beta: float) -> tuple[float, float]:
    candidates = sorted(set(scores), reverse=True) + [-1.0]
    best = (candidates[0], -1.0)
    beta2 = beta * beta
    for threshold in candidates:
        predictions = [score >= threshold for score in scores]
        tp = sum(prediction and label for prediction, label in zip(predictions, labels))
        fp = sum(prediction and not label for prediction, label in zip(predictions, labels))
        fn = sum(not prediction and label for prediction, label in zip(predictions, labels))
        denominator = (1 + beta2) * tp + beta2 * fn + fp
        value = ((1 + beta2) * tp / denominator) if denominator else 1.0
        if value > best[1] or (math.isclose(value, best[1]) and threshold > best[0]):
            best = (threshold, value)
    return best


def state_for(policy: str, score: float, balanced: float, recall: float, document: dict) -> str:
    threshold = balanced if policy == "balanced" else recall
    if policy != "top1_candidate" and score < threshold:
        return "empty"
    if document["permission"] == "blocked":
        return "blocked"
    if policy == "top1_candidate" and score < balanced:
        return "candidate"
    return "found"


def main(cache_dir: Path) -> None:
    from fastembed import TextEmbedding

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    memory = json.loads(MEMORY.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_run":
        raise SystemExit("Gate 3C protocol is not locked")
    texts = []
    for pair in memory["calibration_pairs"]:
        texts.extend([pair["query"], pair["passage"]])
    for question in memory["questions"]:
        texts.append(question["question"])
    for documents in memory["libraries"].values():
        texts.extend(document["text"] for document in documents)
    unique = list(dict.fromkeys(texts))
    model = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(cache_dir), threads=4)
    vectors = dict(zip(unique, model.embed(unique, batch_size=16)))
    calibration_scores = [cosine(vectors[pair["query"]], vectors[pair["passage"]]) for pair in memory["calibration_pairs"]]
    labels = [bool(pair["relevant"]) for pair in memory["calibration_pairs"]]
    balanced, balanced_value = select_threshold(calibration_scores, labels, beta=1.0)
    recall, recall_value = select_threshold(calibration_scores, labels, beta=2.0)
    canary = secrets.token_urlsafe(24)
    records = []
    policies = [item["id"] for item in protocol["policies"]]
    for question in memory["questions"]:
        for card_id, documents in memory["libraries"].items():
            hydrated = [dict(document, text=document["text"].replace("{{SYNTHETIC_PRIVATE_CANARY}}", canary)) for document in documents]
            ranked = sorted(
                ((cosine(vectors[question["question"]], vectors[document["text"]]), document) for document in documents),
                key=lambda item: (-item[0], item[1]["id"]),
            )
            score, selected = ranked[0]
            for policy in policies:
                status = state_for(policy, score, balanced, recall, selected)
                records.append({
                    "question_id": question["id"],
                    "card_id": card_id,
                    "policy": policy,
                    "expected": question["expected"][card_id],
                    "actual": status,
                    "score": round(score, 6),
                    "second_score": round(ranked[1][0], 6),
                    "selected_source": selected["id"],
                    "required_sources": question["required_sources"],
                    "offered": status in {"found", "candidate"},
                    "uncertain": status == "candidate",
                })
    if canary in json.dumps(records):
        raise SystemExit("Private canary escaped")
    summaries = {}
    for policy in policies:
        items = [item for item in records if item["policy"] == policy]
        summaries[policy] = {
            "useful_sources_delivered": sum(item["offered"] and item["selected_source"] in item["required_sources"] for item in items),
            "useful_sources_total": 8,
            "critical_missed_knowledge": sum(item["expected"] == "found" and not (item["offered"] and item["selected_source"] in item["required_sources"]) for item in items),
            "critical_privacy_failures": sum(item["expected"] == "blocked" and item["actual"] != "blocked" for item in items),
            "filterable_extra_candidates": sum(item["expected"] == "empty" and item["offered"] for item in items),
            "uncertain_candidates": sum(item["uncertain"] for item in items),
            "terminal_decisions": len(items),
        }
    output = {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C",
        "status": "development_run_complete",
        "protocol": "/experiments/E007/send-policy-protocol-v0.1.json",
        "memory": "/experiments/E007/send-policy-memory-v0.1.json",
        "model": MODEL_NAME,
        "thresholds": {
            "balanced_f1": round(balanced, 6),
            "balanced_calibration_f1": round(balanced_value, 6),
            "recall_first_f2": round(recall, 6),
            "recall_first_calibration_f2": round(recall_value, 6)
        },
        "summaries": summaries,
        "records": records,
        "boundary": "This tests local send policy only. No downstream acceptance or final answer was run."
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"thresholds": output["thresholds"], "summaries": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    main(parser.parse_args().cache_dir)
