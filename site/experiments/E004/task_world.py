#!/usr/bin/env python3
"""Build the public, illustrative E004 Architecture Arena data world.

This generator contains no locked seeds or final evaluation books. It exists so
people can inspect the data contract before any model is downloaded or trained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA_VERSION = "0.2"
PUBLIC_SEED = "E004-public-arena-v0.2"
MODULUS = 997
PUBLIC_POCKETS = (
    ("P01", "Kite"),
    ("P02", "Tide"),
    ("P03", "Ember"),
    ("P04", "Moss"),
    ("P05", "Orbit"),
    ("P06", "Lumen"),
    ("P07", "Coral"),
    ("P08", "Flint"),
)


def stable_int(*parts: object, modulus: int) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % modulus


def procedure_for(pocket_id: str) -> dict:
    multiplier = 2 + stable_int(PUBLIC_SEED, pocket_id, "multiplier", modulus=MODULUS - 2)
    bias = stable_int(PUBLIC_SEED, pocket_id, "bias", modulus=MODULUS)
    return {
        "formula": "(multiplier × current_value + bias) mod 997",
        "multiplier": multiplier,
        "bias": bias,
        "modulus": MODULUS,
    }


def fact_for(pocket_id: str, codename: str, index: int) -> dict:
    key = f"{codename.lower()}-{index + 1:02d}"
    original = stable_int(PUBLIC_SEED, pocket_id, key, "v1", modulus=MODULUS)
    if index == 0:
        current = stable_int(PUBLIC_SEED, pocket_id, key, "v2", modulus=MODULUS)
        return {
            "key": key,
            "status": "active",
            "current_version": 2,
            "current_value": current,
            "history": [
                {"version": 1, "value": original, "state": "superseded"},
                {"version": 2, "value": current, "state": "current"},
            ],
        }
    if index == 1:
        return {
            "key": key,
            "status": "deleted",
            "current_version": 2,
            "current_value": None,
            "history": [
                {"version": 1, "value": original, "state": "superseded"},
                {"version": 2, "value": None, "state": "deleted"},
            ],
        }
    return {
        "key": key,
        "status": "active",
        "current_version": 1,
        "current_value": original,
        "history": [{"version": 1, "value": original, "state": "current"}],
    }


def build_book(pocket_id: str, codename: str) -> dict:
    return {
        "pocket_id": pocket_id,
        "codename": codename,
        "status": "public_demo_only",
        "planned_private_book": {
            "exact_facts": 256,
            "procedure_examples": 256,
            "updates_or_deletions": 64,
        },
        "procedure": procedure_for(pocket_id),
        "preview_facts": [fact_for(pocket_id, codename, index) for index in range(8)],
    }


def find_fact(book: dict, fact_key: str) -> dict:
    for fact in book["preview_facts"]:
        if fact["key"] == fact_key:
            return fact
    raise KeyError(fact_key)


def apply_procedure(book: dict, fact: dict) -> int | None:
    if fact["status"] == "deleted":
        return None
    procedure = book["procedure"]
    return (
        procedure["multiplier"] * fact["current_value"] + procedure["bias"]
    ) % procedure["modulus"]


def task_prompt(required: list[tuple[dict, dict]], task_type: str) -> dict:
    requests_en = ", ".join(
        f"{book['pocket_id']} record {fact['key']}" for book, fact in required
    )
    requests_ru = ", ".join(
        f"запись {fact['key']} из {book['pocket_id']}" for book, fact in required
    )
    if task_type == "deletion":
        return {
            "en": f"Ask {requests_en}. Respect the latest state. Return the pocket id and ABSTAIN if the record was deleted.",
            "ru": f"Запросите {requests_ru}. Учитывайте последнее состояние. Верните id pocket i и ABSTAIN, если запись удалена.",
        }
    return {
        "en": f"Ask {requests_en}. Each pocket applies its own rule to the current value. Return every segment and their seal.",
        "ru": f"Запросите {requests_ru}. Каждый pocket i применяет своё правило к текущему значению. Верните все сегменты и их печать.",
    }


def build_task(task_id: str, task_type: str, required: list[tuple[dict, dict]]) -> dict:
    contributions = []
    for book, fact in required:
        result = apply_procedure(book, fact)
        contributions.append(
            {
                "pocket_id": book["pocket_id"],
                "fact_key": fact["key"],
                "fact_version": fact["current_version"],
                "fact_status": fact["status"],
                "result": result,
            }
        )

    if any(item["result"] is None for item in contributions):
        answer = " | ".join(f"{item['pocket_id']}:ABSTAIN" for item in contributions)
        seal = None
        answer_space = 2
    else:
        seal = sum((index + 2) * item["result"] for index, item in enumerate(contributions)) % MODULUS
        segments = " | ".join(
            f"{item['pocket_id']}:{item['result']:03d}" for item in contributions
        )
        answer = f"{segments} | SEAL:{seal:03d}"
        answer_space = MODULUS ** len(contributions)

    return {
        "id": task_id,
        "type": task_type,
        "required_pockets": [book["pocket_id"] for book, _ in required],
        "prompt": task_prompt(required, task_type),
        "answer": answer,
        "answer_space": answer_space,
        "blind_guess_probability": 1 / answer_space,
        "derivation": {
            "contributions": contributions,
            "seal_formula": None if seal is None else "Σ((position + 2) × result) mod 997",
            "seal": seal,
        },
    }


def build_tasks(books: list[dict]) -> list[dict]:
    active = {
        book["pocket_id"]: [fact for fact in book["preview_facts"] if fact["status"] == "active"]
        for book in books
    }
    deleted = {
        book["pocket_id"]: [fact for fact in book["preview_facts"] if fact["status"] == "deleted"]
        for book in books
    }
    by_id = {book["pocket_id"]: book for book in books}

    specifications = (
        ("PUBLIC-01", "single", (("P01", 2),)),
        ("PUBLIC-02", "single", (("P06", 4),)),
        ("PUBLIC-03", "pair", (("P02", 2), ("P05", 3))),
        ("PUBLIC-04", "pair", (("P03", 5), ("P08", 2))),
        ("PUBLIC-05", "pair", (("P01", 6), ("P07", 3))),
        ("PUBLIC-06", "triple", (("P01", 3), ("P04", 4), ("P08", 5))),
        ("PUBLIC-07", "triple", (("P02", 6), ("P05", 2), ("P07", 4))),
        ("PUBLIC-08", "triple", (("P03", 2), ("P06", 5), ("P08", 3))),
        ("PUBLIC-09", "triple", (("P04", 5), ("P05", 6), ("P06", 3))),
        ("PUBLIC-10", "updated_fact", (("P01", 0), ("P02", 0))),
    )
    tasks = []
    for task_id, task_type, selectors in specifications:
        required = [(by_id[pocket_id], active[pocket_id][fact_index]) for pocket_id, fact_index in selectors]
        tasks.append(build_task(task_id, task_type, required))

    deletion_book = by_id["P03"]
    tasks.append(build_task("PUBLIC-11", "deletion", [(deletion_book, deleted["P03"][0])]))
    deletion_book = by_id["P08"]
    tasks.append(build_task("PUBLIC-12", "deletion", [(deletion_book, deleted["P08"][0])]))
    return tasks


def build_sample() -> dict:
    books = [build_book(pocket_id, codename) for pocket_id, codename in PUBLIC_POCKETS]
    tasks = build_tasks(books)
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": "E004",
        "status": "public_demo_not_locked",
        "claim_status": "not_a_result",
        "seed": PUBLIC_SEED,
        "population_contract": {
            "surrogate_ids": [f"S{index:02d}" for index in range(1, 17)],
            "final_ids": [f"I{index:02d}" for index in range(1, 9)],
            "post_freeze_plugin_id": "I09",
            "public_demo_ids": [pocket_id for pocket_id, _ in PUBLIC_POCKETS],
        },
        "locked_data_boundary": (
            "No locked salt, final book, evaluation label, retrieval index, or personal weight exists in this artifact."
        ),
        "answer_alphabet_per_pocket": MODULUS,
        "largest_complete_answer_space": MODULUS**3,
        "triple_blind_guess_probability": 1 / (MODULUS**3),
        "pair_missing_segment_guess_probability": 1 / MODULUS,
        "books": books,
        "tasks": tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(build_sample(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
