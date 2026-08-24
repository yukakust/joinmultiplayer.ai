from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch.optim import AdamW
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_ID = "Qwen/Qwen3-0.6B-Base"
MODEL_REVISION = "da87bfb608c14b7cf20ba1ce41287e8de496c0cd"
SEED = 17082026
SKILLS = {"archivist", "safety_keeper"}
CONTROLS = {"correct", "shuffled"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(data_path: Path, skill: str, control: str) -> tuple[dict, list[dict]]:
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    rows = [dict(row) for row in payload["examples"] if row["skill"] == skill and row["split"] == "train"]
    if not rows:
        raise ValueError(f"no training rows for {skill}")
    if control == "shuffled":
        groups: dict[tuple[str, str], list[int]] = {}
        for index, row in enumerate(rows):
            groups.setdefault((row["language"], row["entity"]), []).append(index)
        original = [row["target"] for row in rows]
        for indices in groups.values():
            if len(indices) < 2:
                raise ValueError("shuffled control needs two same-language examples per entity")
            for position, index in enumerate(indices):
                rows[index]["target"] = original[indices[(position + 1) % len(indices)]]
    return payload, rows


def encode_row(tokenizer, row: dict, max_length: int) -> dict[str, torch.Tensor]:
    prefix = f"### Task\n{row['input']}\n\n### Answer\n"
    full = prefix + row["target"] + tokenizer.eos_token
    prefix_ids = tokenizer(prefix, add_special_tokens=False)["input_ids"]
    encoded = tokenizer(
        full,
        add_special_tokens=False,
        max_length=max_length,
        truncation=True,
        padding="max_length",
        return_tensors="pt",
    )
    labels = encoded["input_ids"].clone()
    labels[:, : min(len(prefix_ids), max_length)] = -100
    labels[encoded["attention_mask"] == 0] = -100
    if not torch.any(labels != -100):
        raise ValueError(f"answer was truncated for {row['id']}")
    return {
        "input_ids": encoded["input_ids"],
        "attention_mask": encoded["attention_mask"],
        "labels": labels,
    }


def train(args: argparse.Namespace) -> dict:
    if args.skill not in SKILLS or args.control not in CONTROLS:
        raise ValueError("unsupported skill or control")
    if args.steps < 1:
        raise ValueError("steps must be positive")

    torch.manual_seed(SEED)
    random.seed(SEED)
    torch.set_num_threads(args.threads)
    data, rows = load_rows(args.data, args.skill, args.control)
    base_hash_before = sha256_file(args.model / "model.safetensors")
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        args.model,
        local_files_only=True,
        dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    base.config.use_cache = False
    config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.rank,
        lora_alpha=args.alpha,
        lora_dropout=0.0,
        target_modules=["q_proj", "v_proj"],
        bias="none",
        use_dora=True,
    )
    model = get_peft_model(base, config)
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    model.train()
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    total = sum(parameter.numel() for parameter in model.parameters())
    optimizer = AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate)
    order = list(range(len(rows)))
    random.Random(SEED).shuffle(order)
    losses = []
    started = time.monotonic()
    optimizer.zero_grad(set_to_none=True)
    for step in range(args.steps):
        row = rows[order[step % len(order)]]
        batch = encode_row(tokenizer, row, args.max_length)
        output = model(**batch)
        loss = output.loss
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite loss at step {step + 1}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
        print(json.dumps({"step": step + 1, "loss": losses[-1], "row": row["id"]}), flush=True)

    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output / "adapter", safe_serialization=True)
    tokenizer.save_pretrained(args.output / "adapter")
    base_hash_after = sha256_file(args.model / "model.safetensors")
    summary = {
        "experiment_id": "E005",
        "gate": 4,
        "kind": "development_smoke" if args.steps <= 4 else "development_training",
        "skill": args.skill,
        "control": args.control,
        "seed": SEED,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "data_sha256": data["content_sha256"],
        "steps": args.steps,
        "max_length": args.max_length,
        "rank": args.rank,
        "alpha": args.alpha,
        "learning_rate": args.learning_rate,
        "target_modules": ["q_proj", "v_proj"],
        "use_dora": True,
        "trainable_parameters": trainable,
        "total_parameters": total,
        "losses": losses,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "base_hash_before": base_hash_before,
        "base_hash_after": base_hash_after,
        "base_unchanged": base_hash_before == base_hash_after,
        "adapter_path": "adapter",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--skill", required=True, choices=sorted(SKILLS))
    parser.add_argument("--control", default="correct", choices=sorted(CONTROLS))
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--alpha", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
