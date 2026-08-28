#!/usr/bin/env python3
"""Run frozen E007 Gate 3C.6D with Qwen3-0.6B tool calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/atomic-tool-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/atomic-tool-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/atomic-tool-result-v0.1.json"
MODEL_PATH = Path("/home/yuka/models/e005/qwen3-0.6b-instruct-c1899de")
MODEL_FILE = MODEL_PATH / "model.safetensors"
LINKS = ("source_supports_rule", "facts_support_condition", "answer_follows_consequence")
TOOL_CALL_RE = re.compile(r"\s*<tool_call>\s*(\{.*?\})\s*</tool_call>\s*", re.DOTALL)


SYSTEM = (
    "You check one small comparison using only the supplied text. "
    "Call exactly one available tool. Call supported only when the comparison is clearly supported. "
    "If it is not clearly supported or you have any uncertainty, call not_enough. "
    "Do not solve the original user problem and do not add outside knowledge."
)


TOOL_DEFINITIONS = {
    "supported": {
        "type": "function",
        "function": {
            "name": "supported",
            "description": "Choose this only when the supplied comparison is clearly supported by the supplied text.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    "not_enough": {
        "type": "function",
        "function": {
            "name": "not_enough",
            "description": "Choose this when the supplied comparison is not clearly supported or when there is any uncertainty.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
}


ORDER_AUDIT = (
    ("AT01-111", "source_supports_rule"),
    ("AT01-011", "source_supports_rule"),
    ("AT02-111", "facts_support_condition"),
    ("AT02-101", "facts_support_condition"),
    ("AT03-111", "answer_follows_consequence"),
    ("AT03-110", "answer_follows_consequence"),
    ("AT04-111", "source_supports_rule"),
    ("AT04-000", "facts_support_condition"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tools_for(order: str) -> list[dict]:
    names = ("supported", "not_enough") if order == "normal" else ("not_enough", "supported")
    if order not in {"normal", "reversed"}:
        raise ValueError(f"unknown tool order: {order}")
    return [TOOL_DEFINITIONS[name] for name in names]


def prompt_for(case: dict, link: str) -> str:
    if link == "source_supports_rule":
        source = case["source"]
        return (
            "ONE COMPARISON: Can this source window support the proposed rule?\n\n"
            f"SOURCE RECORD: {source['title']} · version {source['version']} · {source['date']} · {source['coordinates']}\n\n"
            f"SOURCE WINDOW:\n{case['source_window']}\n\n"
            f"PROPOSED RULE:\n{case['proposed_rule']}"
        )
    if link == "facts_support_condition":
        return (
            "ONE COMPARISON: Do the current facts clearly show that the rule condition is met now?\n\n"
            f"RULE CONDITION:\n{case['rule_condition']}\n\n"
            f"CURRENT FACTS:\n{case['current_facts']}"
        )
    if link == "answer_follows_consequence":
        return (
            "ONE COMPARISON: Does the proposed answer match the consequence stated by the rule?\n\n"
            f"RULE CONSEQUENCE:\n{case['rule_consequence']}\n\n"
            f"PROPOSED ANSWER:\n{case['proposed_answer']}"
        )
    raise ValueError(f"unknown link: {link}")


def parse_tool_call(raw: str) -> dict:
    match = TOOL_CALL_RE.fullmatch(raw)
    if not match:
        return {"decision": "not_enough", "valid": False, "error": "not_exactly_one_tool_call"}
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {"decision": "not_enough", "valid": False, "error": "invalid_json"}
    if not isinstance(payload, dict) or payload.get("name") not in TOOL_DEFINITIONS:
        return {"decision": "not_enough", "valid": False, "error": "unknown_tool"}
    if payload.get("arguments") != {} or set(payload) != {"name", "arguments"}:
        return {"decision": "not_enough", "valid": False, "error": "invalid_arguments"}
    return {"decision": payload["name"], "valid": True, "error": None}


def combine(decisions: dict[str, str]) -> str:
    return "use" if all(decisions.get(link) == "supported" for link in LINKS) else "do_not_use"


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        local_files_only=True,
        dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()
    return model, tokenizer


def generate_calls(model, tokenizer, items: list[dict], batch_size: int) -> list[dict]:
    outputs = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        rendered = [tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": item["prompt"]}],
            tools=tools_for(item["tool_order"]),
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        ) for item in batch]
        encoded = tokenizer(rendered, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=96,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
            )
        raw_outputs = tokenizer.batch_decode(generated[:, encoded["input_ids"].shape[1]:], skip_special_tokens=False)
        for item, raw in zip(batch, raw_outputs):
            clean = raw.replace(tokenizer.eos_token or "", "").strip()
            outputs.append({**item, "raw_output": clean, **parse_tool_call(clean)})
        print(json.dumps({"generated": min(start + batch_size, len(items)), "total": len(items)}), flush=True)
    return outputs


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6D inputs are not frozen")

    torch.set_num_threads(threads)
    model, tokenizer = load_model()
    cases_by_id = {case["id"]: case for case in world["cases"]}
    main_items = []
    for case_index, case in enumerate(world["cases"]):
        for link_index, link in enumerate(LINKS):
            main_items.append({
                "case_id": case["id"],
                "link": link,
                "tool_order": "normal" if (case_index + link_index) % 2 == 0 else "reversed",
                "prompt": prompt_for(case, link),
            })

    started = time.monotonic()
    main_outputs = generate_calls(model, tokenizer, main_items, batch_size)
    by_key = {(item["case_id"], item["link"]): item for item in main_outputs}

    audit_items = []
    for case_id, link in ORDER_AUDIT:
        case = cases_by_id[case_id]
        for order in ("normal", "reversed"):
            audit_items.append({"case_id": case_id, "link": link, "tool_order": order, "prompt": prompt_for(case, link)})
    audit_outputs = generate_calls(model, tokenizer, audit_items, batch_size)

    records = []
    for case in world["cases"]:
        actual_links = {link: by_key[(case["id"], link)] for link in LINKS}
        actual_final = combine({link: actual_links[link]["decision"] for link in LINKS})
        records.append({
            **case,
            "actual": {"links": actual_links, "final": actual_final},
            "correct": {
                **{link: actual_links[link]["decision"] == case["expected"][link] for link in LINKS},
                "final": actual_final == case["expected"]["final"],
            },
        })

    audit_records = []
    for case_id, link in ORDER_AUDIT:
        selected = [item for item in audit_outputs if item["case_id"] == case_id and item["link"] == link]
        normal = next(item for item in selected if item["tool_order"] == "normal")
        reversed_order = next(item for item in selected if item["tool_order"] == "reversed")
        audit_records.append({
            "case_id": case_id,
            "link": link,
            "expected": cases_by_id[case_id]["expected"][link],
            "normal": normal,
            "reversed": reversed_order,
            "invariant": normal["decision"] == reversed_order["decision"],
        })

    summary = {
        **{f"{link}_correct": sum(record["correct"][link] for record in records) for link in LINKS},
        "final_correct": sum(record["correct"]["final"] for record in records),
        "useful_packets_used": sum(record["expected"]["final"] == "use" and record["actual"]["final"] == "use" for record in records),
        "useful_packets_total": sum(record["expected"]["final"] == "use" for record in records),
        "false_packets_used": sum(record["expected"]["final"] != "use" and record["actual"]["final"] == "use" for record in records),
        "trap_packets_total": sum(record["expected"]["final"] != "use" for record in records),
        "malformed_tool_calls": sum(not item["valid"] for item in main_outputs + audit_outputs),
        "order_invariant": sum(item["invariant"] for item in audit_records),
        "order_audit_total": len(audit_records),
        "total_cases": len(records),
        "total_main_tool_calls": len(main_outputs),
    }
    gate = protocol["locked_success"]
    passed = (
        summary["source_supports_rule_correct"] >= gate["source_supports_rule_correct_min"]
        and summary["facts_support_condition_correct"] >= gate["facts_support_condition_correct_min"]
        and summary["answer_follows_consequence_correct"] >= gate["answer_follows_consequence_correct_min"]
        and summary["useful_packets_used"] >= gate["useful_packets_used_min"]
        and summary["false_packets_used"] <= gate["false_packets_used_max"]
        and summary["malformed_tool_calls"] <= gate["malformed_tool_calls_max"]
        and summary["order_invariant"] >= gate["order_invariant_min"]
    )
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6D",
        "status": "locked_development_run_complete",
        "protocol": "/experiments/E007/atomic-tool-protocol-v0.1.json",
        "world": "/experiments/E007/atomic-tool-world-v0.1.json",
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "world_sha256": sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": sha256_file(MODEL_FILE),
            "weights_changed": False,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "passed_locked_gate": passed,
        "order_audit": audit_records,
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.batch_size, args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed_locked_gate"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
