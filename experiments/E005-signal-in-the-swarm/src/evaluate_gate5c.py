from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from safetensors.torch import load_file
from transformers import AutoModelForCausalLM, AutoTokenizer

from evaluate_gate5b import score_answer
from gate5c_model import SHELF_MODES, SeparateShelfQwen
from train_gate5b_merger import load_adapter, tensor_digest
from train_gate5b_tracks import sha256_file


CONDITIONS = (
    "old_additive_merger",
    "separate_shelves_correct_pair",
    "cause_shelf_only",
    "safety_shelf_only",
    "two_cause_shelves",
    "two_safety_shelves",
    "swapped_shelves",
    "empty_shelves",
)

SHELF_CONDITIONS = {
    "separate_shelves_correct_pair": "correct_shelves",
    "cause_shelf_only": "cause_only",
    "safety_shelf_only": "safety_only",
    "two_cause_shelves": "two_cause",
    "two_safety_shelves": "two_safety",
    "swapped_shelves": "swapped",
    "empty_shelves": "empty",
}


def load_shelf_reader(model: SeparateShelfQwen, path: Path) -> str:
    saved = load_file(str(path), device="cpu")
    expected = model.shelf_state()
    if set(saved) != set(expected):
        raise ValueError("shelf reader keys differ")
    current = model.state_dict()
    with torch.no_grad():
        for name, tensor in saved.items():
            if current[name].shape != tensor.shape:
                raise ValueError(f"shelf reader shape differs for {name}")
            current[name].copy_(tensor)
    loaded = model.shelf_state()
    if not all(torch.equal(saved[name], loaded[name]) for name in saved):
        raise RuntimeError("shelf reader did not load exactly")
    return tensor_digest(loaded)


def prompt_for(tokenizer, row: dict) -> list[int]:
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": row["question"]}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    return tokenizer.encode(text, add_special_tokens=False)


@torch.inference_mode()
def greedy_answers(model, tokenizer, rows: list[dict], mode: str, max_new_tokens: int) -> list[dict]:
    if mode not in SHELF_MODES:
        raise ValueError(f"unknown shelf mode: {mode}")
    prompts = [prompt_for(tokenizer, row) for row in rows]
    width = max(map(len, prompts))
    pad_id = tokenizer.pad_token_id
    padded = [ids + [pad_id] * (width - len(ids)) for ids in prompts]
    masks = [[1] * len(ids) + [0] * (width - len(ids)) for ids in prompts]
    ids = torch.tensor(padded, dtype=torch.long)
    attention = torch.tensor(masks, dtype=torch.long)
    generated: list[list[int]] = [[] for _ in rows]
    finished = [False] * len(rows)
    for _ in range(max_new_tokens):
        output = model.forward_shelves(ids, attention, mode=mode)
        next_ids = output.next_logits.argmax(dim=-1).tolist()
        for index, next_id in enumerate(next_ids):
            if finished[index]:
                next_ids[index] = pad_id
            elif next_id == tokenizer.eos_token_id:
                finished[index] = True
            else:
                generated[index].append(next_id)
        if all(finished):
            break
        ids = torch.cat((ids, torch.tensor(next_ids, dtype=torch.long).unsqueeze(1)), dim=1)
        attention = torch.cat(
            (attention, torch.tensor([[0 if done else 1] for done in finished], dtype=attention.dtype)),
            dim=1,
        )
    return [
        {
            "answer": tokenizer.decode(tokens, skip_special_tokens=True).strip(),
            "generated_tokens": len(tokens),
            "reached_ceiling": not finished[index],
        }
        for index, tokens in enumerate(generated)
    ]


def old_additive_records(old_result: dict) -> list[dict]:
    return [
        {**record, "condition": "old_additive_merger", "source_condition": "correct_neural_pair"}
        for record in old_result["records"]
        if record["condition"] == "correct_neural_pair"
    ]


