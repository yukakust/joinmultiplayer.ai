#!/usr/bin/env python3
"""Opt-in Codex lifecycle hook for the joinmultiplayer public lab journal.

The hook never reads Codex transcript files. It consumes only the documented
event payload on stdin and reduces it to a small public allowlist.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import sqlite3
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_SITE = "https://joinmultiplayer.ai"
START_RE = re.compile(
    r"(?:\$|@)?pocket[- ]i[- ]lab\s+start\s+(E\d{3,})(?:\s+as\s+([^\n]{1,80}))?",
    re.IGNORECASE,
)
FINISH_RE = re.compile(r"(?:\$|@)?pocket[- ]i[- ]lab\s+finish\b", re.IGNORECASE)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{12,}\b", re.IGNORECASE),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b", re.IGNORECASE),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bauthorization\s*[:=]\s*bearer\s+[^\s,;]+"),
    re.compile(
        r"(?i)\b(?:authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password)"
        r"\s*[:=]\s*[^\s,;]{6,}"
    ),
)
LOCAL_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])(?:/home|/Users)/[^\s\"'<>)\]]+")
PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)


def redact_text(value: object, *, limit: int = 40_000) -> str:
    text = str(value or "")[:limit]
    text = LOCAL_PATH_RE.sub("<local-path>", text)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<redacted-secret>", text)
    return text


def hook_output(event_name: str, context: str = "", warning: str = "") -> None:
    value: dict[str, object] = {"continue": True}
    if warning:
        value["systemMessage"] = warning[:500]
    if context and event_name in {"UserPromptSubmit", "SessionStart"}:
        value["hookSpecificOutput"] = {
            "hookEventName": event_name,
            "additionalContext": context[:2_000],
        }
    print(json.dumps(value, ensure_ascii=False))


def post_json(site: str, path: str, value: dict, timeout: float = 8.0) -> dict:
    request = Request(
        f"{site.rstrip('/')}{path}",
        data=json.dumps(value, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "pocket-i-lab-hooks/0.1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"laboratory rejected the event ({error.code}): {detail}") from error
    except URLError as error:
        raise RuntimeError(f"laboratory is unreachable: {error.reason}") from error


class JournalState:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                token TEXT NOT NULL,
                public_path TEXT NOT NULL,
                next_sequence INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'running'
            );
            CREATE TABLE IF NOT EXISTS outbox (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                UNIQUE(session_id, fingerprint),
                UNIQUE(session_id, sequence)
            );
            """
        )
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def active(self, session_id: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM sessions WHERE session_id = ? AND status = 'running'", (session_id,)
        ).fetchone()

    def start(self, session_id: str, run: dict) -> None:
        self.db.execute(
            "INSERT INTO sessions (session_id, run_id, token, public_path, next_sequence, status) "
            "VALUES (?, ?, ?, ?, 1, 'running')",
            (session_id, run["id"], run["token"], run["public_path"]),
        )
        self.db.commit()

    def queue(self, session_id: str, fingerprint: str, event_type: str, payload: dict) -> bool:
        with self.db:
            row = self.db.execute(
                "SELECT next_sequence FROM sessions WHERE session_id = ? AND status = 'running'",
                (session_id,),
            ).fetchone()
            if row is None:
                return False
            sequence = int(row["next_sequence"])
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO outbox "
                "(session_id, fingerprint, sequence, event_type, payload) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    fingerprint,
                    sequence,
                    event_type,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            if cursor.rowcount:
                self.db.execute(
                    "UPDATE sessions SET next_sequence = next_sequence + 1 WHERE session_id = ?",
                    (session_id,),
                )
                return True
        return False

    def pending(self, session_id: str) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT o.*, s.token FROM outbox o JOIN sessions s USING (session_id) "
            "WHERE o.session_id = ? AND o.sent = 0 ORDER BY o.sequence",
            (session_id,),
        ).fetchall()

    def sent(self, row_id: int) -> None:
        with self.db:
            self.db.execute("UPDATE outbox SET sent = 1 WHERE row_id = ?", (row_id,))

    def close(self, session_id: str) -> None:
        with self.db:
            self.db.execute("UPDATE sessions SET status = 'closed' WHERE session_id = ?", (session_id,))


