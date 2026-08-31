#!/usr/bin/env python3
"""Strict read-only adapters for locally stored visible AI conversations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Iterable


VERSION = "e007-local-conversation-adapters-v0.1"
CHATGPT_ROOTS = (
    "Library/Application Support/ChatGPT",
    "Library/Application Support/com.openai.chat",
    "Library/Application Support/com.openai.chatgpt",
    "Library/Containers/com.openai.chat",
    "Library/Containers/com.openai.chatgpt",
    "Library/Group Containers/group.com.openai.chat",
    "Library/Group Containers/group.com.openai.chatgpt",
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalized(source: str, conversation: str, message: str, role: str, text: str, coordinate: str) -> dict:
    return {
        "source": source,
        "conversation_id": digest(conversation),
        "message_id": message,
        "role": role,
        "text": text.strip(),
        "source_coordinate": coordinate,
    }


def extract_codex(root: Path) -> list[dict]:
    paths_by_session: dict[str, list[Path]] = defaultdict(list)
    children = set()
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        session_id = None
        child = False
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("payload")
                if row.get("type") == "session_meta" and isinstance(payload, dict):
                    session_id = str(payload.get("id") or payload.get("session_id") or path.stem)
                    child = child or bool(payload.get("parent_thread_id"))
        if session_id and child:
            children.add(session_id)
        if session_id:
            paths_by_session[session_id].append(path)
    conversations: dict[str, list[dict]] = defaultdict(list)
    for session_id, paths in sorted(paths_by_session.items()):
        if session_id in children:
            continue
        seen = set()
        for path in paths:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line_number, line in enumerate(handle, 1):
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    payload = row.get("payload")
                    if row.get("type") != "event_msg" or not isinstance(payload, dict):
                        continue
                    kind = payload.get("type")
                    role = {"user_message": "user", "agent_message": "assistant"}.get(kind)
                    text = payload.get("message")
                    if role is None or not isinstance(text, str) or not text.strip():
                        continue
                    key = digest(json.dumps([row.get("timestamp"), kind, payload.get("phase"), text], ensure_ascii=False))
                    if key in seen:
                        continue
                    seen.add(key)
                    conversations[session_id].append(normalized("codex", session_id, key[:16], role, text, f"{path.name}:{line_number}"))
    return [
        {"source": "codex", "conversation_id": digest(identifier), "messages": messages}
        for identifier, messages in sorted(conversations.items()) if messages
    ]


def text_blocks(content) -> list[str]:
    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    return [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str) and block["text"].strip()]


def extract_claude(root: Path) -> list[dict]:
    conversations: dict[str, list[dict]] = defaultdict(list)
    paths = sorted(root.glob("*/*.jsonl")) if root.is_dir() else []
    for path in paths:
        seen = set()
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                record_type = row.get("type")
                if record_type not in {"user", "assistant"} or row.get("isMeta") is True:
                    continue
                message = row.get("message")
                if not isinstance(message, dict):
                    continue
                role = message.get("role")
                if role not in {"user", "assistant"} or role != record_type:
                    continue
                session_id = str(row.get("sessionId") or path.stem)
                for block_number, text in enumerate(text_blocks(message.get("content")), 1):
                    key = str(row.get("uuid") or message.get("id") or digest(f"{line_number}:{block_number}:{text}")) + f":{block_number}"
                    if key in seen:
                        continue
                    seen.add(key)
                    conversations[session_id].append(normalized("claude_code", session_id, key, role, text, f"{path.name}:{line_number}:{block_number}"))
    return [
        {"source": "claude_code", "conversation_id": digest(identifier), "messages": messages}
        for identifier, messages in sorted(conversations.items()) if messages
    ]


def chatgpt_conversation_objects(data) -> Iterable[dict]:
    if isinstance(data, dict) and isinstance(data.get("mapping"), dict):
        yield data
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("mapping"), dict):
                yield item


def extract_chatgpt_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    result = []
    for position, conversation in enumerate(chatgpt_conversation_objects(data), 1):
        identity = str(conversation.get("id") or conversation.get("conversation_id") or f"{path}:{position}")
        rows = []
        nodes = list(conversation["mapping"].values())
        nodes.sort(key=lambda node: (node.get("message", {}).get("create_time") or 0, str(node.get("id") or "")))
        for node_position, node in enumerate(nodes, 1):
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            author = message.get("author")
            role = author.get("role") if isinstance(author, dict) else None
            if role not in {"user", "assistant"}:
                continue
            content = message.get("content")
            if not isinstance(content, dict) or content.get("content_type", "text") != "text":
                continue
            parts = content.get("parts")
            if not isinstance(parts, list):
                continue
            for part_position, part in enumerate(parts, 1):
                if not isinstance(part, str) or not part.strip():
                    continue
                message_id = str(message.get("id") or node.get("id") or node_position) + f":{part_position}"
                rows.append(normalized("chatgpt_desktop", identity, message_id, role, part, f"{path.name}:{position}:{node_position}:{part_position}"))
        if rows:
            result.append({"source": "chatgpt_desktop", "conversation_id": digest(identity), "messages": rows})
    return result


def chatgpt_roots(home: Path) -> list[Path]:
    candidates = [home / relative for relative in CHATGPT_ROOTS]
    for parent in (home / "Library/Application Support", home / "Library/Containers", home / "Library/Group Containers"):
        if not parent.is_dir():
            continue
        try:
            candidates.extend(path for path in parent.iterdir() if path.is_dir() and ("openai" in path.name.casefold() or "chatgpt" in path.name.casefold()))
        except PermissionError:
            continue
    unique = []
    seen = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if path.is_dir() and key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def extract_chatgpt(home: Path) -> tuple[list[dict], list[str]]:
    conversations = []
    unsupported = []
    for root in chatgpt_roots(home):
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            if path.suffix.casefold() == ".json" and path.name.casefold().startswith("conversations"):
                try:
                    parsed = extract_chatgpt_file(path)
                except (OSError, json.JSONDecodeError):
                    unsupported.append(f"json:{path.name}")
                else:
                    conversations.extend(parsed)
            elif path.suffix.casefold() in {".db", ".sqlite", ".sqlite3", ".realm"}:
                unsupported.append(f"{path.suffix.casefold().lstrip('.')}:{path.name}")
    return conversations, sorted(set(unsupported))


def structural_inventory(home: Path) -> dict:
    roots = chatgpt_roots(home)
    files = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            suffix = path.suffix.casefold()
            if suffix not in {".json", ".jsonl", ".db", ".sqlite", ".sqlite3", ".realm"}:
                continue
            item = {"root": root.name, "relative_path": str(path.relative_to(root)), "format": suffix.lstrip("."), "bytes": path.stat().st_size}
            if suffix in {".db", ".sqlite", ".sqlite3"}:
                try:
                    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                    item["tables"] = [row[0] for row in connection.execute("select name from sqlite_master where type='table' order by name")]
                    connection.close()
                except sqlite3.Error:
                    item["tables"] = ["UNREADABLE"]
            files.append(item)
    codex_root = Path(os.environ.get("CODEX_HOME", home / ".codex")) / "sessions"
    claude_root = home / ".claude" / "projects"
    codex_files = list(codex_root.rglob("*.jsonl")) if codex_root.is_dir() else []
    claude_files = list(claude_root.glob("*/*.jsonl")) if claude_root.is_dir() else []
    return {
        "version": VERSION,
        "platform": platform.system(),
        "privacy": "metadata only; no rows or message text",
        "codex": {"root_found": codex_root.is_dir(), "jsonl_files": len(codex_files), "bytes": sum(path.stat().st_size for path in codex_files)},
        "claude_code": {"root_found": claude_root.is_dir(), "main_jsonl_files": len(claude_files), "bytes": sum(path.stat().st_size for path in claude_files)},
        "chatgpt_desktop": {"roots": [str(path) for path in roots], "candidate_files": files},
    }


def write_private(path: Path, payload: dict) -> None:
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "extract"))
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "inventory":
        print(json.dumps(structural_inventory(args.home), ensure_ascii=False, indent=2))
        return
    codex_root = Path(os.environ.get("CODEX_HOME", args.home / ".codex")) / "sessions"
    claude_root = args.home / ".claude" / "projects"
    chatgpt, unsupported = extract_chatgpt(args.home)
    conversations = extract_codex(codex_root) + extract_claude(claude_root) + chatgpt
    summary = {
        source: {
            "conversations": sum(item["source"] == source for item in conversations),
            "messages": sum(len(item["messages"]) for item in conversations if item["source"] == source),
        }
        for source in ("codex", "claude_code", "chatgpt_desktop")
    }
    payload = {"schema_version": "0.1-private", "adapter_version": VERSION, "summary": summary, "unsupported_chatgpt_formats": unsupported, "conversations": conversations}
    if args.output:
        write_private(args.output, payload)
    print(json.dumps({"adapter_version": VERSION, "summary": summary, "unsupported_chatgpt_formats": unsupported, "output": str(args.output) if args.output else None}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
