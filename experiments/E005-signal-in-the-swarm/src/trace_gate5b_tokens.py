from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from evaluate_gate5b import prompt_for
from gate5b_model import ParallelTrackQwen
from train_gate5b_merger import load_adapter
from train_gate5b_tracks import sha256_file


def sha256_json(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token_metrics(model: ParallelTrackQwen, output, row: int) -> dict[str, float]:
    base = output.base_middle[row, -1]
    cause = model.merger.clip(output.cause_delta[row, -1], base)
    safety = model.merger.clip(output.safety_delta[row, -1], base)
    gates = torch.sigmoid(model.merger.gate(torch.cat((base, cause, safety), dim=-1)))
    cause_contribution = gates[0] * cause * model.merger.cause_scale
    safety_contribution = gates[1] * safety * model.merger.safety_scale
    cosine = torch.nn.functional.cosine_similarity(cause.float(), safety.float(), dim=0)
    return {
        "cause_gate": round(float(gates[0]), 6),
        "safety_gate": round(float(gates[1]), 6),
        "cause_contribution_norm": round(float(torch.linalg.vector_norm(cause_contribution.float())), 6),
        "safety_contribution_norm": round(float(torch.linalg.vector_norm(safety_contribution.float())), 6),
        "delta_cosine_similarity": round(float(cosine), 6),
    }


@torch.inference_mode()
def trace_batch(model, tokenizer, rows: list[dict], max_new_tokens: int) -> list[dict]:
    prompts = [prompt_for(tokenizer, row, "correct_neural_pair") for row in rows]
    width = max(map(len, prompts))
    pad_id = tokenizer.pad_token_id
    ids = torch.tensor([[pad_id] * (width - len(prompt)) + prompt for prompt in prompts], dtype=torch.long)
    attention = torch.tensor([[0] * (width - len(prompt)) + [1] * len(prompt) for prompt in prompts], dtype=torch.long)
    traces = [{"token_ids": [], "tokens": []} for _ in rows]
    finished = [False] * len(rows)

    for step in range(max_new_tokens):
        output = model(input_ids=ids, attention_mask=attention, mode="correct")
        next_ids = output.logits[:, -1].argmax(dim=-1).tolist()
        for index, next_id in enumerate(next_ids):
            if finished[index]:
                next_ids[index] = tokenizer.eos_token_id
                continue
            metrics = token_metrics(model, output, index)
            if next_id == tokenizer.eos_token_id:
                traces[index]["tokens"].append({
                    "step": step + 1,
                    "token": "[STOP]",
                    "is_stop": True,
                    **metrics,
                })
                finished[index] = True
                continue
            traces[index]["token_ids"].append(next_id)
            traces[index]["tokens"].append({
                "step": step + 1,
                "token": tokenizer.decode([next_id], skip_special_tokens=False),
                "is_stop": False,
                **metrics,
            })
        if all(finished):
            break
        ids = torch.cat((ids, torch.tensor(next_ids, dtype=torch.long).unsqueeze(1)), dim=1)
        attention = torch.cat((attention, torch.ones((len(rows), 1), dtype=attention.dtype)), dim=1)

    for trace in traces:
        trace["answer"] = tokenizer.decode(trace.pop("token_ids"), skip_special_tokens=True).strip()
        trace["finished_naturally"] = bool(trace["tokens"] and trace["tokens"][-1]["is_stop"])
    return traces


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def summarize(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["language"]].extend(record["tokens"])
        groups["all"].extend(record["tokens"])
    summary = {}
    for language, tokens in groups.items():
        stop_tokens = [token for token in tokens if token.get("is_stop")]
        spoken_tokens = [token for token in tokens if not token.get("is_stop")]
        summary[language] = {
            "decision_tokens": len(tokens),
            "spoken_tokens": len(spoken_tokens),
            "stop_tokens": len(stop_tokens),
            "cause_gate_mean": mean([token["cause_gate"] for token in tokens]),
            "safety_gate_mean": mean([token["safety_gate"] for token in tokens]),
            "cause_contribution_norm_mean": mean([token["cause_contribution_norm"] for token in tokens]),
            "safety_contribution_norm_mean": mean([token["safety_contribution_norm"] for token in tokens]),
            "delta_cosine_similarity_mean": mean([token["delta_cosine_similarity"] for token in tokens]),
            "safety_gate_below_0_25_fraction": mean([
                1.0 if token["safety_gate"] < 0.25 else 0.0 for token in tokens
            ]),
            "cause_gate_on_stop_mean": mean([token["cause_gate"] for token in stop_tokens]),
            "safety_gate_on_stop_mean": mean([token["safety_gate"] for token in stop_tokens]),
            "cause_contribution_norm_on_stop_mean": mean([
                token["cause_contribution_norm"] for token in stop_tokens
            ]),
            "safety_contribution_norm_on_stop_mean": mean([
                token["safety_contribution_norm"] for token in stop_tokens
            ]),
        }
    return summary


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    torch.manual_seed(24082026)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    previous = json.loads(args.previous_results.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_run" or not protocol["frozen_inputs"]["weights_must_not_change"]:
        raise ValueError("Gate 5B.3 protocol is not locked")
    if len(exam["questions"]) != protocol["frozen_inputs"]["question_count"]:
        raise ValueError("locked question count changed")

    expected_answers = {
        record["question_id"]: record["answer"]
        for record in previous["records"]
        if record["condition"] == "correct_neural_pair"
    }
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
    questions = exam["questions"]
    for start in range(0, len(questions), args.batch_size):
        batch = questions[start : start + args.batch_size]
        traces = trace_batch(model, tokenizer, batch, args.max_new_tokens)
        for row, trace in zip(batch, traces):
            answer_matches = trace["answer"] == expected_answers.get(row["id"])
            if not answer_matches:
                raise RuntimeError(f"x-ray changed the frozen answer for {row['id']}")
            records.append({
                "question_id": row["id"],
                "language": row["language"],
                "question": row["question"],
                "expected_cause": row["expected_cause"],
                "expected_safety": row["expected_safety"],
                "answer": trace["answer"],
                "answer_matches_published_gate5b1": answer_matches,
                "finished_naturally": trace["finished_naturally"],
                "tokens": trace["tokens"],
            })
            print(json.dumps({"question": row["id"], "tokens": len(trace["tokens"]), "reproduced": answer_matches}), flush=True)

    result = {
        "experiment_id": "E005",
        "gate": "5B.3",
        "version": "0.1",
        "kind": "token_by_token_neural_track_xray",
        "status": "diagnostic_complete_no_training",
        "protocol_sha256": sha256_json(args.protocol),
        "model_weights_sha256": sha256_file(args.model / "model.safetensors"),
        "question_count": len(records),
        "all_answers_reproduced": all(row["answer_matches_published_gate5b1"] for row in records),
        "summary": summarize(records),
        "plain_result": {
            "en": "The x-ray records numerical influence, not hidden meaning. It shows whether the safety path is muted by the merger or remains present while the shared tail writes the wrong text.",
            "ru": "Рентген записывает числовое влияние, а не спрятанный смысл. Он показывает, заглушает ли мостик SAFETY‑трек или сигнал остаётся сильным, но общий конец модели пишет неправильный текст."
        },
        "claim_boundary": protocol["claim_boundary"],
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--exam", type=Path, required=True)
    parser.add_argument("--previous-results", type=Path, required=True)
    parser.add_argument("--track-dir", type=Path, required=True)
    parser.add_argument("--merger-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--threads", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
