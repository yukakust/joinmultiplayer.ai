#!/usr/bin/env python3
"""A2 development run: local learned memory-token banks with one source decode."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import time
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from arena_common import Contribution, assemble, book_index, expected_local_result, load_world


SEED = 17082026
CAPSULE_DIM = 64
MEMORY_SLOTS = 16
ANSWER_CLASSES = 998  # 0..996 plus ABSTAIN
STEPS = 2000
LEARNING_RATE = 0.01


class NeuralMemoryPocket(nn.Module):
    def __init__(self, input_dim: int, capsule_dim: int = CAPSULE_DIM, slots: int = MEMORY_SLOTS):
        super().__init__()
        self.query = nn.Linear(input_dim, capsule_dim, bias=False)
        self.keys = nn.Parameter(torch.randn(slots, capsule_dim) / math.sqrt(capsule_dim))
        self.values = nn.Parameter(torch.randn(slots, capsule_dim) / math.sqrt(capsule_dim))

    def forward(self, query_embedding: torch.Tensor) -> torch.Tensor:
        query = F.normalize(self.query(query_embedding), dim=-1)
        keys = F.normalize(self.keys, dim=-1)
        weights = torch.softmax(query @ keys.T * 8.0, dim=-1)
        return weights @ self.values


class SourceDecoder(nn.Module):
    def __init__(self, capsule_dim: int = CAPSULE_DIM):
        super().__init__()
        self.norm = nn.LayerNorm(capsule_dim)
        self.output = nn.Linear(capsule_dim, ANSWER_CLASSES)

    def forward(self, capsule: torch.Tensor) -> torch.Tensor:
        return self.output(self.norm(capsule))


def frozen_query_embeddings(model_path: Path, world: dict) -> tuple[dict[tuple[str, str], torch.Tensor], str]:
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        model_path, local_files_only=True, dtype=torch.float32
    )
    base.eval().requires_grad_(False)
    embedding = base.get_input_embeddings()
    result = {}
    with torch.inference_mode():
        for book in world["books"]:
            for fact in book["preview_facts"]:
                text = f"Pocket {book['pocket_id']} local record {fact['key']}"
                ids = tokenizer(text, return_tensors="pt", add_special_tokens=False).input_ids
                result[(book["pocket_id"], fact["key"])] = embedding(ids).mean(dim=1).squeeze(0).cpu()
    digest = hashlib.sha256(embedding.weight.detach().cpu().numpy().tobytes()).hexdigest()
    del base
    return result, digest


def target_for(world: dict, pocket_id: str, fact_key: str) -> int:
    book = book_index(world)[pocket_id]
    fact = next(item for item in book["preview_facts"] if item["key"] == fact_key)
    if fact["status"] == "deleted":
        return 997
    procedure = book["procedure"]
    return (
        procedure["multiplier"] * fact["current_value"] + procedure["bias"]
    ) % procedure["modulus"]


def train(world: dict, embeddings: dict, steps: int = STEPS):
    input_dim = next(iter(embeddings.values())).numel()
    pockets = nn.ModuleDict(
        {book["pocket_id"]: NeuralMemoryPocket(input_dim) for book in world["books"]}
    )
    decoder = SourceDecoder()
    parameters = [*pockets.parameters(), *decoder.parameters()]
    optimizer = torch.optim.AdamW(parameters, lr=LEARNING_RATE)
    examples = [
        (book["pocket_id"], fact["key"], target_for(world, book["pocket_id"], fact["key"]))
        for book in world["books"]
        for fact in book["preview_facts"]
    ]

    def logits_for_all():
        capsules = torch.stack([pockets[pocket](embeddings[(pocket, key)]) for pocket, key, _ in examples])
        return decoder(capsules)

    with torch.no_grad():
        before_logits = logits_for_all()
        before_accuracy = float(
            (before_logits.argmax(dim=-1) == torch.tensor([target for _, _, target in examples])).float().mean()
        )
    losses = []
    targets = torch.tensor([target for _, _, target in examples])
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        logits = logits_for_all()
        loss = F.cross_entropy(logits, targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    with torch.no_grad():
        after_logits = logits_for_all()
        after_accuracy = float((after_logits.argmax(dim=-1) == targets).float().mean())
    return pockets, decoder, {
        "examples": len(examples),
        "steps": steps,
        "learning_rate": LEARNING_RATE,
        "trainable_parameters": sum(parameter.numel() for parameter in parameters),
        "before_accuracy": before_accuracy,
        "after_accuracy": after_accuracy,
        "first_loss": losses[0],
        "last_loss": losses[-1],
    }


def evaluate_tasks(world: dict, embeddings: dict, pockets, decoder) -> dict:
    rows = []
    network_bytes = 0
    segment_correct = segment_total = 0
    with torch.inference_mode():
        for task in world["tasks"]:
            contributions = []
            for requested in task["derivation"]["contributions"]:
                pocket = requested["pocket_id"]
                capsule = pockets[pocket](embeddings[(pocket, requested["fact_key"])])
                network_bytes += capsule.numel() * capsule.element_size()
                predicted = int(decoder(capsule).argmax())
                result = None if predicted == 997 else predicted
                contributions.append(Contribution(task["id"], pocket, result))
                segment_total += 1
                segment_correct += result == expected_local_result(world, task, pocket)
            assembly = assemble(task, contributions)
            rows.append(
                {
                    "task_id": task["id"],
                    "expected": task["answer"],
                    "actual": assembly.answer,
                    "correct": assembly.answer == task["answer"],
                }
            )
    return {
        "tasks": len(rows),
        "complete_exact_match": sum(row["correct"] for row in rows) / len(rows),
        "segment_exact_match": segment_correct / segment_total,
        "estimated_network_bytes": network_bytes,
        "failures": [row for row in rows if not row["correct"]],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("model_path", type=Path)
    parser.add_argument("--threads", type=int, default=22)
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(SEED)
    started = time.perf_counter()
    world = load_world(args.world)
    embeddings, embedding_sha256 = frozen_query_embeddings(args.model_path, world)
    pockets, decoder, training = train(world, embeddings)
    evaluation = evaluate_tasks(world, embeddings, pockets, decoder)
    result = {
        "experiment_id": "E004",
        "protocol_version": "arena-v0.1",
        "architecture_id": "neural_memory",
        "status": "passed" if evaluation["complete_exact_match"] == 1.0 else "failed",
        "claim_status": "public_development_only",
        "seed": SEED,
        "base_embedding_sha256": embedding_sha256,
        "base_trainable_parameters": 0,
        "capsule_dim": CAPSULE_DIM,
        "memory_slots_per_pocket": MEMORY_SLOTS,
        "training": training,
        "evaluation": evaluation,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
        "claim_boundary": "Training and evaluation reuse the same 64 public records. This is an implementation smoke, not held-out generalization.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
