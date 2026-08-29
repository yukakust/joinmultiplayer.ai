#!/usr/bin/env python3
"""Run one locked E007 Gate 16B.5 lane against a local llama-server."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

from run_whole_chat_reader import CASES, prompt, render_transcript, session_id, visible_messages

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/llamacpp-cpu-rocm-protocol-v0.1.json"


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
    parser.add_argument("--lane", choices=("llamacpp_cpu", "llamacpp_rocm"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11439")
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
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
        started = time.perf_counter()
        response = post_json(
            f"{args.base_url.rstrip('/')}/v1/chat/completions",
            {
                "model": "qwen3-8b-bf16",
                "messages": [
                    {"role": "system", "content": "Ты аккуратный читатель. Ответы должны опираться только на переданный разговор."},
                    {"role": "user", "content": prompt(case, transcript)},
                ],
                "temperature": 0,
                "max_tokens": 768,
                "stream": False,
            },
            args.timeout,
        )
        choice = (response.get("choices") or [{}])[0]
        records.append({
            "label": case["label"],
            "message_count": len(messages),
            "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            "questions": case["questions"],
            "answer": choice.get("message", {}).get("content", ""),
            "finish_reason": choice.get("finish_reason"),
            "usage": response.get("usage"),
            "timings": response.get("timings"),
            "wall_seconds": round(time.perf_counter() - started, 3),
        })
        print(json.dumps({"finished": case["label"], "lane": args.lane}), flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": "0.1-private",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "lane": args.lane,
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
