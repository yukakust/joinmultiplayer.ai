#!/usr/bin/env python3
"""Score the frozen Gate 3C.5 pairs with Transformers or a llama.cpp server."""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).parents[3]
CALIBRATION_PATH = ROOT / "site/experiments/E007/send-policy-memory-v0.1.json"
HELDOUT_PATH = ROOT / "site/experiments/E007/relevance-reranker-heldout-v0.1.json"
PROTOCOL_PATH = ROOT / "site/experiments/E007/mobile-reranker-protocol-v0.1.json"


PREFIX = (
    '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. '
    'Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
)
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def pairs() -> tuple[list[dict], list[dict], str]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_download_conversion_or_inference":
        raise SystemExit("Gate 3C.5 protocol is not locked")
    calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))["calibration_pairs"]
    heldout = json.loads(HELDOUT_PATH.read_text(encoding="utf-8"))["pairs"]
    return calibration, heldout, protocol["source_model"]["instruction"]


def prompt(instruction: str, query: str, passage: str) -> str:
    body = f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {passage}"
    return PREFIX + body + SUFFIX


def transformers_scores(model_path: Path, items: list[tuple[str, str]], instruction: str, batch_size: int, threads: int) -> list[float]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(threads)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, padding_side="left")
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, local_files_only=True, dtype=torch.bfloat16, low_cpu_mem_usage=True,
    ).eval()
    false_id = tokenizer.convert_tokens_to_ids("no")
    true_id = tokenizer.convert_tokens_to_ids("yes")
    values: list[float] = []
    for start in range(0, len(items), batch_size):
        batch = [prompt(instruction, query, passage) for query, passage in items[start:start + batch_size]]
        inputs = tokenizer(batch, padding=True, truncation=True, max_length=2048, return_tensors="pt")
        with torch.inference_mode():
            logits = model(**inputs).logits[:, -1, :]
            probabilities = torch.softmax(torch.stack([logits[:, false_id], logits[:, true_id]], dim=1).float(), dim=1)[:, 1]
        values.extend(probabilities.tolist())
    return values


def llama_scores(server: str, items: list[tuple[str, str]], instruction: str) -> list[float]:
    values = []
    for query, passage in items:
        body = json.dumps({
            "prompt": prompt(instruction, query, passage),
            "n_predict": 1,
            "temperature": 0,
            "grammar": 'root ::= "yes" | "no"',
            "n_probs": 2,
            "post_sampling_probs": True,
            "return_tokens": True
        }).encode("utf-8")
        request = urllib.request.Request(server.rstrip("/") + "/completion", data=body, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read())
        probability_rows = payload.get("completion_probabilities") or payload.get("probs") or []
        top = probability_rows[0].get("top_probs", []) if probability_rows else []
        scored = {item.get("token", "").strip().lower(): item.get("prob", 0.0) for item in top}
        yes, no = float(scored.get("yes", 0.0)), float(scored.get("no", 0.0))
        if yes + no == 0:
            generated = payload.get("content", "").strip().lower()
            yes, no = (1.0, 0.0) if generated == "yes" else (0.0, 1.0) if generated == "no" else (math.nan, math.nan)
        values.append(yes / (yes + no))
    return values


def main(args: argparse.Namespace) -> None:
    calibration, heldout, instruction = pairs()
    calibration_inputs = [(item["query"], item["passage"]) for item in calibration]
    heldout_inputs = [(item["question"], item["passage"]) for item in heldout]
    started = time.monotonic()
    if args.mode == "transformers":
        score = lambda items: transformers_scores(args.model, items, instruction, args.batch_size, args.threads)
    else:
        score = lambda items: llama_scores(args.server, items, instruction)
    output = {
        "method": args.method,
        "mode": args.mode,
        "calibration_scores": score(calibration_inputs),
        "heldout_scores": score(heldout_inputs),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "model_file_bytes": args.model.stat().st_size if args.model and args.model.is_file() else None
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", required=True)
    parser.add_argument("--mode", choices=("transformers", "llama"), required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--server", default="http://127.0.0.1:18080")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--threads", type=int, default=20)
    main(parser.parse_args())
