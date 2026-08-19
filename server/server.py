#!/usr/bin/env python3
"""Small accountless research inbox for joinmultiplayer.ai."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


MAX_BODY = 512_000
MAX_ANSWER = 120_000
RATE_LIMIT = 12
RATE_WINDOW_SECONDS = 3600
ALLOWED_ORIGINS = {
    "https://joinmultiplayer.ai",
    "https://www.joinmultiplayer.ai",
    "http://localhost:8091",
    "http://127.0.0.1:8091",
}
QUESTION_NEXT_MOVES = {"answer"}
QUESTION_LANGUAGES = {"en", "ru", "und"}
PUBLIC_ID_RE = re.compile(r"^[QT][0-9]{4,}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clean_text(value: object, field: str, *, required: bool = True, limit: int = 10_000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > limit:
        raise ValueError(f"{field} is too long")
    return value


def validate_response(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("each response must be an object")
    return {
        "model": clean_text(value.get("model", ""), "model", limit=200),
        "raw": clean_text(value.get("raw", ""), "raw answer", limit=MAX_ANSWER),
        "tools": clean_text(value.get("tools", "unknown"), "tools", required=False, limit=100) or "unknown",
        "run_at": clean_text(value.get("run_at", ""), "run date", required=False, limit=40) or "unknown",
    }


def validate_author(value: dict) -> str:
    author_mode = value.get("author_mode", "anonymous")
    if author_mode not in {"anonymous", "pseudonym"}:
        raise ValueError("invalid author mode")
    if author_mode == "pseudonym":
        return clean_text(value.get("pseudonym", ""), "pseudonym", limit=80)
    return "anonymous"


def validate_submission(value: object) -> tuple[str, dict, str]:
    if not isinstance(value, dict):
        raise ValueError("submission must be an object")
    if value.get("website"):
        raise ValueError("submission rejected")
    if value.get("consent") is not True:
        raise ValueError("publication consent is required")

    door = clean_text(value.get("door", ""), "door", limit=3).lower()
    if door not in {"d04", "d06"}:
        raise ValueError("unsupported door")

    question = clean_text(value.get("question", ""), "question", limit=4_000)
    responses_value = value.get("responses")
    if not isinstance(responses_value, list) or not 1 <= len(responses_value) <= 12:
        raise ValueError("bring between 1 and 12 responses")
    responses = [validate_response(response) for response in responses_value]

    payload = {"question": question, "responses": responses}
    if door == "d06":
        payload["mistake"] = clean_text(value.get("mistake", ""), "expert observation", limit=20_000)
        payload["verification"] = clean_text(value.get("verification", ""), "verification path", limit=20_000)

    return door, payload, validate_author(value)


def validate_question_submission(value: object) -> tuple[dict[str, str], str, str]:
    if not isinstance(value, dict):
        raise ValueError("submission must be an object")
    if value.get("website"):
        raise ValueError("submission rejected")
    if value.get("consent") is not True:
        raise ValueError("publication consent is required")

    source_trace_id = clean_text(
        value.get("source_trace_id") or value.get("source_id") or value.get("parent_id") or "",
        "source trace",
        limit=40,
    ).upper()
    if not re.fullmatch(r"T[0-9]{4,}", source_trace_id):
        raise ValueError("source trace is unavailable")

    next_move = clean_text(
        value.get("next_move", "answer"), "next move", required=False, limit=20
    ).lower() or "answer"
    if next_move not in QUESTION_NEXT_MOVES:
        raise ValueError("invalid next move")

    language = clean_text(
        value.get("language", "und"), "language", required=False, limit=8
    ).lower() or "und"
    if language not in QUESTION_LANGUAGES:
        raise ValueError("invalid language")

    payload = {
        "question": clean_text(value.get("question", ""), "question", limit=4_000),
        "why_it_matters": clean_text(
            value.get("why_it_matters", ""), "why it matters", limit=12_000
        ),
        "starting_point": clean_text(
            value.get("starting_point", ""), "starting point", required=False, limit=20_000
        ),
        "sources": clean_text(
            value.get("sources", ""), "sources", required=False, limit=20_000
        ),
        "needed": clean_text(value.get("needed", ""), "needed", limit=20_000),
        "next_move": next_move,
        "language": language,
    }
    return payload, validate_author(value), source_trace_id


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS contributions (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                door TEXT NOT NULL,
                payload TEXT NOT NULL,
                author TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                review_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(contributions)")}
        if "parent_public_id" not in columns:
            db.execute("ALTER TABLE contributions ADD COLUMN parent_public_id TEXT NOT NULL DEFAULT ''")
        if "relation" not in columns:
            db.execute("ALTER TABLE contributions ADD COLUMN relation TEXT NOT NULL DEFAULT ''")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                event_type TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                links TEXT NOT NULL DEFAULT '[]',
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(event_type, object_id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL,
                author TEXT NOT NULL,
                source_trace_id TEXT NOT NULL,
                source_event_id TEXT NOT NULL DEFAULT '',
                relation TEXT NOT NULL DEFAULT 'derives_from',
                status TEXT NOT NULL DEFAULT 'pending',
                research_status TEXT NOT NULL DEFAULT 'open',
                review_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        question_columns = {row[1] for row in db.execute("PRAGMA table_info(questions)")}
        if "research_status" not in question_columns:
            db.execute(
                "ALTER TABLE questions ADD COLUMN research_status TEXT NOT NULL DEFAULT 'open'"
            )
        db.execute(
            "CREATE INDEX IF NOT EXISTS questions_public ON questions(status, row_id)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS questions_source ON questions(source_trace_id, status)"
        )
        public_ids = db.execute(
            "SELECT public_id FROM contributions WHERE status = 'public' ORDER BY row_id"
        ).fetchall()
        for (public_id,) in public_ids:
            record_publication_event(db, public_id)
        public_question_ids = db.execute(
            "SELECT public_id FROM questions WHERE status = 'public' ORDER BY row_id"
        ).fetchall()
        for (public_id,) in public_question_ids:
            record_question_publication_event(db, public_id)


def publication_event_id(db: sqlite3.Connection, object_type: str, object_id: str) -> str:
    row = db.execute(
        "SELECT event_id FROM events WHERE object_type = ? AND object_id = ? "
        "ORDER BY row_id LIMIT 1",
        (object_type, object_id),
    ).fetchone()
    return row[0] if row and row[0] else ""


def record_publication_event(db: sqlite3.Connection, public_id: str) -> None:
    db.row_factory = sqlite3.Row
    record = db.execute(
        "SELECT public_id, parent_public_id, relation, author, payload, updated_at "
        "FROM contributions WHERE public_id = ? AND status = 'public'",
        (public_id,),
    ).fetchone()
    if record is None:
        return
    payload = json.loads(record["payload"])
    links = []
    if record["parent_public_id"]:
        parent_type = "question" if record["parent_public_id"].startswith("Q") else "trace"
        link = {
            "relation": record["relation"] or "continues",
            "target_type": parent_type,
            "target_id": record["parent_public_id"],
        }
        target_event_id = publication_event_id(db, parent_type, record["parent_public_id"])
        if target_event_id:
            link["target_event_id"] = target_event_id
        links.append(link)
    event_type = {
        "continues": "trace_continued",
        "answers": "trace_answered",
    }.get(record["relation"], "trace_published")
    existing = db.execute(
        "SELECT 1 FROM events WHERE event_type = ? AND object_id = ?",
        (event_type, record["public_id"]),
    ).fetchone()
    if existing is not None:
        return
    cursor = db.execute(
        "INSERT INTO events "
        "(event_type, object_type, object_id, actor, links, payload, created_at) "
        "VALUES (?, 'trace', ?, ?, ?, ?, ?)",
        (
            event_type,
            record["public_id"],
            record["author"],
            json.dumps(links, ensure_ascii=False),
            json.dumps({"question": payload.get("question", "")}, ensure_ascii=False),
            record["updated_at"],
        ),
    )
    db.execute("UPDATE events SET event_id = ? WHERE row_id = ?", (f"E{cursor.lastrowid:06d}", cursor.lastrowid))


def record_question_publication_event(db: sqlite3.Connection, public_id: str) -> None:
    db.row_factory = sqlite3.Row
    record = db.execute(
        "SELECT public_id, source_trace_id, source_event_id, relation, author, payload, updated_at "
        "FROM questions WHERE public_id = ? AND status = 'public'",
        (public_id,),
    ).fetchone()
    if record is None:
        return
    existing = db.execute(
        "SELECT 1 FROM events WHERE event_type = 'question_opened' AND object_id = ?",
        (record["public_id"],),
    ).fetchone()
    if existing is not None:
        return
    link = {
        "relation": record["relation"] or "derives_from",
        "target_type": "trace",
        "target_id": record["source_trace_id"],
    }
    target_event_id = record["source_event_id"] or publication_event_id(
        db, "trace", record["source_trace_id"]
    )
    if target_event_id:
        link["target_event_id"] = target_event_id
        if not record["source_event_id"]:
            db.execute(
                "UPDATE questions SET source_event_id = ? WHERE public_id = ?",
                (target_event_id, record["public_id"]),
            )
    payload = json.loads(record["payload"])
    cursor = db.execute(
        "INSERT INTO events "
        "(event_type, object_type, object_id, actor, links, payload, created_at) "
        "VALUES ('question_opened', 'question', ?, ?, ?, ?, ?)",
        (
            record["public_id"],
            record["author"],
            json.dumps([link], ensure_ascii=False),
            json.dumps(
                {
                    "question": payload.get("question", ""),
                    "needed": payload.get("needed", ""),
                    "next_move": payload.get("next_move", "answer"),
                },
                ensure_ascii=False,
            ),
            record["updated_at"],
        ),
    )
    db.execute(
        "UPDATE events SET event_id = ? WHERE row_id = ?",
        (f"E{cursor.lastrowid:06d}", cursor.lastrowid),
    )


class RateLimiter:
    def __init__(self) -> None:
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            events = self.events[key]
            while events and events[0] < now - RATE_WINDOW_SECONDS:
                events.popleft()
            if len(events) >= RATE_LIMIT:
                return False
            events.append(now)
            return True


class ApplicationHandler(SimpleHTTPRequestHandler):
    db_path: Path
    limiter = RateLimiter()

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(HTTPStatus.OK, {"ok": True})
            return
        if path == "/api/public/corpus.json":
            self.send_json(HTTPStatus.OK, self.public_corpus(), public=True)
            return
        if path == "/api/public/questions.json":
            self.get_public_questions("json")
            return
        if path in {"/api/public/questions.jsonl", "/data/questions.jsonl"}:
            self.get_public_questions("jsonl")
            return
        if path == "/api/public/records.json":
            self.get_public_records("json")
            return
        if path in {"/api/public/records.jsonl", "/data/traces.jsonl"}:
            self.get_public_records("jsonl")
            return
        if path == "/api/public/events.json":
            self.get_public_events("json")
            return
        if path in {"/api/public/events.jsonl", "/data/events.jsonl"}:
            self.get_public_events("jsonl")
            return
        if path.startswith("/api/public/"):
            self.get_public(path.removeprefix("/api/public/"))
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self.origin_allowed():
            self.send_json(HTTPStatus.FORBIDDEN, {"error": "origin not allowed"})
            return
        path = urlparse(self.path).path
        try:
            body = self.read_json()
            if path == "/api/contributions":
                self.create_contribution(body)
            elif path == "/api/contributions/status":
                self.get_status(body)
            elif path == "/api/contributions/append":
                self.append_response(body)
            elif path == "/api/questions":
                self.create_question(body)
            elif path == "/api/questions/status":
                self.get_question_status(body)
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except sqlite3.Error:
            self.log_error("database error")
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "temporary storage error"})

    def origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return not origin or origin in ALLOWED_ORIGINS

    def client_key(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "")
        return forwarded.split(",", 1)[0].strip() or self.client_address[0]

    def read_json(self) -> object:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("invalid content length") from error
        if size <= 0 or size > MAX_BODY:
            raise ValueError("invalid request size")
        try:
            return json.loads(self.rfile.read(size))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid JSON") from error

    def create_contribution(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many submissions; try later"})
            return
        door, payload, author = validate_submission(body)
        parent_public_id = clean_text(
            body.get("parent_id", ""), "parent record", required=False, limit=40
        ).upper()
        requested_relation = clean_text(
            body.get("relation", ""), "relation", required=False, limit=20
        ).lower()
        relation = ""
        if parent_public_id:
            if not PUBLIC_ID_RE.fullmatch(parent_public_id):
                raise ValueError("parent record is not public")
            with sqlite3.connect(self.db_path) as db:
                if parent_public_id.startswith("T"):
                    parent = db.execute(
                        "SELECT 1 FROM contributions WHERE public_id = ? AND status = 'public'",
                        (parent_public_id,),
                    ).fetchone()
                    if parent is None:
                        raise ValueError("parent record is not public")
                    if door != "d04":
                        raise ValueError("only D04 traces can continue a conversation")
                    if requested_relation not in {"", "continues"}:
                        raise ValueError("invalid relation for trace parent")
                    relation = "continues"
                    payload["context_mode"] = "continued_conversations"
                else:
                    parent = db.execute(
                        "SELECT payload FROM questions WHERE public_id = ? AND status = 'public'",
                        (parent_public_id,),
                    ).fetchone()
                    if parent is None:
                        raise ValueError("parent record is not public")
                    if requested_relation not in {"", "answers"}:
                        raise ValueError("invalid relation for question parent")
                    parent_payload = json.loads(parent[0])
                    if payload["question"] != parent_payload.get("question"):
                        raise ValueError("question must match the public question exactly")
                    relation = "answers"
                    payload["question_id"] = parent_public_id
                    payload["context_mode"] = "answers_public_question"
        elif requested_relation:
            raise ValueError("relation requires a parent record")
        token = secrets.token_urlsafe(32)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "INSERT INTO contributions "
                "(token_hash, door, payload, author, parent_public_id, relation, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    token_hash(token),
                    door,
                    json.dumps(payload, ensure_ascii=False),
                    author,
                    parent_public_id,
                    relation,
                    now,
                    now,
                ),
            )
            public_id = f"T{cursor.lastrowid:04d}"
            db.execute("UPDATE contributions SET public_id = ? WHERE row_id = ?", (public_id, cursor.lastrowid))
        self.send_json(
            HTTPStatus.CREATED,
            {"id": public_id, "token": token, "status": "pending", "status_path": f"/contribution/#{token}"},
        )

    def create_question(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many submissions; try later"})
            return
        payload, author, source_trace_id = validate_question_submission(body)
        token = secrets.token_urlsafe(32)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            source = db.execute(
                "SELECT 1 FROM contributions WHERE public_id = ? AND status = 'public'",
                (source_trace_id,),
            ).fetchone()
            if source is None:
                raise ValueError("source trace is unavailable")
            source_event_id = publication_event_id(db, "trace", source_trace_id)
            if not source_event_id:
                record_publication_event(db, source_trace_id)
                source_event_id = publication_event_id(db, "trace", source_trace_id)
            cursor = db.execute(
                "INSERT INTO questions "
                "(token_hash, payload, author, source_trace_id, source_event_id, relation, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'derives_from', ?, ?)",
                (
                    token_hash(token),
                    json.dumps(payload, ensure_ascii=False),
                    author,
                    source_trace_id,
                    source_event_id,
                    now,
                    now,
                ),
            )
            public_id = f"Q{cursor.lastrowid:04d}"
            db.execute("UPDATE questions SET public_id = ? WHERE row_id = ?", (public_id, cursor.lastrowid))
        self.send_json(
            HTTPStatus.CREATED,
            {
                "id": public_id,
                "token": token,
                "status": "pending",
                "status_path": f"/question-submission/#{token}",
            },
        )

    def private_question(self, token: str) -> sqlite3.Row | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return db.execute(
                "SELECT public_id, payload, author, source_trace_id, source_event_id, relation, "
                "status, research_status, review_note, created_at, updated_at "
                "FROM questions WHERE token_hash = ?",
                (token_hash(token),),
            ).fetchone()

    def get_question_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid status request")
        record = self.private_question(body.get("token", ""))
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "question not found"})
            return
        response = dict(record)
        response["payload"] = json.loads(response["payload"])
        if response["status"] == "public":
            response["public_path"] = f"/question/?id={response['public_id']}"
        self.send_json(HTTPStatus.OK, response)

    def private_record(self, token: str) -> sqlite3.Row | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return db.execute(
                "SELECT public_id, door, payload, author, parent_public_id, relation, status, review_note, created_at, updated_at "
                "FROM contributions WHERE token_hash = ?",
                (token_hash(token),),
            ).fetchone()

    def get_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid status request")
        record = self.private_record(body.get("token", ""))
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "trace not found"})
            return
        response = dict(record)
        response["payload"] = json.loads(response["payload"])
        if response["status"] == "public":
            response["public_path"] = f"/record/?id={response['public_id']}"
        self.send_json(HTTPStatus.OK, response)

    def append_response(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid append request")
        token = body.get("token", "")
        response = validate_response(body.get("response"))
        hashed = token_hash(token) if isinstance(token, str) else ""
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            record = db.execute(
                "SELECT row_id, door, payload, status FROM contributions WHERE token_hash = ?", (hashed,)
            ).fetchone()
            if record is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "trace not found"})
                return
            if record["door"] != "d04" or record["status"] not in {"pending", "needs_changes"}:
                raise ValueError("this trace cannot accept another answer")
            payload = json.loads(record["payload"])
            if len(payload["responses"]) >= 12:
                raise ValueError("answer limit reached")
            payload["responses"].append(response)
            now = utc_now()
            db.execute(
                "UPDATE contributions SET payload = ?, status = 'pending', updated_at = ? WHERE row_id = ?",
                (json.dumps(payload, ensure_ascii=False), now, record["row_id"]),
            )
        self.send_json(HTTPStatus.OK, {"ok": True, "answers": len(payload["responses"])})

    def get_public(self, public_id: str) -> None:
        public_id = public_id.upper()
        if public_id.startswith("Q"):
            self.get_public_question(public_id)
            return
        if not PUBLIC_ID_RE.fullmatch(public_id) or not public_id.startswith("T"):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "record not found"})
            return
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            record = db.execute(
                "SELECT public_id, door, payload, author, parent_public_id, relation, created_at, updated_at "
                "FROM contributions WHERE public_id = ? AND status = 'public'",
                (public_id,),
            ).fetchone()
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "record not found"})
            return
        response = dict(record)
        response["payload"] = json.loads(response["payload"])
        response["status"] = "public"
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            children = db.execute(
                "SELECT public_id, payload, author FROM contributions "
                "WHERE parent_public_id = ? AND relation = 'continues' AND status = 'public' "
                "ORDER BY row_id",
                (public_id,),
            ).fetchall()
        response["continuations"] = [
            {
                "public_id": child["public_id"],
                "question": json.loads(child["payload"]).get("question", ""),
                "author": child["author"],
            }
            for child in children
        ]
        self.send_json(HTTPStatus.OK, response, public=True)

    def question_traces(self, public_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, door, author, relation, created_at FROM contributions "
                "WHERE parent_public_id = ? AND relation = 'answers' AND status = 'public' "
                "ORDER BY row_id",
                (public_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def public_question_from_row(self, row: sqlite3.Row, traces: list[dict] | None = None) -> dict:
        record = dict(row)
        record["payload"] = json.loads(record["payload"])
        record["object_type"] = "question"
        record["status"] = record.pop("research_status")
        record["traces"] = traces if traces is not None else self.question_traces(record["public_id"])
        return record

    def get_public_question(self, public_id: str) -> None:
        if not re.fullmatch(r"Q[0-9]{4,}", public_id):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "question not found"})
            return
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT public_id, payload, author, source_trace_id, source_event_id, relation, "
                "research_status, created_at, updated_at "
                "FROM questions WHERE public_id = ? AND status = 'public'",
                (public_id,),
            ).fetchone()
        if row is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "question not found"})
            return
        self.send_json(HTTPStatus.OK, self.public_question_from_row(row), public=True)

    def public_questions(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, payload, author, source_trace_id, source_event_id, relation, "
                "research_status, created_at, updated_at "
                "FROM questions WHERE status = 'public' ORDER BY row_id"
            ).fetchall()
            trace_rows = db.execute(
                "SELECT public_id, door, author, parent_public_id, relation, created_at "
                "FROM contributions WHERE relation = 'answers' AND status = 'public' "
                "ORDER BY row_id"
            ).fetchall()
        traces_by_question: dict[str, list[dict]] = defaultdict(list)
        for trace in trace_rows:
            value = dict(trace)
            parent_id = value.pop("parent_public_id")
            traces_by_question[parent_id].append(value)
        return [
            self.public_question_from_row(row, traces_by_question.get(row["public_id"], []))
            for row in rows
        ]

    def public_records(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, door, payload, author, parent_public_id, relation, created_at, updated_at "
                "FROM contributions WHERE status = 'public' ORDER BY row_id"
            ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record["payload"])
            record["status"] = "public"
            records.append(record)
        return records

    def public_events(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT event_id, event_type, object_type, object_id, actor, links, payload, created_at "
                "FROM events ORDER BY row_id"
            ).fetchall()
            public_trace_ids = {
                row[0] for row in db.execute(
                    "SELECT public_id FROM contributions WHERE status = 'public'"
                )
            }
            public_question_ids = {
                row[0] for row in db.execute(
                    "SELECT public_id FROM questions WHERE status = 'public'"
                )
            }
        events = []
        for row in rows:
            event = dict(row)
            if event["object_type"] == "trace" and event["object_id"] not in public_trace_ids:
                continue
            if event["object_type"] == "question" and event["object_id"] not in public_question_ids:
                continue
            event["links"] = json.loads(event["links"])
            event["payload"] = json.loads(event["payload"])
            event["verified"] = False
            events.append(event)
        event_ids = {
            (event["object_type"], event["object_id"]): event["event_id"]
            for event in events
        }
        for event in events:
            for link in event["links"]:
                if "target_event_id" not in link:
                    target_event_id = event_ids.get((link.get("target_type"), link.get("target_id")))
                    if target_event_id:
                        link["target_event_id"] = target_event_id
        return events

    def public_corpus(self) -> dict:
        return {
            "schema_version": "0.2",
            "schema": "https://joinmultiplayer.ai/data/corpus-schema-v0.2.json",
            "license": "https://joinmultiplayer.ai/data-license/",
            "questions": self.public_questions(),
            "traces": self.public_records(),
            "events": self.public_events(),
        }

    def get_public_questions(self, output_format: str) -> None:
        questions = self.public_questions()
        if output_format == "jsonl":
            payload = b"".join(
                json.dumps(question, ensure_ascii=False).encode("utf-8") + b"\n"
                for question in questions
            )
            self.send_payload(
                HTTPStatus.OK, payload, "application/x-ndjson; charset=utf-8", public=True
            )
            return
        self.send_json(
            HTTPStatus.OK,
            {
                "schema_version": "0.2",
                "license": "https://joinmultiplayer.ai/data-license/",
                "questions": questions,
            },
            public=True,
        )

    def get_public_events(self, output_format: str) -> None:
        events = self.public_events()
        if output_format == "jsonl":
            payload = b"".join(
                json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n" for event in events
            )
            self.send_payload(HTTPStatus.OK, payload, "application/x-ndjson; charset=utf-8", public=True)
            return
        self.send_json(
            HTTPStatus.OK,
            {"schema_version": "0.1", "events": events},
            public=True,
        )

    def get_public_records(self, output_format: str) -> None:
        records = self.public_records()
        if output_format == "jsonl":
            payload = b"".join(
                json.dumps(record, ensure_ascii=False).encode("utf-8") + b"\n" for record in records
            )
            self.send_payload(HTTPStatus.OK, payload, "application/x-ndjson; charset=utf-8", public=True)
            return
        self.send_json(
            HTTPStatus.OK,
            {
                "schema_version": "0.2",
                "schema": "https://joinmultiplayer.ai/data/trace-schema-v0.2.json",
                "license": "https://joinmultiplayer.ai/data-license/",
                "records": records,
            },
            public=True,
        )

    def send_json(self, status: HTTPStatus, value: object, *, public: bool = False) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_payload(status, payload, "application/json; charset=utf-8", public=public)

    def send_payload(self, status: HTTPStatus, payload: bytes, content_type: str, *, public: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=60" if public else "no-store")
        if public:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    args = parser.parse_args()

    init_db(args.db)
    ApplicationHandler.db_path = args.db
    handler = lambda *handler_args, **kwargs: ApplicationHandler(  # noqa: E731
        *handler_args, directory=str(args.site), **kwargs
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
