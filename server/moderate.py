#!/usr/bin/env python3
"""Small SSH-side moderation CLI for the contribution inbox."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from server import init_db, record_publication_event


STATUSES = ("pending", "needs_changes", "public", "withdrawn")


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
    args = parser.parse_args()

    init_db(args.db)
    with sqlite3.connect(args.db) as db:
        db.row_factory = sqlite3.Row
        if args.command == "list":
            rows = db.execute(
                "SELECT public_id, door, author, parent_public_id, status, created_at "
                "FROM contributions ORDER BY row_id DESC LIMIT 100"
            ).fetchall()
            for row in rows:
                print("\t".join(str(row[key]) for key in row.keys()))
        elif args.command == "show":
            row = db.execute(
                "SELECT public_id, door, payload, author, parent_public_id, relation, status, review_note, created_at, updated_at "
                "FROM contributions WHERE public_id = ?",
                (args.id,),
            ).fetchone()
            if row is None:
                raise SystemExit("record not found")
            value = dict(row)
            value["payload"] = json.loads(value["payload"])
            print(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            cursor = db.execute(
                "UPDATE contributions SET status = ?, review_note = ?, updated_at = ? WHERE public_id = ?",
                (args.value, args.note, now(), args.id),
            )
            if cursor.rowcount != 1:
                raise SystemExit("record not found")
            if args.value == "public":
                record_publication_event(db, args.id)
            print(f"{args.id}: {args.value}")


if __name__ == "__main__":
    main()
