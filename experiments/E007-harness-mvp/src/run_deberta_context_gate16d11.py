#!/usr/bin/env python3
"""Run Gate 16D.11 quote-only versus source-window DeBERTa NLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def centered_window(tokenizer, source: str, quote: str, claim: str, maximum: int = 512) -> tuple[str, int]:
    quote_start = source.find(quote)
    if quote_start < 0:
        raise ValueError("exact quote missing from source message")
    quote_end = quote_start + len(quote)
    tokens = tokenizer(source, add_special_tokens=False, return_offsets_mapping=True)
    offsets = tokens["offset_mapping"]
    ids = tokens["input_ids"]
    quote_tokens = [i for i, (start, end) in enumerate(offsets) if end > quote_start and start < quote_end]
    if not quote_tokens:
        raise ValueError("quote has no source tokens")
    claim_tokens = len(tokenizer(claim, add_special_tokens=False)["input_ids"])
    budget = maximum - claim_tokens - tokenizer.num_special_tokens_to_add(pair=True)
    if budget < len(quote_tokens):
        raise ValueError("quote and claim do not fit the model")
    budget = min(budget, len(ids))
    first_quote, last_quote = quote_tokens[0], quote_tokens[-1]
    spare = budget - (last_quote - first_quote + 1)
    left = min(first_quote, spare // 2)
    start_token = first_quote - left
    end_token = min(len(ids), start_token + budget)
    start_token = max(0, end_token - budget)
    char_start = offsets[start_token][0]
    char_end = offsets[end_token - 1][1]
    window = source[char_start:char_end]
    if quote not in window:
        raise RuntimeError("centered window lost exact quote")
    return window, budget


def classify(tokenizer, model, premise: str, claim: str) -> dict:
    import torch

    encoded = tokenizer(premise, claim, return_tensors="pt", truncation="only_first", max_length=512)
    with torch.inference_mode():
        probabilities = torch.softmax(model(**encoded).logits[0], dim=-1)
    scores = {model.config.id2label[i].lower(): round(float(value), 8) for i, value in enumerate(probabilities)}
    return {
        "decision": max(scores, key=scores.get),
        "probabilities": scores,
        "input_tokens": int(encoded["input_ids"].shape[-1]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-source", type=Path, required=True)
    parser.add_argument("--reviewed-source", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")

    private = json.loads(args.private_source.read_text())
    reviewed = json.loads(args.reviewed_source.read_text())
    protocol = json.loads(args.protocol.read_text())
    reviewed_rows = {row["id"]: row for row in reviewed["rows"]}

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    spec = protocol["judge"]
    tokenizer = AutoTokenizer.from_pretrained(spec["repository"], revision=spec["revision"], local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        spec["repository"], revision=spec["revision"], local_files_only=True, dtype=torch.float32
    ).eval()

    rows = []
    for source_row in private["rows"]:
        reviewed_claims = {claim["id"]: claim for claim in reviewed_rows[source_row["id"]]["claims"]}
        for claim in source_row["claims"]:
            reviewed_claim = reviewed_claims[claim["id"]]
            if not reviewed_claim.get("exact_quote") or reviewed_claim.get("nli_decision") != "neutral":
                continue
            source = source_row["source_messages"][claim["source_id"]]
            window, premise_budget = centered_window(tokenizer, source, claim["quote"], claim["claim"])
            control = classify(tokenizer, model, claim["quote"], claim["claim"])
            treatment = classify(tokenizer, model, window, claim["claim"])
            row = {
                "id": f'{source_row["id"]}-{claim["id"]}',
                "question_id": source_row["question_id"],
                "language": "ru" if source_row["question_id"] == "Q07" else "en",
                "claim": claim["claim"],
                "quote": claim["quote"],
                "source_message": source,
                "context_window": window,
                "quote_present": claim["quote"] in window,
                "premise_budget": premise_budget,
                "old_full_message_grounded": reviewed_claim["human_grounded"],
                "recorded_control": {
                    "decision": reviewed_claim["nli_decision"],
                    "probabilities": reviewed_claim["nli_probabilities"],
                },
                "recomputed_control": control,
                "treatment": treatment,
            }
            rows.append(row)
            print(json.dumps({"id": row["id"], "control": control["decision"], "context": treatment["decision"], "tokens": treatment["input_tokens"]}), flush=True)

    if len(rows) != protocol["frozen_cases"]["total"]:
        raise RuntimeError(f'Expected {protocol["frozen_cases"]["total"]} cases, found {len(rows)}')
    english = [row for row in rows if row["language"] == "en"]
    english_grounded = [row for row in english if row["old_full_message_grounded"]]
    english_unsupported = [row for row in english if not row["old_full_message_grounded"]]
    summary = {
        "cases": len(rows),
        "quote_present": sum(row["quote_present"] for row in rows),
        "control_reproduced_neutral": sum(row["recomputed_control"]["decision"] == "neutral" for row in rows),
        "context_entailment_all": sum(row["treatment"]["decision"] == "entailment" for row in rows),
        "english_cases": len(english),
        "english_grounded": len(english_grounded),
        "english_grounded_recovered": sum(row["treatment"]["decision"] == "entailment" for row in english_grounded),
        "english_unsupported": len(english_unsupported),
        "english_unsupported_accepted": sum(row["treatment"]["decision"] == "entailment" for row in english_unsupported),
        "russian_diagnostic_cases": sum(row["language"] == "ru" for row in rows),
    }
    passed = (
        summary["cases"] == 23
        and summary["quote_present"] == 23
        and summary["english_grounded_recovered"] >= 16
        and summary["english_unsupported_accepted"] == 0
    )
    result = {
        "schema_version": "0.1-private",
        "experiment": "E007",
        "gate": "16D.11",
        "status": "completed_passed_open_diagnostic" if passed else "completed_failed",
        "protocol": protocol,
        "summary": summary,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
