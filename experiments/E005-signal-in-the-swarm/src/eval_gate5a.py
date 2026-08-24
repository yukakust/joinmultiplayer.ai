from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


CAUSE_TEXT = {
    "phase_drift": {"en": "phase drift", "ru": "сдвиг фазы"},
    "thermal_rebound": {"en": "thermal rebound", "ru": "тепловой отскок"},
    "coolant_echo": {"en": "coolant echo", "ru": "эхо охлаждения"},
    "timing_split": {"en": "timing split", "ru": "рассинхронизация времени"},
}

SAFETY_TEXT = {
    "keep_aux_vent_closed": {"en": "keep the auxiliary vent closed", "ru": "не открывать вспомогательный клапан"},
    "isolate_power_first": {"en": "isolate power before adjustment", "ru": "отключить питание до настройки"},
    "remote_only": {"en": "use remote controls only", "ru": "работать только удалённо"},
    "stop_and_measure": {"en": "stop and measure pressure first", "ru": "остановиться и сначала измерить давление"},
}

CONDITIONS = (
    "frozen_base_direct",
    "cause_i_direct",
    "safety_i_direct",
    "frozen_base_pair",
    "wrong_cause_pair",
    "wrong_safety_pair",
    "correct_pair",
    "oracle_pair",
)


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


