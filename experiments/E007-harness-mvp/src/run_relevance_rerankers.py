#!/usr/bin/env python3
"""Run E007 Gate 3C.4: frozen relevance scorers on a new held-out set."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/relevance-reranker-protocol-v0.1.json"
CALIBRATION_PATH = ROOT / "site/experiments/E007/send-policy-memory-v0.1.json"
HELDOUT_PATH = ROOT / "site/experiments/E007/relevance-reranker-heldout-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/relevance-reranker-result-v0.1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def calibrate(scores: list[float], labels: list[bool]) -> dict:
    positives = [score for score, label in zip(scores, labels) if label]
    negatives = [score for score, label in zip(scores, labels) if not label]
    accept_cut = percentile(positives, 0.25)
    reject_cut = percentile(negatives, 0.75)
    mode = "quantile_band"
    if reject_cut >= accept_cut:
        ordered = sorted(set(scores))
        candidates = [ordered[0] - 1e-9]
        candidates += [(left + right) / 2 for left, right in zip(ordered, ordered[1:])]
        candidates += [ordered[-1] + 1e-9]
        def rank(cut: float) -> tuple[int, int, int, float]:
            predicted = [score >= cut for score in scores]
            correct = sum(prediction == label for prediction, label in zip(predicted, labels))
            false_rejects = sum(label and not prediction for prediction, label in zip(predicted, labels))
            false_accepts = sum(not label and prediction for prediction, label in zip(predicted, labels))
            return (correct, -false_rejects, -false_accepts, -cut)
        midpoint = max(candidates, key=rank)
        accept_cut = reject_cut = midpoint
        mode = "collapsed_best_calibration_midpoint"
    return {
        "mode": mode,
        "reject_at_or_below": reject_cut,
        "accept_at_or_above": accept_cut,
        "calibration_scores": scores,
    }


def decide(score: float, calibration: dict) -> str:
    if score >= calibration["accept_at_or_above"]:
        return "accept"
    if score <= calibration["reject_at_or_below"]:
        return "reject"
    return "unclear"


def embedding_scorer(cache_dir: Path) -> Callable[[list[tuple[str, str]]], list[float]]:
    import numpy as np
    from fastembed import TextEmbedding

    model = TextEmbedding(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        cache_dir=str(cache_dir),
        local_files_only=True,
    )

    def score(pairs: list[tuple[str, str]]) -> list[float]:
        questions = np.asarray(list(model.embed([pair[0] for pair in pairs])))
        passages = np.asarray(list(model.embed([pair[1] for pair in pairs])))
        return np.sum(questions * passages, axis=1).tolist()

    return score


def minilm_scorer(model_path: Path, batch_size: int) -> Callable[[list[tuple[str, str]]], list[float]]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path, local_files_only=True, dtype=torch.float32,
    ).eval()

    def score(pairs: list[tuple[str, str]]) -> list[float]:
        values: list[float] = []
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start:start + batch_size]
            inputs = tokenizer(
                [pair[0] for pair in batch], [pair[1] for pair in batch],
                padding=True, truncation=True, max_length=512, return_tensors="pt",
            )
            with torch.inference_mode():
                logits = model(**inputs).logits.reshape(-1)
            values.extend(logits.tolist())
        return values

    return score


def qwen_reranker_scorer(model_path: Path, instruction: str, batch_size: int) -> Callable[[list[tuple[str, str]]], list[float]]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, padding_side="left")
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True,
    ).eval()
    false_id = tokenizer.convert_tokens_to_ids("no")
    true_id = tokenizer.convert_tokens_to_ids("yes")
    prefix = (
        '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. '
        'Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
    )
    suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)

    def score(pairs: list[tuple[str, str]]) -> list[float]:
        values: list[float] = []
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start:start + batch_size]
            texts = [f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {passage}" for query, passage in batch]
            encoded = tokenizer(texts, padding=False, truncation=True, max_length=2048 - len(prefix_tokens) - len(suffix_tokens))
            encoded["input_ids"] = [prefix_tokens + ids + suffix_tokens for ids in encoded["input_ids"]]
            inputs = tokenizer.pad(encoded, padding=True, return_tensors="pt")
            with torch.inference_mode():
                logits = model(**inputs).logits[:, -1, :]
                pair_logits = torch.stack([logits[:, false_id], logits[:, true_id]], dim=1)
                probabilities = torch.softmax(pair_logits, dim=1)[:, 1]
            values.extend(probabilities.tolist())
        return values

    return score


def evaluate_method(method_id: str, scorer: Callable[[list[tuple[str, str]]], list[float]], calibration_pairs: list[dict], heldout_pairs: list[dict]) -> dict:
    calibration_inputs = [(item["query"], item["passage"]) for item in calibration_pairs]
    calibration_labels = [bool(item["relevant"]) for item in calibration_pairs]
    started = time.monotonic()
    calibration_scores = scorer(calibration_inputs)
    thresholds = calibrate(calibration_scores, calibration_labels)
    heldout_scores = scorer([(item["question"], item["passage"]) for item in heldout_pairs])
    records = []
    for item, score in zip(heldout_pairs, heldout_scores):
        decision = decide(score, thresholds)
        expected = "accept" if item["kind"] == "useful" else "reject"
        records.append({**item, "score": round(float(score), 8), "decision": decision, "expected": expected, "correct": decision == expected})
    by_kind = {}
    for kind in ("useful", "hard_extra", "obvious_extra"):
        selected = [record for record in records if record["kind"] == kind]
        by_kind[kind] = {decision: sum(record["decision"] == decision for record in selected) for decision in ("accept", "unclear", "reject")}
    useful_rejected = by_kind["useful"]["reject"]
    useful_accepted = by_kind["useful"]["accept"]
    hard_accepted = by_kind["hard_extra"]["accept"]
    obvious_accepted = by_kind["obvious_extra"]["accept"]
    unclear_total = sum(record["decision"] == "unclear" for record in records)
    passed = useful_rejected == 0 and useful_accepted >= 7 and hard_accepted <= 1 and obvious_accepted == 0 and unclear_total <= 6
    return {
        "method": method_id,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "thresholds": {key: round(value, 8) if isinstance(value, float) else value for key, value in thresholds.items() if key != "calibration_scores"},
        "calibration": {
            "scores": [round(float(value), 8) for value in calibration_scores],
            "labels": calibration_labels,
        },
        "summary": {
            "correct": sum(record["correct"] for record in records), "total": len(records),
            "useful_rejected": useful_rejected, "useful_accepted": useful_accepted,
            "hard_extras_accepted": hard_accepted, "obvious_extras_accepted": obvious_accepted,
            "unclear_total": unclear_total, "by_kind": by_kind,
        },
        "passed_locked_gate": passed,
        "records": records,
    }


def main(args: argparse.Namespace) -> None:
    import torch

    torch.set_num_threads(args.threads)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))["calibration_pairs"]
    heldout = json.loads(HELDOUT_PATH.read_text(encoding="utf-8"))["pairs"]
    if protocol["status"] != "locked_before_download_or_inference":
        raise SystemExit("Protocol was not locked before inference")
    scorers = {
        "embedding_baseline": embedding_scorer(args.embedding_cache),
        "minilm_reranker": minilm_scorer(args.minilm_model, args.batch_size),
        "qwen_reranker": qwen_reranker_scorer(
            args.qwen_model,
            next(item["instruction"] for item in protocol["methods"] if item["id"] == "qwen_reranker"),
            args.batch_size,
        ),
    }
    methods = [evaluate_method(method_id, scorer, calibration, heldout) for method_id, scorer in scorers.items()]
    result = {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "3C.4",
        "status": "heldout_complete", "protocol": "/experiments/E007/relevance-reranker-protocol-v0.1.json",
        "protocol_sha256": sha256_file(PROTOCOL_PATH), "heldout_sha256": sha256_file(HELDOUT_PATH),
        "methods": methods,
        "winner_rule": "Prefer methods that pass every locked gate; among those, prefer fewer hard-extra accepts, then fewer unclear results, then the smaller model.",
        "boundary": "One English synthetic held-out set. This tests relevance scoring, not truth, privacy, or final answer quality. No method was trained or tuned on the held-out labels.",
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({item["method"]: {**item["summary"], "passed": item["passed_locked_gate"]} for item in methods}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding-cache", type=Path, required=True)
    parser.add_argument("--minilm-model", type=Path, required=True)
    parser.add_argument("--qwen-model", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=4)
    main(parser.parse_args())
