#!/usr/bin/env python3
"""Small SSH-side moderation CLI for the research inbox."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from server import init_db, record_publication_event, record_question_publication_event


STATUSES = ("pending", "needs_changes", "public", "withdrawn")
RESEARCH_STATUSES = ("open", "answered", "disputed", "withdrawn")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("/var/lib/joinmultiplayer/contributions.sqlite3"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    show = subparsers.add_parser("show")
    show.add_argument("id")
    status = subparsers.add_parser("status")
    status.add_argument("id")
    status.add_argument("value", choices=STATUSES)
    status.add_argument("--note", default="")
    research_status = subparsers.add_parser("research-status")
    research_status.add_argument("id")
    research_status.add_argument("value", choices=RESEARCH_STATUSES)
    args = parser.parse_args()

    init_db(args.db)
    with sqlite3.connect(args.db) as db:
        db.row_factory = sqlite3.Row
        if args.command == "list":
            rows = db.execute(
                "SELECT public_id, object_type, method, author, source_id, status, created_at FROM ("
                "SELECT public_id, 'trace' AS object_type, door AS method, author, "
                "parent_public_id AS source_id, status, created_at FROM contributions "
                "UNION ALL "
                "SELECT public_id, 'question' AS object_type, '' AS method, author, "
                "source_trace_id AS source_id, status, created_at FROM questions"
                ") ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
            for row in rows:
                print("\t".join(str(row[key]) for key in row.keys()))
        elif args.command == "show":
            if args.id.upper().startswith("Q"):
                row = db.execute(
                    "SELECT public_id, payload, author, source_trace_id, source_event_id, "
                    "relation, status, research_status, review_note, created_at, updated_at "
                    "FROM questions WHERE public_id = ?",
                    (args.id.upper(),),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT public_id, door, payload, author, parent_public_id, relation, "
                    "status, review_note, created_at, updated_at "
                    "FROM contributions WHERE public_id = ?",
                    (args.id.upper(),),
                ).fetchone()
            if row is None:
                raise SystemExit("record not found")
            value = dict(row)
            value["payload"] = json.loads(value["payload"])
            print(json.dumps(value, ensure_ascii=False, indent=2))
        elif args.command == "research-status":
            public_id = args.id.upper()
            if not public_id.startswith("Q"):
                raise SystemExit("research status is only available for questions")
            cursor = db.execute(
                "UPDATE questions SET research_status = ?, updated_at = ? "
                "WHERE public_id = ? AND status = 'public'",
                (args.value, now(), public_id),
            )
            if cursor.rowcount != 1:
                raise SystemExit("public question not found")
            print(f"{public_id}: {args.value}")
        else:
            public_id = args.id.upper()
            if public_id.startswith("Q"):
                if args.value == "public":
                    source = db.execute(
                        "SELECT 1 FROM questions q JOIN contributions t "
                        "ON t.public_id = q.source_trace_id "
                        "WHERE q.public_id = ? AND t.status = 'public'",
                        (public_id,),
                    ).fetchone()
                    if source is None:
                        raise SystemExit("source trace is not public")
                cursor = db.execute(
                    "UPDATE questions SET status = ?, review_note = ?, updated_at = ? "
                    "WHERE public_id = ?",
                    (args.value, args.note, now(), public_id),
                )
            else:
                if args.value == "public":
                    record = db.execute(
                        "SELECT parent_public_id FROM contributions WHERE public_id = ?",
                        (public_id,),
                    ).fetchone()
                    if record is None:
                        raise SystemExit("record not found")
                    parent_id = record["parent_public_id"]
                    if parent_id:
                        if parent_id.startswith("Q"):
                            parent = db.execute(
                                "SELECT 1 FROM questions WHERE public_id = ? AND status = 'public'",
                                (parent_id,),
                            ).fetchone()
                        else:
                            parent = db.execute(
                                "SELECT 1 FROM contributions WHERE public_id = ? AND status = 'public'",
                                (parent_id,),
                            ).fetchone()
                        if parent is None:
                            raise SystemExit("parent record is not public")
                cursor = db.execute(
                    "UPDATE contributions SET status = ?, review_note = ?, updated_at = ? "
                    "WHERE public_id = ?",
                    (args.value, args.note, now(), public_id),
                )
            if cursor.rowcount != 1:
                raise SystemExit("record not found")
            if args.value == "public":
                if public_id.startswith("Q"):
                    record_question_publication_event(db, public_id)
                else:
                    record_publication_event(db, public_id)
            print(f"{public_id}: {args.value}")


if __name__ == "__main__":
    main()
