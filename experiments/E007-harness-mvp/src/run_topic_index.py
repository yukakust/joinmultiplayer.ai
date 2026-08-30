#!/usr/bin/env python3
"""Build private Qwen-generated conversation topic cards for E007 Gate 16D.1."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL = "Qwen/Qwen3-8B"
REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
SHORT_LIMIT = 10_000
BLOCK_TARGET = 8_000
MAX_NEW_TOKENS = 1_024


TOPIC_TOOL = [{"type": "function", "function": {
    "name": "save_topics", "description": "Save up to eight real topics discussed in this exact text block.",
    "parameters": {"type": "object", "properties": {"topics": {"type": "array", "maxItems": 8, "items": {
        "type": "object", "properties": {
            "name": {"type": "string"}, "summary": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}}
        }, "required": ["name", "summary", "evidence"]
    }}}, "required": ["topics"]}
}}]


MERGE_TOOL = [{"type": "function", "function": {
    "name": "merge_topics", "description": "Merge related topic candidates into at most twelve conversation topics.",
    "parameters": {"type": "object", "properties": {"topics": {"type": "array", "maxItems": 12, "items": {
        "type": "object", "properties": {
            "name": {"type": "string"}, "summary": {"type": "string"},
            "source_topic_ids": {"type": "array", "items": {"type": "string"}}
        }, "required": ["name", "summary", "source_topic_ids"]
    }}}, "required": ["topics"]}
}}]


def parse_call(raw: str, name: str) -> dict:
    calls = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw, re.DOTALL)
    if len(calls) != 1:
        raise ValueError(f"expected one complete {name} call, got {len(calls)}")
    call = json.loads(calls[0])
    if call.get("name") != name or not isinstance(call.get("arguments"), dict):
        raise ValueError(f"expected {name}")
    return call["arguments"]


def generate(model, tokenizer, user: str, tools: list[dict]) -> tuple[str, int]:
    prompt = tokenizer.apply_chat_template(
        [{"role": "system", "content": "You make a faithful table of contents. Use only supplied text. Never invent a topic or evidence coordinate."}, {"role": "user", "content": user}],
        tools=tools, tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(**encoded, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    raw = tokenizer.decode(output[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return raw, int(encoded.input_ids.shape[1])


def message_units(tokenizer, messages: list[dict]) -> tuple[list[dict], int]:
    units = []
    total = 0
    for message in messages:
        tokens = tokenizer.encode(message["text"], add_special_tokens=False)
        total += len(tokens)
        if len(tokens) <= BLOCK_TARGET:
            units.append({"coordinate": message["id"], "role": message["role"], "text": message["text"], "tokens": len(tokens)})
            continue
        for start in range(0, len(tokens), BLOCK_TARGET):
            end = min(len(tokens), start + BLOCK_TARGET)
            units.append({
                "coordinate": f'{message["id"]}:t{start}-{end}', "role": message["role"],
                "text": tokenizer.decode(tokens[start:end], skip_special_tokens=True), "tokens": end - start,
            })
    return units, total


def blocks(units: list[dict]) -> list[list[dict]]:
    output, current, size = [], [], 0
    for unit in units:
        if current and size + unit["tokens"] > BLOCK_TARGET:
            output.append(current); current, size = [], 0
        current.append(unit); size += unit["tokens"]
    if current:
        output.append(current)
    return output


def render_block(block: list[dict]) -> str:
    return "\n\n".join(f'<message coordinate="{unit["coordinate"]}" role="{unit["role"]}">\n{unit["text"]}\n</message>' for unit in block)


def index_conversation(model, tokenizer, conversation: dict) -> dict:
    units, token_count = message_units(tokenizer, conversation["messages"])
    grouped = [units] if token_count <= SHORT_LIMIT else blocks(units)
    valid_coordinates = {unit["coordinate"] for unit in units}
    candidates = []
    errors = []
    for block_index, block in enumerate(grouped, 1):
        raw, input_tokens = generate(model, tokenizer, f"TEXT BLOCK:\n{render_block(block)}\n\nList the main topics actually discussed. Each evidence value must be an exact coordinate from the message tags. Call save_topics.", TOPIC_TOOL)
        try:
            parsed = parse_call(raw, "save_topics")
            topics = parsed.get("topics")
            if not isinstance(topics, list):
                raise ValueError("topics is not a list")
            for topic in topics:
                if not isinstance(topic, dict) or not isinstance(topic.get("name"), str) or not isinstance(topic.get("summary"), str) or not isinstance(topic.get("evidence"), list):
                    raise ValueError("invalid topic shape")
                if not topic["evidence"] or any(item not in valid_coordinates for item in topic["evidence"]):
                    raise ValueError("invented or empty evidence coordinate")
                candidates.append({"id": f'T{len(candidates)+1:03d}', "block": block_index, **topic})
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append({"block": block_index, "error": str(exc), "input_tokens": input_tokens})

    if not candidates:
        return {"status": "ERROR", "qwen_tokens": token_count, "blocks": len(grouped), "topics": [], "errors": errors}
    if len(grouped) == 1:
        topics = [{"name": item["name"], "summary": item["summary"], "evidence": item["evidence"]} for item in candidates[:12]]
    else:
        merge_raw, merge_input_tokens = generate(model, tokenizer, f"TOPIC CANDIDATES:\n{json.dumps(candidates, ensure_ascii=False)}\n\nMerge only related candidates. Keep distinct subjects distinct. Every source_topic_id must exist above. Call merge_topics.", MERGE_TOOL)
        try:
            merged = parse_call(merge_raw, "merge_topics").get("topics")
            candidate_map = {item["id"]: item for item in candidates}
            if not isinstance(merged, list):
                raise ValueError("merged topics is not a list")
            topics = []
            for topic in merged:
                source_ids = topic.get("source_topic_ids") if isinstance(topic, dict) else None
                if not isinstance(source_ids, list) or not source_ids or any(item not in candidate_map for item in source_ids):
                    raise ValueError("invalid merged source_topic_ids")
                evidence = list(dict.fromkeys(coord for source_id in source_ids for coord in candidate_map[source_id]["evidence"]))
                topics.append({"name": topic["name"], "summary": topic["summary"], "evidence": evidence})
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append({"block": "merge", "error": str(exc), "input_tokens": merge_input_tokens})
            topics = []
    return {"status": "CARD" if topics else "ERROR", "qwen_tokens": token_count, "blocks": len(grouped), "topics": topics, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION, dtype=torch.bfloat16, device_map={"": 0}).eval()
    cards = []
    for index, conversation in enumerate(payload["conversations"], 1):
        card = index_conversation(model, tokenizer, conversation)
        cards.append({
            "card_id": f'{payload["node"]}-C{index:04d}',
            "conversation_hash": conversation["conversation_hash"],
            "source_snapshot_hash": conversation["source_snapshot_hash"],
            **card,
        })
        print(json.dumps({"node": payload["node"], "finished": index, "total": len(payload["conversations"]), "status": card["status"], "tokens": card["qwen_tokens"], "topics": len(card["topics"])}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": "0.1-private", "node": payload["node"], "device": payload["device"],
        "model": MODEL, "revision": REVISION, "cards": cards,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
