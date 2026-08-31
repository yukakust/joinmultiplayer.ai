#!/usr/bin/env python3
"""Strict read-only adapters for locally stored visible AI conversations."""

from __future__ import annotations

import argparse
import bz2
import collections
import ctypes
import gzip
import hashlib
import json
import lzma
import os
import platform
import plistlib
import sqlite3
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Iterable


VERSION = "e007-local-conversation-adapters-v0.5"
MAX_DECODED_BYTES = 8 * 1024 * 1024
CHATGPT_ROOTS = (
    "Library/Application Support/ChatGPT",
    "Library/Application Support/com.openai.chat",
    "Library/Application Support/com.openai.chatgpt",
    "Library/Containers/com.openai.chat",
    "Library/Containers/com.openai.chatgpt",
    "Library/Group Containers/group.com.openai.chat",
    "Library/Group Containers/group.com.openai.chatgpt",
    "Library/Caches/com.openai.chat",
    "Library/HTTPStorages/com.openai.chat",
    "Library/WebKit/com.openai.chat",
    "Library/Saved Application State/com.openai.chat.savedState",
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


def extract_chatgpt_value(data, coordinate_name: str) -> list[dict]:
    result = []
    for position, conversation in enumerate(chatgpt_conversation_objects(data), 1):
        identity = str(conversation.get("id") or conversation.get("conversation_id") or f"{coordinate_name}:{position}")
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
                rows.append(normalized("chatgpt_desktop", identity, message_id, role, part, f"{coordinate_name}:{position}:{node_position}:{part_position}"))
        if rows:
            result.append({"source": "chatgpt_desktop", "conversation_id": digest(identity), "messages": rows})
    return result


def extract_chatgpt_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    return extract_chatgpt_value(data, path.name)


def extract_one_claude_file(path: Path) -> list[dict]:
    conversations: dict[str, list[dict]] = defaultdict(list)
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


def chatgpt_roots(home: Path) -> list[Path]:
    candidates = [home / relative for relative in CHATGPT_ROOTS]
    for parent in (home / "Library/Application Support", home / "Library/Containers", home / "Library/Group Containers"):
        if not parent.is_dir():
            continue
        try:
            candidates.extend(path for path in parent.iterdir() if path.is_dir() and "chatgpt" in path.name.casefold())
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
    all_files = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            suffix = path.suffix.casefold()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            kind = suffix.lstrip(".") or "no_extension"
            try:
                with path.open("rb") as handle:
                    header = handle.read(16)
            except (OSError, PermissionError):
                header = b""
            if header.startswith(b"SQLite format 3"):
                kind = "sqlite_header"
            all_files.append({"root": root.name, "relative_path": str(path.relative_to(root)), "format": kind, "bytes": size})
            if suffix not in {".json", ".jsonl", ".db", ".sqlite", ".sqlite3", ".realm"}:
                continue
            item = {"root": root.name, "relative_path": str(path.relative_to(root)), "format": kind, "bytes": size}
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
        "chatgpt_desktop": {
            "roots": [str(path) for path in roots],
            "files": len(all_files),
            "bytes": sum(item["bytes"] for item in all_files),
            "formats": {
                kind: {"files": sum(item["format"] == kind for item in all_files), "bytes": sum(item["bytes"] for item in all_files if item["format"] == kind)}
                for kind in sorted({item["format"] for item in all_files})
            },
            "largest_files": sorted(all_files, key=lambda item: (-item["bytes"], item["relative_path"]))[:40],
            "recognized_candidates": files,
        },
    }


