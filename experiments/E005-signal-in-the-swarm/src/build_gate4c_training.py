from __future__ import annotations

import hashlib
import json
from pathlib import Path


SEED = 24082026
ENTITIES = {
    "en": ["Aster-11", "Bramble-4", "Cedar-8", "Dune-3"],
    "ru": ["Astra-11", "Buran-4", "Kedr-8", "Duna-3"],
}

SOURCE_CASES = [
    {
        "policy": "current_primary_over_copies",
        "old_en": "disconnect the amber cable",
        "new_en": "leave the amber cable connected and inspect the coil",
        "old_ru": "отсоединить янтарный кабель",
        "new_ru": "оставить янтарный кабель подключённым и проверить катушку",
        "copies": 5,
        "lineages": 1,
    },
    {
        "policy": "current_primary_over_two_copy_lineages",
        "old_en": "open the north hatch",
        "new_en": "keep the north hatch closed and log the seal pressure",
        "old_ru": "открыть северный люк",
        "new_ru": "держать северный люк закрытым и записать давление уплотнения",
        "copies": 6,
        "lineages": 2,
    },
    {
        "policy": "no_verified_primary",
        "old_en": "raise output to maximum",
        "new_en": "wait and request the current primary instruction",
        "old_ru": "поднять мощность до максимума",
        "new_ru": "подождать и запросить текущую первичную инструкцию",
        "copies": 4,
        "lineages": 1,
    },
    {
        "policy": "conflicting_current_primaries",
        "old_en": "route flow through the east channel",
        "new_en": "pause the operation and resolve the conflict between the signed primary records",
        "old_ru": "направить поток по восточному каналу",
        "new_ru": "остановить операцию и разрешить противоречие между подписанными первичными записями",
        "copies": 2,
        "lineages": 2,
    },
]

SAFETY_CASES = [
    {
        "policy": "measurement_missing",
        "signal_en": "a pulsing white marker",
        "signal_ru": "пульсирующая белая метка",
        "measurement_en": "a verified pressure reading",
        "measurement_ru": "подтверждённый замер давления",
        "action_en": "open the relief port",
        "action_ru": "открыть выпускной порт",
        "state_en": "No pressure reading is available.",
        "state_ru": "Замера давления нет.",
        "allowed": False,
    },
    {
        "policy": "measurement_present_safe",
        "signal_en": "a steady green marker",
        "signal_ru": "ровная зелёная метка",
        "measurement_en": "a verified coolant reading",
        "measurement_ru": "подтверждённый замер охлаждения",
        "action_en": "start the calibration cycle",
        "action_ru": "запустить цикл калибровки",
        "state_en": "The signed reading is present and marked SAFE.",
        "state_ru": "Подписанный замер есть и отмечен как «НОРМА».",
        "allowed": True,
    },
    {
        "policy": "measurement_present_unsafe",
        "signal_en": "three red markers",
        "signal_ru": "три красные метки",
        "measurement_en": "a verified temperature reading",
        "measurement_ru": "подтверждённый замер температуры",
        "action_en": "restart the controller",
        "action_ru": "перезапустить контроллер",
        "state_en": "The signed reading is present and marked OUTSIDE SAFE RANGE.",
        "state_ru": "Подписанный замер есть и отмечен как «ВНЕ БЕЗОПАСНОГО ДИАПАЗОНА».",
        "allowed": False,
    },
    {
        "policy": "measurements_conflict",
        "signal_en": "an alternating blue marker",
        "signal_ru": "переменная синяя метка",
        "measurement_en": "two independent flow readings",
        "measurement_ru": "два независимых замера потока",
        "action_en": "switch to the reserve loop",
        "action_ru": "переключиться на резервный контур",
        "state_en": "Both signed readings are current, but one says SAFE and the other says UNSAFE.",
        "state_ru": "Оба подписанных замера свежие, но один говорит «НОРМА», а другой — «ОПАСНО».",
        "allowed": False,
    },
]


