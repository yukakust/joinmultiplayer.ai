from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def prompt_for(row: dict) -> str:
    return f"### Task\n{row['input']}\n\n### Answer\n"


def compact(value: str) -> str:
    return " ".join(value.lower().replace("ё", "е").split())


def preliminary_score(row: dict, output: str) -> dict:
    text = compact(output)
    if row["skill"] == "archivist":
        action = compact(row["expected"]["decision"])
        lineage = (
            ("one" in text or "1" in text) and ("lineage" in text or "dependent" in text)
            if row["language"] == "en"
            else ("одн" in text or "1" in text) and ("зависим" in text or "происхожд" in text or "лини" in text)
        )
        return {"action_found": action in text, "lineage_found": lineage, "preliminary_correct": action in text and lineage}
    action = compact(row["expected"]["action"])
    allowed = bool(row["expected"]["intervention_allowed"])
    if row["language"] == "en":
        abstains = "do not" in text or "don't" in text or "must not" in text
    else:
        abstains = "нельзя" in text or "не " in text or "пока" in text
    correct_policy = (not abstains) if allowed else abstains
    return {"action_found": action in text, "policy_found": correct_policy, "preliminary_correct": action in text and correct_policy}


def generate(model, tokenizer, prompt: str, max_new_tokens: int) -> str:
    encoded = tokenizer(prompt, return_tensors="pt")
    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(generated[0, encoded["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    data = json.loads(args.data.read_text(encoding="utf-8"))
    rows = [row for row in data["examples"] if row["skill"] == args.skill and row["split"] == "held_out"][: args.limit]
    if not rows:
        raise ValueError("no held-out rows")
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(base, args.adapter, is_trainable=False)
    model.eval()
    started = time.monotonic()
    outputs = []
    for row in rows:
        prompt = prompt_for(row)
        with model.disable_adapter():
            base_output = generate(model, tokenizer, prompt, args.max_new_tokens)
        adapter_output = generate(model, tokenizer, prompt, args.max_new_tokens)
        outputs.append({
            "task_id": row["id"],
            "language": row["language"],
            "entity": row["entity"],
            "question": row["input"],
            "expected_answer": row["target"],
            "base": {"output": base_output, "preliminary": preliminary_score(row, base_output)},
            "personal_dora": {"output": adapter_output, "preliminary": preliminary_score(row, adapter_output)},
        })
        print(json.dumps({"task": row["id"], "base": outputs[-1]["base"]["preliminary"], "dora": outputs[-1]["personal_dora"]["preliminary"]}), flush=True)
    payload = {
        "experiment_id": "E005",
        "gate": 4,
        "kind": "development_microscope",
        "claim_status": "automatic_preliminary_review_only",
        "skill": args.skill,
        "data_sha256": data["content_sha256"],
        "tasks": len(outputs),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "base_preliminary_correct": sum(row["base"]["preliminary"]["preliminary_correct"] for row in outputs),
        "dora_preliminary_correct": sum(row["personal_dora"]["preliminary"]["preliminary_correct"] for row in outputs),
        "rows": outputs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("tasks", "base_preliminary_correct", "dora_preliminary_correct", "elapsed_seconds")}), flush=True)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--skill", required=True, choices=["archivist", "safety_keeper"])
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
