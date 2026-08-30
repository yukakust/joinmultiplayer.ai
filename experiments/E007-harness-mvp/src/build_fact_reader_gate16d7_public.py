#!/usr/bin/env python3
"""Build reviewed, privacy-safe Gate 16D.7 output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REVIEWS = {
    "Q02-F1": (True, "Точность 100% найдена."),
    "Q02-F2": (True, "Все пять значений N найдены."),
    "Q02-F3": (True, "Результат exact RAG найден."),
    "Q02-F4": (True, "Результат symbolic ensemble найден."),
    "Q02-F5": (False, "Вместо «преимущество не доказано» снова повторила 100% swarm."),
    "Q06-F1": (False, "Выбрала соседнюю проблему C4 вместо fresh unrestricted record."),
    "Q06-F2": (False, "Выбрала соседнюю проблему C4 вместо random correlation."),
    "Q06-F3": (False, "Не сказала, что первый socket закрывал весь audit или singleton array."),
    "Q06-F4": (False, "Не сказала, что другие concurrent sockets выпадали из audit."),
    "Q06-F5": (False, "Не назвала оба превышаемых лимита: maxHttpRequests и maxBytes."),
    "Q07-F1": (False, "Сказала лишь «состояние корректное», но не зафиксировала clean tracking branch."),
    "Q07-F2": (True, "Exact candidate SHA найден."),
    "Q07-F3": (False, "Bitbucket назван, но потеряно важное свойство owner-private."),
    "Q07-F4": (True, "Docker socket найден."),
    "Q07-F5": (True, "Loopback curl найден."),
    "Q08-F1": (True, "Поле root.manifest.rootName найдено."),
    "Q08-F2": (True, "Имя из receiptReference найдено."),
    "Q08-F3": (True, "Отсутствующее сравнение равенства найдено."),
    "Q08-F4": (True, "Copied или misrouted root передан по смыслу как неправильный root."),
    "Q08-F5": (True, "Ссылка очереди на другой root найдена."),
    "Q09-F1": (True, "Получатель Dianach найден."),
    "Q09-F2": (True, "Репозиторий найден."),
    "Q09-F3": (True, "Уровень write найден."),
    "Q09-F4": (True, "Отправленное приглашение найдено."),
    "Q09-F5": (True, "Необходимость принять приглашение найдена."),
}


def answer_of(row: dict) -> str | None:
    extractor = row.get("extractor") or {}
    return extractor.get("fact") or (extractor.get("raw_message") or {}).get("content") or None


def build(private: dict, protocol: dict) -> dict:
    rows = []
    grouped: dict[str, list[dict]] = {}
    for source in private["rows"]:
        meaning_passed, review = REVIEWS[source["id"]]
        public = {
            "id": source["id"],
            "question_id": source["question_id"],
            "fact_id": source["fact_id"],
            "fact_question": source["fact_question"],
            "selected_message_id": source["locator"].get("message_id"),
            "locator_passed": source["locator_pass"],
            "answer": answer_of(source),
            "tool_format_passed": bool(source.get("extractor") and source["extractor"].get("receipt") == "FACT"),
            "meaning_passed": meaning_passed,
            "review": review,
        }
        rows.append(public)
        grouped.setdefault(source["question_id"], []).append(public)

    composition_by_id = {item["question_id"]: item for item in private["compositions"]}
    protocol_by_id = {item["id"]: item for item in protocol["questions"]}
    questions = []
    for question_id in sorted(grouped):
        facts = grouped[question_id]
        complete = all(item["locator_passed"] and item["meaning_passed"] for item in facts)
        questions.append({
            "question_id": question_id,
            "question": protocol_by_id[question_id]["text"],
            "facts": facts,
            "code_joined_answer": " ".join(item["answer"] for item in facts if item["answer"]),
            "complete": complete,
        })

    return {
        "schema_version": "0.1",
        "experiment": "E007",
        "gate": "16D.7",
        "status": "completed_failed",
        "protocol": "/experiments/E007/fact-reader-gate16d7-protocol-v0.1.json",
        "model": "Qwen3-8B Q4_K_M",
        "summary": {
            "valid_locator_receipts": private["mechanical_summary"]["valid_locator_receipts"],
            "correct_message": sum(item["locator_passed"] for item in rows),
            "tool_format_passed": sum(item["tool_format_passed"] for item in rows),
            "fact_meanings_preserved": sum(item["meaning_passed"] for item in rows),
            "fact_meanings_possible": len(rows),
            "complete_hard_questions": sum(item["complete"] for item in questions),
            "complete_hard_questions_possible": len(questions),
            "baseline_complete_hard_questions": 0,
            "gate_passed": False,
        },
        "questions": questions,
        "decision": "One-fact calls recovered two previously failed answers, but missed the locked 4/5 gate. Finer decomposition helps some cases but does not fix evidence location or implication questions by itself.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(json.loads(args.private.read_text()), json.loads(args.protocol.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
