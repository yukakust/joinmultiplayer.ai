#!/usr/bin/env python3
"""Train two tiny DoRA personalities on disjoint synthetic memories.

Development-only: this checks that real local weights can change and that two
independent answers can be assembled. It does not test the four E004 swarm
interfaces or constitute a locked result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import time
from pathlib import Path

import torch
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer


POCKETS = {
    "I01": {"Orin": "VEKU", "Pavo": "NIMRA", "Selen": "JOTI"},
    "I02": {"Flint": "ROKA", "Gale": "TAVEN", "Harbor": "MIPU"},
}
TEMPLATES = (
    "Pocket {pocket} memory. Question: What is {key}'s private code? Answer:",
    "Recall for pocket {pocket}. The private code belonging to {key} is:",
    "{pocket} local-memory lookup. {key} has code:",
    "Question for {pocket}: give only the private code for {key}. Answer:",
)
EVAL_TEMPLATE = "Pocket {pocket} memory check. Reply only with {key}'s private code:"


def normalize_answer(text: str) -> str:
    match = re.search(r"[A-Z]{3,8}", text.upper())
    return match.group(0) if match else text.strip().split()[0].upper() if text.strip() else ""


def adapter_digest(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.named_parameters()):
        if tensor.requires_grad:
            digest.update(name.encode())
            digest.update(tensor.detach().float().cpu().numpy().tobytes())
    return digest.hexdigest()


def encoded_example(tokenizer, pocket: str, key: str, answer: str, template: str):
    prompt = template.format(pocket=pocket, key=key)
    prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
    answer_ids = tokenizer(" " + answer + tokenizer.eos_token, add_special_tokens=False).input_ids
    input_ids = torch.tensor([prompt_ids + answer_ids], dtype=torch.long)
    labels = torch.tensor([[-100] * len(prompt_ids) + answer_ids], dtype=torch.long)
    return input_ids, labels


def load_base(model_path: Path):
    model = AutoModelForCausalLM.from_pretrained(
        model_path, local_files_only=True, dtype=torch.float32
    )
    model.config.use_cache = False
    return model


def generate(model, tokenizer, prompt: str, answer_token_budget: int = 8) -> str:
    model.eval()
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=answer_token_budget,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(output[0, inputs.input_ids.shape[-1] :], skip_special_tokens=True).strip()


def evaluate(model, tokenizer, pocket: str):
    rows = []
    for key, expected in POCKETS[pocket].items():
        prompt = EVAL_TEMPLATE.format(pocket=pocket, key=key)
        raw = generate(model, tokenizer, prompt)
        predicted = normalize_answer(raw)
        rows.append(
            {
                "key": key,
                "expected": expected,
                "raw": raw,
                "predicted": predicted,
                "correct": predicted == expected,
            }
        )
    return rows


def train_pocket(model_path: Path, tokenizer, pocket: str, output: Path, steps: int, lr: float):
    model = load_base(model_path)
    config = LoraConfig(
        r=4,
        lora_alpha=8,
        lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
        use_dora=True,
    )
    model = get_peft_model(model, config)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    before = adapter_digest(model)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=lr)
    examples = [
        encoded_example(tokenizer, pocket, key, answer, template)
        for key, answer in POCKETS[pocket].items()
        for template in TEMPLATES
    ]
    rng = random.Random(17082026 + int(pocket[-1]))
    losses = []
    model.train()
    for step in range(steps):
        input_ids, labels = examples[rng.randrange(len(examples))]
        optimizer.zero_grad(set_to_none=True)
        loss = model(input_ids=input_ids, labels=labels).loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            (p for p in model.parameters() if p.requires_grad), max_norm=1.0
        )
        optimizer.step()
        losses.append(float(loss.detach()))
    after = adapter_digest(model)
    assert before != after, "DoRA adapter did not change"
    output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output, safe_serialization=True)
    return {
        "trainable_parameters": trainable,
        "steps": steps,
        "learning_rate": lr,
        "first_loss": round(losses[0], 6),
        "last_loss": round(losses[-1], 6),
        "adapter_sha256_before": before,
        "adapter_sha256_after": after,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path", type=Path)
    parser.add_argument("adapter_root", type=Path)
    parser.add_argument("--steps", type=int, default=48)
    parser.add_argument("--lr", type=float, default=0.002)
    parser.add_argument("--threads", type=int, default=22)
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(17082026)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)

    started = time.perf_counter()
    frozen = load_base(args.model_path)
    frozen.config.use_cache = True
    baseline = {pocket: evaluate(frozen, tokenizer, pocket) for pocket in POCKETS}
    del frozen

    training = {}
    for pocket in POCKETS:
        training[pocket] = train_pocket(
            args.model_path, tokenizer, pocket, args.adapter_root / pocket, args.steps, args.lr
        )

    matrix = {}
    for adapter_pocket in POCKETS:
        base = load_base(args.model_path)
        model = PeftModel.from_pretrained(base, args.adapter_root / adapter_pocket)
        model.config.use_cache = True
        matrix[adapter_pocket] = {
            question_pocket: evaluate(model, tokenizer, question_pocket)
            for question_pocket in POCKETS
        }
        del model, base

    selected = {"I01": ("Orin", "VEKU"), "I02": ("Gale", "TAVEN")}
    combined_parts = []
    for pocket, (key, expected) in selected.items():
        row = next(item for item in matrix[pocket][pocket] if item["key"] == key)
        combined_parts.append(row["predicted"])
    combined = " | ".join(combined_parts)
    expected_combined = " | ".join(expected for _, expected in selected.values())

    result = {
        "kind": "two_pocket_dora_development_smoke",
        "claim_status": "development_only_not_locked",
        "model_id": "Qwen/Qwen3-0.6B-Base",
        "method": "DoRA r=4 on q/k/v/o projections",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "knowledge": POCKETS,
        "baseline": baseline,
        "training": training,
        "evaluation_matrix": matrix,
        "combined_demo": {
            "query": "Return I01/Orin and I02/Gale in that order.",
            "expected": expected_combined,
            "actual": combined,
            "correct": combined == expected_combined,
            "round_trips": 1,
            "note": "The two local branches are independent; execution is sequential only because this smoke uses one CPU host.",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
