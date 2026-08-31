#!/usr/bin/env python3
"""Build reviewed, privacy-safe Gate 16D.10 output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


# A second manual audit asks the narrower question used by this gate:
# does the short quote alone support every important part of the claim?
QUOTE_SUPPORTED = {
    "Q02-retrieved_shelf-C01",
    "Q02-retrieved_shelf-C02",
    "Q02-retrieved_shelf-C03",
    "Q02-retrieved_shelf-C04",
    "Q02-retrieved_shelf-C05",
    "Q02-oracle_shelf-C01",
    "Q02-oracle_shelf-C02",
    "Q02-oracle_shelf-C03",
    "Q02-oracle_shelf-C04",
    "Q02-oracle_shelf-C05",
    "Q02-oracle_shelf-C06",
    "Q07-retrieved_shelf-C03",
    "Q07-oracle_shelf-C03",
}


def build(private: dict) -> dict:
    rows = []
    for source in private["rows"]:
        quote_supported = source["id"] in QUOTE_SUPPORTED
        accepted = source["decision"] == "supported"
        rows.append(
            {
                "id": source["id"],
                "question_id": source["question_id"],
                "condition": source["condition"],
                "quote": source["quote"],
                "claim": source["claim"],
                "deberta_decision": "neutral",
                "old_full_message_grounded": source["human_grounded"],
                "manual_quote_only_supported": quote_supported,
                "qwen_decision": source["decision"],
                "qwen_reason": source["reason"],
                "qwen_correct_against_quote_only": accepted == quote_supported,
            }
        )
    quote_supported = sum(row["manual_quote_only_supported"] for row in rows)
    accepted = sum(row["qwen_decision"] == "supported" for row in rows)
    true_accepted = sum(row["manual_quote_only_supported"] and row["qwen_decision"] == "supported" for row in rows)
    false_accepted = sum(not row["manual_quote_only_supported"] and row["qwen_decision"] == "supported" for row in rows)
    correct = sum(row["qwen_correct_against_quote_only"] for row in rows)
    return {
        "schema_version": "0.1",
        "experiment": "E007",
        "gate": "16D.10",
        "status": "completed_failed_reference_mismatch_and_false_accepts",
        "protocol": "/experiments/E007/neutral-triage-gate16d10-protocol-v0.1.json",
        "summary_against_old_full_message_labels": private["summary"],
        "summary_after_quote_only_audit": {
            "cases": len(rows),
            "quote_supported": quote_supported,
            "qwen_accepted": accepted,
            "quote_supported_accepted": true_accepted,
            "unsupported_accepted": false_accepted,
            "correct_decisions": correct,
        },
        "finding": "The opened diagnostic exposed a reference-label mismatch. Gate 16D.9 labelled whether a claim was grounded in the full source message, while Gate 16D.10 gave Qwen only the short quote. After a quote-only audit, Qwen retained all 13 claims fully supported by their quote but also accepted five claims whose quotes were too weak. This is useful evidence, but it fails the safety gate and does not validate Qwen as the production judge.",
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(json.loads(args.private.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