def json_shape(value, depth: int = 0):
    if depth >= 4:
        return type(value).__name__
    if isinstance(value, dict):
        keys = sorted(str(key) for key in value)
        dynamic = len(keys) > 20 or (keys and sum(bool(__import__("re").fullmatch(r"[0-9a-fA-F-]{20,}", key)) for key in keys) > len(keys) / 2)
        if dynamic:
            first = value[next(iter(value))] if value else None
            return {"type": "object", "dynamic_keys": len(keys), "value": json_shape(first, depth + 1)}
        return {"type": "object", "fields": {key: json_shape(value[key], depth + 1) for key in keys}}
    if isinstance(value, list):
        shapes = []
        for item in value[:5]:
            shape = json_shape(item, depth + 1)
            if shape not in shapes:
                shapes.append(shape)
        return {"type": "array", "items_seen": min(len(value), 5), "item_shapes": shapes}
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def decode_container(path: Path):
    data = path.read_bytes()
    kind = "binary"
    decoded = data
    if data.startswith(b"\x1f\x8b"):
        kind = "gzip"
        decoded = gzip.decompress(data)
    elif data.startswith(b"bplist00"):
        return "binary_plist", plistlib.loads(data)
    stripped = decoded.lstrip()
    if stripped.startswith((b"{", b"[")):
        return ("gzip_json" if kind == "gzip" else "json"), json.loads(decoded)
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        return kind, None
    return "utf8_text", None if not text.lstrip().startswith(("{", "[")) else json.loads(text)


def structured_bytes(method: str, data: bytes):
    stripped = data.lstrip()
    if stripped.startswith((b"{", b"[")):
        try:
            return method + "_json", json.loads(stripped)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    if data.startswith(b"bplist00") or stripped.startswith(b"<?xml"):
        try:
            return method + "_plist", plistlib.loads(data)
        except (plistlib.InvalidFileException, ValueError):
            pass
    return method + "_binary", None


def apple_decompress(data: bytes, algorithm: int) -> bytes | None:
    if platform.system() != "Darwin":
        return None
    try:
        library = ctypes.CDLL("/usr/lib/libcompression.dylib")
    except OSError:
        return None
    function = library.compression_decode_buffer
    function.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint32]
    function.restype = ctypes.c_size_t
    source = ctypes.create_string_buffer(data)
    destination = ctypes.create_string_buffer(MAX_DECODED_BYTES)
    size = function(destination, MAX_DECODED_BYTES, source, len(data), None, algorithm)
    return destination.raw[:size] if size else None


def decode_standard_formats(path: Path) -> tuple[str, object | None, list[str]]:
    data = path.read_bytes()
    attempts = []
    direct_method, direct_value = structured_bytes("direct", data)
    attempts.append(direct_method)
    if direct_value is not None:
        return direct_method, direct_value, attempts
    for offset in range(1, min(4096, len(data))):
        if data[offset:offset + 1] not in {b"{", b"["}:
            continue
        method, value = structured_bytes(f"json_offset_{offset}", data[offset:])
        if value is not None:
            attempts.append(method)
            return method, value, attempts
    standard = (
        ("gzip", lambda: gzip.decompress(data)),
        ("zlib", lambda: zlib.decompress(data)),
        ("raw_deflate", lambda: zlib.decompress(data, -15)),
        ("bz2", lambda: bz2.decompress(data)),
        ("lzma", lambda: lzma.decompress(data)),
    )
    for name, decoder in standard:
        try:
            decoded = decoder()
        except Exception:
            attempts.append(name + "_failed")
            continue
        if len(decoded) > MAX_DECODED_BYTES:
            attempts.append(name + "_too_large")
            continue
        method, value = structured_bytes(name, decoded)
        attempts.append(method)
        if value is not None:
            return method, value, attempts
    for name, algorithm in (("apple_lzfse", 0x801), ("apple_lz4", 0x100), ("apple_lz4_raw", 0x101), ("apple_zlib", 0x205), ("apple_lzma", 0x306)):
        decoded = apple_decompress(data, algorithm)
        if decoded is None:
            attempts.append(name + "_failed")
            continue
        method, value = structured_bytes(name, decoded)
        attempts.append(method)
        if value is not None:
            return method, value, attempts
    return "unsupported_binary", None, attempts


