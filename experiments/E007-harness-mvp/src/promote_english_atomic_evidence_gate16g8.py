#!/usr/bin/env python3
"""Promote the safe synthetic Gate 16G.8 result without raw model output."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-result", type=Path, required=True)
    parser.add_argument("--world", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    private_bytes = args.private_result.read_bytes()
    private = json.loads(private_bytes)
    world = json.loads(args.world.read_text(encoding="utf-8"))
    if private.get("status") not in {"completed_passed", "completed_failed"}:
        raise RuntimeError("private run is not complete")
    cases = {case["id"]: case for case in world["cases"]}
    manual_completeness = {
        "EN01-G": (False, "Qwen copied the conditional rule but omitted the message showing that its pressure-and-pulse condition occurred."),
        "EN08-G": (False, "Qwen copied the temperature and conditional rule but omitted the message showing that cold-start frost occurred."),
    }
    rows = []
    for row in private["rows"]:
        case = cases[row["id"]]
        complete, note = manual_completeness.get(
            row["id"], (row["supported"] and row["receipt"] == "EXACT_EVIDENCE", None)
        )
        rows.append({
            "id": row["id"], "supported": row["supported"], "claim": case["claim"],
            "messages": case["messages"], "qwen_receipt": row["receipt"],
            "qwen_spans": row["spans"], "oracle_nli": row["oracle_nli"]["decision"],
            "qwen_nli": (row["qwen_nli"] or {}).get("decision"), "accepted": row["accepted"],
            "manual_span_complete": complete if row["supported"] else None,
            "manual_span_note": note,
        })
    supported_rows = [row for row in rows if row["supported"]]
    public = {
        "schema_version": "0.1-public-synthetic", "experiment": "E007", "gate": "16G.8",
        "status": private["status"], "private_result_sha256": hashlib.sha256(private_bytes).hexdigest(),
        "summary": {
            **private["summary"],
            "manual_qwen_supported_complete": sum(row["manual_span_complete"] is True for row in supported_rows),
            "manual_end_to_end_supported_valid": sum(
                row["manual_span_complete"] is True and row["accepted"] for row in supported_rows
            ),
        }, "rows": rows,
        "manual_review": [
            "Qwen returned exact substrings for all ten supported claims and no malformed outputs, but manual review found complete evidence for only eight.",
            "Qwen also returned exact but contradicting evidence for two unsupported claims; English DeBERTa rejected both.",
            "English DeBERTa rejected three of ten supported oracle evidence bundles: multi-premise lineage composition, conditional numerical reasoning, and negation with only.",
            "The mechanical end-to-end lane accepted seven of ten supported claims and zero of ten unsupported claims; only five accepted supported claims also had manually complete evidence.",
            "The locked development gate failed; this is not production approval."
        ],
        "claim_boundary": "Fresh synthetic locked development result; all cases are public and English-only."
    }
    serialized = json.dumps(public, ensure_ascii=False, indent=2) + "\n"
    for forbidden in ("raw", "/home/", "tool_call", "runtime_seconds"):
        if forbidden in serialized:
            raise RuntimeError(f"private field leaked: {forbidden}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
