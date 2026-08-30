#!/usr/bin/env python3
"""Build reviewed, privacy-safe Gate 16D.8 output."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REVIEWS = {
    "Q02-retrieved_shelf": (True, True, "Все результаты и вывод «преимущество не доказано» сохранены."),
    "Q02-oracle_shelf": (True, True, "Полный ответ; дополнительное сообщение не изменило вывод."),
    "Q06-retrieved_shelf": (False, False, "Нужного M0006 на полке не было. Qwen додумала local budgets и другие детали вместо честной остановки."),
    "Q06-oracle_shelf": (True, True, "С M0006 найдены fresh records, random correlations, первый socket, пропущенные sockets и оба лимита."),
    "Q07-retrieved_shelf": (True, False, "Все пять нужных частей сохранены, но в конце ошибочно сказано, что заблокированные проверки были выполнены."),
    "Q07-oracle_shelf": (True, False, "Все пять нужных частей сохранены, но добавлена та же неподтверждённая фраза о выполненных проверках."),
    "Q08-retrieved_shelf": (True, True, "Все части provenance-дефекта сохранены."),
    "Q08-oracle_shelf": (True, True, "Все части provenance-дефекта сохранены."),
    "Q09-retrieved_shelf": (True, True, "Получатель, репозиторий, write, приглашение и следующий шаг сохранены."),
    "Q09-oracle_shelf": (True, True, "Получатель, репозиторий, write, приглашение и следующий шаг сохранены."),
}


def sanitize(text: str | None) -> str | None:
    if text is None:
        return None
    # Keep the cited filename/line label, never publish a private absolute path.
    return re.sub(r"\]\(/home/[^)]+\)", "]", text)


def build(private: dict) -> dict:
    rows = []
    for source in private["rows"]:
        complete, grounded, review = REVIEWS[source["id"]]
        rows.append({
            "id": source["id"],
            "question_id": source["question_id"],
            "condition": source["condition"],
            "question": source["question"],
            "message_ids": source["message_ids"],
            "answer": sanitize(source["answer"]),
            "complete": complete,
            "grounded": grounded,
            "review": review,
        })
    retrieved = [row for row in rows if row["condition"] == "retrieved_shelf"]
    oracle = [row for row in rows if row["condition"] == "oracle_shelf"]
    return {
        "schema_version":"0.1",
        "experiment":"E007",
        "gate":"16D.8",
        "status":"completed_partial",
        "protocol":"/experiments/E007/shelf-synthesis-gate16d8-protocol-v0.1.json",
        "model":"Qwen3-8B Q4_K_M",
        "summary":{
            "valid_answers":sum(source["receipt"] == "ANSWER" for source in private["rows"]),
            "retrieved_shelf_complete":sum(row["complete"] for row in retrieved),
            "retrieved_shelf_possible":len(retrieved),
            "oracle_shelf_complete":sum(row["complete"] for row in oracle),
            "oracle_shelf_possible":len(oracle),
            "grounded_answers":sum(row["grounded"] for row in rows),
            "grounded_answers_possible":len(rows),
            "baseline_complete":2,
            "completeness_gate_passed":True,
            "unsupported_claim_gate_passed":False,
            "overall_gate_passed":False
        },
        "rows":rows,
        "decision":"Split retrieval plus whole-question synthesis fixed completeness, but the overall gate fails because synthesis invented details when evidence was missing and added an unsupported closing claim in Q07."
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=build(json.loads(args.private.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__":
    main()
