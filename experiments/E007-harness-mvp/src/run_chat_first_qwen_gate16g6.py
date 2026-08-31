#!/usr/bin/env python3
"""Run the locked E007 Gate 16G.6 chat-first local retrieval pipeline."""

from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import math
import os
import re
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/chat-first-qwen-gate16g6-protocol-v0.1.json"
QUESTIONS = ROOT / "site/experiments/E007/whole-chat-index-protocol-v0.1.json"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL = "Qwen/Qwen3-8B"
REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)

TOOLS = [
    {"type":"function","function":{
        "name":"send_found",
        "description":"Return a useful answer that is directly supported by the supplied conversation context.",
        "parameters":{"type":"object","properties":{
            "claim":{"type":"string"},
            "evidence_message_ids":{"type":"array","minItems":1,"maxItems":4,"items":{"type":"string"}}
        },"required":["claim","evidence_message_ids"]}
    }},
    {"type":"function","function":{
        "name":"send_empty",
        "description":"Use when the supplied conversation context does not contain a useful answer.",
        "parameters":{"type":"object","properties":{},"additionalProperties":False}
    }},
]


def words(text: str) -> list[str]:
    return [item.casefold() for item in TOKEN.findall(text)]


def bm25_scores(documents: list[str], query: str, k1: float = 1.5, b: float = 0.75) -> list[float]:
    tokenized = [words(document) for document in documents]
    lengths = [len(document) for document in tokenized]
    average = sum(lengths) / len(lengths) if lengths else 1.0
    frequencies = [collections.Counter(document) for document in tokenized]
    document_frequency = collections.Counter()
    for frequency in frequencies:
        document_frequency.update(frequency.keys())
    count = len(documents)
    scores = []
    for length, frequency in zip(lengths, frequencies):
        score = 0.0
        for term, query_frequency in collections.Counter(words(query)).items():
            occurrences = frequency.get(term, 0)
            if not occurrences:
                continue
            present = document_frequency[term]
            inverse = math.log(1 + (count - present + 0.5) / (present + 0.5))
            denominator = occurrences + k1 * (1 - b + b * length / average)
            score += query_frequency * inverse * occurrences * (k1 + 1) / denominator
        scores.append(score)
    return scores


def cosine(left, right) -> float:
    numerator = float(left @ right)
    denominator = math.sqrt(float(left @ left)) * math.sqrt(float(right @ right))
    return numerator / denominator if denominator else 0.0


def ranked_indices(values: list[float], tie_breakers: list[str]) -> list[int]:
    return sorted(range(len(values)), key=lambda index: (-values[index], tie_breakers[index]))


def fuse(first: list[str], second: list[str], limit: int) -> list[str]:
    first_rank = {item: rank for rank, item in enumerate(first, 1)}
    second_rank = {item: rank for rank, item in enumerate(second, 1)}
    items = set(first_rank) | set(second_rank)
    return sorted(items, key=lambda item: (
        -(1 / (60 + first_rank[item]) if item in first_rank else 0)
        -(1 / (60 + second_rank[item]) if item in second_rank else 0),
        item,
    ))[:limit]


def render_messages(messages: list[dict]) -> str:
    return "\n\n".join(
        f'<message id="{message["id"]}" role="{message["role"]}">\n{html.escape(message["text"])}\n</message>'
        for message in messages
    )


def parse_tool(raw: str, valid_ids: set[str]) -> dict:
    calls = re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", raw, re.DOTALL)
    if len(calls) != 1:
        return {"receipt":"ERROR","error":f"expected one complete tool call, got {len(calls)}"}
    try:
        call = json.loads(calls[0])
    except json.JSONDecodeError as error:
        return {"receipt":"ERROR","error":f"invalid tool JSON: {error}"}
    name, arguments = call.get("name"), call.get("arguments")
    if name == "send_empty" and isinstance(arguments, dict) and not arguments:
        return {"receipt":"EMPTY","claim":None,"evidence_message_ids":[],"coordinates_valid":True}
    if name != "send_found" or not isinstance(arguments, dict):
        return {"receipt":"ERROR","error":"unknown tool call"}
    claim, evidence = arguments.get("claim"), arguments.get("evidence_message_ids")
    if not isinstance(claim, str) or not claim.strip() or not isinstance(evidence, list) or not 1 <= len(evidence) <= 4:
        return {"receipt":"ERROR","error":"malformed FOUND payload"}
    valid = all(isinstance(item, str) and item in valid_ids for item in evidence)
    return {"receipt":"FOUND","claim":claim.strip(),"evidence_message_ids":evidence,"coordinates_valid":valid}


