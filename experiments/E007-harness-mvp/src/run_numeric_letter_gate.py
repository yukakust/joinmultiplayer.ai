#!/usr/bin/env python3
"""Run E007 Gate 3C.6J: mirrored 1/A mappings."""

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

PROTOCOL_PATH = ROOT / "site/experiments/E007/numeric-letter-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/numeric-letter-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/numeric-letter-result-v0.1.json"
ACTIONS = ("1", "A")
SYSTEM = (
    "Use only the supplied question, source, proposed answer, and label mapping. "
    "Follow the mapping exactly. Output only 1 or A."
)


def interpretation(summary: dict) -> str:
    if (
        summary["semantic_correct"] >= 18
        and min(summary["deck_correct"].values()) >= 9
        and summary["minimum_class_correct_within_a_deck"] >= 4
    ):
        return "semantic_success"
    if summary["label_choices"]["1"] >= 16:
        return "strong_1_symbol_bias"
    if summary["label_choices"]["A"] >= 16:
        return "strong_A_symbol_bias"
    if summary["paired_label_flips"] >= 8:
        return "mapping_followed_but_semantics_failed"
    return "mixed_or_unresolved"


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6J inputs are not frozen")

    BASE.ACTIONS = ACTIONS
    BASE.SYSTEM = SYSTEM
    BASE.torch.set_num_threads(threads)
    model, tokenizer = BASE.load_model()
    started = time.monotonic()
    outputs = BASE.score(model, tokenizer, world["items"], batch_size)
    records = []
    for output in outputs:
        actual_semantic = output["mapping"][output["decision"]]
        records.append({
            **output,
            "actual_semantic": actual_semantic,
            "label_correct": output["decision"] == output["expected"],
            "semantic_correct": actual_semantic == output["expected_semantic"],
        })

    by_pair = {(record["case_id"], record["deck"]): record for record in records}
    pairs = []
    for case_id in sorted({record["case_id"] for record in records}):
        x, y = by_pair[(case_id, "X")], by_pair[(case_id, "Y")]
        pairs.append({
            "case_id": case_id,
            "X_label": x["decision"],
            "Y_label": y["decision"],
            "label_flipped": x["decision"] != y["decision"],
            "X_semantic": x["actual_semantic"],
            "Y_semantic": y["actual_semantic"],
            "semantic_preserved": x["actual_semantic"] == y["actual_semantic"],
        })

    deck_correct = {
        deck: sum(record["semantic_correct"] for record in records if record["deck"] == deck)
        for deck in ("X", "Y")
    }
    class_deck_correct = {
        f"{deck}_{meaning}": sum(
            record["semantic_correct"]
            for record in records
            if record["deck"] == deck and record["expected_semantic"] == meaning
        )
        for deck in ("X", "Y") for meaning in ("approve", "reject")
    }
    summary = {
        "semantic_correct": sum(record["semantic_correct"] for record in records),
        "total_prompts": 20,
        "deck_correct": deck_correct,
        "class_deck_correct": class_deck_correct,
        "minimum_class_correct_within_a_deck": min(class_deck_correct.values()),
        "label_choices": {
            "1": sum(record["decision"] == "1" for record in records),
            "A": sum(record["decision"] == "A" for record in records),
        },
        "paired_label_flips": sum(pair["label_flipped"] for pair in pairs),
        "paired_semantics_preserved": sum(pair["semantic_preserved"] for pair in pairs),
        "total_pairs": 10,
        "min_prompt_words": min(record["prompt_words"] for record in records),
        "max_prompt_words": max(record["prompt_words"] for record in records),
        "min_prompt_tokens_with_system": min(record["prompt_tokens_with_system"] for record in records),
        "max_prompt_tokens_with_system": max(record["prompt_tokens_with_system"] for record in records),
    }
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6J",
        "status": "paired_synthetic_development_run_complete",
        "protocol": "/experiments/E007/numeric-letter-protocol-v0.1.json",
        "world": "/experiments/E007/numeric-letter-world-v0.1.json",
        "protocol_sha256": BASE.sha256_file(PROTOCOL_PATH),
        "world_sha256": BASE.sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": BASE.sha256_file(BASE.MODEL_FILE),
            "weights_changed": False,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "locked_interpretation": interpretation(summary),
        "pairs": pairs,
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
