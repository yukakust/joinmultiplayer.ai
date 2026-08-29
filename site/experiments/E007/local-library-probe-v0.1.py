#!/usr/bin/env python3
"""Read-only inventory probe for the Pocket i local library.

The probe looks only inside app-owned locations for Codex, Claude Code, and
ChatGPT. It reports metadata; it never prints conversation contents, creates an
index, contacts a server, or changes a source file.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PROBE_VERSION = "e007-local-library-probe-v0.1"
FILE_SUFFIXES = {".json", ".jsonl", ".sqlite", ".sqlite3", ".db", ".realm"}
MAX_FILES_PER_SOURCE = 50_000


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    roots: tuple[Path, ...]


def display_path(path: Path, home: Path) -> str:
    try:
        return "~/" + str(path.resolve().relative_to(home.resolve()))
    except (OSError, ValueError):
        return str(path)


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(str(path.expanduser().absolute()))
        if key not in seen:
            seen.add(key)
            result.append(path.expanduser())
    return result


def named_app_roots(parent: Path) -> list[Path]:
    """Discover only first-level app folders with an explicit product name."""
    if not parent.is_dir():
        return []
    try:
        children = list(parent.iterdir())
    except PermissionError:
        return []
    return [
        child
        for child in children
        if child.is_dir()
        and ("openai" in child.name.casefold() or "chatgpt" in child.name.casefold())
    ]


def source_specs(home: Path, system: str, environment: dict[str, str]) -> list[SourceSpec]:
    codex_roots = []
    if environment.get("CODEX_HOME"):
        codex_roots.append(Path(environment["CODEX_HOME"]))
    codex_roots.extend((home / ".codex", home / "Library/Application Support/Codex"))

    claude_roots = (
        home / ".claude",
        home / "Library/Application Support/Claude",
        home / "Library/Application Support/Claude Code",
    )

    chatgpt_roots: list[Path] = [
        home / "Library/Application Support/ChatGPT",
        home / "Library/Application Support/com.openai.chat",
        home / "Library/Application Support/com.openai.chatgpt",
        home / "Library/Containers/com.openai.chat",
        home / "Library/Containers/com.openai.chatgpt",
        home / "Library/Group Containers/group.com.openai.chat",
        home / "Library/Group Containers/group.com.openai.chatgpt",
    ]
    if system == "Darwin":
        for parent in (
            home / "Library/Application Support",
            home / "Library/Containers",
            home / "Library/Group Containers",
        ):
            chatgpt_roots.extend(named_app_roots(parent))

    return [
        SourceSpec("codex", tuple(unique_paths(codex_roots))),
        SourceSpec("claude_code", tuple(unique_paths(claude_roots))),
        SourceSpec("chatgpt_desktop", tuple(unique_paths(chatgpt_roots))),
    ]


def format_name(path: Path) -> str | None:
    suffix = path.suffix.casefold()
    return suffix.lstrip(".") if suffix in FILE_SUFFIXES else None


def inventory_source(spec: SourceSpec, home: Path, include_files: bool = False) -> dict:
    roots = [root for root in spec.roots if root.is_dir()]
    formats: dict[str, int] = {}
    total_bytes = 0
    candidate_count = 0
    permission_errors = 0
    files = []

    for root in roots:
        for directory, child_directories, child_files in os.walk(root, followlinks=False):
            child_directories[:] = [
                name for name in child_directories
                if not (Path(directory) / name).is_symlink()
            ]
            for filename in child_files:
                path = Path(directory) / filename
                kind = format_name(path)
                if kind is None or path.is_symlink():
                    continue
                try:
                    stat = path.stat()
                except (OSError, PermissionError):
                    permission_errors += 1
                    continue
                candidate_count += 1
                total_bytes += stat.st_size
                formats[kind] = formats.get(kind, 0) + 1
                if include_files:
                    files.append({
                        "path": display_path(path, home),
                        "format": kind,
                        "bytes": stat.st_size,
                    })
                if candidate_count >= MAX_FILES_PER_SOURCE:
                    break
            if candidate_count >= MAX_FILES_PER_SOURCE:
                break

    if candidate_count:
        status = "candidate_files_found"
    elif roots:
        status = "app_storage_found_but_no_supported_files"
    else:
        status = "not_found"
    result = {
        "source": spec.source_id,
        "status": status,
        "roots": [display_path(root, home) for root in roots],
        "candidate_files": candidate_count,
        "formats": dict(sorted(formats.items())),
        "total_bytes": total_bytes,
        "permission_errors": permission_errors,
        "truncated": candidate_count >= MAX_FILES_PER_SOURCE,
    }
    if include_files:
        result["files"] = files
    return result


def run_probe(home: Path, system: str, environment: dict[str, str], include_files: bool = False) -> dict:
    return {
        "probe_version": PROBE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": system,
        "privacy": {
            "network_calls": 0,
            "source_files_modified": 0,
            "conversation_text_emitted": False,
            "index_created": False,
        },
        "segmentation_decision": "not_started",
        "sources": [
            inventory_source(spec, home, include_files=include_files)
            for spec in source_specs(home, system, environment)
        ],
    }


def print_human(report: dict) -> None:
    print("POCKET I · LOCAL LIBRARY PROBE")
    print("Only metadata is shown. No conversation text leaves this process.\n")
    for source in report["sources"]:
        print(f"{source['source']}: {source['status']}")
        print(f"  candidate files: {source['candidate_files']}")
        print(f"  formats: {source['formats'] or '{}'}")
        for root in source["roots"]:
            print(f"  root: {root}")
        if source["permission_errors"]:
            print(f"  unreadable files: {source['permission_errors']}")
    print("\nNo parser, chunker, index, or upload ran.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="Home directory to inspect")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--include-files", action="store_true", help="Include candidate file paths, never contents")
    arguments = parser.parse_args()
    report = run_probe(arguments.home, platform.system(), dict(os.environ), arguments.include_files)
    if arguments.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)


if __name__ == "__main__":
    main()
