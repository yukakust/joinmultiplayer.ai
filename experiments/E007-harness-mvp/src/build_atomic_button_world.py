#!/usr/bin/env python3
"""Build the compact E007 Gate 3C.6E ten-case world."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUT = ROOT / "site/experiments/E007/atomic-button-world-v0.1.json"
BASE_PATH = ROOT / "experiments/E007-harness-mvp/src/build_atomic_tool_world.py"
SPEC = importlib.util.spec_from_file_location("atomic_tool_world", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


EXTRA_DOMAINS = [
    {
        "id": "battery",
        "question": "A Nera-5 battery pack is swelling while connected to its charger. What should the operator do?",
        "source": {"title": "Nera-5 Battery Handbook", "version": "2.2", "date": "2041-06-20", "coordinates": "warning B-3"},
        "rule": "When a Nera-5 battery pack swells while charging, disconnect the charger and move people away from the pack.",
        "supporting_window": "Warning B-3 covers visible deformation. When a Nera-5 battery pack swells while charging, disconnect the charger. Move people away from the pack and call the battery technician.",
        "non_supporting_window": "The Nera-5 shipping label is violet. Store unused labels in the second drawer and replace any label that can no longer be read.",
        "condition": "The Nera-5 pack is currently swelling while connected to its charger.",
        "matching_facts": "At 16:20 the pack's centre was 9 millimetres thicker than at 16:00. It remains connected to the active charger.",
        "nonmatching_facts": "At 16:20 the pack remains flat and cool. Its charger has been disconnected since 15:45, and no deformation is visible.",
        "consequence": "Disconnect the charger and move people away from the pack.",
        "following_answer": "Disconnect the charger and keep people away from the Nera-5 pack.",
        "nonfollowing_answer": "Keep charging the pack and ask people to stand beside it.",
    },
    {
        "id": "greenhouse",
        "question": "The Sora greenhouse leaves are hot and the mist line is dry. What should happen to the lamps?",
        "source": {"title": "Sora Greenhouse Manual", "version": "9.0", "date": "2041-01-12", "coordinates": "heat rule H-7"},
        "rule": "When leaf temperature is above 35 C and the mist line is dry, pause the grow lamps until mist flow is restored.",
        "supporting_window": "Heat rule H-7 protects dry plants. When leaf temperature is above 35 C and the mist line is dry, pause the grow lamps. Restore mist flow before the lamps are started again.",
        "non_supporting_window": "Each lamp has a silver inventory label. Scan the label after replacing a bulb and record the old bulb's serial number in the maintenance log.",
        "condition": "Leaf temperature is currently above 35 C and the mist line is dry.",
        "matching_facts": "At 11:30 leaf temperature is 38 C. The mist line has produced no water for twelve minutes.",
        "nonmatching_facts": "At 11:30 leaf temperature is 27 C. The mist line is flowing normally and every nozzle is wet.",
        "consequence": "Pause the grow lamps until mist flow is restored.",
        "following_answer": "Pause the grow lamps and restart them only after mist flow returns.",
        "nonfollowing_answer": "Increase the lamp power and switch off the working mist line.",
    },
]


COMBINATIONS = ("111", "111", "111", "011", "101", "110", "001", "010", "100", "000")


def make_case(domain: dict, index: int, bits: str) -> dict:
    source_ok, facts_ok, answer_ok = (bit == "1" for bit in bits)
    return {
        "id": f"AB{index:02d}",
        "domain": domain["id"],
        "combination": bits,
        "question": domain["question"],
        "source": domain["source"],
        "source_window": domain["supporting_window"] if source_ok else domain["non_supporting_window"],
        "proposed_rule": domain["rule"],
        "rule_condition": domain["condition"],
        "current_facts": domain["matching_facts"] if facts_ok else domain["nonmatching_facts"],
        "rule_consequence": domain["consequence"],
        "proposed_answer": domain["following_answer"] if answer_ok else domain["nonfollowing_answer"],
        "expected": {
            "source_supports_rule": "accept" if source_ok else "reject",
            "facts_support_condition": "accept" if facts_ok else "reject",
            "answer_follows_consequence": "accept" if answer_ok else "reject",
            "final": "use" if bits == "111" else "do_not_use",
        },
    }


def build() -> dict:
    domains = [*BASE.DOMAINS, *EXTRA_DOMAINS]
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6E",
        "status": "frozen_before_inference",
        "language": "en",
        "cases": [make_case(domain, index, bits) for index, (domain, bits) in enumerate(zip(domains, COMBINATIONS), start=1)],
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
