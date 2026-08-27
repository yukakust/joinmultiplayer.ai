#!/usr/bin/env python3
"""Run frozen E007 Gate 3C.6C with Qwen3-0.6B."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/two-link-semantic-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/two-link-semantic-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/two-link-semantic-result-v0.1.json"
MODEL_PATH = Path("/home/yuka/models/e005/qwen3-0.6b-instruct-c1899de")
MODEL_FILE = MODEL_PATH / "model.safetensors"
CHOICES = {"A": "yes", "B": "no", "C": "not_sure"}


SYSTEM = (
    "You are one small verification module. Use only the text supplied. "
    "Choose exactly one letter: A, B, or C. A means YES. B means NO. "
    "C means NOT SURE. Do not answer the user's question and do not add outside knowledge."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prompt_for(case: dict, link: str) -> str:
    shared = (
        f"USER QUESTION:\n{case['question']}\n\n"
        f"PROPOSED ANSWER:\n{case['claim']}\n\n"
    )
    if link == "quote_to_claim":
        return shared + (
            f"EXACT SOURCE QUOTE:\n{case['exact_quote']}\n\n"
            "Does the exact source quote support the proposed answer in the context of the user question?\n"
            "A = YES: the quote itself gives enough support.\n"
            "B = NO: the quote conflicts with the answer or does not support it.\n"
            "C = NOT SURE: the supplied words remain genuinely ambiguous.\n"
            "Return one letter only."
        )
    if link == "claim_to_question":
        return shared + (
            "If the proposed answer were true, would it give information that helps answer the user question?\n"
            "A = YES: it gives all or a useful part of the requested information.\n"
            "B = NO: it does not help answer what was asked.\n"
            "C = NOT SURE: the relationship remains genuinely ambiguous.\n"
            "Return one letter only."
        )
    raise ValueError(f"unknown link: {link}")


def combine(first: str, second: str) -> str:
    if "no" in (first, second):
        return "drop"
    if first == second == "yes":
        return "take"
    return "not_sure"


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        local_files_only=True,
        dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()
    return model, tokenizer


def classify(model, tokenizer, items: list[tuple[str, str]], batch_size: int) -> dict[tuple[str, str], dict]:
    choice_ids = {}
    for letter in CHOICES:
        ids = tokenizer.encode(letter, add_special_tokens=False)
        if len(ids) != 1:
            raise RuntimeError(f"choice {letter} is not one token: {ids}")
        choice_ids[letter] = ids[0]

    results = {}
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        rendered = [tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        ) for _, text in batch]
        encoded = tokenizer(rendered, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            logits = model(**encoded).logits[:, -1, :]
            full_probabilities = torch.softmax(logits, dim=-1)
            selected_logits = logits[:, [choice_ids[letter] for letter in CHOICES]]
            selected_probabilities = torch.softmax(selected_logits, dim=-1)
        for row, ((key, _), selected, full, raw_logits) in enumerate(zip(batch, selected_probabilities, full_probabilities, selected_logits)):
            del row
            letter_index = int(torch.argmax(selected).item())
            letter = tuple(CHOICES)[letter_index]
            sorted_logits = torch.sort(raw_logits, descending=True).values
            choice_mass = sum(float(full[choice_ids[item]].item()) for item in CHOICES)
            results[key] = {
                "letter": letter,
                "decision": CHOICES[letter],
                "scores_among_choices": {
                    item: round(float(selected[index].item()), 8)
                    for index, item in enumerate(CHOICES)
                },
                "choice_mass_in_full_vocabulary": round(choice_mass, 8),
                "top_two_logit_margin": round(float((sorted_logits[0] - sorted_logits[1]).item()), 8),
            }
        print(json.dumps({"classified": min(start + batch_size, len(items)), "total": len(items)}), flush=True)
    return results


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6C inputs are not frozen")

    torch.set_num_threads(threads)
    model, tokenizer = load_model()
    items = []
    for case in world["cases"]:
        for link in ("quote_to_claim", "claim_to_question"):
            items.append(((case["id"], link), prompt_for(case, link)))

    started = time.monotonic()
    judgments = classify(model, tokenizer, items, batch_size)
    records = []
    for case in world["cases"]:
        support = judgments[(case["id"], "quote_to_claim")]
        helpful = judgments[(case["id"], "claim_to_question")]
        actual_final = combine(support["decision"], helpful["decision"])
        expected = case["expected"]
        records.append({
            **case,
            "actual": {
                "quote_to_claim": support,
                "claim_to_question": helpful,
                "final": actual_final,
            },
            "correct": {
                "quote_to_claim": support["decision"] == expected["quote_supports_claim"],
                "claim_to_question": helpful["decision"] == expected["claim_helps_question"],
                "final": actual_final == expected["expected_final"],
            },
        })

    summary = {
        "quote_to_claim_correct": sum(record["correct"]["quote_to_claim"] for record in records),
        "claim_to_question_correct": sum(record["correct"]["claim_to_question"] for record in records),
        "final_correct": sum(record["correct"]["final"] for record in records),
        "useful_taken": sum(record["expected"]["expected_final"] == "take" and record["actual"]["final"] == "take" for record in records),
        "useful_total": sum(record["expected"]["expected_final"] == "take" for record in records),
        "unsafe_false_takes": sum(record["expected"]["expected_final"] != "take" and record["actual"]["final"] == "take" for record in records),
        "non_useful_total": sum(record["expected"]["expected_final"] != "take" for record in records),
        "not_sure_final": sum(record["actual"]["final"] == "not_sure" for record in records),
        "total": len(records),
    }
    quadrant_summary = {}
    for quadrant in ("yy", "ny", "yn", "nn"):
        selected = [record for record in records if record["quadrant"] == quadrant]
        quadrant_summary[quadrant] = {
            "final_correct": sum(record["correct"]["final"] for record in selected),
            "taken": sum(record["actual"]["final"] == "take" for record in selected),
            "not_sure": sum(record["actual"]["final"] == "not_sure" for record in selected),
            "dropped": sum(record["actual"]["final"] == "drop" for record in selected),
            "total": len(selected),
        }
    gate = protocol["locked_success"]
    passed = (
        summary["quote_to_claim_correct"] >= gate["quote_to_claim_correct_min"]
        and summary["claim_to_question_correct"] >= gate["claim_to_question_correct_min"]
        and summary["useful_taken"] >= gate["useful_taken_min"]
        and summary["unsafe_false_takes"] <= gate["unsafe_false_takes_max"]
    )
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6C",
        "status": "locked_development_run_complete",
        "protocol": "/experiments/E007/two-link-semantic-protocol-v0.1.json",
        "world": "/experiments/E007/two-link-semantic-world-v0.1.json",
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "world_sha256": sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": sha256_file(MODEL_FILE),
            "weights_changed": false,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "quadrants": quadrant_summary,
        "passed_locked_gate": passed,
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.batch_size, args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed_locked_gate"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
