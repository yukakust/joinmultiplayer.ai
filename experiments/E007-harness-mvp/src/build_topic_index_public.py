#!/usr/bin/env python3
"""Build a privacy-safe public Gate 16D.1 result from a private topic index."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def error_kind(reason: str) -> str:
    if "complete save_topics" in reason:
        return "incomplete topic tool-call"
    if "complete merge_topics" in reason:
        return "incomplete merge tool-call"
    if "evidence coordinate" in reason:
        return "invalid evidence coordinate"
    if "source_topic_ids" in reason:
        return "invalid merged topic IDs"
    if "delimiter" in reason:
        return "invalid tool JSON"
    return "other format error"


def build(private: dict, runtime_seconds: int) -> dict:
    rows = []
    reasons = collections.Counter()
    valid = 0
    short_valid = short_total = long_valid = long_total = 0
    for card in private["cards"]:
        is_long = card["qwen_tokens"] > 10_000
        protocol_valid = card["status"] == "CARD" and 0 < len(card["topics"]) <= 12
        kinds = sorted({error_kind(item["error"]) for item in card["errors"]})
        if card["status"] == "CARD" and len(card["topics"]) > 12:
            kinds.append("too many conversation topics")
        reasons.update(kinds)
        valid += int(protocol_valid)
        if is_long:
            long_total += 1; long_valid += int(protocol_valid)
        else:
            short_total += 1; short_valid += int(protocol_valid)
        rows.append({
            "card_id": card["card_id"], "qwen_tokens": card["qwen_tokens"],
            "blocks": card["blocks"], "topic_count": len(card["topics"]),
            "protocol_status": "VALID" if protocol_valid else "ERROR",
            "error_kinds": kinds,
        })
    return {
        "schema_version": "0.1", "experiment": "E007", "gate": "16D.1",
        "status": "yukabox_index_complete_owner_topic_review_pending",
        "protocol": "/experiments/E007/topic-index-protocol-v0.1.json",
        "result": {
            "conversations": len(rows), "valid_cards": valid,
            "invalid_cards": len(rows) - valid,
            "short_conversations": {"valid": short_valid, "total": short_total},
            "long_conversations": {"valid": long_valid, "total": long_total},
            "runtime_seconds": runtime_seconds,
            "error_kinds": dict(reasons),
        },
        "cards": rows,
        "decision": {
            "accepted": "Conversation-level cards are promising for short chats and deserve human semantic review.",
            "rejected": "The current one-shot long-conversation merge and current tool-call reliability are not accepted.",
            "next": "Inspect real card meanings, then replace long-chat one-shot merge with a resumable bounded tree merge before indexing MacBook. Do not test question search yet."
        },
        "privacy": {
            "raw_conversations_public": False, "topic_names_public": False,
            "topic_summaries_public": False, "session_ids_public": False,
            "card_metrics_public": True
        },
        "claim_boundary": "This result measures mechanical card completion, not whether the generated topic names faithfully summarize every conversation."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-seconds", type=int, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    private = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(private, args.runtime_seconds), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
