#!/usr/bin/env python3
"""Private local A/B: current retrieval versus exact-anchor-aware retrieval."""

from __future__ import annotations

import argparse
import collections
import html
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "desktop"))

from pocket_i_app.bridge import MemoryRuntime, _question_centered_excerpt  # noqa: E402
from pocket_i_core.retrieval import _cosine  # noqa: E402


QUESTIONS = (
    "Why did we add DeBERTa to the Pocket i harness, and why could it not be the only judge?",
    "What relay rate limit was proposed to slow the spread of malicious messages between new recipients?",
    "Why should passive room messages not always fail closed and ask the user for permission?",
    "Why was the /x share feature not reachable even though its application code was already deployed?",
)

SLASH_ANCHOR = re.compile(r"(?<![A-Za-z0-9])/(?:[A-Za-z0-9._~:@%+\-=]+(?:/[A-Za-z0-9._~:@%+\-=]+)*)")
TOKEN_ANCHOR = re.compile(r"\b[A-Za-z][A-Za-z0-9_.-]*[A-Za-z0-9]\b|\b\d+(?:\.\d+)*\b")


def technical_anchors(text: str) -> tuple[str, ...]:
    result = {item.casefold() for item in SLASH_ANCHOR.findall(text)}
    for token in TOKEN_ANCHOR.findall(text):
        mixed_case = any(char.isupper() for char in token[1:])
        structured = any(char.isdigit() for char in token) or any(char in token for char in "_.-")
        if mixed_case or structured or token.isdigit():
            result.add(token.casefold())
    return tuple(sorted(result))


def _default_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "pocket-i-desktop" / "memory"
    return Path.home() / ".config" / "pocket-i-desktop" / "memory"


def candidate_route(index, question: str, top_k: int = 5):
    baseline = index.route(question, top_k=len(index._conversation_ids)).conversation_ids
    baseline_rank = {item: rank for rank, item in enumerate(baseline, 1)}
    query_anchors = technical_anchors(question)
    message_anchor_sets = tuple(set(technical_anchors(text)) for text in index._texts)
    anchor_document_frequency = collections.Counter(
        anchor for anchors in message_anchor_sets for anchor in anchors
    )
    count = max(1, len(message_anchor_sets))
    message_anchor_scores = []
    for anchors in message_anchor_sets:
        overlap = set(query_anchors) & anchors
        message_anchor_scores.append(sum(math.log(1 + count / anchor_document_frequency[item]) for item in overlap))
    chat_anchor = {item: 0.0 for item in index._conversation_ids}
    for conversation_id, score in zip(index._message_conversations, message_anchor_scores):
        chat_anchor[conversation_id] = max(chat_anchor[conversation_id], score)
    matching = sorted((item for item in chat_anchor if chat_anchor[item] > 0), key=lambda item: (-chat_anchor[item], item))
    anchor_rank = {item: rank for rank, item in enumerate(matching, 1)}
    score = {
        item: 1 / (60 + baseline_rank[item]) + (4 / (20 + anchor_rank[item]) if item in anchor_rank else 0)
        for item in baseline
    }
    routed = tuple(sorted(baseline, key=lambda item: (-score[item], baseline_rank[item]))[:top_k])
    return routed, query_anchors, message_anchor_scores


def current_hits(index, question: str, conversation_ids):
    return index.context_hits(question, conversation_ids, per_conversation=2, limit=10)


def candidate_hits(index, question: str, conversation_ids, anchor_scores, per_conversation: int = 5):
    lexical = index._bm25(question)
    query_vector = tuple(float(value) for value in tuple(index._embed((question,)))[0])
    neural = [_cosine(query_vector, vector) for vector in index._vectors]
    result = []
    for conversation_id in conversation_ids:
        candidates = [position for position, item in enumerate(index._message_conversations) if item == conversation_id]
        channels = []
        if any(anchor_scores[item] > 0 for item in candidates):
            channels.append(sorted(candidates, key=lambda item: (-anchor_scores[item], item)))
        channels.extend((
            sorted(candidates, key=lambda item: (-lexical[item], item)),
            sorted(candidates, key=lambda item: (-neural[item], item)),
        ))
        selected = []
        for offset in range(per_conversation):
            for channel in channels:
                if offset < len(channel) and channel[offset] not in selected:
                    selected.append(channel[offset])
                    if len(selected) == per_conversation:
                        break
            if len(selected) == per_conversation:
                break
        result.extend((conversation_id, index._message_positions[item]) for item in selected)
    return tuple(result)


def visible_result(library, question: str, conversation_ids, hits, query_anchors):
    by_id = {item.conversation_id: item for item in library.conversations}
    hit_map = collections.defaultdict(list)
    for conversation_id, message_position in hits:
        hit_map[conversation_id].append(message_position)
    rows = []
    for rank, conversation_id in enumerate(conversation_ids, 1):
        conversation = by_id[conversation_id]
        messages = []
        for position in hit_map[conversation_id]:
            message = conversation.messages[position]
            messages.append({
                "position": position + 1,
                "role": message.role,
                "matched_anchors": sorted(set(query_anchors) & set(technical_anchors(message.text))),
                "excerpt": _question_centered_excerpt(message.text, question, limit=900),
            })
        rows.append({
            "rank": rank,
            "conversation": conversation_id[:12],
            "source": conversation.source,
            "total_messages": len(conversation.messages),
            "messages": messages,
        })
    return rows


