#!/usr/bin/env python3
"""Run E007 Gate 3C.6M with complete multi-word button scoring."""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import torch


ROOT = Path(__file__).parents[3]
BASE_PATH = ROOT / "experiments/E007-harness-mvp/src/run_ninety_word_gate.py"
SPEC = importlib.util.spec_from_file_location("run_ninety_word_gate", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

PROTOCOL_PATH = ROOT / "site/experiments/E007/phrase-length-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/phrase-length-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/phrase-length-result-v0.1.json"
SYSTEM = (
    "Use only the supplied question, source, proposed answer, and button meanings. "
    "Choose the button whose written meaning fits. Output exactly one complete button phrase and nothing else."
)


def family_passes(summary: dict) -> bool:
    return (
        summary["semantic_correct"] >= 18
        and min(summary["order_correct"].values()) >= 9
        and summary["minimum_class_correct_within_an_order"] >= 4
        and summary["order_stable_pairs"] >= 9
    )


def score_complete_phrases(model, tokenizer, items: list[dict], batch_size: int) -> list[dict]:
    records = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        expanded, metadata = [], []
        for item in batch:
            rendered = tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": item["prompt"]},
                ],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            prefix_ids = tokenizer(rendered, add_special_tokens=False)["input_ids"]
            for label in item["labels"]:
                candidate_ids = tokenizer.encode(label, add_special_tokens=False)
                expanded.append(prefix_ids + candidate_ids)
                metadata.append((item["id"], label, len(prefix_ids), candidate_ids))
        max_length = max(len(ids) for ids in expanded)
        input_ids, attention_masks, left_pads = [], [], []
        for ids in expanded:
            pad = max_length - len(ids)
            left_pads.append(pad)
            input_ids.append([tokenizer.pad_token_id] * pad + ids)
            attention_masks.append([0] * pad + [1] * len(ids))
        with torch.inference_mode():
            logits = model(
                input_ids=torch.tensor(input_ids, dtype=torch.long),
                attention_mask=torch.tensor(attention_masks, dtype=torch.long),
            ).logits
            log_probs = torch.log_softmax(logits, dim=-1)
        sums = {item["id"]: {} for item in batch}
        means = {item["id"]: {} for item in batch}
        token_counts = {item["id"]: {} for item in batch}
        prompt_tokens = {}
        for row, ((item_id, label, prefix_length, candidate_ids), pad) in enumerate(zip(metadata, left_pads)):
            start_index = pad + prefix_length
            token_scores = [
                float(log_probs[row, start_index + offset - 1, token_id].item())
                for offset, token_id in enumerate(candidate_ids)
            ]
            sums[item_id][label] = sum(token_scores)
            means[item_id][label] = sum(token_scores) / len(token_scores)
            token_counts[item_id][label] = len(candidate_ids)
            prompt_tokens[item_id] = prefix_length
        for item in batch:
            labels = item["labels"]
            sum_tensor = torch.tensor([sums[item["id"]][label] for label in labels])
            mean_tensor = torch.tensor([means[item["id"]][label] for label in labels])
            sum_probabilities = torch.softmax(sum_tensor, dim=0)
            mean_probabilities = torch.softmax(mean_tensor, dim=0)
            sum_decision = labels[int(torch.argmax(sum_tensor).item())]
            mean_decision = labels[int(torch.argmax(mean_tensor).item())]
            records.append({
                **item,
                "prompt_tokens_with_system": prompt_tokens[item["id"]],
                "label_token_counts": token_counts[item["id"]],
                "decision": sum_decision,
                "length_normalized_decision": mean_decision,
                "scores": {label: round(float(sum_probabilities[index].item()), 8) for index, label in enumerate(labels)},
                "length_normalized_scores": {label: round(float(mean_probabilities[index].item()), 8) for index, label in enumerate(labels)},
                "sequence_log_scores": {label: round(sums[item["id"]][label], 8) for label in labels},
                "mean_token_log_scores": {label: round(means[item["id"]][label], 8) for label in labels},
            })
        print(json.dumps({"scored": min(start + batch_size, len(items)), "total": len(items)}), flush=True)
    return records


