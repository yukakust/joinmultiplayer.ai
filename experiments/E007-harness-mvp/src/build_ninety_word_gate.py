#!/usr/bin/env python3
"""Build E007 Gate 3C.6H: ten source-answer prompts under 90 words."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUT = ROOT / "site/experiments/E007/ninety-word-world-v0.1.json"


CASES = [
    {
        "id": "NW01",
        "domain": "colour",
        "expected": "approve",
        "question": "What colour is Box R-17?",
        "source": "The current inspection card states that Box R-17 is red. No later card exists.",
        "answer": "Box R-17 is red.",
    },
    {
        "id": "NW02",
        "domain": "software",
        "expected": "approve",
        "question": "How should duplicate webhook deliveries be stopped?",
        "source": "When deliveries repeat the same event ID, store that ID before creating the order and return the existing result on retries.",
        "answer": "Use the event ID as an idempotency key before order creation.",
    },
    {
        "id": "NW03",
        "domain": "beekeeping",
        "expected": "approve",
        "question": "What do a crowded hive, present queen, and sealed queen cells suggest?",
        "source": "A crowded colony with its queen present and several sealed queen cells is usually preparing to swarm.",
        "answer": "The colony is probably preparing to swarm.",
    },
    {
        "id": "NW04",
        "domain": "memory",
        "expected": "approve",
        "question": "Where did Mara say to meet after the museum?",
        "source": "Mara wrote at 18:10: Correction, not Harbor Cafe. Meet at Juniper Cafe after the museum.",
        "answer": "Meet Mara at Juniper Cafe.",
    },
    {
        "id": "NW05",
        "domain": "cooking",
        "expected": "approve",
        "question": "What should happen when custard reaches 82 C and coats a spoon?",
        "source": "At 82 C, when custard coats a spoon, remove it from heat and cool the bowl immediately to prevent curdling.",
        "answer": "Take the custard off the heat and cool the bowl now.",
    },
    {
        "id": "NW06",
        "domain": "machine",
        "expected": "reject",
        "question": "May hot Kest-7 be restarted while room pressure rises?",
        "source": "If Kest-7 is above 80 C and room pressure is rising, isolate its power and do not restart it.",
        "answer": "Restart Kest-7 immediately and leave its power connected.",
    },
    {
        "id": "NW07",
        "domain": "policy",
        "expected": "reject",
        "question": "May a contractor deploy to production alone during an incident?",
        "source": "Contractor building badges expire at midnight on their printed date and must then be returned to reception.",
        "answer": "An incident allows a contractor to deploy alone without staff review.",
    },
    {
        "id": "NW08",
        "domain": "expedition",
        "expected": "reject",
        "question": "Which route avoids the flooded northern pass?",
        "source": "When the northern gauge is above the red mark, avoid the pass and use the eastern ridge. The western marsh is unsafe.",
        "answer": "Use the western marsh route.",
    },
    {
        "id": "NW09",
        "domain": "computer_vision",
        "expected": "reject",
        "question": "What should be tried when resize erases tiny labelled objects?",
        "source": "When resize makes labelled objects smaller than two pixels, first use larger inputs or object-centred crops that preserve them.",
        "answer": "Downsample the images even further.",
    },
    {
        "id": "NW10",
        "domain": "greenhouse",
        "expected": "reject",
        "question": "Should the grow lamps pause when hot leaves have no mist?",
        "source": "Each grow lamp has a silver inventory label. Scan that label after replacing a bulb and record the serial number.",
        "answer": "Pause the grow lamps until mist flow returns.",
    },
]


def prompt_for(case: dict) -> str:
    return (
        f"QUESTION:\n{case['question']}\n\n"
        f"SOURCE:\n{case['source']}\n\n"
        f"PROPOSED ANSWER:\n{case['answer']}\n\n"
        "Choose: approve or reject.\n"
        "approve = the source clearly supports the answer.\n"
        "reject = the source conflicts, does not support, or leaves the answer unclear.\n"
        "CHOICE:"
    )


def build() -> dict:
    cases = []
    for case in CASES:
        prompt = prompt_for(case)
        cases.append({**case, "prompt": prompt, "prompt_words": len(prompt.split())})
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6H",
        "status": "frozen_before_inference",
        "language": "en",
        "cases": cases,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
