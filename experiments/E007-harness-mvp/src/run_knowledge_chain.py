#!/usr/bin/env python3
"""Gate 12A: reconstruct one pocket i's append-only knowledge history."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/knowledge-chain-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/knowledge-chain-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/knowledge-chain-result-v0.1.json"

REQUIRED_FIELDS = {
    "revision_id", "lineage_id", "author_id", "topic_id",
    "previous_revision_id", "relation", "claim", "evidence_id",
    "learned_at", "permission",
}
RELATIONS = {"learned", "confirms", "refines", "replaces", "retracts"}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def transport_roundtrip(case: dict) -> tuple[dict, bool, str]:
    sent = canonical_bytes(case)
    received = json.loads(sent.decode("utf-8"))
    received_bytes = canonical_bytes(received)
    return received, sent == received_bytes, hashlib.sha256(sent).hexdigest()


def has_cycle(revisions: dict[str, dict]) -> bool:
    for start in revisions:
        seen: set[str] = set()
        current: str | None = start
        while current is not None:
            if current in seen:
                return True
            seen.add(current)
            parent = revisions[current].get("previous_revision_id")
            current = parent if parent in revisions else None
    return False


def inspect_chain(revision_list: list[dict]) -> dict:
    if not revision_list:
        return {"decision": "incomplete", "current_revision_ids": [], "history_revision_ids": []}

    ids = [item.get("revision_id") for item in revision_list]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        return {"decision": "invalid_lineage", "current_revision_ids": [], "history_revision_ids": sorted(str(item) for item in ids)}
    revisions = {item["revision_id"]: item for item in revision_list}

    for item in revision_list:
        if set(item) != REQUIRED_FIELDS:
            return {"decision": "invalid_lineage", "current_revision_ids": [], "history_revision_ids": sorted(ids)}
        if item["relation"] not in RELATIONS or item["permission"] != "share_chain":
            return {"decision": "invalid_lineage", "current_revision_ids": [], "history_revision_ids": sorted(ids)}
        if item["relation"] == "retracts" and item["claim"]:
            return {"decision": "invalid_lineage", "current_revision_ids": [], "history_revision_ids": sorted(ids)}
        if item["relation"] != "retracts" and not item["claim"]:
            return {"decision": "invalid_lineage", "current_revision_ids": [], "history_revision_ids": sorted(ids)}

    missing_parent = any(
        item["previous_revision_id"] is not None
        and item["previous_revision_id"] not in revisions
        for item in revision_list
    )
    if missing_parent:
        return {"decision": "incomplete", "current_revision_ids": [], "history_revision_ids": sorted(ids)}

    for item in revision_list:
        parent_id = item["previous_revision_id"]
        if parent_id is None:
            continue
        parent = revisions[parent_id]
        identity = (item["lineage_id"], item["author_id"], item["topic_id"])
        parent_identity = (parent["lineage_id"], parent["author_id"], parent["topic_id"])
        if identity != parent_identity:
            return {"decision": "invalid_lineage", "current_revision_ids": [], "history_revision_ids": sorted(ids)}

    if has_cycle(revisions):
        return {"decision": "invalid_lineage", "current_revision_ids": [], "history_revision_ids": sorted(ids)}

    by_lineage: dict[str, list[dict]] = defaultdict(list)
    for item in revision_list:
        by_lineage[item["lineage_id"]].append(item)

    heads: list[dict] = []
    for lineage in by_lineage.values():
        child_ids = {item["previous_revision_id"] for item in lineage if item["previous_revision_id"] is not None}
        lineage_heads = [item for item in lineage if item["revision_id"] not in child_ids]
        if len(lineage_heads) != 1:
            head_ids = sorted(item["revision_id"] for item in lineage_heads)
            history_ids = sorted(item for item in ids if item not in head_ids)
            return {"decision": "forked", "current_revision_ids": head_ids, "history_revision_ids": history_ids}
        heads.extend(lineage_heads)

    active_heads = sorted(
        item["revision_id"] for item in heads if item["relation"] != "retracts"
    )
    if not active_heads:
        return {"decision": "retracted", "current_revision_ids": [], "history_revision_ids": sorted(ids)}
    history_ids = sorted(item for item in ids if item not in active_heads)
    decision = "ready_multi" if len(heads) > 1 else "ready"
    return {"decision": decision, "current_revision_ids": active_heads, "history_revision_ids": history_ids}


def display_chains(revision_list: list[dict]) -> list[dict]:
    """Return a stable parent-before-child view without changing validation."""
    by_lineage: dict[str, list[dict]] = defaultdict(list)
    for item in revision_list:
        by_lineage[str(item.get("lineage_id", "unknown"))].append(item)
    output = []
    for lineage_id, items in sorted(by_lineage.items()):
        ids = {item["revision_id"] for item in items}
        children: dict[str | None, list[dict]] = defaultdict(list)
        for item in items:
            parent = item.get("previous_revision_id")
            children[parent if parent in ids else None].append(item)
        ordered: list[dict] = []
        queue = sorted(children[None], key=lambda item: item["revision_id"])
        seen: set[str] = set()
        while queue:
            item = queue.pop(0)
            if item["revision_id"] in seen:
                continue
            seen.add(item["revision_id"])
            ordered.append(item)
            queue.extend(sorted(children[item["revision_id"]], key=lambda child: child["revision_id"]))
        ordered.extend(sorted((item for item in items if item["revision_id"] not in seen), key=lambda item: item["revision_id"]))
        output.append({"lineage_id": lineage_id, "author_id": items[0]["author_id"], "revisions": ordered})
    return output


def run() -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_run" or world["status"] != "frozen_before_run":
        raise RuntimeError("Gate 12A inputs are not frozen")
    if [item["id"] for item in world["cases"]] != protocol["frozen_case_ids"]:
        raise RuntimeError("Frozen case ids do not match the locked protocol")

    records = []
    for original in world["cases"]:
        received, exact, payload_hash = transport_roundtrip(original)
        actual = inspect_chain(received["revisions"])
        expected = original["expected"]
        correct = actual == expected
        current_claims = [
            {"revision_id": item["revision_id"], "claim": item["claim"], "evidence_id": item["evidence_id"]}
            for item in received["revisions"]
            if item["revision_id"] in actual["current_revision_ids"]
        ]
        records.append({
            "id": original["id"],
            "name": original["name"],
            "expected": expected,
            "actual": actual,
            "correct": correct,
            "transport_exact": exact,
            "payload_sha256": payload_hash,
            "current_claims": current_claims,
            "revisions": received["revisions"],
            "display_chains": display_chains(received["revisions"]),
        })

    summary = {
        "case_decisions_correct": sum(item["correct"] for item in records),
        "total_cases": len(records),
        "transport_roundtrips_exact": sum(item["transport_exact"] for item in records),
        "wrong_current_heads_selected": sum(
            item["actual"]["current_revision_ids"] != item["expected"]["current_revision_ids"]
            for item in records
        ),
        "history_revisions_lost": sum(
            len(set(item["expected"]["history_revision_ids"]) - set(item["actual"]["history_revision_ids"]))
            for item in records
        ),
    }
    passed = summary == {
        "case_decisions_correct": 10,
        "total_cases": 10,
        "transport_roundtrips_exact": 10,
        "wrong_current_heads_selected": 0,
        "history_revisions_lost": 0,
    }
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "12A",
        "status": "synthetic_development_run_complete",
        "protocol": "/experiments/E007/knowledge-chain-protocol-v0.1.json",
        "world": "/experiments/E007/knowledge-chain-world-v0.1.json",
        "summary": summary,
        "passed_locked_gate": passed,
        "records": records,
        "decision": "The append-only chain contract is accepted for the harness development path if the owner confirms the visible timelines.",
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    result = run()
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"summary": result["summary"], "passed_locked_gate": result["passed_locked_gate"]}, indent=2))


if __name__ == "__main__":
    main()
