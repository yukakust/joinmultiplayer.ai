"""Deny-by-default credential gate for a complete outbound knowledge capsule."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SecretRule:
    category: str
    pattern: re.Pattern[str]
    value_group: int = 0


FLAGS = re.IGNORECASE | re.MULTILINE
RULES = (
    SecretRule("private_key", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----", FLAGS)),
    SecretRule("authorization_header", re.compile(r"\bauthorization\s*:\s*(?:bearer|basic)\s+[A-Za-z0-9+/_=.:-]{8,}", FLAGS)),
    SecretRule("credential_url", re.compile(r"\b(?:https?|ssh|postgres(?:ql)?|mysql|redis)://[^\s/@:]+:[^\s/@]{4,}@", FLAGS)),
    SecretRule("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    SecretRule("openai_token", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    SecretRule("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    SecretRule("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b", re.IGNORECASE)),
    SecretRule("stripe_live_key", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b")),
    SecretRule("google_api_key", re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b")),
    SecretRule("huggingface_token", re.compile(r"\bhf_[A-Za-z0-9]{24,}\b")),
    SecretRule("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    SecretRule(
        "labelled_credential",
        re.compile(
            r"\b(?:api[_ -]?key|access[_ -]?token|auth[_ -]?token|password|passwd|client[_ -]?secret|session[_ -]?token|secret|cookie)"
            r"\b\s*(?::|=)\s*[\"']?([^\s\"',;}{]{8,})",
            FLAGS,
        ),
        1,
    ),
)

SAFE_VALUES = {
    "redacted", "removed", "placeholder", "changeme", "example", "none",
    "not-set", "not_set", "unset", "null", "xxxxxxxx", "********",
}


def _placeholder(value: str) -> bool:
    lowered = value.strip().strip("\"'").casefold()
    return (
        lowered in SAFE_VALUES
        or lowered.startswith(("${", "{{", "<"))
        or lowered.endswith(("}", ">"))
        or "example" in lowered
    )


def detect_secret_categories(text: str) -> tuple[str, ...]:
    """Return detector categories only. Never return matched secret material."""
    categories = set()
    for rule in RULES:
        for match in rule.pattern.finditer(text):
            if rule.category == "labelled_credential" and _placeholder(match.group(rule.value_group)):
                continue
            categories.add(rule.category)
            break
    return tuple(sorted(categories))


def inspect_capsule(capsule: Any) -> dict[str, Any]:
    """Return an allow payload or a value-free blocked receipt."""
    serialized = json.dumps(capsule, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    categories = detect_secret_categories(serialized)
    if categories:
        return {
            "status": "blocked",
            "reason": "credential_detected",
            "detector_categories": list(categories),
        }
    return {"status": "allowed", "capsule": capsule}
