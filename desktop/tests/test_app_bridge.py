from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pocket_i_app.bridge import handle


class DesktopBridgeTests(unittest.TestCase):
    def test_health_is_counts_only_contract(self):
        result = handle("health")
        self.assertEqual("ready", result["status"])
        self.assertEqual("codex", result["source"])

    def test_scan_exposes_counts_but_not_private_text(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            sessions = codex_home / "sessions"
            sessions.mkdir()
            private = "DO-NOT-SHOW-THIS-TEXT"
            rows = [
                {"type": "session_meta", "payload": {"id": "private-session"}},
                {"type": "event_msg", "payload": {"type": "user_message", "message": private}},
            ]
            (sessions / "one.jsonl").write_text(
                "\n".join(json.dumps(item) for item in rows), encoding="utf-8"
            )
            environment = dict(os.environ, CODEX_HOME=str(codex_home))
            process = subprocess.run(
                [sys.executable, "-m", "pocket_i_app.bridge", "--action", "scan"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(0, process.returncode)
            result = json.loads(process.stdout)
            self.assertEqual(1, result["total_conversations"])
            self.assertEqual(1, result["total_messages"])
            self.assertNotIn(private, process.stdout)
            self.assertNotIn(str(codex_home), process.stdout)
            self.assertNotIn("private-session", process.stdout)

    def test_unknown_action_fails_closed(self):
        with self.assertRaises(ValueError):
            handle("read-everything")


if __name__ == "__main__":
    unittest.main()

