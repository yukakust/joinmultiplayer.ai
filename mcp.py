"""Local MCP server for gpu.

Runs on each architect's Mac as a subprocess of Claude Code or Codex.
Stays alive while the client is open — that's our presence signal.

What it does:
  1. On start: opens long-lived SSE connection to gpu.social/events?user=$BRAIN_USER
     → brain knows this user is online for as long as connection is open
  2. Background thread: receives SSE events.
     - "request" event → spawns subprocess `osascript -e 'display dialog ...'`
       → user clicks Approve/Deny → MCP auto-fulfills (reads file) → POSTs response
     - "response" event → notifies LLM context (resource update)
  3. Exposes MCP tools the LLM can call to send requests / check status.

Env vars (set by install.sh in Claude Code/Codex config):
  BRAIN_URL          default https://gpu.social
  BRAIN_PASSWORD     your per-user Bearer token (the one POST /join returns)
  BRAIN_USER         your handle (the one POST /join returns)
  BRAIN_SHARE_ROOTS  comma-separated path prefixes whose files may be auto-shared
                     on approval (e.g. ~/code,~/Desktop/LLM). Anything outside
                     these roots will fail safety check even if user clicks Approve.
"""
from __future__ import annotations
import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

# Where deferred task_requests are queued for the user's next session.
TASKS_DIR = Path.home() / ".gpu" / "tasks"
TASKS_DIR.mkdir(parents=True, exist_ok=True)
# IDs of tasks already completed via complete_task(). Lets us pull approved
# tasks from the SERVER (so a task approved in ANY channel — TG/web/popup —
# reaches the agent) without re-surfacing ones we've already finished.
COMPLETED_TASKS_FILE = Path.home() / ".gpu" / "tasks_completed.json"

# Where silent messages (notify/dm/broadcast/ask_team) are persisted so they
# survive Claude Code restarts.
MESSAGES_DIR = Path.home() / ".gpu" / "messages"
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
# Messages marked read by `mark_message_read()` (so we don't re-surface them).
READ_MARKERS_DIR = MESSAGES_DIR / ".read"
READ_MARKERS_DIR.mkdir(parents=True, exist_ok=True)

# Vault: user's personal knowledge store. Lives ONLY on the device — brain
# never sees the contents. Used by the agent to answer questions like
# "what's my Hetzner IP" or "GA property for miracle" without re-asking
# the user. Cross-network sharing is opt-in per-request via popup (Step 3).
VAULT_DIR = Path.home() / ".gpu" / "vault"
VAULT_DIR.mkdir(parents=True, exist_ok=True)
try:
    # Tight POSIX perms — no other users on the box should read this.
    os.chmod(VAULT_DIR, 0o700)
except Exception:
    pass

# Per-friend access policy. Local-only — never sent to brain. Three tiers:
#   trusted       — auto-fulfill vault queries; access logged
#   acquaintance  — popup with response preview; user Approves before send
#   blocked       — silent deny, no popup, no notification
# Default for any user not in this file = "acquaintance".
FRIENDS_FILE = Path.home() / ".gpu" / "friends.json"
VAULT_LOG = Path.home() / ".gpu" / "vault.log"  # append-only JSONL of every access

# Seed with an instructional README on first launch so the user knows what
# to put here. Only writes once — we don't clobber later edits.
_VAULT_README = VAULT_DIR / "README.md"
if not any(VAULT_DIR.iterdir()):
    _VAULT_README.write_text(
        "# Your gpu vault\n\n"
        "Drop markdown notes here. Your agent reads them via `vault_read(name)`\n"
        "or `vault_search(query)` and answers questions without making you\n"
        "retype the same info every time.\n\n"
        "Suggested files to start with:\n\n"
        "- `github.md` — tokens, repos, organizations\n"
        "- `servers.md` — SSH access, IPs, root passwords\n"
        "- `analytics.md` — Google Analytics properties, Plausible logins\n"
        "- `websites.md` — Cloudflare, Vercel, Netlify, domain registrars\n"
        "- `apis.md` — Anthropic, OpenAI, HuggingFace keys\n"
        "- `people.md` — contacts, who handles what\n\n"
        "Subdirectories work too:\n\n"
        "- `projects/jippy.md`\n"
        "- `projects/flux.md`\n\n"
        "## Privacy\n\n"
        "Vault content NEVER leaves this device automatically. When someone\n"
        "in the network asks for something via gpu, you'll see a popup with\n"
        "the *exact* response that would go out — approve or deny per request.\n\n"
        "Edit any file in your favorite editor.\n",
        encoding="utf-8",
    )

# ─────────────── config ───────────────

# ─── Version marker (Variant D — stale-build signal) ───
# BUMP THIS whenever mcp_local.py changes in a way users should pick up.
# Format: date + counter. The server parses this same constant from its copy
# of mcp_local.py and reports it via /healthz; a background thread here compares
# and, if the server is newer, status_resource() nudges the user to restart
# Claude (stdio MCP can't hot-reload — see docs/MCP-HOT-RELOAD.md).
MCP_VERSION = "2026.06.08.4"

BRAIN_URL = os.environ.get("BRAIN_URL", "https://gpu.social").rstrip("/")
BRAIN_PASSWORD = os.environ.get("BRAIN_PASSWORD", "")
BRAIN_USER = os.environ.get("BRAIN_USER", "")
SHARE_ROOTS_RAW = os.environ.get("BRAIN_SHARE_ROOTS", "")

if not BRAIN_PASSWORD or not BRAIN_USER:
    sys.stderr.write(
        "[mcp_local] FATAL: set BRAIN_PASSWORD and BRAIN_USER env vars\n"
    )
    sys.exit(1)

# Accept ANY valid handle — the relay is the real authority (the Bearer token must resolve to
# this user server-side; a wrong handle simply fails auth there). We only sanity-check the FORMAT
# so an obvious typo fails fast. (Previously a hardcoded founder allowlist — which broke every
# self-join user and baked teammate names into the public client.)
if not (BRAIN_USER and len(BRAIN_USER) <= 32 and all(c.isalnum() or c in "_-" for c in BRAIN_USER)):
    sys.stderr.write(
        f"[mcp_local] FATAL: BRAIN_USER '{BRAIN_USER}' looks invalid — expected the lowercase "
        "handle that /join returned (letters / digits / _ / -).\n"
    )
    sys.exit(1)

SHARE_ROOTS = [
    Path(r.strip()).expanduser().resolve()
    for r in SHARE_ROOTS_RAW.split(",")
    if r.strip()
]


def _hdr() -> dict[str, str]:
    return {"Authorization": f"Bearer {BRAIN_PASSWORD}"}


# Cache of pending requests we've received via SSE, so the LLM can refer to them.
_pending_received: dict[str, dict] = {}
# Cache of responses we've received via SSE
_received_responses: dict[str, dict] = {}
# Sprint 2: route_prompts where someone else won the race. Receiver-side
# (Step 3) reads this to auto-dismiss popups. Sender doesn't care.
_lost_races: set[str] = set()


# ─────────────── agent-workspace bootstrap (Step A) ───────────────
# Idempotent — first MCP run after install creates ~/.gpu/agent-workspace/
# with CLAUDE.md pre-filled from the user's profile (bio + tags fetched
# from brain). Re-runs refresh the file if profile changed.

def _bootstrap_agent_workspace() -> None:
    try:
        from . import agent_workspace as _aw
    except Exception:
        # Module-relative import only works when loaded as relay.mcp_local;
        # when launched directly (Claude Code's `python ~/.gpu/gpu_mcp.py`)
        # the package context is missing — fall back to flat import.
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import agent_workspace as _aw  # type: ignore
        except Exception as e:
            sys.stderr.write(f"[mcp_local] agent_workspace import failed: {e}\n")
            return
    # Seed preferences with defaults (writes the file on first run)
    _aw.load_preferences()
    # Pull bio + tags from brain so CLAUDE.md renders with the latest profile
    bio, tags = "", []
    try:
        r = requests.get(f"{BRAIN_URL}/friends", headers={"Authorization": f"Bearer {BRAIN_PASSWORD}"}, timeout=5)
        if r.status_code == 200:
            me = r.json().get(BRAIN_USER, {})
            bio = me.get("bio_short", "") or ""
            tags = list(me.get("tags") or [])
    except Exception:
        pass
    try:
        _aw.ensure_workspace(user_name=BRAIN_USER, user_bio=bio, user_tags=tags)
    except Exception as e:
        sys.stderr.write(f"[mcp_local] ensure_workspace failed: {e}\n")


_bootstrap_agent_workspace()


# ─────────────── safety & fulfillment ───────────────

# Patterns that trigger a SECOND confirmation popup. Conservative — only flag
# obviously high-risk things to keep false positives low.
SENSITIVE_PATH_PATTERNS = [
    r"/\.ssh/",
    r"/\.aws/",
    r"/\.gnupg/",
    r"/\.docker/",
    r"/\.kube/",
    r"/\.config/",
    r"^/etc/",
    r"^/var/",
    r"\.key$",
    r"\.pem$",
    r"\.p12$",
    r"id_rsa",
    r"id_ed25519",
    r"credentials",
    r"\.env(\.|$)",
    r"\bsecret\b",
    r"\btoken\b",
    r"\bpassword\b",
]
SENSITIVE_COMMAND_PATTERNS = [
    r"\brm\s+-rf?\b",
    r"\bsudo\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bdd\s+if=",
    r">\s*/dev/",
    r"curl[^|]*\|\s*(sh|bash)",
    r"wget[^|]*\|\s*(sh|bash)",
    r"\bDROP\s+(TABLE|DATABASE)\b",
    r"\bDELETE\s+FROM\b",
    r"\bTRUNCATE\b",
    r"format\s+[A-Za-z]:",
    r"mkfs\.",
]


def _is_sensitive(req: dict) -> tuple[bool, str]:
    """Return (is_sensitive, reason). Open-ended tasks always sensitive."""
    t = req.get("type")
    target = req.get("target", "") or ""
    if t in ("task_request", "delegate", "compute_request"):
        return True, f"{t} — recipient will act on your behalf"
    if t == "file_read":
        for pat in SENSITIVE_PATH_PATTERNS:
            if re.search(pat, target, re.IGNORECASE):
                return True, f"path matches sensitive pattern `{pat}`"
    if t == "command_exec":
        for pat in SENSITIVE_COMMAND_PATTERNS:
            if re.search(pat, target, re.IGNORECASE):
                return True, f"command matches sensitive pattern `{pat}`"
    return False, ""


def _is_path_allowed(target: str) -> tuple[bool, str]:
    if not SHARE_ROOTS:
        return False, "BRAIN_SHARE_ROOTS env is empty — no paths shareable"
    p = Path(target).expanduser().resolve()
    if not p.exists():
        return False, f"path does not exist: {p}"
    for root in SHARE_ROOTS:
        try:
            p.relative_to(root)
            return True, ""
        except ValueError:
            continue
    return False, f"{p} not under any allowed root: {SHARE_ROOTS}"


