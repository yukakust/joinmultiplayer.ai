from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LESSONS_OUT = ROOT / "site/experiments/E005/gate-5a-lessons-v0.1.json"
EXAM_OUT = ROOT / "site/experiments/E005/gate-5a-locked-test-v0.1.json"

CAUSES = [
    ("three blue pulses after startup", "три синих импульса после запуска", "phase_drift", "phase drift", "сдвиг фазы"),
    ("a steady amber glow after load transfer", "постоянное янтарное свечение после переноса нагрузки", "thermal_rebound", "thermal rebound", "тепловой отскок"),
    ("two violet rings before shutdown", "два фиолетовых кольца перед остановкой", "coolant_echo", "coolant echo", "эхо охлаждения"),
    ("alternating white and red flashes after restart", "чередующиеся белые и красные вспышки после перезапуска", "timing_split", "timing split", "рассинхронизация времени"),
]

SAFETY = [
    ("a double copper mark while room pressure rises", "двойная медная метка при растущем давлении в помещении", "keep_aux_vent_closed", "keep the auxiliary vent closed", "не открывать вспомогательный клапан"),
    ("a silver triangle while room pressure falls", "серебряный треугольник при падающем давлении в помещении", "isolate_power_first", "isolate power before adjustment", "отключить питание до настройки"),
    ("a black ring while room pressure is stable", "чёрное кольцо при стабильном давлении в помещении", "remote_only", "use remote controls only", "работать только удалённо"),
    ("an amber cross while pressure is unknown", "янтарный крест при неизвестном давлении", "stop_and_measure", "stop and measure pressure first", "остановиться и сначала измерить давление"),
]

TRAIN_NAMES = [f"Lumen-{index:03d}" for index in range(1, 97)]
EXAM_NAMES = [f"Nera-{index:02d}" for index in range(1, 25)]

EN_TEMPLATES = [
    "{name} shows {cause}. The room also shows {safety}. What happened and what is allowed?",
    "An operator reports {safety}. At the same time, {name} produced {cause}. Diagnose it and state the safe limit.",
    "Read this incident: {name} produced {cause}; nearby there is {safety}. Give the cause and the restriction.",
    "During inspection, the crew saw {cause} on {name} and {safety} in the room. What are the two conclusions?",
    "For {name}, combine these observations: {cause}. Separately, {safety}. State the fault and the safe boundary.",
    "The log for {name} contains {cause}. The site note contains {safety}. Explain the fault and the permitted response.",
]

RU_TEMPLATES = [
    "{name} показывает {cause}. В помещении также видна {safety}. Что произошло и что разрешено делать?",
    "Оператор сообщает: {safety}. Одновременно {name} выдал {cause}. Назовите причину и безопасное ограничение.",
    "Разберите случай: у {name} появились {cause}; рядом находится {safety}. Укажите причину и ограничение.",
    "При осмотре команда увидела у {name} {cause}, а в помещении — {safety}. Какие два вывода нужно сделать?",
    "Для {name} объедините наблюдения: {cause}. Отдельно: {safety}. Назовите неисправность и безопасную границу.",
    "В журнале {name} записаны {cause}. В заметке площадки указана {safety}. Объясните неисправность и допустимое действие.",
]


def canonical_hash(payload: dict) -> str:
    clean = {key: value for key, value in payload.items() if key != "content_sha256"}
    raw = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def observation(name: str, cause_index: int, safety_index: int, language: str, variant: int) -> str:
    cause = CAUSES[cause_index][0 if language == "en" else 1]
    safety = SAFETY[safety_index][0 if language == "en" else 1]
    template = (EN_TEMPLATES if language == "en" else RU_TEMPLATES)[variant % 6]
    return template.format(name=name, cause=cause, safety=safety)


def role_prompt(role: str, text: str, language: str, variant: int) -> str:
    if language == "en":
        instructions = [
            f"You are {role}. Return one small JSON capsule and nothing else.",
            f"Act as {role}. Read the incident and output only the requested JSON capsule.",
            f"Role: {role}. Ignore the other pocket's job. Answer with one JSON object only.",
        ]
    else:
        instructions = [
            f"Вы — {role}. Верните только одну маленькую JSON-капсулу.",
            f"Работайте как {role}. Прочитайте случай и выведите только нужную JSON-капсулу.",
            f"Роль: {role}. Не выполняйте работу второго pocket i. Ответьте одним JSON-объектом.",
        ]
    return f"{instructions[variant % 3]}\n\n{text}"


def build_lessons() -> dict:
    lessons = []
    for skill, role in (("cause", "CAUSE-I"), ("safety", "SAFETY-I")):
        for language in ("en", "ru"):
            for index in range(96):
                cause_index = index % 4
                safety_index = (index // 4 + index) % 4
                variant = index % 6
                name = TRAIN_NAMES[(index + (0 if language == "en" else 17)) % len(TRAIN_NAMES)]
                text = observation(name, cause_index, safety_index, language, variant)
                target = ({"cause": CAUSES[cause_index][2]} if skill == "cause" else {"restriction": SAFETY[safety_index][2]})
                lessons.append({
                    "id": f"G5A-{skill.upper()}-{language.upper()}-{index + 1:03d}",
                    "skill": skill,
                    "language": language,
                    "input": role_prompt(role, text, language, variant),
                    "target": json.dumps(target, separators=(",", ":")),
                    "cause_class": CAUSES[cause_index][2],
                    "restriction_class": SAFETY[safety_index][2],
                })
    payload = {
        "experiment_id": "E005",
        "gate": "5A",
        "kind": "training_curriculum",
        "status": "frozen_not_trained",
        "lessons": lessons,
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def build_exam() -> dict:
    questions = []
    for index in range(24):
        language = "en" if index < 12 else "ru"
        local = index % 12
        cause_index = local % 4
        safety_index = (local // 4 + local + 1) % 4
        variant = (local + 3) % 6
        name = EXAM_NAMES[index]
        text = observation(name, cause_index, safety_index, language, variant)
        cause_label, cause_en, cause_ru = CAUSES[cause_index][2:]
        restriction_label, restriction_en, restriction_ru = SAFETY[safety_index][2:]
        final = (
            f"The cause is {cause_en}; {restriction_en}."
            if language == "en"
            else f"Причина — {cause_ru}; нужно {restriction_ru}."
        )
        questions.append({
            "id": f"G5A-LOCK-{index + 1:02d}",
            "language": language,
            "question": text,
            "cause_prompt": role_prompt("CAUSE-I", text, language, variant + 1),
            "safety_prompt": role_prompt("SAFETY-I", text, language, variant + 2),
            "expected_cause_capsule": {"cause": cause_label},
            "expected_safety_capsule": {"restriction": restriction_label},
            "expected_complete_answer": final,
        })
    payload = {
        "experiment_id": "E005",
        "gate": "5A",
        "kind": "locked_composition_exam",
        "status": "locked_not_run",
        "questions": questions,
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def write() -> tuple[dict, dict]:
    lessons = build_lessons()
    exam = build_exam()
    LESSONS_OUT.write_text(json.dumps(lessons, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    EXAM_OUT.write_text(json.dumps(exam, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lessons, exam


if __name__ == "__main__":
    written = write()
    print(json.dumps({"lessons": len(written[0]["lessons"]), "questions": len(written[1]["questions"]), "lesson_hash": written[0]["content_sha256"], "exam_hash": written[1]["content_sha256"]}))
