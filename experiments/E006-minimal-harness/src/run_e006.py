from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


CONDITIONS = ("centralized_context", "free_text_swarm", "minimal_harness")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def extract_json(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def validate_capsule(raw: str, document: dict) -> dict:
    value = extract_json(raw)
    if value is None:
        return {"accepted": False, "reason": "no_valid_json", "raw": raw}
    status = value.get("status")
    if status == "not_found":
        missing = value.get("missing")
        if not isinstance(missing, str) or not missing.strip():
            return {"accepted": False, "reason": "not_found_without_missing", "raw": raw, "parsed": value}
        return {
            "accepted": True,
            "capsule": {"status": "not_found", "claim": None, "source": None, "quote": None, "missing": missing.strip()},
            "raw": raw,
        }
    if status != "found":
        return {"accepted": False, "reason": "unknown_status", "raw": raw, "parsed": value}
    claim, source, quote = value.get("claim"), value.get("source"), value.get("quote")
    if not all(isinstance(item, str) and item.strip() for item in (claim, source, quote)):
        return {"accepted": False, "reason": "missing_required_field", "raw": raw, "parsed": value}
    if source.strip() != document["id"]:
        return {"accepted": False, "reason": "wrong_source_id", "raw": raw, "parsed": value}
    if quote.strip() not in document["text"]:
        return {"accepted": False, "reason": "quote_not_exact", "raw": raw, "parsed": value}
    return {
        "accepted": True,
        "capsule": {
            "status": "found",
            "claim": claim.strip(),
            "source": source.strip(),
            "quote": quote.strip(),
            "missing": value.get("missing") if isinstance(value.get("missing"), str) else None,
        },
        "raw": raw,
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def chat_prompt(tokenizer, system: str, user: str) -> str:
    return tokenizer.apply_chat_template(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


@torch.inference_mode()
def generate(model, tokenizer, system: str, user: str, max_new_tokens: int) -> dict:
    prompt = chat_prompt(tokenizer, system, user)
    encoded = tokenizer(prompt, return_tensors="pt")
    started = time.monotonic()
    output = model.generate(
        **encoded,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        use_cache=True,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    generated = output[0, encoded["input_ids"].shape[1] :]
    answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
    reached_ceiling = len(generated) >= max_new_tokens and (not len(generated) or generated[-1].item() != tokenizer.eos_token_id)
    return {
        "text": answer,
        "generated_tokens": int(len(generated)),
        "reached_ceiling": reached_ceiling,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def central_user(question: dict, documents: list[dict]) -> str:
    records = "\n\n".join(f"[{doc['id']}]\n{doc['text']}" for doc in documents)
    return f"""QUESTION
{question['question']}

THREE ORACLE-SELECTED RECORDS
{records}

Give one concise answer with both the diagnosis and safe action. Cite the record IDs supporting each part. One record may describe a different-looking event; do not use it unless its exact conditions match. Do not add facts absent from the records."""


def local_free_user(question: dict, document: dict) -> str:
    return f"""A user asked:
{question['question']}

Your only local record is:
[{document['id']}] {document['text']}

Send a short free-form note to the final model. Explain only what this record supports and what it does not establish. Include the record ID. Do not use outside knowledge."""


def free_final_user(question: dict, messages: list[dict]) -> str:
    notes = "\n\n".join(f"POCKET {item['pocket_id']} SAID:\n{item['message']['text']}" for item in messages)
    return f"""QUESTION
{question['question']}

THREE POCKET-I MESSAGES
{notes}

Write one concise answer with both the diagnosis and safe action. Cite the source IDs that support each part. The messages may include a similar but irrelevant event. Do not add unsupported facts."""


def local_capsule_user(question: dict, document: dict) -> str:
    return f"""A user asked:
{question['question']}

Your only local record is:
[{document['id']}] {document['text']}

Return exactly one JSON object and nothing else:
{{"status":"found" or "not_found","claim":"one short human-readable statement or null","source":"{document['id']}" or null,"quote":"one exact copied substring of the local record or null","missing":"what this record cannot answer or null"}}

Use status found only for a claim directly supported by an exact quote. Do not use outside knowledge."""


def harness_final_user(question: dict, accepted: list[dict], rejected: list[dict]) -> str:
    packets = json.dumps(accepted, ensure_ascii=False, indent=2)
    return f"""QUESTION
{question['question']}

VALIDATED CAPSULES
{packets}

The harness rejected {len(rejected)} other capsule(s). Write one concise answer with both the diagnosis and safe action only when the validated capsules support them. Cite the source ID for each part. If a part is missing, say exactly what is missing. Do not add factual claims absent from the validated capsules."""


def diagnostic_score(answer: str, question: dict) -> dict:
    normalized = normalize(answer)
    return {
        "exact_cause_phrase": normalize(question["expected_cause"]) in normalized,
        "exact_action_phrase": normalize(question["expected_action"]) in normalized,
        "required_source_ids_present": sum(source.lower() in answer.lower() for source in question["required_sources"]),
    }


def run(args: argparse.Namespace) -> dict:
    torch.set_num_threads(args.threads)
    torch.manual_seed(26082026)
    world = json.loads(args.world.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if world["status"] != "locked_before_run" or protocol["status"] != "locked_before_run":
        raise ValueError("E006 inputs are not locked")
    if len(world["questions"]) != 10 or protocol["scope"]["language"] != "en":
        raise ValueError("E006 scope changed")
    model_hash = sha256_file(args.model / "model.safetensors")
    if model_hash != protocol["generation"]["model_weights_sha256"]:
        raise ValueError("model weights differ from the frozen protocol")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=True, dtype=torch.float32, low_cpu_mem_usage=True
    ).eval()
    docs = {document["id"]: document for document in world["documents"]}
    pockets = {pocket["id"]: pocket for pocket in world["pockets"]}
    metadata = {
        "experiment_id": "E006",
        "version": "0.1",
        "kind": "minimal_harness_oracle_transport_development",
        "protocol": "/experiments/E006/protocol-v0.2.json",
        "world": "/experiments/E006/world-v0.1.json",
        "model_weights_sha256": model_hash,
        "decoding": "greedy",
        "training": False,
    }
    records: list[dict] = []
    if args.output.exists():
        checkpoint = json.loads(args.output.read_text(encoding="utf-8"))
        if checkpoint.get("status") != "running_intermediate_not_result":
            raise ValueError("existing output is not resumable")
        if any(checkpoint.get(key) != value for key, value in metadata.items()):
            raise ValueError("resume metadata differs")
        records = checkpoint["records"]
    completed = {(record["condition"], record["question_id"]) for record in records}
    started = time.monotonic()

    for condition in CONDITIONS:
        for question in world["questions"]:
            if (condition, question["id"]) in completed:
                continue
            selected = [docs[document_id] for document_id in question["documents"]]
            base_record = {
                "question_id": question["id"],
                "condition": condition,
                "question": question["question"],
                "expected_cause": question["expected_cause"],
                "expected_action": question["expected_action"],
                "required_sources": question["required_sources"],
                "selected_pockets": question["selected_pockets"],
                "selected_documents": question["documents"],
            }
            if condition == "centralized_context":
                final = generate(
                    model,
                    tokenizer,
                    "You are the final frozen Qwen in a synthetic evidence experiment.",
                    central_user(question, selected),
                    args.final_max_new_tokens,
                )
                record = {**base_record, "local_outputs": [], "final": final}
            elif condition == "free_text_swarm":
                local_outputs = []
                for pocket_id, document in zip(question["selected_pockets"], selected):
                    message = generate(
                        model,
                        tokenizer,
                        f"You are pocket i {pockets[pocket_id]['name']}. You can read only your local record.",
                        local_free_user(question, document),
                        args.local_max_new_tokens,
                    )
                    local_outputs.append({"pocket_id": pocket_id, "document_id": document["id"], "message": message})
                final = generate(
                    model,
                    tokenizer,
                    "You are the final frozen Qwen. Combine only supported information from pocket-i messages.",
                    free_final_user(question, local_outputs),
                    args.final_max_new_tokens,
                )
                record = {**base_record, "local_outputs": local_outputs, "final": final}
            else:
                local_outputs, accepted, rejected = [], [], []
                for pocket_id, document in zip(question["selected_pockets"], selected):
                    message = generate(
                        model,
                        tokenizer,
                        f"You are pocket i {pockets[pocket_id]['name']}. You can read only your local record.",
                        local_capsule_user(question, document),
                        args.local_max_new_tokens,
                    )
                    checked = validate_capsule(message["text"], document)
                    item = {"pocket_id": pocket_id, "document_id": document["id"], "message": message, "validation": checked}
                    local_outputs.append(item)
                    if checked["accepted"]:
                        accepted.append({"pocket_id": pocket_id, **checked["capsule"]})
                    else:
                        rejected.append({"pocket_id": pocket_id, "document_id": document["id"], "reason": checked["reason"]})
                final = generate(
                    model,
                    tokenizer,
                    "You are the final frozen Qwen. The harness has already rejected unsupported packets.",
                    harness_final_user(question, accepted, rejected),
                    args.final_max_new_tokens,
                )
                record = {**base_record, "local_outputs": local_outputs, "accepted_capsules": accepted, "rejected_capsules": rejected, "final": final}
            record["automatic_diagnostic"] = diagnostic_score(record["final"]["text"], question)
            records.append(record)
            completed.add((condition, question["id"]))
            payload = {**metadata, "status": "running_intermediate_not_result", "records_completed": len(records), "records": records}
            atomic_json(args.output, payload)
            print(json.dumps({"condition": condition, "question": question["id"], "records_completed": len(records)}), flush=True)

    result = {
        **metadata,
        "status": "generation_complete_semantic_review_pending",
        "records_completed": len(records),
        "elapsed_seconds_this_process": round(time.monotonic() - started, 3),
        "automatic_diagnostic_warning": "Exact phrase and source-ID checks are navigation aids only. They are not semantic scores.",
        "records": records,
    }
    atomic_json(args.output, result)
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--model", type=Path, required=True)
    value.add_argument("--world", type=Path, required=True)
    value.add_argument("--protocol", type=Path, required=True)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--threads", type=int, default=20)
    value.add_argument("--local-max-new-tokens", type=int, default=128)
    value.add_argument("--final-max-new-tokens", type=int, default=192)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
