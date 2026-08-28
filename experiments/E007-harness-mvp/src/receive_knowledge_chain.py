#!/usr/bin/env python3
"""Receive and reconstruct the relation-free Gate 12A.2 knowledge chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path


RECORD_FIELDS = {
    "author_id", "chain_id", "revision_id", "previous_revision_id",
    "claim", "evidence_id", "active", "permission",
}


def reject(reason: str, payload_hash: str, receiver_label: str, count: int = 0) -> dict:
    return {
        "receiver_label": receiver_label,
        "receiver_hostname": platform.node(),
        "payload_sha256": payload_hash,
        "records_received": count,
        "decision": reason,
        "current_revision_id": None,
        "current_claim": None,
        "history_revision_ids": [],
    }


def reconstruct(payload_bytes: bytes, receiver_label: str) -> dict:
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return reject("invalid_json", payload_hash, receiver_label)
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        return reject("invalid_records", payload_hash, receiver_label)
    if any(not isinstance(item, dict) or set(item) != RECORD_FIELDS for item in records):
        return reject("invalid_record_contract", payload_hash, receiver_label, len(records))
    if any(item["permission"] != "share_chain" or not isinstance(item["active"], bool) for item in records):
        return reject("blocked_or_invalid", payload_hash, receiver_label, len(records))

    ids = [item["revision_id"] for item in records]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        return reject("invalid_revision_ids", payload_hash, receiver_label, len(records))
    authors = {item["author_id"] for item in records}
    chains = {item["chain_id"] for item in records}
    if len(authors) != 1 or len(chains) != 1:
        return reject("mixed_chain", payload_hash, receiver_label, len(records))

    by_id = {item["revision_id"]: item for item in records}
    roots = [item for item in records if item["previous_revision_id"] is None]
    if len(roots) != 1:
        return reject("invalid_root", payload_hash, receiver_label, len(records))
    if any(item["previous_revision_id"] is not None and item["previous_revision_id"] not in by_id for item in records):
        return reject("incomplete", payload_hash, receiver_label, len(records))

    parent_ids = {item["previous_revision_id"] for item in records if item["previous_revision_id"] is not None}
    heads = [item for item in records if item["revision_id"] not in parent_ids]
    if len(heads) != 1:
        return reject("forked", payload_hash, receiver_label, len(records))

    head = heads[0]
    reverse_history = []
    seen = {head["revision_id"]}
    parent_id = head["previous_revision_id"]
    while parent_id is not None:
        if parent_id in seen:
            return reject("cycle", payload_hash, receiver_label, len(records))
        seen.add(parent_id)
        reverse_history.append(parent_id)
        parent_id = by_id[parent_id]["previous_revision_id"]
    if len(seen) != len(records):
        return reject("disconnected", payload_hash, receiver_label, len(records))
    history = list(reversed(reverse_history))
    decision = "ready" if head["active"] else "withdrawn"
    return {
        "receiver_label": receiver_label,
        "receiver_hostname": platform.node(),
        "payload_sha256": payload_hash,
        "records_received": len(records),
        "decision": decision,
        "author_id": head["author_id"],
        "chain_id": head["chain_id"],
        "current_revision_id": head["revision_id"] if head["active"] else None,
        "current_claim": head["claim"] if head["active"] else None,
        "history_revision_ids": history + ([] if head["active"] else [head["revision_id"]]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument("--receiver-label", required=True)
    args = parser.parse_args()
    receipt = reconstruct(args.payload.read_bytes(), args.receiver_label)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
