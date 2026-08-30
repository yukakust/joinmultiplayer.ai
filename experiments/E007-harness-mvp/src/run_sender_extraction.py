#!/usr/bin/env python3
"""Run the locked E007 Gate 16C sender-extraction test locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/sender-extraction-protocol-v0.1.json"
sys.path.insert(0, str(Path(__file__).parent))
from run_whole_chat_reader import render_transcript, session_id, visible_messages  # noqa: E402


def parse_array(raw: str) -> list[dict]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("Model did not return a JSON array")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("Model result is not a list")
    return parsed


def make_prompt(questions: list[dict], transcript: str) -> str:
    rendered_questions = "\n".join(f"{q['id']}. {q['question']}" for q in questions)
    return f"""Прочитай разговор и проверь пять вопросов. Используй только этот разговор.
Не используй внешние знания и не угадывай.
Если ответ действительно есть, верни FOUND, одно короткое утверждение своими словами и номера сообщений, которые прямо его подтверждают.
Если ответа нет, верни EMPTY, пустое утверждение и пустой список evidence.

РАЗГОВОР:
<transcript>
{transcript}
</transcript>

ВОПРОСЫ:
{rendered_questions}

Верни строго JSON-массив из пяти объектов:
[
  {{"id":"C1", "status":"FOUND", "claim":"...", "evidence":["M0001"]}},
  {{"id":"C2", "status":"EMPTY", "claim":"", "evidence":[]}}
]"""


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
    if set(labels) != {"CHAT-C", "CHAT-D"}:
        raise RuntimeError("Private mapping must contain exactly CHAT-C and CHAT-D")

    torch.set_num_threads(args.threads)
    torch.manual_seed(30082026)
    spec = protocol["model"]
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        spec["repository"], revision=spec["revision"], local_files_only=True,
        dtype=torch.bfloat16,
    ).eval()

    by_id: dict[str, list[Path]] = {}
    for path in args.sessions.rglob("*.jsonl"):
        identifier = session_id(path)
        if identifier:
            by_id.setdefault(identifier, []).append(path)

    records = []
    for label in ("CHAT-C", "CHAT-D"):
        messages = visible_messages(by_id.get(labels[label], []))
        if not messages:
            raise RuntimeError(f"Conversation missing: {label}")
        transcript = render_transcript(messages)
        questions = [{"id": q["id"], "question": q["question"]} for q in protocol["questions"] if q["conversation"] == label]
        prompt = make_prompt(questions, transcript)
        rendered = tokenizer.apply_chat_template(
            [{"role": "system", "content": "Ты локальный экстрактор pocket i. Не выдумывай отсутствующие знания."}, {"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
        inputs = tokenizer(rendered, return_tensors="pt", add_special_tokens=False)
        started = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(
                **inputs, max_new_tokens=1024, do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = output[0, inputs.input_ids.shape[1]:]
        raw = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        parsed = parse_array(raw)
        message_map = {f"M{i:04d}": m for i, m in enumerate(messages, 1)}
        rehydrated = []
        for item in parsed:
            evidence = item.get("evidence") if isinstance(item, dict) else []
            evidence = evidence if isinstance(evidence, list) else []
            selected = []
            for identifier in evidence:
                message = message_map.get(str(identifier))
                selected.append({
                    "id": str(identifier),
                    "valid": message is not None,
                    "role": message.get("role") if message else None,
                    "phase": message.get("phase") if message else None,
                    "text": message.get("text") if message else None,
                    "sha256": hashlib.sha256(message["text"].encode()).hexdigest() if message else None,
                })
            rehydrated.append({"model_item": item, "selected_messages": selected})
        records.append({
            "label": label,
            "conversation_sha256": hashlib.sha256(transcript.encode()).hexdigest(),
            "messages": len(messages),
            "transcript_tokens": len(tokenizer.encode(transcript, add_special_tokens=False)),
            "prompt_tokens": int(inputs.input_ids.shape[1]),
            "new_tokens": int(new_tokens.shape[0]),
            "seconds": round(time.perf_counter() - started, 3),
            "raw": raw,
            "parsed": rehydrated,
        })
        print(json.dumps({"finished": label, "questions": len(questions)}), flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": "0.1-private",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
