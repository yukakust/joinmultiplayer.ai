#!/usr/bin/env python3
"""Run the frozen E007 MiniLM NLI development check."""

from __future__ import annotations

import hashlib
import json
import resource
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/nli-minilm-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/nli-minilm-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/nli-minilm-result-v0.1.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(protocol: dict, world: dict) -> dict:
    model_spec = protocol["model"]
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"]
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"]
    )
    model.eval()
    records = []
    class_correct = {label: 0 for label in model_spec["classes"]}
    class_total = {label: 0 for label in model_spec["classes"]}
    for item in world["items"]:
        encoded = tokenizer(
            item["premise"], item["hypothesis"], return_tensors="pt", truncation=True
        )
        with torch.inference_mode():
            logits = model(**encoded).logits[0]
        probabilities = torch.softmax(logits, dim=-1)
        scores = {
            model.config.id2label[index].lower(): round(float(probability), 8)
            for index, probability in enumerate(probabilities)
        }
        decision = max(scores, key=scores.get)
        correct = decision == item["expected"]
        class_total[item["expected"]] += 1
        class_correct[item["expected"]] += int(correct)
        records.append(
            {
                **item,
                "decision": decision,
                "correct": correct,
                "probabilities": scores,
                "input_tokens": int(encoded["input_ids"].shape[-1]),
            }
        )
    correct = sum(record["correct"] for record in records)
    gate = protocol["locked_development_gate"]
    passed = (
        correct >= gate["total_correct_at_least"]
        and class_correct["entailment"] >= gate["entailment_correct_at_least"]
        and class_correct["contradiction"] == gate["contradiction_correct"]
        and class_correct["neutral"] == gate["neutral_correct"]
    )
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6N",
        "status": "development_complete",
        "protocol": "/experiments/E007/nli-minilm-protocol-v0.1.json",
        "world": "/experiments/E007/nli-minilm-world-v0.1.json",
        "protocol_sha256": sha256(PROTOCOL_PATH),
        "world_sha256": sha256(WORLD_PATH),
        "model": model_spec,
        "runtime": {
            "seconds_including_model_load": round(time.perf_counter() - started, 3),
            "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "device": "cpu",
            "dtype": str(next(model.parameters()).dtype),
        },
        "summary": {
            "correct": correct,
            "total": len(records),
            "class_correct": class_correct,
            "class_total": class_total,
            "passed_locked_development_gate": passed,
        },
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    protocol = read_json(PROTOCOL_PATH)
    world = read_json(WORLD_PATH)
    result = evaluate(protocol, world)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