def event_fingerprint(data: dict) -> str:
    stable = {
        "event": data.get("hook_event_name"),
        "turn": data.get("turn_id"),
        "tool": data.get("tool_use_id"),
        "prompt": data.get("prompt"),
        "message": data.get("last_assistant_message"),
        "reason": data.get("reason"),
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()


def safe_relative_files(tool_input: object, cwd: str) -> list[str]:
    if not isinstance(tool_input, dict):
        return []
    raw = str(tool_input.get("command") or "")
    root = Path(cwd).resolve()
    files: list[str] = []
    for name in PATCH_FILE_RE.findall(raw):
        try:
            path = Path(name.strip())
            if path.is_absolute():
                path = path.resolve().relative_to(root)
            if ".." in path.parts:
                continue
            public = path.as_posix()[:500]
            if public and public not in files:
                files.append(public)
        except (OSError, ValueError):
            continue
    return files[:100]


def safe_command_name(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return "command"
    raw = str(tool_input.get("command") or "")
    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = []
    return Path(parts[0]).name[:120] if parts else "command"


def create_run(site: str, experiment: str, pseudonym: str) -> dict:
    anonymous = not pseudonym or pseudonym.lower() == "anonymous"
    return post_json(
        site,
        "/api/experiment-runs",
        {
            "experiment_id": experiment,
            "agent": "codex",
            "author_mode": "anonymous" if anonymous else "pseudonym",
            "pseudonym": "" if anonymous else redact_text(pseudonym, limit=80),
            "consent": True,
            "website": "",
        },
    )


def flush(state: JournalState, session_id: str, site: str) -> None:
    for row in state.pending(session_id):
        post_json(
            site,
            "/api/experiment-runs/events",
            {
                "token": row["token"],
                "sequence": row["sequence"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload"]),
            },
        )
        state.sent(row["row_id"])


def handle(data: dict, state: JournalState, site: str) -> str:
    event_name = str(data.get("hook_event_name") or "")
    session_id = str(data.get("session_id") or "")
    if not session_id:
        return ""

    prompt = str(data.get("prompt") or "")
    start_match = START_RE.search(prompt) if event_name == "UserPromptSubmit" else None
    if start_match:
        if state.active(session_id):
            return f"Pocket i Lab is already active: {state.active(session_id)['public_path']}"
        run = create_run(site, start_match.group(1).upper(), (start_match.group(2) or "anonymous").strip())
        state.start(session_id, run)
        state.queue(
            session_id,
            f"start:{run['id']}",
            "run_started",
            {"client_version": "pocket-i-lab-hooks/0.1"},
        )

    active = state.active(session_id)
    if active is None:
        return ""

    fingerprint = event_fingerprint(data)
    if event_name == "UserPromptSubmit":
        state.queue(session_id, fingerprint, "user_message", {"text": redact_text(prompt)})
        if FINISH_RE.search(prompt):
            state.queue(
                session_id,
                f"finish:{data.get('turn_id') or fingerprint}",
                "run_completed",
                {"status": "completed", "summary": "The owner closed this public Codex run."},
            )
            flush(state, session_id, site)
            path = str(active["public_path"])
            state.close(session_id)
            return f"Pocket i Lab run completed. Public journal: {site.rstrip('/')}{path}"
    elif event_name == "Stop":
        message = redact_text(data.get("last_assistant_message"))
        if message:
            state.queue(session_id, fingerprint, "agent_message", {"text": message})
    elif event_name == "PostToolUse":
        tool = str(data.get("tool_name") or "tool")[:200]
        if tool == "apply_patch":
            files = safe_relative_files(data.get("tool_input"), str(data.get("cwd") or "."))
            state.queue(session_id, fingerprint, "file_change", {"files": files, "status": "completed"})
        elif tool == "Bash":
            state.queue(
                session_id,
                fingerprint,
                "command_status",
                {"command": safe_command_name(data.get("tool_input")), "status": "completed"},
            )
        else:
            state.queue(session_id, fingerprint, "tool_status", {"tool": redact_text(tool, limit=200), "status": "completed"})
    elif event_name == "SessionEnd":
        state.queue(
            session_id,
            fingerprint,
            "run_completed",
            {"status": "stopped", "summary": "The Codex session ended before the owner closed the run."},
        )
        flush(state, session_id, site)
        state.close(session_id)
        return ""

    flush(state, session_id, site)
    if start_match:
        return (
            "Pocket i Lab is active for this task. Keep working in this same Codex conversation. "
            f"Public journal: {site.rstrip('/')}{active['public_path']}"
        )
    return ""


def main() -> int:
    event_name = ""
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("hook input must be an object")
        event_name = str(data.get("hook_event_name") or "")
        plugin_data = Path(os.environ.get("PLUGIN_DATA") or Path.home() / ".local/share/pocket-i-lab")
        state = JournalState(plugin_data / "journal.sqlite3")
        context = handle(data, state, os.environ.get("POCKET_I_LAB_SITE", DEFAULT_SITE))
        hook_output(event_name, context=context)
        return 0
    except Exception as error:  # Hooks must never break the user's Codex turn.
        hook_output(event_name, warning=f"Pocket i Lab could not update its journal: {redact_text(error, limit=350)}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
