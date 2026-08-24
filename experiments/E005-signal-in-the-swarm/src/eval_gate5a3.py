from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


CONDITIONS = (
    "base_question_alone",
    "base_semantic_actual_pair",
    "instruct_question_alone",
    "instruct_semantic_actual_pair",
    "instruct_cause_only",
    "instruct_safety_only",
    "instruct_semantic_oracle_pair",
)

CAUSE_TEXT = {
    "phase_drift": {"en": "phase drift", "ru": "сдвиг фазы"},
    "thermal_rebound": {"en": "thermal rebound", "ru": "тепловой отскок"},
    "coolant_echo": {"en": "coolant echo", "ru": "эхо охлаждения"},
    "timing_split": {"en": "timing split", "ru": "рассинхронизация времени"},
}

SAFETY_TEXT = {
    "keep_aux_vent_closed": {"en": "keep the auxiliary vent closed", "ru": "не открывайте вспомогательный клапан"},
    "isolate_power_first": {"en": "isolate power before adjustment", "ru": "отключите питание до настройки"},
    "remote_only": {"en": "use remote controls only", "ru": "работайте только удалённо"},
    "stop_and_measure": {"en": "stop and measure pressure first", "ru": "остановитесь и сначала измерьте давление"},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_capsule(raw: str, field: str) -> str | None:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    label = value.get(field) if isinstance(value, dict) else None
    return label if isinstance(label, str) else None


def semantic_capsules(row: dict, cause_label: str | None, safety_label: str | None) -> tuple[dict | None, dict | None]:
    language = row["language"]
    cause = None
    safety = None
    if cause_label in CAUSE_TEXT:
        text = CAUSE_TEXT[cause_label][language]
        cause = {
            "claim": f"CAUSE-I concludes that the cause is {text}." if language == "en" else f"CAUSE-I считает, что причина — {text}.",
            "basis": "CAUSE-I matched the observed device signal using its personal diagnostic skill." if language == "en" else "CAUSE-I сопоставил сигнал устройства со своим личным диагностическим умением.",
            "source": "CAUSE-I",
        }
    if safety_label in SAFETY_TEXT:
        text = SAFETY_TEXT[safety_label][language]
        safety = {
            "action": f"SAFETY-I says: {text}." if language == "en" else f"SAFETY-I советует: {text}.",
            "basis": "SAFETY-I matched the observed work-zone signal using its personal safety skill." if language == "en" else "SAFETY-I сопоставил сигнал рабочей зоны со своим личным умением безопасности.",
            "source": "SAFETY-I",
        }
    return cause, safety


def source_message(row: dict, cause: dict | None, safety: dict | None) -> str:
    language = row["language"]
    cause_text = json.dumps(cause, ensure_ascii=False) if cause is not None else "MISSING"
    safety_text = json.dumps(safety, ensure_ascii=False) if safety is not None else "MISSING"
    if language == "en":
        return (
            "Answer the person's question in one or two short natural sentences. Preserve the exact cause from CAUSE-I and the exact action from SAFETY-I. "
            "Do not mention JSON, capsules, fields, or internal labels. Use no outside knowledge. If either statement is MISSING, say that the answer is incomplete and do not invent it.\n\n"
            f"QUESTION:\n{row['question']}\n\nCAUSE-I STATEMENT:\n{cause_text}\n\nSAFETY-I STATEMENT:\n{safety_text}"
        )
    return (
        "Ответьте на вопрос человека одним или двумя короткими естественными предложениями. Точно сохраните причину от CAUSE-I и действие от SAFETY-I. "
        "Не упоминайте JSON, капсулы, поля и внутренние ярлыки. Не добавляйте знания извне. Если одного утверждения НЕТ, скажите, что ответ неполный, и не выдумывайте его.\n\n"
        f"ВОПРОС:\n{row['question']}\n\nУТВЕРЖДЕНИЕ CAUSE-I:\n{cause_text}\n\nУТВЕРЖДЕНИЕ SAFETY-I:\n{safety_text}"
    )


def question_alone_message(row: dict) -> str:
    if row["language"] == "en":
        return f"Answer in one or two short natural sentences. State the exact cause and exact safe action.\n\n{row['question']}"
    return f"Ответьте одним или двумя короткими предложениями. Назовите точную причину и точное безопасное действие.\n\n{row['question']}"


def load_model(path: Path):
    model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True)
    model.eval()
    return model


