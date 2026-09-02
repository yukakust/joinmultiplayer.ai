#!/usr/bin/env python3
"""Mirror the canonical intercepted question Q0001 into the new server's DB.

The game's first move ("take Q0001") posts a contribution with parent_id=Q0001.
The new server validates parents against its own questions table, while the
question itself lives in the old site's public corpus — so without this seed
the golden path 400s with "parent record is not public".

Idempotent: skips if Q0001 already exists. Usage:
    python3 seed_q0001.py --db /path/to/db.sqlite3
"""

import argparse
import hashlib
import json
import secrets
import sqlite3
import urllib.request
from datetime import datetime, timezone

CORPUS_URL = "https://joinmultiplayer.ai/api/public/questions.json"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def fetch_q0001() -> dict:
    request = urllib.request.Request(
        CORPUS_URL, headers={"User-Agent": "joinmultiplayer-seed/1.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        corpus = json.load(response)
    items = corpus if isinstance(corpus, list) else corpus.get("questions", [])
    for item in items:
        if item.get("public_id") == "Q0001":
            return item
    raise SystemExit("Q0001 not found in the public corpus")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    args = parser.parse_args()

    entry = fetch_q0001()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with sqlite3.connect(args.db) as db:
        if db.execute("SELECT 1 FROM questions WHERE public_id = 'Q0001'").fetchone():
            print("Q0001 already seeded")
            for table in ("contributions", "questions"):
                db.execute("UPDATE sqlite_sequence SET seq = MAX(seq, 100) WHERE name = ?", (table,))
            return
        db.execute(
            "INSERT INTO questions "
            "(public_id, token_hash, payload, author, source_trace_id, source_event_id, "
            " relation, status, research_status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'public', 'open', ?, ?)",
            (
                "Q0001",
                token_hash(secrets.token_urlsafe(32)),
                json.dumps(entry["payload"], ensure_ascii=False),
                entry.get("author", "Morrow"),
                entry.get("source_trace_id", "T0002"),
                entry.get("source_event_id", ""),
                entry.get("relation", "derives_from"),
                entry.get("created_at", now),
                now,
            ),
        )
    with sqlite3.connect(args.db) as db:
        # keep new-server ids disjoint from the old public corpus (T0001–T00xx, Q0001)
        for table in ("contributions", "questions"):
            db.execute(
                "INSERT INTO sqlite_sequence(name, seq) SELECT ?, 100 WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name = ?)",
                (table, table),
            )
            db.execute("UPDATE sqlite_sequence SET seq = MAX(seq, 100) WHERE name = ?", (table,))
    print("Q0001 seeded as public; id sequences start above 100")


if __name__ == "__main__":
    main()