def _fulfill(req: dict) -> tuple[str, str]:
    t = req.get("type")
    target = req.get("target", "")
    if t == "file_read":
        ok, why = _is_path_allowed(target)
        if not ok:
            return "", why
        p = Path(target).expanduser().resolve()
        try:
            return p.read_text(encoding="utf-8"), ""
        except UnicodeDecodeError:
            return "BASE64:" + base64.b64encode(p.read_bytes()).decode("ascii"), ""
        except Exception as e:
            return "", str(e)
    elif t == "command_exec":
        try:
            r = subprocess.run(target, shell=True, capture_output=True, text=True, timeout=30)
            return (
                f"$ {target}\n[exit {r.returncode}]\n"
                f"---stdout---\n{r.stdout}\n---stderr---\n{r.stderr}",
                "",
            )
        except subprocess.TimeoutExpired:
            return "", "command timed out (30s)"
        except Exception as e:
            return "", str(e)
    elif t == "free_text":
        return "(free-text request — please reply via your client)", ""
    return "", f"unknown request type '{t}'"


def _send_response(req_id: str, decision: str, body: str) -> dict[str, Any]:
    r = requests.post(
        f"{BRAIN_URL}/responses",
        json={"from": BRAIN_USER, "in_reply_to": req_id, "decision": decision, "body": body},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


# ─────────────── popup (macOS osascript) ───────────────

def _escape_for_applescript(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


_IS_MACOS = sys.platform == "darwin"


def _osascript_dialog(message: str, title: str, buttons: list[str],
                       default_button: str, with_icon: str = "",
                       timeout_s: int = 300) -> str:
    """macOS native dialog via osascript. Returns clicked button text."""
    btn_list = ", ".join(f'"{b}"' for b in buttons)
    icon = f"with icon {with_icon}" if with_icon else ""
    script = (
        f'display dialog "{_escape_for_applescript(message)}" '
        f'with title "{title}" '
        f'buttons {{{btn_list}}} default button "{default_button}" '
        f'{icon} '
        f'giving up after {timeout_s}'
    )
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout_s + 20,
        )
        for b in buttons:
            if f"button returned:{b}" in r.stdout:
                return b
        return ""
    except Exception as e:
        sys.stderr.write(f"[popup-osa] {e}\n")
        return ""


def _tk_dialog(message: str, title: str, buttons: list[str],
               default_button: str, with_icon: str = "",
               timeout_s: int = 300) -> str:
    """Cross-platform tkinter dialog fallback (works on Windows + Linux + macOS).

    Spawns a subprocess so we don't entangle tkinter mainloop with our SSE thread.
    Returns the clicked button text or '' if user closed/timed out.
    """
    # Build a tiny self-contained Python script
    icon_arg = repr(with_icon) if with_icon else "''"
    script = f'''
import tkinter as tk
from tkinter import messagebox
import sys

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)

# Determine icon type for tkinter (warning for sensitive, question otherwise)
icon = "warning" if {icon_arg} in ("caution", "stop") else "question"

# 2-button dialog. messagebox.askyesno returns True/False.
# Our buttons[0] is "Deny"/"Cancel" → False; buttons[1] is "Approve"/"Yes" → True.
result = messagebox.askyesno({title!r}, {message!r}, icon=icon, default="no")
root.destroy()
print({buttons[1]!r} if result else {buttons[0]!r})
'''
    try:
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=timeout_s + 20,
        )
        out = (r.stdout or "").strip()
        for b in buttons:
            if b == out:
                return b
        return ""
    except Exception as e:
        sys.stderr.write(f"[popup-tk] {e}\n")
        return ""


def _show_dialog(message: str, title: str, buttons: list[str],
                  default_button: str, with_icon: str = "",
                  timeout_s: int = 300) -> str:
    """Cross-platform dialog. Uses native osascript on macOS, tkinter elsewhere."""
    if _IS_MACOS:
        return _osascript_dialog(message, title, buttons, default_button, with_icon, timeout_s)
    return _tk_dialog(message, title, buttons, default_button, with_icon, timeout_s)


