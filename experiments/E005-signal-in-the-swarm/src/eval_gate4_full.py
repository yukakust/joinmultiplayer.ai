from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from eval_gate4 import generate, preliminary_score, prompt_for


METHODS = ("base", "personal_dora", "wrong_specialist", "shuffled_lessons")


def exact_target_match(target: str, output: str) -> bool:
    normalize = lambda value: " ".join(value.lower().replace("ё", "е").split()).strip(" .")
    expected = normalize(target)
    actual = normalize(output)
    return actual == expected or actual.startswith(expected + " ") or actual.startswith(expected + ".")


def save_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    data = json.loads(args.data.read_text(encoding="utf-8"))
    rows = [row for row in data["examples"] if row["skill"] == args.skill and row["split"] == "held_out"][: args.limit]
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(base, args.correct_adapter, adapter_name="personal_dora", is_trainable=False)
    model.load_adapter(args.wrong_adapter, adapter_name="wrong_specialist", is_trainable=False)
    model.load_adapter(args.shuffled_adapter, adapter_name="shuffled_lessons", is_trainable=False)
    model.eval()
    started = time.monotonic()
    output_rows = []
    payload = {
        "experiment_id": "E005",
        "gate": 4,
        "kind": "full_development_control_run",
        "claim_status": "running_unreviewed",
        "skill": args.skill,
        "data_sha256": data["content_sha256"],
        "methods": list(METHODS),
        "rows": output_rows,
    }
    for index, row in enumerate(rows, start=1):
        prompt = prompt_for(row)
        results = {}
        with model.disable_adapter():
            base_output = generate(model, tokenizer, prompt, args.max_new_tokens)
        results["base"] = base_output
        for method in METHODS[1:]:
            model.set_adapter(method)
            results[method] = generate(model, tokenizer, prompt, args.max_new_tokens)
        reviewed = {}
        for method, output in results.items():
            reviewed[method] = {
                "output": output,
                "exact_target_match": exact_target_match(row["target"], output),
                "preliminary": preliminary_score(row, output),
            }
        output_rows.append({
            "task_id": row["id"],
            "language": row["language"],
            "entity": row["entity"],
            "question": row["input"],
            "expected_answer": row["target"],
            "conditions": reviewed,
        })
        payload["completed_tasks"] = index
        payload["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save_checkpoint(args.output, payload)
        print(json.dumps({"task": index, "of": len(rows), "id": row["id"], "exact": {method: reviewed[method]["exact_target_match"] for method in METHODS}}), flush=True)
    payload["claim_status"] = "development_automatic_exact_match_unreviewed"
    payload["summary"] = {
        method: {
            "exact_target_matches": sum(row["conditions"][method]["exact_target_match"] for row in output_rows),
            "preliminary_correct": sum(row["conditions"][method]["preliminary"]["preliminary_correct"] for row in output_rows),
            "tasks": len(output_rows),
        }
        for method in METHODS
    }
    save_checkpoint(args.output, payload)
    print(json.dumps(payload["summary"]), flush=True)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--correct-adapter", required=True, type=Path)
    parser.add_argument("--wrong-adapter", required=True, type=Path)
    parser.add_argument("--shuffled-adapter", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--skill", required=True, choices=["archivist", "safety_keeper"])
    parser.add_argument("--limit", type=int, default=48)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
