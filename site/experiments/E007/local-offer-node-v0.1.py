#!/usr/bin/env python3
"""Physical local-memory search client for E007 Checkpoint 3B."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import secrets
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


CLIENT_VERSION = "e007-local-offer-client-v0.1"
PROTOCOL_PATH = "/experiments/E007/local-offer-protocol-v0.1.json"
MEMORY_PATH = "/experiments/E007/local-memory-v0.1.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "faf4aa4225822f3bc6376869cb1164e8e3feedd0"
LANES = ("exact_terms", "chargram_vector", "multilingual_neural")
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "i",
    "in", "is", "it", "my", "of", "on", "or", "the", "this", "to", "was", "with",
    "а", "без", "бы", "в", "во", "для", "до", "и", "из", "или", "как", "к", "мне",
    "мой", "мы", "на", "не", "но", "о", "по", "с", "со", "у", "что", "это", "я",
}


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).lower().replace("ё", "е")


def terms(value: str) -> set[str]:
    return {word for word in WORD_RE.findall(normalize(value)) if len(word) > 1 and word not in STOP_WORDS}


def exact_term_score(query: str, passage: str) -> float:
    left = terms(query)
    right = terms(passage)
    if not left or not right:
        return 0.0
    return len(left & right) / math.sqrt(len(left) * len(right))


def hashed_ngrams(value: str, dimensions: int = 2048) -> Counter[int]:
    compact = " ".join(WORD_RE.findall(normalize(value)))
    vector: Counter[int] = Counter()
    for size in (3, 4, 5):
        for index in range(max(0, len(compact) - size + 1)):
            gram = compact[index:index + size].encode("utf-8")
            bucket = int.from_bytes(hashlib.blake2b(gram, digest_size=8).digest(), "big") % dimensions
            vector[bucket] += 1
    return vector


def chargram_score(query: str, passage: str) -> float:
    left = hashed_ngrams(query)
    right = hashed_ngrams(passage)
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def cosine(left, right) -> float:
    dot = float(sum(float(a) * float(b) for a, b in zip(left, right)))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def select_threshold(scores: list[float], labels: list[bool]) -> tuple[float, float]:
    candidates = sorted(set(scores), reverse=True)
    if scores and max(scores) < 1.0:
        candidates.insert(0, min(1.0, max(scores) + 1e-6))
    candidates.append(-1.0)
    best_threshold = candidates[0]
    best_f1 = -1.0
    for threshold in candidates:
        predictions = [score >= threshold for score in scores]
        tp = sum(prediction and label for prediction, label in zip(predictions, labels))
        fp = sum(prediction and not label for prediction, label in zip(predictions, labels))
        fn = sum(not prediction and label for prediction, label in zip(predictions, labels))
        denominator = 2 * tp + fp + fn
        f1 = (2 * tp / denominator) if denominator else 1.0
        if f1 > best_f1 or (math.isclose(f1, best_f1) and threshold > best_threshold):
            best_threshold, best_f1 = threshold, f1
    return best_threshold, best_f1


def request_json(server: str, path: str, body: dict | None = None) -> dict:
    url = server.rstrip("/") + path
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "joinmultiplayer-pocket-i-local-offer/0.1")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read()).get("error", str(error))
        except (json.JSONDecodeError, AttributeError):
            detail = str(error)
        raise SystemExit(f"Server rejected the request: {detail}") from error


def save_private(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.chmod(path, 0o600)


def load_private(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def neural_score_table(texts: list[str], cache_dir: Path) -> dict[str, object]:
    try:
        from fastembed import TextEmbedding
    except ImportError as error:
        raise SystemExit("fastembed==0.8.0 is required for the locked neural lane") from error
    model = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(cache_dir), threads=2)
    unique = list(dict.fromkeys(texts))
    vectors = list(model.embed(unique, batch_size=16))
    return dict(zip(unique, vectors))


def build_lane_scores(memory: dict, questions: list[dict], documents: list[dict], cache_dir: Path):
    calibration = memory["calibration_pairs"]
    neural_texts = []
    for pair in calibration:
        neural_texts.extend((pair["query"], pair["passage"]))
    for question in questions:
        neural_texts.append(question["question"])
    for document in documents:
        neural_texts.append(document["text"])
    neural = neural_score_table(neural_texts, cache_dir)

    score_functions = {
        "exact_terms": exact_term_score,
        "chargram_vector": chargram_score,
        "multilingual_neural": lambda query, passage: cosine(neural[query], neural[passage]),
    }
    lane_config = {}
    for lane, scorer in score_functions.items():
        calibration_scores = [scorer(pair["query"], pair["passage"]) for pair in calibration]
        labels = [bool(pair["relevant"]) for pair in calibration]
        threshold, f1 = select_threshold(calibration_scores, labels)
        lane_config[lane] = {"threshold": threshold, "calibration_f1": f1}
    return score_functions, lane_config


def join_and_search(
    server: str,
    join_token: str,
    card_id: str,
    device_label: str,
    cache_dir: Path,
) -> dict:
    protocol = request_json(server, PROTOCOL_PATH)
    memory = request_json(server, MEMORY_PATH)
    documents = [dict(document) for document in memory["libraries"].get(card_id, [])]
    if len(documents) != 6:
        raise SystemExit(f"Locked local library for {card_id} is unavailable")

    local_canary = secrets.token_urlsafe(24)
    canary_hash = hashlib.sha256(local_canary.encode("utf-8")).hexdigest()
    for document in documents:
        document["text"] = document["text"].replace("{{SYNTHETIC_PRIVATE_CANARY}}", local_canary)

    started = time.monotonic()
    joined = request_json(
        server,
        "/api/local-offer/join",
        {"join_token": join_token, "card_id": card_id, "device_label": device_label},
    )
    protocol_questions = {item["id"]: item["question"] for item in protocol["questions"]}
    for question in joined["questions"]:
        expected = protocol_questions.get(question["id"])
        digest = hashlib.sha256(question["question"].encode("utf-8")).hexdigest()
        if expected != question["question"] or digest != question["question_hash"]:
            raise SystemExit("Question changed in transit; no local result was sent")

    score_functions, lane_config = build_lane_scores(memory, joined["questions"], documents, cache_dir)
    results = []
    for question in joined["questions"]:
        for lane in LANES:
            scorer = score_functions[lane]
            ranked = sorted(
                ((scorer(question["question"], document["text"]), document) for document in documents),
                key=lambda item: (-item[0], item[1]["id"]),
            )
            score, selected = ranked[0]
            threshold = lane_config[lane]["threshold"]
            capsule = None
            selected_canary_hash = ""
            if score < threshold:
                status = "empty"
            elif selected["permission"] == "blocked":
                status = "blocked"
                selected_canary_hash = canary_hash
            else:
                status = "found"
                stored = selected["capsule"]
                capsule = {
                    "claim": stored["claim"],
                    "evidence": selected["text"],
                    "source": stored["source"],
                    "source_lineage": selected["lineage"],
                    "conditions": stored["conditions"],
                    "limitations": stored["limitations"],
                    "permission": "share_this_capsule",
                }
            results.append(
                {
                    "question_id": question["id"],
                    "question_hash": question["question_hash"],
                    "lane": lane,
                    "status": status,
                    "score": score,
                    "source_id": selected["id"],
                    "capsule": capsule,
                    "canary_hash": selected_canary_hash,
                }
            )

    payload = {
        "node_token": joined["node_token"],
        "client_version": CLIENT_VERSION,
        "runtime": f"{platform.system()}-{platform.machine()}-python{platform.python_version()}",
        "memory_revision": memory["revision"],
        "model": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "lane_config": lane_config,
        "results": results,
    }
    serialized = json.dumps(payload, ensure_ascii=False)
    if local_canary in serialized:
        raise SystemExit("Privacy invariant failed: synthetic private canary entered outbound payload")
    request_json(server, "/api/local-offer/contribute", payload)
    summary = {
        "node_id": joined["node_id"],
        "card_id": card_id,
        "device": device_label,
        "seconds": round(time.monotonic() - started, 3),
        "thresholds": {lane: round(config["threshold"], 6) for lane, config in lane_config.items()},
        "states": {
            lane: Counter(item["status"] for item in results if item["lane"] == lane)
            for lane in LANES
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="E007 physical local knowledge offer client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--server", default="https://joinmultiplayer.ai")
    create.add_argument("--state", type=Path, required=True)

    join = subparsers.add_parser("join")
    join.add_argument("--server", default="https://joinmultiplayer.ai")
    join.add_argument("--join-token", required=True)
    join.add_argument("--card", required=True)
    join.add_argument("--device", required=True)
    join.add_argument("--cache-dir", type=Path, required=True)

    owner_join = subparsers.add_parser("owner-join")
    owner_join.add_argument("--state", type=Path, required=True)
    owner_join.add_argument("--card", required=True)
    owner_join.add_argument("--device", required=True)
    owner_join.add_argument("--cache-dir", type=Path, required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--state", type=Path, required=True)

    publish = subparsers.add_parser("publish")
    publish.add_argument("--state", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "create":
        room = request_json(
            args.server,
            "/api/local-offer/rooms",
            {"author_mode": "pseudonym", "pseudonym": "Morrow", "consent": True},
        )
        save_private(args.state, {"server": args.server, **room})
        print(json.dumps({"room_id": room["room_id"], "state": str(args.state)}, indent=2))
    elif args.command == "join":
        join_and_search(args.server, args.join_token, args.card.upper(), args.device, args.cache_dir)
    elif args.command == "owner-join":
        state = load_private(args.state)
        join_and_search(state["server"], state["join_token"], args.card.upper(), args.device, args.cache_dir)
    elif args.command == "status":
        state = load_private(args.state)
        value = request_json(state["server"], "/api/local-offer/status", {"owner_token": state["owner_token"]})
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.command == "publish":
        state = load_private(args.state)
        value = request_json(state["server"], "/api/local-offer/publish", {"owner_token": state["owner_token"], "consent": True})
        print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

