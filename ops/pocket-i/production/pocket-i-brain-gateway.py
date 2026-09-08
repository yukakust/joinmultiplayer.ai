#!/usr/bin/env python3
"""Authenticated reverse proxy for the closed Pocket i alpha."""

from __future__ import annotations

import hmac
import http.client
import gzip
import json
import os
import tempfile
import threading
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
ASYNC_HEADER = "X-Pocket-I-Async"
JOB_TTL_SECONDS = 30 * 60
MAX_JOBS = 64
JOBS: dict[str, dict[str, object]] = {}
JOBS_LOCK = threading.Lock()


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


def _prune_jobs(now: float | None = None) -> None:
    current = time.monotonic() if now is None else now
    expired = [
        job_id for job_id, job in JOBS.items()
        if current - float(job["created_monotonic"]) > JOB_TTL_SECONDS
    ]
    for job_id in expired:
        JOBS.pop(job_id, None)


def _run_async_job(*, job_id: str, backend_name: str, backend_route: str,
                   method: str, body: bytes | None, audit_enabled: bool) -> None:
    started = time.monotonic()
    host, port = BACKENDS[backend_name]
    headers = {"Accept": "application/json"}
    if body is not None:
        headers.update({"Content-Type": "application/json", "Content-Length": str(len(body))})
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        job["state"] = "running"
    connection = http.client.HTTPConnection(host, port, timeout=900)
    try:
        connection.request(method, f"/{backend_route}", body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        elapsed_ms = round((time.monotonic() - started) * 1000)
        audit_id = None
        if audit_enabled and method == "POST":
            try:
                audit_id = write_private_audit(
                    route=f"{backend_name}/{backend_route}",
                    request_body=body,
                    response_status=response.status,
                    response_body=payload,
                    elapsed_ms=elapsed_ms,
                )
            except OSError:
                audit_id = None
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job is not None:
                job.update({
                    "state": "ready" if 200 <= response.status < 300 else "failed",
                    "response_status": response.status,
                    "response_body": payload,
                    "content_type": response.getheader("Content-Type") or "application/json",
                    "elapsed_ms": elapsed_ms,
                    "audit_id": audit_id,
                    "error": None if 200 <= response.status < 300 else "brain rejected the request",
                })
    except (OSError, http.client.HTTPException) as error:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        if audit_enabled and method == "POST":
            try:
                write_private_audit(
                    route=f"{backend_name}/{backend_route}",
                    request_body=body,
                    response_status=502,
                    response_body=None,
                    elapsed_ms=elapsed_ms,
                    error=type(error).__name__,
                )
            except OSError:
                pass
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job is not None:
                job.update({
                    "state": "failed",
                    "response_status": 502,
                    "response_body": None,
                    "elapsed_ms": elapsed_ms,
                    "error": "brain unavailable",
                })
    finally:
        connection.close()


class Gateway(BaseHTTPRequestHandler):
    server_version = "Pocket-i-Brain-Gateway"
    sys_version = ""

    def log_message(self, format_string: str, *args: object) -> None:
        # Never create a second store of private prompts or bearer tokens.
        return

    def _json_error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _json(self, status: int, value: object) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _poll_job(self, job_id: str) -> None:
        with JOBS_LOCK:
            _prune_jobs()
            job = JOBS.get(job_id)
            snapshot = dict(job) if job is not None else None
        if snapshot is None:
            self._json_error(404, "job not found")
            return
        state = str(snapshot["state"])
        if state in {"queued", "running"}:
            self._json(202, {"job_id": job_id, "state": state, "poll_after_ms": 1000})
            return
        if state == "failed":
            self._json(200, {
                "job_id": job_id,
                "state": "failed",
                "response_status": snapshot.get("response_status", 502),
                "elapsed_ms": snapshot.get("elapsed_ms"),
                "error": snapshot.get("error") or "brain unavailable",
            })
            return
        response_body = snapshot.get("response_body")
        self._json(200, {
            "job_id": job_id,
            "state": "ready",
            "response_status": snapshot.get("response_status", 200),
            "elapsed_ms": snapshot.get("elapsed_ms"),
            "audit_id": snapshot.get("audit_id"),
            "result": _decoded_payload(response_body if isinstance(response_body, bytes) else None),
        })

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, f"Bearer {ACCESS_TOKEN}")

    def _proxy(self) -> None:
        if not self._authorized():
            self._json_error(401, "unauthorized")
            return

        route = self.path.split("?", 1)[0].strip("/")
        if self.command == "GET" and route.startswith("jobs/"):
            job_id = route.removeprefix("jobs/")
            if not job_id or "/" in job_id:
                self._json_error(404, "job not found")
                return
            self._poll_job(job_id)
            return
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
        async_enabled = self.command == "POST" and self.headers.get(ASYNC_HEADER, "").strip().lower() == "v1"
        if async_enabled:
            with JOBS_LOCK:
                _prune_jobs()
                if len(JOBS) >= MAX_JOBS:
                    self._json_error(503, "too many active jobs")
                    return
                job_id = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"
                JOBS[job_id] = {
                    "state": "queued",
                    "created_monotonic": time.monotonic(),
                    "response_body": None,
                }
            threading.Thread(
                target=_run_async_job,
                kwargs={
                    "job_id": job_id,
                    "backend_name": backend_name,
                    "backend_route": backend_route,
                    "method": self.command,
                    "body": body,
                    "audit_enabled": audit_enabled,
                },
                daemon=True,
            ).start()
            self._json(202, {"job_id": job_id, "state": "queued", "poll_after_ms": 1000})
            return
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
