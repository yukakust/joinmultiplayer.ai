#!/usr/bin/env python3
"""Create a privacy-safe public Gate 16D.2 result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(private: dict) -> dict:
    queries = []
    for row in private["queries"]:
        queries.append({
            "id": row["id"],
            "question": row["question"],
            "expected_chat": row["gold_card_id"],
            "expected_chat_rank": row["gold_rank"],
            "first_five_chats": [
                {"card_id": item["card_id"], "score": item["score"]}
                for item in row["top_5"]
            ],
        })
    return {
        "schema_version": "0.1",
        "experiment": private["experiment"],
        "gate": private["gate"],
        "status": private["status"],
        "protocol": "/experiments/E007/whole-chat-index-protocol-v0.1.json",
        "model": private["model"],
        "fastembed": private["fastembed"],
        "conversations": private["conversations"],
        "indexed_messages": private["indexed_messages"],
        "runtime_seconds": private["runtime_seconds"],
        "summary": private["summary"],
        "queries": queries,
        "manual_review": {
            "result": "The only top-10 miss is real, not a gold-label error.",
            "failure": "Q01 retrieved an unrelated huge chat containing PostgreSQL backup language. The correct transferred curator corpus conversation ranked 26th.",
        },
        "decision": "FAIL the locked gate. Preserve the multi-vector baseline; test a lexical-plus-neural union or stronger embedding model on the same locked questions.",
        "claim_boundary": private["claim_boundary"],
        "privacy": "No conversation text, matched message text, session identifier, path or conversation hash is public."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    private = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(private), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
