#!/usr/bin/env python3
"""Run E007's frozen fresh twenty-pair DeBERTa NLI test."""

from __future__ import annotations

import hashlib
import json
import resource
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/nli-fresh20-short-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/nli-fresh20-short-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/nli-fresh20-short-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol, world = read(PROTOCOL_PATH), read(WORLD_PATH)
    spec = protocol["model"]
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"])
    model = AutoModelForSequenceClassification.from_pretrained(
        spec["repository"], revision=spec["revision"], dtype=torch.float32
    )
    model.eval()
    records = []
    class_total = {name: 0 for name in spec["classes"]}
    class_correct = {name: 0 for name in spec["classes"]}
    for item in world["items"]:
        encoded = tokenizer(item["premise"], item["hypothesis"], return_tensors="pt", truncation=True)
        with torch.inference_mode():
            probabilities = torch.softmax(model(**encoded).logits[0], dim=-1)
        scores = {model.config.id2label[i].lower(): round(float(p), 8) for i, p in enumerate(probabilities)}
        decision = max(scores, key=scores.get)
        correct = decision == item["expected"]
        class_total[item["expected"]] += 1
        class_correct[item["expected"]] += int(correct)
        records.append({**item, "decision": decision, "correct": correct, "probabilities": scores, "input_tokens": int(encoded["input_ids"].shape[-1])})
    total_correct = sum(item["correct"] for item in records)
    gate = protocol["locked_development_gate"]
    passed = (
        total_correct >= gate["total_correct_at_least"]
        and class_correct["entailment"] >= gate["entailment_correct_at_least"]
        and class_correct["contradiction"] == gate["contradiction_correct"]
        and class_correct["neutral"] >= gate["neutral_correct_at_least"]
    )
    result = {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "3C.6P",
        "status": "fresh_synthetic_development_complete",
        "protocol": "/experiments/E007/nli-fresh20-short-protocol-v0.1.json",
        "world": "/experiments/E007/nli-fresh20-short-world-v0.1.json",
        "protocol_sha256": digest(PROTOCOL_PATH), "world_sha256": digest(WORLD_PATH),
        "model": spec,
        "runtime": {"seconds_including_model_load": round(time.perf_counter() - started, 3), "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "device": "cpu", "dtype": str(next(model.parameters()).dtype)},
        "summary": {"correct": total_correct, "total": len(records), "class_correct": class_correct, "class_total": class_total, "passed_locked_development_gate": passed},
        "records": records, "boundary": protocol["claim_boundary"]
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
