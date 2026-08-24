#!/usr/bin/env python3
"""Deterministic pre-model claim and evidence harness for E005."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SOURCE_QUALITY = {
    "primary_manual": 1.0,
    "primary_diagnostic_guide": 1.0,
    "primary_safety_protocol": 1.0,
    "version_registry": 0.85,
    "independent_sensor_log": 0.8,
    "independent_audit": 0.8,
    "independent_test": 0.8,
    "technical_overview": 0.65,
    "copied_forum_note": 0.4,
    "copied_archive_note": 0.4,
    "unsigned_forum_post": 0.1,
}

STATUS_WEIGHT = {
    "current": 1.0,
    "superseded": 0.08,
    "stale_copy": 0.08,
    "unverified": 0.2,
}

CREDIBLE_ORIGIN_THRESHOLD = 0.65
RELATIVE_ALTERNATIVE_THRESHOLD = 0.4


def claim_stats(claim: dict, documents: dict[str, dict], pockets: dict[str, dict]) -> dict:
    by_lineage: dict[str, list[dict]] = {}
    for evidence_id in claim["evidence"]:
        document = documents[evidence_id]
        by_lineage.setdefault(document["lineage"], []).append(document)

    lineage_scores = {}
    credible_origin = False
    stale_records = 0
    current_records = 0
    for lineage, records in sorted(by_lineage.items()):
        record_scores = []
        for record in records:
            source_quality = SOURCE_QUALITY[record["source_type"]]
            status_weight = STATUS_WEIGHT[record["status"]]
            calibration = pockets[record["owner"]]["calibration"]
            record_scores.append(source_quality * status_weight * calibration)
            credible_origin |= source_quality >= CREDIBLE_ORIGIN_THRESHOLD
            stale_records += record["status"] in {"superseded", "stale_copy"}
            current_records += record["status"] == "current"
        # Copies within one lineage contribute only the strongest record once.
        lineage_scores[lineage] = max(record_scores)

    return {
        "claim_id": claim["id"],
        "role": claim.get("role", "answer"),
        "raw_supporters": len(set(claim["supporters"])),
        "independent_lineages": len(lineage_scores),
        "lineage_scores": {key: round(value, 6) for key, value in lineage_scores.items()},
        "evidence_score": round(sum(lineage_scores.values()), 6),
        "credible_origin": credible_origin,
        "current_records": current_records,
        "stale_records": stale_records,
        "depends_on": claim.get("depends_on", []),
    }


def analyze_task(task: dict, documents: dict[str, dict], pockets: dict[str, dict]) -> dict:
    stats = [claim_stats(claim, documents, pockets) for claim in task["claims"]]
    by_id = {item["claim_id"]: item for item in stats}
    answer_claims = [item for item in stats if item["role"] == "answer"]
    main = max(answer_claims, key=lambda item: (item["evidence_score"], item["independent_lineages"], item["claim_id"]))
    dependencies_met = all(
        dependency in by_id and by_id[dependency]["evidence_score"] > 0
        for dependency in main["depends_on"]
    )
    alternatives = []
    for item in answer_claims:
        if item["claim_id"] == main["claim_id"]:
            continue
        sufficiently_material = (
            item["raw_supporters"] >= main["raw_supporters"]
            or item["evidence_score"] >= RELATIVE_ALTERNATIVE_THRESHOLD * main["evidence_score"]
        )
        if item["credible_origin"] and sufficiently_material:
            alternatives.append(item["claim_id"])

    raw_majority = max(
        answer_claims,
        key=lambda item: (item["raw_supporters"], item["claim_id"]),
    )["claim_id"]
    expected = task["expected"]
    expected_alternatives = [expected["alternative_claim"]] if expected["report_alternative"] else []
    return {
        "task_id": task["id"],
        "family": task["family"],
        "claims": stats,
        "raw_majority_claim": raw_majority,
        "raw_majority_correct": raw_majority == expected["main_claim"],
        "selected_main_claim": main["claim_id"],
        "main_correct": main["claim_id"] == expected["main_claim"] and dependencies_met,
        "dependencies_met": dependencies_met,
        "reported_alternatives": alternatives,
        "minority_policy_correct": sorted(alternatives) == sorted(expected_alternatives),
    }


def run(world: dict) -> dict:
    documents = {document["id"]: document for document in world["documents"]}
    pockets = {pocket["id"]: pocket for pocket in world["pockets"]}
    rows = [analyze_task(task, documents, pockets) for task in world["tasks"]]
    task_count = len(rows)
    return {
        "experiment_id": "E005",
        "protocol_version": world["protocol_version"],
        "kind": "deterministic_public_harness",
        "status": "passed" if all(row["main_correct"] and row["minority_policy_correct"] for row in rows) else "failed",
        "claim_status": "public_development_only",
        "tasks": task_count,
        "raw_majority_accuracy": sum(row["raw_majority_correct"] for row in rows) / task_count,
        "evidence_graph_accuracy": sum(row["main_correct"] for row in rows) / task_count,
        "minority_policy_accuracy": sum(row["minority_policy_correct"] for row in rows) / task_count,
        "rows": rows,
        "claim_boundary": {
            "en": "This harness reads predeclared public claims and provenance. It validates accounting and reporting policy, not retrieval, model understanding, routing, or generalization.",
            "ru": "Harness читает заранее заданные открытые утверждения и происхождение. Он проверяет учёт и политику отчёта, но не поиск, понимание модели, routing или обобщение."
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    args = parser.parse_args()
    world = json.loads(args.world.read_text(encoding="utf-8"))
    print(json.dumps(run(world), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
