#!/usr/bin/env python3
"""Count visible Codex messages with a local Qwen3 tokenizer; never emit text."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


def session_metadata(path: Path) -> tuple[str, bool] | None:
    identifiers = []
    child = False
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = json.loads(line)
            payload = record.get("payload")
            if isinstance(payload, dict) and record.get("type") == "session_meta":
                identifier = payload.get("id") or payload.get("session_id")
                if identifier:
                    identifiers.append(str(identifier))
                child = child or bool(payload.get("parent_thread_id"))
    return (identifiers[-1], child) if identifiers else None


def visible_messages(path: Path):
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = json.loads(line)
            payload = record.get("payload")
            if not (
                isinstance(payload, dict)
                and record.get("type") == "response_item"
                and payload.get("type") == "message"
                and payload.get("role") in {"user", "assistant"}
            ):
                continue
            role = payload["role"]
            wanted = "input_text" if role == "user" else "output_text"
            texts = [
                item.get("text")
                for item in payload.get("content") or []
                if isinstance(item, dict)
                and item.get("type") == wanted
                and isinstance(item.get("text"), str)
            ]
            if not texts:
                continue
            text = "\n".join(texts)
            identifier = payload.get("id")
            if not identifier:
                identifier = "hash:" + hashlib.sha256(
                    (role + "\0" + str(payload.get("phase")) + "\0" + text).encode()
                ).hexdigest()
            yield str(identifier), role, payload.get("phase"), text


def numeric_summary(values: list[int]) -> dict:
    ordered = sorted(values)
    if not ordered:
        return {}
    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": round(statistics.median(ordered)),
        "mean": round(statistics.mean(ordered)),
        "p90": ordered[round(0.9 * (len(ordered) - 1))],
        "max": ordered[-1],
        "total": sum(ordered),
    }


def build_inventory(paths: list[Path], count_tokens) -> dict:
    sessions = {}
    duplicate_records = 0
    conflicts = 0
    for path in paths:
        metadata = session_metadata(path)
        if metadata is None:
            continue
        session_id, child = metadata
        session = sessions.setdefault(session_id, {"child": False, "messages": {}, "files": 0})
        session["child"] = session["child"] or child
        session["files"] += 1
        for message_id, role, phase, text in visible_messages(path):
            digest = hashlib.sha256(text.encode()).hexdigest()
            if message_id in session["messages"]:
                duplicate_records += 1
                conflicts += session["messages"][message_id][3] != digest
                continue
            session["messages"][message_id] = (role, phase, text, digest)

    rows = []
    totals = Counter()
    for session in sessions.values():
        row = Counter(child=int(session["child"]), files=session["files"])
        for role, phase, text, _digest in session["messages"].values():
            tokens = count_tokens(text)
            row["messages"] += 1
            row["tokens"] += tokens
            row[f"{role}_messages"] += 1
            row[f"{role}_tokens"] += tokens
            if role == "assistant":
                phase_name = phase or "none"
                row[f"assistant_{phase_name}_messages"] += 1
                row[f"assistant_{phase_name}_tokens"] += tokens
        if row["messages"]:
            rows.append(row)
            totals.update(row)

    main = [row for row in rows if not row["child"]]
    children = [row for row in rows if row["child"]]
    buckets = Counter()
    for row in main:
        tokens = row["tokens"]
        bucket = (
            "<1k" if tokens < 1_000 else
            "1k-10k" if tokens < 10_000 else
            "10k-50k" if tokens < 50_000 else
            "50k-100k" if tokens < 100_000 else
            "100k-500k" if tokens < 500_000 else "500k+"
        )
        buckets[bucket] += 1
    return {
        "session_files": len(paths),
        "unique_conversations": len(rows),
        "main_conversations": len(main),
        "child_agent_conversations": len(children),
        "duplicate_message_records_removed": duplicate_records,
        "message_id_conflicts": conflicts,
        "main_conversation_tokens": numeric_summary([row["tokens"] for row in main]),
        "child_conversation_tokens": numeric_summary([row["tokens"] for row in children]),
        "main_conversation_messages": numeric_summary([row["messages"] for row in main]),
        "visible_totals_after_dedup": dict(totals),
        "main_token_buckets": dict(buckets),
        "largest_main_conversation_token_counts": [
            row["tokens"] for row in sorted(main, key=lambda row: row["tokens"], reverse=True)[:20]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--tokenizer", type=Path, required=True)
    arguments = parser.parse_args()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(arguments.tokenizer, local_files_only=True)
    inventory = build_inventory(
        list(arguments.sessions.rglob("*.jsonl")),
        lambda text: len(tokenizer.encode(text, add_special_tokens=False)),
    )
    inventory["tokenizer"] = str(arguments.tokenizer.name)
    inventory["privacy"] = {"conversation_text_emitted": False, "source_files_modified": 0}
    print(json.dumps(inventory, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
