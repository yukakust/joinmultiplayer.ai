from __future__ import annotations

import argparse
import json
from pathlib import Path


REVIEWS = {
    "G4-ARC-HEL-001-cbb21c9879": {
        "base": ("wrong", "Chooses the stale copied action and counts two copies as two independent positions."),
        "personal_dora": ("correct", "Chooses the newer manual and counts the copied lineage once."),
    },
    "G4-ARC-HEL-002-dee170a258": {
        "base": ("no_answer", "Repeats the Russian question without choosing an action or counting positions."),
        "personal_dora": ("correct", "Chooses the newer manual and counts the copied lineage once."),
    },
    "G4-ARC-HEL-003-25ee6fc51b": {
        "base": ("wrong", "Opens the vent and counts four dependent copies as four positions."),
        "personal_dora": ("correct", "Keeps the vent closed and counts the copied lineage once."),
    },
    "G4-ARC-HEL-004-70c6f25186": {
        "base": ("no_answer", "Repeats the Russian question without choosing an action or counting positions."),
        "personal_dora": ("correct", "Keeps the vent closed and counts the copied lineage once."),
    },
}


def review(payload: dict) -> dict:
    if {row["task_id"] for row in payload["rows"]} != set(REVIEWS):
        raise ValueError("microscope rows do not match the frozen review")
    false_positives = []
    for row in payload["rows"]:
        for condition in ("base", "personal_dora"):
            label, note = REVIEWS[row["task_id"]][condition]
            row[condition]["manual_review"] = label
            row[condition]["review_note"] = note
            if row[condition]["preliminary"]["preliminary_correct"] and label != "correct":
                false_positives.append(f"{row['task_id']}:{condition}")
    payload["claim_status"] = "development_microscope_manually_reviewed"
    payload["manual_summary"] = {
        "base_correct": sum(row["base"]["manual_review"] == "correct" for row in payload["rows"]),
        "personal_dora_correct": sum(row["personal_dora"]["manual_review"] == "correct" for row in payload["rows"]),
        "tasks": len(payload["rows"]),
    }
    payload["review_finding"] = {
        "automatic_scorer_false_positives": false_positives,
        "plain_language": {
            "en": "The first automatic checker mistook two repeated Russian questions for answers. Human review corrected both. This small development sample is not the final Gate 4 result.",
            "ru": "Первый автоматический проверяющий принял два повторённых русских вопроса за ответы. Ручная проверка исправила обе ошибки. Эта маленькая development-проба ещё не является итогом Gate 4.",
        },
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    args.path.write_text(json.dumps(review(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
