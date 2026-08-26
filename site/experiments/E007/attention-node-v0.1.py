#!/usr/bin/env python3
"""Tiny dependency-free client for E007 Checkpoint 3A."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


CLIENT_VERSION = "e007-attention-client-v0.1"
PROTOCOL_PATH = "/experiments/E007/attention-protocol-v0.1.json"
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


def exact_term_score(question: str, card: str) -> tuple[float, list[str]]:
    question_terms = terms(question)
    card_terms = terms(card)
    matched = sorted(question_terms & card_terms)
    if not question_terms or not card_terms:
        return 0.0, matched
    return len(matched) / math.sqrt(len(question_terms) * len(card_terms)), matched


def hashed_ngrams(value: str, dimensions: int = 2048) -> Counter[int]:
    compact = " ".join(WORD_RE.findall(normalize(value)))
    vector: Counter[int] = Counter()
    for size in (3, 4, 5):
        for index in range(max(0, len(compact) - size + 1)):
            gram = compact[index:index + size].encode("utf-8")
            bucket = int.from_bytes(hashlib.blake2b(gram, digest_size=8).digest(), "big") % dimensions
            vector[bucket] += 1
    return vector


def whole_text_vector_score(question: str, card: str) -> float:
    left = hashed_ngrams(question)
    right = hashed_ngrams(card)
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def request_json(server: str, path: str, body: dict | None = None) -> dict:
    url = server.rstrip("/") + path
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "joinmultiplayer-pocket-i-attention/0.1")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read()).get("error", str(error))
        except (json.JSONDecodeError, AttributeError):
            detail = str(error)
        raise SystemExit(f"Server rejected the request: {detail}") from error


def load_protocol(server: str) -> dict:
    return request_json(server, PROTOCOL_PATH)


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


def card_from_protocol(protocol: dict, card_id: str) -> dict:
    for card in protocol["cards"]:
        if card["id"] == card_id:
            return card
    raise SystemExit(f"Unknown locked card: {card_id}")


def join_and_score(server: str, join_token: str, card_id: str, device_label: str) -> dict:
    protocol = load_protocol(server)
    card = card_from_protocol(protocol, card_id)
    if card["device"] != device_label:
        raise SystemExit(f"Card {card_id} belongs to {card['device']}, not {device_label}")
    started = time.monotonic()
    joined = request_json(
        server,
        "/api/attention/join",
        {"join_token": join_token, "card_id": card_id, "device_label": device_label},
    )
    question = joined["question"]
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    if digest != joined["question_hash"]:
        raise SystemExit("Question changed in transit; no score was sent")
    vector_score = whole_text_vector_score(question, card["description"])
    term_score, matched = exact_term_score(question, card["description"])
    response = {
        "node_token": joined["node_token"],
        "question_hash": digest,
        "whole_text_vector": vector_score,
        "exact_terms": term_score,
        "matched_terms": matched,
        "latency_ms": (time.monotonic() - started) * 1_000,
        "client_version": CLIENT_VERSION,
    }
    request_json(server, "/api/attention/respond", response)
    visible = {
        "node_id": joined["node_id"],
        "card_id": card_id,
        "device": device_label,
        "question_hash": digest,
        "whole_text_vector": round(vector_score, 6),
        "exact_terms": round(term_score, 6),
        "matched_terms": matched,
    }
    print(json.dumps(visible, ensure_ascii=False, indent=2))
    return visible


def main() -> None:
    parser = argparse.ArgumentParser(description="E007 physical attention smoke client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a private four-node attention room")
    create.add_argument("--server", default="https://joinmultiplayer.ai")
    create.add_argument("--question", required=True)
    create.add_argument("--state", type=Path, required=True)

    join = subparsers.add_parser("join", help="join one locked card and return its scores")
    join.add_argument("--server", default="https://joinmultiplayer.ai")
    join.add_argument("--join-token", required=True)
    join.add_argument("--card", required=True)
    join.add_argument("--device", required=True)

    owner_join = subparsers.add_parser("owner-join", help="join using a private owner state file")
    owner_join.add_argument("--state", type=Path, required=True)
    owner_join.add_argument("--card", required=True)
    owner_join.add_argument("--device", required=True)

    status = subparsers.add_parser("status", help="show room state without printing secrets")
    status.add_argument("--state", type=Path, required=True)

    publish = subparsers.add_parser("publish", help="publish a complete owner-reviewed room")
    publish.add_argument("--state", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "create":
        room = request_json(
            args.server,
            "/api/attention/rooms",
            {"question": args.question, "author_mode": "pseudonym", "pseudonym": "Morrow", "consent": True},
        )
        save_private(args.state, {"server": args.server, **room})
        print(json.dumps({"room_id": room["room_id"], "question_hash": room["question_hash"], "state": str(args.state)}, indent=2))
    elif args.command == "join":
        join_and_score(args.server, args.join_token, args.card.upper(), args.device)
    elif args.command == "owner-join":
        state = load_private(args.state)
        join_and_score(state["server"], state["join_token"], args.card.upper(), args.device)
    elif args.command == "status":
        state = load_private(args.state)
        value = request_json(state["server"], "/api/attention/status", {"owner_token": state["owner_token"]})
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.command == "publish":
        state = load_private(args.state)
        value = request_json(state["server"], "/api/attention/publish", {"owner_token": state["owner_token"], "consent": True})
        print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
