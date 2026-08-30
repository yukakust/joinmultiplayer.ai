#!/usr/bin/env python3
"""Export every allowlisted main Codex conversation for private topic indexing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


CLIENT_VERSION = "e007-topic-index-node-v0.1"


def session_metadata(path: Path) -> tuple[str, bool] | None:
    identifier = None
    child = False
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = record.get("payload")
            if record.get("type") == "session_meta" and isinstance(payload, dict):
                identifier = payload.get("id") or payload.get("session_id") or identifier
                child = child or bool(payload.get("parent_thread_id"))
    return (str(identifier), child) if identifier else None


def visible_messages(paths: list[Path]) -> list[dict]:
    messages = {}
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload")
                if not (
                    record.get("type") == "response_item"
                    and isinstance(payload, dict)
                    and payload.get("type") == "message"
                    and payload.get("role") in {"user", "assistant"}
                ):
                    continue
                role = payload["role"]
                wanted = "input_text" if role == "user" else "output_text"
                text = "\n".join(
                    item["text"] for item in payload.get("content") or []
                    if isinstance(item, dict) and item.get("type") == wanted and isinstance(item.get("text"), str)
                ).strip()
                if not text:
                    continue
                key = payload.get("id") or hashlib.sha256((role + "\0" + str(payload.get("phase")) + "\0" + text).encode()).hexdigest()
                messages.setdefault(str(key), {"role": role, "phase": payload.get("phase"), "text": text})
    return list(messages.values())


def build_payload(sessions: Path, node: str, device: str) -> dict:
    grouped = {}
    children = set()
    for path in sessions.rglob("*.jsonl"):
        metadata = session_metadata(path)
        if metadata is None:
            continue
        identifier, child = metadata
        grouped.setdefault(identifier, []).append(path)
        if child:
            children.add(identifier)
    conversations = []
    for identifier, paths in grouped.items():
        if identifier in children:
            continue
        messages = visible_messages(paths)
        if not messages:
            continue
        rows = [{"id": f"M{index:04d}", **message} for index, message in enumerate(messages, 1)]
        snapshot = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        conversations.append({
            "conversation_hash": hashlib.sha256(identifier.encode()).hexdigest(),
            "source_snapshot_hash": snapshot,
            "messages": rows,
        })
    conversations.sort(key=lambda item: item["conversation_hash"])
    return {
        "schema_version": "0.1-private",
        "client_version": CLIENT_VERSION,
        "node": node,
        "device": device,
        "conversations": conversations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", choices=("MAC", "YUKA"), required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite {args.output}")
    payload = build_payload(args.sessions, args.node, args.device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({
        "node": args.node,
        "conversations": len(payload["conversations"]),
        "messages": sum(len(item["messages"]) for item in payload["conversations"]),
        "characters": sum(len(message["text"]) for item in payload["conversations"] for message in item["messages"]),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
