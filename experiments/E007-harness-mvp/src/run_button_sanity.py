#!/usr/bin/env python3
"""Run E007 Gate 3C.6F: the smallest accept/reject sanity check."""

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
PROTOCOL_PATH = ROOT / "site/experiments/E007/button-sanity-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/button-sanity-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/button-sanity-result-v0.1.json"


def prompt_for(case: dict) -> str:
    return (
        f"FIRST TEXT:\n{case['first_text']}\n\n"
        f"SECOND TEXT:\n{case['second_text']}\n\n"
        "Which action fits this one comparison? Return accept if the first text clearly supports the second. "
        "Otherwise return reject.\nACTION:"
    )


def run(threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6F inputs are not frozen")
    torch.set_num_threads(threads)
    model, tokenizer = BASE.load_model()
    items = [{"case_id": case["id"], "prompt": prompt_for(case)} for case in world["cases"]]
    started = time.monotonic()
    outputs = BASE.score_buttons(model, tokenizer, items, batch_size=2)
    by_id = {item["case_id"]: item for item in outputs}
    records = [{
        **case,
        "actual": by_id[case["id"]],
        "correct": by_id[case["id"]]["decision"] == case["expected"],
    } for case in world["cases"]]
    correct = sum(record["correct"] for record in records)
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6F",
        "status": "sanity_run_complete",
        "protocol": "/experiments/E007/button-sanity-protocol-v0.1.json",
        "world": "/experiments/E007/button-sanity-world-v0.1.json",
        "protocol_sha256": BASE.sha256_file(PROTOCOL_PATH),
        "world_sha256": BASE.sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": BASE.sha256_file(BASE.MODEL_FILE),
            "weights_changed": False,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": {"correct": correct, "total": 2},
        "passed_locked_gate": correct == protocol["locked_success"]["correct"],
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed_locked_gate"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
