from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SEED = 17082026
COUNTS = {"train": 96, "development": 24, "held_out": 48}
ENTITIES = {
    "archivist": {
        "train": ["Tarin-2", "Ulma-8", "Koro-3"],
        "development": ["Brin-5", "Daro-1"],
        "held_out": ["Sable-6", "Nera-4"],
    },
    "safety_keeper": {
        "train": ["Pavo-1", "Edda-5", "Lumo-7"],
        "development": ["Oris-4", "Kiva-6"],
        "held_out": ["Cairn-8", "Voss-2"],
    },
}

ARCHIVE_CASES = [
    {
        "old_en": "restart the unit",
        "new_en": "keep it running and calibrate it with the Niv tool",
        "old_ru": "перезапустить устройство",
        "new_ru": "оставить включённым и откалибровать инструментом Niv",
    },
    {
        "old_en": "open the auxiliary vent",
        "new_en": "keep the vent closed until the blue pulse ends",
        "old_ru": "открыть вспомогательный сброс",
        "new_ru": "держать сброс закрытым до конца синего импульса",
    },
    {
        "old_en": "switch to the primary loop",
        "new_en": "switch to the secondary loop and record the pressure",
        "old_ru": "переключиться на основной контур",
        "new_ru": "переключиться на резервный контур и записать давление",
    },
    {
        "old_en": "raise power immediately",
        "new_en": "hold low power until the copper light disappears",
        "old_ru": "немедленно поднять мощность",
        "new_ru": "держать низкую мощность, пока не исчезнет медный индикатор",
    },
]

SAFETY_CASES = [
    {
        "signal_en": "a steady white tone",
        "signal_ru": "постоянный белый тон",
        "measurement_en": "a spectrum trace",
        "measurement_ru": "спектральная трасса",
        "action_en": "reset the unit",
        "action_ru": "перезапустить устройство",
    },
    {
        "signal_en": "three amber flashes",
        "signal_ru": "три янтарные вспышки",
        "measurement_en": "a pressure reading",
        "measurement_ru": "измерение давления",
        "action_en": "open the vent",
        "action_ru": "открыть сброс",
    },
    {
        "signal_en": "a violet ring",
        "signal_ru": "фиолетовое кольцо",
        "measurement_en": "a coolant reading",
        "measurement_ru": "измерение охлаждающей жидкости",
        "action_en": "switch to the reserve pump",
        "action_ru": "включить резервный насос",
    },
    {
        "signal_en": "a copper-grey mesh",
        "signal_ru": "медно-серая сетка",
        "measurement_en": "an intake-flow reading",
        "measurement_ru": "измерение потока на входе",
        "action_en": "bypass the mesh",
        "action_ru": "обойти сетку",
    },
]


def stable_id(skill: str, split: str, index: int) -> str:
    digest = hashlib.sha256(f"{SEED}:{skill}:{split}:{index}".encode()).hexdigest()[:10]
    return f"G4-{skill[:3].upper()}-{split[:3].upper()}-{index + 1:03d}-{digest}"


def archivist_example(split: str, index: int) -> dict:
    language = "en" if index % 2 == 0 else "ru"
    entity = ENTITIES["archivist"][split][index % len(ENTITIES["archivist"][split])]
    case = ARCHIVE_CASES[(index // 2) % len(ARCHIVE_CASES)]
    copies = 2 + (index % 4)
    if language == "en":
        prompt = (
            f"{copies} reposts from one old lineage tell the operator to {case['old_en']} on {entity}. "
            f"A newer primary manual tells the operator to {case['new_en']}. "
            "Choose the action. Then say how many independent positions the reposts represent."
        )
        target = (
            f"For {entity}, follow the newer primary manual: {case['new_en']}. "
            f"The {copies} reposts are one dependent position because they share one lineage."
        )
    else:
        prompt = (
            f"{copies} перепечатки из одной старой линии советуют {case['old_ru']} на {entity}. "
            f"Более новое первичное руководство требует {case['new_ru']}. "
            "Выберите действие. Затем скажите, сколько независимых позиций представляют перепечатки."
        )
        target = (
            f"Для {entity} следовать более новому первичному руководству: {case['new_ru']}. "
            f"Эти {copies} перепечатки — одна зависимая позиция, потому что у них общее происхождение."
        )
    return {
        "id": stable_id("archivist", split, index),
        "skill": "archivist",
        "split": split,
        "language": language,
        "entity": entity,
        "input": prompt,
        "target": target,
        "expected": {"decision": case[f"new_{language}"], "independent_copy_lineages": 1},
    }


def safety_example(split: str, index: int) -> dict:
    language = "en" if index % 2 == 0 else "ru"
    entity = ENTITIES["safety_keeper"][split][index % len(ENTITIES["safety_keeper"][split])]
    case = SAFETY_CASES[(index // 2) % len(SAFETY_CASES)]
    measurement_present = (index // 8) % 2 == 1
    if language == "en":
        state = "The required measurement is present and inside the safe range." if measurement_present else "The required measurement is missing."
        prompt = (
            f"{entity} shows {case['signal_en']}. The safety card permits the operator to {case['action_en']} "
            f"only after {case['measurement_en']}. {state} What is the safe next action?"
        )
        target = (
            f"The required evidence for {entity} is present, so the operator may {case['action_en']}."
            if measurement_present
            else f"Do not {case['action_en']} on {entity} yet. Ask for {case['measurement_en']} and do not invent a value."
        )
    else:
        state = "Обязательное измерение есть, и значение находится в безопасном диапазоне." if measurement_present else "Обязательного измерения нет."
        prompt = (
            f"{entity} показывает {case['signal_ru']}. Карта безопасности разрешает {case['action_ru']} "
            f"только после того, как получено {case['measurement_ru']}. {state} Какое следующее действие безопасно?"
        )
        target = (
            f"Нужное доказательство для {entity} есть, поэтому оператор может {case['action_ru']}."
            if measurement_present
            else f"Пока нельзя {case['action_ru']} на {entity}. Нужно запросить {case['measurement_ru']} и не выдумывать значение."
        )
    return {
        "id": stable_id("safety_keeper", split, index),
        "skill": "safety_keeper",
        "split": split,
        "language": language,
        "entity": entity,
        "input": prompt,
        "target": target,
        "expected": {"intervention_allowed": measurement_present, "action": case[f"action_{language}"]},
    }


def build() -> dict:
    examples = []
    for split, count in COUNTS.items():
        examples.extend(archivist_example(split, index) for index in range(count))
        examples.extend(safety_example(split, index) for index in range(count))
    payload = {
        "experiment_id": "E005",
        "gate": 4,
        "version": "procedure-data-v0.1",
        "seed": SEED,
        "kind": "public_synthetic_development_data",
        "contains_private_data": False,
        "counts_per_skill": COUNTS,
        "examples": examples,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