def greedily_select_areas(messages: list[dict], candidate_ids: list[str], tokenizer, budget: int) -> list[dict]:
    positions = {message["id"]: index for index, message in enumerate(messages)}
    selected: set[int] = set()
    for candidate_id in candidate_ids:
        center = positions[candidate_id]
        area = {index for index in (center - 1, center, center + 1) if 0 <= index < len(messages)}
        proposed = sorted(selected | area)
        if len(tokenizer.encode(render_messages([messages[index] for index in proposed]), add_special_tokens=False)) <= budget:
            selected.update(area)
            continue
        if not selected:
            single_tokens = len(tokenizer.encode(render_messages([messages[center]]), add_special_tokens=False))
            if single_tokens > budget:
                raise RuntimeError(f"One complete candidate message exceeds the {budget}-token long-chat budget")
            selected.add(center)
    if not selected:
        raise RuntimeError("Long-chat area selection produced no messages")
    return [messages[index] for index in sorted(selected)]


def private_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    import fastembed
    import numpy as np
    import torch
    from fastembed import TextEmbedding
    from transformers import AutoModelForCausalLM, AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--index-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--route-only", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite preserved result: {args.output}")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["queries"]
    source_bytes = args.payload.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != protocol["source"]["private_snapshot_sha256"]:
        raise RuntimeError("Private source snapshot does not match the locked protocol")
    payload = json.loads(source_bytes)
    chats = {f'{payload["node"]}-C{index:04d}': chat for index, chat in enumerate(payload["conversations"], 1)}
    coordinates, texts, card_ids = [], [], []
    for card_id, chat in chats.items():
        for message in chat["messages"]:
            coordinates.append([card_id, message["id"]])
            texts.append(message["text"])
            card_ids.append(card_id)
    snapshot = protocol["source"]["private_snapshot_sha256"]
    embedder = TextEmbedding(model_name=EMBED_MODEL, cache_dir=str(args.cache_dir), threads=args.threads)
    if args.index_cache.exists():
        cache = np.load(args.index_cache, allow_pickle=False)
        metadata = json.loads(str(cache["metadata"].item()))
        if metadata != {"model":EMBED_MODEL,"source":snapshot,"coordinates":coordinates}:
            raise RuntimeError("Persisted index does not match the locked source")
        vectors = cache["vectors"]
        index_built = False
    else:
        vectors = np.asarray(list(embedder.embed(texts, batch_size=32)), dtype=np.float32)
        args.index_cache.parent.mkdir(parents=True, exist_ok=True)
        metadata = json.dumps({"model":EMBED_MODEL,"source":snapshot,"coordinates":coordinates}, ensure_ascii=False, separators=(",",":"))
        np.savez_compressed(args.index_cache, vectors=vectors, metadata=np.asarray(metadata))
        index_built = True
    query_vectors = list(embedder.embed([item["question"] for item in questions], batch_size=10))
    routes = []
    for question, query_vector in zip(questions, query_vectors):
        lexical_message = bm25_scores(texts, question["question"])
        dense_message = [cosine(query_vector, vector) for vector in vectors]
        best_lexical, best_dense = {}, {}
        for index, card_id in enumerate(card_ids):
            best_lexical[card_id] = max(best_lexical.get(card_id, float("-inf")), lexical_message[index])
            best_dense[card_id] = max(best_dense.get(card_id, float("-inf")), dense_message[index])
        lexical_chats = sorted(best_lexical, key=lambda card: (-best_lexical[card], card))[:5]
        dense_chats = sorted(best_dense, key=lambda card: (-best_dense[card], card))[:5]
        routed = fuse(lexical_chats, dense_chats, 3)
        routes.append({"id":question["id"],"question":question["question"],"expected_chat":question["gold_card_id"],"routed_chats":routed,"expected_chat_routed":question["gold_card_id"] in routed})
    del embedder

    if args.route_only:
        private_write(args.output, {
            "schema_version":"0.1-private","experiment":"E007","gate":"16G.6-routing",
            "status":"completed_passed" if all(route["expected_chat_routed"] for route in routes) else "completed_failed",
            "index_built_this_run":index_built,
            "summary":{"questions":len(routes),"expected_chat_routed":sum(route["expected_chat_routed"] for route in routes)},
            "routes":routes,
        })
        print(json.dumps({"questions":len(routes),"expected_chat_routed":sum(route["expected_chat_routed"] for route in routes),"index_built_this_run":index_built}),flush=True)
        return

    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, local_files_only=True)
    torch.set_num_threads(args.threads)
    model = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION, local_files_only=True, dtype=torch.bfloat16).eval()
    result = {"schema_version":"0.1-private","experiment":"E007","gate":"16G.6","status":"running","index_built_this_run":index_built,"routes":routes,"rows":[]}
    private_write(args.output, result)
    query_vector_by_id = {item["id"]: vector for item, vector in zip(questions, query_vectors)}
    for route in routes:
        for route_rank, card_id in enumerate(route["routed_chats"], 1):
            messages = chats[card_id]["messages"]
            whole = render_messages(messages)
            whole_tokens = len(tokenizer.encode(whole, add_special_tokens=False))
            if whole_tokens <= 10000:
                supplied = messages
                branch = "whole_short_chat"
            else:
                indices = [index for index, candidate_card in enumerate(card_ids) if candidate_card == card_id]
                ids = [coordinates[index][1] for index in indices]
                documents = [texts[index] for index in indices]
                dense_values = [cosine(query_vector_by_id[route["id"]], vectors[index]) for index in indices]
                lexical_values = bm25_scores(documents, route["question"])
                dense_ids = [ids[index] for index in ranked_indices(dense_values, ids)[:5]]
                lexical_ids = [ids[index] for index in ranked_indices(lexical_values, ids)[:5]]
                supplied = greedily_select_areas(messages, fuse(lexical_ids, dense_ids, 10), tokenizer, 10000)
                branch = "selected_long_chat_areas"
            context = render_messages(supplied)
            user = (
                f'QUESTION:\n{route["question"]}\n\nCONVERSATION CONTEXT:\n{context}\n\n'
                "Use only the supplied context. If it directly contains useful information that answers the question, call send_found with a short plain-language claim and the smallest supporting message IDs. Otherwise call send_empty. Call exactly one tool."
            )
            prompt = tokenizer.apply_chat_template(
                [{"role":"system","content":"You are a faithful local Pocket i reader. Never copy the question as evidence, never use outside knowledge, and never invent a source."},{"role":"user","content":user}],
                tools=TOOLS, tokenize=False, add_generation_prompt=True, enable_thinking=False,
            )
            encoded = tokenizer(prompt, return_tensors="pt")
            started = time.monotonic()
            with torch.inference_mode():
                generated = model.generate(**encoded, max_new_tokens=256, do_sample=False, pad_token_id=tokenizer.eos_token_id)
            raw = tokenizer.decode(generated[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
            parsed = parse_tool(raw, {message["id"] for message in supplied})
            row = {
                "question_id":route["id"],"route_rank":route_rank,"card_id":card_id,
                "is_expected_chat":card_id == route["expected_chat"],"branch":branch,
                "whole_chat_tokens":whole_tokens,"supplied_messages":len(supplied),
                "input_tokens":int(encoded.input_ids.shape[1]),"runtime_seconds":round(time.monotonic()-started,3),
                "raw":raw,**parsed,
            }
            result["rows"].append(row)
            private_write(args.output, result)
            print(json.dumps({key:row[key] for key in ("question_id","route_rank","is_expected_chat","branch","receipt","coordinates_valid","runtime_seconds") if key in row}),flush=True)
    expected_rows = [row for row in result["rows"] if row["is_expected_chat"]]
    result["mechanical_summary"] = {
        "questions":len(routes),
        "expected_chat_routed":sum(route["expected_chat_routed"] for route in routes),
        "expected_chat_found":sum(row["receipt"] == "FOUND" for row in expected_rows),
        "expected_chat_valid_coordinates":sum(row.get("coordinates_valid") is True for row in expected_rows),
        "distractor_false_found":sum(row["receipt"] == "FOUND" for row in result["rows"] if not row["is_expected_chat"]),
        "whole_short_chat_reads":sum(row["branch"] == "whole_short_chat" for row in result["rows"]),
        "selected_long_chat_area_reads":sum(row["branch"] == "selected_long_chat_areas" for row in result["rows"]),
    }
    result["status"] = "awaiting_private_human_review"
    private_write(args.output, result)


if __name__ == "__main__":
    main()
