#!/usr/bin/env python3
"""A4 development run: personal FFN experts invoked for every output symbol."""

from __future__ import annotations

import argparse
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
from run_neural_memory import SEED, frozen_query_embeddings, target_for


HIDDEN_DIM = 64
EXPERT_DIM = 128
OUTPUT_SYMBOLS = 11  # digits 0..9 and ABSTAIN=10
BOS = 11
STEPS = 2000
LEARNING_RATE = 0.01
MAX_EXPERT_NORM = 1.0


def encode_result(value: int) -> list[int]:
    if value == 997:
        return [10, 10, 10]
    return [int(character) for character in f"{value:03d}"]


def decode_result(symbols: list[int]) -> int | None | str:
    if symbols == [10, 10, 10]:
        return None
    if any(symbol < 0 or symbol > 9 for symbol in symbols):
        return "INVALID"
    return int("".join(str(symbol) for symbol in symbols))


class FrozenTokenStem(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.query = nn.Linear(input_dim, hidden_dim)
        self.position = nn.Embedding(3, hidden_dim)
        self.previous = nn.Embedding(12, hidden_dim)
        self.eval().requires_grad_(False)

    def forward(self, query: torch.Tensor, position: torch.Tensor, previous: torch.Tensor):
        return F.normalize(self.query(query) + self.position(position) + self.previous(previous), dim=-1)


class PersonalFFNExpert(nn.Module):
    def __init__(self, hidden_dim: int = HIDDEN_DIM, expert_dim: int = EXPERT_DIM):
        super().__init__()
        self.up = nn.Linear(hidden_dim, expert_dim)
        self.down = nn.Linear(expert_dim, hidden_dim)
        nn.init.zeros_(self.down.weight)
        nn.init.zeros_(self.down.bias)

    def forward(self, hidden: torch.Tensor):
        raw = self.down(F.gelu(self.up(hidden)))
        norm = raw.norm(dim=-1, keepdim=True).clamp_min(1e-8)
        return raw * torch.clamp(MAX_EXPERT_NORM / norm, max=1.0)


class TokenHead(nn.Module):
    def __init__(self, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.norm = nn.LayerNorm(hidden_dim)
        self.output = nn.Linear(hidden_dim, OUTPUT_SYMBOLS)

    def forward(self, z0: torch.Tensor, expert_delta: torch.Tensor):
        return self.output(self.norm(z0 + expert_delta))


def digest(module: nn.Module) -> str:
    value = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        value.update(name.encode())
        value.update(tensor.detach().cpu().numpy().tobytes())
    return value.hexdigest()


def build_token_examples(world: dict):
    examples = []
    for book in world["books"]:
        pocket = book["pocket_id"]
        for fact in book["preview_facts"]:
            symbols = encode_result(target_for(world, pocket, fact["key"]))
            previous = BOS
            for position, symbol in enumerate(symbols):
                examples.append((pocket, fact["key"], position, previous, symbol))
                previous = symbol
    return examples


def train(world: dict, embeddings: dict):
    input_dim = next(iter(embeddings.values())).numel()
    stem = FrozenTokenStem(input_dim)
    stem_before = digest(stem)
    experts = nn.ModuleDict({book["pocket_id"]: PersonalFFNExpert() for book in world["books"]})
    head = TokenHead()
    parameters = [*experts.parameters(), *head.parameters()]
    optimizer = torch.optim.AdamW(parameters, lr=LEARNING_RATE)
    examples = build_token_examples(world)

    def logits_for_all(use_experts: bool = True):
        query = torch.stack([embeddings[(pocket, key)] for pocket, key, _, _, _ in examples])
        position = torch.tensor([position for _, _, position, _, _ in examples])
        previous = torch.tensor([previous for _, _, _, previous, _ in examples])
        z0 = stem(query, position, previous)
        if use_experts:
            delta = torch.stack([experts[pocket](z0[index]) for index, (pocket, *_rest) in enumerate(examples)])
        else:
            delta = torch.zeros_like(z0)
        return head(z0, delta), delta

    targets = torch.tensor([symbol for *_, symbol in examples])
    with torch.no_grad():
        before_logits, fresh_delta = logits_for_all()
        before_accuracy = float((before_logits.argmax(dim=-1) == targets).float().mean())
        fresh_delta_max_norm = float(fresh_delta.norm(dim=-1).max())
    losses = []
    for _ in range(STEPS):
        optimizer.zero_grad(set_to_none=True)
        logits, _ = logits_for_all()
        loss = F.cross_entropy(logits, targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    with torch.no_grad():
        after_logits, trained_delta = logits_for_all()
        after_accuracy = float((after_logits.argmax(dim=-1) == targets).float().mean())
        no_expert_logits, _ = logits_for_all(use_experts=False)
        without_experts_accuracy = float(
            (no_expert_logits.argmax(dim=-1) == targets).float().mean()
        )
        max_observed_expert_norm = float(trained_delta.norm(dim=-1).max())
    stem_after = digest(stem)
    assert stem_before == stem_after
    return stem, experts, head, {
        "records": 64,
        "token_examples": len(examples),
        "steps": STEPS,
        "learning_rate": LEARNING_RATE,
        "trainable_parameters": sum(parameter.numel() for parameter in parameters),
        "stem_parameters": sum(parameter.numel() for parameter in stem.parameters()),
        "stem_hash_before": stem_before,
        "stem_hash_after": stem_after,
        "fresh_expert_max_norm": fresh_delta_max_norm,
        "max_observed_expert_norm": max_observed_expert_norm,
        "before_token_accuracy": before_accuracy,
        "after_token_accuracy": after_accuracy,
        "without_experts_token_accuracy": without_experts_accuracy,
        "first_loss": losses[0],
        "last_loss": losses[-1],
    }


def generate_local(embedding: torch.Tensor, stem, expert, head):
    symbols = []
    previous = BOS
    deltas = []
    with torch.inference_mode():
        for position in range(3):
            z0 = stem(
                embedding,
                torch.tensor(position),
                torch.tensor(previous),
            )
            delta = expert(z0)
            symbol = int(head(z0, delta).argmax())
            symbols.append(symbol)
            deltas.append(delta)
            previous = symbol
    return decode_result(symbols), deltas, symbols


def evaluate_tasks(world: dict, embeddings: dict, stem, experts, head):
    rows = []
    segment_correct = segment_total = network_bytes = token_total = 0
    for task in world["tasks"]:
        contributions = []
        generated_symbols = {}
        for requested in task["derivation"]["contributions"]:
            pocket = requested["pocket_id"]
            value, deltas, symbols = generate_local(
                embeddings[(pocket, requested["fact_key"])], stem, experts[pocket], head
            )
            network_bytes += sum(delta.numel() * delta.element_size() for delta in deltas)
            token_total += len(deltas)
            result = 998 if value == "INVALID" else value
            contributions.append(Contribution(task["id"], pocket, result))
            generated_symbols[pocket] = symbols
            segment_total += 1
            segment_correct += result == expected_local_result(world, task, pocket)
        assembly = assemble(task, contributions)
        rows.append({
            "task_id": task["id"],
            "expected": task["answer"],
            "actual": assembly.answer,
            "symbols": generated_symbols,
            "correct": assembly.answer == task["answer"],
        })
    return {
        "tasks": len(rows),
        "complete_exact_match": sum(row["correct"] for row in rows) / len(rows),
        "segment_exact_match": segment_correct / segment_total,
        "expert_calls": token_total,
        "logical_round_trips_per_segment": 3,
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
    stem, experts, head, training = train(world, embeddings)
    evaluation = evaluate_tasks(world, embeddings, stem, experts, head)
    result = {
        "experiment_id": "E004",
        "protocol_version": "arena-v0.1",
        "architecture_id": "token_moe",
        "status": "passed" if evaluation["complete_exact_match"] == 1.0 else "failed",
        "claim_status": "public_development_only",
        "seed": SEED,
        "base_embedding_sha256": embedding_sha256,
        "base_trainable_parameters": 0,
        "hidden_dim": HIDDEN_DIM,
        "expert_dim": EXPERT_DIM,
        "max_expert_norm": MAX_EXPERT_NORM,
        "training": training,
        "evaluation": evaluation,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
        "execution_note": "Selected pocket branches are logically parallel. This one-host development run executes them sequentially; three autoregressive symbol positions remain sequential by design.",
        "claim_boundary": "Training and evaluation reuse the same public records. This validates per-token expert calls, not WAN operation or held-out generalization.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