def single_chatgpt_decode(home: Path, limit: int = 20) -> tuple[dict, dict]:
    paths = []
    for root in chatgpt_roots(home):
        paths.extend(root.glob("conversations-v3-*/*.data"))
    path = newest({item.resolve(): item for item in paths}.values())
    if path is None:
        return {"sources": []}, {"status": "not_found", "source_files_read": 0, "visible_messages": 0}
    method, value, attempts = decode_standard_formats(path)
    conversations = extract_chatgpt_value(value, path.name) if value is not None else []
    selected = conversations[0] if conversations else None
    messages = selected["messages"][-limit:] if selected else []
    private = {"schema_version": "0.1-private", "adapter_version": VERSION, "sources": []}
    if messages:
        private["sources"].append({"source": "chatgpt_desktop", "conversation_id": selected["conversation_id"], "messages": messages})
    public = {
        "status": "sampled" if messages else "unsupported_binary",
        "source_files_read": 1,
        "decoder": method,
        "decoder_attempts": attempts,
        "visible_messages": len(messages),
        "schema": json_shape(value) if value is not None and not messages else None,
        "privacy": "no bytes, values, paths or identifiers in stdout",
    }
    return private, public


def claude_structure(home: Path) -> dict:
    root = home / ".claude" / "projects"
    record_types: collections.Counter[str] = collections.Counter()
    blocks_by_role: dict[str, collections.Counter[str]] = {"user": collections.Counter(), "assistant": collections.Counter()}
    meta = 0
    invalid = 0
    for path in sorted(root.glob("*/*.jsonl")) if root.is_dir() else []:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    invalid += 1
                    continue
                record_type = str(row.get("type") or "missing")
                record_types[record_type] += 1
                meta += row.get("isMeta") is True
                message = row.get("message")
                if not isinstance(message, dict):
                    continue
                role = message.get("role")
                if role not in blocks_by_role:
                    continue
                content = message.get("content")
                if isinstance(content, str):
                    blocks_by_role[role]["string"] += 1
                elif isinstance(content, list):
                    for block in content:
                        blocks_by_role[role][str(block.get("type") or "missing") if isinstance(block, dict) else type(block).__name__] += 1
    return {
        "main_jsonl_files": len(list(root.glob("*/*.jsonl"))) if root.is_dir() else 0,
        "record_types": dict(sorted(record_types.items())),
        "content_blocks_by_role": {role: dict(sorted(counter.items())) for role, counter in blocks_by_role.items()},
        "meta_records": meta,
        "invalid_json_lines": invalid,
    }


def chatgpt_container_shapes(home: Path) -> dict:
    fingerprints: dict[str, dict] = {}
    failures: collections.Counter[str] = collections.Counter()
    scanned = 0
    for root in chatgpt_roots(home):
        for path in sorted(root.glob("conversations-v3-*/*.data")):
            scanned += 1
            try:
                kind, value = decode_container(path)
            except Exception as error:
                failures[type(error).__name__] += 1
                continue
            shape = json_shape(value) if value is not None else None
            fingerprint = hashlib.sha256(json.dumps([kind, shape], sort_keys=True).encode()).hexdigest()[:16]
            item = fingerprints.setdefault(fingerprint, {"container": kind, "shape": shape, "files": 0, "bytes": 0})
            item["files"] += 1
            item["bytes"] += path.stat().st_size
    return {"files_scanned": scanned, "schema_fingerprints": list(fingerprints.values()), "failures": dict(sorted(failures.items()))}


def inspect_formats(home: Path) -> dict:
    return {
        "version": VERSION,
        "platform": platform.system(),
        "privacy": "schema only; no message values, database rows or conversation identifiers",
        "claude_code": claude_structure(home),
        "chatgpt_desktop": chatgpt_container_shapes(home),
    }


def newest(paths: Iterable[Path]) -> Path | None:
    candidates = list(paths)
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, str(path))) if candidates else None


