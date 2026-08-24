from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from eval_gate4 import prompt_for
from eval_gate4_full import METHODS, generate_batch, save_checkpoint


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    data = json.loads(args.data.read_text(encoding="utf-8"))
    if data.get("training_allowed") is not False or data.get("rag_used") is not False:
        raise ValueError("transfer test must forbid training and RAG")
    rows = [row for row in data["questions"] if row["skill"] == args.skill]
    if not rows:
        raise ValueError("no transfer questions")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(base, args.correct_adapter, adapter_name="personal_dora", is_trainable=False)
    model.load_adapter(args.wrong_adapter, adapter_name="wrong_specialist", is_trainable=False)
    model.load_adapter(args.shuffled_adapter, adapter_name="shuffled_lessons", is_trainable=False)
    model.eval()

    started = time.monotonic()
    prompts = [prompt_for({"input": row["prompt"]}) for row in rows]
    outputs: dict[str, list[str]] = {}
    with model.disable_adapter():
        outputs["base"] = generate_batch(model, tokenizer, prompts, args.max_new_tokens)
    for method in METHODS[1:]:
        model.set_adapter(method)
        outputs[method] = generate_batch(model, tokenizer, prompts, args.max_new_tokens)

    public_rows = []
    for index, row in enumerate(rows):
        public_rows.append({
            "task_id": row["id"],
            "language": row["language"],
            "question": row["prompt"],
            "reference_answer": row["reference_answer"],
            "rubric": row["rubric"],
            "conditions": {method: {"output": outputs[method][index]} for method in METHODS},
        })

    payload = {
        "experiment_id": "E005",
        "gate": "4B",
        "kind": "natural_language_transfer_raw_run",
        "claim_status": "raw_unreviewed",
        "skill": args.skill,
        "data_sha256": data["content_sha256"],
        "training_performed": False,
        "rag_used": False,
        "scoring": "human semantic review; exact-string matching forbidden",
        "methods": list(METHODS),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "rows": public_rows,
    }
    save_checkpoint(args.output, payload)
    print(json.dumps({"skill": args.skill, "tasks": len(public_rows), "elapsed_seconds": payload["elapsed_seconds"]}), flush=True)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--correct-adapter", required=True, type=Path)
    parser.add_argument("--wrong-adapter", required=True, type=Path)
    parser.add_argument("--shuffled-adapter", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--skill", required=True, choices=["archivist", "safety_keeper"])
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
