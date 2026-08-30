#!/usr/bin/env python3
"""Measure a private UI-event conversation payload with the pinned Qwen tokenizer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


MODEL = "Qwen/Qwen3-8B"
REVISION = "b968826d9c46dd6066d109eabc6255188de91218"


def main() -> None:
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    rows = []
    for index, conversation in enumerate(payload["conversations"], 1):
        tokens = sum(
            len(tokenizer.encode(message["text"], add_special_tokens=False))
            for message in conversation["messages"]
        )
        rows.append({
            "card_id": f'{payload["node"]}-C{index:04d}',
            "messages": len(conversation["messages"]),
            "qwen_tokens": tokens,
        })
    ordered = sorted(rows, key=lambda item: item["qwen_tokens"], reverse=True)
    result = {
        "schema_version": "0.2-inventory",
        "source_client_version": payload["client_version"],
        "model": MODEL,
        "revision": REVISION,
        "conversations": len(rows),
        "messages": sum(item["messages"] for item in rows),
        "total_qwen_tokens": sum(item["qwen_tokens"] for item in rows),
        "at_most_10000": sum(item["qwen_tokens"] <= 10_000 for item in rows),
        "over_10000": sum(item["qwen_tokens"] > 10_000 for item in rows),
        "ordered_by_length": ordered,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
