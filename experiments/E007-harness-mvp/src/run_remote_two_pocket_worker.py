#!/usr/bin/env python3
"""Run one Gate 16D private payload on one GPU-backed Qwen3-8B worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_found",
            "description": "Use when this conversation contains information that helps answer the question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["claim", "evidence"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_empty",
            "description": "Use when this conversation contains nothing that helps answer the question.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
        }
    }
]


def parse_tool(raw: str) -> dict:
    calls = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw, flags=re.DOTALL)
    if len(calls) != 1:
        return {"status": "ERROR", "reason": f"expected one tool call, got {len(calls)}"}
    try:
        call = json.loads(calls[0])
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "reason": f"invalid JSON: {exc}"}
    arguments = call.get("arguments") or {}
    if call.get("name") == "send_empty" and arguments == {}:
        return {"status": "EMPTY", "claim": "", "evidence": []}
    if call.get("name") == "send_found" and isinstance(arguments, dict):
        claim, evidence = arguments.get("claim"), arguments.get("evidence")
        if isinstance(claim, str) and claim.strip() and isinstance(evidence, list) and all(isinstance(item, str) for item in evidence):
            return {"status": "FOUND", "claim": claim.strip(), "evidence": evidence}
    return {"status": "ERROR", "reason": "tool call violates contract"}


def render_transcript(messages: list[dict]) -> str:
    return "\n\n".join(f'<message id="{item["id"]}" role="{item["role"]}">\n{item["text"]}\n</message>' for item in messages)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3-8B")
    parser.add_argument("--revision", default="b968826d9c46dd6066d109eabc6255188de91218")
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, revision=args.revision, dtype=torch.bfloat16, device_map={"": 0},
    ).eval()
    records = []
    for conversation in payload["conversations"]:
        transcript = render_transcript(conversation["messages"])
        user = f"""Use only the conversation below. Do not use outside knowledge. For this one question call exactly one tool.

<conversation>
{transcript}
</conversation>

QUESTION:
{payload['question']}"""
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": "You are the local evidence extractor of one pocket i."}, {"role": "user", "content": user}],
            tools=TOOLS, tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
        encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            generated = model.generate(**encoded, max_new_tokens=384, do_sample=False, pad_token_id=tokenizer.eos_token_id)
        raw = tokenizer.decode(generated[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
        decision = parse_tool(raw)
        message_map = {item["id"]: item for item in conversation["messages"]}
        evidence = []
        for message_id in decision.get("evidence", []):
            message = message_map.get(message_id)
            evidence.append({
                "id": message_id,
                "valid": message is not None,
                "role": message.get("role") if message else None,
                "text": message.get("text") if message else None,
                "sha256": hashlib.sha256(message["text"].encode()).hexdigest() if message else None,
            })
        records.append({
            "conversation": conversation["conversation"],
            "conversation_hash": conversation["conversation_hash"],
            "selection_score": conversation["selection_score"],
            "input_tokens": int(encoded.input_ids.shape[1]),
            "decision": decision,
            "selected_messages": evidence,
            "raw": raw,
        })
        print(json.dumps({"node": payload["node"], "conversation": conversation["conversation"], "status": decision["status"]}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": "0.1-private",
        "node": payload["node"],
        "device": payload["device"],
        "question": payload["question"],
        "model": args.model,
        "revision": args.revision,
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
