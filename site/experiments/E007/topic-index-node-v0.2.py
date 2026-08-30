#!/usr/bin/env python3
"""Export the human-visible Codex event stream for private topic indexing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


CLIENT_VERSION = "e007-topic-index-node-v0.2"
VISIBLE_EVENTS = {"user_message": "user", "agent_message": "assistant"}


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


def visible_ui_messages(paths: list[Path]) -> list[dict]:
    """Return only events that Codex exposed in the human conversation UI."""
    events = []
    seen = set()
    for path in sorted(paths):
        with path.open(encoding="utf-8", errors="replace") as handle:
            for position, line in enumerate(handle):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload")
                if record.get("type") != "event_msg" or not isinstance(payload, dict):
                    continue
                event_type = payload.get("type")
                role = VISIBLE_EVENTS.get(event_type)
                text = payload.get("message")
                if role is None or not isinstance(text, str) or not text.strip():
                    continue
                text = text.strip()
                timestamp = str(record.get("timestamp") or "")
                phase = payload.get("phase")
                fingerprint = hashlib.sha256(
                    json.dumps([timestamp, event_type, phase, text], ensure_ascii=False).encode()
                ).hexdigest()
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                events.append({
                    "sort": (timestamp, str(path), position),
                    "role": role,
                    "phase": phase,
                    "text": text,
                })
    events.sort(key=lambda item: item["sort"])
    return [{key: value for key, value in item.items() if key != "sort"} for item in events]


def build_payload(sessions: Path, node: str, device: str) -> dict:
    grouped: dict[str, list[Path]] = {}
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
    eligible = [(identifier, paths) for identifier, paths in grouped.items() if identifier not in children]
    for position, (identifier, paths) in enumerate(eligible, 1):
        messages = visible_ui_messages(paths)
        if not messages:
            continue
        rows = [{"id": f"M{index:04d}", **message} for index, message in enumerate(messages, 1)]
        snapshot = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        conversations.append({
            "conversation_hash": hashlib.sha256(identifier.encode()).hexdigest(),
            "source_snapshot_hash": snapshot,
            "messages": rows,
        })
        if position == 1 or position % 20 == 0 or position == len(eligible):
            print(f"Scanned {position}/{len(eligible)} main conversations…", file=sys.stderr, flush=True)
    conversations.sort(key=lambda item: item["conversation_hash"])
    return {
        "schema_version": "0.2-private",
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
