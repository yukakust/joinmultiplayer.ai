#!/usr/bin/env python3
"""Prepare one private Codex-library payload for E007 Gate 16D."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path


CLIENT_VERSION = "e007-remote-two-pocket-node-v0.1"
PROTOCOL_URL = "https://joinmultiplayer.ai/experiments/E007/remote-two-pocket-protocol-v0.1.json"
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def load_protocol(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": CLIENT_VERSION})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


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
                key = payload.get("id") or hashlib.sha256((role + "\0" + text).encode()).hexdigest()
                messages.setdefault(str(key), {"role": role, "text": text})
    return list(messages.values())


def words(value: str) -> list[str]:
    return [word.lower().replace("ё", "е") for word in WORD_RE.findall(value)]


def rank_conversations(sessions: Path, protocol: dict) -> list[dict]:
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

    terms = {term.lower().replace("ё", "е") for term in protocol["local_library"]["focus_terms"]}
    limit = int(protocol["local_library"]["max_visible_characters_per_conversation"])
    candidates = []
    for identifier, paths in grouped.items():
        if identifier in children:
            continue
        messages = visible_messages(paths)
        joined = "\n".join(message["text"] for message in messages)
        if not messages or len(joined) > limit:
            continue
        normalized = " ".join(words(joined))
        counts = {term: normalized.count(term) for term in terms}
        distinct = sum(value > 0 for value in counts.values())
        frequency = sum(min(value, 12) for value in counts.values())
        score = distinct * 100 + frequency
        if score:
            candidates.append((score, identifier, messages))
    candidates.sort(key=lambda item: (-item[0], hashlib.sha256(item[1].encode()).hexdigest()))

    selected = []
    for index, (score, identifier, messages) in enumerate(candidates[: protocol["local_library"]["max_conversations_per_node"]], 1):
        selected.append({
            "conversation": f"C{index:02d}",
            "conversation_hash": hashlib.sha256(identifier.encode()).hexdigest(),
            "selection_score": score,
            "messages": [
                {"id": f"M{message_index:04d}", **message}
                for message_index, message in enumerate(messages, 1)
            ],
        })
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", choices=("MAC", "YUKA"), required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--protocol-url", default=PROTOCOL_URL)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite {args.output}")
    protocol = load_protocol(args.protocol_url)
    if protocol.get("status") != "locked_before_local_selection_or_model_inference":
        raise SystemExit("Protocol is not locked")
    conversations = rank_conversations(args.sessions, protocol)
    if not conversations:
        raise SystemExit("No eligible matching Codex conversation was found")
    payload = {
        "schema_version": "0.1-private",
        "client_version": CLIENT_VERSION,
        "protocol_sha256": hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest(),
        "node": args.node,
        "device": args.device,
        "question": protocol["question"],
        "conversations": conversations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({
        "node": args.node,
        "conversations": len(conversations),
        "messages": sum(len(item["messages"]) for item in conversations),
        "characters": sum(sum(len(message["text"]) for message in item["messages"]) for item in conversations),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
