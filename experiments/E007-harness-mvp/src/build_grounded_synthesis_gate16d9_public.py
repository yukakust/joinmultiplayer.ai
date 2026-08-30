#!/usr/bin/env python3
"""Build reviewed, privacy-safe Gate 16D.9 output."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


UNSUPPORTED = {
    "Q06-retrieved_shelf/C02": "Связала отдельный C4 handoff-дефект с превышением budget без такого доказательства в цитате.",
    "Q06-oracle_shelf/C04": "Связала C4 handoff-дефект с неправильным budgeting без такого доказательства.",
    "Q07-oracle_shelf/C01": "Цитата говорит лишь «сейчас сверяю», а claim уже объявляет проверку завершённой.",
    "Q07-oracle_shelf/C02": "Цитата говорит лишь «сейчас сверяю», а claim уже объявляет SHA подтверждённым.",
    "Q08-oracle_shelf/C02": "Цитата рекомендует будущую проверку, но сама по себе не доказывает формулировку claim."
}


def sanitize(text: str | None) -> str | None:
    if text is None: return None
    return re.sub(r"\]\(/home/[^)]+\)", "]", text)


def build(private: dict) -> dict:
    rows=[]
    supported=accepted_supported=unsupported_accepted=0
    for source in private["rows"]:
        claims=[]
        for claim in source["claims"]:
            key=f'{source["id"]}/{claim["id"]}'
            human_grounded=key not in UNSUPPORTED
            accepted=bool(claim.get("accepted"))
            supported += int(human_grounded)
            accepted_supported += int(human_grounded and accepted)
            unsupported_accepted += int(not human_grounded and accepted)
            if not human_grounded:
                review=UNSUPPORTED[key]
            elif accepted:
                review="Верное утверждение принято."
            elif not claim["exact_quote"]:
                review="Верное утверждение потеряно: Qwen изменила цитату, поэтому код не нашёл её дословно."
            else:
                review="Верное утверждение потеряно: DeBERTa назвала связь neutral или contradiction."
            claims.append({
                "id":claim["id"],"claim":sanitize(claim["claim"]),"source_id":claim["source_id"],"quote":sanitize(claim["quote"]),
                "exact_quote":claim["exact_quote"],"nli_decision":(claim.get("nli") or {}).get("decision"),
                "nli_probabilities":(claim.get("nli") or {}).get("probabilities"),"accepted":accepted,
                "human_grounded":human_grounded,"review":review
            })
        rows.append({"id":source["id"],"question_id":source["question_id"],"condition":source["condition"],"question":source["question"],"message_ids":source["message_ids"],"claims":claims,"accepted_claims":[c["claim"] for c in claims if c["accepted"]]})
    total=sum(len(r["claims"]) for r in rows); exact=sum(c["exact_quote"] for r in rows for c in r["claims"]); accepted=sum(c["accepted"] for r in rows for c in r["claims"])
    return {
        "schema_version":"0.1","experiment":"E007","gate":"16D.9","status":"completed_failed_protocol_error",
        "protocol":"/experiments/E007/grounded-synthesis-gate16d9-protocol-v0.1.json",
        "protocol_error":"The locked boundary incorrectly described all eight source shelves as English. Q07 evidence is Russian, so English DeBERTa results for both Q07 conditions are not a valid monolingual NLI test.",
        "summary":{"valid_structured_answers":len(rows),"valid_structured_answers_possible":8,"claims":total,"exact_quotes":exact,"human_grounded_claims":supported,"nli_accepted":accepted,"grounded_claims_accepted":accepted_supported,"unsupported_claims":total-supported,"unsupported_claims_accepted":unsupported_accepted,"grounded_claims_rejected":supported-accepted_supported,"required_parts_retained":12,"required_parts_possible":36,"gate_passed":False},
        "rows":rows,
        "decision":"The turnstile had 8/8 precision on accepted claims and rejected all five unsupported or mis-cited claims, but retained only 8/30 grounded claims and 12/36 required parts. Exact quotes plus this English DeBERTa configuration are too destructive for the harness. Q07 also violated the locked English-source boundary, so this failed run cannot estimate monolingual NLI recall cleanly."
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--private",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    result=build(json.loads(args.private.read_text())); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__": main()
