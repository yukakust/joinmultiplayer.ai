#!/usr/bin/env python3
"""Run locked Gate 16D.7: one message location and one-fact extraction."""

from __future__ import annotations

import argparse
import html
import json
import time
import urllib.request
from pathlib import Path


LOCATOR_TOOLS = [
    {"type":"function","function":{"name":"select_one_message","description":"Select the one message that contains the answer to this one-fact question.","parameters":{"type":"object","properties":{"message_id":{"type":"string"}},"required":["message_id"]}}},
    {"type":"function","function":{"name":"send_empty","description":"Use only when no message answers this one-fact question.","parameters":{"type":"object","properties":{}}}},
]
EXTRACTOR_TOOLS = [
    {"type":"function","function":{"name":"send_one_fact","description":"Return only the one fact requested by the question.","parameters":{"type":"object","properties":{"fact":{"type":"string"}},"required":["fact"]}}}
]


def render(messages: list[dict]) -> str:
    return "\n\n".join(f'<message id="{m["id"]}" role="{m["role"]}">\n{html.escape(m["text"])}\n</message>' for m in messages)


def request_tool(endpoint: str, model: str, system: str, user: str, tools: list[dict]) -> tuple[dict, float]:
    body = {
        "model": model,
        "messages": [{"role":"system","content":system},{"role":"user","content":"/no_think\n\n"+user}],
        "tools": tools,
        "tool_choice": "auto",
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0,
        "max_tokens": 128,
    }
    req = urllib.request.Request(endpoint.rstrip("/")+"/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=1800) as response:
        result = json.load(response)
    return result, time.monotonic()-started


def parse_call(message: dict) -> tuple[str, dict]:
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        raise ValueError(f"expected one tool call, got {len(calls)}")
    function = calls[0]["function"]
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    return function["name"], arguments


def locate(endpoint: str, model: str, fact: dict, messages: list[dict]) -> dict:
    response, seconds = request_tool(
        endpoint, model,
        "You only locate one message. Never answer or summarize. Call exactly one tool.",
        f"CONVERSATION:\n{render(messages)}\n\nONE-FACT QUESTION:\n{fact['question']}\n\nSelect exactly one answering message ID, or EMPTY if none answers it.",
        LOCATOR_TOOLS,
    )
    message = response["choices"][0]["message"]
    row = {"seconds":round(seconds,3),"usage":response.get("usage",{}),"raw_message":message}
    try:
        name, args = parse_call(message)
        valid = {m["id"] for m in messages}
        if name == "send_empty":
            row.update(receipt="EMPTY", message_id=None)
        elif name == "select_one_message" and args.get("message_id") in valid:
            row.update(receipt="MESSAGE", message_id=args["message_id"])
        else:
            raise ValueError("invalid locator choice")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        row.update(receipt="ERROR", message_id=None, error=str(error))
    return row


def extract(endpoint: str, model: str, fact: dict, message: dict) -> dict:
    response, seconds = request_tool(
        endpoint, model,
        "You extract exactly one requested fact from one message. Use no outside knowledge. Call exactly one tool.",
        f"ONE-FACT QUESTION:\n{fact['question']}\n\nONE SELECTED MESSAGE:\n{render([message])}\n\nReturn one short sentence containing only the requested fact.",
        EXTRACTOR_TOOLS,
    )
    raw = response["choices"][0]["message"]
    row = {"seconds":round(seconds,3),"usage":response.get("usage",{}),"raw_message":raw}
    try:
        name, args = parse_call(raw)
        value = args.get("fact")
        if name != "send_one_fact" or not isinstance(value, str) or not value.strip():
            raise ValueError("invalid fact")
        row.update(receipt="FACT", fact=value.strip())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        row.update(receipt="ERROR", fact=None, error=str(error))
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:22118")
    parser.add_argument("--model", default="qwen3-8b-q4-k-m")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    payload = json.loads(args.payload.read_text())
    protocol = json.loads(args.protocol.read_text())
    conversations = {f'{payload["node"]}-C{i:04d}':c for i,c in enumerate(payload["conversations"],1)}
    rows = []
    for question in protocol["questions"]:
        conversation = conversations[question["gold_card_id"]]
        by_id = {m["id"]:m for m in conversation["messages"]}
        for fact in question["facts"]:
            locator = locate(args.endpoint,args.model,fact,conversation["messages"])
            locator_pass = locator["receipt"] == "MESSAGE" and locator["message_id"] in fact["accepted_evidence"]
            extractor = None
            if locator["receipt"] == "MESSAGE":
                extractor = extract(args.endpoint,args.model,fact,by_id[locator["message_id"]])
            row = {
                "id":f'{question["id"]}-{fact["id"]}',"question_id":question["id"],"fact_id":fact["id"],
                "fact_question":fact["question"],"required_meaning":fact["required_meaning"],
                "accepted_evidence":fact["accepted_evidence"],"locator":locator,"locator_pass":locator_pass,
                "extractor":extractor,
            }
            rows.append(row)
            print(json.dumps({"id":row["id"],"message":locator["message_id"],"locator_pass":locator_pass,"fact":extractor and extractor.get("fact")},ensure_ascii=False),flush=True)
    by_question = {}
    for row in rows:
        by_question.setdefault(row["question_id"],[]).append(row)
    compositions = []
    for question in protocol["questions"]:
        ordered = by_question[question["id"]]
        answers = [r["extractor"].get("fact") for r in ordered if r["extractor"] and r["extractor"]["receipt"] == "FACT"]
        compositions.append({"question_id":question["id"],"question":question["text"],"facts":answers,"composed_answer":" ".join(answers),"complete_receipts":len(answers)==len(question["facts"])})
    result = {"schema_version":"0.1-private","experiment":"E007","gate":"16D.7","status":"awaiting_human_review","rows":rows,"compositions":compositions,"mechanical_summary":{"valid_locator_receipts":sum(r["locator"]["receipt"]!="ERROR" for r in rows),"correct_message":sum(r["locator_pass"] for r in rows),"valid_fact_receipts":sum(bool(r["extractor"] and r["extractor"]["receipt"]=="FACT") for r in rows),"complete_receipts":sum(c["complete_receipts"] for c in compositions)}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")


if __name__ == "__main__":
    main()
