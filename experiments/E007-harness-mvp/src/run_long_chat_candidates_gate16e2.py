#!/usr/bin/env python3
"""Run Gate 16E.2 persisted recall-first retrieval in long chats."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import time
from pathlib import Path


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def words(text: str) -> list[str]:
    return [item.casefold() for item in TOKEN.findall(text)]


def cosine(left, right) -> float:
    numerator = float(left @ right)
    denominator = math.sqrt(float(left @ left)) * math.sqrt(float(right @ right))
    return numerator / denominator if denominator else 0.0


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


def ranking(values, ids: list[str]) -> list[str]:
    return [ids[index] for index in sorted(range(len(ids)), key=lambda item: (-values[item], ids[item]))]


def source_snapshot(chats: dict, cards: set[str]) -> str:
    serial = [
        [card_id, chats[card_id]["source_snapshot_hash"], [[m["id"], m["role"], m["text"]] for m in chats[card_id]["messages"]]]
        for card_id in sorted(cards)
    ]
    return hashlib.sha256(json.dumps(serial, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    import fastembed
    import numpy as np
    from fastembed import TextEmbedding

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--index-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    if fastembed.__version__ != "0.8.0":
        raise RuntimeError(f"Expected fastembed 0.8.0, got {fastembed.__version__}")
    payload = json.loads(args.payload.read_text())
    protocol = json.loads(args.protocol.read_text())
    chats = {f'{payload["node"]}-C{index:04d}': chat for index, chat in enumerate(payload["conversations"], 1)}
    cards = {query["card_id"] for query in protocol["queries"]}
    snapshot = source_snapshot(chats, cards)
    coordinates = []
    texts = []
    for card_id in sorted(cards):
        for message in chats[card_id]["messages"]:
            coordinates.append([card_id, message["id"]])
            texts.append(message["text"])
    embedder = TextEmbedding(model_name=MODEL, cache_dir=str(args.cache_dir), threads=8)
    built = False
    document_embeddings = 0
    index_started = time.monotonic()
    if args.index_cache.exists():
        cached = np.load(args.index_cache, allow_pickle=False)
        metadata = json.loads(str(cached["metadata"].item()))
        if metadata != {"model": MODEL, "source_snapshot": snapshot, "coordinates": coordinates}:
            raise RuntimeError("Persisted index does not match the source snapshot")
        vectors = cached["vectors"]
    else:
        vectors = np.asarray(list(embedder.embed(texts, batch_size=32)), dtype=np.float32)
        document_embeddings = len(texts)
        built = True
        args.index_cache.parent.mkdir(parents=True, exist_ok=True)
        metadata = json.dumps({"model": MODEL, "source_snapshot": snapshot, "coordinates": coordinates}, ensure_ascii=False, separators=(",", ":"))
        np.savez_compressed(args.index_cache, vectors=vectors, metadata=np.asarray(metadata))
    index_seconds = round(time.monotonic() - index_started, 3)

    by_card = {}
    for index, (card_id, message_id) in enumerate(coordinates):
        by_card.setdefault(card_id, []).append((index, message_id))
    query_started = time.monotonic()
    query_vectors = list(embedder.embed([query["question"] for query in protocol["queries"]], batch_size=12))
    rows = []
    for query, query_vector in zip(protocol["queries"], query_vectors):
        selected = by_card[query["card_id"]]
        ids = [message_id for _, message_id in selected]
        documents = [texts[index] for index, _ in selected]
        dense = ranking([cosine(query_vector, vectors[index]) for index, _ in selected], ids)
        lexical = ranking(bm25_scores(documents, query["question"]), ids)
        dense_top = dense[:5]
        lexical_top = lexical[:5]
        candidates = set(dense_top) | set(lexical_top)
        dense_rank = {message_id: position for position, message_id in enumerate(dense_top, 1)}
        lexical_rank = {message_id: position for position, message_id in enumerate(lexical_top, 1)}
        candidates = sorted(
            candidates,
            key=lambda message_id: (
                -(1 / (60 + dense_rank[message_id]) if message_id in dense_rank else 0)
                -(1 / (60 + lexical_rank[message_id]) if message_id in lexical_rank else 0),
                message_id,
            ),
        )
        gold = set(query["gold_message_ids"])
        row = {
            "id": query["id"], "card_id": query["card_id"], "question": query["question"],
            "gold_message_ids": query["gold_message_ids"], "dense_top_5": dense_top,
            "lexical_top_5": lexical_top, "candidate_message_ids": candidates,
            "candidate_count": len(candidates), "gold_found": bool(gold & set(candidates)),
            "source_coordinates_preserved": all(message_id in ids for message_id in candidates),
        }
        rows.append(row)
        print(json.dumps({"id":row["id"],"candidates":row["candidate_count"],"gold_found":row["gold_found"]}),flush=True)
    summary = {
        "questions": len(rows), "indexed_messages": len(texts), "source_snapshot": snapshot,
        "index_built_this_run": built, "document_embeddings_this_run": document_embeddings,
        "index_load_or_build_seconds": index_seconds, "query_seconds": round(time.monotonic()-query_started,3),
        "gold_found": sum(row["gold_found"] for row in rows),
        "maximum_candidate_count": max(row["candidate_count"] for row in rows),
        "source_coordinates_preserved": sum(row["source_coordinates_preserved"] for row in rows),
    }
    passed = summary["gold_found"] == 12 and summary["maximum_candidate_count"] <= 10 and summary["source_coordinates_preserved"] == 12
    result = {"schema_version":"0.1-private","experiment":"E007","gate":"16E.2","status":"completed_passed" if passed else "completed_failed","summary":summary,"rows":rows,"claim_boundary":protocol["claim_boundary"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")


if __name__ == "__main__":
    main()