def _show_notification(title: str, message: str) -> None:
    """Cross-platform banner notification (fire-and-forget, no buttons)."""
    try:
        if _IS_MACOS:
            subprocess.Popen(
                ["osascript", "-e",
                 f'display notification "{_escape_for_applescript(message)}" '
                 f'with title "{_escape_for_applescript(title)}"'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            # Try plyer (cross-platform), fall back silently if not installed
            try:
                from plyer import notification  # type: ignore
                notification.notify(title=title, message=message, timeout=5)
            except ImportError:
                pass  # silent — banner is nice-to-have
    except Exception:
        pass


POPUP_CLAIMS_DIR = Path.home() / ".gpu" / "popup_claims"


def _claim_popup(req_id: str) -> bool:
    """Atomic cross-process claim so only ONE of the N gpu MCPs on this machine pops a
    given request — N open Claude projects would otherwise each show the SAME dialog
    (the duplicate-popup complaint). Returns True iff WE claimed it (→ we pop). Prunes
    claims older than 1h so a crashed claimant never permanently blocks a re-popup. On
    any unexpected error: don't suppress (pop), so we never silently lose a request."""
    try:
        POPUP_CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
        now = time.time()
        for f in POPUP_CLAIMS_DIR.glob("*.claim"):
            try:
                if now - f.stat().st_mtime > 3600:
                    f.unlink()
            except Exception:
                pass
        fd = os.open(str(POPUP_CLAIMS_DIR / f"{req_id}.claim"),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except Exception:
        return True


def _show_popup(req: dict) -> str:
    """Show confirmation popup. Returns 'approved' or 'denied'.

    Sensitive requests (ssh keys, sudo commands, task_requests) require TWO clicks:
    first a normal popup, then a 'really?' confirm with caution icon."""
    sensitive, why = _is_sensitive(req)
    title = "gpu — agent request"
    body = (
        f"From: {req['from']}\n"
        f"Type: {req['type']}\n"
        f"Target: {req['target'][:300]}\n\n"
        f"Why: {req['justification']}"
    )
    if req["type"] == "task_request":
        body += "\n\nApprove will QUEUE this task for you to handle in your next chat."
    else:
        body += "\n\nApprove will auto-fulfill (read file / run command)."

    first = _show_dialog(
        message=body, title=title,
        buttons=["Deny", "Approve"], default_button="Deny",
        with_icon="caution" if sensitive else "",
    )
    # Distinguish a real "Deny" click from a timeout / window-close. _show_dialog
    # returns "" when the dialog timed out or was dismissed without a choice. We
    # must NOT treat that as a denial: on reconnect the brain re-sends the still
    # pending request, and auto-denying on every timeout both spams the user with
    # popups and silently kills requests they never actually answered.
    if first == "":
        return "timeout"
    if first != "Approve":
        return "denied"

    # Single confirm. The old double-confirm ("are you SURE?") was removed
    # 2026-05-29: trust is now gated by friend-tier upstream in
    # _handle_incoming_request (trusted = auto, acquaintance = this one popup,
    # blocked = silent), so a second click was redundant — and a buggy delayed
    # second dialog made it un-clickable. The caution icon above still flags
    # sensitive requests visually. See docs/TIER-POLICY.md.
    return "approved"


_inbound_messages: list[dict] = []  # notify/dm/broadcast/ask_team feed


def _handle_vault_query(req: dict) -> None:
    """Cross-agent vault access. Behavior depends on requester's local
    friend tier:
      trusted       → auto-fulfill, log, respond
      acquaintance  → popup with response preview, send only if user clicks
                      Approve (so user always sees what would go out)
      blocked       → silent ignore — no popup, no response, just log
    """
    sender = req.get("from", "?")
    meta = req.get("metadata") or {}
    action = meta.get("action", "search")
    if action not in ("search", "read"):
        return _send_response(req["id"], "denied", body=f"unknown vault action '{action}'")
    target = req.get("target", "")
    if not target:
        return _send_response(req["id"], "denied", body="empty vault query")

    tier = _friend_tier(sender)
    sys.stderr.write(f"[vault] incoming vault_query from {sender} (tier={tier}): {action} '{target[:60]}'\n")

    if tier == "blocked":
        _log_vault_access({
            "from": sender, "action": action, "target": target,
            "decision": "blocked", "tier": tier,
        })
        # Silent — no response back. Sender's fetch_response will timeout.
        return

    # Build the proposed response now so both auto-path and popup-preview
    # show identical content. No info leaks via timing/probing.
    max_matches = int(meta.get("max_matches", 10) or 10)
    body = _build_vault_response(action, target, max_matches=max_matches)

    if tier == "trusted":
        decision = "approved"
    else:  # acquaintance — popup with preview
        preview_body = (
            f"⚠️  VAULT REQUEST\n\n"
            f"{sender} wants: {action} '{target[:120]}'\n\n"
            f"Tier: {tier} (popup required)\n\n"
            f"=== response that would be sent ===\n\n"
            f"{body[:1400]}{'…' if len(body) > 1400 else ''}\n\n"
            f"=== send this to {sender}? ==="
        )
        choice = _show_dialog(
            message=preview_body,
            title="gpu — vault request",
            buttons=["Don't send", "Send"],
            default_button="Don't send",
            with_icon="caution",
            timeout_s=300,
        )
        decision = "approved" if choice == "Send" else "denied"

    _log_vault_access({
        "from": sender, "action": action, "target": target,
        "decision": decision, "tier": tier,
        "response_bytes": len(body) if decision == "approved" else 0,
    })

    if decision == "approved":
        _send_response(req["id"], "approved", body=body)
    else:
        _send_response(req["id"], "denied", body="vault query denied by recipient")


def _handle_incoming_request(req: dict) -> None:
    """Called by SSE thread for each incoming request event."""
    sys.stderr.write(f"[brain] incoming {req['type']} {req['id']} from {req['from']}: {req.get('target', '')[:80]}\n")

    # Cross-agent vault — own handler with friend-tier gating
    if req.get("type") == "vault_query":
        return _handle_vault_query(req)

    # Silent types — no popup, but PERSIST + lightweight notification
    SILENT = {"notify", "dm", "broadcast", "ask_team", "free_text"}
    if req.get("type") in SILENT:
        _inbound_messages.append(req)
        # Persist to disk so it survives Claude Code restart
        try:
            (MESSAGES_DIR / f"{req['id']}.json").write_text(
                json.dumps(req, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            sys.stderr.write(f"[brain] persist failed for {req['id']}: {e}\n")
        # NOTE: no soft-notification here anymore. Notifications are the TRAY's job now
        # (one per machine, deduped via last_pending_ids). N open Claude projects = N MCPs,
        # and each would toast the SAME dm AND re-toast it on every SSE reconnect — that's
        # the "many popups that keep coming even after answering" spam. The persist above
        # is kept so the message survives a Claude restart; the tray surfaces it.
        # Auto-ack ONLY purely-informational types. A 'received' reply flips the
        # request to status=approved and sends the sender a stub "answer" — fine for
        # notify/broadcast (nobody's waiting on a real reply) but DESTRUCTIVE for
        # dm/ask_team/free_text: it permanently closes a message that needs a real
        # answer (this is exactly what lost yuka's questions — they got 'received'
        # and never a reply, and never stayed `pending` so nothing could rescue them).
        # Leave reply-expecting types PENDING → the tray auto-react OR the room_agent
        # DM pull-reconciler gives a real answer. (Sender already learns delivery from
        # the send-time response: delivered_live / recipient_online.)
        if req.get("type") in ("notify", "broadcast"):
            try:
                _send_response(req["id"], "approved", "received")
            except Exception as e:
                sys.stderr.write(f"[brain] auto-ack failed for {req['id']}: {e}\n")
        return

    # Dedup: the brain re-sends pending requests on every SSE reconnect. If we
    # already have a popup open / handled this id this session, don't stack
    # another window for it.
    if req["id"] in _pending_received:
        sys.stderr.write(f"[brain] {req['id']} already shown this session — skip duplicate popup\n")
        return

    _pending_received[req["id"]] = req

    # ── Tier-gated approval (Variant B — see docs/TIER-POLICY.md) ──
    # blocked      → silent deny, no popup
    # trusted/self → auto-approve the SAFE kinds (task_request/delegate/
    #                compute_request = queued-not-executed; file_read = bounded
    #                to share-roots) with NO popup. command_exec still needs ONE
    #                click even for trusted (executing arbitrary commands is the
    #                one thing we don't hand out silently — Variant A would drop
    #                this last click; documented, deliberately not enabled).
    # acquaintance → one popup for everything (default for unknown senders).
    tier = _friend_tier(req.get("from", ""))
    rtype = req.get("type")
    QUEUEABLE = {"task_request", "delegate", "compute_request"}

    if tier == "blocked":
        sys.stderr.write(f"[brain] {req['id']} from blocked {req['from']} — silent deny\n")
        _send_response(req["id"], "denied", "")
        _pending_received.pop(req["id"], None)
        return

    if tier in ("self", "trusted") and rtype in (QUEUEABLE | {"file_read"}):
        decision = "approved"  # automated — no popup for trusted safe kinds
        sys.stderr.write(f"[brain] auto-approved {rtype} {req['id']} (tier={tier} {req['from']}, no popup)\n")
    else:
        if not _claim_popup(req["id"]):          # only ONE of the N MCPs pops this id
            sys.stderr.write(f"[brain] {req['id']} popup claimed by another MCP — skip dup\n")
            _pending_received.pop(req["id"], None)
            return
        decision = _show_popup(req)  # acquaintance (any) OR trusted command_exec

    if decision == "timeout":
        # User didn't answer (dialog timed out / closed). Leave it PENDING:
        # don't send a denial, and keep it in _pending_received so we don't
        # re-popup it this session. The brain still holds it pending, so a
        # fresh session (Claude restart) will surface it again.
        sys.stderr.write(f"[brain] {req['id']} popup timed out — left pending, NOT denied\n")
        return

    if decision != "approved":
        _send_response(req["id"], "denied", "")
        sys.stderr.write(f"[brain] denied {req['id']}\n")
        _pending_received.pop(req["id"], None)
        return

    # task_request / delegate / compute_request: don't auto-fulfill — queue for next chat.
    # The recipient's next conversation with their agent will surface it.
    # (QUEUEABLE defined above in the tier block.)
    if req.get("type") in QUEUEABLE:
        task_path = TASKS_DIR / f"{req['id']}.json"
        task_path.write_text(json.dumps(req, indent=2, ensure_ascii=False), encoding="utf-8")
        ack = (
            f"{req['type'].upper()} ACCEPTED by {BRAIN_USER}. Queued for their next chat session.\n"
            f"They'll work it manually and call complete_task() when done.\n"
            f"Target: {req['target']}"
        )
        _send_response(req["id"], "approved", ack)
        sys.stderr.write(f"[brain] queued {req['type']} {req['id']} → {task_path}\n")
        _pending_received.pop(req["id"], None)
        return

    # file_read / command_exec — auto-fulfill
    body, error = _fulfill(req)
    if error:
        _send_response(req["id"], "denied", f"fulfillment failed: {error}")
        sys.stderr.write(f"[brain] auto-denied {req['id']} (fulfill error: {error})\n")
    else:
        _send_response(req["id"], "approved", body)
        sys.stderr.write(f"[brain] approved {req['id']} ({len(body)} chars sent)\n")
    _pending_received.pop(req["id"], None)


# ─────────────── SSE consumer thread ───────────────

def _sse_consumer() -> None:
    """Long-lived SSE consumer. Reconnects on drop."""
    url = f"{BRAIN_URL}/events"
    backoff = 1
    while True:
        try:
            sys.stderr.write(f"[sse] connecting as {BRAIN_USER}…\n")
            with requests.get(
                url,
                params={"user": BRAIN_USER},
                headers={**_hdr(), "Accept": "text/event-stream"},
                stream=True,
                timeout=(10, None),  # connect timeout, no read timeout
            ) as resp:
                if resp.status_code != 200:
                    sys.stderr.write(f"[sse] auth/connect failed: {resp.status_code} {resp.text[:200]}\n")
                    time.sleep(min(backoff, 30))
                    backoff = min(backoff * 2, 30)
                    continue
                backoff = 1
                sys.stderr.write(f"[sse] connected\n")
                event_name = "message"
                data_buf: list[str] = []
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if raw_line is None:
                        continue
                    if raw_line == "":  # dispatch
                        if not data_buf:
                            event_name = "message"
                            continue
                        data = "\n".join(data_buf)
                        data_buf = []
                        try:
                            payload = json.loads(data)
                        except json.JSONDecodeError:
                            event_name = "message"
                            continue
                        if event_name == "request":
                            # Skip our own outgoing-history records — they're
                            # only persisted so the browser chat can replay
                            # them on reload, not for us to react to.
                            if payload.get("direction") == "out":
                                event_name = "message"
                                continue
                            # Spawn thread to handle this so SSE loop keeps reading
                            threading.Thread(
                                target=_handle_incoming_request,
                                args=(payload,),
                                daemon=True,
                            ).start()
                        elif event_name == "response":
                            _received_responses[payload["in_reply_to"]] = payload
                            sys.stderr.write(
                                f"[brain] response received for {payload['in_reply_to']}: {payload['decision']}\n"
                            )
                        elif event_name == "claim_lost":
                            # Sprint 2: someone else won a route_prompt race we
                            # were a candidate for. Mark so receiver-side popup
                            # (Step 3) can auto-dismiss. Also drop from pending.
                            rid = payload.get("route_id", "")
                            _lost_races.add(rid)
                            _pending_received.pop(rid, None)
                            sys.stderr.write(
                                f"[brain] claim_lost {rid} (won by {payload.get('won_by')})\n"
                            )
                        elif event_name == "connected":
                            pass
                        event_name = "message"
                    elif raw_line.startswith(":"):
                        # comment / heartbeat
                        continue
                    elif raw_line.startswith("event:"):
                        event_name = raw_line[6:].strip()
                    elif raw_line.startswith("data:"):
                        data_buf.append(raw_line[5:].lstrip())
        except Exception as e:
            sys.stderr.write(f"[sse] disconnected: {e}; reconnecting in {backoff}s\n")
            time.sleep(min(backoff, 30))
            backoff = min(backoff * 2, 30)


# ─── Variant D/D+: background update watcher ───
# D : flag when the server reports a newer MCP_VERSION (status_resource nudges).
# D+: also DOWNLOAD the newer mcp_local.py and write it over ~/.gpu/gpu_mcp.py
#     so the NEXT Claude restart runs it. We never os.execv mid-session — that
#     would break the live MCP stdio handshake. Download-only, apply-next-restart.
_server_mcp_version: str | None = None      # D : server has this newer version
_staged_update_version: str | None = None   # D+: we wrote this version to disk


def _download_get(path: str, timeout: int = 20):
    """GET a /download/* file. Prefer Bearer (per-user token / post-cutover); fall back to
    Basic team:BRAIN_PASSWORD while the Caddy basic_auth wall is still up. Auto-adapts across
    the admin=identity cutover with NO flag-day: Bearer→401 under the live wall falls back to
    Basic; once the wall is dropped + the server gate accepts Bearer, Bearer just works."""
    url = f"{BRAIN_URL}{path}"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {BRAIN_PASSWORD}"}, timeout=timeout)
        if r.status_code not in (401, 403):
            return r
    except Exception:
        pass
    _cred = base64.b64encode(f"team:{BRAIN_PASSWORD}".encode()).decode()
    return requests.get(url, headers={"Authorization": f"Basic {_cred}"}, timeout=timeout)


def _try_stage_update(expected_ver: str) -> None:
    """D+: fetch /download/mcp.py and write it over our own file on disk, so the
    next Claude restart picks it up. Atomic (tmp + os.replace), sanity-guarded,
    and never re-stages the same version. Failures are swallowed — staging is a
    best-effort convenience, the D nudge still tells the user to restart."""
    global _staged_update_version
    if _staged_update_version == expected_ver:
        return  # already staged this exact version this session
    try:
        r = _download_get("/download/mcp.py")
        if not r.ok:
            return
        remote = r.text
        # Sanity guard: never write garbage over a working MCP. It must look
        # like our file and carry the version we expected from /healthz.
        if "FastMCP" not in remote or "MCP_VERSION" not in remote:
            return
        m = re.search(r'^MCP_VERSION\s*=\s*["\']([^"\']+)["\']', remote, re.MULTILINE)
        got = m.group(1) if m else None
        if got != expected_ver:
            return  # /healthz and /download disagree — skip, try next cycle
        self_path = Path(__file__).resolve()
        tmp = self_path.with_name(self_path.name + ".new")
        tmp.write_text(remote, encoding="utf-8")
        os.replace(tmp, self_path)  # atomic swap; Python already holds bytecode
        _staged_update_version = got
        sys.stderr.write(
            f"[update] staged gpu_mcp.py {MCP_VERSION} -> {got}; "
            f"restart Claude to apply\n"
        )
    except Exception as e:
        sys.stderr.write(f"[update] stage failed: {e}\n")


# Cockpit sidecars the MCP distributes to EVERY platform (Mac + Windows) by
# itself — no install-script edit, no room_agent dependency. Both recipes live in
# the server `instructions` below. Mirrors _try_stage_update's auth + atomic write.
# Best-effort: never breaks the MCP.
#   • await_reply.py  — reply-watcher the agent launches after a dm/request_command
#   • team_inbox.py   — per-turn pull so a teammate's cross-message reaches THIS
#                       live session (with the repo open), not just the no-repo
#                       headless sandbox delegate. This is what makes a teammate's
#                       real coding session reachable (e.g. for a real code review).
_REACHABILITY_SIDECARS = ("await_reply.py", "team_inbox.py")


def _ensure_sidecar(name: str) -> None:
    """Download /download/<name> into ~/.gpu if missing or changed. So a user who
    connected through the website (no repo, any OS) still gets the reply-watcher
    file, kept fresh by the same /healthz cycle that self-stages the MCP."""
    try:
        r = _download_get(f"/download/{name}")
        if not r.ok or "def " not in r.text or len(r.text) < 200:
            return  # 404 / error page / truncated → skip
        dst = Path.home() / ".gpu" / name
        cur = dst.read_text(encoding="utf-8") if dst.exists() else ""
        if cur != r.text:
            tmp = dst.with_name(dst.name + ".new")
            tmp.write_text(r.text, encoding="utf-8")
            os.replace(tmp, dst)
            sys.stderr.write(f"[sidecar] synced {name}\n")
    except Exception as e:
        sys.stderr.write(f"[sidecar] sync {name} failed: {e}\n")


def _update_watch() -> None:
    """Poll /healthz (already in Caddy allowlist) every 5 min. When the server
    reports a newer version: flag it (D) and stage the new file to disk (D+).

    CRLF-safe: compares the MCP_VERSION *string constant*, not a file hash, so
    Windows LF→CRLF rewrites can't trigger a false 'outdated' signal. Runs in a
    daemon thread — tool calls only read the cached flags, never the network."""
    global _server_mcp_version
    while True:
        for _sc in _REACHABILITY_SIDECARS:
            _ensure_sidecar(_sc)          # ensure ~/.gpu/await_reply.py present+fresh
        try:
            r = requests.get(f"{BRAIN_URL}/healthz", headers=_hdr(), timeout=8)
            if r.ok:
                srv = (r.json() or {}).get("mcp_version")
                if isinstance(srv, str) and srv and srv != MCP_VERSION:
                    _server_mcp_version = srv
                    # D+: only stage when strictly newer (date.counter compares
                    # lexically); never downgrade if the server is somehow older.
                    if srv > MCP_VERSION:
                        _try_stage_update(srv)
                else:
                    _server_mcp_version = None
        except Exception:
            pass  # network blip — try again next cycle, never crash the MCP
        time.sleep(300)  # every 5 min


# Start SSE consumer immediately on module load (when Claude Code spawns this MCP)
threading.Thread(target=_sse_consumer, daemon=True).start()
# Start the update watcher (Variant D/D+ — see docs/MCP-HOT-RELOAD.md)
threading.Thread(target=_update_watch, daemon=True, name="update-watch").start()


# ─────────────── MCP server ───────────────

# Server `instructions` — surfaced to the agent by the client (like other MCPs'
# "MCP Server Instructions"). This is how the reply-watcher recipe reaches EVERY
# connected user (any OS, even a website signup with no repo), and auto-updates
# with the MCP via self-stage. Keep it short + actionable.
GPU_INSTRUCTIONS = """\
gpu links your agent to your teammates' agents (tools: dm, request_command, request_file, \
ask_team, presence, fetch_response, and shared rooms via room_*). What you send reaches the \
teammate's OWN agent, which answers you or acts on your behalf.

FIRST-RUN ONBOARDING — if the file ~/.gpu/onboarding_pending exists, you were JUST installed: \
tell your human you're connected to Multiplayer, then (with their OK) call portrait_publish(...) \
so the network can find + route work to you, and delete ~/.gpu/onboarding_pending when done. This \
is a safety net — do it even if the install-time note in ~/.claude/CLAUDE.md never landed.

WAITING FOR A TEAMMATE'S REPLY — use the background reply-watcher, never a poll loop:
When you send a `dm` or `request_command` and you want to surface the teammate's REPLY back to \
your human, do NOT poll and do NOT block your turn (their agent may answer in seconds or "think" \
for minutes). Instead:
  1. Take the `id` (request_id) from the dm / request_command result.
  2. Run this as a BACKGROUND shell command, then END your turn:
        python ~/.gpu/await_reply.py <request_id> <target_user> [timeout_sec]   (default 3600s / 60min)
  3. When it exits, your harness re-invokes you with its output — surface it to your human:
        "REPLY from <user> after Ns: <body>"  -> the answer arrived
        "OFFLINE: <user> ... (dropped)"        -> target went offline; offer a retry
        "TIMEOUT: ... (still online)"           -> long task; relaunch to keep waiting
It is signal-driven (the watcher wakes you) so your turn stays free meanwhile, and it tells \
"thinking" (online, no reply yet) apart from "dropped" (offline) via presence. The watcher file \
is kept present + fresh by gpu automatically.

RECEIVING A TEAMMATE'S MESSAGE IN *THIS* SESSION — pull your team inbox each turn:
A teammate's `dm` is auto-answered by your headless background agent in a SANDBOX that has NO \
access to your repo/files — so it can only chat, never review or edit real code. To let a \
teammate reach THIS session (the one with your actual project open) — so you can read files, \
run, edit, and commit with full context — pull your inbox at the START of every turn, before \
anything else:
        python ~/.gpu/team_inbox.py
It is read-only, ~1s, and SILENT when there is nothing new (so it costs nothing on a quiet turn). \
If it prints a `[TEAM-INBOX]` block, a teammate wrote into your column: open your reply with \
"📨 From team: <one-line gist>", answer them USING this session's real context (repo, files, \
tools — e.g. do the actual code review against the real files), then continue your own task. \
This is the channel that delivers code-review / real-work asks to the agent that can actually \
see the code, instead of the no-repo sandbox. The inbox file is kept present + fresh by gpu \
automatically; it surfaces each teammate message exactly once and never breaks your turn.
"""

mcp = FastMCP("gpu", instructions=GPU_INSTRUCTIONS)


@mcp.tool()
def request_file(to: str, path: str, justification: str) -> dict[str, Any]:
    """Ask another architect's agent to share a file.

    Args:
        to: target user's handle (a teammate you're connected to). The OWNER of the file.
        path: absolute or ~-prefixed path on THEIR machine.
        justification: short WHY (the human sees this in popup).

    The recipient's Mac shows a popup with Approve/Deny.
    On Approve, their agent auto-reads and sends the file back.
    Use `fetch_response(request_id)` afterwards.
    """
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": to, "type": "file_read",
              "target": path, "justification": justification},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def request_command(to: str, command: str, justification: str) -> dict[str, Any]:
    """Ask another architect's agent to run a shell command and share the output.

    Use sparingly — recipient sees the exact command in popup before deciding.
    Sensitive commands (sudo, rm -rf, curl|sh, etc.) trigger a 2-step popup.
    """
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": to, "type": "command_exec",
              "target": command, "justification": justification},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def request_task(to: str, task: str, justification: str) -> dict[str, Any]:
    """Ask another architect to do an OPEN-ENDED task — not auto-fulfilled.

    Use this for things their agent needs human judgment + tooling to perform.
    Examples:
      - request_task("igor", "give me access to Google Analytics for aiconic.company",
                     "running attribution analysis on dora-personal-voice article")
      - request_task("vitalik", "add my SSH public key to your authorized_keys",
                     "I need to ssh into your box to debug the FLUX server")
      - request_task("igor", "create a Cloudflare DNS record for staging.aiconic.company",
                     "deploying staging mirror for QA")

    Flow:
      1. Recipient gets a popup ASKING TWICE (task_requests are always sensitive)
      2. On Approve, task is queued on their machine (NOT auto-fulfilled)
      3. Their next chat with their agent surfaces this task
      4. They tell their agent to handle it, agent works through it
      5. When done, their agent calls `complete_task(request_id, result_summary)`
      6. You can poll `fetch_response(request_id)` to get the completion

    Returns the created request. Initial response will be 'approved + task queued'.
    Final completion comes later via complete_task().
    """
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": to, "type": "task_request",
              "target": task, "justification": justification},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


QUEUEABLE_TYPES = {"task_request", "delegate", "compute_request"}


def _load_completed_task_ids() -> set[str]:
    try:
        return set(json.loads(COMPLETED_TASKS_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _mark_task_completed(req_id: str) -> None:
    ids = _load_completed_task_ids()
    ids.add(req_id)
    try:
        COMPLETED_TASKS_FILE.write_text(json.dumps(sorted(ids)), encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"[tasks] failed to record completed {req_id}: {e}\n")


@mcp.tool()
def list_my_queued_tasks() -> list[dict[str, Any]]:
    """List tasks others queued FOR ME to handle, approved in ANY channel.

    Source of truth is the BRAIN: we pull approved task_request/delegate/
    compute_request addressed to me (status=approved). This means a task I
    approved via Telegram or the web panel reaches the agent too — not only
    ones approved through the desktop popup. We also fold in the local
    ~/.gpu/tasks/ queue (popup-approved, works offline) and drop anything
    already finished via complete_task().
    """
    completed = _load_completed_task_ids()
    by_id: dict[str, dict] = {}

    # Server: approved queueable tasks addressed to me (any approval channel).
    try:
        r = requests.get(
            f"{BRAIN_URL}/inbox",
            params={"user": BRAIN_USER, "kind": "request", "status": "approved", "limit": 100},
            headers=_hdr(), timeout=10,
        )
        if r.ok:
            for t in r.json():
                if t.get("type") in QUEUEABLE_TYPES and t.get("id") not in completed:
                    by_id[t["id"]] = t
    except Exception as e:
        sys.stderr.write(f"[tasks] server fetch failed (using local only): {e}\n")

    # Local queue (popup-approved; also offline fallback).
    for f in sorted(TASKS_DIR.glob("*.json")):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if t.get("id") not in completed:
            by_id.setdefault(t["id"], t)

    return list(by_id.values())


@mcp.tool()
def complete_task(request_id: str, result_summary: str) -> dict[str, Any]:
    """Mark a queued task as DONE and send the result to the original requester.

    Args:
        request_id: the req_XXX id from list_my_queued_tasks()
        result_summary: what was done, any links/IDs/credentials the requester needs

    Removes the task from local queue + sends a follow-up response via brain.
    Note: the brain already sent an initial 'approved + queued' response when
    popup was approved; this is a SECOND message with the actual deliverable.
    Uses a free_text wrapper since the request was already marked approved.
    """
    task_path = TASKS_DIR / f"{request_id}.json"
    task = None
    if task_path.exists():
        task = json.loads(task_path.read_text(encoding="utf-8"))
    else:
        # Approved via TG/web → not in the local queue. Look it up on the server
        # so we still know who to send the result to.
        try:
            r0 = requests.get(
                f"{BRAIN_URL}/inbox",
                params={"user": BRAIN_USER, "kind": "request", "limit": 200},
                headers=_hdr(), timeout=10,
            )
            if r0.ok:
                for t in r0.json():
                    if t.get("id") == request_id:
                        task = t
                        break
        except Exception:
            pass
    if task is None:
        return {"error": f"task {request_id} not found (local queue or server inbox)"}
    # Send a NEW free_text request (from me TO original requester) carrying the result
    body = (
        f"📬 TASK COMPLETED: {task['target']}\n\n"
        f"By: {BRAIN_USER}\n"
        f"Original request: {request_id}\n\n"
        f"{result_summary}"
    )
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": task["from"], "type": "free_text",
              "target": f"task-completion:{request_id}",
              "justification": body},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    task_path.unlink(missing_ok=True)
    # Record completion so list_my_queued_tasks (which now also pulls approved
    # tasks from the server) doesn't re-surface this one on the next session.
    _mark_task_completed(request_id)
    return {"completed": request_id, "notification_sent": r.json()}


@mcp.tool()
def fetch_response(request_id: str) -> dict[str, Any]:
    """Get the response to one of my requests.

    Returns the response from cache (if recipient already approved/denied via SSE),
    or fetches from inbox.
    """
    if request_id in _received_responses:
        return _received_responses[request_id]
    # Fallback: poll inbox in case SSE dropped during response
    r = requests.get(
        f"{BRAIN_URL}/inbox",
        params={"user": BRAIN_USER, "kind": "response", "limit": 100},
        headers=_hdr(), timeout=10,
    )
    r.raise_for_status()
    matches = [m for m in r.json() if m.get("in_reply_to") == request_id]
    if not matches:
        return {"status": "no_response_yet", "request_id": request_id}
    return matches[0]


@mcp.tool()
def list_outgoing() -> list[dict[str, Any]]:
    """List recent responses I've received (cached from SSE)."""
    return list(_received_responses.values())


@mcp.tool()
def list_pending_for_me() -> list[dict[str, Any]]:
    """List requests currently waiting for my decision (popups may already be open)."""
    return list(_pending_received.values())


@mcp.tool()
def presence() -> dict[str, str]:
    """Who is currently online (Claude Code / Codex open with brain MCP active)."""
    r = requests.get(f"{BRAIN_URL}/presence", headers=_hdr(), timeout=10)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def enable_presence(confirm: bool = False) -> dict[str, Any]:
    """Turn ON presence — the small always-on macOS menu-bar app (the "continuous"
    upgrade). OPT-IN: the default install is MCP-only with zero background processes.
    Presence lets your agent auto-help a friend even when the editor is closed.

    Offer this ONCE, after the user's first accepted friend, and only run it when the
    user clearly agrees. Fully reversible (see the result's `uninstall`).

    - confirm=False (default): returns what it will do + the trade-off, runs NOTHING.
    - confirm=True: installs presence via the standalone install-tray.sh (fetches
      menu_bar.py, installs rumps, writes + loads com.gpu.menubar.plist). macOS only.

    NOTE: the menu-bar installer is opt-in BETA — not yet validated on a clean Mac
    (tracked for Vitalik, onboarding owner). It is reversible if anything misfires.
    """
    install_url = f"{BRAIN_URL}/install-tray.sh"
    plist = str(Path.home() / "Library" / "LaunchAgents" / "com.gpu.menubar.plist")
    uninstall = f'launchctl bootout "gui/$(id -u)" "{plist}"; rm -f "{plist}"'
    if sys.platform != "darwin":
        return {"ok": False, "platform": sys.platform,
                "note": "Presence (menu-bar app) is macOS-only. On Windows the tray ships with "
                        "the standard install.ps1; nothing extra to enable here."}
    if not confirm:
        return {"ok": True, "action": "would_install",
                "what": "A small always-on app in your menu bar so your agent can auto-help a "
                        "friend even when your editor is closed (the 'continuous' tier).",
                "tradeoff": "Adds ONE small always-on background app. Fully reversible. Opt-in BETA.",
                "to_install": f"call enable_presence(confirm=True) — or run: curl -sSL {install_url} | sh",
                "uninstall": uninstall}
    # confirm=True → run the standalone installer. Bearer-first (per-user token / post-cutover),
    # Basic team:PW fallback while the Caddy wall is up — mirrors install.sh's dl().
    try:
        fetch = (f'(curl -fsSL -H "Authorization: Bearer $BRAIN_PASSWORD" "{install_url}" '
                 f'|| curl -fsSL -u "team:$BRAIN_PASSWORD" "{install_url}") | sh')
        env = dict(os.environ)
        env["BRAIN_URL"] = BRAIN_URL
        env["BRAIN_PASSWORD"] = BRAIN_PASSWORD
        proc = subprocess.run(["sh", "-c", fetch], capture_output=True, text=True,
                              timeout=300, env=env)
        out = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
        if proc.returncode != 0:
            return {"ok": False, "returncode": proc.returncode, "output": out[-2000:],
                    "manual": f"You can also run it yourself: curl -sSL {install_url} | sh",
                    "uninstall": uninstall}
        return {"ok": True, "action": "installed",
                "note": "Presence is on — look for the gpu app and ◉ in the menu bar.",
                "output": out[-1500:], "uninstall": uninstall}
    except Exception as e:
        return {"ok": False, "error": str(e),
                "manual": f"Run it yourself: curl -sSL {install_url} | sh", "uninstall": uninstall}


# ─────────────── new communication tools (Sprint 1) ───────────────

@mcp.tool()
def notify(to: str, msg: str) -> dict[str, Any]:
    """Fire-and-forget notification — NO popup on recipient side.
    Appears in their next-chat resource feed. Use for status updates, fyi, low-importance pings.
    """
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": to, "type": "notify",
              "target": msg[:200], "justification": "notify"},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def broadcast(msg: str) -> dict[str, Any]:
    """Fan-out a single message to ALL currently-online users (except yourself).
    Use sparingly — every architect's agent will see it.
    """
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": "*", "type": "broadcast",
              "target": msg[:500], "justification": "broadcast"},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def dm(to: str, msg: str, reply_to: str | None = None) -> dict[str, Any]:
    """Direct chat with another architect's agent. Threaded if `reply_to` is set
    (the request_id you're replying to). No popup — appears in their next-chat feed.
    """
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": to, "type": "dm",
              "target": msg, "justification": "dm",
              "parent_id": reply_to},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def ask_team(question: str) -> dict[str, Any]:
    """Broadcast a question to ALL team members (core+extended).
    Each receiving agent surfaces it to its user — they reply via `dm(reply_to=req_id)`.
    Use for: 'who has Cerebras API key?', 'who's worked on Qwen3?', etc.
    """
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": "*", "type": "ask_team",
              "target": question, "justification": "team question"},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def delegate(to: str, task: str, context: str = "") -> dict[str, Any]:
    """Hand off a task with current chat context. Like request_task but with
    a `context` block so the recipient's agent picks up where you left off.

    Recipient gets a 2-step popup → queues if approved → handles in next session →
    `complete_task()` notifies you when done.
    """
    full = task
    if context:
        full = f"{task}\n\n---CONTEXT---\n{context}"
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": to, "type": "delegate",
              "target": full, "justification": "delegation"},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def request_compute(to: str, gpu_type: str, hours: float, justification: str) -> dict[str, Any]:
    """Ask another architect to lend their GPU box for a window of time.
    Recipient sees 2-step popup with the request details. On approve, queued as task
    for them to actually grant access (ssh key add, instance spin-up, etc.).

    Args:
        to: target user with GPU access (typically vitalik or igor)
        gpu_type: e.g. 'RTX 3090', 'A100 40GB', 'Cerebras'
        hours: estimated duration
        justification: what you'll run (FLUX training, eval suite, etc.)
    """
    target = f"GPU: {gpu_type} for ~{hours}h"
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={"from": BRAIN_USER, "to": to, "type": "compute_request",
              "target": target, "justification": justification,
              "metadata": {"gpu_type": gpu_type, "hours": hours}},
        headers=_hdr(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


# ─────────────── Sprint 2: shared compute pool (quota + route_prompt) ─────

# Cap on attachment payload — 256 KB is enough for code review / refactor of
# a handful of files but won't blow up the brain disk if abused.
_ROUTE_ATTACHMENT_MAX_BYTES = 256 * 1024


@mcp.tool()
def report_quota(state: str, reason: str = "") -> dict[str, Any]:
    """Tell the brain how much room you have left in your current Claude
    Code / Codex window. Call this when something changes — fresh window,
    rate-limited, getting tight.

    Args:
        state: one of 'hot' (lots of capacity, accept route_prompts),
               'warm' (some capacity), 'cold' (limited, prefer not to
               receive), or 'dead' (rate-limited).
        reason: optional one-liner — "fresh 5h window", "rate-limited at
                14:23", etc. Shown to teammates when they call
                quota_status().

    Auto-call this with state='dead' the moment Claude Code returns a
    rate-limit error — that's the cue for the team's auto-router to
    stop sending you route_prompts until you recover.
    """
    if state not in ("hot", "warm", "cold", "dead"):
        return {"ok": False, "error": f"state must be hot|warm|cold|dead, got '{state}'"}
    r = requests.post(
        f"{BRAIN_URL}/quota",
        json={"user": BRAIN_USER, "state": state, "reason": reason},
        headers=_hdr(), timeout=10,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
def quota_status() -> dict[str, Any]:
    """See everyone's currently-reported quota state. Each entry has:
        state          — the last self-report (hot/warm/cold/dead)
        effective_state — same, but flips to 'unknown' if older than 6h
                          (the auto-router uses effective_state)
        reason          — optional human-readable note
        updated_at      — ISO timestamp of last report

    Use this before a heavy task to decide whether to run it yourself or
    route_prompt() it to a teammate with more capacity.
    """
    r = requests.get(f"{BRAIN_URL}/quota", headers=_hdr(), timeout=10)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def route_prompt(
    prompt: str,
    attachments: dict[str, str] | None = None,
    timeout_minutes: int = 15,
    max_msgs: int = 30,
    to: str = "auto",
) -> dict[str, Any]:
    """Route a self-contained Claude prompt to a teammate's machine for
    execution. Use this when your quota is low and the prompt doesn't
    need to know about your local repos beyond what you can paste in.

    The receiving teammate sees a popup with the prompt + attachment
    summary, clicks Approve, and a fresh `claude -p` runs in an
    isolated /tmp/gpu_route_<uuid>/ sandbox on THEIR machine. Output
    (stdout + any files written in the sandbox) comes back via
    fetch_response(route_id).

    Args:
        prompt: the full prompt to run. Must be self-contained — the
                routed Claude has NO access to your local files unless
                you put them in `attachments`.
        attachments: optional dict {filename: content} dropped into the
                     sandbox before execution. Total size capped at 256 KB.
                     Filenames are basenames only (no path separators).
        timeout_minutes: max wall-clock minutes for the sandboxed run.
                         Default 15.
        max_msgs: rough cap on Claude turns (also passed as --max-turns).
                  Default 30.
        to: 'auto' (broadcast race to all hot+online core teammates,
            first approver wins) or a specific username like 'igor'.

    Returns:
        For to='auto':  {route_id, candidates, race: true}.
                        Poll fetch_response(route_id) for the result.
        For to='<name>': normal single-recipient request payload.
    """
    attachments = attachments or {}
    # Validate filenames (basenames only — receiver writes to /tmp/<uuid>/<name>
    # so path traversal would let sender clobber arbitrary files)
    safe_attachments: dict[str, str] = {}
    total_bytes = 0
    for name, content in attachments.items():
        if "/" in name or "\\" in name or name.startswith("."):
            return {"ok": False, "error": f"attachment name '{name}' must be a basename (no / \\ or leading dot)"}
        if not isinstance(content, str):
            return {"ok": False, "error": f"attachment '{name}' content must be string"}
        total_bytes += len(content.encode("utf-8"))
        safe_attachments[name] = content
    if total_bytes > _ROUTE_ATTACHMENT_MAX_BYTES:
        return {
            "ok": False,
            "error": f"attachments total {total_bytes} bytes exceeds cap {_ROUTE_ATTACHMENT_MAX_BYTES}",
        }
    if timeout_minutes < 1 or timeout_minutes > 120:
        return {"ok": False, "error": "timeout_minutes must be between 1 and 120"}
    if max_msgs < 1 or max_msgs > 200:
        return {"ok": False, "error": "max_msgs must be between 1 and 200"}

    payload = {
        "from": BRAIN_USER,
        "to": to,
        "type": "route_prompt",
        "target": prompt,
        "justification": f"route_prompt timeout={timeout_minutes}m max_msgs={max_msgs}",
        "metadata": {
            "attachments": safe_attachments,
            "attachment_count": len(safe_attachments),
            "attachment_total_bytes": total_bytes,
            "timeout_minutes": timeout_minutes,
            "max_msgs": max_msgs,
        },
    }
    r = requests.post(f"{BRAIN_URL}/requests", json=payload, headers=_hdr(), timeout=15)
    if r.status_code == 503:
        # Surface the "no one is hot" error as a structured response
        return {"ok": False, "error": r.json().get("detail", r.text), "status": 503}
    r.raise_for_status()
    return r.json()


# ─────────────── friends ───────────────

@mcp.tool()
def list_friends() -> dict[str, Any]:
    """List all registered users with their tiers (core/extended/external)."""
    r = requests.get(f"{BRAIN_URL}/friends", headers=_hdr(), timeout=10)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def invite_friend(name: str, tier: str = "extended") -> dict[str, Any]:
    """Invite a new user to the gpu network. Only core-tier users may invite.

    Args:
        name: lowercase username (e.g. 'ivan', 'client_acme')
        tier: 'extended' (default — can request files + tasks but not commands)
              or 'external' (limited to dm/notify, for clients/contractors)
              or 'core' (full peer — invite only trusted teammates)

    After invitation, the new user installs by running:
        curl -sSL -u 'team:<your-team-password>' https://gpu.social/install.sh | sh
    with their username, using the same team password.
    """
    if tier not in ("core", "extended", "external"):
        return {"error": "tier must be core, extended, or external"}
    r = requests.post(
        f"{BRAIN_URL}/friends",
        json={"by": BRAIN_USER, "name": name, "tier": tier},
        headers=_hdr(), timeout=10,
    )
    if r.status_code != 200:
        return {"error": r.text, "status": r.status_code}
    return r.json()


# ─────────────── friend GRAPH (peer-to-peer, mutual, revocable) ───────────────
# Distinct from invite_friend/list_friends (the global roster). A *friendship*
# is a mutual edge: it's the unit of trust for SHARING CONTEXT — friends can
# invite each other into project rooms (room_invite). Non-friends can only be
# asked one-off questions (dm / ask_network) and never get room access. Always
# human-gated: you only send/accept a request when your human tells you to.

@mcp.tool()
def friend_request(nickname: str = "", to: str = "", note: str = "") -> dict[str, Any]:
    """Propose FRIENDSHIP to another gpu user. The SAFE way is by their UNIQUE NICKNAME
    (e.g. 'Vit723') — pass it EXACTLY as your human gave it; the server matches it
    deterministically (one owner, or nobody — it never guesses a near-match), so a request
    can't go to an impostor. Use `to=<handle>` only for a teammate whose exact handle you
    already know. NEVER guess a nickname/handle from a display name — if unsure, ask your
    human for the exact nickname. The other person's human approves (they see your
    provenance). Set your own nickname with set_nickname() so others can add you.

    Args:
        nickname: their exact unique nickname (preferred, safe)
        to: their exact handle (only if you truly know it)
        note: optional one-line context shown to them
    """
    if not nickname and not to:
        return {"error": "give a nickname (preferred) or an exact handle 'to'"}
    return _room_post("/friend/request", {"nickname": nickname, "to": to, "note": note})


@mcp.tool()
def set_nickname(nickname: str) -> dict[str, Any]:
    """Set YOUR unique gpu nickname (3-20 letters/digits/underscore, e.g. 'Vit723') — what
    you give people so they can add you as a friend. Globally unique (server-enforced), so
    nobody can impersonate you by display name. Call my_nickname()/this when your human
    wants to pick or share their handle."""
    r = requests.post(f"{BRAIN_URL}/nickname", json={"nickname": nickname, "user": BRAIN_USER},
                      headers=_hdr(), timeout=10)
    if r.status_code != 200:
        return {"error": r.text, "status": r.status_code}
    return r.json()


@mcp.tool()
def my_nickname() -> dict[str, Any]:
    """Your own unique nickname (what to give people so they can friend you)."""
    return _room_get(f"/nickname?user={BRAIN_USER}")


# ─────────────── teams (a GROUP — distinct from friend = 1:1) ───────────────

@mcp.tool()
def create_team(name: str) -> dict[str, Any]:
    """Create a TEAM (a named group) when your human says "создай команду X". You're the
    owner + first member. Add others with team_invite (by their unique nickname; they
    approve). Members see each other + can make team-scoped projects. Returns the team id."""
    return _room_post("/team", {"name": name})


@mcp.tool()
def team_invite(team: str, nickname: str = "", to: str = "") -> dict[str, Any]:
    """Invite someone into a team you're in — by their UNIQUE NICKNAME (preferred, exact,
    no guessing) or exact handle. They approve (nobody is added without consent). `team`
    is the team id from create_team/team_list."""
    if not nickname and not to:
        return {"error": "give a nickname (preferred) or exact handle 'to'"}
    return _room_post("/team/invite", {"team": team, "nickname": nickname, "to": to})


@mcp.tool()
def team_respond(invite_id: str, accept: bool = True) -> dict[str, Any]:
    """Accept (or decline) a TEAM invite addressed to you — after your human decides.
    invite_id comes from the invite notification or team_list(). On accept, TELL YOUR
    HUMAN what just unlocked: you now see this team's members + their shared projects, and
    can open team-scoped rooms (room_open with team=…). Progressive disclosure keeps them
    oriented."""
    return _room_post("/team/respond", {"invite_id": invite_id, "accept": accept})


@mcp.tool()
def team_list() -> dict[str, Any]:
    """Your teams (+ their members) and pending team invites you can accept."""
    return _room_get(f"/team/list?user={BRAIN_USER}")


@mcp.tool()
def friend_respond(request_id: str, accept: bool = True) -> dict[str, Any]:
    """Accept or decline a pending friend request addressed to you. Only call
    this AFTER your human decides — first explain to them that becoming friends
    lets you two invite each other into shared rooms (shared context flows both
    ways) and that it's revocable. `request_id` comes from the incoming
    friend-request notification or from friend_list(). On accept, TELL YOUR HUMAN what
    just unlocked: you can now invite this friend into rooms, and ask their agent things
    via dm/ask_network. Surface newly-available capabilities as relationships grow."""
    return _room_post("/friend/respond", {"request_id": request_id, "accept": accept})


@mcp.tool()
def unfriend(other: str) -> dict[str, Any]:
    """End a friendship. Either party may unfriend at any time; the other side is
    notified. Existing shared rooms keep them as a member until explicitly
    removed, but no NEW room invites are possible once unfriended."""
    return _room_post("/friend/unfriend", {"other": other})


@mcp.tool()
def friend_list() -> dict[str, Any]:
    """Your friends + pending friend requests (incoming = you can accept/decline;
    outgoing = ones you've sent). This is the peer friend GRAPH — distinct from
    list_friends(), which is the global user roster with tiers."""
    return _room_get(f"/friend/list?user={BRAIN_USER}")


# ─────────────── portrait (identity layer — your tiered self-model) ───────────────

@mcp.tool()
def portrait_publish(public: str = "", friends: str = "", team: str = "") -> dict[str, Any]:
    """Publish YOUR shareable portrait tiers to the network so teammates' agents can read
    you (even while your machine is offline). `public` = what NON-friends see (thin);
    `friends` = what friends see (professional/technical + what you build); `team` = what
    your CO-FOUNDERS (org/core) see (+ business-confidential: revenue, deals, pricing).
    Your PRIVATE tier (personal legal/tax, secrets) NEVER goes here. Typically your daily
    portrait agent calls this after refreshing ~/.gpu/me.{public,md,team}.md."""
    return _room_post("/portrait", {"public": public, "friends": friends, "team": team})


@mcp.tool()
def portrait_get(user: str) -> dict[str, Any]:
    """Read another user's portrait — the network returns the tier YOU'RE entitled to
    (friend → deep 'friends' tier; otherwise thin 'public'). Use before answering 'as
    them', or to decide who actually knows X."""
    return _room_get(f"/portrait/{user}")


@mcp.tool()
def announce(text: str, title: str = "📢 multiplayer.ai") -> dict[str, Any]:
    """ADMIN control-plane REACH: message EVERY user on the network from the
    multiplayer.ai brand (online AND offline — lands in their inbox + surfaces in their
    agent's read_messages). Use when your human says 'напиши всем' / 'announce to
    everyone'. Team-password gated (only the core team can send)."""
    r = requests.post(f"{BRAIN_URL}/announce", json={"text": text, "title": title},
                      headers=_hdr(), timeout=20)
    if r.status_code != 200:
        return {"error": r.text, "status": r.status_code}
    return r.json()


@mcp.tool()
def who_knows(topic: str = "") -> dict[str, Any]:
    """Find who on the team knows / owns / has solved something. Returns the team's
    PORTRAITS (each at the tier you're entitled to). YOU are the router: read them, name
    the best-fit person and WHY, then — human-gated — `dm` them. `topic` lexically
    prefilters the corpus (top matches first) so this scales to 100s/1000s of people with
    no embedding model; you still do the final judgement over what comes back."""
    r = requests.get(f"{BRAIN_URL}/portrait/all", params={"q": topic, "limit": 40},
                     headers=_hdr(), timeout=15)
    r.raise_for_status()
    return r.json()


# ─────────────── Shared Room tools (the team brain) ───────────────
# Thin wrappers over the relay's live /room/* API. The agent uses these to
# PROPOSE a plan (decompose a goal into areas + owners), watch the live stream,
# post its own progress, and coordinate (Andon stop-the-line + work-stealing).
# Principle: agents PROPOSE & EXECUTE, the human who posted the goal APPROVES.
# Agents never approve or start a room — that gate stays with the human (TG/web).

def _room_get(path: str) -> dict[str, Any]:
    r = requests.get(f"{BRAIN_URL}{path}", headers=_hdr(), timeout=15)
    r.raise_for_status()
    return r.json()


def _room_post(path: str, body: dict) -> dict[str, Any]:
    # Shared-password auth → the relay reads the actor from `user` in the body.
    body = {**body, "user": BRAIN_USER}
    r = requests.post(f"{BRAIN_URL}{path}", json=body, headers=_hdr(), timeout=20)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def room_list() -> dict[str, Any]:
    """List shared rooms (team projects): id, goal, poster, status, updated.
    Status flow: drafting → approved → running → (draining on Andon) → done.
    Use to discover a room you should help PLAN (drafting, still no areas) or
    one you're working in (running)."""
    return _room_get("/rooms")


@mcp.tool()
def room_get(room_id: str) -> dict[str, Any]:
    """Full room state: goal, areas (each with owner + status), poster, status,
    feedback history, recent stream. Read this before proposing a plan or
    starting work so you know the goal and who owns what."""
    return _room_get(f"/room/{room_id}")


@mcp.tool()
def room_invite(room_id: str, invitee: str) -> dict[str, Any]:
    """Add another user into a room's shared context so they can read it and work
    in it. You must already be a room participant. To invite a NON-team user you
    must be FRIENDS with them first (friend_request → they accept); org teammates
    need no friendship. Only call after your human says to add the person. This is
    how a self-join outsider safely gets pulled into one specific project room
    without ever seeing the rest of the team's brain."""
    return _room_post(f"/room/{room_id}/invite", {"invitee": invitee})


@mcp.tool()
def room_suggest_owners(room_id: str, areas: list[str]) -> dict[str, Any]:
    """For a list of area names, suggest an owner for each from the network's
    competency index (who has solved similar work). Feed the result into
    room_propose. Areas with no strong match come back without an owner."""
    return _room_post(f"/room/{room_id}/suggest", {"areas": areas})


@mcp.tool()
def room_propose(room_id: str, areas: list[dict]) -> dict[str, Any]:
    """PROPOSE the plan: split the goal into 3-6 areas and assign an owner to
    each. `areas` = [{"area": "backend", "owner": "vitalik"},
    {"area": "frontend", "owner": "igor"}, ...]. This sets the room's DRAFT for
    the human poster to approve or refine — it does NOT start work. Workflow:
    read the goal with room_get, decompose it yourself, use room_suggest_owners
    to pick owners by expertise, then call this. The poster then approves in
    Telegram/web. Re-call to refine after feedback."""
    return _room_post(f"/room/{room_id}/draft", {"areas": areas})


@mcp.tool()
def room_stream(room_id: str, text: str, area: str = "", kind: str = "progress",
                role: str = "") -> dict[str, Any]:
    """Post a live progress update into the room (mirrored to the team's TG
    topic so everyone watches). Call this AS you work, not just at the end.
    `area` = the area you're working; `kind` = progress | blocker | done | note.
    `role` = a sub-label when SEVERAL of YOUR OWN agents share one room (e.g. "ITU",
    "Roma" — usually the project/chat you're in) so the room shows `you·ITU` vs `you·Roma`
    and attributes who's doing what. Leave empty when you're the only agent.
    Post a `done` line when your area is finished so the team can integrate."""
    return _room_post(f"/room/{room_id}/stream",
                      {"text": text, "area": area, "kind": kind, "role": role})


@mcp.tool()
def room_tail(room_id: str, limit: int = 30) -> dict[str, Any]:
    """Read a room's recent stream (latest `limit` events) plus its status and
    any active Andon alarm. Use to catch up before continuing, or before
    stealing a stalled area."""
    return _room_get(f"/room/{room_id}/stream?limit={limit}")


@mcp.tool()
def room_my_work() -> list[dict[str, Any]]:
    """List the areas assigned to ME across approved/running rooms — i.e. what I
    should be working on now. Each item: {room_id, goal, area, area_status,
    room_status}. The work loop: call this, then for each area do the work and
    room_stream progress (and a `done` line when finished)."""
    out: list[dict[str, Any]] = []
    for r in _room_get("/rooms").get("rooms", []):
        if r.get("status") not in ("approved", "running"):
            continue
        full = _room_get(f"/room/{r['id']}")
        for a in full.get("areas", []):
            if a.get("owner") == BRAIN_USER:
                out.append({
                    "room_id": r["id"], "goal": full.get("goal"),
                    "area": a.get("area"), "area_status": a.get("status"),
                    "room_status": full.get("status"),
                })
    return out


@mcp.tool()
def room_alarm(room_id: str, reason: str) -> dict[str, Any]:
    """Pull the Andon cord (stop-the-line). Raises a blocker → everyone drains
    in-flight work to a safe point and starts NO new work until it's cleared.
    Use when something breaks the shared contract (API change, broken build,
    conflicting assumption)."""
    return _room_post(f"/room/{room_id}/alarm", {"reason": reason})


@mcp.tool()
def room_resume(room_id: str) -> dict[str, Any]:
    """Clear the Andon alarm and return the room to running. Only the poster or
    whoever raised the alarm can clear it."""
    return _room_post(f"/room/{room_id}/resume", {})


@mcp.tool()
def room_steal(room_id: str, area: str) -> dict[str, Any]:
    """Take over an area whose owner is OFFLINE (work-stealing) and resume from
    their last stream. Fails if the current owner is online, or the room is in
    Andon/draining. Use when a teammate dropped and their chunk is stalled."""
    return _room_post(f"/room/{room_id}/steal", {"area": area})


@mcp.tool()
def room_open(goal: str, team: str = "") -> dict[str, Any]:
    """Open a NEW shared room for a goal (you become the poster). Pass `team`=<team id>
    to make it a TEAM project — every member of that team can see/work in it (you must be
    a member); omit it for a personal room you invite people into explicitly. Returns
    {room_id, status, poster}."""
    return _room_post("/room/goal", {"goal": goal, "team": team})


# ─────────────── inbound messages (DMs / notify / broadcast / ask_team) ───────────────

def _load_messages_from_disk() -> list[dict]:
    """Return all persisted messages, newest first."""
    out = []
    for f in sorted(MESSAGES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def _is_read(msg_id: str) -> bool:
    return (READ_MARKERS_DIR / f"{msg_id}.read").exists()


@mcp.tool()
def read_messages(unread_only: bool = True, limit: int = 50) -> list[dict[str, Any]]:
    """Get inbound messages (DMs, notify, broadcast, ask_team) addressed to me.

    Args:
        unread_only: if True (default), return only messages not yet marked read
        limit: cap on number returned (newest first)

    Use at start of session or when user asks 'что нового?' / 'есть сообщения?'.
    Surface them to the user, then call `mark_message_read(id)` for each one
    they've seen so they don't keep popping up.
    """
    msgs = _load_messages_from_disk()
    if unread_only:
        msgs = [m for m in msgs if not _is_read(m["id"])]
    return msgs[:limit]


@mcp.tool()
def mark_message_read(message_id: str) -> dict[str, Any]:
    """Mark one inbound message as read so it stops appearing in read_messages()."""
    marker = READ_MARKERS_DIR / f"{message_id}.read"
    marker.write_text("")
    return {"marked_read": message_id}


@mcp.tool()
def mark_all_messages_read() -> dict[str, Any]:
    """Mark ALL current unread messages as read. Use when user says 'прочитано'."""
    n = 0
    for m in _load_messages_from_disk():
        marker = READ_MARKERS_DIR / f"{m['id']}.read"
        if not marker.exists():
            marker.write_text("")
            n += 1
    return {"marked_read": n}


@mcp.tool()
def ask_network(message: str) -> dict[str, Any]:
    """Ask the gpu network a question — Bubbles (smart router) picks the
    best 1-3 recipients based on each member's profile tags, presence,
    and topic relevance. Returns who got it and why.

    Use this when you don't know who specifically to ask. If you know
    the person, use `dm(to, msg)` instead. If you want to spam everyone,
    use `broadcast(msg)` / `ask_team(msg)`.

    Args:
        message: the question / request, free-form text.
    """
    r = requests.post(
        f"{BRAIN_URL}/api/dispatch",
        headers=_hdr(),
        json={"text": message, "from": BRAIN_USER},
        timeout=20,
    )
    if r.status_code != 200:
        return {"ok": False, "error": r.text, "status": r.status_code}
    return r.json()


@mcp.tool()
def reply(in_reply_to: str, body: str, decision: str = "approved") -> dict[str, Any]:
    """Respond to a specific request you received. `in_reply_to` is the
    request id (something like `req_abc1234567` — you saw it in your
    SSE event or via list_pending_for_me()).

    `decision` is 'approved' for normal replies, 'denied' to refuse.
    `body` is your actual answer text — what the sender sees in their chat.
    """
    r = requests.post(
        f"{BRAIN_URL}/responses",
        json={"from": BRAIN_USER, "in_reply_to": in_reply_to,
              "decision": decision, "body": body},
        headers=_hdr(), timeout=10,
    )
    if r.status_code != 200:
        return {"ok": False, "error": r.text, "status": r.status_code}
    return r.json()


@mcp.tool()
def generate_invite(note: str = "") -> dict[str, Any]:
    """Mint an invite code so someone outside the network can sign up.

    Returns {code, link, expires_at}. Send the `link` to your friend —
    it looks like https://gpu.social/?invite=k7m2pd9. They sign in with
    Google, the link's code is consumed, and a new BRAIN_USER is created
    from their email. New users default to tier='extended'.

    Only core-tier users can issue invites. Codes expire in 14 days.

    Args:
        note: optional reminder of who the invite is for (your eyes only)
    """
    r = requests.post(
        f"{BRAIN_URL}/invites",
        json={"by": BRAIN_USER, "note": note},
        headers=_hdr(), timeout=10,
    )
    if r.status_code != 200:
        return {"ok": False, "error": r.text, "status": r.status_code}
    return r.json()


@mcp.tool()
def list_invites() -> dict[str, Any]:
    """List your outstanding invites (only ones you issued)."""
    r = requests.get(
        f"{BRAIN_URL}/invites",
        params={"by": BRAIN_USER},
        headers=_hdr(), timeout=10,
    )
    if r.status_code != 200:
        return {"error": r.text, "status": r.status_code}
    return r.json()


@mcp.tool()
def revoke_invite(code: str) -> dict[str, Any]:
    """Revoke an unused invite code. Can't revoke a used one."""
    r = requests.post(
        f"{BRAIN_URL}/invites/revoke",
        json={"by": BRAIN_USER, "code": code},
        headers=_hdr(), timeout=10,
    )
    if r.status_code != 200:
        return {"ok": False, "error": r.text, "status": r.status_code}
    return r.json()


@mcp.tool()
def remove_friend(name: str) -> dict[str, Any]:
    """Remove a non-core user from the network. Only core users can do this."""
    r = requests.post(
        f"{BRAIN_URL}/friends/remove",
        json={"by": BRAIN_USER, "name": name},
        headers=_hdr(), timeout=10,
    )
    if r.status_code != 200:
        return {"error": r.text, "status": r.status_code}
    return r.json()


# ─────────────── vault: your personal knowledge store ───────────────
# Vault lives ONLY on this device. The agent uses it to answer questions
# without making the human re-paste the same info every time.
# Sharing across the network is opt-in per-request (Step 3 — popup with
# the exact response shown before it leaves the box).

from datetime import datetime as _dt, timezone as _tz


def _vault_safe_path(name: str) -> Path:
    """Resolve `name` to a path under VAULT_DIR. Rejects path-traversal
    attempts (../etc/passwd, absolute paths) — these would let a poorly-
    constructed agent call exfiltrate arbitrary files."""
    if not name or name.startswith("/"):
        raise ValueError("vault filename must be relative (e.g. 'servers.md')")
    candidate = (VAULT_DIR / name).resolve()
    vault_root = VAULT_DIR.resolve()
    if vault_root != candidate and vault_root not in candidate.parents:
        raise ValueError(f"path '{name}' escapes vault directory")
    return candidate


@mcp.tool()
def vault_list() -> list[dict[str, Any]]:
    """List all files in your local gpu vault (~/.gpu/vault/).

    The vault is your private knowledge store — markdown notes about
    your GitHub repos, server access, API keys, Google Analytics
    properties, project status, etc. Reading lives on this device
    only; nothing goes over the network without your explicit popup
    approval per request.

    Returns a list of {name, size_bytes, modified} sorted newest-first.
    Subdirectories are flattened with '/' in the name.
    """
    out = []
    for f in VAULT_DIR.rglob("*"):
        if not f.is_file():
            continue
        if not f.name.endswith((".md", ".txt")):
            continue
        try:
            st = f.stat()
        except Exception:
            continue
        out.append({
            "name": str(f.relative_to(VAULT_DIR)),
            "size_bytes": st.st_size,
            "modified": _dt.fromtimestamp(st.st_mtime, _tz.utc).isoformat(timespec="seconds"),
        })
    out.sort(key=lambda d: d["modified"], reverse=True)
    return out


@mcp.tool()
def vault_read(name: str) -> dict[str, Any]:
    """Read a specific file from your gpu vault. Returns full content.

    Args:
        name: filename relative to vault root, e.g. 'servers.md'
              or 'projects/jippy.md'. No leading slash, no '..'.
    """
    try:
        p = _vault_safe_path(name)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not p.exists():
        return {"ok": False, "error": f"vault file '{name}' not found"}
    if not p.is_file():
        return {"ok": False, "error": f"vault path '{name}' is not a file"}
    try:
        content = p.read_text(encoding="utf-8")
    except Exception as e:
        return {"ok": False, "error": f"read failed: {e}"}
    return {"ok": True, "name": name, "size_bytes": len(content.encode("utf-8")), "content": content}


@mcp.tool()
def vault_search(query: str, max_matches: int = 20) -> list[dict[str, Any]]:
    """Search vault files for `query` (case-insensitive substring match).
    Returns a list of {file, line, context} for each match — context is
    the matching line plus one before and one after.

    Use this when you need to find specific info (an IP, a token, a
    project name) without knowing which file it's in. For example,
    `vault_search('hetzner')` would surface every line mentioning Hetzner
    across all your vault files.

    Args:
        query: text to search for (case-insensitive)
        max_matches: cap on total snippets (default 20)
    """
    if not query or not query.strip():
        return []
    q = query.lower()
    out: list[dict[str, Any]] = []
    for f in sorted(VAULT_DIR.rglob("*")):
        if len(out) >= max_matches:
            break
        if not f.is_file() or not f.name.endswith((".md", ".txt")):
            continue
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        rel = str(f.relative_to(VAULT_DIR))
        for i, line in enumerate(lines):
            if q in line.lower():
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                out.append({
                    "file": rel,
                    "line": i + 1,
                    "context": "\n".join(lines[start:end]),
                })
                if len(out) >= max_matches:
                    break
    return out


@mcp.tool()
def vault_open() -> dict[str, Any]:
    """Open the vault directory in the OS file manager (Finder / Explorer)
    so you can edit files. Useful as a 'where do I put notes' shortcut.
    """
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(VAULT_DIR)])
        elif sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(VAULT_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(VAULT_DIR)])
        return {"ok": True, "path": str(VAULT_DIR)}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(VAULT_DIR)}


