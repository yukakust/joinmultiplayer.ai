#!/usr/bin/env python3
"""Run the compact E007 Gate 3C.6E two-button test."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/atomic-button-protocol-v0.1.json"
WORLD_PATH = ROOT / "site/experiments/E007/atomic-button-world-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/atomic-button-result-v0.1.json"
MODEL_PATH = Path("/home/yuka/models/e005/qwen3-0.6b-instruct-c1899de")
MODEL_FILE = MODEL_PATH / "model.safetensors"
LINKS = ("source_supports_rule", "facts_support_condition", "answer_follows_consequence")
ACTIONS = ("accept", "reject")


SYSTEM = (
    "You are a tiny evidence gate. You receive one comparison, not the whole problem. "
    "Choose accept only if the first supplied text clearly supports the second. "
    "Choose reject if it conflicts, does not support it, or remains uncertain. "
    "Do not use outside knowledge. Your only possible actions are accept and reject."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prompt_for(case: dict, link: str) -> str:
    if link == "source_supports_rule":
        source = case["source"]
        first_label, first = "SOURCE WINDOW", case["source_window"]
        second_label, second = "PROPOSED RULE", case["proposed_rule"]
        context = f"SOURCE RECORD: {source['title']} · version {source['version']} · {source['date']} · {source['coordinates']}\n\n"
    elif link == "facts_support_condition":
        first_label, first = "CURRENT FACTS", case["current_facts"]
        second_label, second = "RULE CONDITION", case["rule_condition"]
        context = ""
    elif link == "answer_follows_consequence":
        first_label, first = "PROPOSED ANSWER", case["proposed_answer"]
        second_label, second = "RULE CONSEQUENCE", case["rule_consequence"]
        context = ""
    else:
        raise ValueError(f"unknown link: {link}")
    return (
        f"{context}{first_label}:\n{first}\n\n{second_label}:\n{second}\n\n"
        "Which action fits this one comparison? Return accept if the first text clearly supports the second. "
        "Otherwise return reject.\nACTION:"
    )


def combine(decisions: dict[str, str]) -> str:
    return "use" if all(decisions.get(link) == "accept" for link in LINKS) else "do_not_use"


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


def score_buttons(model, tokenizer, items: list[dict], batch_size: int) -> list[dict]:
    action_ids = {}
    for action in ACTIONS:
        token_ids = tokenizer.encode(action, add_special_tokens=False)
        if len(token_ids) != 1:
            raise RuntimeError(f"action {action} is not one token: {token_ids}")
        action_ids[action] = token_ids[0]

    records = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        rendered = [tokenizer.apply_chat_template(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": item["prompt"]}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        ) for item in batch]
        encoded = tokenizer(rendered, return_tensors="pt", padding=True, add_special_tokens=False)
        with torch.inference_mode():
            logits = model(**encoded).logits[:, -1, :]
            selected = logits[:, [action_ids[action] for action in ACTIONS]]
            probabilities = torch.softmax(selected, dim=-1)
        for item, row_logits, row_probabilities in zip(batch, selected, probabilities):
            winner_index = int(torch.argmax(row_logits).item())
            winner = ACTIONS[winner_index]
            records.append({
                **item,
                "decision": winner,
                "scores": {action: round(float(row_probabilities[index].item()), 8) for index, action in enumerate(ACTIONS)},
                "logit_margin": round(float(torch.abs(row_logits[0] - row_logits[1]).item()), 8),
            })
        print(json.dumps({"scored": min(start + batch_size, len(items)), "total": len(items)}), flush=True)
    return records


def run(batch_size: int, threads: int) -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_inference" or world["status"] != "frozen_before_inference":
        raise RuntimeError("Gate 3C.6E inputs are not frozen")

    torch.set_num_threads(threads)
    model, tokenizer = load_model()
    items = [
        {"case_id": case["id"], "link": link, "prompt": prompt_for(case, link)}
        for case in world["cases"] for link in LINKS
    ]
    started = time.monotonic()
    outputs = score_buttons(model, tokenizer, items, batch_size)
    by_key = {(item["case_id"], item["link"]): item for item in outputs}

    records = []
    for case in world["cases"]:
        links = {link: by_key[(case["id"], link)] for link in LINKS}
        final = combine({link: links[link]["decision"] for link in LINKS})
        records.append({
            **case,
            "actual": {"links": links, "final": final},
            "correct": {
                **{link: links[link]["decision"] == case["expected"][link] for link in LINKS},
                "final": final == case["expected"]["final"],
            },
        })

    summary = {
        **{f"{link}_correct": sum(record["correct"][link] for record in records) for link in LINKS},
        "final_correct": sum(record["correct"]["final"] for record in records),
        "useful_packets_used": sum(record["expected"]["final"] == "use" and record["actual"]["final"] == "use" for record in records),
        "useful_packets_total": 3,
        "false_packets_used": sum(record["expected"]["final"] != "use" and record["actual"]["final"] == "use" for record in records),
        "trap_packets_total": 7,
        "total_cases": 10,
        "total_button_decisions": 30,
    }
    gate = protocol["development_signal"]
    passed = (
        all(summary[f"{link}_correct"] >= gate["each_atomic_link_correct_min"] for link in LINKS)
        and summary["useful_packets_used"] >= gate["useful_packets_used_min"]
        and summary["false_packets_used"] <= gate["false_packets_used_max"]
    )
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6E",
        "status": "compact_development_run_complete",
        "protocol": "/experiments/E007/atomic-button-protocol-v0.1.json",
        "world": "/experiments/E007/atomic-button-world-v0.1.json",
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "world_sha256": sha256_file(WORLD_PATH),
        "model": {
            "id": "Qwen/Qwen3-0.6B",
            "snapshot": "c1899de",
            "weights_sha256": sha256_file(MODEL_FILE),
            "weights_changed": False,
        },
        "runtime_seconds": round(time.monotonic() - started, 3),
        "summary": summary,
        "passed_development_signal": passed,
        "records": records,
        "boundary": protocol["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()
    result = run(args.batch_size, args.threads)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed_development_signal"], **result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
