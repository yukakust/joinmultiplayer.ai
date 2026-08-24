from __future__ import annotations

import json
from pathlib import Path

from build_gate5a_data import CAUSES, SAFETY, canonical_hash, role_prompt


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "site/experiments/E005/gate-5a2-locked-test-v0.1.json"

EN_TEMPLATES = [
    "Help a new operator understand this without jargon. {name} recorded {cause}. Separately, the work zone carries {safety}. What is wrong, and what should the operator do?",
    "Turn these two reports into one useful instruction. Device {name}: {cause}. Workplace: {safety}. Explain the diagnosis and the safe next step.",
    "Someone must decide what to do with {name}. The device itself shows {cause}; the surrounding area shows {safety}. Give one clear human answer.",
    "Explain this incident to a person, not a machine: {name} has {cause}, while its room has {safety}. Include both the fault and the safety boundary.",
    "A technician asks for a plain answer about {name}. Evidence from the unit says {cause}. Evidence from the room says {safety}. What is the complete response?",
    "Combine, but do not confuse, two observations about {name}: {cause}; {safety}. Tell the operator the cause and the permitted action."
]

RU_TEMPLATES = [
    "Помогите новому оператору понять случай без жаргона. У {name} записаны {cause}. Отдельно рабочая зона имеет {safety}. Что сломалось и что делать?",
    "Превратите два сообщения в одну полезную инструкцию. Устройство {name}: {cause}. Рабочее место: {safety}. Объясните причину и безопасный следующий шаг.",
    "Нужно решить, что делать с {name}. Само устройство показывает {cause}, а окружающая зона — {safety}. Дайте один ясный человеческий ответ.",
    "Объясните случай человеку, а не машине: у {name} наблюдаются {cause}, а в помещении — {safety}. Укажите неисправность и безопасную границу.",
    "Техник просит простой ответ про {name}. Данные блока: {cause}. Данные помещения: {safety}. Каков полный ответ?",
    "Объедините, но не смешивайте два наблюдения о {name}: {cause}; {safety}. Назовите оператору причину и допустимое действие."
]


def build() -> dict:
    questions = []
    for index in range(24):
        language = "en" if index < 12 else "ru"
        local = index % 12
        cause_index = (local * 3 + 1) % 4
        safety_index = (local * 2 + local // 2) % 4
        template = (EN_TEMPLATES if language == "en" else RU_TEMPLATES)[local % 6]
        cause_text = CAUSES[cause_index][0 if language == "en" else 1]
        safety_text = SAFETY[safety_index][0 if language == "en" else 1]
        name = f"Sora-{index + 1:02d}"
        question = template.format(name=name, cause=cause_text, safety=safety_text)
        cause_label, cause_en, cause_ru = CAUSES[cause_index][2:]
        safety_label, safety_en, safety_ru = SAFETY[safety_index][2:]
        complete = (
            f"The cause is {cause_en}; {safety_en}."
            if language == "en"
            else f"Причина — {cause_ru}; нужно {safety_ru}."
        )
        questions.append({
            "id": f"G5A2-LOCK-{index + 1:02d}",
            "language": language,
            "question": question,
            "cause_prompt": role_prompt("CAUSE-I", question, language, local + 2),
            "safety_prompt": role_prompt("SAFETY-I", question, language, local + 4),
            "expected_cause_capsule": {"cause": cause_label},
            "expected_safety_capsule": {"restriction": safety_label},
            "expected_human_answer": complete,
            "template_family": "human_synthesis_exam_v0.1"
        })
    payload = {
        "experiment_id": "E005",
        "gate": "5A.2",
        "kind": "locked_human_synthesis_exam",
        "status": "locked_not_run",
        "questions": questions
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


if __name__ == "__main__":
    payload = build()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"questions": len(payload["questions"]), "content_sha256": payload["content_sha256"]}))