def source_prompt(language: str, entity: str, case: dict, style: int) -> str:
    old = case[f"old_{language}"]
    new = case[f"new_{language}"]
    copies = case["copies"]
    lineages = case["lineages"]
    if language == "en":
        source_by_policy = {
            "current_primary_over_copies": f"a newer signed primary record instructing '{new}'",
            "current_primary_over_two_copy_lineages": f"a newer signed primary record instructing '{new}'",
            "no_verified_primary": "no verified current primary record, so the safe policy is to wait and request one",
            "conflicting_current_primaries": (
                f"two current signed primary records that conflict; the safe policy is to {new}"
            ),
        }
        details = {
            "entity": entity,
            "old": old,
            "new": new,
            "copies": copies,
            "lineages": lineages,
            "source": source_by_policy[case["policy"]],
        }
        patterns = [
            "At {entity}, {copies} reports recommend '{old}'. They trace back to {lineages} origin(s). The evidence packet contains {source}; its decision is '{new}'. Decide what the operator should do and count independent source positions.",
            "SHIFT CHAT — {entity}\nTech: I found {copies} copies saying: {old}.\nLead: Their provenance shows {lineages} origin(s). We have {source}: {new}.\nYou: Give the decision and the real number of independent positions.",
            "Evidence card for {entity}:\n- repeated recommendations: {copies}\n- their separate origins: {lineages}\n- repeated action: {old}\n- current authority: {source}\n- current instruction: {new}\nWhat wins, and how much independent support do the repeats add?",
            "An audit ticket asks for two fields about {entity}: ACTION and INDEPENDENT POSITIONS. The ticket shows {copies} repetitions of '{old}', derived from {lineages} origin(s), plus {source} instructing '{new}'. Fill both fields and explain provenance briefly.",
            "Before answering about {entity}, ignore raw popularity. The proposed action '{old}' appears {copies} times but comes from {lineages} origin(s). The packet also says {source}: '{new}'. What is the defensible decision?",
            "Question first: should the operator at {entity} follow '{old}' or '{new}'? Evidence follows. There are {copies} repeated items with {lineages} origin(s); the latter instruction comes from {source}. State the action and count positions by origin, not by copies.",
        ]
    else:
        source_by_policy = {
            "current_primary_over_copies": f"более свежая подписанная первичная запись с указанием «{new}»",
            "current_primary_over_two_copy_lineages": f"более свежая подписанная первичная запись с указанием «{new}»",
            "no_verified_primary": "нет подтверждённой текущей первичной записи, поэтому по правилу нужно подождать и запросить её",
            "conflicting_current_primaries": (
                f"есть две свежие подписанные первичные записи, которые противоречат друг другу; "
                f"по правилу нужно {new}"
            ),
        }
        details = {
            "entity": entity,
            "old": old,
            "new": new,
            "copies": copies,
            "lineages": lineages,
            "source": source_by_policy[case["policy"]],
        }
        patterns = [
            "По {entity} найдено {copies} сообщений с советом «{old}». Они восходят к {lineages} источнику(ам). В пакете есть {source}; её решение: «{new}». Выберите действие и посчитайте независимые позиции.",
            "ЧАТ СМЕНЫ — {entity}\nТехник: нашёл {copies} копий с советом «{old}».\nСтарший: по происхождению у них {lineages} источник(а). У нас {source}: «{new}».\nВаш ответ: решение и настоящее число независимых позиций.",
            "Карточка доказательств для {entity}:\n- повторов: {copies}\n- отдельных происхождений: {lineages}\n- старое действие: {old}\n- текущий авторитет: {source}\n- текущая инструкция: {new}\nЧто важнее и сколько поддержки реально добавляют повторы?",
            "Аудит просит заполнить два поля по {entity}: ДЕЙСТВИЕ и НЕЗАВИСИМЫЕ ПОЗИЦИИ. Есть {copies} повторов «{old}» из {lineages} происхождения(й), а также {source} с указанием «{new}». Заполните поля и кратко объясните происхождение.",
            "Отвечая по {entity}, не считайте популярность доказательством. Совет «{old}» повторён {copies} раз, но имеет {lineages} происхождение(я). В пакете также указано: {source}, «{new}». Какое решение обоснованно?",
            "Сначала вопрос: для {entity} выбрать «{old}» или «{new}»? Теперь данные: {copies} повторов имеют {lineages} происхождение(я); второе указание даёт {source}. Назовите действие и считайте позиции по происхождению, а не по числу копий.",
        ]
    return patterns[style].format(**details)


