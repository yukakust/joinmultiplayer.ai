#!/usr/bin/env python3
"""Create the reviewed, privacy-safe public Gate 16D.3 result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REVIEWS = {
    "P01": (True, "Подтверждено, но ответ почти повторяет сам вопрос."),
    "P02": (True, "Верное сравнение swarm и exact RAG."),
    "P03": (True, "Верно передана граница IDAT против ancillary/APNG chunks."),
    "P04": (True, "Верно описан подписанный аудит синтетического трафика."),
    "P05": (True, "Верно описаны Bitbucket checkout и ограничения sandbox."),
    "P06": (True, "Верно описана пропущенная проверка rootName."),
    "P07": (False, "Само утверждение верно, но указано M0004; настоящее доказательство находится в M0021."),
    "P08": (True, "Верно описаны установленный plugin и необходимость перезапуска Codex."),
    "N01": (False, "Ложный FOUND: разговор о plugin не содержит аудита переноса системы-куратора."),
    "N02": (True, "Верный EMPTY."),
    "N03": (True, "Верный EMPTY."),
    "N04": (False, "Ложный FOUND: разговор о переносе проекта не содержит подписанного аудита трафика."),
    "N05": (True, "Верный EMPTY."),
    "N06": (False, "Ложный FOUND: PNG-ревью не содержит проверки rootName receipt."),
    "N07": (True, "Верный EMPTY."),
    "N08": (True, "Верный EMPTY."),
}


def build(private: dict, questions: dict) -> dict:
    question_map = {item["id"]: item["question"] for item in questions["queries"]}
    rows = []
    for row in private["rows"]:
        accepted, note = REVIEWS[row["id"]]
        rows.append({
            "id": row["id"], "kind": row["kind"],
            "question": question_map[row["query_id"]],
            "conversation": row["card_id"], "qwen_choice": row["receipt"],
            "claim": row.get("claim"),
            "evidence_message_ids": row.get("evidence_message_ids", []),
            "accepted": accepted, "review": note,
            "input_tokens": row["input_tokens"],
            "runtime_seconds": row["runtime_seconds"],
        })
    return {
        "schema_version": "0.1", "experiment": "E007", "gate": "16D.3",
        "status": "FAIL",
        "protocol": "/experiments/E007/whole-chat-reader-gate16d3-protocol-v0.1.json",
        "model": private["model"], "revision": private["revision"],
        "summary": {
            "valid_tool_receipts": "16/16",
            "positive_found_with_accepted_evidence": "7/8",
            "negative_empty": "5/8",
            "human_accepted": f'{sum(accepted for accepted, _ in REVIEWS.values())}/16',
        },
        "rows": rows,
        "findings": [
            "A whole short conversation fits comfortably and every run completed a tool call.",
            "Qwen often extracts the right claim and exact message evidence.",
            "Three irrelevant conversations produced false FOUND by repeating the question as a claim.",
            "The test questions ask where knowledge was discussed, so several positive claims are shallow. A later end-to-end test needs real user problems, not only retrieval questions."
        ],
        "decision": "Do not accept the reader yet. Keep the one-question/one-chat/tool contract, but prevent question copying from counting as evidence and retest with real information-seeking questions.",
        "privacy": "No source conversation text, raw model output, paths, hashes or session identifiers are public."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    result = build(
        json.loads(args.input.read_text(encoding="utf-8")),
        json.loads(args.questions.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
