#!/usr/bin/env python3
"""Build the public Gate 5B.2 comparison and deterministic owner-audit queue."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


CONDITIONS = [
    "shared_qwen_alone", "cause_track_alone", "safety_track_alone",
    "wrong_same_role_pair", "semantic_text_capsules", "correct_neural_pair",
]


def atomic_write(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def key(row: dict) -> tuple[str, str, str]:
    return row["question_id"], row["language"], row["condition"]


def compact(row: dict) -> dict:
    judgment = row["judgment"]
    return {
        "cause": judgment["cause"],
        "cause_quote": judgment["cause_quote"],
        "safe_action": judgment["safe_action"],
        "safe_action_quote": judgment["safe_action_quote"],
        "overall": judgment["overall"],
        "confidence": judgment["confidence"],
    }


def condition_counts(records: list[dict]) -> list[dict]:
    result = []
    for condition in CONDITIONS:
        rows = [row for row in records if row["condition"] == condition]
        overall = Counter(row["judgment"]["overall"] for row in rows)
        result.append({
            "id": condition,
            "total": len(rows),
            "complete": overall["correct"],
            "partial": overall["partial"],
            "incorrect": overall["incorrect"],
            "cause_correct": sum(row["judgment"]["cause"] == "correct" for row in rows),
            "safe_action_correct": sum(row["judgment"]["safe_action"] == "correct" for row in rows),
        })
    return result


def build(source: dict, judge_a: dict, judge_b: dict) -> tuple[dict, dict]:
    if judge_a["status"] != "completed" or judge_b["status"] != "completed":
        raise ValueError("both judge runs must be complete")
    if len(judge_a["records"]) != 192 or len(judge_b["records"]) != 192:
        raise ValueError("each judge must contain 192 records")

    source_by_key = {key(row): row for row in source["records"]}
    a_by_key = {key(row): row for row in judge_a["records"]}
    b_by_key = {key(row): row for row in judge_b["records"]}
    if set(source_by_key) != set(a_by_key) or set(a_by_key) != set(b_by_key):
        raise ValueError("source and judge record keys differ")

    overall_disagreements = []
    component_disagreements = 0
    agreements_by_cell = defaultdict(list)
    for record_key in sorted(a_by_key):
        a = a_by_key[record_key]
        b = b_by_key[record_key]
        if a["judgment"]["cause"] != b["judgment"]["cause"] or a["judgment"]["safe_action"] != b["judgment"]["safe_action"]:
            component_disagreements += 1
        if a["judgment"]["overall"] != b["judgment"]["overall"]:
            overall_disagreements.append(record_key)
        else:
            agreements_by_cell[(record_key[2], record_key[1])].append(record_key)

    sampled_agreements = []
    for cell in sorted(agreements_by_cell):
        ranked = sorted(
            agreements_by_cell[cell],
            key=lambda item: hashlib.sha256(("gate5b2-owner-audit|" + "|".join(item)).encode()).hexdigest(),
        )
        if len(ranked) < 2:
            raise ValueError(f"not enough agreements in {cell}")
        sampled_agreements.extend(ranked[:2])

    def audit_item(record_key: tuple[str, str, str], reason: str) -> dict:
        source_row = source_by_key[record_key]
        a = a_by_key[record_key]
        b = b_by_key[record_key]
        return {
            "audit_id": "A-" + hashlib.sha256((reason + "|" + "|".join(record_key)).encode()).hexdigest()[:12],
            "reason": reason,
            "question_id": record_key[0],
            "language": record_key[1],
            "condition_hidden_until_review": record_key[2],
            "question": source_row["question"],
            "expected_cause": source_row["expected_cause"],
            "expected_safe_action": source_row["expected_safety"],
            "answer": source_row["answer"],
            "judge_a3": compact(a),
            "judge_b": compact(b),
        }

    audit_items = [audit_item(item, "overall_disagreement") for item in overall_disagreements]
    audit_items.extend(audit_item(item, "agreement_sample") for item in sampled_agreements)
    audit = {
        "experiment_id": "E005", "gate": "5B.2", "kind": "owner_audit_queue", "version": "0.6",
        "status": "awaiting_owner", "always_review_count": len(overall_disagreements),
        "agreement_sample_count": len(sampled_agreements), "total": len(audit_items),
        "sampling": "two deterministic overall-agreement records from each condition-language cell",
        "expansion_rule": "If the owner corrects more than 2 sampled agreements, review every remaining agreement.",
        "items": audit_items,
    }

    summary = {
        "experiment_id": "E005", "gate": "5B.2", "kind": "two_judge_provisional_summary", "version": "0.6",
        "status": "awaiting_owner_audit",
        "judge_a3": {"model": judge_a["judge"]["model"], "calibration": "12/12", "conditions": condition_counts(judge_a["records"])},
        "judge_b": {"model": judge_b["judge"]["model"], "calibration": "12/12", "conditions": condition_counts(judge_b["records"])},
        "agreement": {
            "overall_agreements": 192 - len(overall_disagreements),
            "overall_disagreements": len(overall_disagreements),
            "component_disagreements": component_disagreements,
            "total": 192,
        },
        "plain_result": {
            "en": "Both judges strongly prefer clear text capsules to the neural hidden-state pair. The neural pair preserved the cause but usually lost the safe action.",
            "ru": "Оба судьи намного выше оценили понятные текстовые капсулы, чем нейронную пару скрытых состояний. Нейронная пара сохранила причину, но почти всегда потеряла безопасное действие."
        },
        "claim_boundary": {
            "en": "Provisional until the owner reviews every overall disagreement and 24 sampled agreements. Both judges share Qwen lineage.",
            "ru": "Результат предварительный, пока владелец не проверит все итоговые разногласия и 24 выбранных совпадения. Оба судьи происходят из семейства Qwen."
        },
    }
    return summary, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--judge-a", type=Path, required=True)
    parser.add_argument("--judge-b", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    summary, audit = build(json.loads(args.source.read_text()), json.loads(args.judge_a.read_text()), json.loads(args.judge_b.read_text()))
    atomic_write(args.summary, summary)
    atomic_write(args.audit, audit)


if __name__ == "__main__":
    main()
