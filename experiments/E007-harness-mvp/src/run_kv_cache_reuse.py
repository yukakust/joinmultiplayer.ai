#!/usr/bin/env python3
"""Measure exact Qwen3-8B prefix-cache reuse on a private cleaned Codex chat."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/kv-cache-reuse-protocol-v0.1.json"
SESSION_ID = "01a01ddb-510a-78c3-bd80-97f8a68b1b79"
QUESTIONS = [
    {
        "id": "CACHE-Q1",
        "question": "Как в разговоре разделили обязанности между локальной памятью и LoRA при усвоении нового знания?",
        "expected": "Память хранит редактируемые факты и источники; LoRA учит способу пользоваться подтверждённым знанием и навыкам поведения.",
        "evidence": "M0002",
    },
    {
        "id": "CACHE-Q2",
        "question": "Какие два режима сетевого нейронного объединения предложили и какой из них считался массовым?",
        "expected": "Streaming neural mode and latent-once mode; latent-once was the mass mode.",
        "evidence": "M0006",
    },
]


def session_id(path: Path) -> str | None:
    found = None
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            record = json.loads(line)
            payload = record.get("payload")
            if record.get("type") == "session_meta" and isinstance(payload, dict):
                found = payload.get("id") or payload.get("session_id") or found
    return str(found) if found else None


def excluded_user_block(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("<recommended_plugins>") or stripped.startswith("<environment_context>")


def visible_messages(paths: list[Path]) -> list[dict]:
    seen: set[str] = set()
    messages = []
    for path in sorted(paths):
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                record = json.loads(line)
                payload = record.get("payload")
                if not (
                    record.get("type") == "response_item"
                    and isinstance(payload, dict)
                    and payload.get("type") == "message"
                    and payload.get("role") in {"user", "assistant"}
                ):
                    continue
                role = payload["role"]
                wanted = "input_text" if role == "user" else "output_text"
                text = "\n".join(
                    item["text"]
                    for item in payload.get("content") or []
                    if isinstance(item, dict) and item.get("type") == wanted and isinstance(item.get("text"), str)
                )
                if not text or (role == "user" and excluded_user_block(text)):
                    continue
                identifier = str(payload.get("id") or hashlib.sha256((role + "\0" + text).encode()).hexdigest())
                if identifier in seen:
                    continue
                seen.add(identifier)
                messages.append({"role": role, "phase": payload.get("phase"), "text": text})
    return messages


def transcript(messages: list[dict]) -> str:
    return "\n\n".join(
        f"[M{index:04d} | {item['role']} | {item.get('phase') or 'message'}]\n{item['text']}"
        for index, item in enumerate(messages, 1)
    )


def rendered_prompt(tokenizer, chat: str, item: dict) -> str:
    user = f"""Прочитай разговор и ответь только по нему. Ничего не додумывай.
Ответь одним коротким абзацем и в конце напиши SUPPORT: M0000.

<transcript>
{chat}
</transcript>

ВОПРОС:
{item['question']}"""
    return tokenizer.apply_chat_template(
        [
            {"role": "system", "content": "Ты аккуратный читатель. Используй только переданный разговор."},
            {"role": "user", "content": user},
        ],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def common_prefix(sequences: list[list[int]]) -> list[int]:
    length = min(len(item) for item in sequences)
    for index in range(length):
        value = sequences[0][index]
        if any(item[index] != value for item in sequences[1:]):
            return sequences[0][:index]
    return sequences[0][:length]


def cache_bytes(cache) -> int:
    return sum(
        layer.keys.numel() * layer.keys.element_size()
        + layer.values.numel() * layer.values.element_size()
        for layer in cache.layers
        if getattr(layer, "keys", None) is not None
    )


def answer(model, tokenizer, prefix_cache, prefix_tokens: int, suffix: list[int], max_new_tokens: int) -> dict:
    clone_started = time.perf_counter()
    branch_cache = copy.deepcopy(prefix_cache)
    clone_seconds = time.perf_counter() - clone_started
    suffix_tensor = torch.tensor([suffix], dtype=torch.long)
    attention_mask = torch.ones((1, prefix_tokens + len(suffix)), dtype=torch.long)
    generation_started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            input_ids=suffix_tensor,
            attention_mask=attention_mask,
            past_key_values=branch_cache,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generation_seconds = time.perf_counter() - generation_started
    new_tokens = output[0, len(suffix):]
    return {
        "suffix_tokens": len(suffix),
        "new_tokens": int(new_tokens.shape[0]),
        "cache_clone_seconds": round(clone_seconds, 3),
        "generation_seconds": round(generation_seconds, 3),
        "cached_total_seconds": round(clone_seconds + generation_seconds, 3),
        "raw": tokenizer.decode(new_tokens, skip_special_tokens=True).strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=12)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference":
        raise RuntimeError("Protocol must be locked before inference")

    torch.set_num_threads(args.threads)
    torch.manual_seed(29082026)
    spec = protocol["model"]
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        spec["repository"], revision=spec["revision"], local_files_only=True, dtype=torch.bfloat16,
    ).eval()

    paths = [path for path in args.sessions.rglob("*.jsonl") if session_id(path) == SESSION_ID]
    messages = visible_messages(paths)
    chat = transcript(messages)
    prompts = [tokenizer.encode(rendered_prompt(tokenizer, chat, item), add_special_tokens=False) for item in QUESTIONS]
    prefix = common_prefix(prompts)
    suffixes = [tokens[len(prefix):] for tokens in prompts]
    if len(prefix) < 10_000 or any(not suffix for suffix in suffixes):
        raise RuntimeError("The common whole-chat prefix was not constructed")

    prefix_tensor = torch.tensor([prefix], dtype=torch.long)
    prefill_started = time.perf_counter()
    with torch.inference_mode():
        prefix_cache = model(input_ids=prefix_tensor, use_cache=True).past_key_values
    prefill_seconds = time.perf_counter() - prefill_started
    initial_length = prefix_cache.get_seq_length()
    measured_bytes = cache_bytes(prefix_cache)

    answers = []
    for item, suffix in zip(QUESTIONS, suffixes):
        result = answer(model, tokenizer, prefix_cache, len(prefix), suffix, 220)
        if prefix_cache.get_seq_length() != initial_length:
            raise RuntimeError("The immutable prefix cache was mutated")
        answers.append({**item, **result})
        print(json.dumps({"finished": item["id"], "seconds": result["cached_total_seconds"]}), flush=True)

    output = {
        "schema_version": "0.1-private",
        "model": spec,
        "conversation": {
            "label": "CHAT-A",
            "visible_messages": len(messages),
            "common_prefix_tokens": len(prefix),
        },
        "cache": {
            "sequence_length": initial_length,
            "bytes": measured_bytes,
            "gibibytes": round(measured_bytes / 1024**3, 6),
            "dtype": str(prefix_cache.layers[0].keys.dtype),
            "layers": len(prefix_cache.layers),
            "key_value_heads": int(prefix_cache.layers[0].keys.shape[1]),
            "head_dim": int(prefix_cache.layers[0].keys.shape[-1]),
        },
        "prefill_seconds": round(prefill_seconds, 3),
        "answers": answers,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
