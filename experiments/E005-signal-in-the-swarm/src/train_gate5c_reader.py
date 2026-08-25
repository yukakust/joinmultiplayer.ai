from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch
from safetensors.torch import save_file
from transformers import AutoModelForCausalLM, AutoTokenizer

from gate5c_model import SeparateShelfQwen
from train_gate5b_merger import load_adapter, tensor_digest
from train_gate5b_tracks import sha256_file


def encode_next_token_examples(tokenizer, lesson: dict, max_length: int) -> list[dict]:
    prompt_text = tokenizer.apply_chat_template(
        [{"role": "user", "content": lesson["prompt"]}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
    target = lesson["target"]
    sentence_break = target.find(". ")
    if sentence_break < 0:
        raise ValueError(f"lesson has no cause/action boundary: {lesson['id']}")
    cause_text = target[: sentence_break + 1]
    full_ids = tokenizer.encode(prompt_text + target + tokenizer.eos_token, add_special_tokens=False)
    cause_boundary = len(tokenizer.encode(prompt_text + cause_text, add_special_tokens=False))
    if len(full_ids) > max_length:
        raise ValueError(f"lesson exceeds max length: {lesson['id']} ({len(full_ids)} > {max_length})")
    if cause_boundary <= len(prompt_ids) or cause_boundary >= len(full_ids):
        raise ValueError(f"invalid cause/action token boundary: {lesson['id']}")
    examples = []
    for target_index in range(len(prompt_ids), len(full_ids)):
        examples.append({
            "lesson_id": lesson["id"],
            "language": lesson["language"],
            "input_ids": full_ids[:target_index],
            "target_id": full_ids[target_index],
            "part": "cause" if target_index < cause_boundary else "safety",
            "weight": 1.0 if target_index < cause_boundary else 2.0,
        })
    return examples


def collate_examples(rows: list[dict], pad_id: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    width = max(len(row["input_ids"]) for row in rows)
    ids, attention, targets, weights = [], [], [], []
    for row in rows:
        padding = width - len(row["input_ids"])
        ids.append(row["input_ids"] + [pad_id] * padding)
        attention.append([1] * len(row["input_ids"]) + [0] * padding)
        targets.append(row["target_id"])
        weights.append(row["weight"])
    return torch.tensor(ids), torch.tensor(attention), torch.tensor(targets), torch.tensor(weights)


def lesson_subset(lessons: list[dict], limit_per_language: int | None) -> list[dict]:
    if not limit_per_language:
        return lessons
    return [
        row
        for language in ("en", "ru")
        for row in [item for item in lessons if item["language"] == language][:limit_per_language]
    ]


def bucketed_batches(examples: list[dict], batch_size: int, seed: int) -> list[list[dict]]:
    buckets: dict[int, list[dict]] = {}
    for row in examples:
        buckets.setdefault(len(row["input_ids"]) // 8, []).append(row)
    rng = random.Random(seed)
    batches = []
    for key in sorted(buckets):
        rows = buckets[key][:]
        rng.shuffle(rows)
        batches.extend(rows[start : start + batch_size] for start in range(0, len(rows), batch_size))
    rng.shuffle(batches)
    return batches


def train_reader(model, examples: list[dict], *, epochs: int, batch_size: int, learning_rate: float, seed: int, pad_id: int) -> dict:
    model.set_shelf_trainable()
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=learning_rate, weight_decay=0.01)
    losses = []
    cause_losses = []
    safety_losses = []
    started = time.monotonic()
    for epoch in range(epochs):
        for rows in bucketed_batches(examples, batch_size, seed + epoch):
            input_ids, attention, targets, weights = collate_examples(rows, pad_id)
            optimizer.zero_grad(set_to_none=True)
            output = model.forward_shelves(input_ids, attention, mode="correct_shelves")
            per_row = torch.nn.functional.cross_entropy(output.next_logits, targets, reduction="none")
            loss = (per_row * weights).sum() / weights.sum()
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite shelf-reader loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimizer.step()
            loss_value = float(loss.detach())
            losses.append(loss_value)
            cause_losses.extend(float(value.detach()) for value, row in zip(per_row, rows) if row["part"] == "cause")
            safety_losses.extend(float(value.detach()) for value, row in zip(per_row, rows) if row["part"] == "safety")
            print(json.dumps({"epoch": epoch + 1, "step": len(losses), "loss": round(loss_value, 6)}), flush=True)
    model.freeze_all()
    window = max(1, min(16, len(losses) // 4))
    return {
        "epochs": epochs,
        "lessons": len({row["lesson_id"] for row in examples}),
        "next_token_examples": len(examples),
        "steps": len(losses),
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "trainable_parameters": sum(parameter.numel() for parameter in trainable),
        "loss_mean_first": sum(losses[:window]) / window,
        "loss_mean_last": sum(losses[-window:]) / window,
        "cause_token_loss_mean": sum(cause_losses) / len(cause_losses),
        "safety_token_loss_mean": sum(safety_losses) / len(safety_losses),
        "loss_trace": [round(value, 6) for value in losses],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def run(args: argparse.Namespace) -> dict:
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    design = json.loads(args.design.read_text(encoding="utf-8"))
    curriculum = json.loads(args.curriculum.read_text(encoding="utf-8"))
    if design["status"] != "locked_before_training" or design["training_started"] or design["exam_run"]:
        raise ValueError("Gate 5C design is not clean and locked")
    if curriculum["status"] != "frozen_before_training":
        raise ValueError("Gate 5B curriculum is not frozen")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True
    ).eval()
    model = SeparateShelfQwen(base)
    cause_digest = load_adapter(model, "cause", args.track_dir / "cause_track.safetensors")
    safety_digest = load_adapter(model, "safety", args.track_dir / "safety_track.safetensors")
    cause_before = tensor_digest(model.adapter_state("cause"))
    safety_before = tensor_digest(model.adapter_state("safety"))
    reader_before = tensor_digest(model.shelf_state())
    base_hash = sha256_file(args.model / "model.safetensors")

    lessons = lesson_subset(curriculum["merger_lessons"], args.limit_per_language)
    examples = [example for lesson in lessons for example in encode_next_token_examples(tokenizer, lesson, args.max_length)]
    training = train_reader(
        model,
        examples,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
        pad_id=tokenizer.pad_token_id,
    )
    result = {
        "experiment_id": "E005",
        "gate": "5C",
        "version": "0.1",
        "kind": "separate_shelf_reader_training",
        "status": "development_smoke" if args.limit_per_language else "reader_trained_exam_not_run",
        "model_weights_sha256": base_hash,
        "cause_adapter_digest": cause_digest,
        "safety_adapter_digest": safety_digest,
        "cause_unchanged": cause_before == tensor_digest(model.adapter_state("cause")),
        "safety_unchanged": safety_before == tensor_digest(model.adapter_state("safety")),
        "reader_changed": reader_before != tensor_digest(model.shelf_state()),
        "shared_and_tail_trainable_parameters": 0,
        "safety_token_weight": 2.0,
        "training": training,
        "exam_run": False,
        "plain_language": {
            "en": "The two old personal tracks stayed frozen. Only the small reader that puts their signals on two separate shelves learned.",
            "ru": "Два старых личных трека остались замороженными. Учился только маленький читатель, который кладёт их сигналы на две разные полки."
        }
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_file(model.shelf_state(), str(args.output_dir / "shelf_reader.safetensors"))
    (args.output_dir / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.public_summary:
        args.public_summary.parent.mkdir(parents=True, exist_ok=True)
        args.public_summary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--curriculum", type=Path, required=True)
    parser.add_argument("--track-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--seed", type=int, default=25082026)
    parser.add_argument("--threads", type=int, default=20)
    parser.add_argument("--limit-per-language", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
