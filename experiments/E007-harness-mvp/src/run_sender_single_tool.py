#!/usr/bin/env python3
"""Run Gate 16C.1: one cached conversation, one question, one tool receipt."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/sender-single-tool-protocol-v0.1.json"
sys.path.insert(0, str(Path(__file__).parent))
from run_kv_cache_reuse import cache_bytes, common_prefix  # noqa: E402
from run_whole_chat_reader import render_transcript, session_id, visible_messages  # noqa: E402

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_found",
            "description": "Use only when the conversation directly contains the requested answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "One short answer supported by the conversation."},
                    "evidence": {"type": "array", "items": {"type": "string"}, "description": "Supporting message IDs such as M0002."}
                },
                "required": ["claim", "evidence"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_empty",
            "description": "Use when the conversation does not contain the requested answer.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
        }
    }
]


def render(tokenizer, transcript: str, question: str) -> str:
    content = f"""Используй только разговор ниже. Не применяй внешние знания и не угадывай.
Для одного вопроса вызови ровно один инструмент:
- send_found, если прямой ответ есть;
- send_empty, если ответа нет.

<transcript>
{transcript}
</transcript>

ВОПРОС:
{question}"""
    return tokenizer.apply_chat_template(
        [{"role": "system", "content": "Ты локальный экстрактор pocket i."}, {"role": "user", "content": content}],
        tools=TOOLS, tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )


def parse_tool(raw: str) -> dict:
    calls = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw, flags=re.DOTALL)
    if len(calls) != 1:
        return {"status": "ERROR", "reason": f"expected one tool call, got {len(calls)}"}
    try:
        call = json.loads(calls[0])
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "reason": f"invalid tool JSON: {exc}"}
    name = call.get("name")
    arguments = call.get("arguments") or {}
    if name == "send_empty" and isinstance(arguments, dict) and not arguments:
        return {"status": "EMPTY", "claim": "", "evidence": []}
    if name == "send_found" and isinstance(arguments, dict):
        claim, evidence = arguments.get("claim"), arguments.get("evidence")
        if isinstance(claim, str) and claim.strip() and isinstance(evidence, list) and all(isinstance(item, str) for item in evidence):
            return {"status": "FOUND", "claim": claim.strip(), "evidence": evidence}
    return {"status": "ERROR", "reason": "tool name or arguments violate the locked contract"}


def branch(model, tokenizer, prefix_cache, prefix_tokens: int, suffix: list[int]) -> dict:
    cache = copy.deepcopy(prefix_cache)
    suffix_tensor = torch.tensor([suffix], dtype=torch.long)
    attention_mask = torch.ones((1, prefix_tokens + len(suffix)), dtype=torch.long)
    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            input_ids=suffix_tensor, attention_mask=attention_mask, past_key_values=cache,
            max_new_tokens=256, do_sample=False, pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = output[0, len(suffix):]
    raw = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return {"seconds": round(time.perf_counter() - started, 3), "new_tokens": int(new_tokens.shape[0]), "raw": raw, "decision": parse_tool(raw)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-cases", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=12)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference":
        raise RuntimeError("Protocol must be locked before inference")
    private = json.loads(args.private_cases.read_text(encoding="utf-8"))
    labels = {item["label"]: item["session_id"] for item in private["conversations"]}

    torch.set_num_threads(args.threads)
    torch.manual_seed(30082026)
    model_spec = protocol["model"]
    tokenizer = AutoTokenizer.from_pretrained(model_spec["repository"], revision=model_spec["revision"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"], local_files_only=True, dtype=torch.bfloat16,
    ).eval()

    by_id: dict[str, list[Path]] = {}
    for path in args.sessions.rglob("*.jsonl"):
        identifier = session_id(path)
        if identifier:
            by_id.setdefault(identifier, []).append(path)

    records = []
    for label in ("CHAT-C", "CHAT-D"):
        messages = visible_messages(by_id.get(labels[label], []))
        transcript = render_transcript(messages)
        questions = [q for q in protocol["questions"] if q["conversation"] == label]
        prompts = [tokenizer.encode(render(tokenizer, transcript, q["question"]), add_special_tokens=False) for q in questions]
        prefix = common_prefix(prompts)
        suffixes = [tokens[len(prefix):] for tokens in prompts]
        if len(prefix) < 5_000 or any(not suffix for suffix in suffixes):
            raise RuntimeError(f"Common conversation prefix failed for {label}")
        prefill_started = time.perf_counter()
        with torch.inference_mode():
            prefix_cache = model(input_ids=torch.tensor([prefix], dtype=torch.long), use_cache=True).past_key_values
        prefill_seconds = round(time.perf_counter() - prefill_started, 3)
        original_length = prefix_cache.get_seq_length()
        message_map = {f"M{i:04d}": message for i, message in enumerate(messages, 1)}
        answers = []
        for question, suffix in zip(questions, suffixes):
            result = branch(model, tokenizer, prefix_cache, len(prefix), suffix)
            if prefix_cache.get_seq_length() != original_length:
                raise RuntimeError("Immutable prefix cache changed")
            decision = result["decision"]
            selected = []
            for evidence_id in decision.get("evidence", []):
                message = message_map.get(evidence_id)
                selected.append({
                    "id": evidence_id, "valid": message is not None,
                    "role": message.get("role") if message else None,
                    "phase": message.get("phase") if message else None,
                    "text": message.get("text") if message else None,
                    "sha256": hashlib.sha256(message["text"].encode()).hexdigest() if message else None,
                })
            answers.append({"id": question["id"], **result, "selected_messages": selected})
            print(json.dumps({"finished": question["id"], "status": decision["status"], "seconds": result["seconds"]}), flush=True)
        records.append({
            "label": label, "messages": len(messages),
            "transcript_tokens": len(tokenizer.encode(transcript, add_special_tokens=False)),
            "common_prefix_tokens": len(prefix), "prefix_cache_bytes": cache_bytes(prefix_cache),
            "prefill_seconds": prefill_seconds, "answers": answers,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": "0.1-private", "protocol": str(PROTOCOL.relative_to(ROOT)), "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
