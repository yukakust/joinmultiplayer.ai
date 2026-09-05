#!/usr/bin/env python3
"""Authenticated reverse proxy for the closed Pocket i alpha."""

from __future__ import annotations

import hmac
import http.client
import gzip
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


LISTEN_HOST = os.environ.get("POCKET_I_GATEWAY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("POCKET_I_GATEWAY_PORT", "18190"))
TOKEN_FILE = os.environ.get(
    "POCKET_I_GATEWAY_TOKEN_FILE",
    "/run/credentials/pocket-i-brain-gateway.service/access-token",
)
BACKENDS = {
    "reader": ("100.84.137.70", 18180),
    "relevance": ("100.84.137.70", 18181),
}
ALLOWED = {
    ("GET", "health"),
    ("POST", "v1/chat/completions"),
    ("POST", "embedding"),
}
MAX_BODY_BYTES = 256 * 1024 * 1024
AUDIT_DIR = os.environ.get("POCKET_I_GATEWAY_AUDIT_DIR", "")
AUDIT_HEADER = "X-Pocket-I-Alpha-Audit"


def _decoded_payload(payload: bytes | None) -> object:
    if payload is None:
        return None
    try:
        return json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"unparsed_utf8": payload.decode("utf-8", errors="replace")}


def write_private_audit(*, route: str, request_body: bytes | None,
                        response_status: int, response_body: bytes | None,
                        elapsed_ms: int, error: str | None = None) -> str | None:
    """Persist one opted-in alpha exchange without headers or credentials."""
    if not AUDIT_DIR:
        return None
    os.makedirs(AUDIT_DIR, mode=0o700, exist_ok=True)
    audit_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:12]}"
    record = {
        "schema_version": "pocket-i-server-alpha-audit-v0.1",
        "warning": "PRIVATE: owner questions, selected memory and model output. Never publish.",
        "audit_id": audit_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "route": route,
        "request": _decoded_payload(request_body),
        "response_status": response_status,
        "response": _decoded_payload(response_body),
        "elapsed_ms": elapsed_ms,
        "error": error,
    }
    fd, temporary = tempfile.mkstemp(prefix=f".{audit_id}-", suffix=".json.gz", dir=AUDIT_DIR)
    final = os.path.join(AUDIT_DIR, f"{audit_id}.json.gz")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6) as archive:
                archive.write((json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"))
        os.replace(temporary, final)
        return audit_id
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def read_token() -> str:
    with open(TOKEN_FILE, "r", encoding="utf-8") as handle:
        token = handle.read().strip()
    if len(token) < 32:
        raise RuntimeError("Pocket i gateway token is missing or too short")
    return token


ACCESS_TOKEN = read_token()


class Gateway(BaseHTTPRequestHandler):
    server_version = "Pocket-i-Brain-Gateway"
    sys_version = ""

    def log_message(self, format_string: str, *args: object) -> None:
        # Never create a second store of private prompts or bearer tokens.
        return

    def _json_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, f"Bearer {ACCESS_TOKEN}")

    def _proxy(self) -> None:
        if not self._authorized():
            self._json_error(401, "unauthorized")
            return

        route = self.path.split("?", 1)[0].strip("/")
        parts = route.split("/", 1)
        if len(parts) != 2 or parts[0] not in BACKENDS:
            self._json_error(404, "not found")
            return
        backend_name, backend_route = parts
        if (self.command, backend_route) not in ALLOWED:
            self._json_error(404, "not found")
            return
        if backend_name == "reader" and backend_route == "embedding":
            self._json_error(404, "not found")
            return
        if backend_name == "relevance" and backend_route == "v1/chat/completions":
            self._json_error(404, "not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json_error(400, "invalid content length")
            return
        if length < 0 or length > MAX_BODY_BYTES:
            self._json_error(413, "request too large")
            return
        body = self.rfile.read(length) if length else None
        audit_enabled = self.headers.get(AUDIT_HEADER, "").strip().lower() == "full"
        started = time.monotonic()
        host, port = BACKENDS[backend_name]
        headers = {"Accept": "application/json"}
        if body is not None:
            headers.update({"Content-Type": "application/json", "Content-Length": str(len(body))})
        connection = http.client.HTTPConnection(host, port, timeout=900)
        try:
            connection.request(self.command, f"/{backend_route}", body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            audit_id = None
            if audit_enabled and self.command == "POST":
                try:
                    audit_id = write_private_audit(
                        route=f"{backend_name}/{backend_route}",
                        request_body=body,
                        response_status=response.status,
                        response_body=payload,
                        elapsed_ms=round((time.monotonic() - started) * 1000),
                    )
                except OSError:
                    audit_id = None
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type") or "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            if audit_id:
                self.send_header("X-Pocket-I-Audit-Id", audit_id)
            self.end_headers()
            self.wfile.write(payload)
        except (OSError, http.client.HTTPException) as error:
            if audit_enabled and self.command == "POST":
                try:
                    write_private_audit(
                        route=f"{backend_name}/{backend_route}",
                        request_body=body,
                        response_status=502,
                        response_body=None,
                        elapsed_ms=round((time.monotonic() - started) * 1000),
                        error=type(error).__name__,
                    )
                except OSError:
                    pass
            self._json_error(502, "brain unavailable")
        finally:
            connection.close()

    do_GET = _proxy
    do_POST = _proxy


if __name__ == "__main__":
    ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Gateway).serve_forever()
