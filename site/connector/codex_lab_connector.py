#!/usr/bin/env python3
"""Run a Codex CLI task and mirror a deliberately small, redacted public journal.

This connector uses the user's existing Codex login. It never asks for an
OpenAI API key and removes API-key-like environment variables from the Codex
process. The per-run publication key is prompted for without echo and is never
written into the public journal.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
LOCAL_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])(?:/home|/Users)/[^\s\"'<>]+")
ENV_ALLOWLIST = {
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TMPDIR",
    "SHELL",
    "CODEX_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
}


def redact_text(value: object, *, limit: int = 40_000) -> str:
    text = str(value or "")[:limit]
    text = LOCAL_PATH_RE.sub("<local-path>", text)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<redacted-secret>", text)
    return text


def safe_environment() -> dict[str, str]:
    """Keep only variables needed to locate Codex and its existing login."""
    return {key: value for key, value in os.environ.items() if key in ENV_ALLOWLIST}


def relative_public_path(value: object, workspace: Path) -> str | None:
    try:
        path = Path(str(value))
        if path.is_absolute():
            path = path.resolve().relative_to(workspace)
        if ".." in path.parts:
            return None
        return path.as_posix()[:500]
    except (OSError, ValueError):
        return None


def command_name(value: object) -> str:
    if isinstance(value, list):
        parts = [str(item) for item in value]
    else:
        try:
            parts = shlex.split(str(value or ""))
        except ValueError:
            parts = []
    if not parts:
        return "command"
    return Path(parts[0]).name[:120] or "command"


def item_kind(item: dict) -> str:
    return str(item.get("type") or "").replace("-", "_").lower()


def normalize_codex_event(event: dict, workspace: Path) -> tuple[str, dict] | None:
    """Map Codex JSONL to the provider-neutral public allowlist.

    Raw reasoning, command output, tool arguments/results, file contents, usage,
    thread identifiers, and environment data are intentionally ignored.
    """
    event_type = str(event.get("type") or "").replace("-", "_").lower()
    if event_type in {"thread.started", "thread_started"}:
        return "run_started", {"client_version": "codex-cli-jsonl"}
    if event_type in {"turn.started", "turn_started"}:
        return "checkpoint", {"text": "Codex began the experiment turn."}
    if event_type in {"turn.completed", "turn_completed"}:
        return "checkpoint", {"text": "Codex completed the experiment turn."}
    if event_type in {"turn.failed", "turn_failed", "error"}:
        message = event.get("message") or event.get("error") or "Codex reported an error."
        if isinstance(message, dict):
            message = message.get("message") or "Codex reported an error."
        return "checkpoint", {"text": redact_text(message, limit=2_000), "status": "failed"}

    if event_type not in {"item.started", "item.completed", "item_started", "item_completed"}:
        return None
    item = event.get("item")
    if not isinstance(item, dict):
        return None
    kind = item_kind(item)
    status = str(item.get("status") or ("completed" if "completed" in event_type else "running"))
    if kind in {"agent_message", "agentmessage"}:
        text = item.get("text") or item.get("message")
        return ("agent_message", {"text": redact_text(text)}) if text else None
    if kind == "plan":
        text = item.get("text")
        return ("plan", {"text": redact_text(text)}) if text else None
    if kind in {"command_execution", "commandexecution"}:
        return "command_status", {
            "command": command_name(item.get("command")),
            "status": status[:80],
            "exit_code": item.get("exit_code", item.get("exitCode")),
        }
    if kind in {"file_change", "filechange"}:
        changes = item.get("changes") or []
        files = []
        if isinstance(changes, list):
            for change in changes:
                raw_path = change.get("path") if isinstance(change, dict) else change
                safe_path = relative_public_path(raw_path, workspace)
                if safe_path and safe_path not in files:
                    files.append(safe_path)
        return "file_change", {"files": files[:100], "status": status[:80]}
    if kind in {"mcp_tool_call", "mcptoolcall", "dynamic_tool_call", "dynamictoolcall"}:
        tool = item.get("tool") or item.get("name") or item.get("server") or "tool"
        return "tool_status", {"tool": redact_text(tool, limit=200), "status": status[:80]}
    return None


def post_json(site: str, path: str, value: dict, *, attempts: int = 3) -> dict:
    body = json.dumps(value, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{site.rstrip('/')}{path}",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "pocket-i-codex-connector/0.1"},
        method="POST",
    )
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"site rejected the journal event ({error.code}): {detail}") from error
        except URLError as error:
            if attempt + 1 == attempts:
                raise RuntimeError(f"cannot reach the laboratory: {error.reason}") from error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("cannot reach the laboratory")


class Publisher:
    def __init__(self, site: str, token: str, local_path: Path) -> None:
        self.site = site
        self.token = token
        self.local_path = local_path
        self.sequence = 0
        local_path.parent.mkdir(parents=True, exist_ok=True)

    def send(self, event_type: str, payload: dict) -> None:
        self.sequence += 1
        event = {
            "sequence": self.sequence,
            "event_type": event_type,
            "payload": payload,
        }
        with self.local_path.open("a", encoding="utf-8") as journal:
            journal.write(json.dumps(event, ensure_ascii=False) + "\n")
        post_json(
            self.site,
            "/api/experiment-runs/events",
            {"token": self.token, **event},
        )


def validate_workspace(workspace: Path) -> Path:
    workspace = workspace.expanduser().resolve()
    if not (workspace / ".git").exists():
        raise RuntimeError("workspace must be a Git checkout of joinmultiplayer.ai")
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    remote = result.stdout.strip().lower()
    if "joinmultiplayer.ai" not in remote:
        raise RuntimeError("origin must point to a joinmultiplayer.ai repository or fork")
    return workspace


def run_codex(args: argparse.Namespace, token: str, run: dict) -> int:
    workspace = validate_workspace(args.workspace)
    codex_bin = shutil.which(args.codex_bin)
    if not codex_bin:
        raise RuntimeError("Codex CLI was not found; install and sign in to Codex first")
    run_id = run["public_id"]
    journal_path = workspace / ".joinmultiplayer" / "journals" / f"{run_id}.jsonl"
    publisher = Publisher(args.site, token, journal_path)
    prompt = str(run["task_prompt"])
    publisher.send(
        "user_message",
        {"text": f"Start {run_id}: design and implement {run['experiment_id']} from its public draft protocol."},
    )
    command = [
        codex_bin,
        "exec",
        "--json",
        "--ignore-user-config",
        "--sandbox",
        "workspace-write",
        "-C",
        str(workspace),
    ]
    if args.model:
        command.extend(["--model", args.model])
    command.append("-")
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=safe_environment(),
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(prompt)
    process.stdin.close()
    last_message = ""
    try:
        for line in process.stdout:
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            normalized = normalize_codex_event(raw, workspace)
            if not normalized:
                continue
            event_type, payload = normalized
            if event_type == "agent_message":
                last_message = str(payload.get("text") or "")
            publisher.send(event_type, payload)
            print(f"[{publisher.sequence:04d}] {event_type}", flush=True)
    except KeyboardInterrupt:
        process.terminate()
        publisher.send("run_completed", {"status": "stopped", "summary": "Stopped by owner."})
        return 130
    return_code = process.wait()
    if return_code == 0:
        publisher.send(
            "run_completed",
            {"status": "completed", "summary": redact_text(last_message or "Codex turn completed.", limit=4_000)},
        )
    else:
        publisher.send(
            "run_completed",
            {"status": "failed", "summary": "Codex exited with an error; raw output stayed local."},
        )
    return return_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="https://joinmultiplayer.ai")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--token", help="private run key; omit to enter it without echo")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--model", default="")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate the private run key and workspace without starting Codex",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = args.token or getpass.getpass("Private run key (not published): ").strip()
    if not token:
        raise RuntimeError("private run key is required")
    run = post_json(args.site, "/api/experiment-runs/status", {"token": token})
    workspace = validate_workspace(args.workspace)
    print(f"Connected {run['public_id']} to {workspace.name}. Public journal: {run['public_path']}")
    if args.check_only:
        return 0
    return run_codex(args, token, run)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"connector error: {error}", file=sys.stderr)
        raise SystemExit(1)
