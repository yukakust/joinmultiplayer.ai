#!/usr/bin/env python3
"""Small accountless contribution inbox for joinmultiplayer.ai."""

from __future__ import annotations

import argparse
import hashlib
import json
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
        "run_at": clean_text(value.get("run_at", ""), "run date", required=False, limit=40) or utc_now(),
    }


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

    author_mode = value.get("author_mode", "anonymous")
    if author_mode not in {"anonymous", "pseudonym"}:
        raise ValueError("invalid author mode")
    author = "anonymous"
    if author_mode == "pseudonym":
        author = clean_text(value.get("pseudonym", ""), "pseudonym", limit=80)
    return door, payload, author


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
        if path == "/api/public/records.json":
            self.get_public_records("json")
            return
        if path == "/api/public/records.jsonl":
            self.get_public_records("jsonl")
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
        token = secrets.token_urlsafe(32)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "INSERT INTO contributions (token_hash, door, payload, author, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (token_hash(token), door, json.dumps(payload, ensure_ascii=False), author, now, now),
            )
            public_id = f"T{cursor.lastrowid:04d}"
            db.execute("UPDATE contributions SET public_id = ? WHERE row_id = ?", (public_id, cursor.lastrowid))
        self.send_json(
            HTTPStatus.CREATED,
            {"id": public_id, "token": token, "status": "pending", "status_path": f"/contribution/#{token}"},
        )

    def private_record(self, token: str) -> sqlite3.Row | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return db.execute(
                "SELECT public_id, door, payload, author, status, review_note, created_at, updated_at FROM contributions WHERE token_hash = ?",
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
        if not public_id or len(public_id) > 40:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "record not found"})
            return
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            record = db.execute(
                "SELECT public_id, door, payload, author, created_at, updated_at FROM contributions WHERE public_id = ? AND status = 'public'",
                (public_id,),
            ).fetchone()
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "record not found"})
            return
        response = dict(record)
        response["payload"] = json.loads(response["payload"])
        response["status"] = "public"
        self.send_json(HTTPStatus.OK, response, public=True)

    def public_records(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, door, payload, author, created_at, updated_at "
                "FROM contributions WHERE status = 'public' ORDER BY row_id"
            ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record["payload"])
            record["status"] = "public"
            records.append(record)
        return records

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
                "schema": "https://joinmultiplayer.ai/data/schema-v0.1.json",
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
