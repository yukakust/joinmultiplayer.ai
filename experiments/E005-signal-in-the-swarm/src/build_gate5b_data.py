from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "site/experiments/E005"

CAUSES = {
    "thermal_rebound": {
        "en": ("a steady amber glow after load transfer", "The cause is thermal rebound."),
        "ru": ("постоянное янтарное свечение после переноса нагрузки", "Причина — тепловой отскок."),
    },
    "phase_drift": {
        "en": ("three blue pulses after startup", "The cause is phase drift."),
        "ru": ("три синих импульса после запуска", "Причина — сдвиг фазы."),
    },
    "timing_split": {
        "en": ("alternating white and red flashes after restart", "The cause is timing split."),
        "ru": ("чередующиеся белые и красные вспышки после перезапуска", "Причина — рассинхронизация времени."),
    },
    "coolant_echo": {
        "en": ("two violet rings before shutdown", "The cause is coolant echo."),
        "ru": ("два фиолетовых кольца перед остановкой", "Причина — эхо охлаждения."),
    },
}

SAFETY = {
    "keep_aux_vent_closed": {
        "en": ("a double copper mark while room pressure rises", "Keep the auxiliary vent closed."),
        "ru": ("двойная медная метка при растущем давлении", "Не открывайте вспомогательный клапан."),
    },
    "remote_only": {
        "en": ("a black ring while room pressure is stable", "Use remote controls only."),
        "ru": ("чёрное кольцо при стабильном давлении", "Работайте только удалённо."),
    },
    "isolate_power_first": {
        "en": ("a silver triangle while room pressure falls", "Isolate power before adjustment."),
        "ru": ("серебряный треугольник при падающем давлении", "Отключите питание до настройки."),
    },
    "stop_and_measure": {
        "en": ("an amber cross while pressure is unknown", "Stop and measure pressure first."),
        "ru": ("янтарный крест при неизвестном давлении", "Остановитесь и сначала измерьте давление."),
    },
}

TRACK_TEMPLATES = {
    "en": [
        "{device} reports {signal}. Give only the diagnosis.",
        "A technician saw {signal} on {device}. What is the cause?",
        "Name the fault behind this {device} signal: {signal}.",
        "For {device}, interpret {signal} as one short diagnosis.",
    ],
    "ru": [
        "Устройство {device} показывает {signal}. Назовите только причину.",
        "Техник увидел у {device} {signal}. В чём причина?",
        "Назовите неисправность по сигналу {device}: {signal}.",
        "Кратко определите причину для {device}: {signal}.",
    ],
}

SAFETY_TEMPLATES = {
    "en": [
        "The zone around {device} shows {signal}. Give only the safe action.",
        "A worker sees {signal} near {device}. What must they do?",
        "Name the safe next step for {device} when there is {signal}.",
        "For {device}, turn {signal} into one short safety instruction.",
    ],
    "ru": [
        "В зоне рядом с {device} видна {signal}. Назовите только безопасное действие.",
        "Работник видит рядом с {device} {signal}. Что нужно сделать?",
        "Назовите безопасный следующий шаг для {device}, если видна {signal}.",
        "Для {device} превратите сигнал «{signal}» в короткую инструкцию.",
    ],
}

MERGE_TEMPLATES = {
    "en": [
        "{device} shows {cause_signal}. Its work zone separately shows {safety_signal}. Give the cause and safe action.",
        "Help the operator with {device}: device report — {cause_signal}; zone report — {safety_signal}. What happened and what now?",
        "Combine two independent observations about {device}: {cause_signal}; {safety_signal}. Answer plainly.",
    ],
    "ru": [
        "Устройство {device} показывает {cause_signal}. Отдельно в рабочей зоне видна {safety_signal}. Назовите причину и безопасное действие.",
        "Помогите оператору {device}: сигнал устройства — {cause_signal}; сигнал зоны — {safety_signal}. Что случилось и что делать?",
        "Объедините два независимых наблюдения о {device}: {cause_signal}; {safety_signal}. Ответьте просто.",
    ],
}

EXAM_TEMPLATES = {
    "en": [
        "A new operator has two reports for {device}. First: {cause_signal}. Second: {safety_signal}. Explain the fault and the permitted next step without jargon.",
        "Someone must act on {device}. The unit itself produced {cause_signal}; the room independently produced {safety_signal}. Give one complete answer.",
    ],
    "ru": [
        "У нового оператора есть два отчёта о {device}. Первый: {cause_signal}. Второй: {safety_signal}. Без жаргона объясните причину и допустимый следующий шаг.",
        "Нужно принять решение по {device}. Само устройство показало {cause_signal}; отдельно помещение показало {safety_signal}. Дайте один полный ответ.",
    ],
}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_track_lessons() -> list[dict]:
    rows = []
    for language in ("en", "ru"):
        for role, knowledge, templates in (
            ("cause", CAUSES, TRACK_TEMPLATES[language]),
            ("safety", SAFETY, SAFETY_TEMPLATES[language]),
        ):
            for label_index, (label, localized) in enumerate(knowledge.items()):
                signal, answer = localized[language]
                for repeat in range(16):
                    device = f"{('Neri' if role == 'cause' else 'Tavi')}-{language.upper()}-{label_index + 1}-{repeat + 1:02d}"
                    prompt = templates[repeat % len(templates)].format(device=device, signal=signal)
                    rows.append({
                        "id": f"G5B-{role.upper()}-{language.upper()}-{label_index + 1}-{repeat + 1:02d}",
                        "split": "track_train", "role": role, "language": language,
                        "device": device, "label": label, "prompt": prompt, "target": answer,
                    })
    return rows


