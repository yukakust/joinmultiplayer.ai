#!/usr/bin/env python3
"""A3 development run: bounded personal deltas relative to a frozen common path."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import resource
import time
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

from arena_common import Contribution, assemble, expected_local_result, load_world
from run_neural_memory import ANSWER_CLASSES, SEED, frozen_query_embeddings, target_for


LATENT_DIM = 64
MAX_DELTA_NORM = 1.0
STEPS = 2000
LEARNING_RATE = 0.01


class CommonTower(nn.Module):
    def __init__(self, input_dim: int, latent_dim: int = LATENT_DIM):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, latent_dim),
            nn.GELU(),
            nn.Linear(latent_dim, latent_dim),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.layers(value)


class PersonalDelta(nn.Module):
    def __init__(self, common: CommonTower):
        super().__init__()
        self.personal = copy.deepcopy(common)
        self.personal.train().requires_grad_(True)
        self.common = common

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        raw = self.personal(value) - self.common(value)
        norm = raw.norm(dim=-1, keepdim=True).clamp_min(1e-8)
        scale = torch.clamp(MAX_DELTA_NORM / norm, max=1.0)
        return raw * scale


class FinalLayers(nn.Module):
    def __init__(self, latent_dim: int = LATENT_DIM):
        super().__init__()
        self.norm = nn.LayerNorm(latent_dim)
        self.output = nn.Linear(latent_dim, ANSWER_CLASSES)

    def forward(self, z0: torch.Tensor, delta: torch.Tensor) -> torch.Tensor:
        return self.output(self.norm(z0 + delta))


def digest(module: nn.Module) -> str:
    value = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        value.update(name.encode())
        value.update(tensor.detach().cpu().numpy().tobytes())
    return value.hexdigest()


def train(world: dict, embeddings: dict):
    input_dim = next(iter(embeddings.values())).numel()
    common = CommonTower(input_dim).eval().requires_grad_(False)
    common_before = digest(common)
    pockets = nn.ModuleDict(
        {book["pocket_id"]: PersonalDelta(common) for book in world["books"]}
    )
    final = FinalLayers()
    parameters = [
        *[parameter for pocket in pockets.values() for parameter in pocket.personal.parameters()],
        *final.parameters(),
    ]
    optimizer = torch.optim.AdamW(parameters, lr=LEARNING_RATE)
    examples = [
        (book["pocket_id"], fact["key"], target_for(world, book["pocket_id"], fact["key"]))
        for book in world["books"]
        for fact in book["preview_facts"]
    ]

    def representations():
        xs = torch.stack([embeddings[(pocket, key)] for pocket, key, _ in examples])
        z0 = F.normalize(common(xs), dim=-1)
        deltas = torch.stack(
            [pockets[pocket](embeddings[(pocket, key)]) for pocket, key, _ in examples]
        )
        return z0, deltas

    targets = torch.tensor([target for _, _, target in examples])
    with torch.no_grad():
        initial_z0, initial_delta = representations()
        fresh_delta_max = float(initial_delta.norm(dim=-1).max())
        before_accuracy = float(
            (final(initial_z0, initial_delta).argmax(dim=-1) == targets).float().mean()
        )
    losses = []
    for _ in range(STEPS):
        optimizer.zero_grad(set_to_none=True)
        z0, deltas = representations()
        loss = F.cross_entropy(final(z0, deltas), targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    with torch.no_grad():
        z0, deltas = representations()
        after_accuracy = float((final(z0, deltas).argmax(dim=-1) == targets).float().mean())
        without_z0_accuracy = float(
            (final(torch.zeros_like(z0), deltas).argmax(dim=-1) == targets).float().mean()
        )
        max_observed_delta_norm = float(deltas.norm(dim=-1).max())
    common_after = digest(common)
    assert common_before == common_after
    return common, pockets, final, {
        "examples": len(examples),
        "steps": STEPS,
        "learning_rate": LEARNING_RATE,
        "trainable_parameters": sum(parameter.numel() for parameter in parameters),
        "common_tower_parameters": sum(parameter.numel() for parameter in common.parameters()),
        "common_hash_before": common_before,
        "common_hash_after": common_after,
        "fresh_delta_max_norm": fresh_delta_max,
        "max_observed_delta_norm": max_observed_delta_norm,
        "before_accuracy": before_accuracy,
        "after_accuracy": after_accuracy,
        "without_z0_accuracy": without_z0_accuracy,
        "first_loss": losses[0],
        "last_loss": losses[-1],
    }


def evaluate_tasks(world: dict, embeddings: dict, common, pockets, final) -> dict:
    rows = []
    segment_correct = segment_total = network_bytes = 0
    with torch.inference_mode():
        for task in world["tasks"]:
            contributions = []
            for requested in task["derivation"]["contributions"]:
                pocket = requested["pocket_id"]
                x = embeddings[(pocket, requested["fact_key"])]
                z0 = F.normalize(common(x), dim=-1)
                delta = pockets[pocket](x)
                network_bytes += delta.numel() * delta.element_size()
                predicted = int(final(z0, delta).argmax())
                result = None if predicted == 997 else predicted
                contributions.append(Contribution(task["id"], pocket, result))
                segment_total += 1
                segment_correct += result == expected_local_result(world, task, pocket)
            assembly = assemble(task, contributions)
            rows.append({
                "task_id": task["id"],
                "expected": task["answer"],
                "actual": assembly.answer,
                "correct": assembly.answer == task["answer"],
            })
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
    common, pockets, final, training = train(world, embeddings)
    evaluation = evaluate_tasks(world, embeddings, common, pockets, final)
    result = {
        "experiment_id": "E004",
        "protocol_version": "arena-v0.1",
        "architecture_id": "latent_delta",
        "status": "passed" if evaluation["complete_exact_match"] == 1.0 else "failed",
        "claim_status": "public_development_only",
        "seed": SEED,
        "base_embedding_sha256": embedding_sha256,
        "base_trainable_parameters": 0,
        "latent_dim": LATENT_DIM,
        "max_delta_norm": MAX_DELTA_NORM,
        "training": training,
        "evaluation": evaluation,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
        "claim_boundary": "Training and evaluation reuse the same public records; this tests the delta equation and interface, not held-out generalization.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