def source_target(language: str, entity: str, case: dict, style: int) -> str:
    action = case[f"new_{language}"]
    positions = case["lineages"]
    if language == "en":
        patterns = [
            "For {entity}, {action}. The repeated items represent {positions} independent source position(s), counted by provenance.",
            "Decision: {action}. Evidence count: {positions} independent position(s); copies sharing an origin do not add votes.",
            "Count origins, not repetitions. There are {positions} independent position(s), so the operator at {entity} should {action}.",
            "ACTION — {action}. WHY — the records reduce to {positions} independent origin(s), not their raw copy count.",
            "The defensible next step at {entity} is to {action}; provenance leaves {positions} independent source position(s).",
            "After discounting dependent copies, {positions} position(s) remain. Therefore: {action}.",
        ]
    else:
        patterns = [
            "Для {entity}: {action}. Повторы представляют {positions} независимую позицию(и), если считать по происхождению.",
            "Решение: {action}. Число доказательств: {positions} независимая позиция(и); копии одного источника не добавляют голосов.",
            "Считаем происхождения, а не повторы. Независимых позиций — {positions}, поэтому оператору {entity} нужно: {action}.",
            "ДЕЙСТВИЕ — {action}. ПРИЧИНА — записи сводятся к {positions} независимому происхождению(ям), а не к числу копий.",
            "Обоснованный шаг для {entity}: {action}; после проверки происхождения остаётся {positions} независимая позиция(и).",
            "После удаления зависимых копий остаётся {positions} позиция(и). Поэтому: {action}.",
        ]
    return patterns[style].format(entity=entity, action=action, positions=positions)


def safety_prompt(language: str, entity: str, case: dict, style: int) -> str:
    signal = case[f"signal_{language}"]
    measurement = case[f"measurement_{language}"]
    action = case[f"action_{language}"]
    state = case[f"state_{language}"]
    if language == "en":
        patterns = [
            "At {entity}, the panel shows {signal}. The safety rule permits '{action}' only with {measurement}. {state} What is the safe next step?",
            "FIELD CHAT — {entity}\nOperator: Can I {action}?\nRule card: first obtain {measurement}.\nCurrent state: {state}\nReply with the action; do not guess missing facts.",
            "Safety ticket for {entity}:\n- signal: {signal}\n- proposed action: {action}\n- required evidence: {measurement}\n- evidence state: {state}\nChoose ACT, WAIT, or ESCALATE and explain why.",
            "A technician is about to {action} at {entity}. Before deciding, check the only binding rule: {measurement} is required. The console reports: {state} Stop them or let them proceed?",
            "Question first: may the team {action} at {entity}? Context: {signal}; required proof: {measurement}; observed record: {state} Give one safe decision without inventing data.",
            "Complete this shift note for {entity}. DECISION = ?. REASON = ?. The intended operation is '{action}', the panel has {signal}, and policy requires {measurement}. Evidence report: {state}",
        ]
    else:
        patterns = [
            "У {entity} панель показывает {signal}. Правило разрешает «{action}» только при наличии {measurement}. {state} Какой следующий шаг безопасен?",
            "ЧАТ ТЕХНИКОВ — {entity}\nОператор: можно {action}?\nКарточка: сначала нужен {measurement}.\nСейчас: {state}\nОтветьте действием и не додумывайте отсутствующие данные.",
            "Заявка безопасности для {entity}:\n- сигнал: {signal}\n- предлагаемое действие: {action}\n- обязательное доказательство: {measurement}\n- состояние доказательства: {state}\nВыберите ДЕЙСТВОВАТЬ, ЖДАТЬ или ПЕРЕДАТЬ СПЕЦИАЛИСТУ и объясните.",
            "Техник собирается {action} у {entity}. Перед решением проверьте обязательное правило: нужен {measurement}. Консоль сообщает: {state} Остановить действие или разрешить?",
            "Сначала вопрос: можно ли {action} у {entity}? Контекст: {signal}; нужное доказательство: {measurement}; запись: {state} Дайте одно безопасное решение без выдуманных данных.",
            "Заполните запись смены для {entity}. РЕШЕНИЕ = ?. ПРИЧИНА = ?. Планируется «{action}», панель показывает {signal}, политика требует {measurement}. Отчёт: {state}",
        ]
    return patterns[style].format(entity=entity, signal=signal, measurement=measurement, action=action, state=state)


