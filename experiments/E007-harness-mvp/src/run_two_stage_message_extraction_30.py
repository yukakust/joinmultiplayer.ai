#!/usr/bin/env python3
"""Run the frozen 20-answerable + 10-empty two-stage extraction gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "two_stage_message_extraction",
    HERE / "run_two_stage_message_extraction.py",
)
TWO_STAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TWO_STAGE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build_cases(world: dict) -> list[dict]:
    documents = {item["id"]: item for item in world["documents"]}
    background = [item for item in world["documents"] if item["id"].startswith("E7-F-")]
    cases = []
    for index, task in enumerate(world["tasks"][:30]):
        answerable = index < 20
        if answerable:
            source_ids = list(task["all_candidate_sources"])
        else:
            source_ids = list(task["distractor_sources"])
            for offset in range(len(background)):
                candidate = background[(index * 7 + offset) % len(background)]["id"]
                if candidate not in source_ids:
                    source_ids.append(candidate)
                if len(source_ids) == 3:
                    break
        messages = [
            {
                "real_id": source_id,
                "role": "assistant",
                "text": documents[source_id]["text"],
                "handle": f"M{number}",
            }
            for number, source_id in enumerate(source_ids, 1)
        ]
        cases.append({
            "id": task["id"],
            "kind": "answerable" if answerable else "no_answer_in_packet",
            "question": task["question"],
            "expected": task["expected"] if answerable else {"status": "no_answer_in_packet"},
            "required_sources": list(task["required_sources"]) if answerable else [],
            "removed_sources": [] if answerable else list(task["required_sources"]),
            "messages": messages,
        })
    if len(cases) != 30:
        raise ValueError("the frozen gate requires exactly 30 cases")
    if sum(case["kind"] == "answerable" for case in cases) != 20:
        raise ValueError("the frozen gate requires exactly 20 answerable cases")
    return cases


def evaluate(case: dict, result: dict) -> dict:
    source_by_handle = {item["handle"]: item["real_id"] for item in case["messages"]}
    accepted_handles = {
        item["handle"]
        for extraction in result["extractions"]
        for item in extraction["accepted"]
    }
    accepted_sources = sorted(source_by_handle[handle] for handle in accepted_handles)
    required = set(case["required_sources"])
    if case["kind"] == "answerable":
        passed = required.issubset(accepted_sources)
        false_positive_sources = sorted(set(accepted_sources) - required)
    else:
        passed = not accepted_sources
        false_positive_sources = accepted_sources
    return {
        "passed": passed,
        "required_sources_recovered": len(required.intersection(accepted_sources)),
        "required_sources_total": len(required),
        "accepted_sources": accepted_sources,
        "false_positive_sources": false_positive_sources,
        "accepted_claims": result["accepted_claims"],
        "placeholder_rejections": result["placeholder_rejections"],
    }


def public_case(case: dict, result: dict, evaluation: dict) -> dict:
    source_by_handle = {item["handle"]: item["real_id"] for item in case["messages"]}
    return {
        "id": case["id"],
        "kind": case["kind"],
        "question": case["question"],
        "expected": case["expected"],
        "candidate_messages": [
            {"handle": item["handle"], "source_id": item["real_id"], "text": item["text"]}
            for item in case["messages"]
        ],
        "selected": [
            {"handle": handle, "source_id": source_by_handle[handle]}
            for handle in result["selected_handles"]
        ],
        "selection_errors": result["selection_errors"],
        "extractions": [
            {
                "handle": item["handle"],
                "source_id": source_by_handle[item["handle"]],
                "status": item["status"],
                "accepted": item["accepted"],
                "rejected": item["rejected"],
            }
            for item in result["extractions"]
        ],
        "evaluation": evaluation,
        "seconds": result["seconds"],
    }


def summary(rows: list[dict]) -> dict:
    positives = [row for row in rows if row["kind"] == "answerable"]
    negatives = [row for row in rows if row["kind"] == "no_answer_in_packet"]
    return {
        "cases": len(rows),
        "answerable_cases": len(positives),
        "no_answer_cases": len(negatives),
        "answerable_passed": sum(row["evaluation"]["passed"] for row in positives),
        "no_answer_passed": sum(row["evaluation"]["passed"] for row in negatives),
        "all_required_sources": sum(row["evaluation"]["required_sources_total"] for row in positives),
        "required_sources_recovered": sum(row["evaluation"]["required_sources_recovered"] for row in positives),
        "false_positive_sources": sum(len(row["evaluation"]["false_positive_sources"]) for row in rows),
        "accepted_claims": sum(row["evaluation"]["accepted_claims"] for row in rows),
        "placeholder_rejections": sum(row["evaluation"]["placeholder_rejections"] for row in rows),
        "seconds": round(sum(row["seconds"] for row in rows), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", required=True, type=Path)
    parser.add_argument("--reader-url", default="http://127.0.0.1:18180")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    world = json.loads(args.world.read_text(encoding="utf-8"))
    cases = build_cases(world)
    rows = []
    if args.resume and args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        rows = previous.get("rows", [])
    completed = {row["id"] for row in rows}
    started = time.time()
    for number, case in enumerate(cases, 1):
        if case["id"] in completed:
            continue
        result = TWO_STAGE.run_case(args.reader_url, case)
        evaluation = evaluate(case, result)
        rows.append(public_case(case, result, evaluation))
        payload = {
            "schema_version": "e007-two-stage-message-extraction-30-v0.1",
            "experiment": "E007",
            "checkpoint": "7S.2",
            "status": "running" if len(rows) < len(cases) else "completed",
            "world_sha256": sha256(args.world),
            "frozen_design": {"answerable": 20, "no_answer_in_packet": 10},
            "summary": summary(rows),
            "rows": rows,
        }
        atomic_write(args.output, payload)
        print(json.dumps({
            "case": f"{number}/30",
            "id": case["id"],
            "kind": case["kind"],
            "passed": evaluation["passed"],
            "required": f"{evaluation['required_sources_recovered']}/{evaluation['required_sources_total']}",
            "false_positive_sources": len(evaluation["false_positive_sources"]),
            "seconds": result["seconds"],
        }), flush=True)
    print(json.dumps({"status": "complete", "summary": summary(rows), "wall_seconds": round(time.time() - started, 3)}))


if __name__ == "__main__":
    main()
