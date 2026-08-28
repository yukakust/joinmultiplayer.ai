#!/usr/bin/env python3
"""Run E007 Gate 3C.6H: ten complete prompts under 90 words."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/ninety-word-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/ninety-word-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/ninety-word-result-v0.1.json"
MODEL_PATH = Path("/home/yuka/models/e005/qwen3-0.6b-instruct-c1899de")
MODEL_FILE = MODEL_PATH / "model.safetensors"
ACTIONS = ("approve", "reject")

SYSTEM = (
    "Use only the supplied question, source, and proposed answer. "
    "Choose approve only when the source clearly supports the proposed answer. "
    "Choose reject when it conflicts, does not support it, or leaves it unclear. "
    "Output one choice."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        local_files_only=True,
        dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()
    return model, tokenizer


def score(model, tokenizer, cases: list[dict], batch_size: int) -> list[dict]:
    action_ids = {}
    for action in ACTIONS:
        ids = tokenizer.encode(action, add_special_tokens=False)
        if len(ids) != 1:
            raise RuntimeError(f"{action} must be one token, got {ids}")
        action_ids[action] = ids[0]

    records = []
    for start in range(0, len(cases), batch_size):
        batch = cases[start:start + batch_size]
        rendered = [
            tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": case["prompt"]},
                ],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            for case in batch
        ]
        encoded = tokenizer(rendered, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            logits = model(**encoded).logits[:, -1, :]
            selected = logits[:, [action_ids[action] for action in ACTIONS]]
            probabilities = torch.softmax(selected, dim=-1)
        prompt_tokens = [len(tokenizer(text, add_special_tokens=False)["input_ids"]) for text in rendered]
        for case, row_logits, row_probabilities, token_count in zip(batch, selected, probabilities, prompt_tokens):
            decision = ACTIONS[int(torch.argmax(row_logits).item())]
            records.append({
                **case,
                "prompt_tokens_with_system": token_count,
                "decision": decision,
                "scores": {
                    action: round(float(row_probabilities[index].item()), 8)
                    for index, action in enumerate(ACTIONS)
                },
                "logit_margin": round(float(torch.abs(row_logits[0] - row_logits[1]).item()), 8),
                "correct": decision == case["expected"],
            })
        print(json.dumps({"scored": min(start + batch_size, len(cases)), "total": len(cases)}), flush=True)
    return records


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6H inputs are not frozen")
    if any(case["prompt_words"] > 90 for case in world["cases"]):
        raise RuntimeError("A frozen prompt exceeds 90 words")

    torch.set_num_threads(threads)
    model, tokenizer = load_model()
    started = time.monotonic()
    records = score(model, tokenizer, world["cases"], batch_size)
    summary = {
        "approve_correct": sum(record["correct"] and record["expected"] == "approve" for record in records),
        "approve_total": 5,
        "reject_correct": sum(record["correct"] and record["expected"] == "reject" for record in records),
        "reject_total": 5,
        "total_correct": sum(record["correct"] for record in records),
        "total_cases": 10,
        "min_prompt_words": min(record["prompt_words"] for record in records),
        "max_prompt_words": max(record["prompt_words"] for record in records),
        "min_prompt_tokens_with_system": min(record["prompt_tokens_with_system"] for record in records),
        "max_prompt_tokens_with_system": max(record["prompt_tokens_with_system"] for record in records),
    }
    gate = protocol["locked_success_rule"]
    passed = (
        summary["approve_correct"] == gate["approve_correct"]
        and summary["reject_correct"] == gate["reject_correct"]
        and summary["total_correct"] == gate["total_correct"]
    )
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6H",
        "status": "synthetic_development_run_complete",
        "protocol": "/experiments/E007/ninety-word-protocol-v0.1.json",
        "world": "/experiments/E007/ninety-word-world-v0.1.json",
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "world_sha256": sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": sha256_file(MODEL_FILE),
            "weights_changed": False,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "passed_locked_gate": passed,
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
    print(json.dumps({"passed": result["passed_locked_gate"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
