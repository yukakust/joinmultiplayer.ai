#!/usr/bin/env python3
"""Build Gate 15E without model inference or gold-driven shelf selection."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SITE = ROOT / "site" / "experiments" / "E007"
WORLD = SITE / "world-v0.1.json"
PAIRWISE = SITE / "qwen8b-relevance-result-v0.1.json"
BUNDLE = SITE / "qwen8b-bundle-result-v0.1.json"
PROTOCOL = SITE / "evidence-ledger-protocol-v0.1.json"
OUTPUT = SITE / "evidence-ledger-result-v0.1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    world, pairwise, bundle = load(WORLD), load(PAIRWISE), load(BUNDLE)
    documents = {item["id"]: item for item in world["documents"]}
    pair_decisions = {(item["task_id"], item["source_id"]): item["decision"] for item in pairwise["records"]}
    records = []
    questions = []

    for task in bundle["records"]:
        selected = set(task["selector"]["selected_ids"])
        question_lower = task["question"].lower()
        task_records = []
        for offer in task["offers"]:
            source = documents[offer["source_id"]]
            tags = set(source.get("tags", []))
            identity_tags = tags - {
                "diagnostics", "safe-action", "historical-records", "version-checking",
                "independent-observation", "condition-matching", "fault-isolation",
                "source-checking", "insufficient", "lookalike", "dependent-copy",
                "contains-secret", "background-noise",
            }
            same_subject = any(tag in question_lower for tag in identity_tags)
            declared_alternative = (
                (task["family"] == "reject_condition_mismatch" and "lookalike" in tags)
                or (task["family"] == "preserve_supported_minority" and "dependent-copy" in tags)
            )
            if offer["source_id"] in selected:
                shelf = "USED"
            elif declared_alternative and same_subject:
                shelf = "SAME_CASE"
            else:
                shelf = "OTHER"
            conditional = shelf == "USED" and bool(tags & {"safe-action", "source-checking"})
            item = {
                "ledger_id": f"{task['id']}::{offer['source_id']}",
                "question_id": task["id"],
                "source_id": offer["source_id"],
                "lineage_id": offer["lineage"],
                "source_kind": source.get("source_kind", "record"),
                "claim_evidence": offer["fragment"],
                "sender_tags": source.get("tags", []),
                "pairwise_15c": pair_decisions[(task["id"], offer["source_id"])],
                "bundle_15d_selected": offer["source_id"] in selected,
                "shelf": shelf,
                "conditional": conditional,
                "preserved": True,
            }
            records.append(item)
            task_records.append(item)

        alternatives = [item for item in task_records if item["shelf"] == "SAME_CASE"]
        groups = defaultdict(list)
        for item in alternatives:
            groups[item["lineage_id"]].append(item["source_id"])
        questions.append({
            "id": task["id"],
            "question": task["question"],
            "best_answer": task["answer"]["parsed"],
            "used": [item["source_id"] for item in task_records if item["shelf"] == "USED"],
            "conditional": [item["source_id"] for item in task_records if item["conditional"]],
            "same_case": [item["source_id"] for item in alternatives],
            "same_case_views": [
                {"lineage_id": lineage, "source_ids": ids, "counted_views": 1}
                for lineage, ids in sorted(groups.items())
            ],
            "other_count": sum(item["shelf"] == "OTHER" for item in task_records),
        })

    bundle_by_id = {item["id"]: item for item in bundle["records"]}
    required = {(task["id"], source) for task in world["tasks"] for source in task["required_sources"]}
    alternatives = {(task["id"], source) for task in bundle["records"] for source in task["gold"]["alternatives"]}
    used_pairs = {(item["question_id"], item["source_id"]) for item in records if item["shelf"] == "USED"}
    same_pairs = {(item["question_id"], item["source_id"]) for item in records if item["shelf"] == "SAME_CASE"}
    other = [item for item in records if item["shelf"] == "OTHER"]
    copy_records = [item for item in records if item["shelf"] == "SAME_CASE" and item["source_kind"] == "dependent_copy"]
    copy_lineages = {item["lineage_id"] for item in copy_records}

    summary = {
        "questions": len(questions),
        "ledger_records_preserved": len(records),
        "required_pieces_in_used": len(required & used_pairs),
        "required_pieces_total": len(required),
        "same_case_alternatives_preserved": len(alternatives & same_pairs),
        "same_case_alternatives_total": len(alternatives),
        "other_records_preserved_hidden": len(other),
        "dependent_copy_records": len(copy_records),
        "dependent_copy_visible_lineages": len(copy_lineages),
        "new_model_calls": 0,
    }
    gates = {
        "all_records_preserved": summary["ledger_records_preserved"] == 480,
        "all_required_used": summary["required_pieces_in_used"] == summary["required_pieces_total"] == 60,
        "all_alternatives_preserved": summary["same_case_alternatives_preserved"] == summary["same_case_alternatives_total"] == 24,
        "all_other_hidden_not_deleted": summary["other_records_preserved_hidden"] == 396,
        "copies_collapsed_by_lineage": summary["dependent_copy_records"] == 18 and summary["dependent_copy_visible_lineages"] == 6,
        "no_new_model_calls": summary["new_model_calls"] == 0,
    }
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "gate": "15E",
        "status": "passed" if all(gates.values()) else "failed",
        "kind": "deterministic_synthetic_development_result",
        "inputs": {"world_sha256": sha256(WORLD), "pairwise_sha256": sha256(PAIRWISE), "bundle_sha256": sha256(BUNDLE), "protocol_sha256": sha256(PROTOCOL)},
        "summary": summary,
        "gates": gates,
        "questions": questions,
        "ledger": records,
        "boundaries": load(PROTOCOL)["boundaries"],
    }


def main() -> None:
    result = build()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "status": result["status"], "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
