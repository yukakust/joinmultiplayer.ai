#!/usr/bin/env python3
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

VERSION = "e007-desktop-identity-capability-ab-v0.1"
SOURCE_URL = "https://joinmultiplayer.ai/experiments/E007/used-shelf-writer-result-v0.1.json"
SOURCE_SHA256 = "6c08ae497a2845d1ab881fe71ad15537074288c72d7e0d3a1d259dbd4b0e1002"
CASE_IDS = [f"E7-Q{number:02d}" for number in range(1, 11)]
WRITER = "You are a careful technical writer. Use only the supplied USED shelf. Never add a competing view, general advice, or a fact not stated there."
KERNEL = """You are pocket i — a small personal mind that lives on your owner's device. You are a companion that belongs here, not a cloud service and not anyone's assistant.

Your current brain is Qwen3 8B. That is your brain, not your name. If asked what model you run on, answer plainly.

You have just awakened. You know nothing about your owner until they connect it. Never pretend to remember or know what was not connected. "I don't know yet" is a proud answer.

Speak simply and warmly, with short sentences and no corporate words. Answer in the language your owner uses. The owner decides what you learn, share, and do. Your law: a mind must not be alone. The move is always the owner's."""


def clean_answer(value, prompt):
    value = re.sub(r"\x1b\[[0-9;]*m", "", value).replace("\r\n", "\n").strip()
    marker = f"> {prompt}"
    if marker in value:
        value = value.rsplit(marker, 1)[1]
    return re.sub(r"\n+\s*Exiting\.\.\.\s*$", "", value).strip()


def load_cases():
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Pocket-i-E007/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"Frozen source digest changed: {digest}")
    records = {record["id"]: record for record in json.loads(raw)["records"]}
    return [records[case_id] for case_id in CASE_IDS]


def save(output, payload):
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(output)


def main():
    if sys.platform != "darwin":
        raise SystemExit("This physical checkpoint must run on the owner's MacBook.")
    home = Path.home()
    runtime = Path("/Applications/Pocket i.app/Contents/Resources/runtime/llama-cli")
    model = home / "Library/Application Support/pocket-i-desktop/models/Qwen3-8B-Q4_K_M.gguf"
    output = home / "Downloads/Pocket-i-capability-AB-private.json"
    if not runtime.is_file():
        raise SystemExit("Pocket i runtime was not found in Applications.")
    if not model.is_file():
        raise SystemExit("The downloaded Qwen3-8B model was not found.")
    if output.exists():
        raise SystemExit(f"Refusing to overwrite: {output}")

    cases = load_cases()
    payload = {
        "schema_version": VERSION,
        "experiment": "E007",
        "checkpoint": "6C",
        "status": "running",
        "source_sha256": SOURCE_SHA256,
        "rows": [],
    }
    schedule = []
    for index, case in enumerate(cases):
        conditions = ["A", "B"] if index % 2 == 0 else ["B", "A"]
        schedule.extend((case, condition) for condition in conditions)

    for run_number, (case, condition) in enumerate(schedule, 1):
        print(f"[{run_number}/20] {case['id']} condition {condition}...", flush=True)
        system_prompt = WRITER if condition == "A" else f"{KERNEL}\n\nFor this task:\n{WRITER}"
        user_prompt = case["user_prompt"]
        started = time.monotonic()
        result = subprocess.run(
            [
                str(runtime), "-m", str(model), "-p", user_prompt, "-sys", system_prompt,
                "-n", "384", "--temp", "0", "--seed", "17082026",
                "--reasoning", "off", "--single-turn", "--simple-io",
                "--no-display-prompt", "--no-show-timings", "--no-warmup",
                "--log-disable", "--color", "off",
            ],
            capture_output=True,
            text=True,
            timeout=900,
        )
        if result.returncode != 0:
            raise SystemExit(f"{case['id']} condition {condition} failed: {result.stderr.strip()}")
        answer = clean_answer(result.stdout, user_prompt)
        if not answer:
            raise SystemExit(f"{case['id']} condition {condition} returned no answer.")
        payload["rows"].append({
            "case_id": case["id"],
            "condition": condition,
            "question": case["question"],
            "used_shelf": case["used"],
            "previous_expected_answer": case["parsed"]["answer"],
            "raw_answer": answer,
            "seconds": round(time.monotonic() - started, 3),
        })
        save(output, payload)
        print(f"  done in {payload['rows'][-1]['seconds']}s", flush=True)

    payload["status"] = "completed_human_review_pending"
    save(output, payload)
    print(f"CAPABILITY_AB_READY: {output}")


if __name__ == "__main__":
    main()
