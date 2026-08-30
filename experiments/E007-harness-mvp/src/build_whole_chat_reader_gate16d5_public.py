#!/usr/bin/env python3
"""Build the reviewed privacy-safe public Gate 16D.5 result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


POSITIVE_REVIEW = {
    "P01": (2, "Полный ответ: подтверждённые части переноса и мусорные partial-файлы названы правильно."),
    "P02": (2, "Полный ответ: найдены и 100% swarm, и равные 100% у exact RAG и symbolic ensemble."),
    "P03": (2, "Полный ответ: названы обе причины провала и изменения следующего запуска."),
    "P04": (1, "Найден точный объём 419 532 800 байт, но не объяснено, что лимит проверял IDAT и пропускал fdAT."),
    "P05": (1, "Правильно найден synthetic upstream и основное исправление, но потеряно требование привязать peer identity к аудиту."),
    "P06": (1, "Основная причина превышения бюджета найдена, но пропущена роль первого закрывшегося socket; кроме того, указано неполное сообщение-доказательство."),
    "P07": (1, "Названы exact SHA и обе заблокированные проверки, но потерян подтверждённый owner-private Bitbucket remote."),
    "P08": (1, "Пропущенная проверка rootName названа точно, но последствие сведено к слишком общему «неправильному происхождению»."),
    "P09": (2, "Полный ответ: Dianach, write и необходимость принять приглашение."),
    "P10": (2, "Полный ответ: hook отсутствовал в уже открытой задаче и перечислены нужные действия."),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private = json.loads(args.private.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    questions = {item["id"]: item for item in protocol["questions"]}

    rows = []
    for source in sorted(private["rows"], key=lambda item: item["id"]):
        question = questions[source["question_id"]]
        if source["kind"] == "positive":
            meaning_score, review = POSITIVE_REVIEW[source["id"]]
            accepted = meaning_score == 2 and source["mechanical_pass"]
        else:
            meaning_score = None
            accepted = source["receipt"] == "EMPTY"
            review = (
                "Верный EMPTY: чужой разговор не использован."
                if accepted
                else "Ложный FOUND: найден другой provenance-дефект из похожей темы, но не ответ на заданный вопрос."
            )
        rows.append(
            {
                "id": source["id"],
                "kind": source["kind"],
                "question_id": source["question_id"],
                "question": source["question"],
                "conversation": "правильный полный чат" if source["kind"] == "positive" else "зафиксированный чужой чат",
                "qwen_choice": source["receipt"],
                "claim": source.get("claim"),
                "evidence_message_ids": source.get("evidence_message_ids", []),
                "expected_meaning": question["required_meaning"] if source["kind"] == "positive" else [],
                "meaning_score": meaning_score,
                "meaning_possible": 2 if source["kind"] == "positive" else None,
                "evidence_passed": source["mechanical_pass"] if source["kind"] == "positive" else None,
                "accepted": accepted,
                "review": review,
            }
        )

    positive = [row for row in rows if row["kind"] == "positive"]
    negative = [row for row in rows if row["kind"] == "negative"]
    result = {
        "schema_version": "0.1",
        "experiment": "E007",
        "gate": "16D.5",
        "status": "completed_failed",
        "protocol": "/experiments/E007/whole-chat-reader-gate16d5-protocol-v0.1.json",
        "model": "Qwen3-8B Q4_K_M",
        "rows": rows,
        "summary": {
            "valid_receipts": sum(row["qwen_choice"] != "ERROR" for row in rows),
            "positive_found": sum(row["qwen_choice"] == "FOUND" for row in positive),
            "positive_evidence_passed": sum(bool(row["evidence_passed"]) for row in positive),
            "positive_meanings_preserved": sum(row["meaning_score"] for row in positive),
            "positive_meanings_possible": 20,
            "positive_complete_answers": sum(row["meaning_score"] == 2 and row["evidence_passed"] for row in positive),
            "negative_empty": sum(row["qwen_choice"] == "EMPTY" for row in negative),
            "gate_passed": False,
        },
        "decision": "The question-copy shortcut is removed. The reader reliably finds useful knowledge, but it often drops one required part of a multi-part answer and can confuse a nearby defect with the requested defect. Add a completeness and exact-claim-to-evidence check before accepting the reader.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
