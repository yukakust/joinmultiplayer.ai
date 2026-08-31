#!/usr/bin/env python3
"""Run Gate 16D.10 Qwen review of DeBERTa-neutral exact-quote claims."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["supported", "not_supported"]},
        "reason": {"type": "string"},
    },
    "required": ["decision", "reason"],
    "additionalProperties": False,
}


def judge(endpoint: str, model: str, quote: str, claim: str) -> dict:
    prompt = (
        "You are checking whether one claim is supported by one source quote.\n\n"
        f"SOURCE QUOTE:\n{quote}\n\nCLAIM:\n{claim}\n\n"
        "Choose supported only when every important part of the claim follows from the quote alone. "
        "Choose not_supported if the quote is only about a similar topic, is weaker, describes a future intention, "
        "misses an important qualifier, or the claim adds a causal link. Do not use outside knowledge."
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Judge one source quote and one claim. Return the required JSON only."},
            {"role": "user", "content": "/no_think\n\n" + prompt},
        ],
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0,
        "max_tokens": 160,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "support_decision", "strict": True, "schema": DECISION_SCHEMA},
        },
    }
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=1800) as response:
        result = json.load(response)
    message = result["choices"][0]["message"]
    row = {
        "seconds": round(time.monotonic() - started, 3),
        "usage": result.get("usage", {}),
        "raw_message": message,
    }
    try:
        parsed = json.loads(message.get("content") or "")
        if parsed.get("decision") not in {"supported", "not_supported"}:
            raise ValueError("invalid decision")
        if not isinstance(parsed.get("reason"), str) or not parsed["reason"].strip():
            raise ValueError("missing reason")
        row.update(receipt="DECISION", decision=parsed["decision"], reason=parsed["reason"].strip())
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        row.update(receipt="ERROR", decision=None, reason=None, error=str(error))
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-result", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:22118")
    parser.add_argument("--model", default="qwen3-8b-q4-k-m")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")

    source = json.loads(args.source_result.read_text())
    protocol = json.loads(args.protocol.read_text())
    cases = []
    for source_row in source["rows"]:
        for claim in source_row["claims"]:
            if claim.get("exact_quote") and claim.get("nli_decision") == "neutral":
                cases.append(
                    {
                        "id": f'{source_row["id"]}-{claim["id"]}',
                        "question_id": source_row["question_id"],
                        "condition": source_row["condition"],
                        "quote": claim["quote"],
                        "claim": claim["claim"],
                        "human_grounded": claim["human_grounded"],
                    }
                )
    frozen = protocol["frozen_cases"]
    if len(cases) != frozen["total"]:
        raise RuntimeError(f'Expected {frozen["total"]} cases, found {len(cases)}')
    if sum(case["human_grounded"] for case in cases) != frozen["human_grounded"]:
        raise RuntimeError("Human-grounded count changed")

    rows = []
    for case in cases:
        result = judge(args.endpoint, args.model, case["quote"], case["claim"])
        accepted = result["decision"] == "supported"
        row = {**case, **result, "accepted": accepted, "correct": accepted == case["human_grounded"]}
        rows.append(row)
        print(json.dumps({"id": row["id"], "decision": row["decision"], "grounded": row["human_grounded"], "correct": row["correct"]}), flush=True)

    summary = {
        "valid_decisions": sum(row["receipt"] == "DECISION" for row in rows),
        "grounded_claims": sum(row["human_grounded"] for row in rows),
        "grounded_claims_recovered": sum(row["human_grounded"] and row["accepted"] for row in rows),
        "unsupported_claims": sum(not row["human_grounded"] for row in rows),
        "unsupported_claims_accepted": sum(not row["human_grounded"] and row["accepted"] for row in rows),
        "correct_decisions": sum(row["correct"] for row in rows),
    }
    success = (
        summary["valid_decisions"] == 23
        and summary["grounded_claims_recovered"] >= 18
        and summary["unsupported_claims_accepted"] == 0
    )
    output = {
        "schema_version": "0.1-private",
        "experiment": "E007",
        "gate": "16D.10",
        "status": "completed_passed_post_hoc" if success else "completed_failed",
        "protocol": protocol,
        "summary": summary,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
