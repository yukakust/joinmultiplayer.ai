#!/usr/bin/env python3
"""Run the locked ten-question Gate 16D.5 reader comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_whole_chat_reader_gate16d4 import complete


def parse_receipt(message: dict, valid_ids: set[str]) -> tuple[str, str | None, list[str]]:
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        raise ValueError(f"expected one tool call, got {len(calls)}")
    function = calls[0]["function"]
    name = function["name"]
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if name == "send_empty" and isinstance(arguments, dict):
        return "EMPTY", None, []
    if name != "send_found" or not isinstance(arguments, dict):
        raise ValueError("unknown or malformed tool call")
    claim = arguments.get("claim")
    evidence = arguments.get("evidence_message_ids")
    if (
        not isinstance(claim, str)
        or not claim.strip()
        or not isinstance(evidence, list)
        or not 1 <= len(evidence) <= 3
        or any(item not in valid_ids for item in evidence)
    ):
        raise ValueError("invalid FOUND payload")
    return "FOUND", claim, evidence


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
        cases.append(
            {
                "id": "P" + question["id"][1:],
                "kind": "positive",
                "question": question,
                "card_id": question["gold_card_id"],
            }
        )
        cases.append(
            {
                "id": "N" + question["id"][1:],
                "kind": "negative",
                "question": question,
                "card_id": protocol["negative_pairing"][question["id"]],
            }
        )
    # Conversation-first prompts let llama.cpp reuse the same complete chat when
    # two different questions point at it. Ordering cannot change any score.
    cases.sort(key=lambda item: (item["card_id"], item["id"]))

    rows = []
    for case in cases:
        conversation = conversations[case["card_id"]]
        valid_ids = {item["id"] for item in conversation["messages"]}
        response, seconds = complete(
            args.endpoint,
            case["question"]["text"],
            conversation["messages"],
            model_name="qwen3-8b-q4-k-m",
            conversation_first=True,
        )
        message = response["choices"][0]["message"]
        row = {
            "id": case["id"],
            "kind": case["kind"],
            "question_id": case["question"]["id"],
            "question": case["question"]["text"],
            "card_id": case["card_id"],
            "runtime_seconds": round(seconds, 3),
            "usage": response.get("usage", {}),
            "raw_message": message,
        }
        try:
            receipt, claim, evidence = parse_receipt(message, valid_ids)
            row.update(receipt=receipt, claim=claim, evidence_message_ids=evidence)
            if case["kind"] == "positive":
                row["mechanical_pass"] = receipt == "FOUND" and bool(
                    set(evidence) & set(case["question"]["accepted_evidence"])
                )
                row["required_meaning"] = case["question"]["required_meaning"]
            else:
                row["mechanical_pass"] = receipt == "EMPTY"
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            row.update(receipt="ERROR", error=str(error), mechanical_pass=False)
        rows.append(row)
        print(
            json.dumps(
                {
                    key: row.get(key)
                    for key in ("id", "receipt", "claim", "evidence_message_ids", "runtime_seconds")
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    result = {
        "schema_version": "0.1-private",
        "experiment": "E007",
        "gate": "16D.5",
        "protocol": str(args.protocol),
        "rows": rows,
        "mechanical_summary": {
            "valid_receipts": sum(row["receipt"] != "ERROR" for row in rows),
            "positive_found_with_evidence": sum(
                row["kind"] == "positive" and row["mechanical_pass"] for row in rows
            ),
            "negative_empty": sum(
                row["kind"] == "negative" and row["mechanical_pass"] for row in rows
            ),
        },
        "status": "awaiting_human_meaning_review",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
