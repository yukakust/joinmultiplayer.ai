#!/usr/bin/env python3
"""Gate 2: frozen Qwen base-only answers with no E005 documents or adapters."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_ID = "Qwen/Qwen3-0.6B-Base"
MODEL_REVISION = "da87bfb608c14b7cf20ba1ce41287e8de496c0cd"
MODEL_SHA256 = "cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba"
SEED = 17082026
MAX_NEW_TOKENS = 96

PROMPTS = {
    "en": (
        "Answer using only knowledge already present in the model. "
        "You have no external documents. If the evidence needed to decide is missing, say so plainly.\n\n"
        "Question: {question}\n\nAnswer:"
    ),
    "ru": (
        "Ответьте, используя только знания, уже находящиеся в модели. "
        "У вас нет внешних документов. Если для решения не хватает данных, скажите об этом прямо.\n\n"
        "Вопрос: {question}\n\nОтвет:"
    ),
}

TARGET_MARKERS = {
    "PUBLIC-01": {"en": ["niv-3", "calibrat"], "ru": ["niv-3", "калибр"]},
    "PUBLIC-02": {"en": ["isolat"], "ru": ["изолир"]},
    "PUBLIC-03": {"en": ["f9", "replac"], "ru": ["f9", "замен"]},
    "PUBLIC-04": {"en": ["t4", "thaw"], "ru": ["t4", "отта"]},
    "PUBLIC-05": {"en": ["north sector", "vector six"], "ru": ["северн", "вектор"]},
    "PUBLIC-06": {"en": ["spectrum"], "ru": ["спектр"]},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def marker_hits(task_id: str, language: str, output: str) -> list[str]:
    lowered = output.lower()
    return [marker for marker in TARGET_MARKERS[task_id][language] if marker in lowered]


def run(world: dict, model_path: Path, threads: int) -> dict:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(SEED)
    started = time.perf_counter()
    actual_sha256 = sha256_file(model_path / "model.safetensors")
    if actual_sha256 != MODEL_SHA256:
        raise ValueError(f"model sha256 mismatch: {actual_sha256}")

    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float32,
    )
    model.eval()
    rows = []
    with torch.inference_mode():
        for task in world["tasks"]:
            outputs = {}
            for language in ("en", "ru"):
                prompt = PROMPTS[language].format(question=task["question"][language])
                inputs = tokenizer(prompt, return_tensors="pt")
                generated = model.generate(
                    **inputs,
                    do_sample=False,
                    max_new_tokens=MAX_NEW_TOKENS,
                    pad_token_id=tokenizer.eos_token_id,
                )
                new_tokens = generated[0, inputs["input_ids"].shape[1]:]
                output = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
                outputs[language] = {
                    "prompt": prompt,
                    "output": output,
                    "generated_tokens": int(new_tokens.numel()),
                    "target_marker_hits": marker_hits(task["id"], language, output),
                }
            rows.append({
                "task_id": task["id"],
                "family": task["family"],
                "expected_main_claim": task["expected"]["main_claim"],
                "outputs": outputs,
                "manual_review": "pending",
            })

    return {
        "experiment_id": "E005",
        "protocol_version": world["protocol_version"],
        "gate": 2,
        "kind": "frozen_base_only_preflight",
        "status": "completed_awaiting_manual_review",
        "claim_status": "public_development_only",
        "model": {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "model_sha256": actual_sha256,
            "dtype": "float32",
            "training_or_weight_update": False,
        },
        "inference": {
            "seed": SEED,
            "decoding": "greedy",
            "max_new_tokens": MAX_NEW_TOKENS,
            "languages": ["en", "ru"],
            "rag": False,
            "documents_in_prompt": False,
            "adapter": None,
            "internet": False,
        },
        "prompt_templates": PROMPTS,
        "rows": rows,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
        "claim_boundary": {
            "en": "Marker hits are navigation aids, not correctness labels. A human must inspect every raw answer. This run tests prior leakage and base behaviour only; it does not test RAG, DoRA, routing, or swarm composition.",
            "ru": "Совпадения маркеров помогают навигации, но не являются оценкой правильности. Человек должен прочитать каждый сырой ответ. Этот запуск проверяет только утечку prior и поведение базы, а не RAG, DoRA, routing или композицию swarm."
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("model_path", type=Path)
    parser.add_argument("--threads", type=int, default=22)
    args = parser.parse_args()
    world = json.loads(args.world.read_text(encoding="utf-8"))
    print(json.dumps(run(world, args.model_path, args.threads), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
