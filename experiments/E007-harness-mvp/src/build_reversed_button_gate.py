#!/usr/bin/env python3
"""Build E007 Gate 3C.6I by reversing only the two action choices."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "site/experiments/E007/ninety-word-world-v0.1.json"
OUT = ROOT / "site/experiments/E007/ninety-word-reversed-world-v0.1.json"


def prompt_for(case: dict) -> str:
    return (
        f"QUESTION:\n{case['question']}\n\n"
        f"SOURCE:\n{case['source']}\n\n"
        f"PROPOSED ANSWER:\n{case['answer']}\n\n"
        "Choose: reject or approve.\n"
        "reject = the source conflicts, does not support, or leaves the answer unclear.\n"
        "approve = the source clearly supports the answer.\n"
        "CHOICE:"
    )


def build() -> dict:
    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    cases = []
    for original_case in original["cases"]:
        case = {key: value for key, value in original_case.items() if key not in {"prompt", "prompt_words"}}
        prompt = prompt_for(case)
        cases.append({**case, "prompt": prompt, "prompt_words": len(prompt.split())})
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6I",
        "status": "frozen_before_inference",
        "language": "en",
        "only_change": "reject is listed and scored before approve",
        "source_world": "/experiments/E007/ninety-word-world-v0.1.json",
        "cases": cases,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
