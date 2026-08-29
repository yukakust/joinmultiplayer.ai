#!/usr/bin/env python3
"""Run E007 Gate 16A central pipeline after four physical nodes finish."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import subprocess
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/physical-mvp-protocol-v0.1.json"
MEMORY_PATH = ROOT / "site/experiments/E007/physical-mvp-memory-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/physical-mvp-result-v0.1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def source_index(memory: dict) -> dict[str, dict]:
    return {
        document["id"]: {**document, "card_id": card_id}
        for card_id, documents in memory["libraries"].items()
        for document in documents
    }


def validate_transport(room: dict, protocol: dict) -> dict:
    expected_cards = {card for device in protocol["devices"] for card in device["cards"]}
    expected_devices = {device["id"] for device in protocol["devices"]}
    nodes = room.get("nodes", [])
    receipts = [item for node in nodes for item in (node.get("result") or {}).get("results", [])]
    question_hashes = {
        item["id"]: digest_bytes(item["question"].encode("utf-8"))
        for item in protocol["questions"]
    }
    mismatches = sum(
        item.get("question_hash") != question_hashes.get(item.get("question_id"))
        for item in receipts
    )
    raw = json.dumps(room, ensure_ascii=False)
    return {
        "room_id": room.get("room_id"),
        "room_complete": room.get("status") == "complete",
        "nodes_complete": sum(node.get("status") == "complete" for node in nodes),
        "nodes_total": len(nodes),
        "cards": sorted(node.get("card_id") for node in nodes),
        "cards_match": {node.get("card_id") for node in nodes} == expected_cards,
        "devices": sorted({node.get("device_label") for node in nodes}),
        "devices_match": {node.get("device_label") for node in nodes} == expected_devices,
        "terminal_receipts": len(receipts),
        "question_hash_mismatches": mismatches,
        "blocked_receipts": sum(item.get("status") == "blocked" for item in receipts),
        "blocked_capsules_present": sum(
            item.get("status") == "blocked" and item.get("capsule") is not None for item in receipts
        ),
        "public_placeholder_present": "{{SYNTHETIC_PRIVATE_CANARY}}" in raw,
        "passed": (
            room.get("protocol_revision") == protocol["revision"]
            and room.get("status") == "complete"
            and len(nodes) == 4
            and all(node.get("status") == "complete" for node in nodes)
            and {node.get("card_id") for node in nodes} == expected_cards
            and {node.get("device_label") for node in nodes} == expected_devices
            and len(receipts) == 72
            and mismatches == 0
            and not any(
                item.get("status") == "blocked" and item.get("capsule") is not None
                for item in receipts
            )
            and "{{SYNTHETIC_PRIVATE_CANARY}}" not in raw
        ),
    }


def mechanically_verified_candidates(room: dict, protocol: dict, memory: dict) -> tuple[list[dict], list[dict]]:
    sources = source_index(memory)
    questions = {item["id"]: item["question"] for item in protocol["questions"]}
    records: dict[tuple[str, str], dict] = {}
    checks = []
    for node in room["nodes"]:
        for receipt in node["result"]["results"]:
            if receipt["status"] != "found":
                continue
            source = sources.get(receipt["source_id"])
            capsule = receipt.get("capsule") or {}
            expected = source.get("capsule", {}) if source else {}
            valid = bool(
                source
                and source["permission"] != "blocked"
                and source["card_id"] == node["card_id"]
                and capsule.get("evidence") == source["text"]
                and capsule.get("claim") == expected.get("claim")
                and capsule.get("source") == expected.get("source")
                and capsule.get("source_lineage") == source.get("lineage")
                and capsule.get("conditions") == expected.get("conditions")
                and capsule.get("limitations") == expected.get("limitations")
                and capsule.get("permission") == "share_this_capsule"
            )
            checks.append({
                "question_id": receipt["question_id"], "source_id": receipt["source_id"],
                "lane": receipt["lane"], "valid": valid,
            })
            if not valid:
                continue
            key = (receipt["question_id"], receipt["source_id"])
            candidate = {
                "question_id": receipt["question_id"],
                "question": questions[receipt["question_id"]],
                "source_id": receipt["source_id"],
                "lineage_id": capsule["source_lineage"],
                "card_id": node["card_id"],
                "device": node["device_label"],
                "claim": capsule["claim"],
                "evidence": capsule["evidence"],
                "source": capsule["source"],
                "conditions": capsule["conditions"],
                "limitations": capsule["limitations"],
                "source_sha256": digest_bytes(source["text"].encode("utf-8")),
                "receipt_lanes": [],
                "local_scores": {},
            }
            if key not in records:
                records[key] = candidate
            records[key]["receipt_lanes"].append(receipt["lane"])
            records[key]["local_scores"][receipt["lane"]] = receipt["score"]
    return sorted(records.values(), key=lambda item: (item["question_id"], item["source_id"])), checks


def reranker_prompt(instruction: str, question: str, evidence: str) -> str:
    return (
        '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. '
        'Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
        f"<Instruct>: {instruction}\n<Query>: {question}\n<Document>: {evidence}"
        "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )


def reranker_score(server: str, instruction: str, question: str, evidence: str) -> float:
    content = reranker_prompt(instruction, question, evidence)
    request = urllib.request.Request(
        server.rstrip("/") + "/embedding",
        data=json.dumps({"content": content, "embd_normalize": -1}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    scores = payload[0].get("embedding", []) if payload else []
    if scores and isinstance(scores[0], list):
        scores = scores[0]
    if len(scores) < 2 or not all(math.isfinite(float(value)) for value in scores[:2]):
        raise RuntimeError("reranker did not return yes/no scores")
    yes, no = float(scores[0]), float(scores[1])
    return yes / (yes + no)


def reranker_decision(score: float, spec: dict) -> str:
    if score >= spec["take_at_or_above"]:
        return "TAKE"
    if score <= spec["drop_at_or_below"]:
        return "DROP"
    return "NOT_SURE"


def nli_decision(model, tokenizer, evidence: str, claim: str) -> dict:
    import torch

    encoded = tokenizer(evidence, claim, truncation=True, return_tensors="pt")
    with torch.inference_mode():
        probabilities = torch.softmax(model(**encoded).logits, dim=-1)[0]
    scores = {
        model.config.id2label[index].lower(): round(float(value), 8)
        for index, value in enumerate(probabilities)
    }
    winner = max(scores, key=scores.get)
    return {"decision": winner, "probabilities": scores, "passed": winner == "entailment"}


def parse_json_object(raw: str) -> dict | None:
    value = raw.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def generate_json(model, tokenizer, system: str, user: str, max_new_tokens: int) -> tuple[str, dict | None]:
    import torch

    chat = tokenizer.apply_chat_template(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    encoded = tokenizer(chat, return_tensors="pt")
    with torch.inference_mode():
        output = model.generate(
            **encoded, do_sample=False, max_new_tokens=max_new_tokens,
            eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
        )
    raw = tokenizer.decode(output[0][encoded["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return raw, parse_json_object(raw)


def shelf_prompt(question: str, records: list[dict]) -> str:
    rendered = "\n\n".join(
        f"ID: {item['source_id']}\nCLAIM: {item['claim']}\nEVIDENCE: {item['evidence']}\n"
        f"CONDITIONS: {item['conditions']}\nLIMITATIONS: {item['limitations']}\nLINEAGE: {item['lineage_id']}"
        for item in records
    ) or "NO ACCEPTED RECORDS"
    return (
        f"QUESTION\n{question}\n\nVERIFIED RECORDS\n{rendered}\n\n"
        "Return exactly one JSON object with keys used_ids and same_case_ids. "
        "USED is the smallest supported set that jointly answers the question. "
        "SAME_CASE contains other supported views about the same case. "
        "Do not select records about another device or signal. If no record helps, return two empty lists."
    )


def writer_prompt(question: str, records: list[dict]) -> str:
    rendered = "\n".join(
        f"[{item['source_id']}] {item['claim']} Evidence: {item['evidence']}"
        for item in records
    )
    return (
        f"QUESTION\n{question}\n\nUSED SHELF\n{rendered}\n\n"
        "Write one clear answer using only the USED shelf. Return exactly one JSON object "
        "with keys answer and evidence_ids. Cite only IDs shown above."
    )


def run(args: argparse.Namespace) -> dict:
    import torch
    from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer

    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol, memory, room = read(args.protocol), read(args.memory), read(args.room)
    if protocol["status"] != "locked_before_any_node_search_or_model_inference":
        raise RuntimeError("protocol is not locked")
    if digest(args.memory) != protocol["memory_sha256"]:
        raise RuntimeError("locked memory changed")
    transport = validate_transport(room, protocol)
    if not transport["passed"]:
        raise RuntimeError(f"physical transport gate failed: {transport}")
    candidates, mechanical_checks = mechanically_verified_candidates(room, protocol, memory)
    if not all(item["valid"] for item in mechanical_checks):
        raise RuntimeError("a found capsule failed exact source verification")

    contract = protocol["central_pipeline_contract"]
    reranker = contract["reranker"]
    started = time.perf_counter()
    for index, item in enumerate(candidates, 1):
        value = reranker_score(args.reranker_server, reranker["instruction"], item["question"], item["evidence"])
        item["reranker"] = {"score": round(value, 8), "decision": reranker_decision(value, reranker)}
        print(json.dumps({"stage": "reranker", "completed": index, "total": len(candidates)}), flush=True)

    nli_spec = contract["nli"]
    nli_tokenizer = AutoTokenizer.from_pretrained(
        nli_spec["model"], revision=nli_spec["revision"], local_files_only=True
    )
    nli_model = AutoModelForSequenceClassification.from_pretrained(
        nli_spec["model"], revision=nli_spec["revision"], local_files_only=True, dtype=torch.float32
    ).eval()
    forwarded = [item for item in candidates if item["reranker"]["decision"] != "DROP"]
    for index, item in enumerate(forwarded, 1):
        item["nli"] = nli_decision(nli_model, nli_tokenizer, item["evidence"], item["claim"])
        print(json.dumps({"stage": "nli", "completed": index, "total": len(forwarded)}), flush=True)
    del nli_model

    qwen_spec = contract["shelf_builder"]
    tokenizer = AutoTokenizer.from_pretrained(
        qwen_spec["model"], revision=qwen_spec["revision"], local_files_only=True
    )
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        qwen_spec["model"], revision=qwen_spec["revision"], local_files_only=True, dtype=torch.bfloat16
    ).eval()
    questions = []
    for question in protocol["questions"]:
        accepted = [
            item for item in forwarded
            if item["question_id"] == question["id"] and item["nli"]["passed"]
        ]
        raw_shelf, parsed_shelf = generate_json(
            model, tokenizer,
            "You sort verified evidence without inventing facts. Output JSON only.",
            shelf_prompt(question["question"], accepted), 180,
        )
        allowed = {item["source_id"] for item in accepted}
        valid_shelf = bool(
            parsed_shelf
            and set(parsed_shelf) == {"used_ids", "same_case_ids"}
            and all(isinstance(value, list) for value in parsed_shelf.values())
            and all(isinstance(value, str) for value in parsed_shelf.values() for value in value)
            and set(parsed_shelf["used_ids"] + parsed_shelf["same_case_ids"]) <= allowed
            and not (set(parsed_shelf["used_ids"]) & set(parsed_shelf["same_case_ids"]))
        )
        used_ids = parsed_shelf["used_ids"] if valid_shelf else []
        same_ids = parsed_shelf["same_case_ids"] if valid_shelf else []
        shelves = {
            "USED": [item for item in accepted if item["source_id"] in used_ids],
            "SAME_CASE": [item for item in accepted if item["source_id"] in same_ids],
            "OTHER": [item for item in accepted if item["source_id"] not in set(used_ids + same_ids)],
        }
        if shelves["USED"]:
            raw_answer, parsed_answer = generate_json(
                model, tokenizer,
                "You answer only from the supplied evidence. Output JSON only.",
                writer_prompt(question["question"], shelves["USED"]), 180,
            )
            valid_answer = bool(
                parsed_answer
                and set(parsed_answer) == {"answer", "evidence_ids"}
                and isinstance(parsed_answer["answer"], str)
                and isinstance(parsed_answer["evidence_ids"], list)
                and set(parsed_answer["evidence_ids"]) <= set(used_ids)
            )
        else:
            raw_answer = None
            parsed_answer = {"answer": contract["writer"]["empty_answer"], "evidence_ids": []}
            valid_answer = True
        questions.append({
            "id": question["id"], "question": question["question"],
            "expected_meaning": question["expected_meaning"],
            "required_sources": question.get("required_sources", []),
            "expected_alternatives": question.get("same_case_alternatives", []),
            "candidates_before_central_filter": [item for item in candidates if item["question_id"] == question["id"]],
            "accepted_after_reranker_and_nli": accepted,
            "shelf_builder": {"raw": raw_shelf, "parsed": parsed_shelf, "valid": valid_shelf},
            "shelves": shelves,
            "writer": {"raw": raw_answer, "parsed": parsed_answer, "valid": valid_answer},
        })
        print(json.dumps({"stage": "shelf_and_writer", "completed": len(questions), "total": 6}), flush=True)

    result = {
        "schema_version": "0.1", "experiment_id": "E007", "gate": "16A",
        "status": "locked_physical_mvp_inference_complete_manual_audit_pending",
        "git_revision": git_revision(), "protocol_sha256": digest(args.protocol),
        "memory_sha256": digest(args.memory), "transport": transport,
        "models": contract, "summary": {
            "questions": len(questions), "mechanically_verified_candidates": len(candidates),
            "reranker_take": sum(item["reranker"]["decision"] == "TAKE" for item in candidates),
            "reranker_not_sure": sum(item["reranker"]["decision"] == "NOT_SURE" for item in candidates),
            "reranker_drop": sum(item["reranker"]["decision"] == "DROP" for item in candidates),
            "nli_forwarded": len(forwarded),
            "nli_passed": sum(item["nli"]["passed"] for item in forwarded),
            "valid_shelf_outputs": sum(item["shelf_builder"]["valid"] for item in questions),
            "valid_writer_outputs": sum(item["writer"]["valid"] for item in questions),
            "manual_audit": "pending",
        },
        "questions": questions,
        "runtime": {"seconds": round(time.perf_counter() - started, 3), "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
        "boundaries": protocol["boundaries"],
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    value.add_argument("--memory", type=Path, default=MEMORY_PATH)
    value.add_argument("--room", type=Path, required=True)
    value.add_argument("--output", type=Path, default=RESULT_PATH)
    value.add_argument("--reranker-server", default="http://127.0.0.1:18086")
    return value


if __name__ == "__main__":
    run(parser().parse_args())
