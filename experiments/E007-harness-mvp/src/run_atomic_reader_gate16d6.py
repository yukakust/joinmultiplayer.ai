#!/usr/bin/env python3
"""Run Gate 16D.6 as separate locator, extractor and code-only composer stages."""

from __future__ import annotations

import argparse
import html
import json
import time
import urllib.request
from pathlib import Path


LOCATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "select_evidence",
            "description": "Select the smallest exact message set that answers this one atomic question. Do not answer the question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    }
                },
                "required": ["message_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_empty",
            "description": "Use when the conversation does not answer this atomic question.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

EXTRACTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_atom_answer",
            "description": "Answer this one atomic question using only the selected evidence messages.",
            "parameters": {
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
            },
        },
    }
]


def render(messages: list[dict]) -> str:
    return "\n\n".join(
        f'<message id="{item["id"]}" role="{item["role"]}">\n{html.escape(item["text"])}\n</message>'
        for item in messages
    )


def request_tool(endpoint: str, system: str, user: str, tools: list[dict]) -> tuple[dict, float]:
    body = {
        "model": "qwen3-8b-q4-k-m",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": "/no_think\n\n" + user}],
        "tools": tools,
        "tool_choice": "auto",
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0,
        "max_tokens": 256,
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


def parse_call(message: dict) -> tuple[str, dict]:
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        raise ValueError(f"expected one tool call, got {len(calls)}")
    function = calls[0]["function"]
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments are not an object")
    return function["name"], arguments


def run_locator(endpoint: str, atom: dict, conversation: dict) -> dict:
    valid_ids = {item["id"] for item in conversation["messages"]}
    user = (
        f"CONVERSATION:\n{render(conversation['messages'])}\n\n"
        f"ONE ATOMIC QUESTION:\n{atom['question']}\n\n"
        "Do only location. If exact messages answer the atomic question, call select_evidence with their IDs. "
        "Otherwise call send_empty. Do not write or summarize the answer. Call exactly one tool."
    )
    response, seconds = request_tool(
        endpoint,
        "You are only an evidence locator. You may select message IDs or return EMPTY. You are forbidden to answer the question.",
        user,
        LOCATOR_TOOLS,
    )
    message = response["choices"][0]["message"]
    row = {"runtime_seconds": round(seconds, 3), "usage": response.get("usage", {}), "raw_message": message}
    try:
        name, arguments = parse_call(message)
        if name == "send_empty":
            row.update(receipt="EMPTY", evidence_message_ids=[])
        elif name == "select_evidence":
            evidence = arguments.get("message_ids")
            if (
                not isinstance(evidence, list)
                or not 1 <= len(evidence) <= 3
                or any(item not in valid_ids for item in evidence)
            ):
                raise ValueError("invalid evidence IDs")
            row.update(receipt="EVIDENCE", evidence_message_ids=evidence)
        else:
            raise ValueError("unknown locator tool")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        row.update(receipt="ERROR", evidence_message_ids=[], error=str(error))
    return row


def run_extractor(endpoint: str, atom: dict, evidence_messages: list[dict]) -> dict:
    user = (
        f"ONE ATOMIC QUESTION:\n{atom['question']}\n\n"
        f"SELECTED EVIDENCE ONLY:\n{render(evidence_messages)}\n\n"
        "Do only extraction. Answer the atomic question in one short complete sentence using only these messages. "
        "Call send_atom_answer exactly once."
    )
    response, seconds = request_tool(
        endpoint,
        "You are only an atomic answer extractor. The search is already complete. Use no outside knowledge and add nothing beyond the selected evidence.",
        user,
        EXTRACTOR_TOOLS,
    )
    message = response["choices"][0]["message"]
    row = {"runtime_seconds": round(seconds, 3), "usage": response.get("usage", {}), "raw_message": message}
    try:
        name, arguments = parse_call(message)
        answer = arguments.get("answer")
        if name != "send_atom_answer" or not isinstance(answer, str) or not answer.strip():
            raise ValueError("invalid atom answer")
        row.update(receipt="ANSWER", answer=answer.strip())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        row.update(receipt="ERROR", answer=None, error=str(error))
    return row


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
    cases = []
    for question in protocol["questions"]:
        for atom in question["atoms"]:
            for kind, card_key in (("positive", "gold_card_id"), ("negative", "negative_card_id")):
                cases.append({"question": question, "atom": atom, "kind": kind, "card_id": question[card_key]})
    cases.sort(key=lambda item: (item["card_id"], item["question"]["id"], item["atom"]["id"], item["kind"]))

    locator_rows = []
    for case in cases:
        locator = run_locator(args.endpoint, case["atom"], conversations[case["card_id"]])
        row = {
            "id": f'{case["kind"][0].upper()}{case["question"]["id"]}-{case["atom"]["id"]}',
            "kind": case["kind"],
            "question_id": case["question"]["id"],
            "atom_id": case["atom"]["id"],
            "atom_question": case["atom"]["question"],
            "card_id": case["card_id"],
            **locator,
        }
        if case["kind"] == "positive":
            row["accepted_evidence"] = case["atom"]["accepted_evidence"]
            row["required_meaning"] = case["atom"]["required_meaning"]
            row["locator_pass"] = row["receipt"] == "EVIDENCE" and bool(
                set(row["evidence_message_ids"]) & set(case["atom"]["accepted_evidence"])
            )
        else:
            row["locator_pass"] = row["receipt"] == "EMPTY"
        locator_rows.append(row)
        print(json.dumps({"stage": "locator", "id": row["id"], "receipt": row["receipt"], "evidence": row["evidence_message_ids"], "pass": row["locator_pass"]}), flush=True)

    extractor_rows = []
    for locator in locator_rows:
        if locator["kind"] != "positive" or locator["receipt"] != "EVIDENCE":
            continue
        conversation = conversations[locator["card_id"]]
        by_id = {item["id"]: item for item in conversation["messages"]}
        evidence_messages = [by_id[item] for item in locator["evidence_message_ids"]]
        atom = next(
            atom
            for question in protocol["questions"] if question["id"] == locator["question_id"]
            for atom in question["atoms"] if atom["id"] == locator["atom_id"]
        )
        extractor = run_extractor(args.endpoint, atom, evidence_messages)
        row = {
            "id": locator["id"],
            "question_id": locator["question_id"],
            "atom_id": locator["atom_id"],
            "atom_question": locator["atom_question"],
            "evidence_message_ids": locator["evidence_message_ids"],
            "required_meaning": locator["required_meaning"],
            **extractor,
        }
        extractor_rows.append(row)
        print(json.dumps({"stage": "extractor", "id": row["id"], "receipt": row["receipt"], "answer": row.get("answer")}, ensure_ascii=False), flush=True)

    extractors = {row["id"]: row for row in extractor_rows}
    compositions = []
    for question in protocol["questions"]:
        answers = [extractors.get(f'P{question["id"]}-{atom["id"]}', {}).get("answer") for atom in question["atoms"]]
        compositions.append(
            {
                "question_id": question["id"],
                "question": question["text"],
                "atom_answers": answers,
                "composed_answer": " ".join(answer for answer in answers if answer),
                "complete_receipts": all(answers),
            }
        )

    result = {
        "schema_version": "0.1-private",
        "experiment": "E007",
        "gate": "16D.6",
        "protocol": str(args.protocol),
        "locator_rows": locator_rows,
        "extractor_rows": extractor_rows,
        "compositions": compositions,
        "mechanical_summary": {
            "valid_locator_receipts": sum(row["receipt"] != "ERROR" for row in locator_rows),
            "positive_atom_evidence_hits": sum(row["kind"] == "positive" and row["locator_pass"] for row in locator_rows),
            "negative_atom_empty": sum(row["kind"] == "negative" and row["locator_pass"] for row in locator_rows),
            "valid_extractor_receipts": sum(row["receipt"] == "ANSWER" for row in extractor_rows),
            "complete_compositions": sum(row["complete_receipts"] for row in compositions),
        },
        "status": "awaiting_human_atom_review",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
