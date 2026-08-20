"""Inspectable synthetic neural components for E002.

Each pocket owns a disjoint key namespace and learns its key-to-byte table by
gradient descent.  The shared base is the all-zero logit table.  A personal
delta is therefore the pocket's learned logits, clipped before it crosses the
transaction boundary.  Probability capsules compose by circular convolution,
which is the distribution of modular addition over 256 possible answers.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

import torch
from torch import Tensor, nn

CLASSES = 256


def stable_byte(text: str) -> int:
    return sha256(text.encode("utf-8")).digest()[0]


@dataclass(frozen=True, slots=True)
class PrivateTable:
    pocket_id: str
    keys: tuple[str, ...]
    values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    pocket_ids: tuple[str, ...]
    key_indices: tuple[int, ...]
    signs: tuple[int, ...]
    offset: int
    answer: int


def make_private_world(seed: int, count: int, keys_per_pocket: int) -> tuple[PrivateTable, ...]:
    if count < 2 or keys_per_pocket < 2:
        raise ValueError("need at least two pockets and two keys per pocket")
    tables = []
    for owner in range(count):
        pocket_id = f"pocket-{owner:02d}"
        keys = tuple(f"{pocket_id}/private-key-{k:02d}" for k in range(keys_per_pocket))
        values = tuple(stable_byte(f"e002:{seed}:{key}") for key in keys)
        tables.append(PrivateTable(pocket_id, keys, values))
    return tuple(tables)


def make_tasks(seed: int, tables: tuple[PrivateTable, ...], count: int) -> tuple[Task, ...]:
    tasks = []
    for index in range(count):
        key_indices = tuple(stable_byte(f"task-key:{seed}:{index}:{p.pocket_id}") % len(p.keys) for p in tables)
        signs = tuple(1 if stable_byte(f"task-sign:{seed}:{index}:{p.pocket_id}") & 1 else -1 for p in tables)
        offset = stable_byte(f"task-offset:{seed}:{index}")
        answer = (offset + sum(s * p.values[k] for p, k, s in zip(tables, key_indices, signs, strict=True))) % CLASSES
        tasks.append(Task(f"n{len(tables)}-task-{index:03d}", tuple(p.pocket_id for p in tables), key_indices, signs, offset, answer))
    return tuple(tasks)


def make_pair_tasks(seed: int, tables: tuple[PrivateTable, ...], count: int) -> tuple[Task, ...]:
    """Create one fixed workload that evenly covers every ordered pocket pair."""
    if len(tables) < 2:
        raise ValueError("pair tasks need at least two pockets")
    pair_count = len(tables) * (len(tables) - 1)
    tasks = []
    for index in range(count):
        pair_index = index % pair_count
        first_index = pair_index // (len(tables) - 1)
        second_index = pair_index % (len(tables) - 1)
        if second_index >= first_index:
            second_index += 1
        selected = (tables[first_index], tables[second_index])
        key_indices = tuple(
            stable_byte(f"coverage-key:{seed}:{index}:{table.pocket_id}") % len(table.keys)
            for table in selected
        )
        signs = tuple(
            1 if stable_byte(f"coverage-sign:{seed}:{index}:{table.pocket_id}") & 1 else -1
            for table in selected
        )
        offset = stable_byte(f"coverage-offset:{seed}:{index}")
        answer = (
            offset
            + sum(
                sign * table.values[key]
                for table, key, sign in zip(selected, key_indices, signs, strict=True)
            )
        ) % CLASSES
        tasks.append(
            Task(
                f"coverage-task-{index:04d}",
                tuple(table.pocket_id for table in selected),
                key_indices,
                signs,
                offset,
                answer,
            )
        )
    return tuple(tasks)


class Pocket(nn.Module):
    """One inspectable personal weight table; rows are private examples."""

    def __init__(self, table: PrivateTable, max_delta_norm: float = 24.0) -> None:
        super().__init__()
        self.table = table
        self.max_delta_norm = float(max_delta_norm)
        self.logits = nn.Embedding(len(table.keys), CLASSES)
        nn.init.zeros_(self.logits.weight)

    def delta(self, key_index: int) -> Tensor:
        raw = self.logits(torch.tensor([key_index])).squeeze(0)
        norm = torch.linalg.vector_norm(raw)
        return raw * torch.clamp(torch.tensor(self.max_delta_norm) / norm.clamp_min(1e-12), max=1.0)

    def capsule(self, key_index: int) -> Tensor:
        return torch.softmax(self.delta(key_index), dim=-1)


def train_pocket(pocket: Pocket, steps: int, learning_rate: float) -> list[float]:
    optimizer = torch.optim.SGD(pocket.parameters(), lr=learning_rate)
    keys = torch.arange(len(pocket.table.keys))
    targets = torch.tensor(pocket.table.values)
    curve = []
    for _ in range(steps):
        optimizer.zero_grad()
        loss = nn.functional.cross_entropy(pocket.logits(keys), targets)
        loss.backward()
        optimizer.step()
        curve.append(float(loss.detach()))
    return curve


def transform_capsule(capsule: Tensor, sign: int) -> Tensor:
    if sign == 1:
        return capsule
    if sign == -1:
        indices = (-torch.arange(CLASSES)) % CLASSES
        return capsule[indices]
    raise ValueError("sign must be -1 or 1")


def circular_merge(capsules: Iterable[Tensor], signs: Iterable[int], offset: int) -> Tensor:
    """Compose independent byte distributions and apply public z0."""
    result = torch.zeros(CLASSES)
    result[0] = 1.0
    pairs = list(zip(capsules, signs, strict=True))
    for capsule, sign in pairs:
        transformed = transform_capsule(capsule, sign)
        result = torch.fft.irfft(torch.fft.rfft(result) * torch.fft.rfft(transformed), n=CLASSES).clamp_min(0)
        result = result / result.sum().clamp_min(1e-12)
    return torch.roll(result, int(offset) % CLASSES)


def uniform_capsule() -> Tensor:
    return torch.full((CLASSES,), 1.0 / CLASSES)
