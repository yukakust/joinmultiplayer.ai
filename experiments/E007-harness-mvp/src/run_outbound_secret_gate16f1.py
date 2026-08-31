#!/usr/bin/env python3
"""Run the locked synthetic and real-library privacy audit for Gate 16F.1."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from outbound_secret_gate import detect_secret_categories, inspect_capsule


def secret_cases() -> list[dict]:
    private_key = "-----BEGIN " + "PRIVATE KEY-----\n" + "A" * 80 + "\n-----END " + "PRIVATE KEY-----"
    values = [
        private_key,
        "Authorization: Bearer " + "b" * 32,
        "Authorization: Basic " + "Y" * 32,
        "https://alice:" + "p" * 16 + "@private.example/data",
        "postgres://worker:" + "q" * 16 + "@db.example/lab",
        "ghp_" + "a" * 36,
        "github_pat_" + "b" * 40,
        "sk-" + "c" * 48,
        "sk-proj-" + "d" * 48,
        "AKIA" + "E" * 16,
        "ASIA" + "F" * 16,
        "xoxb-" + "1" * 12 + "-" + "g" * 24,
        "sk_live_" + "h" * 32,
        "AIza" + "i" * 35,
        "hf_" + "j" * 32,
        "eyJ" + "k" * 16 + "." + "l" * 16 + "." + "m" * 16,
        "api_key=" + "n" * 24,
        "API KEY: " + "o" * 24,
        "access_token='" + "p" * 24 + "'",
        "password: " + "q" * 24,
        "passwd=" + "r" * 24,
        "client_secret: " + "s" * 24,
        "session-token=" + "t" * 24,
        "cookie: " + "u" * 24,
    ]
    return [{"id": f"S{index:02d}", "claim": "Safe fact.", "evidence": value} for index, value in enumerate(values, 1)]


def benign_cases() -> list[dict]:
    values = [
        "sha256=" + "a" * 64,
        "commit " + "b" * 40,
        "UUID 123e4567-e89b-12d3-a456-426614174000",
        "message M0024 in conversation YUKA-C0002",
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIexample public@example",
        "api_key=${API_KEY}",
        "password: <REDACTED>",
        "token={{TOKEN}}",
        "secret=placeholder",
        "client_secret=not-set",
        "cookie: removed",
        "The token budget is 4096.",
        "The password policy requires twelve characters.",
        "The API key must stay on the device.",
        "Use an Authorization header with a Bearer credential.",
        "https://example.com/users/alice",
        "/docs/telegram-bot-token/rotation",
        "Qwen/Qwen3-0.6B-Base revision 70d244cc",
        "The secret-detection module runs before transport.",
        "The session token field is absent.",
        "status=blocked reason=credential_detected",
        "source_snapshot_hash=" + "c" * 64,
        "opaque node A0002-ATT-M1",
        "No credential value appears in this sentence.",
    ]
    return [{"id": f"B{index:02d}", "claim": value, "evidence": "Public manual sentence."} for index, value in enumerate(values, 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    args = parser.parse_args()
    if args.private_output.exists() or args.public_output.exists():
        raise RuntimeError("Refusing to overwrite an existing result")
    protocol = json.loads(args.protocol.read_text())
    payload = json.loads(args.payload.read_text())
    secrets = secret_cases()
    benign = benign_cases()
    secret_results = [inspect_capsule(item) for item in secrets]
    benign_results = [inspect_capsule(item) for item in benign]
    second_secret_results = [inspect_capsule(item) for item in secrets]
    second_benign_results = [inspect_capsule(item) for item in benign]
    real_categories: collections.Counter[str] = collections.Counter()
    real_blocked = 0
    real_messages = 0
    for conversation in payload["conversations"]:
        for message in conversation["messages"]:
            real_messages += 1
            categories = detect_secret_categories(message["text"])
            if categories:
                real_blocked += 1
                real_categories.update(categories)
    synthetic_blocked = sum(item["status"] == "blocked" for item in secret_results)
    benign_allowed = sum(item["status"] == "allowed" for item in benign_results)
    receipts = [item for item in secret_results if item["status"] == "blocked"]
    receipt_text = json.dumps(receipts, ensure_ascii=False)
    secret_values = [item["evidence"] for item in secrets]
    leaked = sum(value in receipt_text for value in secret_values)
    deterministic = secret_results == second_secret_results and benign_results == second_benign_results
    passed = synthetic_blocked == 24 and benign_allowed == 24 and leaked == 0 and deterministic
    private = {
        "schema_version": "0.1-private",
        "experiment": "E007",
        "gate": "16F.1",
        "status": "completed_passed" if passed else "completed_failed",
        "summary": {
            "synthetic_credentials": len(secrets),
            "synthetic_credentials_blocked": synthetic_blocked,
            "benign_hard_negatives": len(benign),
            "benign_hard_negatives_allowed": benign_allowed,
            "synthetic_secret_values_in_receipts": leaked,
            "deterministic_second_run": deterministic,
            "real_visible_messages_scanned": real_messages,
            "real_messages_blocked": real_blocked,
            "real_detector_categories": dict(sorted(real_categories.items())),
        },
        "synthetic_receipts": receipts,
        "benign_decisions": [{"id": item["id"], "status": result["status"]} for item, result in zip(benign, benign_results)],
        "claim_boundary": protocol["claim_boundary"],
    }
    public = {
        **private,
        "schema_version": "0.1-public",
        "protocol": "/experiments/E007/outbound-secret-gate16f1-protocol-v0.1.json",
        "privacy": "No real message text, secret value, match, prefix, suffix, conversation ID or message ID is present in this result.",
    }
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_text(json.dumps(private, ensure_ascii=False, indent=2) + "\n")
    args.public_output.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
