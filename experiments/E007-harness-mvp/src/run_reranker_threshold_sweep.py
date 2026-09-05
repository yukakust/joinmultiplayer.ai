#!/usr/bin/env python3
"""Run the frozen E007 30-question threshold sweep against Qwen3-Reranker-4B."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


INSTRUCTION = "Given a peer question, decide whether this local conversation contains information that directly helps answer it."
PREFIX = '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
THRESHOLDS = [0.003, 0.005, 0.01, 0.03, 0.05, 0.1, 0.2, 0.5, 0.8, 0.92222771]


def useful(row: dict, source_id: str) -> bool:
    if row["kind"] != "answerable":
        return False
    if "-NOISE" in source_id or "-LOOKALIKE" in source_id:
        return False
    return True


def score(url: str, question: str, document: str) -> float:
    content = f"{PREFIX}<Instruct>: {INSTRUCTION}\n<Query>: {question}\n<Document>: {document}{SUFFIX}"
    body = json.dumps({"content": content, "embd_normalize": -1}).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.load(response)
    values = payload[0]["embedding"]
    if values and isinstance(values[0], list):
        values = values[0]
    yes, no = float(values[0]), float(values[1])
    return yes / (yes + no)


def metrics(rows: list[dict], threshold: float) -> dict:
    tp = fp = tn = fn = 0
    answerable_complete = no_answer_clean = 0
    for row in rows:
        for item in row["items"]:
            kept = item["score"] >= threshold
            if item["useful"] and kept: tp += 1
            elif item["useful"]: fn += 1
            elif kept: fp += 1
            else: tn += 1
        if row["kind"] == "answerable" and all(i["score"] >= threshold for i in row["items"] if i["useful"]):
            answerable_complete += 1
        if row["kind"] != "answerable" and not any(i["score"] >= threshold for i in row["items"]):
            no_answer_clean += 1
    return {
        "threshold": threshold,
        "useful_kept": tp,
        "useful_total": tp + fn,
        "useful_recall": round(tp / (tp + fn), 6),
        "irrelevant_dropped": tn,
        "irrelevant_total": tn + fp,
        "irrelevant_rejection": round(tn / (tn + fp), 6),
        "false_passes": fp,
        "useful_losses": fn,
        "answerable_complete": answerable_complete,
        "answerable_total": 20,
        "no_answer_clean": no_answer_clean,
        "no_answer_total": 10,
        "strict_questions_correct": answerable_complete + no_answer_clean,
        "strict_questions_total": 30
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--url", default="http://100.84.137.70:18181/embedding")
    args = parser.parse_args()
    source = json.loads(args.input.read_text())
    started = time.time()
    rows = []
    total = sum(len(row["candidate_messages"]) for row in source["rows"])
    done = 0
    for row in source["rows"]:
        items = []
        for message in row["candidate_messages"]:
            value = score(args.url, row["question"], message["text"])
            items.append({
                "source_id": message["source_id"],
                "useful": useful(row, message["source_id"]),
                "score": round(value, 8)
            })
            done += 1
            print(f"scored {done}/{total}", flush=True)
        rows.append({"id": row["id"], "kind": row["kind"], "items": items})
    result = {
        "schema_version": "e007-reranker-threshold-sweep-result-v0.1",
        "experiment": "E007",
        "checkpoint": "7S.14",
        "status": "completed_development",
        "model": "Qwen3-Reranker-4B Q4_K_M",
        "pairs": total,
        "seconds": round(time.time() - started, 3),
        "sweep": [metrics(rows, value) for value in THRESHOLDS],
        "rows": rows,
        "claim_boundary": "Candidate cutoff selection on a public synthetic set; unseen whole-conversation validation remains required."
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["sweep"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
