"""Deny-by-default readers for the local Pocket i conversation library."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import platform
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .pipeline import Conversation, Message


SOURCE_NAMES = ("codex", "claude_code", "chatgpt_desktop")


@dataclass(frozen=True)
class AdapterStatus:
    source: str
    status: str
    conversations: int
    messages: int
    files_read: int
    unsupported_files: int = 0


@dataclass(frozen=True)
class LocalLibrary:
    conversations: tuple[Conversation, ...]
    adapters: tuple[AdapterStatus, ...]

    def public_summary(self) -> dict[str, object]:
        """Return counts only: no text, paths, IDs or source coordinates."""
        return {
            "schema_version": "desktop-library-summary-v0.1",
            "platform": platform.system(),
            "privacy": "counts only; no text, paths, conversation IDs or message coordinates",
            "total_conversations": len(self.conversations),
            "total_messages": sum(len(item.messages) for item in self.conversations),
            "adapters": [asdict(item) for item in self.adapters],
        }


@dataclass(frozen=True)
class ConversationCount:
    source: str
    status: str
    conversations: int


@dataclass(frozen=True)
class LocalLibraryCounts:
    adapters: tuple[ConversationCount, ...]

    @property
    def total_conversations(self) -> int:
        return sum(item.conversations for item in self.adapters)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _path_token(path: Path) -> str:
    return _hash(str(path.resolve()))[:12]


def _conversation(source: str, raw_id: str, messages: Sequence[Message]) -> Conversation:
    return Conversation(_hash(f"{source}:{raw_id}"), source, tuple(messages))


def _visible_text_blocks(content: object) -> list[str]:
    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    return [
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
        and block["text"].strip()
    ]


def read_codex(root: Path) -> tuple[tuple[Conversation, ...], int]:
    """Read only visible Codex user/agent event messages from main sessions."""
    grouped: dict[str, list[tuple[str, Message]]] = {}
    child_sessions: set[str] = set()
    files_read = 0
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else ():
        files_read += 1
        path_token = _path_token(path)
        raw_session_id: str | None = None
        is_child = False
        rows: list[tuple[str, str, str, str]] = []
        try:
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("payload")
                if row.get("type") == "session_meta" and isinstance(payload, dict):
                    raw_session_id = str(payload.get("id") or payload.get("session_id") or "") or None
                    is_child = is_child or bool(payload.get("parent_thread_id"))
                    continue
                if row.get("type") != "event_msg" or not isinstance(payload, dict):
                    continue
                role = {"user_message": "user", "agent_message": "assistant"}.get(payload.get("type"))
                text = payload.get("message")
                if role is None or not isinstance(text, str) or not text.strip():
                    continue
                event_key = _hash(json.dumps([row.get("timestamp"), payload.get("type"), payload.get("phase"), text], ensure_ascii=False))
                rows.append((event_key, f"codex:{path_token}:{line_number}", role, text.strip()))
        if raw_session_id is None:
            continue
        if is_child:
            child_sessions.add(raw_session_id)
        bucket = grouped.setdefault(raw_session_id, [])
        bucket.extend((key, Message(coordinate, role, text)) for key, coordinate, role, text in rows)

    result = []
    for raw_session_id, keyed_messages in sorted(grouped.items()):
        if raw_session_id in child_sessions:
            continue
        seen: set[str] = set()
        messages = []
        for key, message in keyed_messages:
            if key in seen:
                continue
            seen.add(key)
            messages.append(message)
        if messages:
            result.append(_conversation("codex", raw_session_id, messages))
    return tuple(result), files_read


def read_claude_code(root: Path) -> tuple[tuple[Conversation, ...], int]:
    """Read only visible text blocks from main Claude Code messages."""
    grouped: dict[str, list[tuple[str, Message]]] = {}
    files_read = 0
    for path in sorted(root.glob("*/*.jsonl")) if root.is_dir() else ():
        files_read += 1
        path_token = _path_token(path)
        try:
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                record_type = row.get("type")
                if record_type not in {"user", "assistant"} or row.get("isMeta") is True:
                    continue
                message = row.get("message")
                if not isinstance(message, dict) or message.get("role") != record_type:
                    continue
                raw_session_id = str(row.get("sessionId") or path.stem)
                for block_number, text in enumerate(_visible_text_blocks(message.get("content")), 1):
                    key = str(row.get("uuid") or message.get("id") or _hash(f"{line_number}:{block_number}:{text}")) + f":{block_number}"
                    coordinate = f"claude:{path_token}:{line_number}:{block_number}"
                    grouped.setdefault(raw_session_id, []).append((key, Message(coordinate, record_type, text.strip())))

    result = []
    for raw_session_id, keyed_messages in sorted(grouped.items()):
        seen: set[str] = set()
        messages = []
        for key, message in keyed_messages:
            if key in seen:
                continue
            seen.add(key)
            messages.append(message)
        if messages:
            result.append(_conversation("claude_code", raw_session_id, messages))
    return tuple(result), files_read


def _count_codex_conversations(root: Path, metadata_line_limit: int = 64) -> int:
    sessions: set[str] = set()
    child_sessions: set[str] = set()
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else ():
        try:
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line_number, line in enumerate(handle, 1):
                if line_number > metadata_line_limit:
                    break
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("payload")
                if row.get("type") != "session_meta" or not isinstance(payload, dict):
                    continue
                raw_session_id = str(payload.get("id") or payload.get("session_id") or "")
                if raw_session_id:
                    sessions.add(raw_session_id)
                    if payload.get("parent_thread_id"):
                        child_sessions.add(raw_session_id)
                break
    return len(sessions - child_sessions)


def _count_claude_conversations(root: Path, metadata_line_limit: int = 64) -> int:
    sessions: set[str] = set()
    for path in sorted(root.glob("*/*.jsonl")) if root.is_dir() else ():
        try:
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line_number, line in enumerate(handle, 1):
                if line_number > metadata_line_limit:
                    break
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                raw_session_id = str(row.get("sessionId") or "")
                if raw_session_id:
                    sessions.add(raw_session_id)
                    break
    return len(sessions)


def count_local_conversations(
    *,
    home: Path | None = None,
    codex_home: Path | None = None,
    sources: Sequence[str] = ("codex", "claude_code"),
    environ: Mapping[str, str] | None = None,
) -> LocalLibraryCounts:
    """Count conversations from metadata without reading their message bodies."""
    explicit_home = home is not None
    home = (home or Path.home()).expanduser()
    environ = environ or os.environ
    unknown = set(sources) - {"codex", "claude_code"}
    if unknown:
        raise ValueError(f"unsupported count-only sources: {sorted(unknown)}")
    counts = []
    if "codex" in sources:
        if codex_home is not None:
            resolved_codex_home = codex_home
        elif not explicit_home and environ.get("CODEX_HOME"):
            resolved_codex_home = Path(environ["CODEX_HOME"])
        else:
            resolved_codex_home = home / ".codex"
        count = _count_codex_conversations(resolved_codex_home / "sessions")
        counts.append(ConversationCount("codex", "ready" if count else "not_found_or_empty", count))
    if "claude_code" in sources:
        count = _count_claude_conversations(home / ".claude" / "projects")
        counts.append(ConversationCount("claude_code", "ready" if count else "not_found_or_empty", count))
    return LocalLibraryCounts(tuple(counts))


def _chatgpt_objects(value: object) -> Iterable[dict]:
    if isinstance(value, dict) and isinstance(value.get("mapping"), dict):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("mapping"), dict):
                yield item


def _chatgpt_from_value(value: object, file_token: str) -> list[Conversation]:
    result = []
    for position, item in enumerate(_chatgpt_objects(value), 1):
        raw_id = str(item.get("id") or item.get("conversation_id") or f"{file_token}:{position}")
        nodes = list(item["mapping"].values())
        nodes.sort(key=lambda node: (node.get("message", {}).get("create_time") or 0, str(node.get("id") or "")))
        messages = []
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
                if isinstance(part, str) and part.strip():
                    messages.append(Message(f"chatgpt:{file_token}:{position}:{node_position}:{part_position}", role, part.strip()))
        if messages:
            result.append(_conversation("chatgpt_desktop", raw_id, messages))
    return result


def _decode_small_json_container(path: Path, max_bytes: int = 64 * 1024 * 1024) -> object | None:
    if path.stat().st_size > max_bytes:
        return None
    data = path.read_bytes()
    attempts = [data]
    if data.startswith(b"\x1f\x8b"):
        try:
            attempts.append(gzip.decompress(data))
        except (OSError, EOFError):
            pass
    try:
        attempts.append(zlib.decompress(data))
    except zlib.error:
        pass
    for decoded in attempts:
        stripped = decoded.lstrip()
        if not stripped.startswith((b"{", b"[")):
            continue
        try:
            return json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return None


def chatgpt_roots(home: Path, environ: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    """Return only explicit application-owned roots; never scan the whole home."""
    environ = environ or os.environ
    roots = [
        home / "Library/Application Support/ChatGPT",
        home / "Library/Application Support/com.openai.chat",
        home / "Library/Group Containers/group.com.openai.chat",
        home / ".config/ChatGPT",
        home / ".config/com.openai.chat",
        home / "AppData/Roaming/ChatGPT",
        home / "AppData/Roaming/com.openai.chat",
        home / "AppData/Local/ChatGPT",
        home / "AppData/Local/com.openai.chat",
    ]
    for variable in ("APPDATA", "LOCALAPPDATA"):
        base = environ.get(variable)
        if base:
            roots.extend((Path(base) / "ChatGPT", Path(base) / "com.openai.chat"))
    unique = []
    seen = set()
    for root in roots:
        key = str(root)
        if root.is_dir() and key not in seen:
            seen.add(key)
            unique.append(root)
    return tuple(unique)


def read_chatgpt_desktop(home: Path, environ: Mapping[str, str] | None = None) -> tuple[tuple[Conversation, ...], int, int]:
    conversations = []
    files_read = 0
    unsupported = 0
    seen_paths: set[str] = set()
    for root in chatgpt_roots(home, environ):
        candidates = list(root.glob("conversations*.json")) + list(root.glob("conversations-v3-*/*.data"))
        for path in sorted(candidates):
            key = str(path.resolve())
            if key in seen_paths or not path.is_file() or path.is_symlink():
                continue
            seen_paths.add(key)
            files_read += 1
            try:
                value = _decode_small_json_container(path)
            except OSError:
                value = None
            if value is None:
                unsupported += 1
                continue
            parsed = _chatgpt_from_value(value, _path_token(path))
            if not parsed:
                unsupported += 1
            conversations.extend(parsed)
    return tuple(conversations), files_read, unsupported


def scan_local_library(
    *,
    home: Path | None = None,
    codex_home: Path | None = None,
    sources: Sequence[str] = SOURCE_NAMES,
    environ: Mapping[str, str] | None = None,
) -> LocalLibrary:
    explicit_home = home is not None
    home = (home or Path.home()).expanduser()
    environ = environ or os.environ
    unknown = set(sources) - set(SOURCE_NAMES)
    if unknown:
        raise ValueError(f"unknown sources: {sorted(unknown)}")
    conversations: list[Conversation] = []
    statuses = []

    if "codex" in sources:
        if codex_home is not None:
            resolved_codex_home = codex_home
        elif not explicit_home and environ.get("CODEX_HOME"):
            resolved_codex_home = Path(environ["CODEX_HOME"])
        else:
            resolved_codex_home = home / ".codex"
        root = resolved_codex_home / "sessions"
        items, files_read = read_codex(root)
        conversations.extend(items)
        statuses.append(AdapterStatus("codex", "ready" if items else "not_found_or_empty", len(items), sum(len(item.messages) for item in items), files_read))
    if "claude_code" in sources:
        items, files_read = read_claude_code(home / ".claude" / "projects")
        conversations.extend(items)
        statuses.append(AdapterStatus("claude_code", "ready" if items else "not_found_or_empty", len(items), sum(len(item.messages) for item in items), files_read))
    if "chatgpt_desktop" in sources:
        items, files_read, unsupported = read_chatgpt_desktop(home, environ)
        conversations.extend(items)
        status = "ready" if items else "unsupported_local_format" if unsupported else "not_found_or_empty"
        statuses.append(AdapterStatus("chatgpt_desktop", status, len(items), sum(len(item.messages) for item in items), files_read, unsupported))

    return LocalLibrary(tuple(conversations), tuple(statuses))
