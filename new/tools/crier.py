#!/usr/bin/env python3
"""The town crier: announces new open questions — the game calls.

Reads the public corpus, finds open questions that have not been announced
yet, composes a call, and posts it to Telegram channels/groups when a bot
token is configured. Without a token it prints the drafts (dry run), so it
is safe to run at any time.

Environment:
  CRIER_CORPUS        corpus URL (default: production corpus)
  CRIER_SITE          site base for links (default: https://new.joinmultiplayer.ai)
  CRIER_STATE         state file remembering announced ids
                      (default: ./crier-state.json next to this script)
  TELEGRAM_BOT_TOKEN  bot token from @BotFather (empty -> dry run)
  TELEGRAM_CHAT_IDS   comma-separated chat ids or @channelnames

The crier never invents content: everything in the post comes verbatim from
the public corpus record.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

CORPUS = os.environ.get("CRIER_CORPUS", "https://joinmultiplayer.ai/api/public/corpus.json")
SITE = os.environ.get("CRIER_SITE", "https://new.joinmultiplayer.ai").rstrip("/")
STATE = pathlib.Path(os.environ.get("CRIER_STATE", str(pathlib.Path(__file__).parent / "crier-state.json")))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHATS = [chat.strip() for chat in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if chat.strip()]


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "joinmultiplayer-crier/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"announced": []}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def compose(question: dict) -> str:
    payload = question.get("payload", {})
    text = (payload.get("question") or "").strip()
    needed = (payload.get("needed") or "").strip()
    qid = question["public_id"]
    lines = [
        "🔥 Игра зовёт. / The game calls.",
        "",
        f"Открыт вопрос {qid} — ход ещё ничей:",
        f"«{text}»",
    ]
    if needed:
        needed_short = needed if len(needed) <= 300 else needed[:297] + "…"
        lines += ["", f"Чего не хватает: {needed_short}"]
    lines += [
        "",
        f"Подключайся: {SITE}/question/?id={qid}",
        f"Или приведи своего ИИ: {SITE}/play/",
    ]
    return "\n".join(lines)


def post_telegram(text: str) -> None:
    for chat in CHATS:
        payload = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": False}).encode()
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
            if not result.get("ok"):
                print(f"telegram error for {chat}: {result}", file=sys.stderr)


def main() -> None:
    corpus = fetch_json(CORPUS)
    state = load_state()
    announced = set(state.get("announced", []))
    fresh = [
        question
        for question in corpus.get("questions", [])
        if question.get("status") == "open"
        and not (question.get("traces") or [])
        and question.get("public_id") not in announced
    ]
    if not fresh:
        print("crier: nothing new to announce")
        return
    for question in fresh:
        text = compose(question)
        if TOKEN and CHATS:
            post_telegram(text)
            print(f"crier: announced {question['public_id']} to {len(CHATS)} chat(s)")
        else:
            print("crier: DRY RUN (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS to post)")
            print("-" * 60)
            print(text)
            print("-" * 60)
        announced.add(question["public_id"])
    state["announced"] = sorted(announced)
    save_state(state)


if __name__ == "__main__":
    main()
