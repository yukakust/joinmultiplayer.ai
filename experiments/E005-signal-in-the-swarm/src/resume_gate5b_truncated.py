from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from evaluate_gate5b import CONDITIONS, greedy_answers, mode_for, score_answer
from gate5b_model import ParallelTrackQwen
from train_gate5b_merger import load_adapter


def token_count(tokenizer, answer: str) -> int:
    return len(tokenizer.encode(answer, add_special_tokens=False))


def is_cut_off(tokenizer, record: dict, old_ceiling: int) -> bool:
    return token_count(tokenizer, record["answer"]) >= old_ceiling


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    source = json.loads(args.source.read_text(encoding="utf-8"))
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if source["max_new_tokens"] != 40 or protocol["status"] != "locked_before_correction":
        raise ValueError("Gate 5B.1 inputs are not the frozen correction")
    if protocol["emergency_ceiling"] != args.max_new_tokens or protocol["batch_size"] != args.batch_size:
        raise ValueError("runtime differs from the frozen correction protocol")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    tokenizer.padding_side = "left"
    base = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True
    ).eval()
    model = ParallelTrackQwen(base).eval()
    load_adapter(model, "cause", args.track_dir / "cause_track.safetensors")
    load_adapter(model, "safety", args.track_dir / "safety_track.safetensors")
    load_adapter(model, "merger", args.merger_dir / "merger.safetensors")

    result = copy.deepcopy(source)
    source_by_key = {(record["condition"], record["question_id"]): record for record in source["records"]}
    result_by_key = {(record["condition"], record["question_id"]): record for record in result["records"]}
    questions = exam["questions"]
    cut_keys = {
        key for key, record in source_by_key.items()
        if is_cut_off(tokenizer, record, source["max_new_tokens"])
    }
    rerun_batches = 0
    extended = 0
    for condition in CONDITIONS:
        rows_by_mode: dict[str, list[dict]] = {}
        for row in questions:
            rows_by_mode.setdefault(mode_for(row, condition), []).append(row)
        for rows in rows_by_mode.values():
            for start in range(0, len(rows), args.batch_size):
                batch = rows[start : start + args.batch_size]
                if not any((condition, row["id"]) in cut_keys for row in batch):
                    continue
                answers = greedy_answers(model, tokenizer, batch, condition, args.max_new_tokens)
                rerun_batches += 1
                for row, answer in zip(batch, answers):
                    key = (condition, row["id"])
                    if key not in cut_keys:
                        continue
                    old = source_by_key[key]["answer"]
                    if not answer.startswith(old):
                        raise RuntimeError(f"corrected answer changed its frozen prefix: {condition}/{row['id']}")
                    record = result_by_key[key]
                    record["original_cut_off_answer"] = old
                    record["answer"] = answer
                    record["automatic_score"] = score_answer(answer, row)
                    record["decoding_correction"] = {
                        "old_tokens": token_count(tokenizer, old),
                        "new_tokens": token_count(tokenizer, answer),
                        "reached_emergency_ceiling": token_count(tokenizer, answer) >= args.max_new_tokens,
                    }
                    extended += answer != old
                print(json.dumps({"condition": condition, "batch": rerun_batches, "extended_so_far": extended}), flush=True)

    counts = {
        condition: sum(record["automatic_score"]["complete"] for record in result["records"] if record["condition"] == condition)
        for condition in CONDITIONS
    }
    result["gate"] = "5B.1"
    result["kind"] = "locked_parallel_neural_track_exam_decoding_correction"
    result["status"] = "provisional_automatic_score_awaiting_human_review"
    result["max_new_tokens"] = args.max_new_tokens
    result["counts"] = counts
    result["decoding_correction"] = {
        "source_result": args.source.name,
        "cut_off_records": len(cut_keys),
        "rerun_batches": rerun_batches,
        "answers_extended": extended,
        "weights_changed": False,
        "questions_changed": False,
        "pass_rule_changed": False,
    }
    result["automatic_score_warning"] = "Phrase containment is not semantic review. A paraphrase may be correct even when this score is false."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--exam", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--track-dir", type=Path, required=True)
    parser.add_argument("--merger-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--threads", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
