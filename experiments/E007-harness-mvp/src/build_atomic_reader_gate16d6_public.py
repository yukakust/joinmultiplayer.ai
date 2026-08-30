#!/usr/bin/env python3
"""Build the reviewed, privacy-safe public Gate 16D.6 result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REVIEWS = {
    "PQ01-A": (True, "Нашла подтверждённые dump, Git bundle и проверку корпуса."),
    "PQ01-B": (True, "Нашла незавершённые partial-файлы и верно объяснила, почему это не резервные копии."),
    "PQ02-A": (True, "Нашла 100% точность для всех размеров swarm."),
    "PQ02-B": (False, "Назвала другое верное ограничение эксперимента, но пропустила равные 100% у exact RAG и symbolic ensemble."),
    "PQ03-A": (True, "Нашла малое число испытаний и математически невозможный старый порог."),
    "PQ03-B": (True, "Нашла wrong-key control, 256 заданий и отдельную ревизию."),
    "PQ04-A": (True, "Нашла проверку IDAT и отсутствие проверки fdAT/ancillary-данных."),
    "PQ04-B": (True, "Вернула точный размер: 419 532 800 байт."),
    "PQ05-A": (True, "Верно объяснила, что трафик не дошёл до настоящей цели и реальная peer identity не проверялась."),
    "PQ05-B": (True, "Нашла test-only upstream, настоящий lifecycle target и привязку identity."),
    "PQ06-A": (False, "Выбрала не то сообщение и описала другую проблему C4 вместо свежих session records и случайных correlations."),
    "PQ06-B": (False, "Дала общий ответ, но потеряла три важных детали: первый socket, пропущенные concurrent sockets и общий budget."),
    "PQ07-A": (False, "Назвала clean branch и SHA, но потеряла owner-private Bitbucket remote."),
    "PQ07-B": (True, "Нашла обе заблокированные проверки: Docker socket и loopback curl."),
    "PQ08-A": (True, "Нашла отсутствующую проверку root.manifest.rootName против имени из receiptReference."),
    "PQ08-B": (False, "Слишком общий ответ: не объяснила, что чужой root мог пройти, пока очередь фиксировала другой."),
    "PQ09-A": (True, "Нашла Dianach и право write."),
    "PQ09-B": (False, "Выбрала не то сообщение и предложила добавить email вместо принятия GitHub-приглашения."),
    "PQ10-A": (True, "Нашла, что уже открытая задача не подхватила новый hook."),
    "PQ10-B": (True, "Верно перечислила перезапуск, новую задачу, разрешение hook и команду запуска."),
}


def build(private: dict, protocol: dict) -> dict:
    questions = {item["id"]: item for item in protocol["questions"]}
    locators = {item["id"]: item for item in private["locator_rows"]}
    extractors = {item["id"]: item for item in private["extractor_rows"]}
    compositions = {item["question_id"]: item for item in private["compositions"]}
    rows = []
    meanings = 0
    complete = 0

    for question_id in sorted(questions):
        question = questions[question_id]
        atoms = []
        question_complete = True
        for atom in question["atoms"]:
            row_id = f"P{question_id}-{atom['id']}"
            locator = locators[row_id]
            extractor = extractors[row_id]
            meaning_passed, review = REVIEWS[row_id]
            meanings += int(meaning_passed)
            question_complete = question_complete and locator["locator_pass"] and meaning_passed
            atoms.append({
                "id": atom["id"],
                "question": atom["question"],
                "selected_message_ids": locator.get("evidence_message_ids", []),
                "locator_passed": locator["locator_pass"],
                "answer": extractor.get("answer"),
                "meaning_passed": meaning_passed,
                "review": review,
            })
        complete += int(question_complete)
        negative = [locators[f"N{question_id}-{atom['id']}"] for atom in question["atoms"]]
        rows.append({
            "question_id": question_id,
            "question": question["text"],
            "atoms": atoms,
            "composed_answer": compositions[question_id]["composed_answer"],
            "complete": question_complete,
            "unrelated_chat": [
                {"atom_id": atom["id"], "receipt": row["receipt"]}
                for atom, row in zip(question["atoms"], negative)
            ],
        })

    mechanical = private["mechanical_summary"]
    return {
        "schema_version": "0.1",
        "experiment": "E007",
        "gate": "16D.6",
        "status": "completed_failed",
        "protocol": "/experiments/E007/atomic-reader-gate16d6-protocol-v0.1.json",
        "model": "Qwen3-8B Q4_K_M",
        "summary": {
            "valid_locator_receipts": mechanical["valid_locator_receipts"],
            "positive_atom_evidence_hits": mechanical["positive_atom_evidence_hits"],
            "negative_atom_empty": mechanical["negative_atom_empty"],
            "valid_extractor_receipts": mechanical["valid_extractor_receipts"],
            "atom_meanings_preserved": meanings,
            "atom_meanings_possible": 20,
            "complete_answers": complete,
            "baseline_atom_meanings": 15,
            "baseline_complete_answers": 5,
            "gate_passed": False,
        },
        "questions": rows,
        "decision": "Splitting each question into a locator call, an extractor call and a code-only join did not improve quality. It exposed separate locator and extractor failures, so the failed result is preserved.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(
        json.loads(args.private.read_text(encoding="utf-8")),
        json.loads(args.protocol.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
