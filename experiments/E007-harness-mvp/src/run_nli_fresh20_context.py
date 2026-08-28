#!/usr/bin/env python3
"""Run the paired E007 NLI context-sensitivity test."""

from __future__ import annotations

import hashlib
import json
import resource
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/nli-fresh20-context-protocol-v0.1.json"
CONTEXT_PATH = ROOT / "site/experiments/E007/nli-fresh20-context-world-v0.1.json"
SHORT_WORLD_PATH = ROOT / "site/experiments/E007/nli-fresh20-short-world-v0.1.json"
SHORT_RESULT_PATH = ROOT / "site/experiments/E007/nli-fresh20-short-result-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/nli-fresh20-context-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol, contexts = read(PROTOCOL_PATH), read(CONTEXT_PATH)
    short_world, short_result = read(SHORT_WORLD_PATH), read(SHORT_RESULT_PATH)
    spec = protocol["model"]
    base_by_id = {item["id"]: item for item in short_world["items"]}
    old_by_id = {item["id"]: item for item in short_result["records"]}
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"])
    model = AutoModelForSequenceClassification.from_pretrained(spec["repository"], revision=spec["revision"], dtype=torch.float32)
    model.eval()
    records = []
    class_total = {name: 0 for name in spec["classes"]}
    class_correct = {name: 0 for name in spec["classes"]}
    for context in contexts["items"]:
        base, old = base_by_id[context["id"]], old_by_id[context["id"]]
        premise = f"User question: {context['question']}\n\nSource context: {context['before']} {base['premise']} {context['after']}"
        encoded = tokenizer(premise, base["hypothesis"], return_tensors="pt", truncation=True)
        with torch.inference_mode():
            probabilities = torch.softmax(model(**encoded).logits[0], dim=-1)
        scores = {model.config.id2label[i].lower(): round(float(p), 8) for i, p in enumerate(probabilities)}
        decision = max(scores, key=scores.get)
        correct = decision == base["expected"]
        class_total[base["expected"]] += 1
        class_correct[base["expected"]] += int(correct)
        records.append({**base, **context, "expanded_premise": premise, "short_decision": old["decision"], "short_confidence": old["probabilities"][old["decision"]], "decision": decision, "correct": correct, "probabilities": scores, "input_tokens": int(encoded["input_ids"].shape[-1]), "decision_changed": decision != old["decision"]})
    total_correct = sum(item["correct"] for item in records)
    short_correct = short_result["summary"]["correct"]
    gate = protocol["locked_development_gate"]
    passed = (
        total_correct >= gate["total_correct_at_least"]
        and class_correct["entailment"] >= gate["entailment_correct_at_least"]
        and class_correct["contradiction"] == gate["contradiction_correct"]
        and class_correct["neutral"] >= gate["neutral_correct_at_least"]
        and short_correct - total_correct <= gate["maximum_drop_from_short_20_of_20"]
    )
    result = {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "3C.6Q",
        "status": "paired_context_development_complete",
        "protocol": "/experiments/E007/nli-fresh20-context-protocol-v0.1.json",
        "context_world": "/experiments/E007/nli-fresh20-context-world-v0.1.json",
        "short_world": "/experiments/E007/nli-fresh20-short-world-v0.1.json",
        "protocol_sha256": digest(PROTOCOL_PATH), "context_world_sha256": digest(CONTEXT_PATH), "short_world_sha256": digest(SHORT_WORLD_PATH),
        "model": spec,
        "runtime": {"seconds_including_model_load": round(time.perf_counter() - started, 3), "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "device": "cpu", "dtype": str(next(model.parameters()).dtype)},
        "summary": {"correct": total_correct, "total": len(records), "short_correct": short_correct, "delta_from_short": total_correct - short_correct, "changed_decisions": sum(item["decision_changed"] for item in records), "class_correct": class_correct, "class_total": class_total, "passed_locked_development_gate": passed},
        "records": records, "boundary": protocol["claim_boundary"]
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
