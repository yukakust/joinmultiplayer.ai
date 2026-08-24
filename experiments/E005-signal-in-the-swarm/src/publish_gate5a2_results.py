from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "experiments/E005-signal-in-the-swarm/artifacts/gate5a2-raw-v0.1.json"
PUBLIC = ROOT / "site/experiments/E005/gate-5a2-results-v0.1.json"

# Frozen source Qwen often paraphrased a correct restriction. A human reviewed
# every unedited answer. These are the only rows that preserve both required
# facts precisely enough to act on.
HUMAN_COMPLETE = {
    "actual_pair": {"G5A2-LOCK-01", "G5A2-LOCK-06", "G5A2-LOCK-08", "G5A2-LOCK-09"},
    "oracle_pair": {"G5A2-LOCK-01", "G5A2-LOCK-06", "G5A2-LOCK-08", "G5A2-LOCK-09"},
}


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    rows = []
    for row in raw["rows"]:
        conditions = {}
        for name, result in row["conditions"].items():
            copied = dict(result)
            if name in HUMAN_COMPLETE:
                copied["human_complete"] = row["id"] in HUMAN_COMPLETE[name]
                copied["human_review"] = (
                    "kept_both_facts" if copied["human_complete"] else "lost_or_changed_a_fact"
                )
            conditions[name] = copied
        rows.append({**row, "conditions": conditions})

    public = {
        "experiment_id": "E005",
        "gate": "5A.2",
        "status": "failed",
        "title": {
            "en": "The pockets knew. The final i lost their knowledge.",
            "ru": "Pocket i знали. Финальный i потерял их знания.",
        },
        "plain_result": {
            "en": (
                "CAUSE-I and SAFETY-I produced their capsules, but frozen Qwen turned both facts "
                "into a complete natural answer only 4 times out of 24. The pass rule was 20."
            ),
            "ru": (
                "CAUSE-I и SAFETY-I выдали свои капсулы, но замороженная Qwen сохранила оба факта "
                "в понятном ответе только 4 раза из 24. Для победы нужно было 20."
            ),
        },
        "language_result": {
            "en": {"human_complete": 4, "total": 12},
            "ru": {"human_complete": 0, "total": 12},
        },
        "automatic_complete": raw["summary"]["actual_pair"]["complete"],
        "human_complete": len(HUMAN_COMPLETE["actual_pair"]),
        "required_complete": 20,
        "why_two_numbers": {
            "en": (
                "The automatic checker required frozen phrases and counted 1. A human also accepted "
                "three faithful paraphrases, producing 4. Neither result is close to passing."
            ),
            "ru": (
                "Автопроверка искала заранее записанные фразы и засчитала 1 ответ. Человек принял "
                "ещё три верных пересказа — получилось 4. До победы далеко в обоих случаях."
            ),
        },
        "diagnosis": {
            "en": (
                "This run does not refute the two-pocket result. It finds a new broken part: a small "
                "frozen Qwen is not a reliable translator from explicit capsules to a human answer."
            ),
            "ru": (
                "Этот запуск не отменяет результат двух pocket i. Он нашёл новое слабое место: "
                "маленькая замороженная Qwen ненадёжно переводит явные капсулы в человеческий ответ."
            ),
        },
        "next_step": {
            "en": (
                "Before Gate 5B, compare stronger or specifically taught source mergers on this same "
                "locked exam. Do not change the questions or pocket capsules."
            ),
            "ru": (
                "До Gate 5B нужно на этом же замороженном экзамене сравнить более сильный или специально "
                "обученный финальный сборщик. Вопросы и капсулы pocket i менять нельзя."
            ),
        },
        "claim_boundary": {
            "en": (
                "This tests one-pass language synthesis from explicit text capsules. It still does not "
                "test latent-state merging, routing, separate devices, or swarm growth."
            ),
            "ru": (
                "Здесь проверяется одноразовая сборка ответа из явных текстовых капсул. Здесь всё ещё нет "
                "объединения скрытых состояний, routing, разных устройств и роста swarm."
            ),
        },
        "conditions": raw["conditions"],
        "generation": raw["generation"],
        "hashes": {
            "exam_content_sha256": raw["exam_content_sha256"],
            "exam_file_sha256": raw["exam_file_sha256"],
            "base_file_sha256": raw["base_file_sha256"],
            "adapter_file_sha256": raw["adapter_file_sha256"],
        },
        "rows": rows,
    }
    PUBLIC.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
