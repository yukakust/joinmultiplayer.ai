#!/usr/bin/env python3
"""Measured, offline, CPU-only launch of the pinned E004 frozen base."""

from __future__ import annotations

import argparse
import json
import os
import resource
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path", type=Path)
    parser.add_argument("--threads", type=int, default=22)
    parser.add_argument("--max-new-tokens", type=int, default=12)
    args = parser.parse_args()

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(17082026)

    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        local_files_only=True,
        dtype=torch.float32,
    )
    model.eval()
    model.requires_grad_(False)
    loaded = time.perf_counter()

    prompt = "A pocket intelligence is"
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.inference_mode():
        logits = model(**inputs).logits
        generated = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    finished = time.perf_counter()

    new_tokens = generated.shape[-1] - inputs.input_ids.shape[-1]
    generation_seconds = finished - loaded
    result = {
        "kind": "frozen_base_smoke",
        "model_path": str(args.model_path),
        "device": "cpu",
        "dtype": str(next(model.parameters()).dtype),
        "threads": args.threads,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "trainable_parameters": sum(
            parameter.numel() for parameter in model.parameters() if parameter.requires_grad
        ),
        "load_seconds": round(loaded - started, 4),
        "generation_seconds": round(generation_seconds, 4),
        "new_tokens": int(new_tokens),
        "tokens_per_second": round(new_tokens / generation_seconds, 4),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
        "logits_shape": list(logits.shape),
        "logits_finite": bool(torch.isfinite(logits).all().item()),
        "prompt": prompt,
        "completion": tokenizer.decode(generated[0], skip_special_tokens=True),
    }
    assert result["trainable_parameters"] == 0
    assert result["logits_finite"]
    assert result["new_tokens"] > 0
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
