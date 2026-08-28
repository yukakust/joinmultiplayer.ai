#!/usr/bin/env python3
"""Apply two deterministic post-hoc calibrations to E007 mirrored labels."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).parents[3]
INPUT = ROOT / "site/experiments/E007/numeric-letter-result-v0.1.json"
PROTOCOL = ROOT / "site/experiments/E007/mirrored-calibration-protocol-v0.1.json"
OUTPUT = ROOT / "site/experiments/E007/mirrored-calibration-result-v0.1.json"


def log_odds(record: dict) -> float:
    return math.log(record["scores"]["1"] / record["scores"]["A"])


def build() -> dict:
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    by_key = {(record["case_id"], record["deck"]): record for record in source["records"]}
    records = []
    for case_id in sorted({record["case_id"] for record in source["records"]}):
        x, y = by_key[(case_id, "X")], by_key[(case_id, "Y")]
        agreement = x["actual_semantic"] if x["actual_semantic"] == y["actual_semantic"] else "unsure"
        x_margin, y_margin = log_odds(x), log_odds(y)
        calibrated_margin = (x_margin - y_margin) / 2
        calibrated = "approve" if calibrated_margin > 0 else "reject"
        expected = x["expected_semantic"]
        records.append({
            "case_id": case_id,
            "expected": expected,
            "deck_X": {"label": x["decision"], "meaning": x["actual_semantic"], "log_odds_1_over_A": round(x_margin, 8)},
            "deck_Y": {"label": y["decision"], "meaning": y["actual_semantic"], "log_odds_1_over_A": round(y_margin, 8)},
            "agreement_method": {
                "decision": agreement,
                "correct": agreement == expected,
                "answered": agreement != "unsure"
            },
            "logit_calibration": {
                "semantic_margin": round(calibrated_margin, 8),
                "decision": calibrated,
                "correct": calibrated == expected
            }
        })
    answered = [record for record in records if record["agreement_method"]["answered"]]
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6K",
        "status": "post_hoc_exploratory_analysis_complete",
        "protocol": "/experiments/E007/mirrored-calibration-protocol-v0.1.json",
        "input": "/experiments/E007/numeric-letter-result-v0.1.json",
        "summary": {
            "agreement_method": {
                "answered": len(answered),
                "unsure": len(records) - len(answered),
                "correct_when_answered": sum(record["agreement_method"]["correct"] for record in answered),
                "wrong_when_answered": sum(not record["agreement_method"]["correct"] for record in answered)
            },
            "logit_calibration": {
                "correct": sum(record["logit_calibration"]["correct"] for record in records),
                "total": len(records),
                "approve_decisions": sum(record["logit_calibration"]["decision"] == "approve" for record in records),
                "reject_decisions": sum(record["logit_calibration"]["decision"] == "reject" for record in records)
            }
        },
        "conclusion": {
            "en": "Neither simple calibration worked. Agreement covered only four cases and was right on two. Logit subtraction still returned approve for all ten cases.",
            "ru": "Ни одна простая калибровка не сработала. Согласие ответило лишь на четыре случая и было верно в двух. Вычитание логитов всё равно вернуло approve для всех десяти случаев."
        },
        "records": records,
        "boundary": protocol["claim_boundary"]
    }


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
