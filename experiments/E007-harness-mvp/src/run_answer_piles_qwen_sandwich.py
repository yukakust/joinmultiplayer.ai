#!/usr/bin/env python3
"""Run E007 Gate 13D: DeBERTa → Qwen canonicalizer → DeBERTa."""

from __future__ import annotations

import hashlib
import itertools
import json
import resource
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/answer-piles-qwen-sandwich-protocol-v0.1.json"
SOURCE_PATH = ROOT / "site/experiments/E007/answer-piles-second-pass-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/answer-piles-qwen-sandwich-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_user_prompt(pile: dict) -> str:
    statements = "\n".join(f"- {text}" for text in pile["answers"])
    return f"STATEMENTS IN ONE PILE:\n{statements}\n\nONE ATOMIC CLAIM:"


def pair_key(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right)))


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


def generate_canonicals(model, tokenizer, piles: list[dict], spec: dict, batch_size: int = 4) -> list[dict]:
    prompts = []
    for pile in piles:
        user = make_user_prompt(pile)
        rendered = tokenizer.apply_chat_template(
            [{"role": "system", "content": spec["system"]}, {"role": "user", "content": user}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        prompts.append((pile, user, rendered))

    records = []
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        encoded = tokenizer(
            [item[2] for item in batch],
            padding=True,
            return_tensors="pt",
        )
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            output = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=spec["max_new_tokens"],
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
            )
        for item, row in zip(batch, output):
            generated = row[input_length:]
            text = tokenizer.decode(generated, skip_special_tokens=True).strip()
            records.append({
                "pile_id": item[0]["pile_id"],
                "original_answers": item[0]["answers"],
                "user_prompt": item[1],
                "canonical_claim": text,
                "generated_tokens": int(len(generated)),
                "hit_token_limit": len(generated) >= spec["max_new_tokens"] and tokenizer.eos_token_id not in generated,
            })
    return records


def score_nli(model, tokenizer, jobs: list[dict], batch_size: int = 16) -> list[dict]:
    records = []
    for start in range(0, len(jobs), batch_size):
        batch = jobs[start : start + batch_size]
        encoded = tokenizer(
            [job["premise"] for job in batch],
            [job["hypothesis"] for job in batch],
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
            records.append({
                **job,
                "decision": max(scores, key=scores.get),
                "probabilities": scores,
                "input_tokens": int(tokens),
            })
    return records


def main() -> None:
    protocol, source = read(PROTOCOL_PATH), read(SOURCE_PATH)
    if digest(SOURCE_PATH) != protocol["source"]["sha256"]:
        raise RuntimeError("Frozen source pile file changed")
    started = time.perf_counter()

    qspec = protocol["qwen"]
    qtokenizer = AutoTokenizer.from_pretrained(qspec["repository"], revision=qspec["revision"])
    qmodel = AutoModelForCausalLM.from_pretrained(
        qspec["repository"], revision=qspec["revision"], dtype=torch.bfloat16
    )
    qmodel.eval()
    canonical_records = generate_canonicals(qmodel, qtokenizer, source["piles"], qspec)
    del qmodel

    dspec = protocol["deberta"]
    dtokenizer = AutoTokenizer.from_pretrained(dspec["repository"], revision=dspec["revision"])
    dmodel = AutoModelForSequenceClassification.from_pretrained(
        dspec["repository"], revision=dspec["revision"], dtype=torch.float32
    )
    dmodel.eval()

    validation_jobs = []
    for record in canonical_records:
        for index, original in enumerate(record["original_answers"]):
            validation_jobs.append({
                "pile_id": record["pile_id"], "original_index": index,
                "direction": "original_to_canonical", "premise": original,
                "hypothesis": record["canonical_claim"],
            })
            validation_jobs.append({
                "pile_id": record["pile_id"], "original_index": index,
                "direction": "canonical_to_original", "premise": record["canonical_claim"],
                "hypothesis": original,
            })
    validation_records = score_nli(dmodel, dtokenizer, validation_jobs)
    for canonical in canonical_records:
        checks = [record for record in validation_records if record["pile_id"] == canonical["pile_id"]]
        canonical["validation"] = checks
        canonical["valid"] = bool(canonical["canonical_claim"]) and not canonical["hit_token_limit"] and all(
            check["decision"] == "entailment" for check in checks
        )

    valid = [record for record in canonical_records if record["valid"]]
    comparison_jobs = []
    for left, right in itertools.combinations(valid, 2):
        comparison_jobs.append({
            "left_pile": left["pile_id"], "right_pile": right["pile_id"],
            "direction": "left_to_right", "premise": left["canonical_claim"],
            "hypothesis": right["canonical_claim"],
        })
        comparison_jobs.append({
            "left_pile": left["pile_id"], "right_pile": right["pile_id"],
            "direction": "right_to_left", "premise": right["canonical_claim"],
            "hypothesis": left["canonical_claim"],
        })
    comparison_directions = score_nli(dmodel, dtokenizer, comparison_jobs)
    comparison_records = []
    for index in range(0, len(comparison_directions), 2):
        forward, reverse = comparison_directions[index], comparison_directions[index + 1]
        merge = forward["decision"] == "entailment" and reverse["decision"] == "entailment"
        comparison_records.append({
            "left_pile": forward["left_pile"],
            "right_pile": forward["right_pile"],
            "left_to_right": forward,
            "right_to_left": reverse,
            "merge": merge,
        })

    expected = {pair_key(*pair) for pair in protocol["source"]["expected_merges"]}
    predicted = {
        pair_key(record["left_pile"], record["right_pile"])
        for record in comparison_records if record["merge"]
    }
    raw_groups = components([pile["pile_id"] for pile in source["piles"]], predicted)
    pile_by_id = {pile["pile_id"]: pile for pile in source["piles"]}
    final_groups = []
    forbidden = 0
    for index, pile_ids in enumerate(raw_groups, 1):
        piles = [pile_by_id[pile_id] for pile_id in pile_ids]
        gold_piles = sorted({gold for pile in piles for gold in pile["gold_piles"]})
        answers = [answer for pile in piles for answer in pile["answers"]]
        final_groups.append({
            "group_id": f"Q{index:02d}", "source_piles": pile_ids,
            "gold_piles": gold_piles, "answers": answers,
        })
        forbidden += sum(
            int(left in gold_piles and right in gold_piles)
            for left, right in source["forbidden_gold_merges"]
        )
    exact = sum(
        any(group["gold_piles"] == [gold] and len(group["answers"]) == 2 for group in final_groups)
        for gold in ["G1", "G2", "G3", "G4", "G5", "G6"]
    )
    lost = sum(len(pile["answers"]) for pile in source["piles"]) - sum(len(group["answers"]) for group in final_groups)
    recovered = len(expected & predicted)
    false_merges = len(predicted - expected)
    gate = protocol["locked_development_gate"]
    summary = {
        "input_piles": len(source["piles"]),
        "valid_canonical_claims": sum(record["valid"] for record in canonical_records),
        "expected_merges_recovered": recovered,
        "expected_merges_total": len(expected),
        "false_merges": false_merges,
        "missed_expected_merges": len(expected - predicted),
        "final_groups": len(final_groups),
        "final_exact_paraphrase_piles": exact,
        "final_forbidden_merges": forbidden,
        "lost_answers": lost,
    }
    summary["passed_locked_development_gate"] = (
        summary["valid_canonical_claims"] == gate["valid_canonical_claims"]
        and recovered == gate["expected_merges_recovered"]
        and false_merges == gate["false_merges"]
        and exact == gate["final_exact_paraphrase_piles"]
        and forbidden == gate["final_forbidden_merges"]
        and lost == gate["lost_answers"]
    )
    result = {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "13D",
        "status": "posthoc_qwen_sandwich_development_complete",
        "protocol": "/experiments/E007/answer-piles-qwen-sandwich-protocol-v0.1.json",
        "source": protocol["source"]["piles"],
        "protocol_sha256": digest(PROTOCOL_PATH), "source_sha256": digest(SOURCE_PATH),
        "qwen": qspec, "deberta": dspec,
        "runtime": {
            "seconds_including_model_load": round(time.perf_counter() - started, 3),
            "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "device": "cpu",
        },
        "summary": summary,
        "canonical_records": canonical_records,
        "comparison_records": comparison_records,
        "predicted_merge_pairs": sorted(predicted),
        "missed_merge_pairs": sorted(expected - predicted),
        "false_merge_pairs": sorted(predicted - expected),
        "final_groups": final_groups,
        "boundary": protocol["boundary"],
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
