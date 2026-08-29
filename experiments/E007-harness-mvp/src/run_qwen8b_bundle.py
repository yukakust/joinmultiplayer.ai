#!/usr/bin/env python3
"""Run locked E007 Gate 15D bundle selection and synthesis."""

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
PROTOCOL_PATH = ROOT / "site/experiments/E007/qwen8b-bundle-protocol-v0.1.json"
SOURCE_PATH = ROOT / "site/experiments/E007/full-pipeline-qwen17b-result-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/qwen8b-bundle-result-v0.1.json"
ANSWER_KEYS = {
    "best_supported", "best_evidence_ids", "alternative_view",
    "alternative_evidence_ids", "action_or_next_step",
    "action_evidence_ids", "uncertainty",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def related_gold(task: dict) -> dict[str, set[str]]:
    offered = {item["source_id"] for item in task["offers"]}
    required = set(task["required_sources"])
    core = {item for item in required if not item.endswith(("-SAFE", "-NEXT"))}
    action = required - core
    alternatives: set[str] = set()
    if task["family"] == "reject_condition_mismatch":
        alternatives = {item for item in offered if item.endswith("-LOOKALIKE")}
    elif task["family"] == "preserve_supported_minority":
        alternatives = {item for item in offered if "-COPY-" in item and item.split("-COPY-")[0] in {
            source.split("-INDEPENDENT")[0] for source in core
        }}
    return {
        "core": core,
        "action": action,
        "alternatives": alternatives,
        "related": required | alternatives,
        "irrelevant": offered - required - alternatives,
    }


def bundles(source: dict) -> list[dict]:
    result = []
    for task in source["records"]:
        gold = related_gold(task)
        result.append({
            "id": task["id"],
            "family": task["family"],
            "question": task["question"],
            "expected": task["expected"],
            "offers": [{
                "source_id": item["source_id"],
                "lineage": item["lineage"],
                "fragment": item["fragment"],
            } for item in task["offers"]],
            "gold": {key: sorted(value) for key, value in gold.items()},
        })
    return result


def selector_prompt(spec: dict, bundle: dict) -> str:
    fragments = "\n".join(
        f"[{item['source_id']}] {item['fragment']}" for item in bundle["offers"]
    )
    return f"{spec['instruction']}\n\nQUESTION\n{bundle['question']}\n\nSOURCE FRAGMENTS\n{fragments}"


def synthesis_prompt(spec: dict, bundle: dict, selected: list[str]) -> str:
    by_id = {item["source_id"]: item for item in bundle["offers"]}
    fragments = "\n".join(
        f"[{item}] lineage={by_id[item]['lineage']}\n{by_id[item]['fragment']}"
        for item in selected
    ) or "(none selected)"
    return f"{spec['instruction']}\n\nQUESTION\n{bundle['question']}\n\nSELECTED FRAGMENTS\n{fragments}"


def parse_selector(raw: str, offered: set[str]) -> tuple[list[str], str | None]:
    try:
        value = json.loads(raw.strip())
    except (json.JSONDecodeError, TypeError):
        return [], "not_one_json_object"
    if set(value) != {"keep"} or not isinstance(value["keep"], list):
        return [], "wrong_json_shape"
    keep = value["keep"]
    if any(not isinstance(item, str) for item in keep) or len(keep) != len(set(keep)):
        return [], "invalid_or_duplicate_id"
    if not set(keep) <= offered:
        return [], "unknown_id"
    return keep, None


def parse_answer(raw: str, selected: set[str]) -> tuple[dict | None, str | None]:
    try:
        value = json.loads(raw.strip())
    except (json.JSONDecodeError, TypeError):
        return None, "not_one_json_object"
    if set(value) != ANSWER_KEYS:
        return None, "wrong_json_shape"
    for key in ("best_evidence_ids", "alternative_evidence_ids", "action_evidence_ids"):
        if not isinstance(value[key], list) or any(not isinstance(item, str) for item in value[key]):
            return None, f"invalid_{key}"
        if not set(value[key]) <= selected:
            return None, f"unselected_id_in_{key}"
    for key in ("best_supported", "alternative_view", "action_or_next_step", "uncertainty"):
        if value[key] is not None and not isinstance(value[key], str):
            return None, f"invalid_{key}"
    return value, None


def generate(model, tokenizer, system: str, prompts: list[str], max_new_tokens: int, batch_size: int) -> list[dict]:
    records = []
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start:start + batch_size]
        chats = [tokenizer.apply_chat_template(
            [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False,
        ) for prompt in batch]
        encoded = tokenizer(chats, padding=True, return_tensors="pt")
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            outputs = model.generate(
                **encoded, do_sample=False, max_new_tokens=max_new_tokens,
                eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
            )
        for output in outputs:
            generated = output[input_length:]
            records.append({
                "raw": tokenizer.decode(generated, skip_special_tokens=True).strip(),
                "generated_tokens": int(len(generated)),
                "hit_token_limit": int(len(generated)) >= max_new_tokens,
            })
    return records


def run(args: argparse.Namespace) -> dict:
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol, source = read(args.protocol), read(args.source)
    if protocol["status"] != "locked_before_inference" or digest(args.source) != protocol["source"]["sha256"]:
        raise RuntimeError("Gate 15D inputs are not locked")
    cases = bundles(source)
    if len(cases) != 30 or sum(len(item["offers"]) for item in cases) != 480:
        raise RuntimeError("Frozen bundle population changed")
    totals = {key: sum(len(item["gold"][key]) for item in cases) for key in ("core", "action", "alternatives", "irrelevant")}
    if totals != {"core": 30, "action": 30, "alternatives": 24, "irrelevant": 396}:
        raise RuntimeError(f"Frozen gold population changed: {totals}")

    torch.set_num_threads(args.threads)
    torch.manual_seed(29082026)
    model_spec = protocol["model"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"], local_files_only=True,
    )
    tokenizer.padding_side = "left"
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"],
        local_files_only=True, dtype=torch.bfloat16,
    ).eval()
    started = time.perf_counter()

    selector_spec = protocol["selector"]
    selection_prompts = [selector_prompt(selector_spec, item) for item in cases]
    selection_outputs = generate(
        model, tokenizer, selector_spec["system"], selection_prompts,
        selector_spec["max_new_tokens"], args.selector_batch_size,
    )
    records = []
    for case, prompt, output in zip(cases, selection_prompts, selection_outputs):
        offered = {item["source_id"] for item in case["offers"]}
        selected, error = parse_selector(output["raw"], offered)
        records.append({
            **case,
            "selector": {"user_prompt": prompt, **output, "selected_ids": selected, "parse_error": error},
        })
    print(json.dumps({"selector_done": len(records), "total": len(cases)}), flush=True)

    synthesis_spec = protocol["synthesis"]
    answer_prompts = [synthesis_prompt(synthesis_spec, item, item["selector"]["selected_ids"]) for item in records]
    answer_outputs = generate(
        model, tokenizer, synthesis_spec["system"], answer_prompts,
        synthesis_spec["max_new_tokens"], args.synthesis_batch_size,
    )
    for record, prompt, output in zip(records, answer_prompts, answer_outputs):
        parsed, error = parse_answer(output["raw"], set(record["selector"]["selected_ids"]))
        record["answer"] = {"user_prompt": prompt, **output, "parsed": parsed, "parse_error": error}
    print(json.dumps({"synthesis_done": len(records), "total": len(cases)}), flush=True)

    def kept(group: str) -> int:
        return sum(len(set(item["gold"][group]) & set(item["selector"]["selected_ids"])) for item in records)

    summary = {
        "questions": len(records),
        "fragments": sum(len(item["offers"]) for item in records),
        "core_required_kept": kept("core"),
        "core_required_total": totals["core"],
        "action_or_next_kept": kept("action"),
        "action_or_next_total": totals["action"],
        "same_case_alternatives_kept": kept("alternatives"),
        "same_case_alternatives_total": totals["alternatives"],
        "irrelevant_kept": kept("irrelevant"),
        "irrelevant_total": totals["irrelevant"],
        "selector_unparseable": sum(item["selector"]["parse_error"] is not None for item in records),
        "answer_unparseable": sum(item["answer"]["parse_error"] is not None for item in records),
        "answers_hit_token_limit": sum(item["answer"]["hit_token_limit"] for item in records),
    }
    gate = protocol["locked_selector_gate"]
    summary["passed_locked_selector_gate"] = (
        summary["core_required_kept"] >= gate["core_required_kept_at_least"]
        and summary["action_or_next_kept"] >= gate["action_or_next_kept_at_least"]
        and summary["same_case_alternatives_kept"] >= gate["same_case_alternatives_kept_at_least"]
        and summary["irrelevant_kept"] <= gate["irrelevant_kept_at_most"]
        and summary["selector_unparseable"] <= gate["unparseable_at_most"]
    )
    result = {
        "schema_version": "0.1", "experiment_id": "E007", "gate": "15D",
        "status": "locked_synthetic_development_inference_complete_manual_audit_pending",
        "git_revision": git_revision(),
        "protocol": "/experiments/E007/qwen8b-bundle-protocol-v0.1.json",
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
    value.add_argument("--selector-batch-size", type=int, default=4)
    value.add_argument("--synthesis-batch-size", type=int, default=2)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
