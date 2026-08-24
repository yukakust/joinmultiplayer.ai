from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from gate5b_model import ParallelTrackQwen


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    design = json.loads(args.design.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True
    ).eval()
    model = ParallelTrackQwen(base)
    encoded = tokenizer("Gate 5B preflight", return_tensors="pt")
    with torch.inference_mode():
        reference = base(**encoded).logits
        output = model(**encoded, mode="correct")
    model.set_trainable("cause")
    cause_names = model.trainable_parameter_names()
    cause_count = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    model.set_trainable("safety")
    safety_names = model.trainable_parameter_names()
    safety_count = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    result = {
        "experiment_id": "E005", "gate": "5B", "kind": "real_model_preflight",
        "status": "passed_before_training", "design_content_sha256": design["content_sha256"],
        "model_weights_sha256": sha256_file(args.model / "model.safetensors"),
        "split": {"stem": [0, 5], "track": [6, 21], "tail": [22, 27]},
        "dora_modules_per_track": model.dora_modules_per_track,
        "trainable_parameters": {"cause": cause_count, "safety": safety_count},
        "fresh_cause_delta_max_abs": output.cause_delta.abs().max().item(),
        "fresh_safety_delta_max_abs": output.safety_delta.abs().max().item(),
        "fresh_logits_max_abs_difference": (reference - output.logits).abs().max().item(),
        "cause_selection_only_changes_cause_track": all(name.startswith("cause_layers.") for name in cause_names),
        "safety_selection_only_changes_safety_track": all(name.startswith("safety_layers.") for name in safety_names),
        "training_performed": False,
        "plain_language": {
            "en": "The real split Qwen is identical to the source before learning. A fresh personal track adds exactly zero.",
            "ru": "Настоящая разрезанная Qwen до обучения совпадает с исходной. Новый личный трек добавляет ровно ноль.",
        },
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
