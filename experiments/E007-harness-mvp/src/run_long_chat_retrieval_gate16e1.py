#!/usr/bin/env python3
"""Run Gate 16E.1 dense, lexical and hybrid search inside long chats."""

from __future__ import annotations

import argparse
import collections
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
    query_terms = collections.Counter(words(query))
    scores = []
    for length, frequency in zip(lengths, frequencies):
        score = 0.0
        for term, query_frequency in query_terms.items():
            occurrences = frequency.get(term, 0)
            if not occurrences:
                continue
            present = document_frequency[term]
            inverse = math.log(1 + (count - present + 0.5) / (present + 0.5))
            denominator = occurrences + k1 * (1 - b + b * length / average)
            score += query_frequency * inverse * (occurrences * (k1 + 1) / denominator)
        scores.append(score)
    return scores


def ranks(values: list[float], ids: list[str]) -> list[dict]:
    return [
        {"message_id": ids[index], "score": round(values[index], 8)}
        for index in sorted(range(len(ids)), key=lambda item: (-values[item], ids[item]))
    ]


def rank_of(ranking: list[dict], gold: set[str]) -> int:
    return next(position for position, item in enumerate(ranking, 1) if item["message_id"] in gold)


def main() -> None:
    import fastembed
    from fastembed import TextEmbedding

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    if fastembed.__version__ != "0.8.0":
        raise RuntimeError(f"Expected fastembed 0.8.0, got {fastembed.__version__}")
    payload = json.loads(args.payload.read_text())
    protocol = json.loads(args.protocol.read_text())
    chats = {f'{payload["node"]}-C{index:04d}': chat for index, chat in enumerate(payload["conversations"], 1)}
    required_cards = {item["card_id"] for item in protocol["population"]["conversations"]}
    if not required_cards <= chats.keys():
        raise RuntimeError("A frozen long conversation is missing")

    texts = []
    coordinates = []
    for card_id in sorted(required_cards):
        for message in chats[card_id]["messages"]:
            texts.append(message["text"])
            coordinates.append((card_id, message["id"]))
    started = time.monotonic()
    embedder = TextEmbedding(model_name=MODEL, cache_dir=str(args.cache_dir), threads=8)
    document_vectors = list(embedder.embed(texts, batch_size=32))
    query_vectors = list(embedder.embed([query["question"] for query in protocol["queries"]], batch_size=12))
    by_card = {}
    for index, (card_id, message_id) in enumerate(coordinates):
        by_card.setdefault(card_id, []).append((index, message_id))

    rows = []
    for query, query_vector in zip(protocol["queries"], query_vectors):
        card_id = query["card_id"]
        selected = by_card[card_id]
        ids = [message_id for _, message_id in selected]
        documents = [texts[index] for index, _ in selected]
        dense_values = [cosine(query_vector, document_vectors[index]) for index, _ in selected]
        lexical_values = bm25_scores(documents, query["question"])
        dense = ranks(dense_values, ids)
        lexical = ranks(lexical_values, ids)
        dense_position = {item["message_id"]: position for position, item in enumerate(dense, 1)}
        lexical_position = {item["message_id"]: position for position, item in enumerate(lexical, 1)}
        fused_values = [1 / (60 + dense_position[mid]) + 1 / (60 + lexical_position[mid]) for mid in ids]
        hybrid = ranks(fused_values, ids)
        gold = set(query["gold_message_ids"])
        anchor = hybrid[0]["message_id"]
        anchor_index = ids.index(anchor)
        neighbours = ids[max(0, anchor_index - 1): min(len(ids), anchor_index + 2)]
        row = {
            "id": query["id"],
            "card_id": card_id,
            "question": query["question"],
            "gold_message_ids": query["gold_message_ids"],
            "dense_rank": rank_of(dense, gold),
            "lexical_rank": rank_of(lexical, gold),
            "hybrid_rank": rank_of(hybrid, gold),
            "dense_top_5": dense[:5],
            "lexical_top_5": lexical[:5],
            "hybrid_top_5": hybrid[:5],
            "returned_anchor": anchor,
            "returned_neighbour_ids": neighbours,
            "source_coordinates_preserved": all(mid in ids for mid in neighbours),
        }
        rows.append(row)
        print(json.dumps({"id": row["id"], "dense": row["dense_rank"], "lexical": row["lexical_rank"], "hybrid": row["hybrid_rank"]}), flush=True)

    def recall(method: str, limit: int) -> int:
        return sum(row[f"{method}_rank"] <= limit for row in rows)

    summary = {
        "questions": len(rows),
        "indexed_messages": len(texts),
        "dense_recall_at_1": recall("dense", 1),
        "dense_recall_at_3": recall("dense", 3),
        "lexical_recall_at_1": recall("lexical", 1),
        "lexical_recall_at_3": recall("lexical", 3),
        "hybrid_recall_at_1": recall("hybrid", 1),
        "hybrid_recall_at_3": recall("hybrid", 3),
        "source_coordinates_preserved": sum(row["source_coordinates_preserved"] for row in rows),
        "runtime_seconds": round(time.monotonic() - started, 3),
    }
    passed = (
        summary["hybrid_recall_at_3"] == 12
        and summary["hybrid_recall_at_1"] >= 10
        and summary["hybrid_recall_at_3"] >= summary["dense_recall_at_3"]
        and summary["source_coordinates_preserved"] == 12
    )
    result = {
        "schema_version": "0.1-private",
        "experiment": "E007",
        "gate": "16E.1",
        "status": "completed_passed" if passed else "completed_failed",
        "model": MODEL,
        "fastembed": fastembed.__version__,
        "summary": summary,
        "rows": rows,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
