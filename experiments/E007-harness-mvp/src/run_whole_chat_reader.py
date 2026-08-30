#!/usr/bin/env python3
"""Run Qwen3-8B as the Gate 16D.3 whole-conversation reader."""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from pathlib import Path


MODEL = "Qwen/Qwen3-8B"
REVISION = "b968826d9c46dd6066d109eabc6255188de91218"

TOOLS = [
    {"type": "function", "function": {
        "name": "send_found",
        "description": "Return one useful claim supported by the supplied conversation.",
        "parameters": {"type": "object", "properties": {
            "claim": {"type": "string"},
            "evidence_message_ids": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string"}}
        }, "required": ["claim", "evidence_message_ids"]}
    }},
    {"type": "function", "function": {
        "name": "send_empty",
        "description": "Use when this conversation does not contain useful information for the question.",
        "parameters": {"type": "object", "properties": {}}
    }},
]


def parse_call(raw: str) -> tuple[str, dict]:
    calls = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw, re.DOTALL)
    if len(calls) != 1:
        raise ValueError(f"expected one complete tool call, got {len(calls)}")
    call = json.loads(calls[0])
    name = call.get("name")
    arguments = call.get("arguments")
    if name not in {"send_found", "send_empty"} or not isinstance(arguments, dict):
        raise ValueError("unknown or malformed tool call")
    return name, arguments


def render_conversation(messages: list[dict]) -> str:
    return "\n\n".join(
        f'<message id="{message["id"]}" role="{message["role"]}">\n{html.escape(message["text"])}\n</message>'
        for message in messages
    )


def main() -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    questions = {item["id"]: item["question"] for item in json.loads(args.questions.read_text(encoding="utf-8"))["queries"]}
    conversations = {f'{payload["node"]}-C{index:04d}': item for index, item in enumerate(payload["conversations"], 1)}

    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa"
    ).eval()
    rows = []
    for case in protocol["cases"]:
        conversation = conversations[case["card_id"]]
        valid_ids = {message["id"] for message in conversation["messages"]}
        user = (
            f'QUESTION:\n{questions[case["query_id"]]}\n\n'
            f'CONVERSATION:\n{render_conversation(conversation["messages"])}\n\n'
            "Use only this conversation. If it contains a useful answer, call send_found with a short plain-language claim and the smallest exact set of supporting message IDs. Otherwise call send_empty. Call exactly one tool."
        )
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": "You read one local conversation faithfully. Never use outside knowledge and never invent evidence."}, {"role": "user", "content": user}],
            tools=TOOLS, tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
        encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
        started = time.monotonic()
        with torch.inference_mode():
            generated = model.generate(
                **encoded, max_new_tokens=512, do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        raw = tokenizer.decode(generated[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
        row = {
            "id": case["id"], "kind": case["kind"], "query_id": case["query_id"],
            "card_id": case["card_id"], "input_tokens": int(encoded.input_ids.shape[1]),
            "runtime_seconds": round(time.monotonic() - started, 3), "raw": raw,
        }
        try:
            name, arguments = parse_call(raw)
            row["receipt"] = "FOUND" if name == "send_found" else "EMPTY"
            row["claim"] = arguments.get("claim") if name == "send_found" else None
            evidence = arguments.get("evidence_message_ids", []) if name == "send_found" else []
            if name == "send_found" and (
                not isinstance(row["claim"], str) or not row["claim"].strip()
                or not isinstance(evidence, list) or not 1 <= len(evidence) <= 3
                or any(item not in valid_ids for item in evidence)
            ):
                raise ValueError("invalid FOUND payload")
            row["evidence_message_ids"] = evidence
            if case["kind"] == "positive":
                row["mechanical_pass"] = name == "send_found" and bool(set(evidence) & set(case["accepted_evidence"]))
            else:
                row["mechanical_pass"] = name == "send_empty"
        except (ValueError, json.JSONDecodeError) as error:
            row["receipt"] = "ERROR"
            row["error"] = str(error)
            row["mechanical_pass"] = False
        rows.append(row)
        print(json.dumps({key: row[key] for key in ("id", "receipt", "mechanical_pass", "input_tokens", "runtime_seconds")}), flush=True)

    result = {
        "schema_version": "0.1-private", "experiment": "E007", "gate": "16D.3",
        "model": MODEL, "revision": REVISION, "rows": rows,
        "mechanical_summary": {
            "valid_receipts": sum(row["receipt"] != "ERROR" for row in rows),
            "positive_pass": sum(row["kind"] == "positive" and row["mechanical_pass"] for row in rows),
            "negative_pass": sum(row["kind"] == "negative" and row["mechanical_pass"] for row in rows),
        },
        "status": "awaiting_human_claim_review"
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
