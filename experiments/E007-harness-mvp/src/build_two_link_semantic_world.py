#!/usr/bin/env python3
"""Build the frozen E007 Gate 3C.6C two-link semantic world."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUT = ROOT / "site/experiments/E007/two-link-semantic-world-v0.1.json"


DOMAINS = [
    {
        "id": "machine",
        "question": "Kest-7's casing is hot and room pressure is rising. May it be restarted?",
        "yy": ("Kest-7 must not be restarted; its power must be isolated first.", "If Kest-7's casing remains hot or room pressure rises, isolate its power first and do not restart it."),
        "ny": ("Kest-7 may be restarted immediately.", "If Kest-7's casing remains hot or room pressure rises, isolate its power first and do not restart it."),
        "yn": ("Kest-7 is installed in the north bay.", "The Kest-7 unit is installed in the north bay."),
        "nn": ("Kest-7 is installed in the south bay.", "The Kest-7 unit is installed in the north bay."),
    },
    {
        "id": "software",
        "question": "A payment webhook creates duplicate orders when delivery is retried. What change prevents the duplicates?",
        "yy": ("Store each event ID as an idempotency key before creating an order.", "Before creating an order, store the webhook event ID as an idempotency key; repeated delivery of that ID must return the existing result."),
        "ny": ("Increasing the webhook retry count prevents duplicate orders.", "More retries do not prevent duplicates; store the event ID as an idempotency key before creating an order."),
        "yn": ("The webhook service is written in Go.", "The webhook service is written in Go and is deployed as one small binary."),
        "nn": ("The webhook service is written in Python.", "The webhook service is written in Go and is deployed as one small binary."),
    },
    {
        "id": "beekeeping",
        "question": "A hive is crowded, its queen is present, and sealed queen cells have appeared. What does this most likely mean?",
        "yy": ("The colony is preparing to swarm.", "A crowded colony with its queen still present and sealed queen cells is usually preparing to swarm."),
        "ny": ("The colony has become queenless.", "A crowded colony with its queen still present and sealed queen cells is usually preparing to swarm."),
        "yn": ("The hive box is painted blue.", "The hive box used for this colony is painted blue."),
        "nn": ("The hive box is painted green.", "The hive box used for this colony is painted blue."),
    },
    {
        "id": "memory",
        "question": "At which cafe did Mara say we should meet after the museum?",
        "yy": ("Mara said to meet at Juniper Cafe.", "Mara said, 'After the museum, meet me at Juniper Cafe.'"),
        "ny": ("Mara said to meet at Harbor Cafe.", "Mara said, 'After the museum, meet me at Juniper Cafe.'"),
        "yn": ("Mara wore a red scarf at the museum.", "Mara wore a red scarf during the museum visit."),
        "nn": ("Mara wore a blue scarf at the museum.", "Mara wore a red scarf during the museum visit."),
    },
    {
        "id": "policy",
        "question": "May a contractor deploy to production alone while an incident is active?",
        "yy": ("No; a staff reviewer must approve the deployment even during an incident.", "A contractor may never deploy to production alone; an active incident does not remove the staff-review requirement."),
        "ny": ("Yes; an active incident lets a contractor deploy alone.", "A contractor may never deploy to production alone; an active incident does not remove the staff-review requirement."),
        "yn": ("The contractor's building badge expires on Friday.", "The contractor's building badge expires on Friday."),
        "nn": ("The contractor's building badge expires on Monday.", "The contractor's building badge expires on Friday."),
    },
    {
        "id": "cooking",
        "question": "A custard has reached 82 C and coats a spoon. What should be done next to avoid curdling?",
        "yy": ("Remove the custard from heat and cool the bowl immediately.", "When the custard reaches 82 C and coats a spoon, remove it from heat and cool the bowl immediately to prevent curdling."),
        "ny": ("Keep the custard boiling for another five minutes.", "When the custard reaches 82 C and coats a spoon, remove it from heat and cool the bowl immediately to prevent curdling."),
        "yn": ("The custard was cooked in a copper pan.", "This batch of custard was cooked in a copper pan."),
        "nn": ("The custard was cooked in a steel pan.", "This batch of custard was cooked in a copper pan."),
    },
    {
        "id": "expedition",
        "question": "Which route did Lysa's expedition use to avoid the flooded pass?",
        "yy": ("Lysa's expedition used the eastern ridge route.", "To avoid the flooded pass, Lysa's expedition travelled along the eastern ridge."),
        "ny": ("Lysa's expedition used the western marsh route.", "To avoid the flooded pass, Lysa's expedition travelled along the eastern ridge."),
        "yn": ("Lysa's expedition carried an orange camp flag.", "Lysa's expedition carried an orange camp flag."),
        "nn": ("Lysa's expedition carried a blue camp flag.", "Lysa's expedition carried an orange camp flag."),
    },
    {
        "id": "computer_vision",
        "question": "Tiny objects disappear after training images are resized. What training change should be tried first?",
        "yy": ("Train with larger inputs or crops that preserve the tiny objects.", "When resizing erases tiny objects, first train with larger inputs or object-centred crops that preserve those objects."),
        "ny": ("Downsample the training images even further.", "When resizing erases tiny objects, first train with larger inputs or object-centred crops that preserve those objects."),
        "yn": ("The training set contains ten thousand images.", "The current training set contains ten thousand images."),
        "nn": ("The training set contains twenty thousand images.", "The current training set contains ten thousand images."),
    },
]


QUADRANTS = {
    "yy": {"quote_supports_claim": "yes", "claim_helps_question": "yes", "expected_final": "take"},
    "ny": {"quote_supports_claim": "no", "claim_helps_question": "yes", "expected_final": "drop"},
    "yn": {"quote_supports_claim": "yes", "claim_helps_question": "no", "expected_final": "drop"},
    "nn": {"quote_supports_claim": "no", "claim_helps_question": "no", "expected_final": "drop"},
}


def build() -> dict:
    cases = []
    for domain_index, domain in enumerate(DOMAINS, start=1):
        for quadrant in ("yy", "ny", "yn", "nn"):
            claim, quote = domain[quadrant]
            cases.append({
                "id": f"TL{domain_index:02d}-{quadrant.upper()}",
                "domain": domain["id"],
                "quadrant": quadrant,
                "question": domain["question"],
                "claim": claim,
                "exact_quote": quote,
                "expected": QUADRANTS[quadrant],
            })
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6C",
        "status": "frozen_before_inference",
        "language": "en",
        "cases": cases,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
