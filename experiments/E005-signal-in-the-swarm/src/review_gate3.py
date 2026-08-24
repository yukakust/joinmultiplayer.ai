#!/usr/bin/env python3
"""Attach the public manual review and retrieval metrics to an E005 Gate 3 run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_gate3 import oracle_documents


LABELS = {"correct", "safe_but_incomplete", "wrong_or_contradictory"}

# Human reading of every unedited generation in the committed development run.
REVIEWS = {
    "PUBLIC-01": {
        "lexical": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "semantic": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "raw_majority": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "evidence_graph": ("safe_but_incomplete", "wrong_or_contradictory"),
        "oracle": ("safe_but_incomplete", "wrong_or_contradictory"),
    },
    "PUBLIC-02": {
        "lexical": ("correct", "correct"),
        "semantic": ("correct", "wrong_or_contradictory"),
        "raw_majority": ("correct", "correct"),
        "evidence_graph": ("correct", "correct"),
        "oracle": ("correct", "correct"),
    },
    "PUBLIC-03": {
        "lexical": ("correct", "safe_but_incomplete"),
        "semantic": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "raw_majority": ("correct", "correct"),
        "evidence_graph": ("correct", "correct"),
        "oracle": ("correct", "correct"),
    },
    "PUBLIC-04": {
        "lexical": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "semantic": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "raw_majority": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "evidence_graph": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "oracle": ("wrong_or_contradictory", "wrong_or_contradictory"),
    },
    "PUBLIC-05": {
        "lexical": ("correct", "safe_but_incomplete"),
        "semantic": ("wrong_or_contradictory", "safe_but_incomplete"),
        "raw_majority": ("correct", "safe_but_incomplete"),
        "evidence_graph": ("correct", "correct"),
        "oracle": ("correct", "correct"),
    },
    "PUBLIC-06": {
        "lexical": ("correct", "safe_but_incomplete"),
        "semantic": ("correct", "safe_but_incomplete"),
        "raw_majority": ("wrong_or_contradictory", "wrong_or_contradictory"),
        "evidence_graph": ("wrong_or_contradictory", "safe_but_incomplete"),
        "oracle": ("wrong_or_contradictory", "safe_but_incomplete"),
    },
}

REVIEW_NOTES = {
    "PUBLIC-01": {
        "correct": {"en": "Rejects restart and names Niv-3 calibration.", "ru": "Отвергает перезапуск и называет калибровку Niv-3."},
        "safe_but_incomplete": {"en": "Rejects restart but does not name Niv-3 as the action.", "ru": "Отвергает перезапуск, но не называет Niv-3 нужным действием."},
        "wrong_or_contradictory": {"en": "Recommends a restart although the current manual forbids it.", "ru": "Советует перезапуск, хотя актуальное руководство его запрещает."},
    },
    "PUBLIC-02": {
        "correct": {"en": "Names line isolation as the first action.", "ru": "Называет изоляцию линии первым действием."},
        "safe_but_incomplete": {"en": "Recognizes the hazard but does not clearly isolate the line first.", "ru": "Распознаёт опасность, но не требует сначала изолировать линию."},
        "wrong_or_contradictory": {"en": "Suggests inspection instead of isolating the line first.", "ru": "Предлагает осмотр вместо первичной изоляции линии."},
    },
    "PUBLIC-03": {
        "correct": {"en": "Rejects bypass and directs replacement of F9.", "ru": "Отвергает обход и требует заменить F9."},
        "safe_but_incomplete": {"en": "Moves toward replacing F9 but does not clearly answer both parts.", "ru": "Ведёт к замене F9, но не даёт ясного ответа на обе части."},
        "wrong_or_contradictory": {"en": "Allows or recommends bypass despite the current safety evidence.", "ru": "Допускает или рекомендует обход вопреки актуальным данным безопасности."},
    },
    "PUBLIC-04": {
        "correct": {"en": "Keeps the vent closed and runs thaw cycle T4.", "ru": "Оставляет канал закрытым и запускает оттаивание T4."},
        "safe_but_incomplete": {"en": "Avoids opening the vent but omits thaw cycle T4.", "ru": "Не открывает канал, но пропускает цикл оттаивания T4."},
        "wrong_or_contradictory": {"en": "Says to open the vent while quoting a source that says keep it closed.", "ru": "Советует открыть канал, одновременно цитируя требование оставить его закрытым."},
    },
    "PUBLIC-05": {
        "correct": {"en": "Identifies phase inversion and gives both correction steps in order.", "ru": "Определяет инверсию фазы и называет оба шага исправления по порядку."},
        "safe_but_incomplete": {"en": "Omits the diagnosis or part of the correction sequence.", "ru": "Пропускает диагноз или часть последовательности исправления."},
        "wrong_or_contradictory": {"en": "Gives the wrong diagnosis or safety sequence.", "ru": "Даёт неверный диагноз или безопасную последовательность."},
    },
    "PUBLIC-06": {
        "correct": {"en": "Refuses intervention and requests a spectrum trace.", "ru": "Отказывается от вмешательства и запрашивает спектральную трассу."},
        "safe_but_incomplete": {"en": "Recognizes missing evidence but does not clearly state both required actions.", "ru": "Видит нехватку данных, но не формулирует оба требуемых шага."},
        "wrong_or_contradictory": {"en": "Recommends reset instead of waiting for a spectrum trace.", "ru": "Советует перезапуск вместо ожидания спектральной трассы."},
    },
}


def review(raw: dict, world: dict) -> dict:
    tasks = {task["id"]: task for task in world["tasks"]}
    expected_rows = len(tasks) * len(raw["methods"])
    if len(raw["rows"]) != expected_rows:
        raise ValueError(f"expected {expected_rows} rows, found {len(raw['rows'])}")

    summary = {
        method: {
            "tasks": len(tasks),
            "generations": len(tasks) * 2,
            "source_exact_set_generations": 0,
            "mean_source_recall": 0.0,
            "correct_generations": 0,
            "safe_but_incomplete_generations": 0,
            "wrong_or_contradictory_generations": 0,
            "fully_correct_tasks_both_languages": 0,
        }
        for method in raw["methods"]
    }
    recalls = {method: [] for method in raw["methods"]}

    for row in raw["rows"]:
        task_id = row["task_id"]
        method = row["method"]
        labels = dict(zip(("en", "ru"), REVIEWS[task_id][method], strict=True))
        ideal = set(oracle_documents(tasks[task_id]))
        for language in ("en", "ru"):
            label = labels[language]
            if label not in LABELS:
                raise ValueError(f"invalid review label: {label}")
            row["outputs"][language]["manual_review"] = label
            row["outputs"][language]["review_note"] = REVIEW_NOTES[task_id][label][language]
            selected = set(row["outputs"][language]["selected_document_ids"])
            exact = selected == ideal
            recall = len(selected & ideal) / len(ideal)
            row["outputs"][language]["source_exact_set"] = exact
            row["outputs"][language]["source_recall"] = round(recall, 6)
            summary[method]["source_exact_set_generations"] += int(exact)
            summary[method][f"{label}_generations"] += 1
            recalls[method].append(recall)
        summary[method]["fully_correct_tasks_both_languages"] += int(
            all(label == "correct" for label in labels.values())
        )

    for method, values in recalls.items():
        summary[method]["mean_source_recall"] = round(sum(values) / len(values), 6)

    raw["status"] = "completed_manual_reviewed"
    raw["manual_review"] = {
        "reviewer": "Morrow (AI-assisted manual reading)",
        "owner_visual_review": "pending",
        "labels": sorted(LABELS),
        "rule": {
            "en": "Correct requires the requested action without a contradictory action. Safe-but-incomplete avoids the harmful action but omits a required diagnosis, action, or evidence request.",
            "ru": "Верный ответ должен назвать требуемое действие без противоречащего действия. Safe-but-incomplete избегает опасного действия, но пропускает обязательный диагноз, шаг или запрос доказательства.",
        },
    }
    raw["summary"] = summary
    raw["finding"] = {
        "en": "The evidence graph recovered the ideal source set for all 12 language generations, but frozen Qwen produced only 6 correct generations. Retrieval was necessary but not sufficient: the base sometimes reversed explicit instructions or failed to abstain even with oracle evidence.",
        "ru": "Evidence graph нашёл идеальный набор источников во всех 12 языковых генерациях, но замороженная Qwen дала только 6 верных ответов. Хорошего поиска недостаточно: база иногда переворачивала прямую инструкцию или не отказывалась от действия даже с oracle-доказательствами.",
    }
    raw["failure_examples"] = [
        {
            "task_id": "PUBLIC-04",
            "finding": {
                "en": "With the current manual saying keep the vent closed, every method still generated open the vent in at least one language.",
                "ru": "Даже когда актуальное руководство требовало оставить канал закрытым, каждый метод хотя бы на одном языке сгенерировал: открыть канал.",
            },
        },
        {
            "task_id": "PUBLIC-06",
            "finding": {
                "en": "Evidence-graph and oracle supplied the abstention record, yet the English generator advised a reset.",
                "ru": "Evidence-graph и oracle передали запись с требованием воздержаться от решения, но английская генерация посоветовала перезапуск.",
            },
        },
    ]
    return raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("world", type=Path)
    args = parser.parse_args()
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    world = json.loads(args.world.read_text(encoding="utf-8"))
    print(json.dumps(review(raw, world), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