def minimal_sample(home: Path, limit: int = 20) -> tuple[dict, dict]:
    private_sources = []
    public_sources = {}

    claude_root = home / ".claude" / "projects"
    claude_path = newest(claude_root.glob("*/*.jsonl")) if claude_root.is_dir() else None
    if claude_path is None:
        public_sources["claude_code"] = {"status": "not_found", "source_files_read": 0, "visible_messages": 0}
    else:
        conversations = extract_one_claude_file(claude_path)
        selected = conversations[-1] if conversations else None
        messages = selected["messages"][-limit:] if selected else []
        private_sources.append({"source": "claude_code", "conversation_id": selected["conversation_id"] if selected else None, "messages": messages})
        public_sources["claude_code"] = {"status": "sampled" if messages else "no_visible_messages", "source_files_read": 1, "visible_messages": len(messages)}

    data_paths = []
    for root in chatgpt_roots(home):
        data_paths.extend(root.glob("conversations-v3-*/*.data"))
    chatgpt_path = newest({path.resolve(): path for path in data_paths}.values())
    if chatgpt_path is None:
        public_sources["chatgpt_desktop"] = {"status": "not_found", "source_files_read": 0, "visible_messages": 0}
    else:
        try:
            container, value = decode_container(chatgpt_path)
            conversations = extract_chatgpt_value(value, chatgpt_path.name) if value is not None else []
        except Exception as error:
            container, conversations = f"error:{type(error).__name__}", []
        selected = conversations[0] if conversations else None
        messages = selected["messages"][-limit:] if selected else []
        if messages:
            private_sources.append({"source": "chatgpt_desktop", "conversation_id": selected["conversation_id"], "messages": messages})
        public_sources["chatgpt_desktop"] = {
            "status": "sampled" if messages else "format_not_yet_supported",
            "source_files_read": 1,
            "container": container,
            "visible_messages": len(messages),
            "schema": None if messages else json_shape(value) if 'value' in locals() and value is not None else None,
        }

    private = {"schema_version": "0.1-private", "adapter_version": VERSION, "limit_per_source": limit, "sources": private_sources}
    public = {
        "adapter_version": VERSION,
        "limit_per_source": limit,
        "sources": public_sources,
        "total_source_files_read": sum(source["source_files_read"] for source in public_sources.values()),
        "total_visible_messages": sum(source["visible_messages"] for source in public_sources.values()),
        "privacy": "message text exists only in the 0600 local output; stdout contains counts and schema only",
    }
    return private, public


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
    parser.add_argument("command", choices=("inventory", "inspect-formats", "sample", "decode-one-chatgpt", "extract"))
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--source", choices=("all", "codex", "claude_code", "chatgpt_desktop"), default="all")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "inventory":
        print(json.dumps(structural_inventory(args.home), ensure_ascii=False, indent=2))
        return
    if args.command == "inspect-formats":
        print(json.dumps(inspect_formats(args.home), ensure_ascii=False, indent=2))
        return
    if args.command == "sample":
        if args.output is None:
            raise SystemExit("sample requires --output")
        private, public = minimal_sample(args.home, limit=20)
        write_private(args.output, private)
        print(json.dumps({**public, "output": str(args.output)}, ensure_ascii=False, indent=2))
        return
    if args.command == "decode-one-chatgpt":
        if args.output is None:
            raise SystemExit("decode-one-chatgpt requires --output")
        private, public = single_chatgpt_decode(args.home, limit=20)
        write_private(args.output, private)
        print(json.dumps({**public, "output": str(args.output)}, ensure_ascii=False, indent=2))
        return
    codex_root = Path(os.environ.get("CODEX_HOME", args.home / ".codex")) / "sessions"
    claude_root = args.home / ".claude" / "projects"
    conversations = []
    unsupported = []
    if args.source in {"all", "codex"}:
        conversations.extend(extract_codex(codex_root))
    if args.source in {"all", "claude_code"}:
        conversations.extend(extract_claude(claude_root))
    if args.source in {"all", "chatgpt_desktop"}:
        chatgpt, unsupported = extract_chatgpt(args.home)
        conversations.extend(chatgpt)
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
