from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from gate5b_model import ParallelTrackQwen
from train_gate5b_merger import load_adapter
from train_gate5b_tracks import sha256_file


CONDITIONS = (
    "shared_qwen_alone",
    "cause_track_alone",
    "safety_track_alone",
    "wrong_same_role_pair",
    "semantic_text_capsules",
    "correct_neural_pair",
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")
    return " ".join(re.findall(r"[\w]+", text, flags=re.UNICODE))


def score_answer(answer: str, row: dict) -> dict:
    actual = normalize(answer)
    cause = normalize(row["expected_cause"])
    safety = normalize(row["expected_safety"])
    cause_hit = cause in actual
    safety_hit = safety in actual
    return {"cause_hit": cause_hit, "safety_hit": safety_hit, "complete": cause_hit and safety_hit}


def prompt_for(tokenizer, row: dict, condition: str) -> list[int]:
    content = row["question"]
    if condition == "semantic_text_capsules":
        if row["language"] == "ru":
            content += f"\n\nДва pocket i передали проверенные наблюдения:\n- {row['expected_cause']}\n- {row['expected_safety']}\nДайте один короткий полный ответ обычным языком."
        else:
            content += f"\n\nTwo pocket i sent verified observations:\n- {row['expected_cause']}\n- {row['expected_safety']}\nGive one short complete answer in plain language."
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": content}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    return tokenizer.encode(text, add_special_tokens=False)


def mode_for(row: dict, condition: str) -> str:
    mode = {
        "shared_qwen_alone": "base",
        "cause_track_alone": "cause",
        "safety_track_alone": "safety",
        "semantic_text_capsules": "base",
        "correct_neural_pair": "correct",
    }.get(condition)
    if condition == "wrong_same_role_pair":
        number = int(row["id"].rsplit("-", 1)[-1])
        mode = "wrong_cause" if number % 2 == 0 else "wrong_safety"
    return mode


@torch.inference_mode()
def greedy_answers(model, tokenizer, rows: list[dict], condition: str, max_new_tokens: int) -> list[str]:
    prompts = [prompt_for(tokenizer, row, condition) for row in rows]
    width = max(map(len, prompts))
    pad_id = tokenizer.pad_token_id
    padded = [[pad_id] * (width - len(ids)) + ids for ids in prompts]
    masks = [[0] * (width - len(ids)) + [1] * len(ids) for ids in prompts]
    ids = torch.tensor(padded, dtype=torch.long)
    attention = torch.tensor(masks, dtype=torch.long)
    mode = mode_for(rows[0], condition)
    if any(mode_for(row, condition) != mode for row in rows):
        raise ValueError("one batch cannot mix neural modes")
    generated: list[list[int]] = [[] for _ in rows]
    finished = [False] * len(rows)
    for _ in range(max_new_tokens):
        output = model(input_ids=ids, attention_mask=attention, mode=mode)
        next_ids = output.logits[:, -1].argmax(dim=-1).tolist()
        for index, next_id in enumerate(next_ids):
            if finished[index]:
                next_ids[index] = tokenizer.eos_token_id
            elif next_id == tokenizer.eos_token_id:
                finished[index] = True
            else:
                generated[index].append(next_id)
        if all(finished):
            break
        ids = torch.cat((ids, torch.tensor(next_ids, dtype=torch.long).unsqueeze(1)), dim=1)
        attention = torch.cat((attention, torch.ones((len(rows), 1), dtype=attention.dtype)), dim=1)
    return [tokenizer.decode(tokens, skip_special_tokens=True).strip() for tokens in generated]


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    torch.manual_seed(24082026)
    design = json.loads(args.design.read_text(encoding="utf-8"))
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    merger_summary = json.loads((args.merger_dir / "summary.json").read_text(encoding="utf-8"))
    if design["status"] != "locked_not_run" or exam["status"] != "locked_not_run" or protocol["status"] != "locked_before_exam":
        raise ValueError("exam inputs are not locked")
    if merger_summary["status"] != "merger_trained_exam_not_run" or merger_summary["exam_run"]:
        raise ValueError("merger checkpoint is not ready")
    if tuple(design["conditions"]) != CONDITIONS:
        raise ValueError("condition order differs from frozen design")

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

    started = time.monotonic()
    records = []
    for condition in CONDITIONS:
        rows_by_mode: dict[str, list[dict]] = {}
        for row in exam["questions"]:
            rows_by_mode.setdefault(mode_for(row, condition), []).append(row)
        answer_by_id = {}
        for rows in rows_by_mode.values():
            for start in range(0, len(rows), args.batch_size):
                batch = rows[start : start + args.batch_size]
                answers = greedy_answers(model, tokenizer, batch, condition, args.max_new_tokens)
                answer_by_id.update(zip((row["id"] for row in batch), answers))
        for row in exam["questions"]:
            answer = answer_by_id[row["id"]]
            provisional = score_answer(answer, row)
            records.append({
                "question_id": row["id"], "language": row["language"], "condition": condition,
                "question": row["question"], "expected_cause": row["expected_cause"],
                "expected_safety": row["expected_safety"], "answer": answer,
                "automatic_score": provisional,
            })
            print(json.dumps({"condition": condition, "question": row["id"], **provisional}), flush=True)

    counts = {condition: sum(record["automatic_score"]["complete"] for record in records if record["condition"] == condition) for condition in CONDITIONS}
    rule = design["pass_rule"]
    best_single = max(counts["cause_track_alone"], counts["safety_track_alone"])
    gates = {
        "correct_pair_minimum": counts["correct_neural_pair"] >= rule["correct_neural_pair_at_least"],
        "base_maximum": counts["shared_qwen_alone"] <= rule["shared_qwen_alone_at_most"],
        "cause_single_maximum": counts["cause_track_alone"] <= rule["each_single_track_at_most"],
        "safety_single_maximum": counts["safety_track_alone"] <= rule["each_single_track_at_most"],
        "wrong_pair_maximum": counts["wrong_same_role_pair"] <= rule["wrong_pair_at_most"],
        "lead_over_best_single": counts["correct_neural_pair"] - best_single >= rule["correct_pair_lead_over_best_single_at_least"],
        "close_to_text_capsules": counts["semantic_text_capsules"] - counts["correct_neural_pair"] <= rule["correct_pair_may_trail_text_capsules_by_at_most"],
    }
    result = {
        "experiment_id": "E005",
        "gate": "5B",
        "kind": "locked_parallel_neural_track_exam",
        "status": "provisional_automatic_score_awaiting_human_review",
        "model_weights_sha256": sha256_file(args.model / "model.safetensors"),
        "max_new_tokens": args.max_new_tokens,
        "counts": counts,
        "gates": gates,
        "all_automatic_gates_passed": all(gates.values()),
        "automatic_score_warning": "String containment is provisional. Human review of every raw answer is required.",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--exam", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--track-dir", type=Path, required=True)
    parser.add_argument("--merger-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
