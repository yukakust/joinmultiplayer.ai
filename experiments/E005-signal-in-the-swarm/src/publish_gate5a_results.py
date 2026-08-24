from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "experiments/E005-signal-in-the-swarm/artifacts/gate5a-raw-v0.1.json"
PUBLIC = ROOT / "site/experiments/E005/gate-5a-results-v0.1.json"


def publish() -> dict:
    data = json.loads(RAW.read_text(encoding="utf-8"))
    if len(data.get("rows", [])) != 24 or len(data.get("conditions", [])) != 8:
        raise ValueError("incomplete Gate 5A raw result")
    cause_correct = sum(row["conditions"]["correct_pair"]["cause_capsule"] == row["expected_cause_capsule"] for row in data["rows"])
    safety_correct = sum(row["conditions"]["correct_pair"]["safety_capsule"] == row["expected_safety_capsule"] for row in data["rows"])
    data["status"] = "published_preliminary_owner_review_required"
    data["component_summary"] = {"cause_capsules_correct": cause_correct, "safety_capsules_correct": safety_correct, "total": 24}
    data["review_method"] = {
        "pair_conditions": "A complete answer requires both parsed capsules to exactly match the preregistered labels.",
        "direct_conditions": "Preliminary phrase-presence check; every raw answer remains visible for owner review."
    }
    data["claim_boundary"] = {
        "en": "Gate 5A supports one-round composition through explicit text capsules and a deterministic renderer. It does not test learned routing, latent-state merging, multiple devices, or swarm scaling.",
        "ru": "Gate 5A подтверждает однораундовое объединение через явные текстовые капсулы и простой неизменяемый сборщик. Он не проверяет обученный routing, объединение скрытых состояний, разные устройства или рост swarm."
    }
    PUBLIC.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    result = publish()
    print(json.dumps({"summary": result["summary"], "components": result["component_summary"], "passed": result["passed"]}))
