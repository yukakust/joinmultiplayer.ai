"""Private SQLite cache for local message embeddings."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .pipeline import Conversation
from .retrieval import EmbedBatch, HybridChatIndex


SCHEMA_VERSION = "desktop-index-cache-v0.1"
ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class CacheStats:
    messages: int
    reused: int
    embedded: int
    deleted: int
    rebuilt_for_model_change: bool

    def public_summary(self) -> dict[str, object]:
        return {
            "messages": self.messages,
            "reused": self.reused,
            "embedded": self.embedded,
            "deleted": self.deleted,
            "rebuilt_for_model_change": self.rebuilt_for_model_change,
            "privacy": "counts only; no text, IDs, paths or vectors",
        }


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _message_rows(conversations: Sequence[Conversation]) -> list[tuple[str, str, str, str]]:
    rows = []
    for conversation in conversations:
        for message in conversation.messages:
            cache_key = _digest(f"{conversation.conversation_id}\0{message.coordinate}")
            rows.append((cache_key, conversation.conversation_id, _digest(message.text), message.text))
    return rows


def _pack(vector: Sequence[float]) -> bytes:
    if not vector:
        raise ValueError("embedding vectors must not be empty")
    return struct.pack(f"<{len(vector)}f", *(float(item) for item in vector))


def _unpack(blob: bytes, dimension: int) -> tuple[float, ...]:
    if dimension < 1 or len(blob) != dimension * 4:
        raise ValueError("cached vector has an invalid dimension")
    return struct.unpack(f"<{dimension}f", blob)


def _open_private(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    connection = sqlite3.connect(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    connection.execute("pragma journal_mode=delete")
    connection.execute("pragma secure_delete=on")
    connection.execute("pragma temp_store=memory")
    connection.executescript(
        """
        create table if not exists metadata (
            key text primary key,
            value text not null
        );
        create table if not exists vectors (
            cache_key text primary key,
            conversation_key text not null,
            content_hash text not null,
            dimension integer not null,
            vector blob not null
        );
        """
    )
    return connection


def build_cached_index(
    conversations: Sequence[Conversation],
    embed: EmbedBatch,
    *,
    cache_path: Path,
    model_fingerprint: str,
    batch_size: int = 128,
    on_progress: ProgressCallback | None = None,
) -> tuple[HybridChatIndex, CacheStats]:
    """Reuse unchanged message vectors and embed only new or changed messages."""
    if not model_fingerprint.strip():
        raise ValueError("model_fingerprint must not be empty")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    rows = _message_rows(conversations)
    connection = _open_private(cache_path)
    rebuilt = False
    try:
        metadata = dict(connection.execute("select key, value from metadata"))
        expected = {"schema_version": SCHEMA_VERSION, "model_fingerprint": model_fingerprint}
        if metadata and metadata != expected:
            connection.execute("delete from vectors")
            connection.execute("delete from metadata")
            rebuilt = True
        connection.executemany("insert or replace into metadata(key, value) values (?, ?)", expected.items())

        cached = {
            key: (content_hash, int(dimension), vector)
            for key, content_hash, dimension, vector in connection.execute(
                "select cache_key, content_hash, dimension, vector from vectors"
            )
        }
        current_keys = {item[0] for item in rows}
        stale = set(cached) - current_keys
        if stale:
            connection.executemany("delete from vectors where cache_key = ?", ((item,) for item in stale))

        vectors: list[tuple[float, ...] | None] = [None] * len(rows)
        missing_indices = []
        for index, (cache_key, _conversation_key, content_hash, _text) in enumerate(rows):
            item = cached.get(cache_key)
            if item is None or item[0] != content_hash:
                missing_indices.append(index)
                continue
            vectors[index] = _unpack(item[2], item[1])

        completed = len(rows) - len(missing_indices)
        if on_progress is not None:
            on_progress(completed, len(rows))
        for start in range(0, len(missing_indices), batch_size):
            batch_indices = missing_indices[start : start + batch_size]
            batch_texts = [rows[index][3] for index in batch_indices]
            embedded_vectors = tuple(
                tuple(float(value) for value in vector) for vector in embed(batch_texts)
            )
            if len(embedded_vectors) != len(batch_indices):
                raise ValueError("embedder returned the wrong number of new vectors")
            for index, vector in zip(batch_indices, embedded_vectors):
                cache_key, conversation_key, content_hash, _text = rows[index]
                vectors[index] = vector
                connection.execute(
                    "insert or replace into vectors(cache_key, conversation_key, content_hash, dimension, vector) values (?, ?, ?, ?, ?)",
                    (cache_key, conversation_key, content_hash, len(vector), _pack(vector)),
                )
            # Each completed batch survives an app restart.
            connection.commit()
            completed += len(batch_indices)
            if on_progress is not None:
                on_progress(completed, len(rows))
        connection.commit()
    finally:
        connection.close()

    complete_vectors = tuple(item for item in vectors if item is not None)
    if len(complete_vectors) != len(rows):
        raise RuntimeError("index cache left a message without a vector")
    stats = CacheStats(
        messages=len(rows),
        reused=len(rows) - len(missing_indices),
        embedded=len(missing_indices),
        deleted=len(stale),
        rebuilt_for_model_change=rebuilt,
    )
    return HybridChatIndex(conversations, embed, document_vectors=complete_vectors), stats