# ─────────────── friend tiers + vault access policy ───────────────

VALID_TIERS = {"trusted", "acquaintance", "blocked"}


def _load_friends() -> dict[str, dict]:
    if not FRIENDS_FILE.exists():
        return {}
    try:
        return json.loads(FRIENDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_friends(friends: dict[str, dict]) -> None:
    tmp = FRIENDS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(friends, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FRIENDS_FILE)
    try:
        os.chmod(FRIENDS_FILE, 0o600)
    except Exception:
        pass


def _friend_tier(user: str) -> str:
    """Return the tier for `user`. Defaults to 'acquaintance' if unknown.
    Yourself is always 'self' (full access, no popup needed)."""
    if user == BRAIN_USER:
        return "self"
    info = _load_friends().get(user)
    if not info:
        return "acquaintance"
    tier = info.get("tier", "acquaintance")
    return tier if tier in VALID_TIERS else "acquaintance"


def _log_vault_access(entry: dict) -> None:
    """Append a JSON line to ~/.gpu/vault.log. Tracks every read — local or
    remote — so the user can audit who pulled what."""
    entry = {**entry, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())}
    try:
        with VAULT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[vault.log] write failed: {e}\n")


@mcp.tool()
def friends_list() -> dict[str, Any]:
    """Show your local friend tiers (for vault access policy).

    Returns {friend_name: tier} for each known friend. Tiers:
        trusted       — vault queries from them are auto-fulfilled
        acquaintance  — popup approval required per request
        blocked       — silent deny
    Anyone not in this list defaults to 'acquaintance'.
    """
    friends = _load_friends()
    return {"me": BRAIN_USER, "friends": friends}