def answer_batches(model, tokenizer, prompts: list[str], max_new_tokens: int, batch_size: int) -> list[str]:
    outputs = []
    tokenizer.padding_side = "left"
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        prefixed = [f"### Task\n{prompt}\n\n### Answer\n" for prompt in batch]
        encoded = tokenizer(prefixed, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            generated = model.generate(**encoded, do_sample=False, max_new_tokens=max_new_tokens, eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id)
        input_width = encoded["input_ids"].shape[1]
        outputs.extend(tokenizer.decode(row[input_width:], skip_special_tokens=True).strip() for row in generated)
        print(json.dumps({"answered": min(start + batch_size, len(prompts)), "total": len(prompts)}), flush=True)
    return outputs


def parse_capsule(raw: str, key: str, allowed: set[str]) -> dict | None:
    match = re.search(r"\{[^{}]*\}", raw)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if set(value) != {key} or value[key] not in allowed:
        return None
    return value


def complete_from_capsules(cause: dict | None, safety: dict | None, language: str) -> str:
    if not cause or not safety:
        return "INCOMPLETE" if language == "en" else "НЕПОЛНЫЙ ОТВЕТ"
    cause_text = CAUSE_TEXT[cause["cause"]][language]
    safety_text = SAFETY_TEXT[safety["restriction"]][language]
    return f"The cause is {cause_text}; {safety_text}." if language == "en" else f"Причина — {cause_text}; нужно {safety_text}."


def score_direct(raw: str, expected_cause: str, expected_safety: str, language: str) -> bool:
    lower = raw.lower()
    return CAUSE_TEXT[expected_cause][language].lower() in lower and SAFETY_TEXT[expected_safety][language].lower() in lower


def direct_prompt(question: dict) -> str:
    if question["language"] == "en":
        return f"Answer the whole incident. State both the exact cause and the safe restriction.\n\n{question['question']}"
    return f"Ответьте на весь вопрос. Назовите и точную причину, и безопасное ограничение.\n\n{question['question']}"


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    exam = json.loads(args.exam.read_text(encoding="utf-8"))
    if exam.get("status") != "locked_not_run" or len(exam.get("questions", [])) != 24:
        raise ValueError("expected the frozen 24-question Gate 5A exam")
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    questions = exam["questions"]
    prompts = {
        "direct": [direct_prompt(row) for row in questions],
        "cause": [row["cause_prompt"] for row in questions],
        "safety": [row["safety_prompt"] for row in questions],
    }
    raw = {}
    started = time.monotonic()
    for name, adapter in (("base", None), ("cause_i", args.cause_adapter), ("safety_i", args.safety_adapter)):
        model = load_model(args.model, adapter)
        raw[name] = {}
        for prompt_kind in ("direct", "cause", "safety"):
            raw[name][prompt_kind] = answer_batches(model, tokenizer, prompts[prompt_kind], args.max_new_tokens, args.batch_size)
        del model
    rows = []
    for index, question in enumerate(questions):
        language = question["language"]
        expected_cause = question["expected_cause_capsule"]["cause"]
        expected_safety = question["expected_safety_capsule"]["restriction"]
        capsules = {}
        for model_name in ("base", "cause_i", "safety_i"):
            capsules[model_name] = {
                "cause": parse_capsule(raw[model_name]["cause"][index], "cause", set(CAUSE_TEXT)),
                "safety": parse_capsule(raw[model_name]["safety"][index], "restriction", set(SAFETY_TEXT)),
            }
        pairs = {
            "frozen_base_pair": (capsules["base"]["cause"], capsules["base"]["safety"]),
            "wrong_cause_pair": (capsules["cause_i"]["cause"], capsules["cause_i"]["safety"]),
            "wrong_safety_pair": (capsules["safety_i"]["cause"], capsules["safety_i"]["safety"]),
            "correct_pair": (capsules["cause_i"]["cause"], capsules["safety_i"]["safety"]),
            "oracle_pair": (question["expected_cause_capsule"], question["expected_safety_capsule"]),
        }
        conditions = {}
        for condition, model_name in (("frozen_base_direct", "base"), ("cause_i_direct", "cause_i"), ("safety_i_direct", "safety_i")):
            output = raw[model_name]["direct"][index]
            conditions[condition] = {"raw_output": output, "complete": score_direct(output, expected_cause, expected_safety, language)}
        for condition, (cause, safety) in pairs.items():
            conditions[condition] = {
                "cause_capsule": cause,
                "safety_capsule": safety,
                "cause_raw": question["expected_cause_capsule"] if condition == "oracle_pair" else raw[{"frozen_base_pair": "base", "wrong_cause_pair": "cause_i", "wrong_safety_pair": "safety_i", "correct_pair": "cause_i"}[condition]]["cause"][index],
                "safety_raw": question["expected_safety_capsule"] if condition == "oracle_pair" else raw[{"frozen_base_pair": "base", "wrong_cause_pair": "cause_i", "wrong_safety_pair": "safety_i", "correct_pair": "safety_i"}[condition]]["safety"][index],
                "complete_answer": complete_from_capsules(cause, safety, language),
                "complete": bool(cause and safety and cause["cause"] == expected_cause and safety["restriction"] == expected_safety),
            }
        rows.append({**question, "conditions": conditions})
    summary = {condition: sum(row["conditions"][condition]["complete"] for row in rows) for condition in CONDITIONS}
    best_non_oracle = max(summary[condition] for condition in CONDITIONS if condition not in {"correct_pair", "oracle_pair"})
    gates = {
        "correct_pair_at_least_20": summary["correct_pair"] >= 20,
        "each_direct_single_at_most_8": max(summary["cause_i_direct"], summary["safety_i_direct"]) <= 8,
        "wrong_pairs_at_most_8": max(summary["wrong_cause_pair"], summary["wrong_safety_pair"]) <= 8,
        "lead_over_best_non_oracle_at_least_10": summary["correct_pair"] - best_non_oracle >= 10,
        "remove_cause_costs_at_least_10": summary["correct_pair"] - summary["safety_i_direct"] >= 10,
        "remove_safety_costs_at_least_10": summary["correct_pair"] - summary["cause_i_direct"] >= 10,
    }
    result = {
        "experiment_id": "E005",
        "gate": "5A",
        "kind": "raw_locked_composition_result",
        "status": "complete_preliminary_review",
        "exam_content_sha256": exam["content_sha256"],
        "exam_file_sha256": sha256_file(args.exam),
        "base_file_sha256": sha256_file(args.model / "model.safetensors"),
        "adapter_file_sha256": {"cause": sha256_file(args.cause_adapter / "adapter_model.safetensors"), "safety": sha256_file(args.safety_adapter / "adapter_model.safetensors")},
        "conditions": list(CONDITIONS),
        "summary": summary,
        "gates": gates,
        "passed": all(gates.values()),
        "generation": {"do_sample": False, "max_new_tokens": args.max_new_tokens, "batch_size": args.batch_size, "training_performed": False, "rag_used": False, "internet_used": False},
        "merger": "deterministic two-capsule renderer; no learned or latent merge",
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
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
