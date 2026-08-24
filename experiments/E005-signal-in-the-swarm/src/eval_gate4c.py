from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


CONDITIONS = ("frozen_base", "matching_dora", "wrong_skill_dora", "shuffled_lessons_dora")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model(model_path: Path, adapter_path: Path | None):
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True)
    if adapter_path is not None:
        model = PeftModel.from_pretrained(model, adapter_path, local_files_only=True)
    model.eval()
    return model


def answer(model, tokenizer, prompt: str, max_new_tokens: int) -> str:
    prefix = f"### Task\n{prompt}\n\n### Answer\n"
    encoded = tokenizer(prefix, return_tensors="pt", add_special_tokens=False)
    with torch.inference_mode():
        output = model.generate(**encoded, do_sample=False, max_new_tokens=max_new_tokens, eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(output[0, encoded["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    if exam.get("status") != "locked_not_run" or len(exam.get("questions", [])) != 48:
        raise ValueError("expected the frozen 48-question exam")
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    adapters = {
        "source_correct": args.source_correct,
        "safe_correct": args.safe_correct,
        "source_shuffled": args.source_shuffled,
        "safe_shuffled": args.safe_shuffled,
    }
    rows = {question["id"]: {**question, "conditions": {}} for question in exam["questions"]}
    plan = [
        ("frozen_base", None, {"source_work", "safe_action"}),
        ("matching_dora", adapters["source_correct"], {"source_work"}),
        ("matching_dora", adapters["safe_correct"], {"safe_action"}),
        ("wrong_skill_dora", adapters["safe_correct"], {"source_work"}),
        ("wrong_skill_dora", adapters["source_correct"], {"safe_action"}),
        ("shuffled_lessons_dora", adapters["source_shuffled"], {"source_work"}),
        ("shuffled_lessons_dora", adapters["safe_shuffled"], {"safe_action"}),
    ]
    started = time.monotonic()
    for condition, adapter_path, skills in plan:
        model = load_model(args.model, adapter_path)
        selected = [question for question in exam["questions"] if question["skill"] in skills]
        for index, question in enumerate(selected):
            rows[question["id"]]["conditions"][condition] = {"output": answer(model, tokenizer, question["prompt"], args.max_new_tokens), "review": "unscored"}
            if (index + 1) % 6 == 0:
                print(json.dumps({"condition": condition, "adapter": adapter_path.name if adapter_path else "none", "answered": index + 1, "total": len(selected)}), flush=True)
        del model
    result = {
        "experiment_id": "E005",
        "gate": "4C",
        "kind": "raw_locked_transfer_generations",
        "status": "complete_unscored_owner_review_required",
        "exam_content_sha256": exam["content_sha256"],
        "exam_file_sha256": sha256_file(args.exam),
        "base_file_sha256": sha256_file(args.model / "model.safetensors"),
        "adapter_file_sha256": {name: sha256_file(path / "adapter_model.safetensors") for name, path in adapters.items()},
        "conditions": list(CONDITIONS),
        "generation": {"do_sample": False, "max_new_tokens": args.max_new_tokens, "rag_used": False, "internet_used": False, "training_performed": False, "exact_string_scoring_performed": False},
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "rows": list(rows.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--exam", type=Path, required=True)
    parser.add_argument("--source-correct", type=Path, required=True)
    parser.add_argument("--safe-correct", type=Path, required=True)
    parser.add_argument("--source-shuffled", type=Path, required=True)
    parser.add_argument("--safe-shuffled", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--threads", type=int, default=12)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
