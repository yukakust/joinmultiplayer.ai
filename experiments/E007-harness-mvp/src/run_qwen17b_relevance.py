#!/usr/bin/env python3
"""Run locked E007 Gate 15B Qwen3-1.7B relevance decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/qwen17b-relevance-protocol-v0.1.json"
SOURCE_PATH = ROOT / "site/experiments/E007/full-pipeline-qwen17b-result-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/qwen17b-relevance-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def make_prompt(template: str, question: str, fragment: str) -> str:
    return template.format(question=question, fragment=fragment)


def parse_decision(text: str) -> str:
    normalized = text.strip().upper().rstrip(".!")
    return normalized if normalized in {"USEFUL", "NOT_USEFUL"} else "UNPARSEABLE"


def frozen_pairs(source: dict) -> list[dict]:
    pairs = []
    for task in source["records"]:
        required = set(task["required_sources"])
        for offer in task["offers"]:
            pairs.append({
                "id": f"{task['id']}::{offer['source_id']}",
                "task_id": task["id"],
                "source_id": offer["source_id"],
                "question": task["question"],
                "fragment": offer["fragment"],
                "gold": "USEFUL" if offer["source_id"] in required else "NOT_USEFUL",
            })
    return pairs


def run(args: argparse.Namespace) -> dict:
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol, source = read(args.protocol), read(args.source)
    if protocol["status"] != "locked_before_inference" or digest(args.source) != protocol["source"]["sha256"]:
        raise RuntimeError("Gate 15B inputs are not the locked source")
    pairs = frozen_pairs(source)
    if len(pairs) != 480 or sum(item["gold"] == "USEFUL" for item in pairs) != 60:
        raise RuntimeError("Frozen pair population changed")
    spec, prompt_spec = protocol["model"], protocol["prompt"]
    torch.set_num_threads(args.threads)
    torch.manual_seed(29082026)
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"], local_files_only=True)
    tokenizer.padding_side = "left"
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        spec["repository"], revision=spec["revision"], local_files_only=True, dtype=torch.bfloat16
    ).eval()
    started = time.perf_counter()
    records = []
    for start in range(0, len(pairs), args.batch_size):
        batch = pairs[start : start + args.batch_size]
        user_prompts = [make_prompt(prompt_spec["template"], item["question"], item["fragment"]) for item in batch]
        chats = [tokenizer.apply_chat_template(
            [{"role":"system","content":prompt_spec["system"]},{"role":"user","content":user}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False,
        ) for user in user_prompts]
        encoded = tokenizer(chats, padding=True, return_tensors="pt")
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            outputs = model.generate(
                **encoded, do_sample=False, max_new_tokens=spec["max_new_tokens"],
                eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
            )
        for item, user, output in zip(batch, user_prompts, outputs):
            generated = output[input_length:]
            raw = tokenizer.decode(generated, skip_special_tokens=True).strip()
            decision = parse_decision(raw)
            records.append({
                **item, "user_prompt": user, "raw_output": raw, "decision": decision,
                "correct": decision == item["gold"], "generated_tokens": int(len(generated)),
            })
        if len(records) % 80 == 0:
            print(json.dumps({"done":len(records),"total":len(pairs)}), flush=True)
    required = [item for item in records if item["gold"] == "USEFUL"]
    unrelated = [item for item in records if item["gold"] == "NOT_USEFUL"]
    summary = {
        "total": len(records),
        "required_kept": sum(item["decision"] == "USEFUL" for item in required),
        "required_total": len(required),
        "required_lost": sum(item["decision"] != "USEFUL" for item in required),
        "unrelated_kept": sum(item["decision"] == "USEFUL" for item in unrelated),
        "unrelated_total": len(unrelated),
        "unrelated_dropped": sum(item["decision"] == "NOT_USEFUL" for item in unrelated),
        "unparseable": sum(item["decision"] == "UNPARSEABLE" for item in records),
    }
    gate = protocol["locked_development_gate"]
    summary["passed_locked_development_gate"] = (
        summary["required_kept"] >= gate["required_kept_at_least"]
        and summary["unrelated_kept"] <= gate["unrelated_kept_at_most"]
        and summary["unparseable"] <= gate["unparseable_at_most"]
    )
    result = {
        "schema_version":"0.1", "experiment_id":"E007", "gate":"15B",
        "status":"locked_comparative_synthetic_development_complete",
        "git_revision":git_revision(), "protocol":"/experiments/E007/qwen17b-relevance-protocol-v0.1.json",
        "protocol_sha256":digest(args.protocol), "source_sha256":digest(args.source),
        "model":{"repository":spec["repository"],"revision":spec["revision"]},
        "summary":summary, "baseline":protocol["baseline"], "records":records,
        "runtime":{"seconds":round(time.perf_counter()-started,3),"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
        "boundaries":protocol["boundaries"],
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return result


def parser() -> argparse.ArgumentParser:
    value=argparse.ArgumentParser()
    value.add_argument("--protocol",type=Path,default=PROTOCOL_PATH)
    value.add_argument("--source",type=Path,default=SOURCE_PATH)
    value.add_argument("--output",type=Path,default=RESULT_PATH)
    value.add_argument("--threads",type=int,default=20)
    value.add_argument("--batch-size",type=int,default=16)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
