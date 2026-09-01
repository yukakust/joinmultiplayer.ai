"""Small private bridge between the desktop window and the Python core.

The bridge deliberately exposes counts only. Conversation text, paths and
identifiers never cross into the Electron renderer at this checkpoint.
"""

from __future__ import annotations

import argparse
import json
import sys

from pocket_i_core.library import scan_local_library


ENABLED_SOURCES = ("codex", "claude_code")


def handle(action: str) -> dict[str, object]:
    if action == "health":
        return {
            "status": "ready",
            "version": "desktop-alpha-checkpoint-6d",
            "enabled_sources": list(ENABLED_SOURCES),
            "privacy": "no conversation text, paths or identifiers",
        }
    if action == "scan":
        library = scan_local_library(sources=ENABLED_SOURCES)
        return {
            "schema_version": "desktop-library-counts-v0.1",
            "status": "ready",
            "version": "desktop-alpha-checkpoint-6d",
            "total_conversations": len(library.conversations),
            "adapters": [
                {
                    "source": adapter.source,
                    "state": adapter.status,
                    "conversations": adapter.conversations,
                }
                for adapter in library.adapters
            ],
        }
    raise ValueError("unsupported bridge action")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pocket i desktop private bridge")
    parser.add_argument("--action", choices=("health", "scan"), required=True)
    args = parser.parse_args(argv)
    try:
        result = handle(args.action)
    except Exception as error:  # fail closed at the renderer boundary
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": type(error).__name__,
                    "message": "The local library could not be inspected.",
                }
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
