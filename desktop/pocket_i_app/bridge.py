"""Small private bridge between the desktop window and the Python core.

The bridge deliberately exposes counts only. Conversation text, paths and
identifiers never cross into the Electron renderer at this checkpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

from pocket_i_core.index_cache import build_cached_index
from pocket_i_core.library import count_local_conversations, scan_local_library


ENABLED_SOURCES = ("codex", "claude_code")
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBED_FINGERPRINT = "fastembed-0.8.0:paraphrase-multilingual-MiniLM-L12-v2"
EmbedBatch = Callable[[Sequence[str]], Sequence[Sequence[float]]]


def _counts_payload(library: object) -> dict[str, object]:
    return {
        "total_conversations": library.total_conversations,
        "adapters": [
            {
                "source": adapter.source,
                "state": adapter.status,
                "conversations": adapter.conversations,
            }
            for adapter in library.adapters
        ],
    }


def _state_path(data_dir: Path) -> Path:
    return data_dir / "memory-state.json"


def _read_state(data_dir: Path | None) -> dict[str, object]:
    if data_dir is None:
        return {"connected": False, "total_conversations": 0, "adapters": []}
    try:
        value = json.loads(_state_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"connected": False, "total_conversations": 0, "adapters": []}
    if (
        value.get("schema_version") != "desktop-memory-state-v0.1"
        or value.get("model_fingerprint") != EMBED_FINGERPRINT
        or not (data_dir / "index.sqlite3").is_file()
    ):
        return {"connected": False, "total_conversations": 0, "adapters": []}
    return {
        "connected": True,
        "total_conversations": int(value.get("total_conversations", 0)),
        "adapters": value.get("adapters", []),
    }


def _write_state(data_dir: Path, payload: dict[str, object]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        data_dir.chmod(0o700)
    except OSError:
        pass
    path = _state_path(data_dir)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)
    path.chmod(0o600)


def _production_embedder(data_dir: Path) -> EmbedBatch:
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        data_dir.chmod(0o700)
    except OSError:
        pass
    try:
        import fastembed
        from fastembed import TextEmbedding
    except ImportError as error:
        raise RuntimeError("The local memory search tool is missing.") from error
    if fastembed.__version__ != "0.8.0":
        raise RuntimeError(f"Expected fastembed 0.8.0, got {fastembed.__version__}.")
    model = TextEmbedding(model_name=EMBED_MODEL, cache_dir=str(data_dir / "models"), threads=2)

    def embed(texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return tuple(tuple(float(value) for value in vector) for vector in model.embed(list(texts), batch_size=32))

    return embed


def handle(
    action: str,
    *,
    data_dir: Path | None = None,
    home: Path | None = None,
    codex_home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    embed: EmbedBatch | None = None,
) -> dict[str, object]:
    if action == "health":
        return {
            "status": "ready",
            "version": "desktop-alpha-checkpoint-6d",
            "enabled_sources": list(ENABLED_SOURCES),
            "privacy": "no conversation text, paths or identifiers",
        }
    if action == "scan":
        library = count_local_conversations(
            home=home, codex_home=codex_home, sources=ENABLED_SOURCES, environ=environ
        )
        return {
            "schema_version": "desktop-library-counts-v0.1",
            "status": "ready",
            "version": "desktop-alpha-checkpoint-6d",
            **_counts_payload(library),
        }
    if action == "memory-status":
        return {"schema_version": "desktop-memory-status-v0.1", "status": "ready", **_read_state(data_dir)}
    if action == "connect":
        if data_dir is None:
            raise ValueError("data_dir is required for memory connection")
        library = scan_local_library(
            home=home, codex_home=codex_home, sources=ENABLED_SOURCES, environ=environ
        )
        selected_embed = embed
        if selected_embed is None:
            selected_embed = _production_embedder(data_dir) if library.conversations else lambda _texts: ()
        index, stats = build_cached_index(
            library.conversations,
            selected_embed,
            cache_path=data_dir / "index.sqlite3",
            model_fingerprint=EMBED_FINGERPRINT,
        )
        counts = count_local_conversations(
            home=home, codex_home=codex_home, sources=ENABLED_SOURCES, environ=environ
        )
        state = {
            "schema_version": "desktop-memory-state-v0.1",
            "total_conversations": counts.total_conversations,
            "adapters": _counts_payload(counts)["adapters"],
            "indexed_messages": index.messages,
            "model_fingerprint": EMBED_FINGERPRINT,
        }
        _write_state(data_dir, state)
        return {
            "schema_version": "desktop-memory-connect-v0.1",
            "status": "ready",
            "connected": True,
            **_counts_payload(counts),
            "indexed_messages": stats.messages,
            "reused_messages": stats.reused,
            "embedded_messages": stats.embedded,
        }
    raise ValueError("unsupported bridge action")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pocket i desktop private bridge")
    parser.add_argument("--action", choices=("health", "scan", "memory-status", "connect"), required=True)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        result = handle(args.action, data_dir=args.data_dir)
    except Exception as error:  # fail closed at the renderer boundary
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": type(error).__name__,
                    "message": "The local library could not be inspected.",
                }
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
