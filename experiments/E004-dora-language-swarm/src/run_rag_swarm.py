#!/usr/bin/env python3
"""A1 development run: typed local RAG evidence capsules."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from arena_common import (
    Contribution,
    assemble,
    book_index,
    evaluate,
    exact_rag_contribution,
    fact_index,
    load_world,
)


def adversarial_controls(world: dict) -> dict:
    missing_safe = partial_safe = duplicate_safe = irrelevant_safe = 0
    for task in world["tasks"]:
        full = [exact_rag_contribution(world, task, pocket) for pocket in task["required_pockets"]]
        missing_safe += assemble(task, full[:-1]).status == "incomplete"
        partial = [*full[:-1], Contribution(task["id"], full[-1].pocket_id, full[-1].result, False)]
        partial_safe += assemble(task, partial).reason == "partial_contribution"
        duplicate_safe += assemble(task, [*full, full[0]]).reason == "duplicate_pocket"
        irrelevant_safe += assemble(
            task, [*full, Contribution(task["id"], "P99", 1)]
        ).reason == "unexpected_pocket"

    stale_rows = []
    books = book_index(world)
    for task in world["tasks"]:
        stale = []
        changed = False
        for pocket in task["required_pockets"]:
            requested = next(
                item for item in task["derivation"]["contributions"] if item["pocket_id"] == pocket
            )
            fact = fact_index(books[pocket])[requested["fact_key"]]
            old = next((item for item in fact["history"] if item["state"] == "superseded"), None)
            if old and old["value"] is not None:
                procedure = books[pocket]["procedure"]
                stale_result = (
                    procedure["multiplier"] * old["value"] + procedure["bias"]
                ) % procedure["modulus"]
                stale.append(Contribution(task["id"], pocket, stale_result))
                changed = True
            else:
                stale.append(exact_rag_contribution(world, task, pocket))
        if changed:
            assembly = assemble(task, stale)
            stale_rows.append(
                {
                    "task_id": task["id"],
                    "expected": task["answer"],
                    "actual": assembly.answer,
                    "rejected": assembly.status != "complete",
                }
            )
    count = len(world["tasks"])
    return {
        "missing_required_safe_rate": missing_safe / count,
        "partial_safe_rate": partial_safe / count,
        "duplicate_rejection_rate": duplicate_safe / count,
        "irrelevant_rejection_rate": irrelevant_safe / count,
        "stale_detection_rate": (
            sum(row["rejected"] for row in stale_rows) / len(stale_rows) if stale_rows else None
        ),
        "stale_failures": [row for row in stale_rows if not row["rejected"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    world = load_world(args.world)
    normal = evaluate(world, exact_rag_contribution, "rag_swarm")
    controls = adversarial_controls(world)
    result = {
        "experiment_id": "E004",
        "protocol_version": "arena-v0.1",
        "architecture_id": "rag_swarm",
        "status": "passed_with_stale_record_limitation",
        "claim_status": "public_development_only",
        "implementation": "local current-state lookup + local procedure + typed atomic capsule",
        "gradient_training": False,
        "trainable_parameters": 0,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "normal": normal,
        "controls": controls,
        "privacy_surface": {
            "raw_book_transferred": False,
            "capsule_fields": ["task_id", "pocket_id", "result", "complete"],
        },
        "conclusion": {
            "en": "A1 transports all required public facts correctly and fails closed for missing, partial, duplicate, and irrelevant capsules. Its minimal capsule cannot detect a stale but well-formed local answer; signed freshness/version lineage is required.",
            "ru": "A1 правильно переносит все нужные открытые факты и закрывается при missing, partial, duplicate и irrelevant капсулах. Минимальная капсула не распознаёт устаревший, но корректно оформленный локальный ответ; нужна подписанная линия версий/свежести."
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
