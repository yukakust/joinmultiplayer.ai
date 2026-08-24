from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import torch
from safetensors.torch import save_file
from torch import nn
from transformers import AutoModelForCausalLM, AutoTokenizer

from gate5b_model import ParallelTrackQwen


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encode_lesson(tokenizer, lesson: dict, max_length: int) -> dict:
    user = [{"role": "user", "content": lesson["prompt"]}]
    prompt_text = tokenizer.apply_chat_template(
        user, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
    full_ids = tokenizer.encode(
        prompt_text + lesson["target"] + tokenizer.eos_token,
        add_special_tokens=False,
    )[:max_length]
    labels = [-100] * min(len(prompt_ids), len(full_ids)) + full_ids[len(prompt_ids) :]
    if not any(value != -100 for value in labels):
        raise ValueError(f"lesson target was truncated: {lesson['id']}")
    return {"id": lesson["id"], "input_ids": full_ids, "labels": labels}


def collate(rows: list[dict], pad_id: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    width = max(len(row["input_ids"]) for row in rows)
    input_ids, labels, attention = [], [], []
    for row in rows:
        padding = width - len(row["input_ids"])
        input_ids.append(row["input_ids"] + [pad_id] * padding)
        labels.append(row["labels"] + [-100] * padding)
        attention.append([1] * len(row["input_ids"]) + [0] * padding)
    return torch.tensor(input_ids), torch.tensor(labels), torch.tensor(attention)


def causal_loss(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    return nn.functional.cross_entropy(
        logits[:, :-1].contiguous().view(-1, logits.shape[-1]),
        labels[:, 1:].contiguous().view(-1),
        ignore_index=-100,
    )


def train_part(model, encoded: list[dict], part: str, *, epochs: int, batch_size: int, learning_rate: float, seed: int, pad_id: int) -> dict:
    model.set_trainable(part)
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=learning_rate, weight_decay=0.01)
    losses = []
    started = time.monotonic()
    for epoch in range(epochs):
        order = list(range(len(encoded)))
        random.Random(seed + epoch).shuffle(order)
        for start in range(0, len(order), batch_size):
            batch = [encoded[index] for index in order[start : start + batch_size]]
            input_ids, labels, attention = collate(batch, pad_id)
            optimizer.zero_grad(set_to_none=True)
            output = model(input_ids=input_ids, attention_mask=attention, mode=part)
            loss = causal_loss(output.logits, labels)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite {part} loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimizer.step()
            losses.append(loss.item())
            print(json.dumps({"part": part, "epoch": epoch + 1, "step": len(losses), "loss": round(loss.item(), 6)}), flush=True)
    model.freeze_all()
    window = min(8, len(losses))
    return {
        "part": part, "epochs": epochs, "lessons": len(encoded), "steps": len(losses),
        "batch_size": batch_size, "learning_rate": learning_rate,
        "trainable_parameters": sum(parameter.numel() for parameter in trainable),
        "loss_mean_first": sum(losses[:window]) / window,
        "loss_mean_last": sum(losses[-window:]) / window,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def run(args: argparse.Namespace) -> dict:
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    curriculum = json.loads(args.curriculum.read_text(encoding="utf-8"))
    design = json.loads(args.design.read_text(encoding="utf-8"))
    if curriculum["status"] != "frozen_before_training" or design["status"] != "locked_not_run":
        raise ValueError("Gate 5B inputs are not frozen")
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True
    ).eval()
    model = ParallelTrackQwen(base)
    lessons = curriculum["track_lessons"]
    if args.limit:
        lessons = [
            row
            for role in ("cause", "safety")
            for row in [item for item in lessons if item["role"] == role][: args.limit]
        ]
    encoded = {
        role: [encode_lesson(tokenizer, row, args.max_length) for row in lessons if row["role"] == role]
        for role in ("cause", "safety")
    }
    shared_before = model.shared.model.layers[0].self_attn.q_proj.weight.detach().clone()
    cause_result = train_part(
        model, encoded["cause"], "cause", epochs=args.epochs, batch_size=args.batch_size,
        learning_rate=args.learning_rate, seed=args.seed, pad_id=tokenizer.pad_token_id,
    )
    safety_before = {name: value.clone() for name, value in model.adapter_state("safety").items()}
    cause_after = {name: value.clone() for name, value in model.adapter_state("cause").items()}
    safety_result = train_part(
        model, encoded["safety"], "safety", epochs=args.epochs, batch_size=args.batch_size,
        learning_rate=args.learning_rate, seed=args.seed + 1000, pad_id=tokenizer.pad_token_id,
    )
    shared_unchanged = torch.equal(shared_before, model.shared.model.layers[0].self_attn.q_proj.weight)
    cause_unchanged_during_safety = all(torch.equal(value, model.adapter_state("cause")[name]) for name, value in cause_after.items())
    safety_unchanged_before_own_training = any(not torch.equal(value, model.adapter_state("safety")[name]) for name, value in safety_before.items())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_file(model.adapter_state("cause"), str(args.output_dir / "cause_track.safetensors"))
    save_file(model.adapter_state("safety"), str(args.output_dir / "safety_track.safetensors"))
    result = {
        "experiment_id": "E005", "gate": "5B", "kind": "personal_track_training",
        "status": "development_smoke" if args.limit else "trained_exam_not_run",
        "design_content_sha256": design["content_sha256"],
        "curriculum_content_sha256": curriculum["content_sha256"],
        "model_weights_sha256": sha256_file(args.model / "model.safetensors"),
        "seed": args.seed, "rank": 8, "track_layers": [6, 21],
        "cause": cause_result, "safety": safety_result,
        "shared_unchanged": shared_unchanged,
        "cause_unchanged_during_safety_training": cause_unchanged_during_safety,
        "safety_changed_only_during_own_training": safety_unchanged_before_own_training,
        "merger_trained": False, "exam_run": False,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--curriculum", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=24082026)
    parser.add_argument("--threads", type=int, default=20)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
