#!/usr/bin/env python3
"""Run one locked Gate 16B.3 Ollama lane without publishing private chats."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

from run_whole_chat_reader import CASES, render_transcript, session_id, visible_messages

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/kv-cache-quantization-protocol-v0.1.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_prompt(case: dict, transcript: str) -> str:
    questions = "\n".join(f"{item['id']}. {item['question']}" for item in case["questions"])
    return f"""Прочитай разговор и ответь на три вопроса только по нему.
Не используй внешние знания. Если ответа нет, напиши NOT_FOUND.
Для каждого ответа укажи настоящий номер сообщения из разговора, где находится ответ.
Не копируй пример номера: найди фактический M-номер самостоятельно.

<transcript>
{transcript}
</transcript>

ВОПРОСЫ:
{questions}

Верни только JSON-массив из трёх объектов:
[{{"id":"{case['questions'][0]['id']}","answer":"краткий ответ","evidence":["M0123"]}}]"""


def post_json(url: str, payload: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, choices=("q8_kv", "q4_kv"))
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol = read_json(PROTOCOL)
    if protocol["status"] != "locked_before_inference":
        raise RuntimeError("Protocol must be locked before inference")

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
        prompt = build_prompt(case, transcript)
        started = time.perf_counter()
        response = post_json(
            f"{args.base_url.rstrip('/')}/api/chat",
            {
                "model": protocol["model"]["name"],
                "messages": [
                    {"role": "system", "content": "Ты аккуратный читатель частного разговора."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "think": False,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0,
                    "seed": 29082026,
                    "num_ctx": 16384,
                    "num_predict": 768,
                },
            },
            args.timeout,
        )
        records.append({
            "label": case["label"],
            "message_count": len(messages),
            "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            "questions": case["questions"],
            "answer": response.get("message", {}).get("content", ""),
            "prompt_eval_count": response.get("prompt_eval_count"),
            "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
            "eval_count": response.get("eval_count"),
            "eval_duration_ns": response.get("eval_duration"),
            "load_duration_ns": response.get("load_duration"),
            "total_duration_ns": response.get("total_duration"),
            "wall_seconds": round(time.perf_counter() - started, 3),
        })
        print(json.dumps({"finished": case["label"], "lane": args.lane}), flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": "0.1-private",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "lane": args.lane,
        "base_url": args.base_url,
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
