from __future__ import annotations

import argparse
import json
from pathlib import Path


METHOD_LABELS = {
    "base": {"en": "Clean Qwen", "ru": "Чистая Qwen"},
    "personal_dora": {"en": "Qwen + the right personal DoRA", "ru": "Qwen + нужная личная DoRA"},
    "wrong_specialist": {"en": "Qwen + another pocket i's DoRA", "ru": "Qwen + DoRA другого pocket i"},
    "shuffled_lessons": {"en": "Qwen + DoRA trained on shuffled lessons", "ru": "Qwen + DoRA с перепутанными уроками"},
}


def public_skill(source: dict) -> dict:
    return {
        "skill": source["skill"],
        "source_held_out_rows": source["source_held_out_rows"],
        "unique_questions": source["unique_input_count"],
        "duplicate_rows_excluded": source["duplicate_rows_not_independent_evidence"],
        "summary": source["summary"],
        "rows": source["rows"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archivist", required=True, type=Path)
    parser.add_argument("--safety", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    archivist = json.loads(args.archivist.read_text(encoding="utf-8"))
    safety = json.loads(args.safety.read_text(encoding="utf-8"))
    skills = [public_skill(archivist), public_skill(safety)]
    payload = {
        "experiment_id": "E005",
        "gate": 4,
        "kind": "development_skill_transfer_results",
        "claim_status": "automatic_exact_match_owner_review_pending",
        "question": {
            "en": "Can personal DoRA weights learn a small reusable skill instead of retrieving a stored answer?",
            "ru": "Могут ли личные веса DoRA выучить маленькое умение, а не найти сохранённый ответ?",
        },
        "answer": {
            "en": "In this small synthetic test, yes: each matching personal DoRA produced the exact expected answer on every unique held-out question. None of the three controls did.",
            "ru": "В этом маленьком синтетическом тесте — да: каждая нужная личная DoRA дала точный ожидаемый ответ на все разные скрытые вопросы. Ни один из трёх контрольных вариантов этого не сделал.",
        },
        "methods": METHOD_LABELS,
        "totals": {
            "unique_questions": sum(skill["unique_questions"] for skill in skills),
            "personal_dora_exact": sum(skill["summary"]["personal_dora"]["exact_target_matches"] for skill in skills),
            "base_exact": sum(skill["summary"]["base"]["exact_target_matches"] for skill in skills),
            "wrong_specialist_exact": sum(skill["summary"]["wrong_specialist"]["exact_target_matches"] for skill in skills),
            "shuffled_lessons_exact": sum(skill["summary"]["shuffled_lessons"]["exact_target_matches"] for skill in skills),
            "duplicate_rows_excluded": sum(skill["duplicate_rows_excluded"] for skill in skills),
        },
        "limits": [
            {
                "en": "This is a development result on a small, templated, synthetic world. It is not proof of a general skill, real-world safety, routing, or a swarm.",
                "ru": "Это development-результат в маленьком шаблонном синтетическом мире. Он не доказывает общий навык, безопасность в реальном мире, routing или swarm.",
            },
            {
                "en": "The dataset contained repeated question rows. They remain in the source data, but only 8 Archivist and 16 Safety Keeper questions are counted as independent evidence.",
                "ru": "В наборе были повторяющиеся строки. Они остались в исходных данных, но как отдельные доказательства считаются только 8 вопросов Архивиста и 16 вопросов Хранителя.",
            },
            {
                "en": "The exact-match score is automatic. The owner has not yet confirmed every answer on this page.",
                "ru": "Точное совпадение проверила программа. Владелец ещё не подтвердил каждый ответ на этой странице.",
            },
            {
                "en": "A first serial evaluator was stopped after one saved task because it was too slow. Its four answers exactly matched the batched evaluator.",
                "ru": "Первую медленную проверку остановили после одного сохранённого вопроса. Все четыре ответа буква в букву совпали с ускоренной проверкой.",
            },
        ],
        "skills": skills,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
