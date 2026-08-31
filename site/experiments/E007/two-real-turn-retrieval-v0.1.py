#!/usr/bin/env python3
"""Run a two-turn local retrieval smoke without emitting conversation text."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import math
import os
import re
from pathlib import Path


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
MAX_SOURCE_WINDOW = 32 * 1024 * 1024
MAX_METADATA_PREFIX = 2 * 1024 * 1024


def load_adapter(path: Path):
    loader = SourceFileLoader("pocket_i_adapters", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the local adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def words(text: str) -> list[str]:
    return [item.casefold() for item in TOKEN.findall(text)]


def bm25_scores(documents: list[str], query: str, k1: float = 1.5, b: float = 0.75) -> list[float]:
    tokenized = [words(document) for document in documents]
    lengths = [len(document) for document in tokenized]
    average = sum(lengths) / len(lengths) if lengths else 1.0
    frequencies = [collections.Counter(document) for document in tokenized]
    document_frequency = collections.Counter()
    for frequency in frequencies:
        document_frequency.update(frequency.keys())
    count = len(documents)
    scores = []
    for length, frequency in zip(lengths, frequencies):
        score = 0.0
        for term, query_frequency in collections.Counter(words(query)).items():
            occurrences = frequency.get(term, 0)
            if not occurrences:
                continue
            present = document_frequency[term]
            inverse = math.log(1 + (count - present + 0.5) / (present + 0.5))
            denominator = occurrences + k1 * (1 - b + b * length / average)
            score += query_frequency * inverse * occurrences * (k1 + 1) / denominator
        scores.append(score)
    return scores


def cosine(left, right) -> float:
    numerator = float(left @ right)
    denominator = math.sqrt(float(left @ left)) * math.sqrt(float(right @ right))
    return numerator / denominator if denominator else 0.0


def last_turn(messages: list[dict]) -> tuple[int, int]:
    for user_index in range(len(messages) - 2, -1, -1):
        if messages[user_index]["role"] != "user":
            continue
        for assistant_index in range(user_index + 1, len(messages)):
            if messages[assistant_index]["role"] == "assistant":
                return user_index, assistant_index
    raise RuntimeError("No user → assistant turn exists in the twenty-message sample")


def codex_metadata(path: Path) -> tuple[str, bool] | None:
    identifier = None
    child = False
    consumed = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            consumed += len(line.encode("utf-8", errors="replace"))
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                row = None
            if isinstance(row, dict):
                payload = row.get("payload")
                if row.get("type") == "session_meta" and isinstance(payload, dict):
                    identifier = str(payload.get("id") or payload.get("session_id") or path.stem)
                    child = child or bool(payload.get("parent_thread_id"))
            if consumed >= MAX_METADATA_PREFIX:
                break
    return (identifier, child) if identifier else None


def tail_text(path: Path, maximum_bytes: int = MAX_SOURCE_WINDOW) -> str:
    with path.open("rb") as handle:
        size = handle.seek(0, os.SEEK_END)
        start = max(0, size - maximum_bytes)
        handle.seek(start)
        data = handle.read(maximum_bytes)
    if start:
        newline = data.find(b"\n")
        data = data[newline + 1:] if newline >= 0 else b""
    return data.decode("utf-8", errors="replace")


def one_codex_sample(root: Path, limit: int = 20) -> tuple[list[dict], int]:
    paths = sorted(root.rglob("*.jsonl"), key=lambda path: (-path.stat().st_mtime_ns, str(path)))
    inspected = 0
    selected = None
    identifier = None
    for path in paths:
        inspected += 1
        metadata = codex_metadata(path)
        if metadata and not metadata[1]:
            identifier, selected = metadata[0], path
            break
    if selected is None or identifier is None:
        raise RuntimeError("No main Codex session found")
    messages = []
    seen = set()
    for line_number, line in enumerate(tail_text(selected).splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = row.get("payload")
        if row.get("type") != "event_msg" or not isinstance(payload, dict):
            continue
        role = {"user_message": "user", "agent_message": "assistant"}.get(payload.get("type"))
        text = payload.get("message")
        if role is None or not isinstance(text, str) or not text.strip():
            continue
        fingerprint = hashlib.sha256(json.dumps([row.get("timestamp"), payload.get("type"), payload.get("phase"), text], ensure_ascii=False).encode()).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        messages.append({"source":"codex","role":role,"text":text.strip(),"coordinate":f"C{line_number:06d}"})
    return messages[-limit:], inspected


def one_claude_sample(adapter, home: Path, limit: int = 20) -> list[dict]:
    root = home / ".claude" / "projects"
    paths = list(root.glob("*/*.jsonl")) if root.is_dir() else []
    if not paths:
        raise RuntimeError("No Claude Code main session found")
    path = max(paths, key=lambda item: (item.stat().st_mtime_ns, str(item)))
    messages = []
    seen = set()
    for line_number, line in enumerate(tail_text(path).splitlines(), 1):
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
        for block_number, text in enumerate(adapter.text_blocks(message.get("content")), 1):
            key = str(row.get("uuid") or message.get("id") or hashlib.sha256(f"{line_number}:{block_number}:{text}".encode()).hexdigest()) + f":{block_number}"
            if key in seen:
                continue
            seen.add(key)
            messages.append({"source":"claude_code","role":record_type,"text":text.strip(),"coordinate":f"D{line_number:06d}:{block_number}"})
    if not messages:
        raise RuntimeError("The newest Claude Code file has no visible messages")
    return messages[-limit:]


def main() -> None:
    import fastembed
    import numpy as np
    from fastembed import TextEmbedding

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    if fastembed.__version__ != "0.8.0":
        raise RuntimeError(f"Expected fastembed 0.8.0, got {fastembed.__version__}")
    adapter = load_adapter(args.adapter)
    home = Path.home()
    claude = one_claude_sample(adapter, home)
    codex, metadata_files = one_codex_sample(Path(os.environ.get("CODEX_HOME", home / ".codex")) / "sessions")
    all_messages = claude + codex
    turns = []
    query_positions = set()
    for source, messages in (("claude_code", claude), ("codex", codex)):
        user_index, assistant_index = last_turn(messages)
        absolute_user = all_messages.index(messages[user_index])
        absolute_assistant = all_messages.index(messages[assistant_index])
        query_positions.add(absolute_user)
        turns.append({"source":source,"query":messages[user_index]["text"],"gold_index":absolute_assistant,"gold_coordinate":messages[assistant_index]["coordinate"]})
    candidates = [(index, message) for index, message in enumerate(all_messages) if index not in query_positions]
    texts = [message["text"] for _, message in candidates]
    embedder = TextEmbedding(model_name=MODEL, cache_dir=str(args.cache_dir), threads=2)
    document_vectors = np.asarray(list(embedder.embed(texts, batch_size=16)), dtype=np.float32)
    query_vectors = list(embedder.embed([turn["query"] for turn in turns], batch_size=2))
    rows = []
    for turn, query_vector in zip(turns, query_vectors):
        lexical_scores = bm25_scores(texts, turn["query"])
        dense_scores = [cosine(query_vector, vector) for vector in document_vectors]
        lexical = sorted(range(len(candidates)), key=lambda index: (-lexical_scores[index], candidates[index][1]["coordinate"]))[:5]
        dense = sorted(range(len(candidates)), key=lambda index: (-dense_scores[index], candidates[index][1]["coordinate"]))[:5]
        union = list(dict.fromkeys(lexical + dense))
        gold_candidate = next(index for index, (original, _) in enumerate(candidates) if original == turn["gold_index"])
        rows.append({
            "source": turn["source"],
            "gold_coordinate": turn["gold_coordinate"],
            "lexical_rank": lexical.index(gold_candidate) + 1 if gold_candidate in lexical else None,
            "dense_rank": dense.index(gold_candidate) + 1 if gold_candidate in dense else None,
            "candidate_union": [candidates[index][1]["coordinate"] for index in union],
            "candidate_count": len(union),
            "gold_found": gold_candidate in union,
        })
    passed = sum(row["gold_found"] for row in rows) == 2
    result = {
        "schema_version":"0.1-private-no-text",
        "experiment":"E007",
        "gate":"16G.4",
        "status":"completed_passed" if passed else "completed_failed",
        "summary":{"source_file_windows_read":2,"maximum_bytes_per_source_window":MAX_SOURCE_WINDOW,"codex_metadata_files_inspected":metadata_files,"visible_messages_indexed":len(all_messages),"turns":2,"gold_found":sum(row["gold_found"] for row in rows)},
        "rows":rows,
        "claim_boundary":"Two-example exact historical-turn plumbing smoke; no paraphrase or empty-answer claim."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor,"w",encoding="utf-8") as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write("\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
