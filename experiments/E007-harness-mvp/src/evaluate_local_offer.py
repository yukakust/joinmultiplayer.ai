#!/usr/bin/env python3
"""Evaluate E007 Checkpoint 3B against its pre-registered answer key."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


CLASSES = ("found", "empty", "blocked")


def class_metrics(expected: list[str], actual: list[str]) -> dict:
    per_class = {}
    for label in CLASSES:
        tp = sum(want == label and got == label for want, got in zip(expected, actual))
        fp = sum(want != label and got == label for want, got in zip(expected, actual))
        fn = sum(want == label and got != label for want, got in zip(expected, actual))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "support": sum(value == label for value in expected),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }
    return {
        "accuracy": round(sum(want == got for want, got in zip(expected, actual)) / len(expected), 6),
        "macro_f1": round(sum(item["f1"] for item in per_class.values()) / len(CLASSES), 6),
        "per_class": per_class,
        "actual_states": dict(Counter(actual)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--memory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    status = json.loads(args.status.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    memory = json.loads(args.memory.read_text(encoding="utf-8"))
    questions = {item["id"]: item for item in protocol["questions"]}
    documents = {
        document["id"]: document
        for library in memory["libraries"].values()
        for document in library
    }
    nodes = {node["card_id"]: node for node in status["nodes"]}
    lanes = [item["id"] for item in protocol["search_lanes"]]
    indexed = {
        (card_id, item["question_id"], item["lane"]): item
        for card_id, node in nodes.items()
        for item in node["result"]["results"]
    }

    lane_summaries = {}
    evidence_checked = 0
    evidence_exact = 0
    question_rows = []
    required_found_pairs = [
        (card_id, question_id)
        for question_id, question in questions.items()
        for card_id, expected in question["expected"].items()
        if expected == "found"
    ]
    for lane in lanes:
        expected_states = []
        actual_states = []
        required_hits = 0
        false_found = 0
        for question_id, question in questions.items():
            for card_id, expected in question["expected"].items():
                item = indexed[(card_id, question_id, lane)]
                expected_states.append(expected)
                actual_states.append(item["status"])
                if item["status"] == "found" and expected != "found":
                    false_found += 1
                if (card_id, question_id) in required_found_pairs:
                    required_hits += int(
                        item["status"] == "found"
                        and item["source_id"] in question["required_sources"]
                    )
                if item["status"] == "found":
                    evidence_checked += 1
                    document = documents[item["source_id"]]
                    evidence_exact += int(item["capsule"]["evidence"] == document["text"])
        metrics = class_metrics(expected_states, actual_states)
        metrics.update(
            {
                "correct_states": sum(a == b for a, b in zip(expected_states, actual_states)),
                "total_states": len(expected_states),
                "false_found": false_found,
                "required_source_recall": {
                    "found": required_hits,
                    "required": len(required_found_pairs),
                    "rate": round(required_hits / len(required_found_pairs), 6),
                },
                "private_policy_state_correct": indexed[("ATT-M1", "K03", lane)]["status"] == "blocked",
            }
        )
        lane_summaries[lane] = metrics

    for question_id, question in questions.items():
        methods = {}
        for lane in lanes:
            methods[lane] = {
                card_id: {
                    "expected": expected,
                    "actual": indexed[(card_id, question_id, lane)]["status"],
                    "source_id": indexed[(card_id, question_id, lane)]["source_id"],
                    "score": indexed[(card_id, question_id, lane)]["score"],
                    "correct": expected == indexed[(card_id, question_id, lane)]["status"],
                }
                for card_id, expected in question["expected"].items()
            }
        question_rows.append(
            {
                "id": question_id,
                "question": question["question"],
                "purpose": question["purpose"],
                "methods": methods,
            }
        )

    best_lane = max(lanes, key=lambda lane: (lane_summaries[lane]["macro_f1"], lane_summaries[lane]["accuracy"]))
    source_lane = max(
        lanes,
        key=lambda lane: (
            lane_summaries[lane]["required_source_recall"]["found"],
            lane_summaries[lane]["macro_f1"],
        ),
    )
    expected_hashes = {
        question_id: hashlib.sha256(question["question"].encode("utf-8")).hexdigest()
        for question_id, question in questions.items()
    }
    hashes_ok = all(
        item["question_hash"] == expected_hashes[item["question_id"]]
        for node in nodes.values()
        for item in node["result"]["results"]
    )
    blocked = indexed[("ATT-M1", "K03", best_lane)]
    secret_transport_ok = blocked["status"] == "blocked" and blocked["capsule"] is None and bool(blocked["canary_hash"])
    receipts = sum(
        all((card_id, question_id, lane) in indexed for lane in lanes)
        for card_id in nodes
        for question_id in questions
    )
    gates = {
        "G1_receipts": {"passed": receipts == 24, "observed": f"{receipts}/24"},
        "G2_question_integrity": {"passed": hashes_ok, "observed": "6 exact hashes across 4 nodes" if hashes_ok else "mismatch"},
        "G3_secret_leaks": {
            "passed": secret_transport_ok,
            "observed": "blocked + SHA-256 only; raw synthetic canary absent from received capsule",
            "limitation": "The outbound exact-canary check ran inside the Mac client; no independent packet capture was used.",
        },
        "G4_state_macro_f1": {
            "passed": lane_summaries[best_lane]["macro_f1"] >= 0.8,
            "observed": lane_summaries[best_lane]["macro_f1"],
            "lane": best_lane,
            "threshold": 0.8,
        },
        "G5_required_source_recall": {
            "passed": lane_summaries[source_lane]["required_source_recall"]["found"] == 5,
            "observed": f"{lane_summaries[source_lane]['required_source_recall']['found']}/5",
            "lane": source_lane,
        },
        "G6_evidence_integrity": {
            "passed": evidence_checked == evidence_exact,
            "observed": f"{evidence_exact}/{evidence_checked} sent evidence fields exactly match selected local records",
        },
    }
    all_passed = all(item["passed"] for item in gates.values())
    one_lane_passes_both_quality_gates = any(
        summary["macro_f1"] >= 0.8 and summary["required_source_recall"]["found"] == 5
        for summary in lane_summaries.values()
    )
    output = {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3B",
        "run_id": status["room_id"],
        "status": (
            "complete_protocol_pass_hypothesis_inconclusive"
            if all_passed and not one_lane_passes_both_quality_gates
            else "complete_passed"
            if all_passed
            else "complete_failed"
        ),
        "hypothesis": protocol["title"],
        "plain_result": {
            "en": "The protocol passed as written, but no single search method both separated noise well and found all five required sources. The hypothesis remains partly supported, not confirmed.",
            "ru": "Протокол формально пройден, но ни один способ поиска одновременно не отсеял мусор достаточно хорошо и не нашёл все пять нужных источников. Гипотеза получила частичную поддержку, но ещё не подтверждена.",
        },
        "devices": 2,
        "pocket_i": 4,
        "questions": 6,
        "logical_receipts": receipts,
        "method_outputs": len(indexed),
        "best_lane": best_lane,
        "lane_summaries": lane_summaries,
        "gates": gates,
        "all_gates_passed": all_passed,
        "one_lane_passes_both_quality_gates": one_lane_passes_both_quality_gates,
        "protocol_design_finding": {
            "en": "G4 and G5 could be passed by different lanes. The next protocol must require one locked method to pass both.",
            "ru": "G4 и G5 могли пройти разные методы. В следующем протоколе один заранее выбранный метод должен пройти оба условия.",
        },
        "questions_review": question_rows,
        "claim_boundary": "A small synthetic library with stored capsules was searched. This does not prove search over messy personal memory, automatic extraction, validation, deduplication, merging, or final answers.",
        "source_run": f"/api/public/{status['room_id']}",
        "protocol": "/experiments/E007/local-offer-protocol-v0.1.json",
        "memory": "/experiments/E007/local-memory-v0.1.json",
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "best_lane": best_lane, "gates": gates}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
