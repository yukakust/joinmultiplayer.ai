#!/usr/bin/env python3
"""Build E007 Gate 3C.6M: semantic button phrases from one to four words."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "site/experiments/E007/ninety-word-world-v0.1.json"
OUT = ROOT / "site/experiments/E007/phrase-length-world-v0.1.json"
FAMILIES = [
    {"id": "USER", "positive": "include", "negative": "not presented", "balanced": False},
    {"id": "W1", "positive": "supported", "negative": "unsupported", "balanced": True},
    {"id": "W2", "positive": "answer supported", "negative": "answer unsupported", "balanced": True},
    {"id": "W3", "positive": "source supports answer", "negative": "source lacks support", "balanced": True},
    {"id": "W4", "positive": "source supports this answer", "negative": "source does not support", "balanced": True},
]
ORDERS = ("POSITIVE_FIRST", "NEGATIVE_FIRST")
MEANINGS = {
    "approve": "the source clearly supports the proposed answer",
    "reject": "the source conflicts, does not support, or leaves the proposed answer unclear",
}


def prompt_for(case: dict, family: dict, order: str) -> str:
    labels = [family["positive"], family["negative"]]
    if order == "NEGATIVE_FIRST":
        labels.reverse()
    return (
        f"QUESTION:\n{case['question']}\n\n"
        f"SOURCE:\n{case['source']}\n\n"
        f"PROPOSED ANSWER:\n{case['answer']}\n\n"
        f"Choose exactly one button: {labels[0]} or {labels[1]}.\n"
        f"{family['positive']} = {MEANINGS['approve']}.\n"
        f"{family['negative']} = {MEANINGS['reject']}.\n"
        "BUTTON:"
    )


def build() -> dict:
    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    items = []
    for family in FAMILIES:
        mapping = {family["positive"]: "approve", family["negative"]: "reject"}
        expected_label = {meaning: label for label, meaning in mapping.items()}
        for order in ORDERS:
            for original_case in original["cases"]:
                case = {key: value for key, value in original_case.items() if key not in {"prompt", "prompt_words"}}
                prompt = prompt_for(case, family, order)
                items.append({
                    **case,
                    "id": f"{case['id']}-{family['id']}-{order}",
                    "case_id": case["id"],
                    "family_id": family["id"],
                    "family": family,
                    "order": order,
                    "mapping": mapping,
                    "labels": [family["positive"], family["negative"]],
                    "expected_semantic": case["expected"],
                    "expected": expected_label[case["expected"]],
                    "prompt": prompt,
                    "prompt_words": len(prompt.split()),
                })
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6M",
        "status": "frozen_before_inference",
        "language": "en",
        "source_world": "/experiments/E007/ninety-word-world-v0.1.json",
        "families": FAMILIES,
        "orders": list(ORDERS),
        "items": items,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
