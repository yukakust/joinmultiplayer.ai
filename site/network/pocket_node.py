#!/usr/bin/env python3
"""Run one E003 pocket i node on a headless Mac or Linux computer."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import math
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post(site: str, path: str, value: dict) -> dict:
    request = Request(
        f"{site.rstrip('/')}{path}",
        data=json.dumps(value).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "pocket-i-e003-node/0.1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"laboratory rejected the request ({error.code}): {detail}") from error
    except URLError as error:
        raise RuntimeError(f"laboratory is unreachable: {error.reason}") from error


def train(table: list[int]) -> list[list[float]]:
    weights = [[0.0] * 16 for _ in range(16)]
    for _ in range(180):
        for key, target in enumerate(table):
            row = weights[key]
            maximum = max(row)
            exps = [math.exp(value - maximum) for value in row]
            total = sum(exps)
            for output in range(16):
                gradient = exps[output] / total - float(output == target)
                row[output] -= 0.35 * gradient
    return weights


def metrics(weights: list[list[float]], table: list[int]) -> dict:
    correct = sum(
        max(range(16), key=lambda output: weights[key][output]) == target
        for key, target in enumerate(table)
    )
    delta_norm = math.sqrt(sum(value * value for row in weights for value in row))
    checksum = hashlib.sha256(json.dumps(weights).encode("utf-8")).hexdigest()
    return {
        "accuracy": correct / 16,
        "delta_norm": delta_norm,
        "weight_checksum": checksum,
        "runtime": "python-headless/0.1",
    }


def save_state(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="https://joinmultiplayer.ai")
    parser.add_argument("--label", default="server")
    parser.add_argument(
        "--state",
        type=Path,
        default=Path.home() / ".local" / "share" / "pocket-i" / "e003-node.json",
    )
    args = parser.parse_args()

    if args.state.exists():
        state = json.loads(args.state.read_text(encoding="utf-8"))
        print(f"Resuming {state['node_id']} from {args.state}")
    else:
        join_token = getpass.getpass("Private E003 join token: ").strip()
        if not join_token:
            raise RuntimeError("join token is required")
        joined = post(
            args.site,
            "/api/pocket-network/join",
            {"join_token": join_token, "label": args.label},
        )
        weights = train(joined["training_table"])
        state = {
            "node_id": joined["node_id"],
            "node_token": joined["node_token"],
            "weights": weights,
            "training_table": joined["training_table"],
        }
        save_state(args.state, state)
        post(
            args.site,
            "/api/pocket-network/ready",
            {"node_token": state["node_token"], "metrics": metrics(weights, state["training_table"])},
        )
        print(f"{state['node_id']} trained locally and is ready. State: {args.state}")

    while True:
        status = post(args.site, "/api/pocket-network/status", {"token": state["node_token"]})
        if status["status"] == "running" and status["node_status"] == "ready":
            capsules = [state["weights"][key] for key in status["task_keys"]]
            post(
                args.site,
                "/api/pocket-network/contribute",
                {"node_token": state["node_token"], "capsules": capsules},
            )
            print(f"{state['node_id']} returned {len(capsules)} complete capsules.")
        elif status["status"] == "complete":
            print(json.dumps(status["result"], indent=2))
            return 0
        time.sleep(2)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"pocket i node error: {error}")
        raise SystemExit(1)
