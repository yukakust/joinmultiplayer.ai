#!/usr/bin/env python3
"""Run E007 Gate 13C: a meta-NLI second pass over whole answer piles."""

from __future__ import annotations

import hashlib
import itertools
import json
import resource
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/answer-piles-second-pass-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/answer-piles-second-pass-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/answer-piles-second-pass-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_premise(left: dict, right: dict) -> str:
    left_lines = "\n".join(f"- {text}" for text in left["answers"])
    right_lines = "\n".join(f"- {text}" for text in right["answers"])
    return f"PILE A:\n{left_lines}\n\nPILE B:\n{right_lines}"


def components(ids: list[str], merge_pairs: set[tuple[str, str]]) -> list[list[str]]:
    remaining = set(ids)
    groups = []
    while remaining:
        root = min(remaining)
        stack = [root]
        group = set()
        while stack:
            current = stack.pop()
            if current in group:
                continue
            group.add(current)
            for left, right in merge_pairs:
                if left == current and right not in group:
                    stack.append(right)
                elif right == current and left not in group:
                    stack.append(left)
        remaining -= group
        groups.append(sorted(group))
    return groups


def main() -> None:
    protocol, world = read(PROTOCOL_PATH), read(WORLD_PATH)
    spec = protocol["model"]
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"])
    model = AutoModelForSequenceClassification.from_pretrained(
        spec["repository"], revision=spec["revision"], dtype=torch.float32
    )
    model.eval()

    jobs = []
    for left, right in itertools.combinations(world["piles"], 2):
        jobs.append((left, right, make_premise(left, right)))
    records = []
    for start in range(0, len(jobs), 16):
        batch = jobs[start : start + 16]
        encoded = tokenizer(
            [job[2] for job in batch],
            [protocol["frozen_input"]["hypothesis"] for _ in batch],
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        with torch.inference_mode():
            probabilities = torch.softmax(model(**encoded).logits, dim=-1)
        for job, score_tensor, tokens in zip(batch, probabilities, encoded["attention_mask"].sum(dim=1)):
            scores = {
                model.config.id2label[index].lower(): round(float(score), 8)
                for index, score in enumerate(score_tensor)
            }
            decision = max(scores, key=scores.get)
            records.append({
                "left_pile": job[0]["pile_id"],
                "right_pile": job[1]["pile_id"],
                "premise": job[2],
                "hypothesis": protocol["frozen_input"]["hypothesis"],
                "decision": decision,
                "probabilities": scores,
                "input_tokens": int(tokens),
                "merge": decision == "entailment",
            })

    expected = {
        tuple(sorted((item["left_pile"], item["right_pile"])))
        for item in world["expected_merges"]
    }
    predicted = {
        tuple(sorted((record["left_pile"], record["right_pile"])))
        for record in records if record["merge"]
    }
    recovered = len(expected & predicted)
    false_merges = len(predicted - expected)
    missed = len(expected - predicted)
    raw_groups = components([pile["pile_id"] for pile in world["piles"]], predicted)
    pile_by_id = {pile["pile_id"]: pile for pile in world["piles"]}
    final_groups = []
    forbidden = 0
    lost = 0
    for index, pile_ids in enumerate(raw_groups, 1):
        source_piles = [pile_by_id[pile_id] for pile_id in pile_ids]
        gold_piles = sorted({gold for pile in source_piles for gold in pile["gold_piles"]})
        answers = [answer for pile in source_piles for answer in pile["answers"]]
        final_groups.append({
            "group_id": f"S{index:02d}",
            "source_piles": pile_ids,
            "gold_piles": gold_piles,
            "answers": answers,
        })
        for left, right in world["forbidden_gold_merges"]:
            forbidden += int(left in gold_piles and right in gold_piles)
    lost = sum(len(pile["answers"]) for pile in world["piles"]) - sum(len(group["answers"]) for group in final_groups)
    exact_paraphrase = sum(
        any(group["gold_piles"] == [gold] and len(group["answers"]) == 2 for group in final_groups)
        for gold in ["G1", "G2", "G3", "G4", "G5", "G6"]
    )
    gate = protocol["locked_development_gate"]
    passed = (
        recovered == gate["recover_expected_merges"]
        and false_merges == gate["false_merges"]
        and exact_paraphrase == gate["final_exact_paraphrase_piles"]
        and forbidden == gate["final_forbidden_merges"]
        and lost == gate["lost_answers"]
    )
    result = {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "13C",
        "status": "posthoc_paired_synthetic_development_complete",
        "protocol": "/experiments/E007/answer-piles-second-pass-protocol-v0.1.json",
        "world": "/experiments/E007/answer-piles-second-pass-world-v0.1.json",
        "protocol_sha256": digest(PROTOCOL_PATH),
        "world_sha256": digest(WORLD_PATH),
        "model": spec,
        "runtime": {
            "seconds_including_model_load": round(time.perf_counter() - started, 3),
            "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "device": "cpu",
            "dtype": str(next(model.parameters()).dtype),
        },
        "summary": {
            "input_piles": len(world["piles"]),
            "pile_pairs": len(records),
            "expected_merges_recovered": recovered,
            "expected_merges_total": len(expected),
            "false_merges": false_merges,
            "missed_expected_merges": missed,
            "final_groups": len(final_groups),
            "final_exact_paraphrase_piles": exact_paraphrase,
            "final_forbidden_merges": forbidden,
            "lost_answers": lost,
            "passed_locked_development_gate": passed,
        },
        "predicted_merge_pairs": sorted(predicted),
        "missed_merge_pairs": sorted(expected - predicted),
        "false_merge_pairs": sorted(predicted - expected),
        "final_groups": final_groups,
        "pair_records": records,
        "boundary": protocol["boundary"],
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
