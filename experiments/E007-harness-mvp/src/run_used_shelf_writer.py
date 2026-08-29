#!/usr/bin/env python3
"""Run locked E007 Gate 15F writer on the USED shelf only."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/used-shelf-writer-protocol-v0.1.json"
SOURCE_PATH = ROOT / "site/experiments/E007/evidence-ledger-result-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/used-shelf-writer-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def cases(source: dict) -> list[dict]:
    by_question: dict[str, list[dict]] = {}
    for item in source["ledger"]:
        if item["shelf"] == "USED":
            by_question.setdefault(item["question_id"], []).append(item)
    return [{
        "id": item["id"],
        "question": item["question"],
        "used": [{
            "source_id": record["source_id"],
            "lineage_id": record["lineage_id"],
            "fragment": record["claim_evidence"],
            "conditional": record["conditional"],
        } for record in by_question[item["id"]]],
    } for item in source["questions"]]


def prompt(spec: dict, case: dict) -> str:
    fragments = "\n".join(f"[{item['source_id']}] {item['fragment']}" for item in case["used"])
    return f"{spec['instruction']}\n\nQUESTION\n{case['question']}\n\nUSED SHELF\n{fragments}"


def parse_answer(raw: str, allowed: set[str]) -> tuple[dict | None, str | None]:
    try:
        value = json.loads(raw.strip())
    except (json.JSONDecodeError, TypeError):
        return None, "not_one_json_object"
    if set(value) != {"answer", "evidence_ids"} or not isinstance(value["answer"], str) or not isinstance(value["evidence_ids"], list):
        return None, "wrong_json_shape"
    if any(not isinstance(item, str) for item in value["evidence_ids"]) or not set(value["evidence_ids"]) <= allowed:
        return None, "invalid_evidence_ids"
    return value, None


def run(args: argparse.Namespace) -> dict:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol, source = read(args.protocol), read(args.source)
    if protocol["status"] != "locked_before_inference" or digest(args.source) != protocol["source"]["sha256"]:
        raise RuntimeError("Gate 15F inputs are not locked")
    task_cases = cases(source)
    if len(task_cases) != 30 or sum(len(item["used"]) for item in task_cases) != 60:
        raise RuntimeError("Frozen USED population changed")

    torch.set_num_threads(args.threads)
    torch.manual_seed(29082026)
    model_spec, writer = protocol["model"], protocol["writer"]
    tokenizer = AutoTokenizer.from_pretrained(model_spec["repository"], revision=model_spec["revision"], local_files_only=True)
    tokenizer.padding_side = "left"
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_spec["repository"], revision=model_spec["revision"], local_files_only=True, dtype=torch.bfloat16).eval()
    prompts = [prompt(writer, item) for item in task_cases]
    started = time.perf_counter()
    records = []
    for start in range(0, len(prompts), args.batch_size):
        batch_prompts = prompts[start:start + args.batch_size]
        chats = [tokenizer.apply_chat_template([
            {"role": "system", "content": writer["system"]},
            {"role": "user", "content": value},
        ], tokenize=False, add_generation_prompt=True, enable_thinking=False) for value in batch_prompts]
        encoded = tokenizer(chats, padding=True, return_tensors="pt")
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            outputs = model.generate(**encoded, do_sample=False, max_new_tokens=writer["max_new_tokens"], eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id)
        for case, user_prompt, output in zip(task_cases[start:start + args.batch_size], batch_prompts, outputs):
            generated = output[input_length:]
            raw = tokenizer.decode(generated, skip_special_tokens=True).strip()
            parsed, error = parse_answer(raw, {item["source_id"] for item in case["used"]})
            records.append({**case, "user_prompt": user_prompt, "raw_output": raw, "parsed": parsed, "parse_error": error, "generated_tokens": int(len(generated)), "hit_token_limit": int(len(generated)) >= writer["max_new_tokens"]})
        print(json.dumps({"completed": len(records), "total": len(task_cases)}), flush=True)

    summary = {
        "questions": len(records),
        "used_fragments": sum(len(item["used"]) for item in records),
        "parseable_answers": sum(item["parse_error"] is None for item in records),
        "answers_hitting_token_limit": sum(item["hit_token_limit"] for item in records),
        "manual_review": "pending",
    }
    result = {
        "schema_version": "0.1", "experiment_id": "E007", "gate": "15F",
        "status": "locked_synthetic_development_inference_complete_manual_audit_pending",
        "git_revision": git_revision(), "protocol": "/experiments/E007/used-shelf-writer-protocol-v0.1.json",
        "protocol_sha256": digest(args.protocol), "source_sha256": digest(args.source),
        "model": {"repository": model_spec["repository"], "revision": model_spec["revision"]},
        "summary": summary, "records": records,
        "runtime": {"seconds": round(time.perf_counter() - started, 3), "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
        "boundaries": protocol["boundaries"],
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    value.add_argument("--source", type=Path, default=SOURCE_PATH)
    value.add_argument("--output", type=Path, default=RESULT_PATH)
    value.add_argument("--threads", type=int, default=20)
    value.add_argument("--batch-size", type=int, default=2)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
