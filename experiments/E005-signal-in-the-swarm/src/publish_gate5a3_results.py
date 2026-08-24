from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "experiments/E005-signal-in-the-swarm/artifacts/gate5a3-raw-v0.1.json"
PUBLIC = ROOT / "site/experiments/E005/gate-5a3-results-v0.1.json"

HUMAN_COMPLETE = {
    "base_semantic_actual_pair": {
        "G5A2-LOCK-01", "G5A2-LOCK-02", "G5A2-LOCK-05", "G5A2-LOCK-06",
        "G5A2-LOCK-07", "G5A2-LOCK-08", "G5A2-LOCK-09", "G5A2-LOCK-11",
        "G5A2-LOCK-12", "G5A2-LOCK-13", "G5A2-LOCK-14",
    },
    "instruct_semantic_actual_pair": {
        "G5A2-LOCK-01", "G5A2-LOCK-02", "G5A2-LOCK-03", "G5A2-LOCK-05",
        "G5A2-LOCK-06", "G5A2-LOCK-07", "G5A2-LOCK-08", "G5A2-LOCK-09",
        "G5A2-LOCK-10", "G5A2-LOCK-11", "G5A2-LOCK-12", "G5A2-LOCK-13",
        "G5A2-LOCK-15", "G5A2-LOCK-18", "G5A2-LOCK-19", "G5A2-LOCK-20",
        "G5A2-LOCK-24",
    },
    "instruct_semantic_oracle_pair": {
        "G5A2-LOCK-01", "G5A2-LOCK-02", "G5A2-LOCK-03", "G5A2-LOCK-05",
        "G5A2-LOCK-06", "G5A2-LOCK-07", "G5A2-LOCK-08", "G5A2-LOCK-09",
        "G5A2-LOCK-10", "G5A2-LOCK-11", "G5A2-LOCK-12", "G5A2-LOCK-13",
        "G5A2-LOCK-15", "G5A2-LOCK-18", "G5A2-LOCK-19", "G5A2-LOCK-20",
        "G5A2-LOCK-24",
    },
}


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    rows = []
    for row in raw["rows"]:
        conditions = {}
        for condition, result in row["conditions"].items():
            copied = dict(result)
            if condition in HUMAN_COMPLETE:
                copied["human_complete"] = row["id"] in HUMAN_COMPLETE[condition]
                copied["human_review"] = "kept_both_facts" if copied["human_complete"] else "lost_changed_or_contradicted_a_fact"
            conditions[condition] = copied
        rows.append({**row, "conditions": conditions})
    public = {
        "experiment_id": "E005",
        "gate": "5A.3",
        "status": "failed_but_improved",
        "title": {
            "en": "Clear capsules helped. They were not enough.",
            "ru": "Понятные капсулы помогли. Но этого мало.",
        },
        "plain_result": {
            "en": "Instruction Qwen kept both pocket facts in 17 of 24 answers. The pass rule was 20. Base Qwen reached 11. The previous coded interface reached 4.",
            "ru": "Instruction-Qwen сохранила оба факта в 17 ответах из 24. Для победы нужно было 20. Base Qwen получила 11. Прежний интерфейс с кодами — 4.",
        },
        "human_summary": {
            "previous_coded_base": 4,
            "base_semantic_actual_pair": 11,
            "instruct_semantic_actual_pair": 17,
            "instruct_semantic_oracle_pair": 17,
            "required": 20,
        },
        "language_summary": {
            "instruct_semantic_actual_pair": {
                "en": {"complete": 11, "total": 12},
                "ru": {"complete": 6, "total": 12},
            }
        },
        "machine_summary": raw["summary"],
        "diagnosis": {
            "en": "The code labels and 64-token limit were real problems. After removing them, the remaining bottleneck is reliable instruction following and multilingual synthesis in the small final model.",
            "ru": "Кодовые ярлыки и лимит в 64 токена действительно мешали. После их удаления осталось другое слабое место: маленькая финальная модель ненадёжно выполняет инструкции и склеивает знания на разных языках.",
        },
        "claim_boundary": {
            "en": "The semantic statements came from a deterministic public codebook. This run did not teach pockets to produce evidence-rich statements and did not test latent parallel neural tracks.",
            "ru": "Понятные утверждения создала открытая неизменяемая таблица. Мы ещё не учили сами pocket i выдавать утверждения с доказательствами и не проверяли параллельные нейронные треки.",
        },
        "next_step": {
            "en": "Do not proceed to Gate 5B yet. First test a stronger or specially trained final merger on this unchanged exam and semantic contract.",
            "ru": "Gate 5B пока не начинаем. Сначала проверим более сильный или специально обученный финальный сборщик на том же экзамене и том же контракте.",
        },
        "conditions": list(raw["summary"]),
        "generation": raw["generation"],
        "models": raw["models"],
        "hashes": {
            "design_content_sha256": raw["design_content_sha256"],
            "exam_content_sha256": raw["exam_content_sha256"],
        },
        "rows": rows,
    }
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