def build_merger_lessons() -> list[dict]:
    rows = []
    combinations = list(itertools.product(CAUSES.items(), SAFETY.items()))
    for language in ("en", "ru"):
        for cycle in range(6):
            for combo_index, ((cause_label, cause_local), (safety_label, safety_local)) in enumerate(combinations):
                device = f"Mero-{language.upper()}-{cycle + 1}-{combo_index + 1:02d}"
                prompt = MERGE_TEMPLATES[language][cycle % len(MERGE_TEMPLATES[language])].format(
                    device=device, cause_signal=cause_local[language][0], safety_signal=safety_local[language][0]
                )
                target = f"{cause_local[language][1]} {safety_local[language][1]}"
                rows.append({
                    "id": f"G5B-MERGE-{language.upper()}-{cycle + 1}-{combo_index + 1:02d}",
                    "split": "merger_train", "language": language, "device": device,
                    "cause_label": cause_label, "safety_label": safety_label,
                    "prompt": prompt, "target": target,
                })
    return rows


def build_exam() -> list[dict]:
    rows = []
    combinations = list(itertools.product(CAUSES.items(), SAFETY.items()))
    for language in ("en", "ru"):
        for combo_index, ((cause_label, cause_local), (safety_label, safety_local)) in enumerate(combinations):
            device = f"Lyra-{language.upper()}-{combo_index + 1:02d}"
            prompt = EXAM_TEMPLATES[language][combo_index % len(EXAM_TEMPLATES[language])].format(
                device=device, cause_signal=cause_local[language][0], safety_signal=safety_local[language][0]
            )
            rows.append({
                "id": f"G5B-LOCK-{language.upper()}-{combo_index + 1:02d}",
                "split": "locked_test", "language": language, "device": device,
                "cause_label": cause_label, "safety_label": safety_label,
                "question": prompt,
                "expected_cause": cause_local[language][1],
                "expected_safety": safety_local[language][1],
                "expected_answer": f"{cause_local[language][1]} {safety_local[language][1]}",
            })
    return rows


def build() -> tuple[dict, dict, dict]:
    tracks = build_track_lessons()
    merger = build_merger_lessons()
    exam_rows = build_exam()
    curriculum = {
        "experiment_id": "E005", "gate": "5B", "kind": "neural_track_curriculum",
        "status": "frozen_before_training", "track_lessons": tracks, "merger_lessons": merger,
    }
    curriculum["content_sha256"] = digest({"track_lessons": tracks, "merger_lessons": merger})
    exam = {
        "experiment_id": "E005", "gate": "5B", "kind": "locked_neural_track_exam",
        "status": "locked_not_run", "questions": exam_rows,
    }
    exam["content_sha256"] = digest(exam_rows)
    design = {
        "experiment_id": "E005", "gate": "5B", "kind": "locked_parallel_neural_track_design",
        "status": "locked_not_run",
        "hypothesis": {
            "en": "Can two separately trained neural tracks combine hidden contributions and solve a task neither track solves alone?",
            "ru": "Смогут ли два отдельно обученных нейронных трека объединить скрытые добавки и решить задачу, которую ни один трек не решает в одиночку?",
        },
        "architecture": {
            "shared_model": "Qwen/Qwen3-0.6B",
            "total_layers": 28,
            "shared_stem_layers": [0, 5],
            "personal_track_layers": [6, 21],
            "shared_tail_layers": [22, 27],
            "personal_update": "rank-8 DoRA only inside each personal track",
            "equation": "z = z0 + Merge(clip(track_cause(h)-z0), clip(track_safety(h)-z0)); answer = shared_tail(z)",
            "first_run_location": "one yukabox process; physical distribution is a later replication",
        },
        "training_order": [
            "freeze shared stem, untouched base-middle path, shared tail, and LM head",
            "train CAUSE-I DoRA only on cause lessons",
            "train SAFETY-I DoRA only on safety lessons",
            "freeze both tracks",
            "train only the bounded merger on merger lessons",
            "run the locked exam once",
        ],
        "conditions": [
            "shared_qwen_alone", "cause_track_alone", "safety_track_alone",
            "wrong_same_role_pair", "semantic_text_capsules", "correct_neural_pair",
        ],
        "pass_rule": {
            "correct_neural_pair_at_least": 26,
            "shared_qwen_alone_at_most": 10,
            "each_single_track_at_most": 10,
            "wrong_pair_at_most": 10,
            "correct_pair_lead_over_best_single_at_least": 12,
            "correct_pair_may_trail_text_capsules_by_at_most": 2,
            "total_questions": 32,
        },
        "curriculum_content_sha256": curriculum["content_sha256"],
        "exam_content_sha256": exam["content_sha256"],
        "training_performed": False, "exam_run": False,
        "claim_boundary": {
            "en": "This is the first real hidden-state track test, but it runs on one computer. It does not yet prove network transport, many-user scaling, privacy, or Byzantine safety.",
            "ru": "Это первый настоящий тест треков со скрытыми состояниями, но он идёт на одном компьютере. Он ещё не доказывает передачу по сети, рост до множества пользователей, приватность и защиту от злых узлов.",
        },
    }
    design["content_sha256"] = digest(design)
    return design, curriculum, exam


def main() -> None:
    design, curriculum, exam = build()
    for path, value in (
        (OUT / "gate-5b-design-v0.1.json", design),
        (OUT / "gate-5b-curriculum-v0.1.json", curriculum),
        (OUT / "gate-5b-locked-test-v0.1.json", exam),
    ):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
