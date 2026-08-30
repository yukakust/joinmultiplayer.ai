#!/usr/bin/env python3
"""Run the locked Gate 16D.4 information-extraction comparison."""

from __future__ import annotations

import argparse
import html
import json
import time
import urllib.request
from pathlib import Path


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_found",
            "description": "Return a new answer learned from the conversation and its smallest supporting message set.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence_message_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                },
                "required": ["claim", "evidence_message_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_empty",
            "description": "Use when the conversation does not answer the question.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def render(messages: list[dict]) -> str:
    return "\n\n".join(
        f'<message id="{item["id"]}" role="{item["role"]}">\n{html.escape(item["text"])}\n</message>'
        for item in messages
    )


def complete(endpoint: str, question: str, messages: list[dict]) -> tuple[dict, float]:
    prompt = (
        f"/no_think\n\nQUESTION:\n{question}\n\nCONVERSATION:\n{render(messages)}\n\n"
        "Answer only from this conversation. The question does not contain its answer. "
        "If the conversation answers it, call send_found with a short complete answer and the smallest exact set of supporting message IDs. "
        "If it does not, call send_empty. Call exactly one tool."
    )
    body = {
        "model": "Qwen3-8B-BF16.gguf",
        "messages": [
            {
                "role": "system",
                "content": "Read one local conversation faithfully. Never copy the question as an answer. Never use outside knowledge or invent evidence.",
            },
            {"role": "user", "content": prompt},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0,
        "max_tokens": 512,
    }
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=1800) as response:
        result = json.load(response)
    return result, time.monotonic() - started


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:22118")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    conversations = {
        f'{payload["node"]}-C{index:04d}': item
        for index, item in enumerate(payload["conversations"], 1)
    }
    rows = []
    for case in protocol["cases"]:
        conversation = conversations[case["card_id"]]
        valid_ids = {item["id"] for item in conversation["messages"]}
        response, seconds = complete(
            args.endpoint, protocol["question"]["text"], conversation["messages"]
        )
        message = response["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        row = {
            "id": case["id"],
            "kind": case["kind"],
            "card_id": case["card_id"],
            "runtime_seconds": round(seconds, 3),
            "usage": response.get("usage", {}),
            "raw_message": message,
        }
        try:
            if len(calls) != 1:
                raise ValueError(f"expected one tool call, got {len(calls)}")
            function = calls[0]["function"]
            name = function["name"]
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if name not in {"send_found", "send_empty"} or not isinstance(arguments, dict):
                raise ValueError("unknown or malformed tool call")
            row["receipt"] = "FOUND" if name == "send_found" else "EMPTY"
            row["claim"] = arguments.get("claim") if name == "send_found" else None
            evidence = arguments.get("evidence_message_ids", []) if name == "send_found" else []
            if name == "send_found" and (
                not isinstance(row["claim"], str)
                or not row["claim"].strip()
                or not isinstance(evidence, list)
                or not 1 <= len(evidence) <= 3
                or any(item not in valid_ids for item in evidence)
            ):
                raise ValueError("invalid FOUND payload")
            row["evidence_message_ids"] = evidence
            if case["kind"] == "positive":
                row["mechanical_pass"] = name == "send_found" and bool(
                    set(evidence) & set(case["accepted_evidence"])
                )
            else:
                row["mechanical_pass"] = name == "send_empty"
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            row["receipt"] = "ERROR"
            row["error"] = str(error)
            row["mechanical_pass"] = False
        rows.append(row)
        print(json.dumps({key: row.get(key) for key in ("id", "receipt", "claim", "evidence_message_ids", "runtime_seconds")}, ensure_ascii=False), flush=True)

    result = {
        "schema_version": "0.1-private",
        "experiment": "E007",
        "gate": "16D.4",
        "protocol": str(args.protocol),
        "rows": rows,
        "status": "awaiting_human_meaning_review",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
