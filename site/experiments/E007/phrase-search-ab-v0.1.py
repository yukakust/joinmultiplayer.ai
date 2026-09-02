#!/usr/bin/env python3
"""Private local A/B: exact-anchor search versus corpus-derived phrase search."""

from __future__ import annotations

import argparse
import collections
import html
import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "desktop"))

from pocket_i_app.bridge import MemoryRuntime  # noqa: E402
from pocket_i_core.retrieval import words  # noqa: E402


BASE_PATH = Path(__file__).with_name("anchor-search-ab-v0.1.py")
BASE_SPEC = importlib.util.spec_from_file_location("anchor_search_ab_v01", BASE_PATH)
assert BASE_SPEC and BASE_SPEC.loader
BASE = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE)


STOPWORDS = frozenset(
    "a an and are as at be been but by can could did do does for from had has have how i if in into is it "
    "may might must not of on or our should so than that the their them then there these they this those to "
    "was we were what when where which who why will with would you your".split()
)


def _query_ngrams(question: str) -> tuple[tuple[str, ...], ...]:
    tokens = words(question)
    result = set()
    for width in (2, 3):
        for start in range(len(tokens) - width + 1):
            phrase = tuple(tokens[start : start + width])
            if sum(token not in STOPWORDS for token in phrase) >= 2:
                result.add(phrase)
    return tuple(sorted(result))


def corpus_phrase_scores(index, question: str):
    """Score exact 2/3-token phrases selected from the query, never a domain list."""
    candidates = set(_query_ngrams(question))
    matches: list[set[tuple[str, ...]]] = []
    frequency: collections.Counter[tuple[str, ...]] = collections.Counter()
    for tokens in index._tokenized:
        found = set()
        for width in (2, 3):
            found.update(
                phrase
                for start in range(len(tokens) - width + 1)
                if (phrase := tuple(tokens[start : start + width])) in candidates
            )
        matches.append(found)
        frequency.update(found)
    count = max(1, len(index._tokenized))
    usable = {
        phrase: len(phrase) * math.log(1 + count / frequency[phrase])
        for phrase in candidates
        if frequency[phrase] and frequency[phrase] <= max(10, count // 100)
    }
    scores = [sum(usable[phrase] for phrase in found if phrase in usable) for found in matches]
    return tuple(" ".join(phrase) for phrase in sorted(usable)), scores


def phrase_route(index, question: str, top_k: int = 5):
    anchor_route, anchors, anchor_scores = BASE.candidate_route(
        index, question, top_k=len(index._conversation_ids)
    )
    anchor_rank = {item: rank for rank, item in enumerate(anchor_route, 1)}
    phrases, phrase_scores = corpus_phrase_scores(index, question)
    chat_phrase = {item: 0.0 for item in index._conversation_ids}
    for conversation_id, score in zip(index._message_conversations, phrase_scores):
        chat_phrase[conversation_id] = max(chat_phrase[conversation_id], score)
    matching = sorted(
        (item for item in chat_phrase if chat_phrase[item] > 0),
        key=lambda item: (-chat_phrase[item], item),
    )
    phrase_rank = {item: rank for rank, item in enumerate(matching, 1)}
    score = {
        item: 1 / (60 + anchor_rank[item])
        + (4 / (20 + phrase_rank[item]) if item in phrase_rank else 0)
        for item in anchor_route
    }
    routed = tuple(sorted(anchor_route, key=lambda item: (-score[item], anchor_rank[item]))[:top_k])
    combined_scores = [anchor + phrase for anchor, phrase in zip(anchor_scores, phrase_scores)]
    return routed, anchors, phrases, combined_scores


def render_html(results) -> str:
    articles = []
    for number, result in enumerate(results, 1):
        articles.append(
            f"<article><h2>{number}. {html.escape(result['question'])}</h2>"
            f"<p class='anchors'>Technical anchors: {html.escape(', '.join(result['anchors']) or 'none')}</p>"
            f"<p class='phrases'>Corpus-found phrases: {html.escape(', '.join(result['phrases']) or 'none')}</p>"
            f"<div class='columns'>{BASE.render_column('B · TECHNICAL ANCHORS', result['anchor'])}"
            f"{BASE.render_column('C · + AUTOMATIC PHRASES', result['phrase'])}</div></article>"
        )
    return """<!doctype html><html><head><meta charset='utf-8'><title>Pocket i phrase search A/B</title><style>
body{font:16px system-ui;background:#111;color:#eee;margin:0;padding:32px}main{max-width:1800px;margin:auto}
h1{margin-bottom:6px}.warning{color:#ff9d55}.columns{display:grid;grid-template-columns:1fr 1fr;gap:20px}
article{border-top:1px solid #555;margin-top:32px;padding-top:20px}section{min-width:0}details{border:1px solid #555;margin:10px 0;padding:12px;background:#181818}
summary{cursor:pointer;font-weight:700}.snippet{border-left:3px solid #d66b22;padding:8px 12px;margin:12px 0;background:#0c0c0c}
.snippet small{display:block;color:#e99a62;margin-top:4px}.snippet p{white-space:pre-wrap;overflow-wrap:anywhere}.anchors{color:#ff9d55}.phrases{color:#9bd27d}
@media(max-width:900px){.columns{grid-template-columns:1fr}}
</style></head><body><main><h1>Pocket i · private phrase-search A/B</h1>
<p class='warning'>PRIVATE — contains excerpts from your local conversations. Do not upload this file.</p>
<p>B is the accepted technical-anchor search. C adds only automatically discovered rare 2–3 word phrases from each question. No Qwen or DeBERTa was used.</p>""" + "".join(articles) + "</main></body></html>"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=BASE._default_data_dir())
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
    index, library = runtime.index, runtime.library
    results = []
    for number, question in enumerate(BASE.QUESTIONS, 1):
        print(f"Comparing question {number}/{len(BASE.QUESTIONS)}…", flush=True)
        anchor_ids, anchors, anchor_scores = BASE.candidate_route(index, question)
        anchor_hits = BASE.candidate_hits(index, question, anchor_ids, anchor_scores)
        phrase_ids, _anchors, phrases, combined_scores = phrase_route(index, question)
        phrase_hits = BASE.candidate_hits(index, question, phrase_ids, combined_scores)
        results.append({
            "question": question,
            "anchors": list(anchors),
            "phrases": list(phrases),
            "anchor": BASE.visible_result(library, question, anchor_ids, anchor_hits, anchors),
            "phrase": BASE.visible_result(library, question, phrase_ids, phrase_hits, anchors),
        })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = args.output_dir / f"Pocket-i-phrase-search-AB-{stamp}-private.json"
    html_path = args.output_dir / f"Pocket-i-phrase-search-AB-{stamp}-private.html"
    payload = {
        "schema_version": "e007-phrase-search-ab-private-v0.1",
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
