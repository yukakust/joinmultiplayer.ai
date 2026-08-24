from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file
from transformers import AutoModelForCausalLM, AutoTokenizer

from gate5b_model import ParallelTrackQwen
from train_gate5b_tracks import causal_loss, collate, encode_lesson, sha256_file


def tensor_digest(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def load_adapter(model: ParallelTrackQwen, part: str, path: Path) -> str:
    saved = load_file(str(path), device="cpu")
    expected = model.adapter_state(part)
    if set(saved) != set(expected):
        missing = sorted(set(expected) - set(saved))
        extra = sorted(set(saved) - set(expected))
        raise ValueError(f"{part} adapter keys differ: missing={missing[:3]} extra={extra[:3]}")
    current = model.state_dict()
    with torch.no_grad():
        for name, tensor in saved.items():
            if current[name].shape != tensor.shape:
                raise ValueError(f"{part} adapter shape differs for {name}")
            current[name].copy_(tensor)
    loaded = model.adapter_state(part)
    if not all(torch.equal(saved[name], loaded[name]) for name in saved):
        raise RuntimeError(f"{part} adapter did not load exactly")
    return tensor_digest(loaded)


def train_merger(
    model: ParallelTrackQwen,
    encoded: list[dict],
    *,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    seed: int,
    pad_id: int,
) -> dict:
    model.set_trainable("merger")
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=learning_rate, weight_decay=0.01)
    losses: list[float] = []
    started = time.monotonic()
    for epoch in range(epochs):
        order = list(range(len(encoded)))
        random.Random(seed + epoch).shuffle(order)
        for start in range(0, len(order), batch_size):
            rows = [encoded[index] for index in order[start : start + batch_size]]
            input_ids, labels, attention = collate(rows, pad_id)
            optimizer.zero_grad(set_to_none=True)
            output = model(input_ids=input_ids, attention_mask=attention, mode="correct")
            loss = causal_loss(output.logits, labels)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite merger loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimizer.step()
            losses.append(loss.item())
            print(json.dumps({"part": "merger", "epoch": epoch + 1, "step": len(losses), "loss": round(loss.item(), 6)}), flush=True)
    model.freeze_all()
    window = min(8, len(losses))
    return {
        "epochs": epochs,
        "lessons": len(encoded),
        "steps": len(losses),
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "trainable_parameters": sum(parameter.numel() for parameter in trainable),
        "loss_mean_first": sum(losses[:window]) / window,
        "loss_mean_last": sum(losses[-window:]) / window,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def run(args: argparse.Namespace) -> dict:
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    design = json.loads(args.design.read_text(encoding="utf-8"))
    curriculum = json.loads(args.curriculum.read_text(encoding="utf-8"))
    track_summary = json.loads((args.track_dir / "summary.json").read_text(encoding="utf-8"))
    if design["status"] != "locked_not_run" or curriculum["status"] != "frozen_before_training":
        raise ValueError("Gate 5B inputs are not frozen")
    if track_summary["status"] != "trained_exam_not_run" or track_summary["merger_trained"] or track_summary["exam_run"]:
        raise ValueError("personal-track checkpoint is not clean")
    if track_summary["design_content_sha256"] != design["content_sha256"] or track_summary["curriculum_content_sha256"] != curriculum["content_sha256"]:
        raise ValueError("personal-track checkpoint belongs to different frozen inputs")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True
    ).eval()
    model = ParallelTrackQwen(base)
    cause_digest = load_adapter(model, "cause", args.track_dir / "cause_track.safetensors")
    safety_digest = load_adapter(model, "safety", args.track_dir / "safety_track.safetensors")
    cause_before = tensor_digest(model.adapter_state("cause"))
    safety_before = tensor_digest(model.adapter_state("safety"))
    merger_before = tensor_digest(model.adapter_state("merger"))

    lessons = curriculum["merger_lessons"][: args.limit or None]
    encoded = [encode_lesson(tokenizer, row, args.max_length) for row in lessons]
    merger_result = train_merger(
        model,
        encoded,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
        pad_id=tokenizer.pad_token_id,
    )
    cause_after = tensor_digest(model.adapter_state("cause"))
    safety_after = tensor_digest(model.adapter_state("safety"))
    merger_after = tensor_digest(model.adapter_state("merger"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_file(model.adapter_state("merger"), str(args.output_dir / "merger.safetensors"))
    result = {
        "experiment_id": "E005",
        "gate": "5B",
        "kind": "hidden_state_merger_training",
        "status": "development_smoke" if args.limit else "merger_trained_exam_not_run",
        "design_content_sha256": design["content_sha256"],
        "curriculum_content_sha256": curriculum["content_sha256"],
        "model_weights_sha256": sha256_file(args.model / "model.safetensors"),
        "seed": args.seed,
        "cause_adapter_digest": cause_digest,
        "safety_adapter_digest": safety_digest,
        "merger": merger_result,
        "cause_unchanged": cause_before == cause_after,
        "safety_unchanged": safety_before == safety_after,
        "merger_changed": merger_before != merger_after,
        "exam_run": False,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--curriculum", type=Path, required=True)
    parser.add_argument("--track-dir", type=Path, required=True)
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
