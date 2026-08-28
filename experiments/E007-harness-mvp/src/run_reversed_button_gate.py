#!/usr/bin/env python3
"""Run E007 Gate 3C.6I: the paired reversed-button control."""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path


ROOT = Path(__file__).parents[3]
BASE_PATH = ROOT / "experiments/E007-harness-mvp/src/run_ninety_word_gate.py"
SPEC = importlib.util.spec_from_file_location("run_ninety_word_gate", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

PROTOCOL_PATH = ROOT / "site/experiments/E007/ninety-word-reversed-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/ninety-word-reversed-world-v0.1.json"
PREVIOUS_RESULT_PATH = ROOT / "site/experiments/E007/ninety-word-result-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/ninety-word-reversed-result-v0.1.json"
ACTIONS = ("reject", "approve")
SYSTEM = (
    "Use only the supplied question, source, and proposed answer. "
    "Choose reject when it conflicts, does not support it, or leaves it unclear. "
    "Choose approve only when the source clearly supports the proposed answer. "
    "Output one choice."
)


def interpretation(summary: dict) -> str:
    if summary["total_correct"] >= 9 and summary["approve_correct"] >= 4 and summary["reject_correct"] >= 4:
        return "semantic_success"
    if summary["switched_approve_to_reject"] >= 8:
        return "strong_order_effect"
    if summary["approve_choices"] >= 8:
        return "strong_approve_label_bias"
    return "mixed_or_unresolved"


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    previous = json.loads(PREVIOUS_RESULT_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6I inputs are not frozen")

    BASE.ACTIONS = ACTIONS
    BASE.SYSTEM = SYSTEM
    BASE.torch.set_num_threads(threads)
    model, tokenizer = BASE.load_model()
    started = time.monotonic()
    outputs = BASE.score(model, tokenizer, world["cases"], batch_size)
    previous_by_id = {record["id"]: record for record in previous["records"]}
    records = []
    for output in outputs:
        old_decision = previous_by_id[output["id"]]["decision"]
        records.append({
            **output,
            "previous_decision": old_decision,
            "changed_from_previous": output["decision"] != old_decision,
            "correct": output["decision"] == output["expected"],
        })

    summary = {
        "approve_correct": sum(record["correct"] and record["expected"] == "approve" for record in records),
        "approve_total": 5,
        "reject_correct": sum(record["correct"] and record["expected"] == "reject" for record in records),
        "reject_total": 5,
        "total_correct": sum(record["correct"] for record in records),
        "total_cases": 10,
        "approve_choices": sum(record["decision"] == "approve" for record in records),
        "reject_choices": sum(record["decision"] == "reject" for record in records),
        "switched_approve_to_reject": sum(
            record["previous_decision"] == "approve" and record["decision"] == "reject"
            for record in records
        ),
        "min_prompt_words": min(record["prompt_words"] for record in records),
        "max_prompt_words": max(record["prompt_words"] for record in records),
        "min_prompt_tokens_with_system": min(record["prompt_tokens_with_system"] for record in records),
        "max_prompt_tokens_with_system": max(record["prompt_tokens_with_system"] for record in records),
    }
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6I",
        "status": "paired_synthetic_development_run_complete",
        "protocol": "/experiments/E007/ninety-word-reversed-protocol-v0.1.json",
        "world": "/experiments/E007/ninety-word-reversed-world-v0.1.json",
        "previous_result": "/experiments/E007/ninety-word-result-v0.1.json",
        "protocol_sha256": BASE.sha256_file(PROTOCOL_PATH),
        "world_sha256": BASE.sha256_file(WORLD_PATH),
        "previous_result_sha256": BASE.sha256_file(PREVIOUS_RESULT_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": BASE.sha256_file(BASE.MODEL_FILE),
            "weights_changed": False,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "locked_interpretation": interpretation(summary),
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.batch_size, args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"interpretation": result["locked_interpretation"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
