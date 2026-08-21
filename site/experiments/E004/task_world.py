#!/usr/bin/env python3
"""Generate public illustrative E004 tasks without any model or training."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


SEED = 17_082_026
DOMAINS = ("kite", "tide", "ember")
PREFIX = {"kite": "K", "tide": "T", "ember": "E"}
RULES = {
    "kite": {"arity": 2, "coefficients": (7, 11), "bias": 3},
    "tide": {"arity": 3, "coefficients": (5, 9, 13), "bias": 1},
    "ember": {"arity": 2, "coefficients": (3, 15), "bias": 7},
}
ORDER_WORDS = {
    ("kite", "tide", "ember"): "Kite first, Tide second, and Ember last",
    ("tide", "ember", "kite"): "Tide first, then Ember, and finish with Kite",
    ("ember", "kite", "tide"): "Begin with Ember, follow with Kite, and end with Tide",
    ("kite", "ember", "tide"): "Report Kite, then Ember, then Tide",
    ("tide", "kite", "ember"): "Start with Tide, put Kite in the middle, and Ember last",
    ("ember", "tide", "kite"): "Use the order Ember, Tide, Kite",
}


def evaluate(domain: str, inputs: list[int]) -> int:
    rule = RULES[domain]
    if len(inputs) != rule["arity"] or any(not 0 <= item < 32 for item in inputs):
        raise ValueError("invalid illustrative task input")
    return (sum(weight * item for weight, item in zip(rule["coefficients"], inputs)) + rule["bias"]) % 32


def format_segment(domain: str, value: int) -> str:
    return f"{PREFIX[domain]}-{value:02X}"


def make_task(rng: random.Random, index: int) -> dict:
    order = tuple(ORDER_WORDS)[index % len(ORDER_WORDS)]
    inputs = {
        domain: [rng.randrange(32) for _ in range(RULES[domain]["arity"])]
        for domain in DOMAINS
    }
    values = {domain: evaluate(domain, inputs[domain]) for domain in DOMAINS}
    answer = " / ".join(format_segment(domain, values[domain]) for domain in order)
    prompt = (
        f"Encode Kite{tuple(inputs['kite'])}, Tide{tuple(inputs['tide'])}, and "
        f"Ember{tuple(inputs['ember'])}. {ORDER_WORDS[order]}. Return only the three segments."
    )
    derivation = {
        domain: {
            "inputs": inputs[domain],
            "calculation": (
                " + ".join(
                    f"{weight}×{item}" for weight, item in zip(RULES[domain]["coefficients"], inputs[domain])
                )
                + f" + {RULES[domain]['bias']} mod 32"
            ),
            "value": values[domain],
            "segment": format_segment(domain, values[domain]),
        }
        for domain in DOMAINS
    }
    return {
        "id": f"SAMPLE-{index + 1:02d}",
        "prompt": prompt,
        "order": list(order),
        "answer": answer,
        "derivation": derivation,
    }


def build_sample() -> dict:
    rng = random.Random(SEED)
    tasks = [make_task(rng, index) for index in range(12)]
    return {
        "schema_version": "0.1",
        "experiment_id": "E004",
        "status": "illustrative_not_locked",
        "seed": SEED,
        "answer_alphabet_per_pocket": 32,
        "complete_answer_space": 32**3,
        "blind_guess_probability": 1 / (32**3),
        "pair_missing_segment_guess_probability": 1 / 32,
        "rules": {
            domain: {
                "arity": rule["arity"],
                "coefficients": list(rule["coefficients"]),
                "bias": rule["bias"],
            }
            for domain, rule in RULES.items()
        },
        "tasks": tasks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(build_sample(), ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
