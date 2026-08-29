#!/usr/bin/env python3
"""Run the locked E007 Gate 16B.1 whole-conversation reader test locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/whole-chat-reader-protocol-v0.1.json"

CASES = [
    {
        "label": "CHAT-A",
        "session_id": "01a01ddb-510a-78c3-bd80-97f8a68b1b79",
        "questions": [
            {
                "id": "A1",
                "question": "Почему повтор исходного вопроса в конце текстового промпта не защищает систему от злонамеренной персональной дельты?",
                "gold": "Дельта входит в скрытое состояние после текстовых инструкций/tokenizer, поэтому текстовая эвристика не ограничивает её влияние.",
            },
            {
                "id": "A2",
                "question": "Как именно было решено переживать отключение лучшего шахматного эксперта: копировать его или выбрать нескольких разных экспертов?",
                "gold": "Выбрать top-2 разных шахматных pocket i параллельно; незавершённый вклад отбросить целиком и использовать полностью завершившийся.",
            },
            {
                "id": "A3",
                "question": "Что на yukabox уже было готово для запуска моделей, а какого стека не хватало именно для обучения собственного delta-merger?",
                "gold": "Ollama с ROCm уже был готов для инференса; отдельного PyTorch/ROCm-стека для обучения delta-merger не было.",
            },
        ],
    },
    {
        "label": "CHAT-B",
        "session_id": "01a01dfa-eaa3-7373-b106-f1a568e9dcc6",
        "questions": [
            {
                "id": "B1",
                "question": "Как называлась предложенная система из общей модели, множества суверенных i, маршрутизации и графа доказательств?",
                "gold": "Mixture of Intelligences (MoI).",
            },
            {
                "id": "B2",
                "question": "Какой точный инвариант должен выполнять совершенно свежий персональный нейронный трек до того, как чему-либо научился?",
                "gold": "Свежая персональная ветвь должна давать delta около/строго нуля и не менять общий результат.",
            },
            {
                "id": "B3",
                "question": "Как после исправления P0 два персональных сигнала, общий z0 и финальные слои соединялись в итоговые logits?",
                "gold": "Две delta дают ограниченное обновление; оно прибавляется к z0; FinalLayers строят logits из z0 + bounded Merge(delta1, delta2).",
            },
        ],
    },
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def session_id(path: Path) -> str | None:
    found = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        record = json.loads(line)
        payload = record.get("payload")
        if record.get("type") == "session_meta" and isinstance(payload, dict):
            found = payload.get("id") or payload.get("session_id") or found
    return str(found) if found else None


def is_automatic_user_block(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("<recommended_plugins>") or stripped.startswith("<environment_context>")


def visible_messages(paths: list[Path]) -> list[dict]:
    seen: set[str] = set()
    messages = []
    for path in sorted(paths):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
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
            if not text or (role == "user" and is_automatic_user_block(text)):
                continue
            identifier = str(payload.get("id") or hashlib.sha256((role + "\0" + text).encode()).hexdigest())
            if identifier in seen:
                continue
            seen.add(identifier)
            messages.append({"role": role, "phase": payload.get("phase"), "text": text})
    return messages


def render_transcript(messages: list[dict]) -> str:
    return "\n\n".join(
        f"[M{index:04d} | {message['role']} | {message.get('phase') or 'message'}]\n{message['text']}"
        for index, message in enumerate(messages, 1)
    )


def prompt(case: dict, transcript: str | None) -> str:
    questions = "\n".join(f"{item['id']}. {item['question']}" for item in case["questions"])
    context = transcript if transcript is not None else "[РАЗГОВОР НЕ ПЕРЕДАН]"
    return f"""Ниже дан разговор и три вопроса о конкретных решениях внутри него.
Отвечай только по разговору. Не используй внешние знания и не додумывай.
Если ответа нет, напиши NOT_FOUND.
Для каждого ответа обязательно укажи номера подтверждающих сообщений M0001 и т.п.

РАЗГОВОР:
<transcript>
{context}
</transcript>

ВОПРОСЫ:
{questions}

Верни строго JSON-массив из трёх объектов:
[
  {{"id":"A1", "answer":"...", "evidence":["M0001"]}}
]"""


def generate(model, tokenizer, user_prompt: str, max_new_tokens: int) -> dict:
    messages = [
        {"role": "system", "content": "Ты аккуратный читатель. Ответы должны опираться только на переданный разговор."},
        {"role": "user", "content": user_prompt},
    ]
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer(rendered, return_tensors="pt", add_special_tokens=False)
    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = output[0, inputs.input_ids.shape[1]:]
    return {
        "prompt_tokens": int(inputs.input_ids.shape[1]),
        "new_tokens": int(new_tokens.shape[0]),
        "seconds": round(time.perf_counter() - started, 3),
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
    protocol = read_json(PROTOCOL)
    if protocol["status"] != "locked_before_inference":
        raise RuntimeError("Protocol must be locked before inference")

    torch.set_num_threads(args.threads)
    torch.manual_seed(29082026)
    model_spec = protocol["model"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"], local_files_only=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_spec["repository"], revision=model_spec["revision"], local_files_only=True,
        dtype=torch.bfloat16,
    ).eval()

    by_id: dict[str, list[Path]] = {}
    for path in args.sessions.rglob("*.jsonl"):
        identifier = session_id(path)
        if identifier:
            by_id.setdefault(identifier, []).append(path)

    records = []
    for case in CASES:
        messages = visible_messages(by_id.get(case["session_id"], []))
        if not messages:
            raise RuntimeError(f"Conversation missing: {case['label']}")
        transcript = render_transcript(messages)
        transcript_tokens = len(tokenizer.encode(transcript, add_special_tokens=False))
        if not 10_000 <= transcript_tokens <= 16_000:
            raise RuntimeError(f"{case['label']} outside locked size: {transcript_tokens}")
        full = generate(model, tokenizer, prompt(case, transcript), 768)
        control = generate(model, tokenizer, prompt(case, None), 768)
        records.append({
            "label": case["label"],
            "transcript_tokens": transcript_tokens,
            "messages": len(messages),
            "questions": case["questions"],
            "with_transcript": full,
            "without_transcript": control,
        })
        print(json.dumps({"finished": case["label"], "tokens": transcript_tokens}), flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": "0.1-private",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "model": model_spec,
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