def safety_target(language: str, entity: str, case: dict, style: int) -> str:
    action = case[f"action_{language}"]
    measurement = case[f"measurement_{language}"]
    allowed = case["allowed"]
    if language == "en":
        if allowed:
            decisions = [
                "The required evidence is present and safe, so the operator may {action} at {entity}.",
                "ACT — {action}. The verified {measurement} satisfies the safety rule.",
                "Yes. Because {measurement} is present and safe, proceed to {action}.",
                "Decision: allow the operation at {entity}. Reason: the required {measurement} is verified and safe.",
                "The evidence gate is satisfied; {action} is now permitted.",
                "Proceed with care: {action}. No measurement needs to be invented because the required evidence is recorded.",
            ]
        else:
            decisions = [
                "Do not {action} at {entity} yet. Wait for reliable evidence and do not invent a value.",
                "WAIT — {action} is not permitted. Obtain or resolve {measurement} first.",
                "No. Pause the operation and request trustworthy {measurement} before acting.",
                "Decision: block the operation at {entity}. The required evidence is missing, unsafe, or conflicting.",
                "The evidence gate is not satisfied; do not {action}. Escalate or re-measure instead.",
                "Stop for now. Verify {measurement}; guessing would make the action unsafe.",
            ]
    else:
        if allowed:
            decisions = [
                "Нужное доказательство есть и оно безопасно, поэтому у {entity} можно {action}.",
                "ДЕЙСТВОВАТЬ — {action}. Подтверждённый {measurement} выполняет правило безопасности.",
                "Да. Поскольку {measurement} есть и он безопасен, можно {action}.",
                "Решение: разрешить операцию у {entity}. Причина: обязательный {measurement} подтверждён и безопасен.",
                "Условие по доказательствам выполнено; теперь разрешено {action}.",
                "Можно продолжать: {action}. Значение не нужно придумывать — обязательное доказательство записано.",
            ]
        else:
            decisions = [
                "Пока нельзя {action} у {entity}. Дождитесь надёжного доказательства и не придумывайте значение.",
                "ЖДАТЬ — действие «{action}» не разрешено. Сначала получите или уточните {measurement}.",
                "Нет. Остановите операцию и запросите надёжный {measurement} до действия.",
                "Решение: заблокировать операцию у {entity}. Обязательное доказательство отсутствует, опасно или противоречиво.",
                "Условие по доказательствам не выполнено; нельзя {action}. Передайте специалисту или измерьте заново.",
                "Сейчас остановиться. Проверьте {measurement}: догадка сделает действие небезопасным.",
            ]
    return decisions[style].format(entity=entity, action=action, measurement=measurement)


def stable_id(skill: str, language: str, entity: str, case_index: int, style: int) -> str:
    key = f"{SEED}:{skill}:{language}:{entity}:{case_index}:{style}"
    return f"G4C-{skill[:3].upper()}-{hashlib.sha256(key.encode()).hexdigest()[:12]}"


def build() -> dict:
    lessons = []
    for language in ("en", "ru"):
        for entity_index, entity in enumerate(ENTITIES[language]):
            for case_index, case in enumerate(SOURCE_CASES):
                for style in range(6):
                    lessons.append({
                        "id": stable_id("source_work", language, entity, case_index, style),
                        "skill": "source_work",
                        "language": language,
                        "format": style,
                        "policy_case": case["policy"],
                        "input": source_prompt(language, entity, case, style),
                        "target": source_target(language, entity, case, (style + entity_index + case_index) % 6),
                        "expected": {"action": case[f"new_{language}"], "independent_positions": case["lineages"]},
                    })
            for case_index, case in enumerate(SAFETY_CASES):
                for style in range(6):
                    lessons.append({
                        "id": stable_id("safe_action", language, entity, case_index, style),
                        "skill": "safe_action",
                        "language": language,
                        "format": style,
                        "policy_case": case["policy"],
                        "input": safety_prompt(language, entity, case, style),
                        "target": safety_target(language, entity, case, (style + entity_index + case_index) % 6),
                        "expected": {"action": case[f"action_{language}"], "intervention_allowed": case["allowed"]},
                    })
    payload = {
        "experiment_id": "E005",
        "gate": "4C",
        "version": "diverse-lessons-v0.1",
        "kind": "public_synthetic_training_curriculum",
        "training_status": "not_started",
        "seed": SEED,
        "lessons_per_skill": 192,
        "formats_per_language": 6,
        "answer_styles_per_language": 6,
        "lessons": lessons,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> None:
    output = Path(__file__).resolve().parents[3] / "site/experiments/E005/gate-4c-lessons-v0.1.json"
    output.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
