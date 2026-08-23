"""Shared immutable task loader, atomic assembler, and scorer for E004 arena."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


EXPECTED_DATA_SHA256 = "f3fd2cb5730ab602ef232ddf6dfa8b8f0376561234ab050a42543fd94a685370"
MODULUS = 997


@dataclass(frozen=True)
class Contribution:
    task_id: str
    pocket_id: str
    result: int | None
    complete: bool = True


@dataclass(frozen=True)
class Assembly:
    status: str
    answer: str | None
    reason: str | None
    network_bytes: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_world(path: Path) -> dict:
    actual = sha256_file(path)
    if actual != EXPECTED_DATA_SHA256:
        raise ValueError(f"shared task hash mismatch: {actual}")
    world = json.loads(path.read_text(encoding="utf-8"))
    if len(world.get("books", [])) != 8 or len(world.get("tasks", [])) != 12:
        raise ValueError("shared world must contain exactly 8 books and 12 tasks")
    return world


def book_index(world: dict) -> dict[str, dict]:
    return {book["pocket_id"]: book for book in world["books"]}


def fact_index(book: dict) -> dict[str, dict]:
    return {fact["key"]: fact for fact in book["preview_facts"]}


def expected_local_result(world: dict, task: dict, pocket_id: str) -> int | None:
    requested = next(
        item for item in task["derivation"]["contributions"] if item["pocket_id"] == pocket_id
    )
    book = book_index(world)[pocket_id]
    fact = fact_index(book)[requested["fact_key"]]
    if fact["status"] == "deleted":
        return None
    procedure = book["procedure"]
    return (
        procedure["multiplier"] * fact["current_value"] + procedure["bias"]
    ) % procedure["modulus"]


def exact_rag_contribution(world: dict, task: dict, pocket_id: str) -> Contribution:
    return Contribution(
        task_id=task["id"],
        pocket_id=pocket_id,
        result=expected_local_result(world, task, pocket_id),
        complete=True,
    )


def assemble(task: dict, contributions: Iterable[Contribution]) -> Assembly:
    items = list(contributions)
    serialized = json.dumps(
        [item.__dict__ for item in items], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    required = task["required_pockets"]
    ids = [item.pocket_id for item in items]
    if any(item.task_id != task["id"] for item in items):
        return Assembly("rejected", None, "task_id_mismatch", len(serialized))
    if any(not item.complete for item in items):
        return Assembly("incomplete", None, "partial_contribution", len(serialized))
    if len(ids) != len(set(ids)):
        return Assembly("rejected", None, "duplicate_pocket", len(serialized))
    if set(ids) - set(required):
        return Assembly("rejected", None, "unexpected_pocket", len(serialized))
    if set(required) - set(ids):
        return Assembly("incomplete", None, "missing_required_pocket", len(serialized))
    ordered = [next(item for item in items if item.pocket_id == pocket_id) for pocket_id in required]
    if any(item.result is None for item in ordered):
        answer = " | ".join(f"{item.pocket_id}:ABSTAIN" for item in ordered)
        return Assembly("complete", answer, None, len(serialized))
    if any(not isinstance(item.result, int) or not 0 <= item.result < MODULUS for item in ordered):
        return Assembly("rejected", None, "result_out_of_range", len(serialized))
    seal = sum((index + 2) * item.result for index, item in enumerate(ordered)) % MODULUS
    segments = " | ".join(f"{item.pocket_id}:{item.result:03d}" for item in ordered)
    return Assembly("complete", f"{segments} | SEAL:{seal:03d}", None, len(serialized))


def evaluate(
    world: dict,
    contributor: Callable[[dict, dict, str], Contribution],
    architecture_id: str,
) -> dict:
    rows = []
    by_type: dict[str, list[bool]] = defaultdict(list)
    total_segments = 0
    correct_segments = 0
    total_bytes = 0
    for task in world["tasks"]:
        contributions = [contributor(world, task, pocket) for pocket in task["required_pockets"]]
        assembly = assemble(task, contributions)
        correct = assembly.answer == task["answer"]
        by_type[task["type"]].append(correct)
        total_bytes += assembly.network_bytes
        for item in contributions:
            total_segments += 1
            if item.complete and item.result == expected_local_result(world, task, item.pocket_id):
                correct_segments += 1
        rows.append(
            {
                "task_id": task["id"],
                "type": task["type"],
                "expected": task["answer"],
                "actual": assembly.answer,
                "status": assembly.status,
                "reason": assembly.reason,
                "correct": correct,
            }
        )
    exact = sum(row["correct"] for row in rows)
    return {
        "architecture_id": architecture_id,
        "tasks": len(rows),
        "complete_exact_match": exact / len(rows),
        "segment_exact_match": correct_segments / total_segments,
        "task_family_accuracy": {
            name: sum(values) / len(values) for name, values in sorted(by_type.items())
        },
        "estimated_network_bytes": total_bytes,
        "failures": [row for row in rows if not row["correct"]],
        "rows": rows,
    }


def accessible_task_counts(world: dict) -> dict[str, int]:
    ordered = [f"P{index:02d}" for index in range(1, 9)]
    result = {}
    for size in (1, 2, 4, 8):
        available = set(ordered[:size])
        result[str(size)] = sum(
            set(task["required_pockets"]).issubset(available) for task in world["tasks"]
        )
    return result


def harness_self_test(world: dict) -> dict:
    exact = evaluate(world, exact_rag_contribution, "exact_rag_control")
    task = world["tasks"][5]
    full = [exact_rag_contribution(world, task, pocket) for pocket in task["required_pockets"]]
    missing = assemble(task, full[:-1])
    partial = assemble(
        task,
        [*full[:-1], Contribution(task["id"], full[-1].pocket_id, full[-1].result, False)],
    )
    duplicate = assemble(task, [*full, full[0]])
    wrong_task = assemble(
        task,
        [Contribution("WRONG", item.pocket_id, item.result, item.complete) for item in full],
    )
    checks = {
        "recomputes_all_12": exact["complete_exact_match"] == 1.0,
        "missing_is_incomplete": missing.reason == "missing_required_pocket",
        "partial_is_incomplete": partial.reason == "partial_contribution",
        "duplicate_is_rejected": duplicate.reason == "duplicate_pocket",
        "wrong_task_is_rejected": wrong_task.reason == "task_id_mismatch",
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "exact_rag_control": exact,
        "accessible_task_counts": accessible_task_counts(world),
        "task_type_counts": dict(sorted(Counter(task["type"] for task in world["tasks"]).items())),
    }
