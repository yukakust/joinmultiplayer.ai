#!/usr/bin/env python3
"""Private E007 7S.3 replay with sentence-level citable evidence.

Raw memory and per-case outputs must remain outside the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from pocket_i_core.nli import LocalNli

import run_raw_first_private_replay as base


MAX_ALLOWED_PER_SOURCE = 2


def choose_allowed(units: list[dict]) -> list[dict]:
    take = [item for item in units if item["reranker"]["decision"] == "TAKE"]
    return sorted(take, key=lambda item: (-item["reranker"]["score"], item["evidence_id"]))[:MAX_ALLOWED_PER_SOURCE]


def extraction_prompt(question: str, sources: list[dict], allowed: list[dict]) -> str:
    context = "\n\n".join(f"SOURCE {item['source_id']}\n{item['text']}" for item in sources)
    evidence = "\n".join(f"[{item['evidence_id']}] {item['text']}" for item in allowed)
    return (
        f"QUESTION\n{question}\n\nFULL CONTEXT (read for meaning; not citable)\n{context}\n\n"
        f"THE ONLY CITABLE EVIDENCE\n{evidence}\n\n"
        'Return JSON only: {"candidates":[{"claim":"one short claim that directly answers the question","evidence_ids":["S1.2"]}]}. '
        "Use only the allowed evidence IDs. Return at most two claims. Do not include neighboring advice. "
        'If the allowed evidence does not answer the question, return {"candidates":[]}.'
    )


def validate_candidates(raw: str, allowed: list[dict]) -> tuple[list[dict], list[dict]]:
    try:
        payload = base.extract_json(raw)
    except (ValueError, json.JSONDecodeError):
        return [], [{"reason": "invalid_json"}]
    unit_by_id = {item["evidence_id"]: item for item in allowed}
    accepted, rejected = [], []
    for index, item in enumerate(payload.get("candidates", [])[:2], 1):
        claim = str(item.get("claim", "")).strip()
        ids = list(dict.fromkeys(str(value).strip() for value in item.get("evidence_ids", []) if str(value).strip()))
        selected = [unit_by_id.get(value) for value in ids]
        reason = None
        if not claim or len(claim) > 400:
            reason = "invalid_claim"
        elif not 1 <= len(ids) <= 2:
            reason = "invalid_evidence_ids"
        elif any(value is None for value in selected):
            reason = "non_allowed_evidence_id"
        if reason:
            rejected.append({"candidate_id": f"E{index}", "claim": claim, "evidence_ids": ids, "reason": reason})
            continue
        accepted.append({
            "candidate_id": f"E{index}",
            "claim": claim,
            "evidence_ids": ids,
            "evidence_blocks": selected,
            "quote": "\n".join(value["text"] for value in selected),
        })
    return accepted, rejected


def run(args: argparse.Namespace) -> dict:
    if args.output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("private output must stay outside the repository")
    if args.output.exists():
        raise ValueError("refusing to overwrite a preserved private result")
    records = base.private_articles(args.input)
    nli = LocalNli(args.nli)
    totals = {
        "cases": len(records), "raw_sources": 0, "sentences": 0, "sentence_take": 0,
        "sentence_not_sure": 0, "sentence_drop": 0, "cases_with_allowed": 0,
        "claims": 0, "grounded": 0, "answered": 0,
    }
    started = time.monotonic()
    for row_number, record in enumerate(records, 1):
        print(f"[{row_number}/8] selecting exact evidence sentences", flush=True)
        sources = [item for item in record["sources"] if item["source_id"] in record["old_grounded_source_ids"]]
        record["sources"] = sources
        totals["raw_sources"] += len(sources)
        scored, allowed = [], []
        for source in sources:
            units = base.evidence_units([source])
            for unit in units:
                score = base.reranker_score(args.reranker, record["question"], unit["text"])
                decision = base.reranker_decision(score)
                unit["reranker"] = {"score": round(score, 8), "decision": decision}
                totals["sentences"] += 1
                totals[f"sentence_{decision.lower()}"] += 1
            scored.extend(units)
            allowed.extend(choose_allowed(units))
        record["scored_sentences"] = scored
        record["allowed_evidence"] = allowed
        if allowed:
            totals["cases_with_allowed"] += 1
        else:
            record.update({"raw_extraction": "", "valid_candidates": [], "rejected_candidates": [], "grounded_claims": [], "final_answer": base.NO_INFORMATION, "terminal": "no_allowed_sentence"})
            continue
        raw = base.qwen(
            args.qwen,
            "Extract only the minimal answer supported by the explicitly allowed exact evidence.",
            extraction_prompt(record["question"], sources, allowed),
            tokens=512,
        )
        accepted, rejected = validate_candidates(raw, allowed)
        record["raw_extraction"] = raw
        record["valid_candidates"] = accepted
        record["rejected_candidates"] = rejected
        totals["claims"] += len(accepted)
        signals = nli([(item["quote"], item["claim"]) for item in accepted]) if accepted else []
        grounded = []
        for item, (label, confidence) in zip(accepted, signals):
            item["deberta"] = {"label": label, "confidence": round(float(confidence), 8)}
            if label == "entailment":
                grounded.append(item)
        record["grounded_claims"] = grounded
        totals["grounded"] += len(grounded)
        if not grounded:
            record.update({"final_answer": base.NO_INFORMATION, "terminal": "no_grounded_claim"})
            continue
        answer = base.qwen(
            args.qwen,
            "Write only the direct answer supported by the accepted evidence shelf.",
            base.writer_prompt(record["question"], grounded),
            tokens=384,
        )
        if not base.valid_final(answer, grounded):
            record.update({"final_answer": base.NO_INFORMATION, "raw_writer_answer": answer, "terminal": "invalid_final_citations"})
            continue
        record.update({"final_answer": answer, "terminal": "answered"})
        totals["answered"] += 1
    result = {
        "schema_version": "e007-minimal-evidence-private-replay-v0.1",
        "warning": "PRIVATE: contains local memory excerpts and model outputs; do not publish",
        "protocol": "minimal-evidence-selection-protocol-v0.1",
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "totals": totals,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.chmod(0o600)
    print(json.dumps({"private_output": str(args.output), "totals": totals}, indent=2), flush=True)
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--input", type=Path, required=True)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--reranker", default="http://127.0.0.1:18084")
    value.add_argument("--qwen", default="http://127.0.0.1:18085")
    value.add_argument("--nli", type=Path, default=Path("desktop/app/nli-current"))
    return value


if __name__ == "__main__":
    run(parser().parse_args())
