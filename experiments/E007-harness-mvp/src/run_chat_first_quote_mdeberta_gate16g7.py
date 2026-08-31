#!/usr/bin/env python3
"""Run E007 Gate 16G.7 exact-quote and multilingual NLI acceptance."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
from pathlib import Path


QWEN_REPOSITORY = "Qwen/Qwen3-8B"
QWEN_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"

TOOLS = [
    {"type": "function", "function": {
        "name": "send_quote",
        "description": "Copy one exact source quote only when it directly proves the entire claim.",
        "parameters": {"type": "object", "properties": {
            "source_id": {"type": "string"},
            "quote": {"type": "string"}
        }, "required": ["source_id", "quote"], "additionalProperties": False}
    }},
    {"type": "function", "function": {
        "name": "send_no_quote",
        "description": "Use when no one exact quote directly proves the entire claim.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
    }}
]


def parse_quote_tool(raw: str, sources: dict[str, str], maximum_characters: int) -> dict:
    calls = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw, re.DOTALL)
    if len(calls) != 1:
        return {"quote_receipt": "ERROR", "quote_error": f"expected one complete tool call, got {len(calls)}"}
    try:
        call = json.loads(calls[0])
    except json.JSONDecodeError as error:
        return {"quote_receipt": "ERROR", "quote_error": f"invalid tool JSON: {error}"}
    name, arguments = call.get("name"), call.get("arguments")
    if name == "send_no_quote" and isinstance(arguments, dict) and not arguments:
        return {"quote_receipt": "NO_QUOTE", "source_id": None, "quote": None, "quote_exact": False}
    if name != "send_quote" or not isinstance(arguments, dict):
        return {"quote_receipt": "ERROR", "quote_error": "unknown tool call"}
    source_id, quote = arguments.get("source_id"), arguments.get("quote")
    if source_id not in sources or not isinstance(quote, str) or not quote.strip():
        return {"quote_receipt": "ERROR", "quote_error": "malformed quote payload"}
    if len(quote) > maximum_characters:
        return {"quote_receipt": "ERROR", "quote_error": "quote exceeds locked character limit"}
    exact = quote in sources[source_id]
    return {
        "quote_receipt": "EXACT_QUOTE" if exact else "ERROR",
        "source_id": source_id,
        "quote": quote,
        "quote_exact": exact,
        **({} if exact else {"quote_error": "quote is not an exact source substring"}),
    }


def centered_window(tokenizer, source: str, quote: str, claim: str, maximum: int = 512) -> tuple[str, int]:
    quote_start = source.find(quote)
    if quote_start < 0:
        raise ValueError("exact quote missing from source")
    quote_end = quote_start + len(quote)
    encoded = tokenizer(source, add_special_tokens=False, return_offsets_mapping=True)
    offsets, ids = encoded["offset_mapping"], encoded["input_ids"]
    quote_tokens = [index for index, (start, end) in enumerate(offsets) if end > quote_start and start < quote_end]
    if not quote_tokens:
        raise ValueError("quote has no source tokens")
    claim_tokens = len(tokenizer(claim, add_special_tokens=False)["input_ids"])
    budget = maximum - claim_tokens - tokenizer.num_special_tokens_to_add(pair=True)
    if budget < len(quote_tokens):
        raise ValueError("quote and claim do not fit the NLI model")
    budget = min(budget, len(ids))
    first, last = quote_tokens[0], quote_tokens[-1]
    spare = budget - (last - first + 1)
    start_token = first - min(first, spare // 2)
    end_token = min(len(ids), start_token + budget)
    start_token = max(0, end_token - budget)
    window = source[offsets[start_token][0]:offsets[end_token - 1][1]]
    if quote not in window:
        raise RuntimeError("centered window lost exact quote")
    return window, budget


def private_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_sources(sources: dict[str, str]) -> str:
    return "\n\n".join(f'<message id="{source_id}">\n{html.escape(text)}\n</message>' for source_id, text in sources.items())


def main() -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer, StoppingCriteria

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reader-result", type=Path, required=True)
    parser.add_argument("--conversation-snapshot", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.resume:
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    reader_bytes, snapshot_bytes = args.reader_result.read_bytes(), args.conversation_snapshot.read_bytes()
    if hashlib.sha256(reader_bytes).hexdigest() != protocol["inputs"]["private_reader_result_sha256"]:
        raise RuntimeError("reader result does not match locked protocol")
    if hashlib.sha256(snapshot_bytes).hexdigest() != protocol["inputs"]["private_conversation_snapshot_sha256"]:
        raise RuntimeError("conversation snapshot does not match locked protocol")
    reader, snapshot = json.loads(reader_bytes), json.loads(snapshot_bytes)
    chats = {f'{snapshot["node"]}-C{index:04d}': chat for index, chat in enumerate(snapshot["conversations"], 1)}
    candidates = [row for row in reader["rows"] if row["receipt"] == "FOUND"]
    if len(candidates) != protocol["inputs"]["candidates"]:
        raise RuntimeError("candidate count changed")

    tokenizer = AutoTokenizer.from_pretrained(QWEN_REPOSITORY, revision=QWEN_REVISION, local_files_only=True)

    class StopAfterToolCall(StoppingCriteria):
        def __init__(self, prefix_tokens: int): self.prefix_tokens = prefix_tokens
        def __call__(self, input_ids, scores, **kwargs):
            return "</tool_call>" in tokenizer.decode(input_ids[0, self.prefix_tokens:], skip_special_tokens=True)

    if args.resume:
        result = json.loads(args.output.read_text(encoding="utf-8"))
        if result.get("protocol_sha256") != hashlib.sha256(args.protocol.read_bytes()).hexdigest():
            raise RuntimeError("cannot resume under a changed protocol")
        result["status"] = "running_quote_extraction"
    else:
        result = {
            "schema_version": "0.1-private",
            "experiment": "E007",
            "gate": "16G.7",
            "status": "running_quote_extraction",
            "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
            "rows": [],
        }
        private_write(args.output, result)
    completed = {(row["question_id"], row["card_id"]) for row in result["rows"]}

    torch.set_num_threads(args.threads)
    qwen = AutoModelForCausalLM.from_pretrained(
        QWEN_REPOSITORY, revision=QWEN_REVISION, local_files_only=True, dtype=torch.bfloat16
    ).eval()
    maximum_quote = int(protocol["quote_extractor"]["maximum_quote_characters"])
    for candidate in candidates:
        key = (candidate["question_id"], candidate["card_id"])
        if key in completed:
            continue
        messages = {message["id"]: message["text"] for message in chats[candidate["card_id"]]["messages"]}
        sources = {source_id: messages[source_id] for source_id in candidate["evidence_message_ids"]}
        user = (
            f'CLAIM TO VERIFY:\n{candidate["claim"]}\n\nCITED SOURCE MESSAGES:\n{render_sources(sources)}\n\n'
            f"Call send_quote only if one exact contiguous quote of at most {maximum_quote} characters, copied character-for-character from one cited message, directly proves the entire claim. Related text or proof of only part of the claim is not enough. Otherwise call send_no_quote. Call exactly one tool."
        )
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": "You are a strict evidence extractor. Never repair, paraphrase, translate, or invent a quote."}, {"role": "user", "content": user}],
            tools=TOOLS, tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
        encoded = tokenizer(prompt, return_tensors="pt")
        started = time.monotonic()
        with torch.inference_mode():
            generated = qwen.generate(
                **encoded,
                max_new_tokens=int(protocol["quote_extractor"]["max_new_tokens"]),
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                stopping_criteria=[StopAfterToolCall(int(encoded.input_ids.shape[1]))],
            )
        raw = tokenizer.decode(generated[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
        parsed = parse_quote_tool(raw, sources, maximum_quote)
        row = {
            "question_id": candidate["question_id"],
            "card_id": candidate["card_id"],
            "human_grounded": bool(candidate["is_expected_chat"]),
            "claim": candidate["claim"],
            "sources": sources,
            "input_tokens": int(encoded.input_ids.shape[1]),
            "quote_runtime_seconds": round(time.monotonic() - started, 3),
            "raw": raw,
            **parsed,
        }
        result["rows"].append(row)
        private_write(args.output, result)
        print(json.dumps({"question_id": row["question_id"], "grounded": row["human_grounded"], "quote_receipt": row["quote_receipt"], "seconds": row["quote_runtime_seconds"]}), flush=True)
    del qwen

    result["status"] = "running_nli"
    private_write(args.output, result)
    nli_spec = protocol["nli"]
    nli_tokenizer = AutoTokenizer.from_pretrained(nli_spec["repository"], revision=nli_spec["revision"], local_files_only=True)
    nli_model = AutoModelForSequenceClassification.from_pretrained(
        nli_spec["repository"], revision=nli_spec["revision"], local_files_only=True, dtype=torch.float32
    ).eval()
    for row in result["rows"]:
        if row["quote_receipt"] != "EXACT_QUOTE":
            row["nli"] = None
            row["accepted"] = False
            continue
        source = row["sources"][row["source_id"]]
        window, _ = centered_window(nli_tokenizer, source, row["quote"], row["claim"], int(nli_spec["maximum_pair_tokens"]))
        encoded = nli_tokenizer(window, row["claim"], return_tensors="pt", truncation="only_first", max_length=int(nli_spec["maximum_pair_tokens"]))
        with torch.inference_mode():
            probabilities = torch.softmax(nli_model(**encoded).logits[0], dim=-1)
        scores = {nli_model.config.id2label[index].lower(): round(float(value), 8) for index, value in enumerate(probabilities)}
        decision = max(scores, key=scores.get)
        row["context_window"] = window
        row["nli"] = {"decision": decision, "probabilities": scores, "input_tokens": int(encoded["input_ids"].shape[-1])}
        row["accepted"] = decision == "entailment"
    grounded = [row for row in result["rows"] if row["human_grounded"]]
    unsupported = [row for row in result["rows"] if not row["human_grounded"]]
    summary = {
        "candidates": len(result["rows"]),
        "exact_quotes": sum(row["quote_receipt"] == "EXACT_QUOTE" for row in result["rows"]),
        "no_quote": sum(row["quote_receipt"] == "NO_QUOTE" for row in result["rows"]),
        "malformed": sum(row["quote_receipt"] == "ERROR" for row in result["rows"]),
        "grounded": len(grounded),
        "grounded_accepted": sum(row["accepted"] for row in grounded),
        "unsupported": len(unsupported),
        "unsupported_accepted": sum(row["accepted"] for row in unsupported),
    }
    result["summary"] = summary
    result["status"] = "awaiting_private_human_review"
    private_write(args.output, result)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