def summarize_family(records: list[dict], family: dict) -> dict:
    orders = ("POSITIVE_FIRST", "NEGATIVE_FIRST")
    order_correct = {
        order: sum(record["semantic_correct"] for record in records if record["order"] == order)
        for order in orders
    }
    class_order_correct = {
        f"{order}_{meaning}": sum(
            record["semantic_correct"]
            for record in records
            if record["order"] == order and record["expected_semantic"] == meaning
        )
        for order in orders for meaning in ("approve", "reject")
    }
    by_pair = {(record["case_id"], record["order"]): record for record in records}
    pairs = []
    for case_id in sorted({record["case_id"] for record in records}):
        first = by_pair[(case_id, "POSITIVE_FIRST")]
        second = by_pair[(case_id, "NEGATIVE_FIRST")]
        pairs.append({
            "case_id": case_id,
            "positive_first_decision": first["decision"],
            "negative_first_decision": second["decision"],
            "positive_first_semantic": first["actual_semantic"],
            "negative_first_semantic": second["actual_semantic"],
            "semantic_stable": first["actual_semantic"] == second["actual_semantic"],
        })
    summary = {
        "family_id": family["id"],
        "positive": family["positive"],
        "negative": family["negative"],
        "balanced": family["balanced"],
        "semantic_correct": sum(record["semantic_correct"] for record in records),
        "total": 20,
        "order_correct": order_correct,
        "class_order_correct": class_order_correct,
        "minimum_class_correct_within_an_order": min(class_order_correct.values()),
        "order_stable_pairs": sum(pair["semantic_stable"] for pair in pairs),
        "total_pairs": 10,
        "label_choices": {
            family["positive"]: sum(record["decision"] == family["positive"] for record in records),
            family["negative"]: sum(record["decision"] == family["negative"] for record in records),
        },
        "length_normalized_semantic_correct": sum(record["length_normalized_semantic_correct"] for record in records),
        "pairs": pairs,
    }
    summary["passed"] = family_passes(summary) if family["balanced"] else False
    return summary


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6M inputs are not frozen")

    torch.set_num_threads(threads)
    model, tokenizer = BASE.load_model()
    started = time.monotonic()
    outputs = score_complete_phrases(model, tokenizer, world["items"], batch_size)
    records = []
    for output in outputs:
        actual_semantic = output["mapping"][output["decision"]]
        normalized_semantic = output["mapping"][output["length_normalized_decision"]]
        records.append({
            **output,
            "actual_semantic": actual_semantic,
            "semantic_correct": actual_semantic == output["expected_semantic"],
            "length_normalized_semantic": normalized_semantic,
            "length_normalized_semantic_correct": normalized_semantic == output["expected_semantic"],
        })

    family_summaries = []
    for family in world["families"]:
        family_records = [record for record in records if record["family_id"] == family["id"]]
        family_summaries.append(summarize_family(family_records, family))
    passing = [summary for summary in family_summaries if summary["passed"]]
    selected = passing[0]["family_id"] if passing else None
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6M",
        "status": "synthetic_development_comparison_complete",
        "protocol": "/experiments/E007/phrase-length-protocol-v0.1.json",
        "world": "/experiments/E007/phrase-length-world-v0.1.json",
        "protocol_sha256": BASE.sha256_file(PROTOCOL_PATH),
        "world_sha256": BASE.sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": BASE.sha256_file(BASE.MODEL_FILE),
            "weights_changed": False,
        },
        "scoring": "summed_complete_sequence_log_probability",
        "runtime_seconds": round(time.monotonic() - started, 3),
        "selected_family": selected,
        "families": family_summaries,
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.batch_size, args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selected_family": result["selected_family"],
        "families": [{key: family[key] for key in ("family_id", "semantic_correct", "order_correct", "order_stable_pairs", "passed", "length_normalized_semantic_correct")} for family in result["families"]]
    }, indent=2))


if __name__ == "__main__":
    main()