def render_column(title: str, rows) -> str:
    cards = []
    for row in rows:
        snippets = "".join(
            f"<div class='snippet'><b>Message {item['position']} · {html.escape(item['role'])}</b>"
            f"<small>anchors: {html.escape(', '.join(item['matched_anchors']) or 'none')}</small>"
            f"<p>{html.escape(item['excerpt'])}</p></div>"
            for item in row["messages"]
        )
        cards.append(
            f"<details{' open' if row['rank'] == 1 else ''}><summary>{row['rank']}. {html.escape(row['source'])} · "
            f"chat {html.escape(row['conversation'])} · {row['total_messages']} messages</summary>{snippets}</details>"
        )
    return f"<section><h3>{html.escape(title)}</h3>{''.join(cards)}</section>"


def render_html(results) -> str:
    questions = []
    for number, result in enumerate(results, 1):
        questions.append(
            f"<article><h2>{number}. {html.escape(result['question'])}</h2>"
            f"<p class='anchors'>Exact anchors: {html.escape(', '.join(result['anchors']) or 'none')}</p>"
            f"<div class='columns'>{render_column('A · CURRENT', result['current'])}"
            f"{render_column('B · ANCHOR-AWARE', result['candidate'])}</div></article>"
        )
    return """<!doctype html><html><head><meta charset='utf-8'><title>Pocket i search A/B</title><style>
body{font:16px system-ui;background:#111;color:#eee;margin:0;padding:32px}main{max-width:1800px;margin:auto}
h1{margin-bottom:6px}.warning{color:#ff9d55}.columns{display:grid;grid-template-columns:1fr 1fr;gap:20px}
article{border-top:1px solid #555;margin-top:32px;padding-top:20px}section{min-width:0}details{border:1px solid #555;margin:10px 0;padding:12px;background:#181818}
summary{cursor:pointer;font-weight:700}.snippet{border-left:3px solid #d66b22;padding:8px 12px;margin:12px 0;background:#0c0c0c}
.snippet small{display:block;color:#e99a62;margin-top:4px}.snippet p{white-space:pre-wrap;overflow-wrap:anywhere}.anchors{color:#ff9d55}
@media(max-width:900px){.columns{grid-template-columns:1fr}}
</style></head><body><main><h1>Pocket i · private search A/B</h1>
<p class='warning'>PRIVATE — contains excerpts from your local conversations. Do not upload this file.</p>
<p>A is the current app search. B adds exact technical anchors and shows up to five candidate messages per chat. No Qwen or DeBERTa was used.</p>""" + "".join(questions) + "</main></body></html>"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=_default_data_dir())
    parser.add_argument("--output-dir", type=Path, default=Path.home() / "Downloads")
    args = parser.parse_args()
    print("Reading the same local Codex and Claude library…", flush=True)
    runtime = MemoryRuntime(
        data_dir=args.data_dir,
        on_progress=lambda value: print(
            f"{value.get('phase')} {value.get('completed', '')}/{value.get('total', '')}",
            file=sys.stderr,
            flush=True,
        ),
    )
    runtime.connect()
    index = runtime.index
    library = runtime.library
    results = []
    for number, question in enumerate(QUESTIONS, 1):
        print(f"Comparing question {number}/{len(QUESTIONS)}…", flush=True)
        current_route = index.route(question, top_k=5).conversation_ids
        current = current_hits(index, question, current_route)
        candidate_route_ids, anchors, anchor_scores = candidate_route(index, question)
        candidate = candidate_hits(index, question, candidate_route_ids, anchor_scores)
        results.append({
            "question": question,
            "anchors": list(anchors),
            "current": visible_result(
                library,
                question,
                current_route,
                tuple((item.conversation_id, item.message_position) for item in current),
                anchors,
            ),
            "candidate": visible_result(library, question, candidate_route_ids, candidate, anchors),
        })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = args.output_dir / f"Pocket-i-anchor-search-AB-{stamp}-private.json"
    html_path = args.output_dir / f"Pocket-i-anchor-search-AB-{stamp}-private.html"
    payload = {
        "schema_version": "e007-anchor-search-ab-private-v0.1",
        "warning": "PRIVATE: contains local conversation excerpts; never upload automatically",
        "questions": results,
    }
    descriptor = os.open(json_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    descriptor = os.open(html_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(render_html(results))
    print(f"PRIVATE_JSON: {json_path}")
    print(f"PRIVATE_HTML: {html_path}")
    if sys.platform == "darwin":
        os.spawnlp(os.P_NOWAIT, "open", "open", str(html_path))


if __name__ == "__main__":
    main()
