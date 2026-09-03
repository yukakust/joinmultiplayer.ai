#!/usr/bin/env python3
"""Private E007 7S.2 replay of the executable Miro harness order.

The input contains owner-private memory excerpts. Never write its contents to
the repository. The output path must also remain outside the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.request
from pathlib import Path

from pocket_i_core.nli import LocalNli


TAKE_AT = 0.92222771
DROP_AT = 0.00292693
NO_INFORMATION = "I couldn't find supported information in your connected memory."
RERANKER_INSTRUCTION = "Given a question, decide whether the passage contains information that directly helps answer that question."
EXPECTED_RAW_CASES = {2: "useful", 3: "useful", 8: "useful", 9: "wrong_context", 11: "useful", 14: "wrong_context", 15: "useful", 20: "wrong_context"}
PREFIX = (
    '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. '
    'Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
)
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_json(value: str) -> dict:
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model returned no JSON object")
    return json.loads(value[start : end + 1])


def private_articles(path: Path) -> list[dict]:
    source = path.read_text(encoding="utf-8")
    records = []
    for number, article in enumerate(re.findall(r"<article>(.*?)</article>", source, re.S), 1):
        heading = re.search(r"<h2>(.*?)</h2>", article, re.S)
        expected = re.search(r"Expected: <b>(.*?)</b>", article, re.S)
        trace = re.search(r"<summary>Full private trace</summary><pre>(.*?)</pre>", article, re.S)
        if not heading or not trace:
            continue
        question = re.sub(r"^\s*\d+\.\s*", "", html.unescape(re.sub(r"<[^>]+>", "", heading.group(1)))).strip()
        events = json.loads(html.unescape(trace.group(1)))
        grounded = [event for event in events if event.get("stage") == "grounded_evidence"]
        accepted_ids = grounded[-1].get("details", {}).get("accepted_ids", []) if grounded else []
        if not accepted_ids:
            continue
        sources_event = next(event for event in events if event.get("stage") == "sources_received")
        checked_event = next(event for event in events if event.get("stage") == "evidence_id_check")
        old_candidates = checked_event.get("details", {}).get("accepted", [])
        old_source_ids = sorted({
            source_id
            for candidate in old_candidates
            if candidate.get("candidate_id") in accepted_ids
            for source_id in candidate.get("source_ids", [])
        })
        records.append({
            "original_row": number,
            "expected_raw_case": EXPECTED_RAW_CASES[number],
            "question": question,
            "expected": html.unescape(re.sub(r"<[^>]+>", "", expected.group(1))).strip() if expected else "",
            "sources": sources_event["details"]["sources"],
            "old_grounded_source_ids": old_source_ids,
        })
    if len(records) != 8:
        raise ValueError(f"expected the frozen eight grounded cases, found {len(records)}")
    return records


def reranker_prompt(question: str, passage: str) -> str:
    body = f"<Instruct>: {RERANKER_INSTRUCTION}\n<Query>: {question}\n<Document>: {passage}"
    return PREFIX + body + SUFFIX


def post_json(url: str, payload: dict, timeout: int = 600) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def reranker_score(server: str, question: str, passage: str) -> float:
    body = post_json(server.rstrip("/") + "/embedding", {
        "content": reranker_prompt(question, passage),
        "embd_normalize": -1,
    })
    values = body[0]["embedding"]
    if values and isinstance(values[0], list):
        values = values[0]
    yes, no = float(values[0]), float(values[1])
    return yes / (yes + no)


def reranker_decision(score: float) -> str:
    if score >= TAKE_AT:
        return "TAKE"
    if score <= DROP_AT:
        return "DROP"
    return "NOT_SURE"


def qwen(server: str, system: str, prompt: str, *, tokens: int) -> str:
    result = post_json(server.rstrip("/") + "/v1/chat/completions", {
        "model": "qwen3:8b",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0,
        "max_tokens": tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    })
    return str(result["choices"][0]["message"]["content"]).strip()


def evidence_units(sources: list[dict]) -> list[dict]:
    units = []
    for source in sources:
        source_id = str(source["source_id"])
        text = str(source["text"])[:1800]
        pieces = re.findall(r"[^.!?。！？]+(?:[.!?。！？]+(?=\s|$)|$)", text)
        for index, piece in enumerate((value.strip() for value in pieces if value.strip()), 1):
            units.append({"evidence_id": f"{source_id}.{index}", "source_id": source_id, "text": piece})
    return units


def extraction_prompt(question: str, units: list[dict]) -> str:
    rendered = "\n\n".join(f"[{item['evidence_id']}] {item['text']}" for item in units)
    return (
        "QUESTION\n" + question + "\n\nALLOWED EXACT EVIDENCE BLOCKS\n" + rendered +
        '\n\nReturn JSON only: {"candidates":[{"claim":"one atomic answer claim","evidence_ids":["S1.2"]}]}. '
        "Use only listed IDs. Use one to four IDs per claim and at most six claims. "
        'If the blocks do not answer the question, return {"candidates":[]}.'
    )


def validate_candidates(raw: str, sources: list[dict]) -> tuple[list[dict], list[dict]]:
    try:
        payload = extract_json(raw)
    except (ValueError, json.JSONDecodeError):
        return [], [{"reason": "invalid_json"}]
    units = evidence_units(sources)
    unit_by_id = {item["evidence_id"]: item for item in units}
    source_by_id = {str(item["source_id"]): str(item["text"])[:1800] for item in sources}
    accepted, rejected = [], []
    for index, item in enumerate(payload.get("candidates", [])[:6], 1):
        claim = str(item.get("claim", "")).strip()
        ids = list(dict.fromkeys(str(value).strip() for value in item.get("evidence_ids", []) if str(value).strip()))
        selected = [unit_by_id.get(value) for value in ids]
        reason = None
        if not claim or len(claim) > 600:
            reason = "invalid_claim"
        elif not 1 <= len(ids) <= 4:
            reason = "invalid_evidence_ids"
        elif any(value is None for value in selected):
            reason = "invented_evidence_id"
        if reason:
            rejected.append({"candidate_id": f"E{index}", "claim": claim, "evidence_ids": ids, "reason": reason})
            continue
        source_ids = sorted({value["source_id"] for value in selected})
        accepted.append({
            "candidate_id": f"E{index}",
            "claim": claim,
            "evidence_ids": ids,
            "evidence_blocks": selected,
            "quote": "\n".join(value["text"] for value in selected),
            "source_contexts": [{"source_id": source_id, "text": source_by_id[source_id]} for source_id in source_ids],
        })
    return accepted, rejected


def writer_prompt(question: str, claims: list[dict]) -> str:
    evidence = "\n\n".join(
        f"[{item['candidate_id']}] CLAIM: {item['claim']}\nEXACT SOURCE: {item['quote']}"
        for item in claims
    )
    return (
        f"QUESTION\n{question}\n\nACCEPTED EVIDENCE SHELVES\n{evidence}\n\n"
        "Write one short direct answer using only these shelves. Cite every factual sentence with its label, such as [E1]. "
        "Do not add facts."
    )


def valid_final(answer: str, claims: list[dict]) -> bool:
    allowed = {item["candidate_id"] for item in claims}
    citations = re.findall(r"\[(E\d+)\]", answer)
    return bool(citations) and all(value in allowed for value in citations)


def run(args: argparse.Namespace) -> dict:
    if args.output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("private output must stay outside the repository")
    if args.output.exists():
        raise ValueError("refusing to overwrite a preserved private result")
    records = private_articles(args.input)
    nli = LocalNli(args.nli)
    started = time.monotonic()
    totals = {"raw_excerpts": 0, "take": 0, "not_sure": 0, "drop": 0, "claims": 0, "grounded": 0, "answered": 0}
    for row_number, record in enumerate(records, 1):
        print(f"[{row_number}/8] reranking raw excerpts", flush=True)
        # The frozen unit is the raw source bundle behind the one claim that
        # previously survived DeBERTa.  Reranking every retrieved source would
        # change the experiment from an eight-case ordering replay into a new
        # retrieval benchmark.
        frozen_sources = [
            source for source in record["sources"]
            if source["source_id"] in record["old_grounded_source_ids"]
        ]
        record["sources"] = frozen_sources
        for source in frozen_sources:
            score = reranker_score(args.reranker, record["question"], source["text"])
            source["reranker"] = {"score": round(score, 8), "decision": reranker_decision(score)}
            totals["raw_excerpts"] += 1
            totals[source["reranker"]["decision"].lower()] += 1
        forwarded = [item for item in frozen_sources if item["reranker"]["decision"] != "DROP"]
        old_decisions = {
            item["source_id"]: item["reranker"]["decision"]
            for item in record["sources"] if item["source_id"] in record["old_grounded_source_ids"]
        }
        record["old_grounded_source_decisions"] = old_decisions
        record["forwarded_source_ids"] = [item["source_id"] for item in forwarded]
        if not forwarded:
            record.update({"raw_extraction": "", "valid_candidates": [], "rejected_candidates": [], "grounded_claims": [], "final_answer": NO_INFORMATION, "terminal": "no_relevant_raw_excerpt"})
            continue
        units = evidence_units(forwarded)
        raw = qwen(args.qwen, "You extract exact evidence after relevance screening. Return only JSON.", extraction_prompt(record["question"], units), tokens=1024)
        accepted, rejected = validate_candidates(raw, forwarded)
        record["raw_extraction"] = raw
        record["valid_candidates"] = accepted
        record["rejected_candidates"] = rejected
        totals["claims"] += len(accepted)
        if accepted:
            signals = nli([(item["source_contexts"][0]["text"], item["claim"]) for item in accepted])
        else:
            signals = []
        grounded = []
        for item, (label, confidence) in zip(accepted, signals):
            item["deberta"] = {"label": label, "confidence": round(float(confidence), 8)}
            if label == "entailment":
                grounded.append(item)
        record["grounded_claims"] = grounded
        totals["grounded"] += len(grounded)
        if not grounded:
            record.update({"final_answer": NO_INFORMATION, "terminal": "no_grounded_claim"})
            continue
        answer = qwen(args.qwen, "You write only from accepted evidence shelves.", writer_prompt(record["question"], grounded), tokens=512)
        if not valid_final(answer, grounded):
            record.update({"final_answer": NO_INFORMATION, "raw_writer_answer": answer, "terminal": "invalid_final_citations"})
            continue
        record.update({"final_answer": answer, "terminal": "answered"})
        totals["answered"] += 1
    result = {
        "schema_version": "e007-raw-first-private-replay-v0.1",
        "warning": "PRIVATE: contains local memory excerpts and model outputs; do not publish",
        "protocol": "raw-first-reranker-replay-protocol-v0.1",
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "architecture_sha256": digest(Path(args.architecture).read_text(encoding="utf-8")),
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
    value.add_argument("--architecture", type=Path, default=Path("site/experiments/E007/miro-executable-harness-v0.1.json"))
    value.add_argument("--reranker", default="http://127.0.0.1:18084")
    value.add_argument("--qwen", default="http://127.0.0.1:18085")
    value.add_argument("--nli", type=Path, default=Path("desktop/app/nli-current"))
    return value


if __name__ == "__main__":
    run(parser().parse_args())
