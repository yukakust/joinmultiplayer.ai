#!/usr/bin/env python3
"""Build E007 Gate 3C.6J: mirrored 1/A action mappings."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "site/experiments/E007/ninety-word-world-v0.1.json"
OUT = ROOT / "site/experiments/E007/numeric-letter-world-v0.1.json"
DECKS = {
    "X": {"1": "approve", "A": "reject"},
    "Y": {"1": "reject", "A": "approve"},
}
MEANINGS = {
    "approve": "the source clearly supports the answer",
    "reject": "the source conflicts, does not support, or leaves the answer unclear",
}


def prompt_for(case: dict, mapping: dict[str, str]) -> str:
    return (
        f"QUESTION:\n{case['question']}\n\n"
        f"SOURCE:\n{case['source']}\n\n"
        f"PROPOSED ANSWER:\n{case['answer']}\n\n"
        "Choose exactly one: 1 or A.\n"
        f"1 = {MEANINGS[mapping['1']]}.\n"
        f"A = {MEANINGS[mapping['A']]}.\n"
        "CHOICE:"
    )


def build() -> dict:
    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    items = []
    for deck, mapping in DECKS.items():
        expected_label = {meaning: label for label, meaning in mapping.items()}
        for original_case in original["cases"]:
            case = {key: value for key, value in original_case.items() if key not in {"prompt", "prompt_words"}}
            prompt = prompt_for(case, mapping)
            items.append({
                **case,
                "id": f"{case['id']}-{deck}",
                "case_id": case["id"],
                "deck": deck,
                "mapping": mapping,
                "expected_semantic": case["expected"],
                "expected": expected_label[case["expected"]],
                "prompt": prompt,
                "prompt_words": len(prompt.split()),
            })
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6J",
        "status": "frozen_before_inference",
        "language": "en",
        "source_world": "/experiments/E007/ninety-word-world-v0.1.json",
        "decks": DECKS,
        "items": items,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
