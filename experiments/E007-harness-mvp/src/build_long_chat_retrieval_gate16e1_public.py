#!/usr/bin/env python3
"""Build privacy-safe Gate 16E.1 result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = json.loads(args.private.read_text())
    protocol = json.loads(args.protocol.read_text())
    rows = []
    for row in private["rows"]:
        rows.append({
            "id": row["id"], "card_id": row["card_id"], "question": row["question"],
            "gold_message_ids": row["gold_message_ids"], "dense_rank": row["dense_rank"],
            "lexical_rank": row["lexical_rank"], "hybrid_rank": row["hybrid_rank"],
            "dense_top_5_ids": [item["message_id"] for item in row["dense_top_5"]],
            "lexical_top_5_ids": [item["message_id"] for item in row["lexical_top_5"]],
            "hybrid_top_5_ids": [item["message_id"] for item in row["hybrid_top_5"]],
            "source_coordinates_preserved": row["source_coordinates_preserved"],
        })
    result = {
        "schema_version": "0.1", "experiment": "E007", "gate": "16E.1",
        "status": private["status"], "protocol": "/experiments/E007/long-chat-retrieval-gate16e1-protocol-v0.1.json",
        "summary": private["summary"], "rows": rows,
        "finding": "The locked hybrid gate failed: hybrid recall was 6/12 at one and 9/12 at three. Plain lexical BM25 was stronger and placed all 12 accepted messages in its top five. Do not select one hybrid winner. The next candidate returns a bounded union of candidates and lets the reader inspect them one at a time.",
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
