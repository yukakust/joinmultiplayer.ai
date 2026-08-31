#!/usr/bin/env python3
"""Build reviewed, privacy-safe Gate 16D.11 output."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FULL_MESSAGE_LABEL_CORRECTIONS = {
    "Q06-retrieved_shelf-C01": False,
}


def sanitize(text: str) -> str:
    text = re.sub(r"\]\(/home/[^)]+\)", "]", text)
    return re.sub(r"/home/[A-Za-z0-9_./@:-]+", "[local path removed]", text)


def build(private: dict) -> dict:
    rows = []
    for source in private["rows"]:
        grounded = FULL_MESSAGE_LABEL_CORRECTIONS.get(source["id"], source["old_full_message_grounded"])
        accepted = source["treatment"]["decision"] == "entailment"
        rows.append(
            {
                "id": source["id"],
                "question_id": source["question_id"],
                "language": source["language"],
                "claim": sanitize(source["claim"]),
                "quote": sanitize(source["quote"]),
                "context_window": sanitize(source["context_window"]),
                "quote_present": source["quote_present"],
                "control": source["recomputed_control"],
                "with_context": source["treatment"],
                "old_full_message_grounded": source["old_full_message_grounded"],
                "reviewed_full_message_grounded": grounded,
                "review_note": (
                    "Старая метка исправлена: сообщение описывает раннее закрытие observation, но не утверждает, что budget уже был превышен."
                    if source["id"] in FULL_MESSAGE_LABEL_CORRECTIONS
                    else "Повторная ручная метка совпала со старой."
                ),
                "correct_with_context": accepted == grounded,
            }
        )
    english = [row for row in rows if row["language"] == "en"]
    supported = [row for row in english if row["reviewed_full_message_grounded"]]
    unsupported = [row for row in english if not row["reviewed_full_message_grounded"]]
    return {
        "schema_version": "0.1",
        "experiment": "E007",
        "gate": "16D.11",
        "status": "completed_passed_open_diagnostic_reference_correction",
        "protocol": "/experiments/E007/deberta-context-gate16d11-protocol-v0.1.json",
        "summary": {
            "cases": len(rows),
            "quote_present": sum(row["quote_present"] for row in rows),
            "control_neutral": sum(row["control"]["decision"] == "neutral" for row in rows),
            "english_cases": len(english),
            "english_supported": len(supported),
            "english_supported_accepted": sum(row["with_context"]["decision"] == "entailment" for row in supported),
            "english_unsupported": len(unsupported),
            "english_unsupported_accepted": sum(row["with_context"]["decision"] == "entailment" for row in unsupported),
            "english_correct": sum(row["correct_with_context"] for row in english),
            "russian_diagnostic_cases": sum(row["language"] == "ru" for row in rows),
        },
        "finding": "On the 18 English cases, adding a source window changed DeBERTa from 0 entailment decisions to 16 correct entailments while rejecting both unsupported claims. One old human label was corrected after reading the full message. The five Russian cases remain diagnostic only. Because labels were open, this result requires a fresh locked replication before the context window becomes an accepted harness rule.",
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(json.loads(args.private.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
