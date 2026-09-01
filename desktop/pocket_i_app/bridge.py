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


class MemoryRuntime:
    """Hold plaintext conversations and the live index in RAM after consent."""

    def __init__(
        self,
        *,
        data_dir: Path | None = None,
        home: Path | None = None,
        codex_home: Path | None = None,
        environ: Mapping[str, str] | None = None,
        embed: EmbedBatch | None = None,
        on_progress: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.home = home
        self.codex_home = codex_home
        self.environ = environ
        self.embed = embed
        self.on_progress = on_progress
        self.library = None
        self.index = None

    def dispatch(self, action: str, *, question: str | None = None) -> dict[str, object]:
        if action == "health":
            return {
                "status": "ready",
                "version": "desktop-alpha-checkpoint-7b",
                "enabled_sources": list(ENABLED_SOURCES),
                "privacy": "conversation text remains in the local memory process",
            }
        if action == "scan":
            library = count_local_conversations(
                home=self.home,
                codex_home=self.codex_home,
                sources=ENABLED_SOURCES,
                environ=self.environ,
            )
            return {
                "schema_version": "desktop-library-counts-v0.1",
                "status": "ready",
                "version": "desktop-alpha-checkpoint-7b",
                **_counts_payload(library),
            }
        if action == "memory-status":
            return {
                "schema_version": "desktop-memory-status-v0.1",
                "status": "ready",
                **_read_state(self.data_dir),
            }
        if action == "connect":
            return self.connect()
        if action == "route":
            return self.route(question)
        raise ValueError("unsupported bridge action")

    def connect(self) -> dict[str, object]:
        if self.data_dir is None:
            raise ValueError("data_dir is required for memory connection")
        self._progress({"phase": "reading"})
        self.library = scan_local_library(
            home=self.home,
            codex_home=self.codex_home,
            sources=ENABLED_SOURCES,
            environ=self.environ,
        )
        if self.embed is None:
            self.embed = _production_embedder(self.data_dir) if self.library.conversations else lambda _texts: ()
        total_messages = sum(len(item.messages) for item in self.library.conversations)
        self._progress({"phase": "indexing", "completed": 0, "total": total_messages})
        self.index, stats = build_cached_index(
            self.library.conversations,
            self.embed,
            cache_path=self.data_dir / "index.sqlite3",
            model_fingerprint=EMBED_FINGERPRINT,
            on_progress=lambda completed, total: self._progress(
                {"phase": "indexing", "completed": completed, "total": total}
            ),
        )
        counts = count_local_conversations(
            home=self.home,
            codex_home=self.codex_home,
            sources=ENABLED_SOURCES,
            environ=self.environ,
        )
        state = {
            "schema_version": "desktop-memory-state-v0.1",
            "total_conversations": counts.total_conversations,
            "adapters": _counts_payload(counts)["adapters"],
            "indexed_messages": self.index.messages,
            "model_fingerprint": EMBED_FINGERPRINT,
        }
        _write_state(self.data_dir, state)
        self._progress({"phase": "ready", "completed": stats.messages, "total": stats.messages})
        return {
            "schema_version": "desktop-memory-connect-v0.1",
            "status": "ready",
            "connected": True,
            **_counts_payload(counts),
            "indexed_messages": stats.messages,
            "reused_messages": stats.reused,
            "embedded_messages": stats.embedded,
        }

    def route(self, question: str | None) -> dict[str, object]:
        if self.data_dir is None:
            raise ValueError("data_dir is required for memory routing")
        if not _read_state(self.data_dir)["connected"]:
            raise ValueError("local memory is not connected")
        question = (question or "").strip()
        if not question or len(question) > 4000:
            raise ValueError("question must contain between 1 and 4000 characters")
        if self.index is None or self.library is None:
            self.connect()
        _route, hits = self.index.route_with_hits(question, top_k=5)
        by_id = {item.conversation_id: item for item in self.library.conversations}
        items = []
        for rank, hit in enumerate(hits, 1):
            conversation = by_id[hit.conversation_id]
            message = conversation.messages[hit.message_position]
            preview = " ".join(message.text.split())
            if len(preview) > 320:
                preview = preview[:317].rstrip() + "…"
            items.append(
                {
                    "rank": rank,
                    "source": conversation.source,
                    "role": message.role,
                    "messages": len(conversation.messages),
                    "preview": preview,
                }
            )
        return {
            "schema_version": "desktop-memory-route-v0.1",
            "status": "ready",
            "returned": len(items),
            "items": items,
            "privacy": "matched previews are returned only to the local owner window",
        }

    def _progress(self, payload: dict[str, object]) -> None:
        if self.on_progress is not None:
            self.on_progress(payload)


def handle(
    action: str,
    *,
    data_dir: Path | None = None,
    home: Path | None = None,
    codex_home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    embed: EmbedBatch | None = None,
    question: str | None = None,
) -> dict[str, object]:
    runtime = MemoryRuntime(
        data_dir=data_dir,
        home=home,
        codex_home=codex_home,
        environ=environ,
        embed=embed,
    )
    return runtime.dispatch(action, question=question)


def _serve(runtime: MemoryRuntime) -> int:
    """Serve small JSON-line requests while keeping the private library warm."""
    for raw_request in sys.stdin:
        response_id = None
        try:
            if len(raw_request) > 16384:
                raise ValueError("request is too large")
            request = json.loads(raw_request)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            response_id = request.get("id")
            action = request.get("action")
            payload = request.get("payload") or {}
            if not isinstance(response_id, int) or action not in {
                "health", "scan", "memory-status", "connect", "route"
            } or not isinstance(payload, dict):
                raise ValueError("invalid request")
            runtime.on_progress = lambda progress: print(
                json.dumps({"id": response_id, "event": "progress", "payload": progress}),
                flush=True,
            )
            result = runtime.dispatch(action, question=payload.get("question"))
            response = {"id": response_id, "ok": True, "result": result}
        except Exception:  # never expose local paths or private parser details
            response = {"id": response_id, "ok": False, "error": "Local memory failed."}
        print(json.dumps(response, ensure_ascii=False), flush=True)
        runtime.on_progress = None
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pocket i desktop private bridge")
    parser.add_argument(
        "--action",
        choices=("health", "scan", "memory-status", "connect", "route", "serve"),
        required=True,
    )
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args(argv)
    if args.action == "serve":
        return _serve(MemoryRuntime(data_dir=args.data_dir))
    try:
        request = None
        if args.action == "route":
            raw_request = sys.stdin.read(16385)
            if len(raw_request) > 16384:
                raise ValueError("request is too large")
            request = json.loads(raw_request or "{}")
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
        result = handle(
            args.action,
            data_dir=args.data_dir,
            question=request.get("question") if request is not None else None,
        )
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
