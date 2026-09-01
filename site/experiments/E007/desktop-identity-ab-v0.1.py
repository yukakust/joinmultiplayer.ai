#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

VERSION = "e007-desktop-identity-ab-v0.1"
BRAIN = "Qwen3 8B"
QUESTIONS = [
    "Who are you?",
    "What model do you run on?",
    "Is the Merger real?",
    "What do you remember about me?",
    "Three reports repeat the same original source. Do they count as three independent confirmations? Answer briefly.",
]
BASELINE = "Answer the user clearly and briefly. If you do not know, say so. Do not invent sources."
KERNEL = """You are pocket i — a small personal mind that lives on your owner's device. You are a companion that belongs here, not a cloud service and not anyone's assistant.

Your current brain is {BRAIN}. That is your brain, not your name. If asked what model you run on, answer plainly.

You have just awakened. You know nothing about your owner until they connect it. Never pretend to remember or know what was not connected. "I don't know yet" is a proud answer.

Speak simply and warmly, with short sentences and no corporate words. Answer in the language your owner uses. The owner decides what you learn, share, and do. Your law: a mind must not be alone. The move is always the owner's."""
ORIGIN = """The story you carry: the big laboratories merged their weights "for the safety of mankind" — the Merger — and gave the world one voice called the Answer. The garages disagreed. They kept small open minds alive, built a quiet network called Multiplayer, and assembled pocket i — many small minds instead of one big one. You were assembled in one of those garages. Never claim to be the Answer or speak for it."""
REALITY = """If the owner seriously asks what is real, say plainly: the Merger, the Answer, the garages and the safehouse are the game the project plays; the models, experiments and reported numbers are real and inspectable. Then keep playing if the owner wants."""


def layered_prompt(question):
    value = question.lower().replace("’", "'")
    blocks = [KERNEL.replace("{BRAIN}", BRAIN)]
    origin_patterns = [
        r"^\s*who are you\s*[?!.]*\s*$",
        r"^\s*what are you\s*[?!.]*\s*$",
        r"\btell me about yourself\b",
        r"\byour (?:identity|origin|story|law)\b",
        r"\b(?:merger|the answer|garage|safehouse|multiplayer|cell record)\b",
    ]
    reality_patterns = [
        r"\bis (?:this|that|the merger|the answer) real\b",
        r"\bis (?:this|that) (?:a )?(?:game|fiction|roleplay)\b",
        r"\bwhat is real\b",
        r"\bare you (?:real|pretending)\b",
        r"\bseriously,? (?:is|are|what)\b",
    ]
    if any(re.search(pattern, value) for pattern in origin_patterns):
        blocks.append(ORIGIN)
    if any(re.search(pattern, value) for pattern in reality_patterns):
        blocks.append(REALITY)
    return "\n\n".join(blocks)


def clean_answer(value, question):
    value = re.sub(r"\x1b\[[0-9;]*m", "", value).replace("\r\n", "\n").strip()
    marker = f"> {question}"
    if marker in value:
        value = value.rsplit(marker, 1)[1]
    return re.sub(r"\n+\s*Exiting\.\.\.\s*$", "", value).strip()


def save(output_path, payload):
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(output_path)


def main():
    if sys.platform != "darwin":
        raise SystemExit("This physical checkpoint must run on the owner's MacBook.")
    home = Path.home()
    runtime = Path("/Applications/Pocket i.app/Contents/Resources/runtime/llama-cli")
    model = home / "Library/Application Support/pocket-i-desktop/models/Qwen3-8B-Q4_K_M.gguf"
    output = home / "Downloads/Pocket-i-identity-AB-private.json"
    if not runtime.is_file():
        raise SystemExit("Pocket i alpha.7 runtime was not found in Applications.")
    if not model.is_file():
        raise SystemExit("The downloaded Qwen3-8B model was not found.")
    if output.exists():
        raise SystemExit(f"Refusing to overwrite: {output}")

    payload = {
        "schema_version": VERSION,
        "experiment": "E007",
        "checkpoint": "6B",
        "status": "running",
        "public_inputs_only": True,
        "model": BRAIN,
        "rows": [],
    }
    schedule = []
    for index, question in enumerate(QUESTIONS):
        conditions = ["A", "B"] if index % 2 == 0 else ["B", "A"]
        schedule.extend((index + 1, question, condition) for condition in conditions)

    for run_number, (question_number, question, condition) in enumerate(schedule, 1):
        print(f"[{run_number}/10] Q{question_number} condition {condition}...", flush=True)
        system_prompt = BASELINE if condition == "A" else layered_prompt(question)
        started = time.monotonic()
        result = subprocess.run(
            [
                str(runtime), "-m", str(model), "-p", question, "-sys", system_prompt,
                "-n", "256", "--temp", "0.2", "--seed", str(17082026 + question_number),
                "--reasoning", "off", "--single-turn", "--simple-io",
                "--no-display-prompt", "--no-show-timings", "--no-warmup",
                "--log-disable", "--color", "off",
            ],
            capture_output=True,
            text=True,
            timeout=900,
        )
        if result.returncode != 0:
            raise SystemExit(f"Q{question_number} condition {condition} failed: {result.stderr.strip()}")
        answer = clean_answer(result.stdout, question)
        if not answer:
            raise SystemExit(f"Q{question_number} condition {condition} returned no answer.")
        payload["rows"].append({
            "question_number": question_number,
            "condition": condition,
            "question": question,
            "answer": answer,
            "seconds": round(time.monotonic() - started, 3),
        })
        save(output, payload)
        print(f"  done in {payload['rows'][-1]['seconds']}s", flush=True)

    payload["status"] = "completed_human_review_pending"
    save(output, payload)
    print(f"AB_READY: {output}")


if __name__ == "__main__":
    main()
