#!/usr/bin/env python3
"""Run E007 Gate 13B: bidirectional DeBERTa NLI answer piles."""

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
PROTOCOL_PATH = ROOT / "site/experiments/E007/answer-piles-nli-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/answer-piles-nli-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/answer-piles-nli-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair_key(left_id: str, right_id: str) -> tuple[str, str]:
    return tuple(sorted((left_id, right_id)))


def relation(left_decision: str, right_decision: str) -> str:
    if left_decision == "entailment" and right_decision == "entailment":
        return "same_version"
    if "contradiction" in (left_decision, right_decision):
        return "opposing_versions"
    return "different_or_related"


def build_piles(answers: list[dict], relations: dict[tuple[str, str], str]) -> list[list[str]]:
    piles: list[list[str]] = []
    for answer in sorted(answers, key=lambda item: item["id"]):
        answer_id = answer["id"]
        for pile in piles:
            if all(relations[pair_key(answer_id, member)] == "same_version" for member in pile):
                pile.append(answer_id)
                break
        else:
            piles.append([answer_id])
    return piles


def pairwise_metrics(answers: list[dict], piles: list[list[str]]) -> dict:
    gold = {
        pair_key(left["id"], right["id"])
        for left, right in itertools.combinations(answers, 2)
        if left["gold_pile"] == right["gold_pile"]
    }
    predicted = {
        pair_key(left, right)
        for pile in piles
        for left, right in itertools.combinations(pile, 2)
    }
    tp = len(gold & predicted)
    fp = len(predicted - gold)
    fn = len(gold - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }


def infer_pair_records(model, tokenizer, answers: list[dict], batch_size: int = 16) -> list[dict]:
    jobs = []
    for left, right in itertools.combinations(answers, 2):
        jobs.append((left, right, left["text"], right["text"]))
        jobs.append((left, right, right["text"], left["text"]))

    outputs = []
    for start in range(0, len(jobs), batch_size):
        batch = jobs[start : start + batch_size]
        encoded = tokenizer(
            [job[2] for job in batch],
            [job[3] for job in batch],
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        with torch.inference_mode():
            probabilities = torch.softmax(model(**encoded).logits, dim=-1)
        for job, scores_tensor, tokens in zip(batch, probabilities, encoded["attention_mask"].sum(dim=1)):
            scores = {
                model.config.id2label[index].lower(): round(float(score), 8)
                for index, score in enumerate(scores_tensor)
            }
            outputs.append({
                "left_id": job[0]["id"],
                "right_id": job[1]["id"],
                "premise_id": job[0]["id"] if job[2] == job[0]["text"] else job[1]["id"],
                "hypothesis_id": job[1]["id"] if job[3] == job[1]["text"] else job[0]["id"],
                "decision": max(scores, key=scores.get),
                "probabilities": scores,
                "input_tokens": int(tokens),
            })

    records = []
    for index in range(0, len(outputs), 2):
        forward, reverse = outputs[index], outputs[index + 1]
        records.append({
            "left_id": forward["left_id"],
            "right_id": forward["right_id"],
            "left_to_right": {
                "decision": forward["decision"],
                "probabilities": forward["probabilities"],
                "input_tokens": forward["input_tokens"],
            },
            "right_to_left": {
                "decision": reverse["decision"],
                "probabilities": reverse["probabilities"],
                "input_tokens": reverse["input_tokens"],
            },
            "relation": relation(forward["decision"], reverse["decision"]),
        })
    return records


def main() -> None:
    protocol, world = read(PROTOCOL_PATH), read(WORLD_PATH)
    spec = protocol["model"]
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"])
    model = AutoModelForSequenceClassification.from_pretrained(
        spec["repository"], revision=spec["revision"], dtype=torch.float32
    )
    model.eval()

    answers = world["answers"]
    pair_records = infer_pair_records(model, tokenizer, answers)
    relation_map = {
        pair_key(record["left_id"], record["right_id"]): record["relation"]
        for record in pair_records
    }
    raw_piles = build_piles(answers, relation_map)
    answer_by_id = {answer["id"]: answer for answer in answers}
    piles = []
    for index, answer_ids in enumerate(raw_piles, 1):
        members = [answer_by_id[answer_id] for answer_id in answer_ids]
        piles.append({
            "pile_id": f"P{index:02d}",
            "answer_ids": answer_ids,
            "gold_piles": sorted({member["gold_pile"] for member in members}),
            "answers": members,
        })

    metrics = pairwise_metrics(answers, raw_piles)
    exact = 0
    for gold in world["gold_piles"]:
        if len(gold["answer_ids"]) > 1 and any(set(pile) == set(gold["answer_ids"]) for pile in raw_piles):
            exact += 1
    forbidden = 0
    for item in world["forbidden_merges"]:
        if any(
            item["left_pile"] in pile["gold_piles"] and item["right_pile"] in pile["gold_piles"]
            for pile in piles
        ):
            forbidden += 1
    opposing = sum(record["relation"] == "opposing_versions" for record in pair_records)
    related = sum(record["relation"] == "different_or_related" for record in pair_records)
    same = sum(record["relation"] == "same_version" for record in pair_records)
    lost = len(answers) - sum(len(pile) for pile in raw_piles)
    gate = protocol["locked_development_gate"]
    passed = (
        exact == gate["exact_paraphrase_piles"]
        and forbidden == gate["forbidden_merges"]
        and lost == gate["lost_answers"]
        and metrics["f1"] >= gate["pairwise_f1_at_least"]
    )
    result = {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "13B",
        "status": "paired_synthetic_development_complete",
        "protocol": "/experiments/E007/answer-piles-nli-protocol-v0.1.json",
        "world": "/experiments/E007/answer-piles-nli-world-v0.1.json",
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
            "answers": len(answers),
            "pairs": len(pair_records),
            "model_calls": len(pair_records) * 2,
            "predicted_piles": len(piles),
            "gold_piles": len(world["gold_piles"]),
            "exact_paraphrase_piles": exact,
            "paraphrase_piles_total": gate["paraphrase_piles_total"],
            "forbidden_merges": forbidden,
            "lost_answers": lost,
            "same_version_pairs": same,
            "opposing_version_pairs": opposing,
            "different_or_related_pairs": related,
            "pairwise": metrics,
            "passed_locked_development_gate": passed,
        },
        "piles": piles,
        "pair_records": pair_records,
        "boundary": protocol["comparison_boundary"],
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
