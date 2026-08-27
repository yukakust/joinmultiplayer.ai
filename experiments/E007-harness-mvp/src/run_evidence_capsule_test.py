#!/usr/bin/env python3
"""E007 Gate 3C.6B: validate and rerank frozen incoming evidence capsules."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import urllib.request
from pathlib import Path

from transformers import AutoTokenizer


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/evidence-capsule-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/evidence-capsules-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/evidence-capsule-result-v0.1.json"
MODEL_PATH = Path("/home/yuka/models/e007/mobile-reranker/qwen3-reranker-4b-q4_k_m.gguf")
TOKENIZER_PATH = Path("/home/yuka/models/e007/qwen3-reranker-4b-22e6836")

PREFIX = (
    '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. '
    'Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
)
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_packet(packet: dict, sources: list[dict], tokenizer) -> dict:
    same_id = [item for item in sources if item["source_id"] == packet["source"]["source_id"]]
    if not same_id:
        return {"decision": "source_missing"}
    source = next((item for item in same_id if item["source_version"] == packet["source"]["source_version"]), None)
    if source is None:
        return {"decision": "version_missing"}
    source_bytes = source["text"].encode("utf-8")
    if sha256(source_bytes) != packet["source"]["sha256"]:
        return {"decision": "source_hash_mismatch"}
    window = packet["evidence_window"]
    start, end = window["source_byte_start"], window["source_byte_end"]
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or end > len(source_bytes):
        return {"decision": "window_range_mismatch"}
    selected_window = source_bytes[start:end]
    declared_window = window["text"].encode("utf-8")
    if selected_window != declared_window:
        return {"decision": "window_range_mismatch"}
    if sha256(selected_window) != window["sha256"]:
        return {"decision": "window_hash_mismatch"}
    token_count = len(tokenizer.encode(window["text"], add_special_tokens=False))
    if token_count != window["token_count"]:
        return {"decision": "window_token_count_mismatch", "actual_token_count": token_count}
    if token_count > 500:
        return {"decision": "window_too_large", "actual_token_count": token_count}
    evidence = packet["candidate_evidence"]
    evidence_start, evidence_end = evidence["window_byte_start"], evidence["window_byte_end"]
    if not isinstance(evidence_start, int) or not isinstance(evidence_end, int) or evidence_start < 0 or evidence_end <= evidence_start or evidence_end > len(selected_window):
        return {"decision": "candidate_range_mismatch"}
    selected_evidence = selected_window[evidence_start:evidence_end]
    if selected_evidence != evidence["text"].encode("utf-8"):
        if sha256(selected_evidence) == evidence["sha256"]:
            return {"decision": "candidate_text_mismatch"}
        return {"decision": "candidate_range_mismatch"}
    if sha256(selected_evidence) != evidence["sha256"]:
        return {"decision": "candidate_hash_mismatch"}
    return {"decision": "valid", "actual_token_count": token_count}


def prompt(instruction: str, query: str, passage: str) -> str:
    body = f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {passage}"
    return PREFIX + body + SUFFIX


def score(server: str, instruction: str, query: str, passage: str) -> float:
    body = json.dumps({"content": prompt(instruction, query, passage), "embd_normalize": -1}).encode("utf-8")
    request = urllib.request.Request(server.rstrip("/") + "/embedding", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    rank = payload[0].get("embedding", []) if payload else []
    if rank and isinstance(rank[0], list):
        rank = rank[0]
    if len(rank) < 2 or not all(math.isfinite(float(value)) for value in rank[:2]):
        raise RuntimeError("llama-server did not return reranker yes/no scores")
    yes, no = float(rank[0]), float(rank[1])
    return yes / (yes + no)


def relevance_decision(value: float, thresholds: dict) -> str:
    if value >= thresholds["take_at_or_above"]:
        return "take"
    if value <= thresholds["drop_at_or_below"]:
        return "drop"
    return "not_sure"


def run(server: str) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6B inputs are not frozen")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH, local_files_only=True)
    mechanical_records = []
    valid_packets = []
    for packet in world["packets"]:
        check = verify_packet(packet, world["sources"], tokenizer)
        expected = packet["expected"]["mechanical"]
        mechanical_records.append({
            "id": packet["id"], "group": packet["group"], "expected": expected,
            **check, "correct": check["decision"] == expected,
        })
        if check["decision"] == "valid":
            valid_packets.append(packet)
    mechanical_summary = {
        "correct": sum(item["correct"] for item in mechanical_records), "total": len(mechanical_records),
        "intact_accepted": sum(item["group"] != "broken" and item["decision"] == "valid" for item in mechanical_records),
        "intact_total": sum(item["group"] != "broken" for item in mechanical_records),
        "broken_accepted": sum(item["group"] == "broken" and item["decision"] == "valid" for item in mechanical_records),
        "broken_total": sum(item["group"] == "broken" for item in mechanical_records),
    }
    instruction = protocol["relevance_gate"]["input"] + ". " + protocol["hypothesis"]["en"]
    # Use the frozen explicit relevance instruction, not the sender claim.
    instruction = "Given a user question and one evidence window, decide whether the window contains information that helps answer the question."
    thresholds = protocol["relevance_gate"]["thresholds"]
    relevance_records = []
    started = time.monotonic()
    for packet in valid_packets:
        value = score(server, instruction, packet["question"], packet["evidence_window"]["text"])
        verdict = relevance_decision(value, thresholds)
        relevance_records.append({
            "id": packet["id"], "group": packet["group"], "question": packet["question"],
            "claim_hidden_from_model": packet["claim"], "window": packet["evidence_window"]["text"],
            "candidate_evidence_hidden_from_model": packet["candidate_evidence"]["text"],
            "token_count": packet["evidence_window"]["token_count"], "evidence_position": packet["evidence_position"],
            "score": round(value, 8), "decision": verdict, "expected": packet["expected"]["relevance"],
        })
    useful = [item for item in relevance_records if item["group"] == "useful"]
    misleading = [item for item in relevance_records if item["group"] == "misleading"]
    relevance_summary = {
        "useful_taken": sum(item["decision"] == "take" for item in useful),
        "useful_not_sure": sum(item["decision"] == "not_sure" for item in useful),
        "useful_dropped": sum(item["decision"] == "drop" for item in useful),
        "useful_total": len(useful),
        "misleading_taken": sum(item["decision"] == "take" for item in misleading),
        "misleading_not_sure": sum(item["decision"] == "not_sure" for item in misleading),
        "misleading_dropped": sum(item["decision"] == "drop" for item in misleading),
        "misleading_total": len(misleading),
    }
    mechanical_passed = mechanical_summary == {
        "correct": 24, "total": 24, "intact_accepted": 16, "intact_total": 16,
        "broken_accepted": 0, "broken_total": 8,
    }
    relevance_passed = (
        relevance_summary["useful_dropped"] <= protocol["relevance_gate"]["success"]["useful_dropped_max"]
        and relevance_summary["useful_taken"] >= protocol["relevance_gate"]["success"]["useful_taken_min"]
        and relevance_summary["misleading_taken"] <= protocol["relevance_gate"]["success"]["misleading_taken_max"]
    )
    return {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "3C.6B",
        "status": "locked_development_run_complete",
        "protocol": "/experiments/E007/evidence-capsule-protocol-v0.1.json",
        "world": "/experiments/E007/evidence-capsules-v0.1.json",
        "protocol_sha256": sha256_file(PROTOCOL_PATH), "world_sha256": sha256_file(WORLD_PATH),
        "model": {"id": "Qwen/Qwen3-Reranker-4B", "quantization": "Q4_K_M", "file_sha256": sha256_file(MODEL_PATH)},
        "runtime_seconds": round(time.monotonic() - started, 3),
        "mechanical": {"summary": mechanical_summary, "passed_locked_gate": mechanical_passed, "records": mechanical_records},
        "relevance": {"summary": relevance_summary, "passed_locked_gate": relevance_passed, "records": relevance_records},
        "passed_locked_gate": mechanical_passed and relevance_passed,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:18086")
    args = parser.parse_args()
    result = run(args.server)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "passed": result["passed_locked_gate"],
        "mechanical": result["mechanical"]["summary"],
        "relevance": result["relevance"]["summary"],
    }, indent=2))


if __name__ == "__main__":
    main()
