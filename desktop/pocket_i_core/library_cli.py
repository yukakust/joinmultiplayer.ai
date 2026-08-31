"""Inspect or write the strict local conversation library."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .library import SOURCE_NAMES, scan_local_library


def _write_private(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "extract"))
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--source", choices=("all",) + SOURCE_NAMES, default="all")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sources = SOURCE_NAMES if args.source == "all" else (args.source,)
    library = scan_local_library(home=args.home, codex_home=args.codex_home, sources=sources)
    if args.command == "extract":
        if args.output is None:
            raise SystemExit("extract requires --output")
        payload = {
            "schema_version": "desktop-local-library-v0.1-private",
            "conversations": [
                {
                    "conversation_id": item.conversation_id,
                    "source": item.source,
                    "messages": [
                        {"coordinate": message.coordinate, "role": message.role, "text": message.text}
                        for message in item.messages
                    ],
                }
                for item in library.conversations
            ],
        }
        _write_private(args.output, payload)
    summary = library.public_summary()
    if args.output is not None:
        summary["private_output_written"] = True
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

