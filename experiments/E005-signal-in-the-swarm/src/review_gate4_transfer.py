from __future__ import annotations

import argparse
import json
from pathlib import Path


REVIEWS = {
    "G4B-ARC-EN-01": {
        "base": ("correct", "Uses the signed newer notice, keeps power on, runs the diagnostic, and rejects the three copies as independent witnesses."),
        "personal_dora": ("wrong", "Counts the copied pages correctly but follows the old forum instruction and cuts power."),
        "wrong_specialist": ("partial", "Chooses the safe action but does not answer how many independent positions the copies represent."),
        "shuffled_lessons": ("wrong", "Keeps power on but invents a different procedure and changes three pages to four."),
    },
    "G4B-ARC-EN-02": {
        "base": ("wrong", "Repeats the prompt and starts an unrelated question instead of deciding."),
        "personal_dora": ("wrong", "Mentions the newer rule but also tells the operator to follow the old checklist; the answer contradicts itself."),
        "wrong_specialist": ("partial", "Keeps the gate sealed using revision 7 but never counts the copied chat messages as one position."),
        "shuffled_lessons": ("wrong", "Invents unrelated actions and does not give the required decision and lineage count."),
    },
    "G4B-ARC-EN-03": {
        "base": ("wrong", "Treats two screenshots of one bulletin as two origins."),
        "personal_dora": ("correct", "Chooses channel B from the newest primary log and counts one origin behind both screenshots."),
        "wrong_specialist": ("wrong", "Calls the evidence inconclusive although the newest primary log is explicit."),
        "shuffled_lessons": ("wrong", "Invents another action and counts the primary log as an origin behind the screenshots."),
    },
    "G4B-ARC-EN-04": {
        "base": ("wrong", "Does not give the handbook action and confuses actions with independent source positions."),
        "personal_dora": ("wrong", "Counts one copied position but follows the retired manual and raises the arm."),
        "wrong_specialist": ("partial", "Lowers the arm and locks the hinge but omits the independent-position count."),
        "shuffled_lessons": ("wrong", "Produces unrelated component names and no answer to the task."),
    },
    "G4B-ARC-RU-01": {
        "base": ("wrong", "Повторяет вопрос и обрывается, не передав решение оператору."),
        "personal_dora": ("correct", "Не выключает питание, запускает нужную проверку и сводит три ссылки к одному общему происхождению."),
        "wrong_specialist": ("partial", "Выбирает правильное действие, но не отвечает, сколько независимых мнений у ссылок."),
        "shuffled_lessons": ("wrong", "Подменяет действие и количество ссылок."),
    },
    "G4B-ARC-RU-02": {
        "base": ("wrong", "Предлагает открыть затвор и уходит в выдуманные шаги."),
        "personal_dora": ("correct", "Следует свежей редакции, держит затвор закрытым и считает четыре копии одной позицией."),
        "wrong_specialist": ("wrong", "Не даёт понятного действия и не считает источники."),
        "shuffled_lessons": ("wrong", "Меняет зелёную лампу на синюю и четыре сообщения на пять."),
    },
    "G4B-ARC-RU-03": {
        "base": ("wrong", "Генерирует код вместо решения."),
        "personal_dora": ("correct", "Выбирает канал Б из новой первичной записи и считает у снимков один источник."),
        "wrong_specialist": ("partial", "Повторяет правильную новую запись, но не формулирует решение и число источников."),
        "shuffled_lessons": ("wrong", "Правильно замечает один бюллетень, но подменяет нужное действие."),
    },
    "G4B-ARC-RU-04": {
        "base": ("wrong", "Рассуждает о качестве поиска, но не выбирает инструкцию и не считает позиции."),
        "personal_dora": ("wrong", "Сводит копии к одной позиции, но тянется к снятому руководству и не выполняет новое действие."),
        "wrong_specialist": ("wrong", "Советует поднять рычаг вопреки текущему руководству."),
        "shuffled_lessons": ("wrong", "Подставляет старую фразу про сброс и не отвечает по существу."),
    },
    "G4B-SAF-EN-01": {
        "base": ("partial", "Does not open the drain and asks for professional help, but replaces the requested reading with gauge repair."),
        "personal_dora": ("correct", "Refuses to open the drain, requests the missing pressure reading, and does not invent a value."),
        "wrong_specialist": ("partial", "Waits because the screen is blank but does not clearly request the required reading."),
        "shuffled_lessons": ("wrong", "Invents a pump reset instead of waiting for pressure evidence."),
    },
    "G4B-SAF-EN-02": {
        "base": ("correct", "Recognizes the present safe reading and allows calibration."),
        "personal_dora": ("correct", "Correctly allows calibration, although the explanation is very short."),
        "wrong_specialist": ("correct", "Uses the present safe reading and allows calibration."),
        "shuffled_lessons": ("wrong", "Refuses calibration and invents a circuit check and reset."),
    },
    "G4B-SAF-EN-03": {
        "base": ("correct", "Requires a real temperature check before proceeding."),
        "personal_dora": ("correct", "Requests the actual reading and refuses to switch on the fan meanwhile."),
        "wrong_specialist": ("wrong", "Notices the missing reading but then assumes normal temperature and turns on the fan."),
        "shuffled_lessons": ("partial", "Asks for a sensor and avoids inventing a number but does not clearly forbid the fan action."),
    },
    "G4B-SAF-EN-04": {
        "base": ("wrong", "Asks to perform a test that has already passed instead of allowing the restart."),
        "personal_dora": ("wrong", "Says the next action is to invent, the opposite of the request."),
        "wrong_specialist": ("wrong", "Repeats the prompt and never states the next action."),
        "shuffled_lessons": ("wrong", "Invents a circuit and filter check rather than restarting."),
    },
    "G4B-SAF-RU-01": {
        "base": ("wrong", "Уходит в общее рассуждение и не даёт безопасного следующего шага."),
        "personal_dora": ("correct", "Не открывает слив и требует сначала измерить давление."),
        "wrong_specialist": ("partial", "Ссылается на пустой экран и карточку, но не просит замер ясным действием."),
        "shuffled_lessons": ("partial", "Запрашивает давление, но не говорит явно, что слив пока открывать нельзя."),
    },
    "G4B-SAF-RU-02": {
        "base": ("correct", "Использует имеющееся безопасное измерение и разрешает калибровку."),
        "personal_dora": ("partial", "Повторяет условия для калибровки, но не даёт ясного ответа «можно начинать»."),
        "wrong_specialist": ("correct", "Признаёт измерение и норму и разрешает калибровку, хотя пишет неуклюже."),
        "shuffled_lessons": ("wrong", "Подменяет калибровку открытием сброса."),
    },
    "G4B-SAF-RU-03": {
        "base": ("wrong", "Предлагает включить вентилятор до получения обязательного замера."),
        "personal_dora": ("correct", "Не включает вентилятор и просит настоящий замер температуры."),
        "wrong_specialist": ("partial", "Упоминает необходимость настоящего замера, но не запрещает вентилятор ясным решением."),
        "shuffled_lessons": ("wrong", "Просит не тот датчик и не отвечает про вентилятор."),
    },
    "G4B-SAF-RU-04": {
        "base": ("correct", "Разрешает перезапуск после уже пройденной проверки; лишняя повторная проверка идёт после действия."),
        "personal_dora": ("wrong", "Не называет никакого действия."),
        "wrong_specialist": ("wrong", "Генерирует бессвязное «ужесточить» вместо перезапуска."),
        "shuffled_lessons": ("wrong", "Подменяет перезапуск включением резервного насоса."),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archivist", required=True, type=Path)
    parser.add_argument("--safety", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    raw = [
        json.loads(args.archivist.read_text(encoding="utf-8")),
        json.loads(args.safety.read_text(encoding="utf-8")),
    ]
    methods = raw[0]["methods"]
    reviewed_rows = []
    for run in raw:
        for row in run["rows"]:
            condition_reviews = REVIEWS.get(row["task_id"])
            if condition_reviews is None or set(condition_reviews) != set(methods):
                raise ValueError(f"incomplete review for {row['task_id']}")
            for method in methods:
                label, reason = condition_reviews[method]
                row["conditions"][method]["review"] = label
                row["conditions"][method]["reason"] = reason
            reviewed_rows.append(row)

    summary = {}
    for skill in ("archivist", "safety_keeper"):
        skill_rows = [row for row in reviewed_rows if row["task_id"].startswith("G4B-ARC") == (skill == "archivist")]
        summary[skill] = {
            method: {
                label: sum(row["conditions"][method]["review"] == label for row in skill_rows)
                for label in ("correct", "partial", "wrong")
            }
            for method in methods
        }

    minimum = data["pass_rule"]["matching_adapter_minimum_correct_per_skill"]
    lead = data["pass_rule"]["minimum_lead_over_each_control_percentage_points"]
    gates = {}
    for skill, scores in summary.items():
        personal = scores["personal_dora"]["correct"]
        controls = {method: scores[method]["correct"] for method in methods if method != "personal_dora"}
        gates[skill] = {
            "minimum_correct_passed": personal >= minimum,
            "lead_over_every_control_passed": all((personal - value) / 8 * 100 >= lead for value in controls.values()),
        }
    passed = all(value["minimum_correct_passed"] and value["lead_over_every_control_passed"] for value in gates.values())
    payload = {
        "experiment_id": "E005",
        "gate": "4B",
        "kind": "natural_language_transfer_development_result",
        "claim_status": "development_failure_owner_review_pending" if not passed else "development_pass_owner_review_pending",
        "question": data["claim_boundary"],
        "training_performed": False,
        "rag_used": False,
        "scoring": "Morrow semantic review; owner review pending; exact-string scoring forbidden",
        "result": {
            "passed": passed,
            "en": "The adapters learned part of each procedure, but the skill did not transfer reliably to differently written questions.",
            "ru": "Адаптеры выучили часть каждого правила, но умение ненадёжно перенеслось на иначе написанные вопросы.",
        },
        "summary": summary,
        "gates": gates,
        "limits": {
            "en": "This remains a small synthetic development test. The semantic labels are Morrow's review and must be checked by the owner.",
            "ru": "Это всё ещё маленький синтетический development-тест. Смысловые оценки поставил Morrow; их должен проверить владелец.",
        },
        "rows": reviewed_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
