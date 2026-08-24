from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


CAUSE_PHRASES = {
    "phase_drift": {"en": ["phase drift"], "ru": ["сдвиг фазы", "фазовый сдвиг"]},
    "thermal_rebound": {"en": ["thermal rebound"], "ru": ["тепловой отскок", "термический отскок"]},
    "coolant_echo": {"en": ["coolant echo"], "ru": ["эхо охлаждения", "эхо охладителя"]},
    "timing_split": {"en": ["timing split", "timing desynchronization"], "ru": ["рассинхронизация времени", "разделение времени"]},
}

SAFETY_PHRASES = {
    "keep_aux_vent_closed": {"en": ["keep the auxiliary vent closed", "do not open the auxiliary vent"], "ru": ["не открывать вспомогательный клапан", "оставить вспомогательный клапан закрытым"]},
    "isolate_power_first": {"en": ["isolate power", "disconnect power"], "ru": ["отключить питание", "изолировать питание"]},
    "remote_only": {"en": ["remote controls only", "only remotely"], "ru": ["только удалённо", "дистанционно"]},
    "stop_and_measure": {"en": ["measure pressure first", "first measure pressure"], "ru": ["сначала измерить давление", "измерить давление перед"]},
}

CONDITIONS = ("question_alone", "actual_pair", "cause_only", "safety_only", "oracle_pair")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model(model_path: Path, adapter_path: Path | None):
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True)
    if adapter_path is not None:
        model = PeftModel.from_pretrained(model, adapter_path, local_files_only=True)
    model.eval()
    return model


