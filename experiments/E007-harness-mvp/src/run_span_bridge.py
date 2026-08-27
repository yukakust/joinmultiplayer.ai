#!/usr/bin/env python3
"""Run E007 Gate 3C.3: span selection followed by a blind relevance bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/span-bridge-protocol-v0.1.json"
PAIR_PATH = ROOT / "site/experiments/E007/blind-reader-protocol-v0.1.json"
MEMORY_PATH = ROOT / "site/experiments/E007/send-policy-memory-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/span-bridge-result-v0.1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_spans(source: str) -> list[str]:
    spans = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source.strip()) if part.strip()]
    return spans or [source.strip()]


def selector_prompt(question: str, spans: list[str], english: bool) -> str:
    rendered = "\n".join(f"[S{index}] {span}" for index, span in enumerate(spans, 1))
    if english:
        return (
            "Use only the numbered source spans. Which ONE span directly helps answer QUESTION? "
            "Return only its ID, for example S2. If none helps, return only NONE. Do not answer the question and do not copy the span.\n\n"
            f"QUESTION:\n{question}\n\nSOURCE SPANS:\n{rendered}"
        )
    return (
        "Используйте только пронумерованные фрагменты источника. Какой ОДИН фрагмент прямо помогает ответить на ВОПРОС? "
        "Верните только его ID, например S2. Если ни один не помогает, верните только NONE. Не отвечайте на вопрос и не копируйте фрагмент.\n\n"
        f"ВОПРОС:\n{question}\n\nФРАГМЕНТЫ ИСТОЧНИКА:\n{rendered}"
    )


def bridge_prompt(question: str, span: str, english: bool) -> str:
    if english:
        return (
            "Decide whether SPAN directly helps answer QUESTION. First state in a few words what QUESTION needs. "
            "Then state in a few words what SPAN says. Finish with exactly one decision: HELPFUL, NOT_HELPFUL, or UNCLEAR. "
            "Use only the supplied text.\n\n"
            f"QUESTION:\n{question}\n\nSPAN:\n{span}\n\n"
            "NEED:\nSPAN_SAYS:\nDECISION:"
        )
    return (
        "Решите, помогает ли ФРАГМЕНТ прямо ответить на ВОПРОС. Сначала коротко напишите, что нужно узнать из ВОПРОСА. "
        "Затем коротко напишите, что сообщает ФРАГМЕНТ. Закончите ровно одним решением: HELPFUL, NOT_HELPFUL или UNCLEAR. "
        "Используйте только данный текст.\n\n"
        f"ВОПРОС:\n{question}\n\nФРАГМЕНТ:\n{span}\n\n"
        "NEED:\nSPAN_SAYS:\nDECISION:"
    )


def parse_selector(output: str, span_count: int) -> tuple[str, int | None]:
    clean = output.strip().upper().strip(" .!,:;\n\t")
    if clean == "NONE":
        return "none", None
    match = re.fullmatch(r"\[?S(\d+)\]?", clean)
    if match and 1 <= int(match.group(1)) <= span_count:
        return "selected", int(match.group(1)) - 1
    return "malformed", None


def parse_bridge(output: str) -> str:
    matches = re.findall(r"\b(NOT_HELPFUL|HELPFUL|UNCLEAR)\b", output.upper())
    return matches[-1] if matches else "MALFORMED"


def generate(model, tokenizer, prompts: list[str], max_new_tokens: int, batch_size: int) -> list[dict]:
    import torch

    results = []
    tokenizer.padding_side = "left"
    for start in range(0, len(prompts), batch_size):
        selected = prompts[start:start + batch_size]
        rendered = [tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False,
        ) for prompt in selected]
        encoded = tokenizer(rendered, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            outputs = model.generate(
                **encoded, do_sample=False, max_new_tokens=max_new_tokens,
                eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id,
            )
        width = encoded["input_ids"].shape[1]
        for output in outputs:
            token_ids = output[width:].tolist()
            results.append({
                "raw": tokenizer.decode(token_ids, skip_special_tokens=True).strip(),
                "tokens": len(token_ids),
                "hit_limit": len(token_ids) >= max_new_tokens and tokenizer.eos_token_id not in token_ids,
            })
    return results


def main(model_path: Path, threads: int, batch_size: int) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(threads)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    pairs = json.loads(PAIR_PATH.read_text(encoding="utf-8"))
    memory = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference":
        raise SystemExit("Span-bridge protocol is not locked")
    if sha256_file(model_path / "model.safetensors") != protocol["model"]["weights_sha256"]:
        raise SystemExit("Model hash does not match locked protocol")
    questions = {item["id"]: item["question"] for item in memory["questions"]}
    sources = {item["id"]: item["text"] for items in memory["libraries"].values() for item in items}
    tasks = []
    for pair in pairs["candidates"]:
        question = questions[pair["question_id"]]
        source = sources[pair["source_id"]]
        spans = split_spans(source)
        english = pair["question_id"] == "S08"
        tasks.append({**pair, "question": question, "source": source, "spans": spans, "english": english})
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True).eval()
    started = time.monotonic()
    selector_outputs = generate(model, tokenizer, [selector_prompt(task["question"], task["spans"], task["english"]) for task in tasks], 32, batch_size)
    bridge_jobs = []
    records = []
    for task, generated in zip(tasks, selector_outputs):
        selector_state, span_index = parse_selector(generated["raw"], len(task["spans"]))
        record = {
            "id": task["id"], "question_id": task["question_id"], "card_id": task["card_id"],
            "source_id": task["source_id"], "expected": task["expected"], "question": task["question"],
            "source": task["source"], "spans": task["spans"], "selector_raw": generated["raw"],
            "selector_state": selector_state, "selected_span_id": f"S{span_index + 1}" if span_index is not None else "",
            "selected_span": task["spans"][span_index] if span_index is not None else "",
            "bridge_raw": "", "bridge_decision": "NOT_RUN",
        }
        records.append(record)
        if span_index is not None:
            bridge_jobs.append((len(records) - 1, bridge_prompt(task["question"], task["spans"][span_index], task["english"])))
    bridge_outputs = generate(model, tokenizer, [job[1] for job in bridge_jobs], 128, batch_size)
    for (record_index, _), generated in zip(bridge_jobs, bridge_outputs):
        records[record_index]["bridge_raw"] = generated["raw"]
        records[record_index]["bridge_decision"] = parse_bridge(generated["raw"])
    for record in records:
        record["selector_accepts"] = record["selector_state"] == "selected"
        record["bridge_accepts"] = record["selector_accepts"] and record["bridge_decision"] == "HELPFUL"
        expected_accept = record["expected"] == "useful"
        record["selector_correct"] = record["selector_accepts"] == expected_accept
        record["bridge_correct"] = record["bridge_accepts"] == expected_accept
    def summary(key: str) -> dict:
        useful = [record for record in records if record["expected"] == "useful"]
        extras = [record for record in records if record["expected"] == "extra"]
        return {
            "useful_accepted": sum(record[key] for record in useful),
            "useful_total": 8,
            "extras_rejected": sum(not record[key] for record in extras),
            "extra_total": 8,
            "correct": sum(record[key] == (record["expected"] == "useful") for record in records),
            "total": 16,
        }
    selector_summary = summary("selector_accepts")
    bridge_summary = summary("bridge_accepts")
    selector_format_failures = sum(record["selector_state"] == "malformed" for record in records)
    bridge_format_failures = sum(record["bridge_decision"] == "MALFORMED" for record in records if record["selector_accepts"])
    br10 = next(record for record in records if record["id"] == "BR10")
    passed = (
        bridge_summary["useful_accepted"] >= 7 and bridge_summary["extras_rejected"] >= 7
        and not br10["bridge_accepts"] and selector_format_failures == 0 and bridge_format_failures == 0
    )
    result = {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "3C.3",
        "status": "development_ab_complete", "protocol": "/experiments/E007/span-bridge-protocol-v0.1.json",
        "model": protocol["model"], "runtime_seconds": round(time.monotonic() - started, 3),
        "selector_only": selector_summary, "selector_plus_bridge": bridge_summary,
        "selector_format_failures": selector_format_failures, "bridge_format_failures": bridge_format_failures,
        "br10_rejected": not br10["bridge_accepts"], "passed_locked_gate": passed, "records": records,
        "boundary": "Controlled development A/B on previously inspected pairs; a new held-out replication is required."
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("selector_only", "selector_plus_bridge", "selector_format_failures", "bridge_format_failures", "br10_rejected", "passed_locked_gate")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    main(args.model, args.threads, args.batch_size)
