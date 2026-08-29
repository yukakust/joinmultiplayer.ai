#!/usr/bin/env python3
"""Run E007 Gate 14A: closed-world answer synthesis."""

from __future__ import annotations

import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
WORLD_PATH = ROOT / "site/experiments/E007/answer-synthesis-world-v0.1.json"
PROTOCOL_PATH = ROOT / "site/experiments/E007/answer-synthesis-protocol-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/answer-synthesis-result-v0.1.json"
DEBERTA_REPOSITORY = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
DEBERTA_REVISION = "6f5cf0a2b59cabb106aca4c287eed12e357e90eb"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def make_user_prompt(case: dict) -> str:
    piles = []
    for pile in case["piles"]:
        claims = "\n".join(f"- {claim}" for claim in pile["claims"])
        piles.append(f"{pile['pile_id']}:\n{claims}")
    return f"QUESTION:\n{case['question']}\n\nACCEPTED PILES:\n" + "\n\n".join(piles) + "\n\nFINAL ANSWER:"


def score_nli(model, tokenizer, premise: str, hypothesis: str) -> dict:
    encoded = tokenizer(premise, hypothesis, truncation=True, return_tensors="pt")
    with torch.inference_mode():
        probabilities = torch.softmax(model(**encoded).logits, dim=-1)[0]
    scores = {
        model.config.id2label[index].lower(): round(float(score), 8)
        for index, score in enumerate(probabilities)
    }
    return {
        "decision": max(scores, key=scores.get),
        "probabilities": scores,
        "input_tokens": int(encoded["attention_mask"].sum()),
    }


def generate_nonempty(model, tokenizer, cases: list[dict], spec: dict, batch_size: int = 4) -> list[dict]:
    rendered = []
    for case in cases:
        user_prompt = make_user_prompt(case)
        chat = tokenizer.apply_chat_template(
            [{"role": "system", "content": spec["system"]}, {"role": "user", "content": user_prompt}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        rendered.append((case, user_prompt, chat))

    records = []
    for start in range(0, len(rendered), batch_size):
        batch = rendered[start : start + batch_size]
        encoded = tokenizer([item[2] for item in batch], padding=True, return_tensors="pt")
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            outputs = model.generate(
                **encoded,
                do_sample=False,
                max_new_tokens=spec["max_new_tokens"],
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
            )
        for item, output in zip(batch, outputs):
            generated = output[input_length:]
            text = tokenizer.decode(generated, skip_special_tokens=True).strip()
            records.append({
                "id": item[0]["id"],
                "question": item[0]["question"],
                "piles": item[0]["piles"],
                "user_prompt": item[1],
                "answer": text,
                "path": "qwen_generation",
                "generated_tokens": int(len(generated)),
                "hit_token_limit": len(generated) >= spec["max_new_tokens"] and tokenizer.eos_token_id not in generated.tolist(),
            })
    return records


def main() -> None:
    if RESULT_PATH.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {RESULT_PATH}")
    world, protocol = read(WORLD_PATH), read(PROTOCOL_PATH)
    if digest(WORLD_PATH) != protocol["source"]["sha256"]:
        raise RuntimeError("Frozen Gate 14A world changed")
    started = time.perf_counter()

    spec = protocol["model"]
    tokenizer = AutoTokenizer.from_pretrained(
        spec["repository"], revision=spec["revision"], local_files_only=True
    )
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        spec["repository"], revision=spec["revision"], local_files_only=True, dtype=torch.bfloat16
    ).eval()
    nonempty = [case for case in world["cases"] if case["piles"]]
    generated = generate_nonempty(model, tokenizer, nonempty, spec)
    del model

    by_id = {record["id"]: record for record in generated}
    for case in world["cases"]:
        if not case["piles"]:
            by_id[case["id"]] = {
                "id": case["id"],
                "question": case["question"],
                "piles": [],
                "user_prompt": None,
                "answer": world["canned_empty_response"],
                "path": "deterministic_empty_response",
                "generated_tokens": 0,
                "hit_token_limit": False,
            }

    dtokenizer = AutoTokenizer.from_pretrained(
        DEBERTA_REPOSITORY, revision=DEBERTA_REVISION, local_files_only=True
    )
    dmodel = AutoModelForSequenceClassification.from_pretrained(
        DEBERTA_REPOSITORY, revision=DEBERTA_REVISION, local_files_only=True, dtype=torch.float32
    ).eval()
    for case in world["cases"]:
        record = by_id[case["id"]]
        if not case["piles"]:
            record["diagnostics"] = {"exact_canned_response": record["answer"] == world["canned_empty_response"]}
            continue
        claims = [claim for pile in case["piles"] for claim in pile["claims"]]
        joined = "\n".join(f"- {claim}" for claim in claims)
        record["diagnostics"] = {
            "all_claims_to_answer": score_nli(dmodel, dtokenizer, joined, record["answer"]),
            "answer_to_each_claim": [
                {"claim": claim, **score_nli(dmodel, dtokenizer, record["answer"], claim)}
                for claim in claims
            ],
        }

    ordered = [by_id[case["id"]] for case in world["cases"]]
    result = {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "gate": "14A",
        "kind": "locked_synthetic_english_development",
        "git_revision": git_revision(),
        "protocol_sha256": digest(PROTOCOL_PATH),
        "world_sha256": digest(WORLD_PATH),
        "model": {"repository": spec["repository"], "revision": spec["revision"]},
        "diagnostic_model": {"repository": DEBERTA_REPOSITORY, "revision": DEBERTA_REVISION},
        "records": ordered,
        "mechanical_summary": {
            "cases": len(ordered),
            "nonempty_answers": sum(bool(record["answer"]) for record in ordered if record["piles"]),
            "nonempty_total": len(nonempty),
            "exact_empty_answers": sum(record["diagnostics"].get("exact_canned_response", False) for record in ordered),
            "empty_total": len(ordered) - len(nonempty),
            "token_limit_hits": sum(record["hit_token_limit"] for record in ordered),
            "manual_gate_pending": True,
        },
        "runtime": {
            "seconds": round(time.perf_counter() - started, 3),
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["mechanical_summary"], indent=2))


if __name__ == "__main__":
    main()