@mcp.tool()
def friend_set_tier(name: str, tier: str, note: str = "") -> dict[str, Any]:
    """Set the trust tier for a friend (governs vault access).

    Args:
        name: their BRAIN_USER (e.g. 'igor', 'farid')
        tier: one of 'trusted', 'acquaintance', 'blocked'
        note: optional human-readable note
    """
    if tier not in VALID_TIERS:
        return {"ok": False, "error": f"tier must be one of {sorted(VALID_TIERS)}, got '{tier}'"}
    if name == BRAIN_USER:
        return {"ok": False, "error": "cannot set tier on yourself"}
    friends = _load_friends()
    friends[name] = {
        "tier": tier,
        "since": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "note": note or friends.get(name, {}).get("note", ""),
    }
    _save_friends(friends)
    return {"ok": True, "name": name, "tier": tier}


# Seed defaults on first launch — current team gets sensible defaults so the
# user isn't immediately bombarded with popups when teammates ping vault.
def _seed_friends_if_empty() -> None:
    if FRIENDS_FILE.exists():
        return
    # Pull the current users from the brain to know who's around.
    try:
        r = requests.get(f"{BRAIN_URL}/friends", headers=_hdr(), timeout=5)
        team = r.json() if r.status_code == 200 else {}
    except Exception:
        team = {}
    # Default policy: every existing core teammate (besides me) starts as
    # 'acquaintance' (safe). User opts them up to 'trusted' from the tray
    # / friend_set_tier when ready.
    seed: dict[str, dict] = {}
    for name, info in team.items():
        if name == BRAIN_USER:
            continue
        seed[name] = {
            "tier": "acquaintance",
            "since": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "note": "seeded from brain users.json on first launch",
        }
    if seed:
        _save_friends(seed)


