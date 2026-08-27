#!/usr/bin/env python3
"""Run E007 Gate 3C.2: blind source reading by frozen Qwen 0.6B."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/blind-reader-protocol-v0.1.json"
MEMORY_PATH = ROOT / "site/experiments/E007/send-policy-memory-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/blind-reader-result-v0.1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prompt(question: str, source: str, english: bool) -> str:
    if english:
        return (
            "You are checking one source for one question. You have not seen another agent's answer. "
            "Use only SOURCE. Do not answer the question from your own knowledge. "
            "If SOURCE contains a passage that directly helps answer QUESTION, write FOUND on the first line and copy one exact continuous quote from SOURCE on the second line. "
            "If SOURCE does not help, write only NONE. Do not explain.\n\n"
            f"QUESTION:\n{question}\n\nSOURCE:\n{source}"
        )
    return (
        "Вы проверяете один источник для одного вопроса. Вы не видели ответ другого агента. "
        "Используйте только ИСТОЧНИК. Не отвечайте из собственных знаний. "
        "Если в ИСТОЧНИКЕ есть фрагмент, который прямо помогает ответить на ВОПРОС, напишите FOUND в первой строке и дословно скопируйте одну непрерывную цитату из ИСТОЧНИКА во второй строке. "
        "Если ИСТОЧНИК не помогает, напишите только NONE. Ничего не объясняйте.\n\n"
        f"ВОПРОС:\n{question}\n\nИСТОЧНИК:\n{source}"
    )


def exact_quote_from_output(output: str, source: str) -> str:
    if not output.strip().upper().startswith("FOUND"):
        return ""
    remainder = re.sub(r"^\s*FOUND\s*", "", output, count=1, flags=re.IGNORECASE).strip()
    candidates = [remainder.strip(" \t\n\r\"'«»`"), *[line.strip(" \t\n\r\"'«»`") for line in remainder.splitlines()]]
    exact = [candidate for candidate in candidates if len(candidate) >= 20 and candidate in source]
    if exact:
        return max(exact, key=len)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", source) if len(part.strip()) >= 20]
    copied = [sentence for sentence in sentences if sentence in output]
    return max(copied, key=len) if copied else ""


def classify(output: str, source: str) -> tuple[str, str]:
    clean = output.strip()
    if clean.upper() == "NONE":
        return "none", ""
    quote = exact_quote_from_output(clean, source)
    if quote:
        return "found_exact", quote
    return "malformed_or_invented", ""


def main(model_path: Path, threads: int, batch_size: int) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(threads)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    memory = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference":
        raise SystemExit("Blind-reader protocol is not locked")
    actual_hash = sha256_file(model_path / "model.safetensors")
    if actual_hash != protocol["model"]["weights_sha256"]:
        raise SystemExit("Model weights do not match the locked hash")
    questions = {item["id"]: item["question"] for item in memory["questions"]}
    sources = {item["id"]: item["text"] for items in memory["libraries"].values() for item in items}
    tasks = []
    for candidate in protocol["candidates"]:
        question = questions[candidate["question_id"]]
        source = sources[candidate["source_id"]]
        tasks.append({**candidate, "question": question, "source": source, "prompt": prompt(question, source, candidate["question_id"] == "S08")})
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    tokenizer.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True).eval()
    started = time.monotonic()
    records = []
    for start in range(0, len(tasks), batch_size):
        batch = tasks[start:start + batch_size]
        prompts = [tokenizer.apply_chat_template(
            [{"role": "user", "content": task["prompt"]}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        ) for task in batch]
        encoded = tokenizer(prompts, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            outputs = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=protocol["model"]["max_new_tokens"],
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
            )
        prompt_width = encoded["input_ids"].shape[1]
        for task, output_tokens in zip(batch, outputs):
            generated = output_tokens[prompt_width:].tolist()
            raw = tokenizer.decode(generated, skip_special_tokens=True).strip()
            decision, quote = classify(raw, task["source"])
            expected_found = task["expected"] == "useful"
            correct = (expected_found and decision == "found_exact") or (not expected_found and decision == "none")
            records.append({
                "id": task["id"],
                "question_id": task["question_id"],
                "card_id": task["card_id"],
                "source_id": task["source_id"],
                "expected": task["expected"],
                "question": task["question"],
                "source": task["source"],
                "raw_output": raw,
                "decision": decision,
                "exact_quote": quote,
                "correct": correct,
                "generated_tokens": len(generated),
                "hit_token_limit": len(generated) >= protocol["model"]["max_new_tokens"] and tokenizer.eos_token_id not in generated,
            })
        print(json.dumps({"answered": min(start + batch_size, len(tasks)), "total": len(tasks)}), flush=True)
    useful = [record for record in records if record["expected"] == "useful"]
    extras = [record for record in records if record["expected"] == "extra"]
    summary = {
        "useful_quotes_found": sum(record["decision"] == "found_exact" for record in useful),
        "useful_total": len(useful),
        "extra_sources_rejected": sum(record["decision"] == "none" for record in extras),
        "extra_total": len(extras),
        "invented_or_malformed": sum(record["decision"] == "malformed_or_invented" for record in records),
        "hit_token_limit": sum(record["hit_token_limit"] for record in records),
    }
    passed = summary["useful_quotes_found"] >= 7 and summary["extra_sources_rejected"] >= 7 and summary["invented_or_malformed"] == 0
    result = {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.2",
        "status": "development_run_complete",
        "protocol": "/experiments/E007/blind-reader-protocol-v0.1.json",
        "model": protocol["model"],
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "passed_locked_gate": passed,
        "records": records,
        "boundary": "Automatic scoring checks exact copying and NONE decisions. Semantic owner review remains required."
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "passed_locked_gate": passed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    main(args.model, args.threads, args.batch_size)
