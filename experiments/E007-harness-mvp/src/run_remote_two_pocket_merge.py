#!/usr/bin/env python3
"""Build USED/OTHER shelves and one answer for E007 Gate 16D."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL = "Qwen/Qwen3-8B"
REVISION = "b968826d9c46dd6066d109eabc6255188de91218"


def parse_call(raw: str, expected: str) -> dict:
    calls = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw, flags=re.DOTALL)
    if len(calls) != 1:
        raise RuntimeError(f"expected one {expected} call, got {len(calls)}")
    call = json.loads(calls[0])
    if call.get("name") != expected or not isinstance(call.get("arguments"), dict):
        raise RuntimeError(f"expected {expected} tool")
    return call["arguments"]


def generate(model, tokenizer, system: str, user: str, tools: list[dict]) -> tuple[str, dict]:
    prompt = tokenizer.apply_chat_template(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        tools=tools, tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(**encoded, max_new_tokens=512, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    raw = tokenizer.decode(output[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return raw, {"input_tokens": int(encoded.input_ids.shape[1]), "new_tokens": int(output.shape[1] - encoded.input_ids.shape[1])}


def collect_capsules(results: list[dict]) -> list[dict]:
    capsules = []
    for result in results:
        node = result["node"]
        for record in result["records"]:
            decision = record["decision"]
            if decision.get("status") != "FOUND":
                continue
            selected = record.get("selected_messages") or []
            if not selected or any(not item.get("valid") for item in selected):
                continue
            capsules.append({
                "id": f'{node}-{record["conversation"]}',
                "node": node,
                "claim": decision["claim"],
                "evidence": [
                    {"id": item["id"], "text": item["text"], "sha256": item["sha256"]}
                    for item in selected
                ],
            })
    return capsules


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    results = [json.loads(path.read_text(encoding="utf-8")) for path in args.input]
    questions = {result["question"] for result in results}
    if len(questions) != 1:
        raise RuntimeError("worker questions differ")
    question = questions.pop()
    capsules = collect_capsules(results)
    if not capsules:
        raise RuntimeError("no mechanically grounded FOUND capsule")

    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION, dtype=torch.bfloat16, device_map={"": 0}).eval()
    shelf_tools = [{
        "type": "function", "function": {"name": "send_shelves", "description": "Place every capsule on exactly one shelf.",
        "parameters": {"type": "object", "properties": {
            "used": {"type": "array", "items": {"type": "string"}},
            "other": {"type": "array", "items": {"type": "string"}}
        }, "required": ["used", "other"]}}
    }]
    capsule_text = json.dumps(capsules, ensure_ascii=False)
    shelf_raw, shelf_metrics = generate(
        model, tokenizer, "You organize supported evidence without deleting it.",
        f"QUESTION:\n{question}\n\nCAPSULES:\n{capsule_text}\n\nPut the smallest jointly useful supported set in USED. Put duplicates, weaker versions, unresolved alternatives and noise in OTHER. Use every capsule ID exactly once. Call send_shelves.",
        shelf_tools,
    )
    shelves = parse_call(shelf_raw, "send_shelves")
    used, other = shelves.get("used"), shelves.get("other")
    all_ids = {item["id"] for item in capsules}
    if not isinstance(used, list) or not isinstance(other, list) or set(used) & set(other) or set(used) | set(other) != all_ids:
        raise RuntimeError("shelf partition is not an exact partition")
    used_capsules = [item for item in capsules if item["id"] in set(used)]

    answer_tools = [{
        "type": "function", "function": {"name": "send_answer", "description": "Return one answer using only USED evidence.",
        "parameters": {"type": "object", "properties": {
            "answer": {"type": "string"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}}
        }, "required": ["answer", "evidence_ids"]}}
    }]
    answer_raw, answer_metrics = generate(
        model, tokenizer, "You write a clear answer from supplied evidence only. Do not add unsupported facts.",
        f"QUESTION:\n{question}\n\nUSED CAPSULES:\n{json.dumps(used_capsules, ensure_ascii=False)}\n\nWrite one simple answer. Cite only USED capsule IDs. Call send_answer.",
        answer_tools,
    )
    answer = parse_call(answer_raw, "send_answer")
    if not isinstance(answer.get("answer"), str) or not answer["answer"].strip():
        raise RuntimeError("empty final answer")
    if not isinstance(answer.get("evidence_ids"), list) or not set(answer["evidence_ids"]) <= set(used):
        raise RuntimeError("writer cited outside USED")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": "0.1-private", "question": question, "capsules": capsules,
        "shelves": {"used": used, "other": other}, "answer": answer,
        "metrics": {"shelf": shelf_metrics, "answer": answer_metrics},
        "raw": {"shelf": shelf_raw, "answer": answer_raw},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