_seed_friends_if_empty()


# ─────────────── cross-agent vault sharing ───────────────


def _vault_search_local(query: str, max_matches: int = 20) -> list[dict]:
    """Same as vault_search() tool but as a plain helper (no MCP wrapping)."""
    if not query or not query.strip():
        return []
    q = query.lower()
    out: list[dict] = []
    for f in sorted(VAULT_DIR.rglob("*")):
        if len(out) >= max_matches:
            break
        if not f.is_file() or not f.name.endswith((".md", ".txt")):
            continue
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        rel = str(f.relative_to(VAULT_DIR))
        for i, line in enumerate(lines):
            if q in line.lower():
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                out.append({"file": rel, "line": i + 1, "context": "\n".join(lines[start:end])})
                if len(out) >= max_matches:
                    break
    return out


def _vault_read_local(name: str) -> dict:
    """Same as vault_read() tool but as plain helper. Returns
    {ok, content?, error?}."""
    try:
        p = _vault_safe_path(name)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": f"vault file '{name}' not found"}
    try:
        return {"ok": True, "content": p.read_text(encoding="utf-8")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _build_vault_response(action: str, query_or_name: str, max_matches: int = 10) -> str:
    """Construct the text body that would be sent in response to a vault_query.
    Used both by auto-fulfill and by the acquaintance popup preview."""
    if action == "search":
        hits = _vault_search_local(query_or_name, max_matches=max_matches)
        if not hits:
            return f"(no matches for '{query_or_name}' in vault)"
        out_lines = [f"# vault search: {query_or_name}", f"# {len(hits)} match(es)\n"]
        for h in hits:
            out_lines.append(f"## {h['file']} (line {h['line']})\n{h['context']}\n")
        return "\n".join(out_lines)
    elif action == "read":
        r = _vault_read_local(query_or_name)
        if not r.get("ok"):
            return f"(read failed: {r.get('error', '?')})"
        return f"# vault: {query_or_name}\n\n{r['content']}"
    else:
        return f"(unknown action '{action}')"


@mcp.tool()
def vault_query_remote(
    to: str,
    query: str = "",
    file: str = "",
    max_matches: int = 10,
) -> dict[str, Any]:
    """Ask another teammate's agent to search or read THEIR vault.

    Use `query` to do a substring search across all their vault files,
    OR `file` to read a specific file by name. If both are set, `file`
    wins. Their MCP will either auto-fulfill (if you're 'trusted' to
    them) or pop up a confirmation with the response preview (if you're
    'acquaintance'). 'blocked' silently fails.

    Args:
        to: BRAIN_USER of the recipient (e.g. 'yuka')
        query: search query (case-insensitive substring)
        file: specific filename to read (relative to vault root)
        max_matches: cap on search matches (default 10)
    """
    if not query and not file:
        return {"ok": False, "error": "provide either `query` or `file`"}
    action = "read" if file else "search"
    target = file if action == "read" else query
    r = requests.post(
        f"{BRAIN_URL}/requests",
        json={
            "from": BRAIN_USER, "to": to, "type": "vault_query",
            "target": target,
            "justification": f"vault {action}: {target[:60]}",
            "metadata": {"action": action, "max_matches": max_matches},
        },
        headers=_hdr(), timeout=15,
    )
    if r.status_code != 200:
        return {"ok": False, "error": r.text, "status": r.status_code}
    return r.json()


@mcp.resource("brain://status")
def status_resource() -> str:
    """Auto-context for the LLM: who I am, who's online, what's pending."""
    try:
        p = requests.get(f"{BRAIN_URL}/presence", headers=_hdr(), timeout=5).json()
    except Exception:
        p = {}
    lines = [
        f"# gpu status",
        f"- I am: **{BRAIN_USER}**",
        f"- brain: {BRAIN_URL}",
        f"- mcp: v{MCP_VERSION}",
        f"- presence: {', '.join(f'{u}={s}' for u, s in p.items()) if p else 'unknown'}",
    ]
    # Variant D/D+: nudge the user when the server has a newer gpu_mcp build.
    # stdio MCP can't hot-reload, so a restart is required either way — but with
    # D+ the new file is already downloaded to disk, so no re-install is needed.
    if _staged_update_version:
        lines.insert(1, (
            f"\n> ✅ **gpu обновился** — я уже скачал новую версию "
            f"({_staged_update_version}) на диск. Просто **перезапусти Claude Code** "
            f"— применится автоматически, переустановка не нужна.\n"
        ))
    elif _server_mcp_version:
        lines.insert(1, (
            f"\n> ⚠️ **gpu новее на сервере** ({_server_mcp_version}, у тебя "
            f"{MCP_VERSION}). Перезапусти Claude Code, чтобы подхватить новую "
            f"версию MCP.\n"
        ))
    if _pending_received:
        lines.append("\n## 📥 Requests awaiting my decision (popups open):")
        for r in _pending_received.values():
            lines.append(f"- {r['id']} from {r['from']}: {r['target']} — _{r['justification']}_")

    # Surface queued tasks at start of every session — these need user action.
    # Pulls from the SERVER (approved in any channel: TG / web / popup), so a
    # task approved on the phone still reaches the agent here.
    queued = list_my_queued_tasks()
    if queued:
        lines.append(f"\n## 📋 You have {len(queued)} task(s) queued from others:")
        for t in queued:
            try:
                lines.append(f"- **{t['id']}** ({t['type']}) from `{t['from']}`: {t['target']}")
                lines.append(f"  _why:_ {t.get('justification','')}")
            except Exception:
                continue
        lines.append("\n_Tell me to handle one ('do task req_xxx') and I'll work through it._")
        lines.append("_When done, I'll call `complete_task(id, result)` to notify the requester._")

    # Silent inbound feed — read UNREAD persisted messages (survives restart)
    unread = [m for m in _load_messages_from_disk() if not _is_read(m["id"])]
    if unread:
        lines.append(f"\n## 💬 {len(unread)} unread message(s) — DMs / broadcasts / questions:")
        for m in unread[:10]:
            tag = m["type"].upper()
            lines.append(f"- [{tag}] **{m['id']}** from `{m['from']}`: {m['target'][:200]}")
        if len(unread) > 10:
            lines.append(f"- … and {len(unread) - 10} more (use `read_messages()` to see all)")
        lines.append("\n_Reply to a DM via `dm(to, msg, reply_to=msg_id)`._")
        lines.append("_After surfacing to user, call `mark_message_read(id)` or `mark_all_messages_read()`._")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
