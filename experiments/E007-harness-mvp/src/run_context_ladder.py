#!/usr/bin/env python3
"""Run E007 Gate 3C.6G context ladder."""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import torch


ROOT = Path(__file__).parents[3]
BASE_PATH = ROOT / "experiments/E007-harness-mvp/src/run_atomic_button_test.py"
SPEC = importlib.util.spec_from_file_location("atomic_button_runner", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
PROTOCOL_PATH = ROOT / "site/experiments/E007/context-ladder-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/context-ladder-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/context-ladder-result-v0.1.json"


def run(threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6G inputs are not frozen")
    torch.set_num_threads(threads)
    model, tokenizer = BASE.load_model()
    items = [{"case_id": case["id"], "prompt": case["prompt"]} for case in world["cases"]]
    started = time.monotonic()
    outputs = BASE.score_buttons(model, tokenizer, items, batch_size=2)
    by_id = {item["case_id"]: item for item in outputs}
    records = []
    for case in world["cases"]:
        actual = by_id[case["id"]]
        records.append({
            **case,
            "prompt_tokens": len(tokenizer.encode(case["prompt"], add_special_tokens=False)),
            "actual": actual,
            "correct": actual["decision"] == case["expected"],
        })
    levels = []
    for level in range(5):
        selected = [record for record in records if record["level"] == level]
        levels.append({
            "level": level,
            "name": selected[0]["name"],
            "correct": sum(record["correct"] for record in selected),
            "total": 2,
            "prompt_words": selected[0]["prompt_words"],
            "prompt_tokens": selected[0]["prompt_tokens"],
            "passed": all(record["correct"] for record in selected),
        })
    correct = sum(record["correct"] for record in records)
    failed = [level for level in levels if not level["passed"]]
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6G",
        "status": "context_ladder_run_complete",
        "protocol": "/experiments/E007/context-ladder-protocol-v0.1.json",
        "world": "/experiments/E007/context-ladder-world-v0.1.json",
        "protocol_sha256": BASE.sha256_file(PROTOCOL_PATH),
        "world_sha256": BASE.sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": BASE.sha256_file(BASE.MODEL_FILE),
            "weights_changed": False,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": {
            "correct": correct,
            "total": 10,
            "levels_passed": sum(level["passed"] for level in levels),
            "levels_total": 5,
            "first_failed_level": failed[0]["level"] if failed else None,
        },
        "levels": levels,
        "passed_locked_gate": correct == protocol["locked_success"]["total_correct"],
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed_locked_gate"], **result["summary"], "levels": result["levels"]}, indent=2))


if __name__ == "__main__":
    main()
