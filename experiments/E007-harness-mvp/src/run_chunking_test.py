#!/usr/bin/env python3
"""E007 Gate 3C.6A.2: compare naive and structure-aware source cutting."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/chunking-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/chunking-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/chunking-result-v0.1.json"
MODEL_PATH = Path("/home/yuka/models/e007/mobile-reranker/qwen3-reranker-4b-q4_k_m.gguf")

PREFIX = (
    '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. '
    'Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
)
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_source(blocks: list[dict]) -> tuple[str, dict[str, tuple[int, int]]]:
    """Join frozen blocks and preserve exact UTF-8 byte ranges."""
    parts: list[str] = []
    ranges: dict[str, tuple[int, int]] = {}
    cursor = 0
    for index, block in enumerate(blocks):
        if index:
            separator = "\n\n"
            parts.append(separator)
            cursor += len(separator.encode("utf-8"))
        text = block["text"]
        start = cursor
        parts.append(text)
        cursor += len(text.encode("utf-8"))
        ranges[block["id"]] = (start, cursor)
    return "".join(parts), ranges


def covered_atoms(start: int, end: int, atom_ranges: dict[str, tuple[int, int]]) -> list[str]:
    return [atom for atom, (atom_start, atom_end) in atom_ranges.items() if start <= atom_start and atom_end <= end]


def fixed_word_chunks(source: str, atom_ranges: dict[str, tuple[int, int]], size: int = 45) -> list[dict]:
    encoded = source.encode("utf-8")
    # Match on text for word boundaries, then convert character offsets to bytes.
    words = list(re.finditer(r"\S+", source))
    chunks = []
    for number, first in enumerate(range(0, len(words), size), 1):
        selected = words[first:first + size]
        char_start, char_end = selected[0].start(), selected[-1].end()
        byte_start = len(source[:char_start].encode("utf-8"))
        byte_end = len(source[:char_end].encode("utf-8"))
        chunks.append({
            "id": f"F{number:02d}", "byte_start": byte_start, "byte_end": byte_end,
            "text": encoded[byte_start:byte_end].decode("utf-8"),
            "atoms": covered_atoms(byte_start, byte_end, atom_ranges),
        })
    return chunks


def structure_windows(source: str, blocks: list[dict], atom_ranges: dict[str, tuple[int, int]]) -> list[dict]:
    encoded = source.encode("utf-8")
    windows = []
    for index, block in enumerate(blocks):
        first = max(0, index - 1)
        last = min(len(blocks) - 1, index + 1)
        start = atom_ranges[blocks[first]["id"]][0]
        end = atom_ranges[blocks[last]["id"]][1]
        windows.append({
            "id": f"S{index + 1:02d}", "focus_atom": block["id"],
            "byte_start": start, "byte_end": end,
            "text": encoded[start:end].decode("utf-8"),
            "atoms": covered_atoms(start, end, atom_ranges),
        })
    return windows


def prompt(instruction: str, query: str, passage: str) -> str:
    body = f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {passage}"
    return PREFIX + body + SUFFIX


def score(server: str, instruction: str, query: str, passage: str) -> float:
    body = json.dumps({"content": prompt(instruction, query, passage), "embd_normalize": -1}).encode("utf-8")
    request = urllib.request.Request(
        server.rstrip("/") + "/embedding", data=body, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    rank = payload[0].get("embedding", []) if payload else []
    if rank and isinstance(rank[0], list):
        rank = rank[0]
    if len(rank) < 2 or not all(math.isfinite(float(value)) for value in rank[:2]):
        raise RuntimeError("llama-server did not return reranker yes/no scores")
    yes, no = float(rank[0]), float(rank[1])
    return yes / (yes + no)


def decision(value: float, policy: dict) -> str:
    if value >= policy["accept_at_or_above"]:
        return "take"
    if value <= policy["reject_at_or_below"]:
        return "drop"
    return "not_sure"


def evaluate_method(method_id: str, chunks: list[dict], questions: list[dict], scores: list[list[float]], policy: dict) -> dict:
    records = []
    for question, row_scores in zip(questions, scores):
        ranked = []
        for chunk, value in zip(chunks, row_scores):
            verdict = decision(value, policy)
            ranked.append({
                "chunk_id": chunk["id"], "score": round(value, 8), "decision": verdict,
                "atoms": chunk["atoms"], "text": chunk["text"],
                "byte_start": chunk["byte_start"], "byte_end": chunk["byte_end"],
            })
        ranked.sort(key=lambda item: (-item["score"], item["chunk_id"]))
        retained = [item for item in ranked if item["decision"] != "drop"][:3]
        found = sorted({atom for item in retained for atom in item["atoms"]})
        required = question.get("required_atoms", [])
        missing = [atom for atom in required if atom not in found]
        share = question.get("must_share_context", [])
        share_preserved = None if not share else any(all(atom in item["atoms"] for atom in share) for item in retained)
        forbidden = question.get("forbidden_atoms", [])
        forbidden_retained = sorted({atom for atom in forbidden if atom in found})
        false_take = not required and any(item["decision"] == "take" for item in retained)
        complete = not missing and not forbidden_retained and not false_take and share_preserved is not False
        records.append({
            "question_id": question["id"], "question": question["text"],
            "required_atoms": required, "found_required_atoms": [atom for atom in required if atom in found],
            "missing_atoms": missing, "must_share_context": share, "share_preserved": share_preserved,
            "forbidden_atoms_retained": forbidden_retained, "false_take": false_take,
            "complete": complete, "retained": retained, "all_ranked": ranked,
        })
    required_total = sum(len(item.get("required_atoms", [])) for item in questions)
    required_found = sum(len(item["found_required_atoms"]) for item in records)
    share_records = [item for item in records if item["share_preserved"] is not None]
    summary = {
        "complete_questions": sum(item["complete"] for item in records),
        "total_questions": len(records),
        "required_atoms_found": required_found,
        "required_atoms_total": required_total,
        "must_share_groups_preserved": sum(item["share_preserved"] is True for item in share_records),
        "must_share_groups_total": len(share_records),
        "forbidden_atoms_retained": sum(len(item["forbidden_atoms_retained"]) for item in records),
        "false_take_on_absent_answer": sum(item["false_take"] for item in records),
    }
    return {"method": method_id, "summary": summary, "records": records, "chunks": chunks}


def run(server: str) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_implementation_or_inference":
        raise RuntimeError("Gate 3C.6A.2 protocol is not locked")
    if world["status"] != "frozen_before_implementation_or_inference":
        raise RuntimeError("Gate 3C.6A.2 world is not frozen")
    source, ranges = build_source(world["source"]["blocks"])
    methods = {
        "fixed_45": fixed_word_chunks(source, ranges),
        "structure_overlap": structure_windows(source, world["source"]["blocks"], ranges),
    }
    instruction = protocol["frozen_model"]["instruction"]
    outputs = []
    started = time.monotonic()
    for method_id, chunks in methods.items():
        rows = []
        for question in world["questions"]:
            rows.append([score(server, instruction, question["text"], chunk["text"]) for chunk in chunks])
        outputs.append(evaluate_method(method_id, chunks, world["questions"], rows, protocol["selection_policy"]))
    fixed = next(item for item in outputs if item["method"] == "fixed_45")["summary"]
    structured = next(item for item in outputs if item["method"] == "structure_overlap")["summary"]
    gate = protocol["success_gate"]
    passed = (
        structured["complete_questions"] >= gate["structure_complete_questions_min"]
        and structured["must_share_groups_preserved"] == structured["must_share_groups_total"] == 4
        and structured["forbidden_atoms_retained"] <= gate["structure_forbidden_atoms_retained_max"]
        and structured["false_take_on_absent_answer"] <= gate["structure_false_take_on_absent_answer_max"]
        and structured["complete_questions"] >= fixed["complete_questions"] + 2
    )
    return {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "3C.6A.2",
        "status": "development_run_complete", "protocol": "/experiments/E007/chunking-protocol-v0.1.json",
        "world": "/experiments/E007/chunking-world-v0.1.json",
        "protocol_sha256": sha256_file(PROTOCOL_PATH), "world_sha256": sha256_file(WORLD_PATH),
        "model": {"file_sha256": sha256_file(MODEL_PATH), "quantization": "Q4_K_M"},
        "runtime_seconds": round(time.monotonic() - started, 3), "methods": outputs,
        "passed_locked_gate": passed,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:18085")
    args = parser.parse_args()
    result = run(args.server)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed_locked_gate"], "methods": {item["method"]: item["summary"] for item in result["methods"]}}, indent=2))


if __name__ == "__main__":
    main()