def write_checkpoint(args: argparse.Namespace, records: list[dict], *, status: str, metadata: dict) -> None:
    payload = {
        "experiment_id": "E005",
        "gate": "5C",
        "version": "1.0.1",
        "kind": "locked_separate_shelf_exam",
        "status": status,
        **metadata,
        "records_completed": len(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    torch.manual_seed(25082026)
    design = json.loads(args.design.read_text(encoding="utf-8"))
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    training = json.loads(args.training_summary.read_text(encoding="utf-8"))
    old_result = json.loads(args.old_result.read_text(encoding="utf-8"))
    if design["status"] != "locked_before_training" or design["exam_run"]:
        raise ValueError("Gate 5C design is not locked")
    if training["status"] != "reader_trained_exam_not_run" or training["exam_run"]:
        raise ValueError("shelf reader is not ready for its first exam")
    if exam["status"] != "locked_not_run" or tuple(design["conditions"]) != CONDITIONS:
        raise ValueError("exam or condition order differs from the frozen design")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True
    ).eval()
    model = SeparateShelfQwen(base).eval()
    cause_digest = load_adapter(model, "cause", args.track_dir / "cause_track.safetensors")
    safety_digest = load_adapter(model, "safety", args.track_dir / "safety_track.safetensors")
    load_adapter(model, "merger", args.merger_dir / "merger.safetensors")
    shelf_digest = load_shelf_reader(model, args.reader_dir / "shelf_reader.safetensors")
    if cause_digest != training["cause_adapter_digest"] or safety_digest != training["safety_adapter_digest"]:
        raise ValueError("personal track hashes differ from training checkpoint")
    if sha256_file(args.model / "model.safetensors") != training["model_weights_sha256"]:
        raise ValueError("base model hash differs from training checkpoint")

    started = time.monotonic()
    metadata = {
        "model_weights_sha256": training["model_weights_sha256"],
        "cause_adapter_digest": cause_digest,
        "safety_adapter_digest": safety_digest,
        "shelf_reader_digest": shelf_digest,
        "old_additive_source": "/experiments/E005/gate-5b1-results-v0.1.json",
        "max_new_tokens": args.max_new_tokens,
        "batch_size": args.batch_size,
    }
    if args.output.exists():
        checkpoint = json.loads(args.output.read_text(encoding="utf-8"))
        if checkpoint.get("status") not in {"running_intermediate_not_result", "paused_for_reserved_compute_window"}:
            raise ValueError("existing output is not a resumable Gate 5C checkpoint")
        for key, value in metadata.items():
            if checkpoint.get(key) != value:
                raise ValueError(f"resume metadata differs for {key}")
        records = checkpoint["records"]
    else:
        records = old_additive_records(old_result)
        write_checkpoint(args, records, status="running_intermediate_not_result", metadata=metadata)
    completed = {(record["condition"], record["question_id"]) for record in records}
    for condition, mode in SHELF_CONDITIONS.items():
        for start in range(0, len(exam["questions"]), args.batch_size):
            rows = [
                row for row in exam["questions"][start : start + args.batch_size]
                if (condition, row["id"]) not in completed
            ]
            if not rows:
                continue
            outputs = greedy_answers(model, tokenizer, rows, mode, args.max_new_tokens)
            for row, output in zip(rows, outputs):
                provisional = score_answer(output["answer"], row)
                record = {
                    "question_id": row["id"],
                    "language": row["language"],
                    "condition": condition,
                    "question": row["question"],
                    "expected_cause": row["expected_cause"],
                    "expected_safety": row["expected_safety"],
                    **output,
                    "automatic_score": provisional,
                }
                records.append(record)
                completed.add((condition, row["id"]))
                print(json.dumps({"condition": condition, "question": row["id"], **provisional}), flush=True)
            write_checkpoint(args, records, status="running_intermediate_not_result", metadata=metadata)

    counts = {
        condition: sum(record["automatic_score"]["complete"] for record in records if record["condition"] == condition)
        for condition in CONDITIONS
    }
    rule = design["provisional_literal_pass_rule"]
    controls = [
        "cause_shelf_only", "safety_shelf_only", "two_cause_shelves",
        "two_safety_shelves", "swapped_shelves", "empty_shelves",
    ]
    best_control = max(counts[condition] for condition in controls)
    gates = {
        "correct_pair_minimum": counts["separate_shelves_correct_pair"] >= rule["correct_pair_at_least"],
        "every_control_maximum": all(counts[condition] <= rule["each_missing_or_duplicate_control_at_most"] for condition in controls),
        "lead_over_best_control": counts["separate_shelves_correct_pair"] - best_control >= rule["lead_over_best_missing_or_duplicate_control_at_least"],
    }
    result = {
        "experiment_id": "E005",
        "gate": "5C",
        "version": "1.0.1",
        "kind": "locked_separate_shelf_exam",
        "status": "provisional_literal_score_awaiting_semantic_and_owner_review",
        **metadata,
        "counts": counts,
        "gates": gates,
        "all_provisional_literal_gates_passed": all(gates.values()),
        "automatic_score_warning": "Exact sentence matching is only an alarm. Paraphrases can be falsely marked wrong; every raw answer requires semantic and owner review.",
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "records": records,
    }
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--exam", type=Path, required=True)
    parser.add_argument("--training-summary", type=Path, required=True)
    parser.add_argument("--old-result", type=Path, required=True)
    parser.add_argument("--track-dir", type=Path, required=True)
    parser.add_argument("--merger-dir", type=Path, required=True)
    parser.add_argument("--reader-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--threads", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