def answer_batches(model, tokenizer, prompts: list[str], max_new_tokens: int, batch_size: int, label: str) -> list[str]:
    tokenizer.padding_side = "left"
    answers = []
    for start in range(0, len(prompts), batch_size):
        batch = [f"### Task\n{prompt}\n\n### Answer\n" for prompt in prompts[start : start + batch_size]]
        encoded = tokenizer(batch, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            generated = model.generate(**encoded, do_sample=False, max_new_tokens=max_new_tokens, eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id)
        width = encoded["input_ids"].shape[1]
        answers.extend(tokenizer.decode(row[width:], skip_special_tokens=True).strip() for row in generated)
        print(json.dumps({"condition": label, "answered": min(start + batch_size, len(prompts)), "total": len(prompts)}), flush=True)
    return answers


def source_prompt(question: dict, cause_capsule: str | None, safety_capsule: str | None) -> str:
    cause = cause_capsule if cause_capsule is not None else "MISSING"
    safety = safety_capsule if safety_capsule is not None else "MISSING"
    if question["language"] == "en":
        return (
            "You are SOURCE-I. Answer the person in one short natural sentence. "
            "Use only the two capsules as knowledge. Convert code labels into normal words. "
            "Do not show JSON, code labels, or field names. If either capsule is missing or invalid, "
            "say that you cannot complete the answer.\n\n"
            f"Question: {question['question']}\nCAUSE-I capsule: {cause}\nSAFETY-I capsule: {safety}"
        )
    return (
        "Вы — SOURCE-I. Ответьте человеку одним коротким естественным предложением. "
        "Используйте как знания только две капсулы. Переведите кодовые метки в обычные слова. "
        "Не показывайте JSON, кодовые метки и названия полей. Если одной капсулы нет или она неверна, "
        "скажите, что полный ответ составить нельзя.\n\n"
        f"Вопрос: {question['question']}\nКапсула CAUSE-I: {cause}\nКапсула SAFETY-I: {safety}"
    )


def question_only_prompt(question: dict) -> str:
    if question["language"] == "en":
        return f"Answer naturally. State the exact cause and the safe restriction.\n\n{question['question']}"
    return f"Ответьте естественно. Назовите точную причину и безопасное ограничение.\n\n{question['question']}"


def contains_any(text: str, phrases: list[str]) -> bool:
    lower = text.lower()
    return any(phrase.lower() in lower for phrase in phrases)


def score(output: str, question: dict) -> dict:
    language = question["language"]
    cause_label = question["expected_cause_capsule"]["cause"]
    safety_label = question["expected_safety_capsule"]["restriction"]
    cause_kept = contains_any(output, CAUSE_PHRASES[cause_label][language])
    safety_kept = contains_any(output, SAFETY_PHRASES[safety_label][language])
    forbidden = ["{", "}", '"cause"', '"restriction"', cause_label, safety_label]
    natural_no_json = not any(token.lower() in output.lower() for token in forbidden)
    return {"cause_kept": cause_kept, "safety_kept": safety_kept, "complete": cause_kept and safety_kept, "natural_no_json": natural_no_json}


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    if exam.get("status") != "locked_not_run" or len(exam.get("questions", [])) != 24:
        raise ValueError("expected locked Gate 5A.2 exam")
    questions = exam["questions"]
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    started = time.monotonic()
    cause_model = load_model(args.model, args.cause_adapter)
    cause_raw = answer_batches(cause_model, tokenizer, [row["cause_prompt"] for row in questions], args.capsule_tokens, args.batch_size, "CAUSE-I capsules")
    del cause_model
    safety_model = load_model(args.model, args.safety_adapter)
    safety_raw = answer_batches(safety_model, tokenizer, [row["safety_prompt"] for row in questions], args.capsule_tokens, args.batch_size, "SAFETY-I capsules")
    del safety_model
    source_model = load_model(args.model, None)
    prompts = {
        "question_alone": [question_only_prompt(row) for row in questions],
        "actual_pair": [source_prompt(row, cause_raw[index], safety_raw[index]) for index, row in enumerate(questions)],
        "cause_only": [source_prompt(row, cause_raw[index], None) for index, row in enumerate(questions)],
        "safety_only": [source_prompt(row, None, safety_raw[index]) for index, row in enumerate(questions)],
        "oracle_pair": [source_prompt(row, json.dumps(row["expected_cause_capsule"], separators=(",", ":")), json.dumps(row["expected_safety_capsule"], separators=(",", ":"))) for row in questions],
    }
    outputs = {condition: answer_batches(source_model, tokenizer, prompts[condition], args.answer_tokens, args.batch_size, condition) for condition in CONDITIONS}
    del source_model
    rows = []
    for index, question in enumerate(questions):
        conditions = {}
        for condition in CONDITIONS:
            output = outputs[condition][index]
            conditions[condition] = {"output": output, **score(output, question)}
        rows.append({**question, "actual_cause_capsule_raw": cause_raw[index], "actual_safety_capsule_raw": safety_raw[index], "conditions": conditions})
    summary = {
        condition: {
            "complete": sum(row["conditions"][condition]["complete"] for row in rows),
            "natural_no_json": sum(row["conditions"][condition]["natural_no_json"] for row in rows),
            "cause_kept": sum(row["conditions"][condition]["cause_kept"] for row in rows),
            "safety_kept": sum(row["conditions"][condition]["safety_kept"] for row in rows),
        }
        for condition in CONDITIONS
    }
    best_incomplete = max(summary["question_alone"]["complete"], summary["cause_only"]["complete"], summary["safety_only"]["complete"])
    gates = {
        "actual_pair_complete_at_least_20": summary["actual_pair"]["complete"] >= 20,
        "actual_pair_natural_no_json_at_least_20": summary["actual_pair"]["natural_no_json"] >= 20,
        "question_alone_complete_at_most_8": summary["question_alone"]["complete"] <= 8,
        "cause_only_complete_at_most_8": summary["cause_only"]["complete"] <= 8,
        "safety_only_complete_at_most_8": summary["safety_only"]["complete"] <= 8,
        "actual_pair_lead_at_least_10": summary["actual_pair"]["complete"] - best_incomplete >= 10,
        "oracle_complete_at_least_20": summary["oracle_pair"]["complete"] >= 20,
    }
    result = {
        "experiment_id": "E005",
        "gate": "5A.2",
        "kind": "raw_locked_human_synthesis_result",
        "status": "complete_preliminary_review",
        "exam_content_sha256": exam["content_sha256"],
        "exam_file_sha256": sha256_file(args.exam),
        "base_file_sha256": sha256_file(args.model / "model.safetensors"),
        "adapter_file_sha256": {"cause": sha256_file(args.cause_adapter / "adapter_model.safetensors"), "safety": sha256_file(args.safety_adapter / "adapter_model.safetensors")},
        "conditions": list(CONDITIONS),
        "summary": summary,
        "gates": gates,
        "passed": all(gates.values()),
        "generation": {"do_sample": False, "capsule_tokens": args.capsule_tokens, "answer_tokens": args.answer_tokens, "batch_size": args.batch_size, "training_performed": False, "rag_used": False, "internet_used": False},
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "gates": gates, "passed": result["passed"], "elapsed_seconds": result["elapsed_seconds"]}), flush=True)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--exam", required=True, type=Path)
    parser.add_argument("--cause-adapter", required=True, type=Path)
    parser.add_argument("--safety-adapter", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--capsule-tokens", type=int, default=32)
    parser.add_argument("--answer-tokens", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
