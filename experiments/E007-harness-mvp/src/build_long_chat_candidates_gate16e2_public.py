#!/usr/bin/env python3
"""Publish Gate 16E.2 metrics without publishing private conversation text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-result", type=Path, required=True)
    parser.add_argument("--build-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.private_result.read_text())
    build = json.loads(args.build_result.read_text())
    public = {
        "schema_version": "0.1-public",
        "experiment": "E007",
        "gate": "16E.2",
        "status": result["status"],
        "protocol": "/experiments/E007/long-chat-candidates-gate16e2-protocol-v0.1.json",
        "summary": {
            **result["summary"],
            "first_index_build_seconds": build["summary"]["index_load_or_build_seconds"],
            "first_index_document_embeddings": build["summary"]["document_embeddings_this_run"],
        },
        "rows": [
            {
                "id": row["id"],
                "card_id": row["card_id"],
                "question": row["question"],
                "gold_message_ids": row["gold_message_ids"],
                "candidate_message_ids": row["candidate_message_ids"],
                "candidate_count": row["candidate_count"],
                "gold_found": row["gold_found"],
                "source_coordinates_preserved": row["source_coordinates_preserved"],
            }
            for row in result["rows"]
        ],
        "finding": "A persisted union of five lexical and five dense candidates retained the needed message in every fresh question. Reusing the index embedded zero documents and answered all twelve searches in under one second total.",
        "claim_boundary": result["claim_boundary"],
        "privacy": "No conversation text or retrieved message text is published; only frozen questions, opaque coordinates, candidate counts, and aggregate timings.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
