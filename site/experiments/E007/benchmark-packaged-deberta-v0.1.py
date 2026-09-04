#!/usr/bin/env python3
"""Time the packaged Pocket i DeBERTa without reading the owner's memory."""

from __future__ import annotations

import json
import plistlib
import queue
import subprocess
import tempfile
import threading
import time
from pathlib import Path


APP = Path("/Applications/Pocket i.app")
OUTPUT = Path.home() / "Downloads" / "Pocket-i-DeBERTa-benchmark.json"
TIMEOUT_SECONDS = 900


def candidate(number: int) -> dict[str, object]:
    quote = f"Verified source {number}: isolate power before restarting unit Kest-{number}."
    return {
        "candidate_id": f"E{number}",
        "quote": quote,
        "claim": f"Power must be isolated before Kest-{number} is restarted.",
        "source_contexts": [{"text": quote, "exact_quotes": [quote]}],
    }


def read_line(stream: object, result: queue.Queue[str]) -> None:
    result.put(stream.readline())


def request(process: subprocess.Popen[str], request_id: int, count: int) -> dict[str, object]:
    payload = {
        "id": request_id,
        "action": "nli",
        "payload": {"candidates": [candidate(index) for index in range(1, count + 1)]},
    }
    started = time.monotonic()
    process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    process.stdin.flush()

    lines: queue.Queue[str] = queue.Queue()
    threading.Thread(target=read_line, args=(process.stdout, lines), daemon=True).start()
    next_notice = 15
    while True:
        elapsed = time.monotonic() - started
        try:
            line = lines.get(timeout=1)
            break
        except queue.Empty:
            if process.poll() is not None:
                raise RuntimeError(f"Pocket i core stopped with code {process.returncode}")
            if elapsed >= TIMEOUT_SECONDS:
                raise TimeoutError(f"No response after {TIMEOUT_SECONDS} seconds")
            if elapsed >= next_notice:
                print(f"  still running: {int(elapsed)}s", flush=True)
                next_notice += 15

    elapsed = time.monotonic() - started
    if not line:
        raise RuntimeError("Pocket i core returned no response")
    response = json.loads(line)
    if not response.get("ok"):
        raise RuntimeError(str(response.get("error", "Local NLI failed")))
    items = response.get("result", {}).get("items", [])
    return {
        "candidate_count": count,
        "seconds": round(elapsed, 3),
        "labels_returned": len(items),
        "labels": [item.get("label") for item in items],
    }


def main() -> int:
    executable = APP / "Contents" / "Resources" / "sidecar" / "pocket-i-core"
    nli_dir = APP / "Contents" / "Resources" / "nli"
    info_path = APP / "Contents" / "Info.plist"
    if not executable.is_file() or not nli_dir.is_dir() or not info_path.is_file():
        raise SystemExit("Pocket i is not installed, or its packaged DeBERTa files are missing.")
    with info_path.open("rb") as handle:
        version = plistlib.load(handle).get("CFBundleShortVersionString", "unknown")

    with tempfile.TemporaryDirectory(prefix="pocket-i-deberta-benchmark-") as data_dir:
        process = subprocess.Popen(
            [
                str(executable),
                "--action", "serve",
                "--data-dir", data_dir,
                "--nli-dir", str(nli_dir),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        try:
            print("[1/3] Cold DeBERTa: one synthetic comparison", flush=True)
            cold_one = request(process, 1, 1)
            print(f"  done: {cold_one['seconds']}s", flush=True)
            print("[2/3] Warm DeBERTa: one synthetic comparison", flush=True)
            warm_one = request(process, 2, 1)
            print(f"  done: {warm_one['seconds']}s", flush=True)
            print("[3/3] Warm DeBERTa: eight synthetic comparisons", flush=True)
            warm_eight = request(process, 3, 8)
            print(f"  done: {warm_eight['seconds']}s", flush=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    report = {
        "schema_version": "pocket-i-packaged-deberta-benchmark-v0.1",
        "privacy": "Synthetic text only; the owner's connected memory was not read.",
        "app_version": version,
        "runs": {
            "cold_one": cold_one,
            "warm_one": warm_one,
            "warm_eight": warm_eight,
        },
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"BENCHMARK_READY: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