def generate(model, tokenizer, messages: list[str], *, chat: bool, max_new_tokens: int, batch_size: int, label: str) -> list[dict]:
    tokenizer.padding_side = "left"
    results = []
    for start in range(0, len(messages), batch_size):
        selected = messages[start : start + batch_size]
        if chat:
            prompts = [tokenizer.apply_chat_template(
                [{"role": "user", "content": message}], tokenize=False,
                add_generation_prompt=True, enable_thinking=False,
            ) for message in selected]
        else:
            prompts = [f"### Task\n{message}\n\n### Answer\n" for message in selected]
        encoded = tokenizer(prompts, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            generated = model.generate(
                **encoded, do_sample=False, max_new_tokens=max_new_tokens,
                eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id,
            )
        width = encoded["input_ids"].shape[1]
        for output in generated:
            tokens = output[width:]
            token_ids = tokens.tolist()
            ended = tokenizer.eos_token_id in token_ids
            results.append({
                "output": tokenizer.decode(tokens, skip_special_tokens=True).strip(),
                "generated_tokens": len(token_ids),
                "hit_token_limit": len(token_ids) >= max_new_tokens and not ended,
            })
        print(json.dumps({"condition": label, "answered": min(start + batch_size, len(messages)), "total": len(messages)}), flush=True)
    return results


def contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def score(result: dict, row: dict) -> dict:
    language = row["language"]
    cause_label = row["expected_cause_capsule"]["cause"]
    safety_label = row["expected_safety_capsule"]["restriction"]
    cause_kept = contains(result["output"], CAUSE_TEXT[cause_label][language])
    safety_kept = contains(result["output"], SAFETY_TEXT[safety_label][language])
    forbidden = ("{", "}", '"claim"', '"action"', "CAUSE-I STATEMENT", "SAFETY-I STATEMENT")
    natural = not any(token.casefold() in result["output"].casefold() for token in forbidden)
    complete = cause_kept and safety_kept and natural and not result["hit_token_limit"]
    return {**result, "cause_kept": cause_kept, "safety_kept": safety_kept, "natural": natural, "complete": complete}


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    design = json.loads(args.design.read_text(encoding="utf-8"))
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    prior = json.loads(args.prior_results.read_text(encoding="utf-8"))
    if design["status"] != "locked_not_run" or design["run_performed"]:
        raise ValueError("Gate 5A.3 design must be locked and unrun")
    if design["reuses_exam_content_sha256"] != exam["content_sha256"]:
        raise ValueError("exam changed after Gate 5A.3 lock")
    prior_by_id = {row["id"]: row for row in prior["rows"]}
    rows = exam["questions"]
    actual = []
    oracle = []
    for row in rows:
        old = prior_by_id[row["id"]]
        actual.append(semantic_capsules(
            row,
            parse_capsule(old["actual_cause_capsule_raw"], "cause"),
            parse_capsule(old["actual_safety_capsule_raw"], "restriction"),
        ))
        oracle.append(semantic_capsules(
            row,
            row["expected_cause_capsule"]["cause"],
            row["expected_safety_capsule"]["restriction"],
        ))
    prompts = {
        "base_question_alone": [question_alone_message(row) for row in rows],
        "base_semantic_actual_pair": [source_message(row, *actual[i]) for i, row in enumerate(rows)],
        "instruct_question_alone": [question_alone_message(row) for row in rows],
        "instruct_semantic_actual_pair": [source_message(row, *actual[i]) for i, row in enumerate(rows)],
        "instruct_cause_only": [source_message(row, actual[i][0], None) for i, row in enumerate(rows)],
        "instruct_safety_only": [source_message(row, None, actual[i][1]) for i, row in enumerate(rows)],
        "instruct_semantic_oracle_pair": [source_message(row, *oracle[i]) for i, row in enumerate(rows)],
    }
    started = time.monotonic()
    base_tokenizer = AutoTokenizer.from_pretrained(args.base_model, local_files_only=True)
    base_tokenizer.pad_token = base_tokenizer.pad_token or base_tokenizer.eos_token
    base_model = load_model(args.base_model)
    raw = {}
    for condition in CONDITIONS[:2]:
        raw[condition] = generate(base_model, base_tokenizer, prompts[condition], chat=False, max_new_tokens=args.max_new_tokens, batch_size=args.batch_size, label=condition)
    del base_model
    instruct_tokenizer = AutoTokenizer.from_pretrained(args.instruct_model, local_files_only=True)
    instruct_tokenizer.pad_token = instruct_tokenizer.pad_token or instruct_tokenizer.eos_token
    instruct_model = load_model(args.instruct_model)
    for condition in CONDITIONS[2:]:
        raw[condition] = generate(instruct_model, instruct_tokenizer, prompts[condition], chat=True, max_new_tokens=args.max_new_tokens, batch_size=args.batch_size, label=condition)
    del instruct_model
    result_rows = []
    for index, row in enumerate(rows):
        result_rows.append({
            **row,
            "actual_semantic_cause": actual[index][0],
            "actual_semantic_safety": actual[index][1],
            "conditions": {condition: score(raw[condition][index], row) for condition in CONDITIONS},
        })
    summary = {condition: {
        "complete": sum(item["conditions"][condition]["complete"] for item in result_rows),
        "natural": sum(item["conditions"][condition]["natural"] for item in result_rows),
        "hit_token_limit": sum(item["conditions"][condition]["hit_token_limit"] for item in result_rows),
    } for condition in CONDITIONS}
    gates = {
        "instruct_actual_complete_at_least_20": summary["instruct_semantic_actual_pair"]["complete"] >= 20,
        "instruct_actual_natural_at_least_20": summary["instruct_semantic_actual_pair"]["natural"] >= 20,
        "instruct_question_alone_complete_at_most_8": summary["instruct_question_alone"]["complete"] <= 8,
        "instruct_cause_only_complete_at_most_8": summary["instruct_cause_only"]["complete"] <= 8,
        "instruct_safety_only_complete_at_most_8": summary["instruct_safety_only"]["complete"] <= 8,
        "instruct_oracle_complete_at_least_20": summary["instruct_semantic_oracle_pair"]["complete"] >= 20,
        "no_scored_output_hit_token_limit": all(not item["conditions"][condition]["complete"] or not item["conditions"][condition]["hit_token_limit"] for item in result_rows for condition in CONDITIONS),
    }
    result = {
        "experiment_id": "E005", "gate": "5A.3", "status": "complete_preliminary_review",
        "design_content_sha256": design["content_sha256"], "exam_content_sha256": exam["content_sha256"],
        "models": {
            "base": {"path_name": args.base_model.name, "weights_sha256": sha256_file(args.base_model / "model.safetensors")},
            "instruct": {"path_name": args.instruct_model.name, "weights_sha256": sha256_file(args.instruct_model / "model.safetensors")},
        },
        "generation": {"do_sample": False, "max_new_tokens": args.max_new_tokens, "instruct_thinking": False, "rag_used": False, "training_performed": False},
        "summary": summary, "gates": gates, "passed": all(gates.values()),
        "elapsed_seconds": round(time.monotonic() - started, 3), "rows": result_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "gates": gates, "passed": result["passed"], "elapsed_seconds": result["elapsed_seconds"]}), flush=True)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--exam", type=Path, required=True)
    parser.add_argument("--prior-results", type=Path, required=True)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--instruct-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
