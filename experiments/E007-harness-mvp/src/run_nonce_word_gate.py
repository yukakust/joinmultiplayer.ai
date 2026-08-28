#!/usr/bin/env python3
"""Run E007 Gate 3C.6L with complete two-token label scoring."""

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

PROTOCOL_PATH = ROOT / "site/experiments/E007/nonce-word-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/nonce-word-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/nonce-word-result-v0.1.json"
LABELS = ("KSEL", "PTHY")
SYSTEM = (
    "Use only the supplied question, source, proposed answer, and label mapping. "
    "The labels are invented words. Follow the written mapping exactly. "
    "Output only KSEL or PTHY."
)


def interpretation(summary: dict) -> str:
    if (
        summary["semantic_correct"] >= 18
        and min(summary["deck_correct"].values()) >= 9
        and summary["minimum_class_correct_within_a_deck"] >= 4
    ):
        return "semantic_success"
    if summary["label_choices"]["KSEL"] >= 16:
        return "strong_KSEL_bias"
    if summary["label_choices"]["PTHY"] >= 16:
        return "strong_PTHY_bias"
    if summary["paired_label_flips"] >= 8:
        return "mapping_followed_but_semantics_failed"
    return "mixed_or_unresolved"


def score_complete_labels(model, tokenizer, items: list[dict], batch_size: int) -> list[dict]:
    label_ids = {label: tokenizer.encode(label, add_special_tokens=False) for label in LABELS}
    if any(len(ids) != 2 for ids in label_ids.values()):
        raise RuntimeError(f"Expected equal two-token labels, got {label_ids}")
    records = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        expanded = []
        metadata = []
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
            for label in LABELS:
                expanded.append(prefix_ids + label_ids[label])
                metadata.append((item["id"], label, len(prefix_ids), len(label_ids[label])))
        max_length = max(len(ids) for ids in expanded)
        input_ids, attention_masks, left_pads = [], [], []
        for ids in expanded:
            pad = max_length - len(ids)
            left_pads.append(pad)
            input_ids.append([tokenizer.pad_token_id] * pad + ids)
            attention_masks.append([0] * pad + [1] * len(ids))
        input_tensor = torch.tensor(input_ids, dtype=torch.long)
        mask_tensor = torch.tensor(attention_masks, dtype=torch.long)
        with torch.inference_mode():
            logits = model(input_ids=input_tensor, attention_mask=mask_tensor).logits
            log_probs = torch.log_softmax(logits, dim=-1)
        scores_by_item = {item["id"]: {} for item in batch}
        prompt_tokens = {}
        for row, ((item_id, label, prefix_length, label_length), pad) in enumerate(zip(metadata, left_pads)):
            candidate_ids = label_ids[label]
            score = 0.0
            candidate_start = pad + prefix_length
            for offset in range(label_length):
                score += float(log_probs[row, candidate_start + offset - 1, candidate_ids[offset]].item())
            scores_by_item[item_id][label] = score
            prompt_tokens[item_id] = prefix_length
        for item in batch:
            raw = torch.tensor([scores_by_item[item["id"]][label] for label in LABELS])
            probabilities = torch.softmax(raw, dim=0)
            decision = LABELS[int(torch.argmax(raw).item())]
            records.append({
                **item,
                "prompt_tokens_with_system": prompt_tokens[item["id"]],
                "decision": decision,
                "scores": {label: round(float(probabilities[index].item()), 8) for index, label in enumerate(LABELS)},
                "sequence_log_scores": {label: round(scores_by_item[item["id"]][label], 8) for label in LABELS},
                "log_score_margin": round(float(torch.abs(raw[0] - raw[1]).item()), 8),
            })
        print(json.dumps({"scored": min(start + batch_size, len(items)), "total": len(items)}), flush=True)
    return records


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6L inputs are not frozen")

    torch.set_num_threads(threads)
    model, tokenizer = BASE.load_model()
    started = time.monotonic()
    outputs = score_complete_labels(model, tokenizer, world["items"], batch_size)
    records = []
    for output in outputs:
        actual_semantic = output["mapping"][output["decision"]]
        records.append({
            **output,
            "actual_semantic": actual_semantic,
            "label_correct": output["decision"] == output["expected"],
            "semantic_correct": actual_semantic == output["expected_semantic"],
        })

    by_pair = {(record["case_id"], record["deck"]): record for record in records}
    pairs = []
    for case_id in sorted({record["case_id"] for record in records}):
        main, mirror = by_pair[(case_id, "MAIN")], by_pair[(case_id, "MIRROR")]
        pairs.append({
            "case_id": case_id,
            "main_label": main["decision"],
            "mirror_label": mirror["decision"],
            "label_flipped": main["decision"] != mirror["decision"],
            "main_semantic": main["actual_semantic"],
            "mirror_semantic": mirror["actual_semantic"],
            "semantic_preserved": main["actual_semantic"] == mirror["actual_semantic"],
        })

    deck_correct = {
        deck: sum(record["semantic_correct"] for record in records if record["deck"] == deck)
        for deck in ("MAIN", "MIRROR")
    }
    class_deck_correct = {
        f"{deck}_{meaning}": sum(
            record["semantic_correct"]
            for record in records
            if record["deck"] == deck and record["expected_semantic"] == meaning
        )
        for deck in ("MAIN", "MIRROR") for meaning in ("approve", "reject")
    }
    summary = {
        "semantic_correct": sum(record["semantic_correct"] for record in records),
        "total_prompts": 20,
        "deck_correct": deck_correct,
        "class_deck_correct": class_deck_correct,
        "minimum_class_correct_within_a_deck": min(class_deck_correct.values()),
        "label_choices": {label: sum(record["decision"] == label for record in records) for label in LABELS},
        "paired_label_flips": sum(pair["label_flipped"] for pair in pairs),
        "paired_semantics_preserved": sum(pair["semantic_preserved"] for pair in pairs),
        "total_pairs": 10,
        "min_prompt_words": min(record["prompt_words"] for record in records),
        "max_prompt_words": max(record["prompt_words"] for record in records),
        "min_prompt_tokens_with_system": min(record["prompt_tokens_with_system"] for record in records),
        "max_prompt_tokens_with_system": max(record["prompt_tokens_with_system"] for record in records),
    }
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6L",
        "status": "paired_synthetic_development_run_complete",
        "protocol": "/experiments/E007/nonce-word-protocol-v0.1.json",
        "world": "/experiments/E007/nonce-word-world-v0.1.json",
        "protocol_sha256": BASE.sha256_file(PROTOCOL_PATH),
        "world_sha256": BASE.sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": BASE.sha256_file(BASE.MODEL_FILE),
            "weights_changed": False,
        },
        "scoring": {"labels": {label: tokenizer.encode(label, add_special_tokens=False) for label in LABELS}, "method": "summed_complete_sequence_log_probability"},
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "locked_interpretation": interpretation(summary),
        "pairs": pairs,
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.batch_size, args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"interpretation": result["locked_interpretation"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
