from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pocket_i_app.bridge import MemoryRuntime, handle


def tiny_embedder(texts):
    return [[float(len(text)), float(sum(ord(char) for char in text) % 101)] for text in texts]


class DesktopBridgeTests(unittest.TestCase):
    def test_connect_builds_private_index_and_persists_counts_only_state(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            data_dir = Path(directory) / "private-memory"
            codex = home / ".codex" / "sessions"
            codex.mkdir(parents=True)
            private = "PRIVATE MEMORY TEXT"
            (codex / "one.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "session_meta", "payload": {"id": "private-session"}}),
                        json.dumps({"type": "event_msg", "payload": {"type": "user_message", "message": private}}),
                    ]
                ),
                encoding="utf-8",
            )

            before = handle("memory-status", data_dir=data_dir)
            connected = handle("connect", data_dir=data_dir, home=home, embed=tiny_embedder)
            after = handle("memory-status", data_dir=data_dir)

            self.assertFalse(before["connected"])
            self.assertTrue(connected["connected"])
            self.assertEqual(1, connected["indexed_messages"])
            self.assertTrue(after["connected"])
            self.assertEqual(1, after["total_conversations"])
            self.assertEqual(0o600, (data_dir / "index.sqlite3").stat().st_mode & 0o777)
            self.assertEqual(0o600, (data_dir / "memory-state.json").stat().st_mode & 0o777)
            self.assertNotIn(private.encode(), (data_dir / "index.sqlite3").read_bytes())
            self.assertNotIn(private, (data_dir / "memory-state.json").read_text(encoding="utf-8"))
            self.assertNotIn("private-session", json.dumps(connected))

    def test_health_is_counts_only_contract(self):
        result = handle("health")
        self.assertEqual("ready", result["status"])
        self.assertEqual(["codex", "claude_code"], result["enabled_sources"])

    def test_scan_exposes_counts_but_not_private_text(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            sessions = codex_home / "sessions"
            sessions.mkdir()
            home = codex_home / "home"
            claude = home / ".claude" / "projects" / "private-project"
            claude.mkdir(parents=True)
            private = "DO-NOT-SHOW-THIS-TEXT"
            rows = [
                {"type": "session_meta", "payload": {"id": "private-session"}},
                {"type": "event_msg", "payload": {"type": "user_message", "message": private}},
            ]
            (sessions / "one.jsonl").write_text(
                "\n".join(json.dumps(item) for item in rows), encoding="utf-8"
            )
            claude_rows = [
                {
                    "type": "user",
                    "sessionId": "private-claude-session",
                    "uuid": "private-message",
                    "message": {"role": "user", "content": private},
                }
            ]
            (claude / "one.jsonl").write_text(
                "\n".join(json.dumps(item) for item in claude_rows), encoding="utf-8"
            )
            environment = dict(os.environ, CODEX_HOME=str(codex_home), HOME=str(home))
            process = subprocess.run(
                [sys.executable, "-m", "pocket_i_app.bridge", "--action", "scan"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(0, process.returncode)
            result = json.loads(process.stdout)
            self.assertEqual(2, result["total_conversations"])
            self.assertEqual(
                {"codex": 1, "claude_code": 1},
                {item["source"]: item["conversations"] for item in result["adapters"]},
            )
            self.assertEqual(
                {"schema_version", "status", "version", "total_conversations", "adapters"},
                set(result),
            )
            self.assertTrue(all(set(item) == {"source", "state", "conversations"} for item in result["adapters"]))
            self.assertNotIn(private, process.stdout)
            self.assertNotIn(str(codex_home), process.stdout)
            self.assertNotIn("private-session", process.stdout)
            self.assertNotIn("private-claude-session", process.stdout)
            self.assertNotIn("private-project", process.stdout)

    def test_unknown_action_fails_closed(self):
        with self.assertRaises(ValueError):
            handle("read-everything")

    def test_runtime_keeps_library_warm_and_returns_local_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            data_dir = Path(directory) / "private-memory"
            codex = home / ".codex" / "sessions"
            codex.mkdir(parents=True)
            private = "Copper thermostat needs a cold reset after drift."
            (codex / "one.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"type": "session_meta", "payload": {"id": "private-session"}}),
                        json.dumps({"type": "event_msg", "payload": {"type": "user_message", "message": private}}),
                    ]
                ),
                encoding="utf-8",
            )
            runtime = MemoryRuntime(data_dir=data_dir, home=home, embed=tiny_embedder)
            runtime.dispatch("connect")
            original_library = runtime.library
            original_index = runtime.index

            routed = runtime.dispatch("route", question="copper thermostat")

            self.assertIs(runtime.library, original_library)
            self.assertIs(runtime.index, original_index)
            self.assertEqual(1, routed["returned"])
            self.assertIn("Copper thermostat", routed["items"][0]["preview"])
            self.assertNotIn("private-session", json.dumps(routed))


if __name__ == "__main__":
    unittest.main()
