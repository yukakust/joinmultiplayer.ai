#!/usr/bin/env python3
"""Run E007 Gate 16D.2 whole-conversation retrieval without publishing text."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def cosine(left, right) -> float:
    numerator = float(left @ right)
    denominator = math.sqrt(float(left @ left)) * math.sqrt(float(right @ right))
    return numerator / denominator if denominator else 0.0


def main() -> None:
    import fastembed
    from fastembed import TextEmbedding

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    if fastembed.__version__ != "0.8.0":
        raise RuntimeError(f"Expected fastembed 0.8.0, got {fastembed.__version__}")
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if payload.get("client_version") != "e007-topic-index-node-v0.2":
        raise RuntimeError("Expected the human-visible UI event connector")

    texts = []
    coordinates = []
    for conversation_index, conversation in enumerate(payload["conversations"], 1):
        card_id = f'{payload["node"]}-C{conversation_index:04d}'
        for message in conversation["messages"]:
            texts.append(message["text"])
            coordinates.append((card_id, message["id"]))

    started = time.monotonic()
    model = TextEmbedding(model_name=MODEL, cache_dir=str(args.cache_dir), threads=8)
    document_vectors = list(model.embed(texts, batch_size=32))
    query_vectors = list(model.embed([item["question"] for item in protocol["queries"]], batch_size=10))
    rows = []
    for query, query_vector in zip(protocol["queries"], query_vectors):
        best_by_chat = {}
        for (card_id, message_id), vector in zip(coordinates, document_vectors):
            score = cosine(query_vector, vector)
            current = best_by_chat.get(card_id)
            if current is None or score > current["score"]:
                best_by_chat[card_id] = {"card_id": card_id, "message_id": message_id, "score": score}
        ranking = sorted(best_by_chat.values(), key=lambda item: (-item["score"], item["card_id"]))
        rank = next(index for index, item in enumerate(ranking, 1) if item["card_id"] == query["gold_card_id"])
        rows.append({
            "id": query["id"], "question": query["question"],
            "gold_card_id": query["gold_card_id"], "gold_rank": rank,
            "top_5": [{**item, "score": round(item["score"], 6)} for item in ranking[:5]],
        })

    def hits(limit: int) -> int:
        return sum(item["gold_rank"] <= limit for item in rows)

    summary = {
        "recall_at_1": hits(1), "recall_at_3": hits(3),
        "recall_at_5": hits(5), "recall_at_10": hits(10),
        "mean_reciprocal_rank": round(sum(1 / item["gold_rank"] for item in rows) / len(rows), 6),
    }
    passed = summary["recall_at_5"] == 10 and summary["recall_at_3"] >= 9
    result = {
        "schema_version": "0.1", "experiment": "E007", "gate": "16D.2",
        "status": "PASS" if passed else "FAIL",
        "model": MODEL, "fastembed": fastembed.__version__,
        "conversations": len(payload["conversations"]), "indexed_messages": len(texts),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary, "queries": rows,
        "claim_boundary": "This measures chat retrieval only. Qwen did not read, judge or answer the retrieved conversations."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
